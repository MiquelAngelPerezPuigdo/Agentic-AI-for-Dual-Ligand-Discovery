from __future__ import annotations

import random
import numpy as np
from rdkit import Chem, DataStructs
from rdkit.Chem import rdFingerprintGenerator

from .inventory import pair_id
from .io import finite, wells


def pair_features(inventory, candidates):
    """Symmetric structural features for explicitly labelled fingerprint initialization."""
    generator = rdFingerprintGenerator.GetMorganGenerator(radius=2, fpSize=256)
    fingerprints = {}
    for key, ligand in inventory.items():
        arr = np.zeros(256)
        DataStructs.ConvertToNumpyArray(generator.GetFingerprint(Chem.MolFromSmiles(ligand["smiles"])), arr)
        fingerprints[key] = arr
    return np.array([np.r_[fingerprints[c["ligand_a"]] + fingerprints[c["ligand_b"]],
                               abs(fingerprints[c["ligand_a"]] - fingerprints[c["ligand_b"]])]
                     for c in candidates])


def maxmin(candidates, features, count, exclude=(), seed=42):
    """Deterministic diversity initialization. This is NOT a trained GoLLuM surrogate."""
    excluded = set(exclude)
    available = [i for i, c in enumerate(candidates) if c["pair_id"] not in excluded]
    if len(available) < count or count < 0:
        raise ValueError("Insufficient exploration candidates")
    if count == 0:
        return []
    x = np.asarray(features, dtype=float)
    if x.ndim != 2 or len(x) != len(candidates) or not np.isfinite(x).all():
        raise ValueError("Invalid exploration features")
    chosen = [random.Random(seed).choice(available)]
    distance = ((x - x[chosen[0]]) ** 2).sum(axis=1)
    while len(chosen) < count:
        options = [i for i in available if i not in chosen]
        pick = max(options, key=lambda i: (distance[i], candidates[i]["pair_id"]))
        chosen.append(pick)
        distance = np.minimum(distance, ((x - x[pick]) ** 2).sum(axis=1))
    return [candidates[i]["pair_id"] for i in chosen]


def ranked_ids(rows, candidates):
    expected = {c["pair_id"] for c in candidates}
    if len(rows) != len(expected) or {r["pair_id"] for r in rows} != expected:
        raise ValueError("Ranking must contain each candidate exactly once")
    for row in rows:
        finite(row["mean_score"], "mean_score", 0, 100)
        finite(row["score_sd"], "score_sd", 0)
    return [r["pair_id"] for r in sorted(rows, key=lambda r: (-float(r["mean_score"]), r["pair_id"]))]


def consensus_select(candidates, ranking, features, count, weight=0.5, minimum_percentile=0.25,
                     acquisition=None, required_ligands=()):
    """Greedy rank consensus, with mandatory ligand coverage before ordinary filling.

    Coverage can override the LLM floor; every choice still uses both rank signals.
    The campaign's complete unordered-pair library permits a two-ligand-per-well
    completion bound. Final validation also rejects incomplete sparse selections.
    """
    order = ranked_ids(ranking, candidates)
    n = len(candidates)
    if not 0 <= weight <= 1 or not 0 <= minimum_percentile <= 1 or not 0 <= count <= n:
        raise ValueError("Invalid consensus settings")
    utility = {key: 1-i/max(1, n-1) for i, key in enumerate(order)}
    features = np.asarray(features, dtype=float)
    if features.ndim != 2 or len(features) != n or not np.isfinite(features).all():
        raise ValueError("Features must be finite and match candidate order")
    available = list(range(n))
    above_floor = {i for i, c in enumerate(candidates) if utility[c["pair_id"]] >= minimum_percentile}
    if len(above_floor) < count:
        raise ValueError("LLM percentile floor leaves fewer candidates than required")
    missing = set(required_ligands)
    candidate_ligands = {ligand for c in candidates for ligand in (c["ligand_a"], c["ligand_b"])}
    if missing-candidate_ligands:
        raise ValueError("Required ligands have no candidate pairs: "+", ".join(sorted(missing-candidate_ligands)))
    if (len(missing)+1)//2 > count:
        raise ValueError("Too few pair wells to cover all required ligands")
    if acquisition is not None:
        if set(acquisition) != set(order):
            raise ValueError("GoLLuM acquisition file must cover every candidate")
        fixed = [finite(acquisition[c["pair_id"]], "acquisition") for c in candidates]
    else:
        fixed = None
    selected, trace = [], []
    distance = ((features-features.mean(axis=0))**2).sum(axis=1)
    for step in range(count):
        normal = [i for i in available if i in above_floor]
        new = {i: missing.intersection((candidates[i]["ligand_a"], candidates[i]["ligand_b"]))
               for i in available}
        if missing:
            slots_after = count-step-1
            coverage = [i for i in available if new[i] and (len(missing)-len(new[i])+1)//2 <= slots_after]
            preferred = [i for i in coverage if i in above_floor]
            choices = preferred or coverage
            if not choices:
                raise ValueError("Cannot complete required ligand coverage within the allocated pair wells")
            # Cover two new ligands where possible, using the same consensus to
            # choose between equally useful coverage candidates.
            most_new = max(len(new[i]) for i in choices)
            choices = [i for i in choices if len(new[i]) == most_new]
            rank_pool = normal if preferred else normal+[i for i in coverage if i not in above_floor]
            phase = "coverage"
        else:
            choices = rank_pool = normal
            phase = "consensus"
        if not choices:
            raise ValueError("Not enough candidates remain above the LLM percentile floor")
        broad = sorted(rank_pool, key=lambda i: (-(fixed[i] if fixed is not None else distance[i]), candidates[i]["pair_id"]))
        broad_rank = {i: 1-rank/max(1, len(broad)-1) for rank, i in enumerate(broad)}
        choose = max(choices, key=lambda i: (weight*utility[candidates[i]["pair_id"]]+(1-weight)*broad_rank[i],
                                              utility[candidates[i]["pair_id"]], candidates[i]["pair_id"]))
        key = candidates[choose]["pair_id"]
        selected.append(key)
        newly_covered = sorted(new[choose])
        missing.difference_update(newly_covered)
        trace.append({"pair_id": key, "llm_percentile": utility[key], "exploration_percentile": broad_rank[choose],
                      "consensus_score": weight*utility[key]+(1-weight)*broad_rank[choose],
                      "exploration_method": "trained_gollum_acquisition" if fixed is not None else "diversity_initialization",
                      "selection_step": step+1, "selection_phase": phase,
                      "new_ligands_covered": ";".join(newly_covered), "uncovered_ligands_remaining": len(missing),
                      "llm_floor_override": choose not in above_floor})
        available.remove(choose)
        next_distance = ((features-features[choose])**2).sum(axis=1)
        distance = next_distance if step == 0 else np.minimum(distance, next_distance)
    if missing:
        raise ValueError("Selection omitted required ligands: "+", ".join(sorted(missing)))
    return selected, trace


def round1_required_ligands(config, inventory):
    required = config["design"].get("require_all_ligands_in_round1_pairs", False)
    if not isinstance(required, bool):
        raise ValueError("require_all_ligands_in_round1_pairs must be true or false")
    return set(inventory) if required else set()


def ligand_coverage(inventory, design):
    """Count pair wells only; single-ligand references do not satisfy coverage."""
    counts = dict.fromkeys(inventory, 0)
    for row in design:
        if row["kind"] != "pair":
            continue
        for key in (row["ligand_a"], row["ligand_b"]):
            if key not in counts:
                raise ValueError("Unknown ligand in coverage report: "+key)
            counts[key] += 1
    return [{"ligand_id": key, "name": inventory[key]["name"], "pair_well_count": counts[key],
             "covered": counts[key] > 0} for key in sorted(inventory)]


def validate_round1_coverage(config, inventory, design):
    required = round1_required_ligands(config, inventory)
    if required:
        missing = [row["ligand_id"] for row in ligand_coverage(inventory, design) if not row["covered"]]
        if missing:
            raise ValueError("First-round pair design omits required ligands: "+", ".join(missing))


def make_design(config, inventory, candidates, ranking, exploration, round_number, history=()):
    design = config["design"]
    n = int(design[f"round{round_number}_total"])
    controls = design.get(f"round{round_number}_controls")
    if controls is None:
        raise ValueError(f"Decide round{round_number}_controls, including singles and repeats, first")
    if not 1 <= n <= 96 or len(controls) >= n:
        raise ValueError("Invalid batch/control count")
    candidate_map = {c["pair_id"]: c for c in candidates}
    order = ranked_ids(ranking, candidates)
    excluded = {r["pair_id"] for r in history if r.get("pair_id") and r.get("kind", "pair") == "pair"}
    count = n - len(controls)
    selected = []
    if round_number == 1:
        if len(exploration) != count:
            raise ValueError("Round-one consensus must select exactly the allocated number of pair wells")
        for key in exploration:
            if key not in candidate_map or key in {r[0] for r in selected}:
                raise ValueError("Invalid or duplicate exploration candidate")
            selected.append((key, "consensus_" + design["exploration_backend"]))
    for key in order:
        if len(selected) >= count:
            break
        if key not in excluded and key not in {r[0] for r in selected}:
            selected.append((key, "llm"))
    if len(selected) != count:
        raise ValueError("Not enough untested pairs; repeats must be explicit controls")
    entries = []
    for key, method in selected:
        entries.append({**candidate_map[key], "kind": "pair", "selection_method": method})
    if round_number == 1:
        validate_round1_coverage(config, inventory, entries)
    for control in controls:
        row = {"pair_id": "", "ligand_a": "", "ligand_b": "", **control,
               "selection_method": "specified_control"}
        if row["kind"] not in ("single", "no_ligand", "no_pd", "blank", "pair"):
            raise ValueError(f"Unknown control kind: {row['kind']}")
        for ligand in (row["ligand_a"], row["ligand_b"]):
            if ligand and ligand not in inventory:
                raise ValueError(f"Unknown control ligand: {ligand}")
        if row["kind"] == "single" and (not row["ligand_a"] or row["ligand_b"]):
            raise ValueError("A single control requires exactly one ligand")
        if row["kind"] in ("pair", "no_pd"):
            row["pair_id"] = pair_id(row["ligand_a"], row["ligand_b"])
        entries.append(row)
    random.Random(design["seed"] + round_number).shuffle(entries)
    for i, (row, well) in enumerate(zip(entries, wells()), 1):
        row.update(round=round_number, sample_id=f"R{round_number}-{i:03d}", well=well)
    return entries
