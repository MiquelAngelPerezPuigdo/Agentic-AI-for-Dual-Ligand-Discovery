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
    monkeypatch.setenv("ANTHROPIC_API_KEY", "synthetic_existing_key")
    report_path = run(tmp_path/"loop", ROOT/"hte_inputs/ligands.csv", ROOT/"hte_inputs/campaign.json",
                      ROOT/"hte_inputs/literature.json", ROOT/"hte_inputs/pair_embeddings_t5-base.npz")
    report = read_json(report_path)
    assert (report_path.parent/"round1_design.csv").read_bytes() == (ROOT/"campaigns/hackathon2026/round1_design.csv").read_bytes()
    assert report["initial_mock_scores_used_for_selection"] is False
    assert report["paid_api_calls"] == 0 and not report["physical_execution_allowed"]
    assert report["prompt_caching_enabled"] and not report["live_cache_hits_verified"]
    assert all((report_path.parent/path).exists() for path in report["cache_summaries"])
    assert report["actual_lm_embeddings"] == {"pairs": 435, "dimensions": 768}
    assert report["round1_ligands_covered_in_pairs"] == 30 and not report["round1_missing_ligands"]
    coverage = read_csv(report_path.parent/"round1_ligand_coverage.csv")
    assert len(coverage) == 30 and all(int(row["pair_well_count"]) >= 1 for row in coverage)
    assert len(report["mocked_requests"]) > 500
    assert all(1 <= r["candidates"] <= 8 for r in report["mocked_requests"])
    initial = [r for r in report["mocked_requests"] if r["feedback_samples"] == 0]
    feedback = [r for r in report["mocked_requests"] if r["feedback_samples"] == 48]
    assert len(initial) == 340 and len(feedback) > 250
    assert sum(r["candidates"] for r in initial)==435*5
    assert sum(r["candidates"] for r in feedback)==387*5
    assert all(not r["includes_reference"] for r in initial+feedback)
    assert report["first_round_qc_pass"] and report["incomplete_export_ignored"]
    assert report["duplicate_event_ignored"] and report["no_pair_repeats"] and report["substrate_dosed_once_per_round"]
    assert report["combined_is_dosed_once_per_round"]
    assert report["analytical_practice_pass"]
    assert (report_path.parent/report["analytical_practice_report"]).exists()
    next_dosing = report_path.parent/report["next_dosing_csv"]
    rows = read_csv(next_dosing)
    assert sum(row["selection_method"] == "llm" for row in rows)==22
    assert sum(row["kind"] == "single" for row in rows)==1
    assert len(rows) == 23 and all(float(r["sm_stock_ul"]) == 25 for r in rows)
    assert all(float(r["internal_standard_predosed_umol"]) == 0 and
               float(r["substrate_predosed_umol"]) == 0 and
               float(r["internal_standard_added_umol"]) == 2.5 for r in rows)
    assert not (next_dosing.parent/"protocols").exists()
    assert os.environ["ANTHROPIC_API_KEY"] == "synthetic_existing_key"
