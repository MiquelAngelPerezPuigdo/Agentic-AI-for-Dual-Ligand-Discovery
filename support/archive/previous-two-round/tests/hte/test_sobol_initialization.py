"""Production initialization must reproduce David's saved notebook proposal."""
import copy
from pathlib import Path
import sys

import numpy as np
import pytest

from hte.cli import main
from hte.embeddings import load_embeddings
from hte.initialization import initial_select
from hte.inventory import campaign_inventory, candidates
from hte.io import digest, read_csv, read_json


ROOT = Path(__file__).resolve().parents[2]
# Independently recorded from cell 30 output at David's commit c2682f3.
NOTEBOOK_PAIR_IDS = """
L16__L20 L22__L29 L04__L18 L27__L28 L05__L17 L10__L19
L09__L30 L03__L06 L01__L25 L13__L21 L23__L31 L08__L11
L26__L28 L15__L20 L02__L05 L14__L17 L04__L24 L12__L18
L16__L18 L26__L29 L16__L17 L19__L28 L18__L25 L15__L17
L06__L30 L18__L27 L01__L29 L05__L20 L15__L31 L05__L23
L20__L28 L15__L19 L15__L27 L04__L25 L02__L27 L09__L28
L08__L18 L16__L28 L12__L27 L02__L24 L01__L14 L05__L25
L05__L14 L18__L28 L16__L26 L03__L19 L22__L28 L17__L27
""".split()


@pytest.fixture(scope="module")
def inputs():
    config = read_json(ROOT/"hte_inputs/campaign.json")
    inventory = campaign_inventory(ROOT/"hte_inputs/ligands.csv", config)
    pairs = candidates(inventory)
    ranking = read_csv(ROOT/"campaigns/hackathon2026/scoring/ranking.csv")
    features = load_embeddings(ROOT/"hte_inputs/pair_embeddings_t5-base.npz", inventory, pairs)
    return config, inventory, pairs, ranking, features


def test_exact_notebook_reproduction_coverage_and_floor_audit(inputs):
    selected, trace, metadata = initial_select(*inputs)
    assert selected == NOTEBOOK_PAIR_IDS
    assert len(set(selected)) == 48
    inventory = inputs[1]
    covered = {ligand for key in selected[:24] for ligand in key.split("__")}
    assert covered == set(inventory)
    assert [row["selection_source"] for row in trace] == ["repo_consensus"]*24+["sobol"]*24
    assert sum(row["llm_floor_override"] for row in trace) == 0
    assert sum(row["sampling_below_llm_floor"] for row in trace) == 3
    assert all(row["selection_source"] == "sobol" for row in trace if row["below_llm_floor"])
    assert sorted(row["sobol_target_index"] for row in trace[24:]) == list(range(24))
    assert metadata["pca_variance_retained"] == pytest.approx(0.8944359920573077)
    assert metadata["sobol"]["draw_count"] == 32
    assert metadata["sobol"]["retained_target_count"] == 24
    assert metadata["paid_api_calls"] == metadata["model_inference_calls"] == 0
    assert metadata["retained_consensus_pair_ids"] == selected[:24]
    assert all(not row["sampling_below_llm_floor"] for row in trace[:24])


@pytest.mark.parametrize("key,value,message", [
    ("initialization_method", "consensus", "initialization_method"),
    ("exploration_backend", "lm_diversity_initialization", "embedding backend"),
    ("require_lm_embeddings", False, "embedding backend"),
    ("require_all_ligands_in_round1_pairs", "true", "Boolean"),
    ("initialization_keep_from_consensus", 49, "pair count"),
    ("initialization_keep_from_consensus", True, "pair count"),
    ("initialization_seed", -1, "initialization_seed"),
    ("initialization_seed", True, "initialization_seed"),
    ("initialization_pca_dimensions", 0, "PCA dimensions"),
    ("initialization_pca_dimensions", 435, "PCA dimensions"),
    ("initialization_pca_dimensions", 16.0, "PCA dimensions"),
    ("round1_total", 48.0, "integer round1_total"),
    ("round1_controls", None, "round1_controls"),
    ("consensus_weight_llm", float("nan"), "finite"),
    ("minimum_llm_percentile", True, "Boolean"),
])
def test_invalid_initializer_settings_stop(inputs, key, value, message):
    config, *rest = inputs
    bad = copy.deepcopy(config)
    bad["design"][key] = value
    with pytest.raises(ValueError, match=message):
        initial_select(bad, *rest)


@pytest.mark.parametrize("invalid", ["missing_row", "nonfinite", "identical"])
def test_invalid_embedding_inputs_stop(inputs, invalid):
    *first, features = inputs
    features = features.copy()
    if invalid == "missing_row":
        features = features[:-1]
    elif invalid == "nonfinite":
        features[0, 0] = np.nan
    else:
        features[:] = 1
    with pytest.raises(ValueError, match="Features|identical"):
        initial_select(*first, features)


def test_duplicate_candidates_rejected(inputs):
    config, inventory, pairs, ranking, features = inputs
    broken = [*pairs[:-1], pairs[0]]
    with pytest.raises(ValueError, match="Duplicate candidate"):
        initial_select(config, inventory, broken, ranking, features)


def test_cli_exports_sources_provenance_and_preserves_existing_outputs(tmp_path, monkeypatch):
    output = tmp_path/"round1.csv"
    argv = ["hte", "--config", str(ROOT/"hte_inputs/campaign.json"),
            "--inventory", str(ROOT/"hte_inputs/ligands.csv"), "design",
            "--ranking", str(ROOT/"campaigns/hackathon2026/scoring/ranking.csv"),
            "--embeddings", str(ROOT/"hte_inputs/pair_embeddings_t5-base.npz"),
            "--output", str(output)]
    monkeypatch.setattr(sys, "argv", argv)
    main()
    rows = read_csv(output)
    assert {row["pair_id"] for row in rows} == set(NOTEBOOK_PAIR_IDS)
    assert sum(row["selection_method"] == "initial_repo_consensus" for row in rows) == 24
    assert sum(row["selection_method"] == "initial_sobol" for row in rows) == 24
    metadata = read_json(str(output)+".metadata.json")
    assert metadata["required_ligand_coverage"]
    assert metadata["ligands_covered_in_pairs"] == 30
    assert metadata["coverage_floor_overrides"] == 0
    assert metadata["sampling_below_llm_floor_count"] == 3
    assert metadata["source_files"]["embeddings"]["sha256"] == digest(ROOT/"hte_inputs/pair_embeddings_t5-base.npz")
    files = {path.name: path.read_bytes() for path in tmp_path.iterdir()}
    with pytest.raises(SystemExit) as stopped:
        main()
    assert stopped.value.code == 2
    assert files == {path.name: path.read_bytes() for path in tmp_path.iterdir()}


def test_cli_refuses_orphan_audit_file_before_loading_embeddings(tmp_path, monkeypatch):
    output = tmp_path/"round1.csv"
    audit = Path(str(output)+".metadata.json")
    audit.write_text("preserve the old audit")
    monkeypatch.setattr(sys, "argv", ["hte", "--config", str(ROOT/"hte_inputs/campaign.json"),
        "--inventory", str(ROOT/"hte_inputs/ligands.csv"), "design", "--ranking", "missing.csv",
        "--embeddings", "missing.npz", "--output", str(output)])
    with pytest.raises(SystemExit):
        main()
    assert audit.read_text() == "preserve the old audit"
    assert not output.exists()
