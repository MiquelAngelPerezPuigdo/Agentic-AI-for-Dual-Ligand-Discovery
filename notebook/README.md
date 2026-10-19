# Run the notebook directly on a GPU

All added code runs in ordinary cells in **[batch_suggestions.ipynb](batch_suggestions.ipynb)**. There is no worker script or request/result-file exchange. Embeddings and proposals stay in memory. CSV export is optional and disabled by default (`SAVE_RESULTS = False`).

The notebook still reads the repository's existing inputs and calls its existing inventory and consensus-selection functions. Original repository source files are unchanged.

## Start Jupyter on a GPU node

From the repository's main folder, activate the existing environment and launch Jupyter inside a Slurm GPU allocation:

```bash
conda activate dual-ligand-notebook
srun --partition=mig12gb --account=liac --qos=normal \
  --gres=gpu:1 --ntasks=1 --cpus-per-task=2 --mem=8G --time=01:00:00 \
  python -m jupyter lab --no-browser --ip=0.0.0.0 --port=8890 \
  --ServerApp.port_retries=0 notebook/batch_suggestions.ipynb
```

Keep that terminal running. Jupyter prints a server URL containing the allocated GPU node name and an access token. Connect to that server from VS Code using **Select Kernel → Existing Jupyter Server**, supplying the printed URL with its GPU hostname. Select **HTE (dual-ligand-notebook)** on that server, then **Restart Kernel and Run All Cells**.

The Jupyter server and kernel must run inside the GPU allocation. Selecting the Conda environment on a login node alone does not allocate a GPU. The first GPU check cell reports the GPU name or stops with a clear error. Stop the server with Ctrl+C when finished to release the allocation.

If port 8890 is occupied, choose another port in the launch command. Connecting from a local browser instead of remote VS Code may require an SSH tunnel through the cluster login node.

## Use the notebook

- Change the batch settings and prompt, then run the cells in order.
- Default: **24 repository-method suggestions + 24 Sobol selections**, with all 30 active ligands represented.
- Set `SAMPLER = "maxmin"` to use MaxMin instead.
- T5-base computes fresh embeddings directly on the notebook GPU. The first run downloads model weights; subsequent runs can reuse those weights. No pair-embedding files are loaded or saved.
- Read the in-memory `suggestions` and `coverage` tables and the PCA plots.
- To export, set `SAVE_RESULTS = True`, rerun the settings cell, then run the optional export section. This writes CSVs and settings under `output/notebook_batches/`.

A previous-experiments CSV can exclude tested pairs; exclusion does not retrain a model. Changing chemistry in the embedding prompt requires matching Claude scores. The saved ranking needs no paid API calls.

## First-time installation

The existing `dual-ligand-notebook` environment is already configured. For a new installation, run these commands from the repository's main folder before the GPU launch above:

```bash
conda env create -f notebook/environment.yml
conda activate dual-ligand-notebook
python -m ipykernel install --user --name dual-ligand-notebook --display-name "HTE (dual-ligand-notebook)" --env PYTHONNOUSERSITE 1
```

To update an existing environment, use `conda env update -f notebook/environment.yml` and restart the kernel.

The environment installs the original repository with `-e .`; no changes to `pyproject.toml` are required. Do not use `pip install hte`, which downloads an unrelated package.

The Sobol matching approach follows [ALICE's initializer](https://github.com/schwallergroup/alice/blob/cda460d627e074d3cd57c47df13df08cea9346c6/src/alice/initialization/initializers.py). PCA, finite-candidate matching and ligand coverage affect the final discrete design, which does not retain exact continuous Sobol balance guarantees.
