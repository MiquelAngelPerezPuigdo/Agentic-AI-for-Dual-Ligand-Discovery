"""Small CPU-compatible projected-embedding GP for the upstream GoLLuM optimizer.

This adapter learns the embedding projection through GP marginal likelihood.
It does not update the original language-model weights.
"""
import torch
from torch import nn
import gpytorch
from botorch.models import SingleTaskGP
from botorch.models.transforms.outcome import Standardize


class ProjectionKernel(gpytorch.kernels.Kernel):
    def __init__(self, input_dim, projection_dim):
        super().__init__()
        self.project = nn.Sequential(nn.Linear(input_dim, projection_dim), nn.ELU()).double()
        self.base = gpytorch.kernels.ScaleKernel(gpytorch.kernels.MaternKernel(nu=2.5)).double()

    def forward(self, x1, x2, diag=False, **params):
        return self.base(self.project(x1), self.project(x2), diag=diag, **params)


class ProjectedGP(SingleTaskGP):
    def __init__(self, train_x, train_y, seed=42, steps=100):
        torch.manual_seed(seed)
        likelihood = gpytorch.likelihoods.GaussianLikelihood(noise_constraint=gpytorch.constraints.GreaterThan(1e-4))
        likelihood.noise = 0.01
        super().__init__(train_X=train_x, train_Y=train_y,
                         likelihood=likelihood,
                         covar_module=ProjectionKernel(train_x.shape[-1], min(32, train_x.shape[-1])),
                         outcome_transform=Standardize(1))
        self.steps = steps
        self.to(dtype=torch.float64)

    def fit(self):
        self.train()
        self.likelihood.train()
        mll = gpytorch.mlls.ExactMarginalLogLikelihood(self.likelihood, self)
        optimizer = torch.optim.Adam(self.parameters(), lr=0.025)
        for _ in range(self.steps):
            optimizer.zero_grad()
            loss = -mll(self(self.train_inputs[0]), self.train_targets)
            if not torch.isfinite(loss):
                raise ValueError("GoLLuM GP fitting became nonfinite")
            loss.backward()
            torch.nn.utils.clip_grad_norm_(self.parameters(), 10)
            optimizer.step()
        self.eval()
        self.likelihood.eval()

    def predict(self, x):
        self.eval()
        self.likelihood.eval()
        with torch.no_grad():
            posterior = self.posterior(x)
        return posterior.mean, posterior.variance
