"""David Ming Segura's consensus/Sobol initialization, without model inference.

The algorithm is the default in notebook/batch_suggestions.ipynb at commit
c2682f3db09eb496b92d11fb6725e9870157e301. It reuses the saved Claude ranking
and verified T5 embeddings. It neither fits a surrogate nor selects round two.
"""
from __future__ import annotations

import hashlib
import importlib.metadata

import numpy as np
from scipy.spatial.distance import cdist
from scipy.stats import qmc
from sklearn.decomposition import PCA
from sklearn.preprocessing import MinMaxScaler, StandardScaler

from .design import consensus_select, rank_percentiles, ranked_ids, round1_required_ligands
from .inventory import pair_id
from .io import finite, object_digest


NOTEBOOK_COMMIT = "c2682f3db09eb496b92d11fb6725e9870157e301"
BACKEND = "lm_consensus_sobol_initialization"


def pca_coordinates(features, dimensions=16, seed=1):
    """Use the notebook's full-SVD StandardScaler -> PCA -> MinMax transform."""
    x = np.asarray(features, dtype=float)
    if x.ndim != 2 or len(x) < 2 or not x.shape[1] or not np.isfinite(x).all():
        raise ValueError("PCA requires at least two finite embedding rows")
    maximum = min(len(x)-1, x.shape[1])
    if type(dimensions) is not int or not 1 <= dimensions <= maximum:
        raise ValueError(f"PCA dimensions must be an integer from 1 to {maximum}")
    if not np.any(np.ptp(x, axis=0)):
        raise ValueError("All embeddings are identical; PCA cannot describe diversity")
    standardized = StandardScaler().fit_transform(x)
    pca = PCA(n_components=dimensions, svd_solver="full", random_state=seed)
    components = pca.fit_transform(standardized)
    coordinates = MinMaxScaler().fit_transform(components)
    return coordinates, components, pca.explained_variance_ratio_


def initial_select(config, inventory, candidates, ranking, features):
    """Return ordered pair IDs, trace and provenance for consensus + Sobol.

    First make the full consensus baseline. Retain a diverse, coverage-aware
    subset in scaled PCA space, then uniquely match Sobol targets to candidates.
    The sampling half has no Claude floor. The final ligand coverage check is
    mandatory when configured; it never silently repairs the sampled result.
    """
    design = config["design"]
    if design.get("initialization_method") != "consensus_sobol":
        raise ValueError("initialization_method must be consensus_sobol")
    if design.get("exploration_backend") != BACKEND or design.get("require_lm_embeddings") is not True:
        raise ValueError("Consensus/Sobol initialization requires the LM embedding backend")
    if type(design.get("require_all_ligands_in_round1_pairs")) is not bool:
        raise ValueError("require_all_ligands_in_round1_pairs must be Boolean")
    total, controls = design.get("round1_total"), design.get("round1_controls")
    if type(total) is not int or not isinstance(controls, list):
        raise ValueError("Decide integer round1_total and round1_controls before initialization")
    count = total-len(controls)
    keep = design.get("initialization_keep_from_consensus")
    seed = design.get("initialization_seed")
    if not 1 <= count <= len(candidates) or type(keep) is not int or not 0 <= keep <= count:
        raise ValueError("Invalid total or retained consensus pair count")
    if type(seed) is not int or not 0 <= seed <= 2**32-1:
        raise ValueError("initialization_seed must be an integer from 0 to 4294967295")
    weight = finite(design["consensus_weight_llm"], "consensus_weight_llm", 0, 1)
    floor = finite(design["minimum_llm_percentile"], "minimum_llm_percentile", 0, 1)
    ids = [row["pair_id"] for row in candidates]
    if len(set(ids)) != len(ids):
        raise ValueError("Duplicate candidate pair IDs")
    for row in candidates:
        a, b = row["ligand_a"], row["ligand_b"]
        if a not in inventory or b not in inventory or a >= b or row["pair_id"] != pair_id(a, b):
            raise ValueError("Candidates must be canonical pairs of different inventory ligands")
    ranked_ids(ranking, candidates)
    x = np.asarray(features, dtype=float)
    if x.ndim != 2 or len(x) != len(candidates) or not x.shape[1] or not np.isfinite(x).all():
        raise ValueError("Features must be finite and match candidate order")
    dimensions = design.get("initialization_pca_dimensions")
    coordinates, _, variance = pca_coordinates(x, dimensions, seed)
    required = set(round1_required_ligands(config, inventory))
    baseline, baseline_trace = consensus_select(
        candidates, ranking, x, count, weight, floor, required_ligands=required)
    index = {key: i for i, key in enumerate(ids)}
    baseline_indices = [index[key] for key in baseline]
    subset_required = required if 2*keep >= len(required) else set()
    retained, retained_trace = consensus_select(
        [candidates[i] for i in baseline_indices],
        [row for row in ranking if row["pair_id"] in baseline],
        coordinates[baseline_indices], keep, 0.0, 0.0,
        required_ligands=subset_required)

    chosen = [index[key] for key in retained]
    available = [i for i in range(len(ids)) if i not in chosen]
    remaining = count-keep
    target_matches = {}
    target_power = (remaining-1).bit_length() if remaining else None
    if remaining:
        targets = qmc.Sobol(d=dimensions, scramble=True, seed=seed).random_base2(target_power)[:remaining]
        original_targets = targets.copy()
        target_indices = list(range(remaining))
        for _ in range(remaining):
            distances = cdist(targets, coordinates[available])
            row, column = np.unravel_index(distances.argmin(), distances.shape)
            selected_index = available.pop(int(column))
            chosen.append(selected_index)
            target_matches[ids[selected_index]] = {
                "sobol_target_index": target_indices.pop(int(row)),
                "sobol_target_distance": float(distances[row, column]),
            }
            targets = np.delete(targets, row, axis=0)
    else:
        original_targets = np.empty((0, dimensions))
    selection = [ids[i] for i in chosen]
    covered = {ligand for i in chosen for ligand in (candidates[i]["ligand_a"], candidates[i]["ligand_b"])}
    if required-covered:
        raise ValueError("Mixed batch is missing required ligands: "+", ".join(sorted(required-covered)))
    if len(selection) != count or len(set(selection)) != count:
        raise ValueError("Initialization did not produce the required distinct pair count")

    utility = rank_percentiles({row["pair_id"]: float(row["mean_score"]) for row in ranking})
    baseline_by_id = {row["pair_id"]: row for row in baseline_trace}
    retained_by_id = {row["pair_id"]: row for row in retained_trace}
    missing, trace = set(required), []
    for step, key in enumerate(selection, 1):
        candidate = candidates[index[key]]
        new = missing.intersection((candidate["ligand_a"], candidate["ligand_b"]))
        missing.difference_update(new)
        base, kept = baseline_by_id.get(key, {}), retained_by_id.get(key, {})
        sampled = step > keep
        trace.append({
            "pair_id": key, "selection_step": step,
            "selection_source": "sobol" if sampled else "repo_consensus",
            "selection_phase": "sobol" if sampled else ("coverage" if new else "retained_diversity"),
            "llm_percentile": utility[key], "below_llm_floor": utility[key] < floor,
            "sampling_below_llm_floor": sampled and utility[key] < floor,
            "llm_floor_override": bool(not sampled and base.get("llm_floor_override", False)),
            "in_baseline_batch": bool(base),
            "baseline_selection_step": base.get("selection_step", ""),
            "baseline_consensus_score": base.get("consensus_score", ""),
            "retained_diversity_percentile": kept.get("exploration_percentile", ""),
            "sobol_target_index": target_matches.get(key, {}).get("sobol_target_index", ""),
            "sobol_target_distance": target_matches.get(key, {}).get("sobol_target_distance", ""),
            "new_ligands_covered": ";".join(sorted(new)), "uncovered_ligands_remaining": len(missing),
        })
    metadata = {
        "schema_version": 1, "initialization_method": "consensus_sobol", "backend": BACKEND,
        "implementation_source": {
            "author": "David Ming Segura", "notebook": "notebook/batch_suggestions.ipynb",
            "commit": NOTEBOOK_COMMIT,
            "paper": "https://arxiv.org/abs/2609.11790",
            "alice_initializer": "https://github.com/schwallergroup/alice/blob/cda460d627e074d3cd57c47df13df08cea9346c6/src/alice/initialization/initializers.py",
            "scope": "ALICE-inspired initialization; SciPy Sobol, not ALICE surrogate training or feedback optimization",
        },
        "candidate_count": len(candidates), "embedding_dimensions": x.shape[1], "pairs": count,
        "consensus_weight_llm": weight, "minimum_llm_percentile": floor,
        "initialization_keep_from_consensus": keep, "initialization_seed": seed,
        "pca_dimensions": dimensions, "pca_svd_solver": "full",
        "preprocessing": ["StandardScaler", "PCA", "MinMaxScaler"],
        "pca_explained_variance_ratio": variance.tolist(), "pca_variance_retained": float(variance.sum()),
        "baseline_pair_ids": baseline, "baseline_trace": baseline_trace,
        "retained_consensus_pair_ids": retained, "retained_subset_trace": retained_trace,
        "required_ligands": sorted(required), "retained_subset_required_ligands": sorted(subset_required),
        "selection_source_counts": {"repo_consensus": keep, "sobol": remaining},
        "sampling_uses_claude_floor": False,
        "sampling_below_llm_floor_count": sum(row["sampling_below_llm_floor"] for row in trace),
        "sobol": {
            "engine": "scipy.stats.qmc.Sobol", "scramble": True, "seed": seed,
            "draw_power": target_power, "draw_count": 2**target_power if remaining else 0,
            "retained_target_count": remaining, "targets": original_targets.tolist(),
            "matching": "greedy closest unused target-candidate pair, excluding retained consensus pairs",
            "balance_note": "Truncation and finite-candidate matching do not preserve exact continuous power-of-two balance guarantees.",
        },
        "input_digests": {
            "config": object_digest(config), "inventory": object_digest(inventory),
            "candidates": object_digest(candidates), "ranking": object_digest(ranking),
            "features_float64_sha256": hashlib.sha256(np.ascontiguousarray(x).tobytes()).hexdigest(),
        },
        "packages": {name: importlib.metadata.version(name) for name in ("numpy", "scipy", "scikit-learn")},
        "paid_api_calls": 0, "model_inference_calls": 0,
    }
    return selection, trace, metadata
