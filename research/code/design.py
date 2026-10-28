from __future__ import annotations

import random
from collections import Counter
import numpy as np
from rdkit import Chem, DataStructs
from rdkit.Chem import rdFingerprintGenerator

from .inventory import pair_id
from .io import finite, wells, reaction_wells, well_name


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


def ranked_ids(rows, candidates):
    expected = {c["pair_id"] for c in candidates}
    if len(rows) != len(expected) or {r["pair_id"] for r in rows} != expected:
        raise ValueError("Ranking must contain each candidate exactly once")
    for row in rows:
        finite(row["mean_score"], "mean_score", 0, 100)
        finite(row["score_sd"], "score_sd", 0)
    return [r["pair_id"] for r in sorted(rows, key=lambda r: (-float(r["mean_score"]), r["pair_id"]))]


def rank_percentiles(values):
    """Average ranks for ties, so IDs do not invent differences in model scores."""
    order = sorted(values, key=lambda key: (-values[key], str(key)))
    result = {}
    start = 0
    while start < len(order):
        end = start+1
        while end < len(order) and values[order[end]] == values[order[start]]:
            end += 1
        percentile = 1-(start+end-1)/2/max(1, len(order)-1)
        for key in order[start:end]:
            result[key] = percentile
        start = end
    return result


def consensus_select(candidates, ranking, features, count, weight=0.5, minimum_percentile=0.25,
                     required_ligands=()):
    """Greedy rank consensus, with mandatory ligand coverage before ordinary filling.

    Coverage can override the LLM floor; every choice still uses both rank signals.
    The campaign's complete unordered-pair library permits a two-ligand-per-well
    completion bound. Final validation also rejects incomplete sparse selections.
    """
    ranked_ids(ranking, candidates)
    n = len(candidates)
    if not 0 <= weight <= 1 or not 0 <= minimum_percentile <= 1 or not 0 <= count <= n:
        raise ValueError("Invalid consensus settings")
    utility = rank_percentiles({row["pair_id"]: float(row["mean_score"]) for row in ranking})
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
        broad_rank = rank_percentiles({i: distance[i] for i in rank_pool})
        choose = max(choices, key=lambda i: (weight*utility[candidates[i]["pair_id"]]+(1-weight)*broad_rank[i],
                                              utility[candidates[i]["pair_id"]], candidates[i]["pair_id"]))
        key = candidates[choose]["pair_id"]
        selected.append(key)
        newly_covered = sorted(new[choose])
        missing.difference_update(newly_covered)
        trace.append({"pair_id": key, "llm_percentile": utility[key], "exploration_percentile": broad_rank[choose],
                      "consensus_score": weight*utility[key]+(1-weight)*broad_rank[choose],
                      "exploration_method": "diversity_initialization",
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


def validate_design(config, inventory, rows, history=()):
    """Validate edited CSVs as well as generated designs against the campaign."""
    excluded = {entry["ligand_id"] for entry in config["design"].get("excluded_ligands", [])}
    if any(row.get(k) in excluded for row in rows for k in ("ligand_a", "ligand_b")):
        raise ValueError("Design uses an excluded unavailable ligand")
    if not rows or len({str(row["round"]) for row in rows}) != 1:
        raise ValueError("A design must contain one nonempty round")
    round_number = str(rows[0]["round"])
    if round_number not in ("1", "2") or len(rows) != config["design"][f"round{round_number}_total"]:
        raise ValueError("Design count differs from the configured round")
    available = set(reaction_wells(config))
    if any(row.get("well") not in available for row in rows):
        raise ValueError("Design well is absent from the reaction definition")
    lc = [well_name(row["lc_well"]) for row in rows]
    if len(set(lc)) != len(lc):
        raise ValueError("Duplicate LC destination well")
    controls = config["design"].get(f"round{round_number}_controls")
    if controls is None:
        raise ValueError("Specify the configured controls before making a design")
    def signature(row):
        return (row["kind"], row.get("ligand_a", ""), row.get("ligand_b", ""))
    actual_controls = [row for row in rows if row["kind"] != "pair"
                       or row.get("selection_method") == "specified_control"]
    if Counter(map(signature, actual_controls)) != Counter(map(signature, controls)):
        raise ValueError("Design controls differ from the configured reference/control wells")
    experimental = [row for row in rows if row["kind"] == "pair"
                    and row.get("selection_method") != "specified_control"]
    ids = [row["pair_id"] for row in experimental]
    if len(ids) != len(set(ids)):
        raise ValueError("Experimental pairs must be distinct; repeats require explicit controls")
    for row in rows:
        a, b = row.get("ligand_a", ""), row.get("ligand_b", "")
        if any(key and key not in inventory for key in (a, b)):
            raise ValueError("Unknown ligand in design")
        if row["kind"] in ("pair", "no_pd") and (not a or not b or a >= b or row["pair_id"] != pair_id(a, b)):
            raise ValueError("Pair ID must match two different, canonically ordered ligands")
        if row["kind"] == "single" and (not a or b or row.get("pair_id")):
            raise ValueError("A single reference requires one ligand and an empty pair ID")
    if round_number == "1":
        validate_round1_coverage(config, inventory, rows)
    else:
        counts = Counter(key for row in rows for key in (row.get("ligand_a"), row.get("ligand_b")) if key)
        for key, limit in config["design"].get("round2_ligand_caps", {}).items():
            if key not in inventory or type(limit) is not int or limit < 0:
                raise ValueError("Invalid round-two ligand cap")
            if counts[key] > limit:
                raise ValueError(f"Round-two ligand cap exceeded: {key} {counts[key]} > {limit}")
    if round_number == "2" and history:
        validate_design(config, inventory, history)
        if str(history[0]["round"]) != "1":
            raise ValueError("Round-two history must be the complete first round")
        tested = {row["pair_id"] for row in history if row["kind"] == "pair"}
        if tested.intersection(ids):
            raise ValueError("Round two repeats a first-round experimental pair")


def make_design(config, inventory, candidates, ranking, exploration, round_number, history=()):
    design = config["design"]
    n = int(design[f"round{round_number}_total"])
    controls = design.get(f"round{round_number}_controls")
    if controls is None:
        raise ValueError(f"Decide round{round_number}_controls, including singles and repeats, first")
    if not 1 <= n <= len(reaction_wells(config)) or len(controls) >= n:
        raise ValueError("Invalid batch/control count")
    candidate_map = {c["pair_id"]: c for c in candidates}
    order = ranked_ids(ranking, candidates)
    excluded = {r["pair_id"] for r in history if r.get("pair_id") and r.get("kind", "pair") == "pair"}
    count = n - len(controls)
    selected = []
    caps = design.get("round2_ligand_caps", {}) if round_number == 2 else {}
    use = Counter(key for row in controls for key in (row.get("ligand_a"), row.get("ligand_b")) if key)
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
            ligands = (candidate_map[key]["ligand_a"], candidate_map[key]["ligand_b"])
            if any(use[ligand] >= caps[ligand] for ligand in ligands if ligand in caps):
                continue
            selected.append((key, "llm"))
            use.update(ligands)
    if len(selected) != count:
        raise ValueError("Not enough untested pairs within the ligand caps; repeats must be explicit controls")
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
    for i, (row, well) in enumerate(zip(entries, reaction_wells(config)), 1):
        row.update(round=round_number, sample_id=f"R{round_number}-{i:03d}", well=well, lc_well=wells()[i-1])
    validate_design(config, inventory, entries, history)
    return entries
