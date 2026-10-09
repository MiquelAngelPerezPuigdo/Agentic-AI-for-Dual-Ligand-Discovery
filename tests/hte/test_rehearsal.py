import os
from pathlib import Path

import anthropic

from hte.io import read_csv, read_json
from hte.rehearsal import run


ROOT = Path(__file__).resolve().parents[2]


def test_offline_loop_scores_feedback_without_network_or_repeated_events(tmp_path, monkeypatch):
    def reject_online_client(**kwargs):
        raise AssertionError("The offline rehearsal attempted to create an online client")

    monkeypatch.setattr(anthropic, "Anthropic", reject_online_client)
    def reject_gollum_optimizer(*args, **kwargs):
        raise AssertionError("The campaign called a GoLLuM yield optimizer")
    monkeypatch.setattr("hte.adapters.gollum_acquisition", reject_gollum_optimizer)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "synthetic_existing_key")
    report_path = run(tmp_path/"loop", ROOT/"hte_inputs/ligands.csv", ROOT/"hte_inputs/campaign.json",
                      ROOT/"hte_inputs/literature.json", ROOT/"hte_inputs/pair_embeddings_t5-base.npz")
    report = read_json(report_path)
    assert report["paid_api_calls"] == 0 and not report["physical_execution_allowed"]
    assert report["prompt_caching_enabled"] and not report["live_cache_hits_verified"]
    assert all((report_path.parent/path).exists() for path in report["cache_summaries"])
    assert report["actual_lm_embeddings"] == {"pairs": 465, "dimensions": 768}
    assert report["round1_ligands_covered_in_pairs"] == 31 and not report["round1_missing_ligands"]
    coverage = read_csv(report_path.parent/"round1_ligand_coverage.csv")
    assert len(coverage) == 31 and all(int(row["pair_well_count"]) >= 1 for row in coverage)
    assert len(report["mocked_requests"]) == 10
    initial = [r for r in report["mocked_requests"] if r["feedback_samples"] == 0]
    feedback = [r for r in report["mocked_requests"] if r["feedback_samples"] == 66]
    assert len(initial) == len(feedback) == 5
    assert all(r["candidates"] == 465 for r in initial)
    assert all(r["candidates"] == 400 and r["includes_reference"] for r in feedback)
    assert report["first_round_qc_pass"] and report["incomplete_export_ignored"]
    assert report["duplicate_event_ignored"] and report["no_pair_repeats"] and report["no_substrate_redose"]
    assert report["no_internal_standard_redose"]
    next_dosing = report_path.parent/report["next_dosing_csv"]
    rows = read_csv(next_dosing)
    assert all(row["selection_method"] == "llm" for row in rows)
    assert len(rows) == 10 and all(float(r["sm_DCM_ul"]) == 0 for r in rows)
    assert all(float(r["naphthalene_predosed_umol"]) == 0.05 and
               float(r["naphthalene_added_with_substrate_umol"]) == 0 for r in rows)
    assert not (next_dosing.parent/"protocols").exists()
    assert os.environ["ANTHROPIC_API_KEY"] == "synthetic_existing_key"
