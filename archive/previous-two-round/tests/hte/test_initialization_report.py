"""The published initialization report must describe the actual selected batch."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("initialization_report", ROOT / "scripts/initialization-report.py")
report = importlib.util.module_from_spec(spec)
spec.loader.exec_module(report)


def test_pair_statistics_separate_donor_counts_and_sampling_floor():
    inventory = {"L01": {"phosphorus_atoms": "1"}, "L02": {"phosphorus_atoms": "2"},
                 "L03": {"phosphorus_atoms": "2"}}
    ids = ["L01__L02", "L01__L03", "L02__L03"]
    ranking = [{"pair_id": key, "mean_score": 50+i, "score_sd": 1} for i, key in enumerate(ids)]
    trace = [
        {"selection_step": 1, "uncovered_ligands_remaining": 1, "selection_source": "repo_consensus"},
        {"selection_step": 2, "uncovered_ligands_remaining": 0, "selection_source": "sobol",
         "sampling_below_llm_floor": True}]
    s = report.statistics([ids[0], ids[2]], ids, inventory, ranking,
                          np.array([[0, 1, 2], [1, 0, 1], [2, 1, 0]], dtype=float), trace, set())
    assert s["phosphorus_donor_pair_types"] == {"1P+2P": 1, "2P+2P": 1}
    assert s["selection_source_counts"] == {"repo_consensus": 1, "sobol": 1}
    assert s["sampling_below_llm_floor"] == 1
    assert s["coverage_floor_overrides"] == 0
    assert s["coverage_completed_at_step"] == 2


def test_published_report_reproduces_official_hybrid_and_labels_previews():
    args = SimpleNamespace(
        config=ROOT / "hte_inputs/campaign.json", inventory=ROOT / "hte_inputs/ligands.csv",
        evidence=ROOT / "hte_inputs/literature.json",
        design=ROOT / "campaigns/hackathon2026/round1_design.csv",
        ranking=ROOT / "campaigns/hackathon2026/scoring/ranking.csv",
        embeddings=ROOT / "hte_inputs/pair_embeddings_t5-base.npz")
    data, inventory, design, _, _, _, _, methods = report.prepare(args)
    official = methods[0]["statistics"]
    assert set(methods[0]["selected"]) == {row["pair_id"] for row in design}
    assert official["selection_source_counts"] == {"repo_consensus": 24, "sobol": 24}
    assert official["ligands_covered"] == 30
    assert official["sampling_below_llm_floor"] == 3
    assert sum(official["phosphorus_donor_pair_types"].values()) == 48
    assert all(method["statistics"]["ligands_covered"] == 30 for method in methods[:-1])
    assert [method["baseline_llm_weight"] for method in methods[2:4]] == [0.25, 0.75]
    markdown = report.markdown_report(data, inventory, methods)
    assert "24 retained consensus choices + 24 Sobol exploration choices" in markdown
    assert "Claude-only R2" in markdown
    assert "baseline 25% Claude weight" in markdown
    assert f"Uses per ligand | {official['min_uses']}–{official['max_uses']}" in markdown
    assert "no pair-yield model or Gaussian process is fitted" in markdown
