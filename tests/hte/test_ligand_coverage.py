import copy
from pathlib import Path
import sys

import pytest

from hte.adapters import load_embeddings
from hte.cli import main
from hte.demo import synthetic_config
from hte.design import (consensus_select, ligand_coverage, make_design,
                        round1_required_ligands)
from hte.inventory import candidates, load_inventory
from hte.io import read_csv, read_json, write_csv
from hte.planning import dosing_rows


ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def library():
    config = synthetic_config(ROOT/"hte_inputs/campaign.json")
    inventory = load_inventory(ROOT/"hte_inputs/ligands.csv", confirmed=True)
    pairs = candidates(inventory)
    features = load_embeddings(ROOT/"hte_inputs/pair_embeddings_t5-base.npz", inventory, pairs)
    # Adversarial scores: every pair containing L31 is below the ordinary floor.
    ranking = [{"pair_id": row["pair_id"], "mean_score": 0 if "L31" in
                (row["ligand_a"], row["ligand_b"]) else 80, "score_sd": 0, "scoring_calls": 5}
               for row in pairs]
    return config, inventory, pairs, features, ranking


def test_low_scoring_ligand_is_covered_without_extra_wells_or_pair_repeats(library):
    config, inventory, pairs, features, ranking = library
    selected, trace = consensus_select(pairs, ranking, features, 65, required_ligands=inventory)
    design = make_design(config, inventory, pairs, ranking, selected, 1)
    coverage = ligand_coverage(inventory, design)
    assert len(selected) == len(set(selected)) == 65 and len(design) == 66
    assert len(coverage) == 31 and all(row["pair_well_count"] >= 1 for row in coverage)
    assert sum(row["pair_well_count"] for row in coverage) == 130
    overrides = [row for row in trace if row["llm_floor_override"]]
    assert len(overrides) == 1 and "L31" in overrides[0]["new_ligands_covered"].split(";")
    assert overrides[0]["llm_percentile"] < 0.25 and overrides[0]["selection_phase"] == "coverage"
    assert trace[-1]["uncovered_ligands_remaining"] == 0
    assert all(row["consensus_score"] == pytest.approx(
        0.5*row["llm_percentile"]+0.5*row["exploration_percentile"]) for row in trace)
    assert consensus_select(pairs, ranking, features, 65, required_ligands=inventory) == (selected, trace)


def test_tight_complete_library_budget_overrides_star_shaped_llm_preference(library):
    _, inventory, pairs, features, _ = library
    ranking = [{"pair_id": row["pair_id"], "mean_score": 80 if row["ligand_a"] == "L01" else 0,
                "score_sd": 0, "scoring_calls": 5} for row in pairs]
    selected, trace = consensus_select(pairs, ranking, features, 16, minimum_percentile=0.94,
                                      required_ligands=inventory)
    covered = {key for pair in selected for key in pair.split("__")}
    assert covered == set(inventory) and len(set(selected)) == 16
    assert any(row["llm_floor_override"] for row in trace)


@pytest.mark.parametrize("count,required,message", [
    (15, [f"L{i:02d}" for i in range(1, 32)], "Too few pair wells"),
    (65, ["L99"], "no candidate pairs"),
    (0, ["L01"], "Too few pair wells"),
])
def test_impossible_coverage_stops_instead_of_omitting_ligands(library, count, required, message):
    _, _, pairs, features, ranking = library
    with pytest.raises(ValueError, match=message):
        consensus_select(pairs, ranking, features, count, required_ligands=required)


def test_reference_does_not_replace_pair_coverage_and_manual_design_is_rejected(library):
    config, inventory, pairs, _, ranking = library
    missing_l17 = [row["pair_id"] for row in pairs if "L17" not in
                   (row["ligand_a"], row["ligand_b"])][:65]
    with pytest.raises(ValueError, match="omits required ligands:.*L17"):
        make_design(config, inventory, pairs, ranking, missing_l17, 1)
    legacy = copy.deepcopy(config)
    legacy["design"]["require_all_ligands_in_round1_pairs"] = False
    manual_design = make_design(legacy, inventory, pairs, ranking, missing_l17, 1)
    assert any(row["kind"] == "single" and row["ligand_a"] == "L17" for row in manual_design)
    assert next(row for row in ligand_coverage(inventory, manual_design) if row["ligand_id"] == "L17")["pair_well_count"] == 0
    with pytest.raises(ValueError, match="omits required ligands:.*L17"):
        dosing_rows(config, inventory, manual_design)


def test_cli_exports_auditable_coverage_and_override_reports(library, tmp_path, monkeypatch, capsys):
    _, _, _, _, ranking = library
    ranking_path = tmp_path/"SYNTHETIC_ranking.csv"
    write_csv(ranking_path, ranking)
    output = tmp_path/"SYNTHETIC_first_batch.csv"
    monkeypatch.setattr(sys, "argv", ["hte", "--config", str(ROOT/"hte_inputs/campaign.json"),
        "--inventory", str(ROOT/"hte_inputs/ligands.csv"), "design", "--ranking", str(ranking_path),
        "--embeddings", str(ROOT/"hte_inputs/pair_embeddings_t5-base.npz"), "--output", str(output)])
    main()
    coverage = read_csv(str(output)+".ligand_coverage.csv")
    assert len(read_csv(output)) == 66 and len(coverage) == 31
    assert all(int(row["pair_well_count"]) >= 1 for row in coverage)
    metadata = read_json(str(output)+".metadata.json")
    assert metadata["ligands_covered_in_pairs"] == 31 and not metadata["missing_ligands"]
    assert metadata["required_ligand_coverage"] and metadata["coverage_floor_overrides"] == 1
    assert "31/31" in capsys.readouterr().out


def test_coverage_setting_requires_a_boolean(library):
    config, inventory, *_ = library
    bad = copy.deepcopy(config)
    bad["design"]["require_all_ligands_in_round1_pairs"] = "false"
    with pytest.raises(ValueError, match="must be true or false"):
        round1_required_ligands(bad, inventory)
