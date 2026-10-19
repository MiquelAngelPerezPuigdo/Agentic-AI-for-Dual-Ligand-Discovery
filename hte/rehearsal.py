"""Offline LC-to-next-batch rehearsal using real embeddings and a mocked SDK client."""
from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from .embeddings import load_embeddings
from .demo import fixtures, synthetic_config
from .design import ligand_coverage
from .inventory import candidates, campaign_inventory
from .io import new_output, read_csv, read_json, write_csv, write_json
from .protocols import export
from .scoring import prompt_cache_settings, score_candidates
from .workflow import watch


def run(output, inventory_path, config_path, evidence_path, embeddings_path):
    import anthropic

    out = new_output(output)
    config = synthetic_config(config_path)
    config["design"].update(require_lm_embeddings=True,
                            exploration_backend="lm_diversity_initialization")
    # The actual workflow rejects demo configs. Only the isolated, mocked SDK context
    # receives a non-demo copy; all physical validation remains false.
    scoring_config = copy.deepcopy(config)
    scoring_config["demo"] = False
    scoring_config["validation"] = {key: False for key in config["validation"]}
    inventory = campaign_inventory(inventory_path, config, confirmed=True)
    pairs = candidates(inventory)
    features = load_embeddings(embeddings_path, inventory, pairs)
    evidence = read_json(evidence_path)
    calls = []
    write_json(out/"SYNTHETIC_ONLY.json", {"synthetic_only": True, "paid_api_calls": 0,
               "mocked_claude": True, "physical_execution_allowed": False})
    write_json(out/"campaign.json", config)

    class Response:
        model = "OFFLINE_MOCK_CLAUDE"
        id = "offline_synthetic_response"
        stop_reason = "end_turn"
        usage = SimpleNamespace(model_dump=lambda: {"input_tokens": 0, "output_tokens": 0})

        def __init__(self, payload):
            measured = payload["measured_results"]
            by_ligand = {}
            for row in measured:
                if row["qc_pass"] not in (True, "True") or row["yield_percent"] in (None, ""):
                    continue
                for ligand in (row["ligand_a"], row["ligand_b"]):
                    if ligand:
                        by_ligand.setdefault(ligand, []).append(float(row["yield_percent"]))
            scores = {}
            for partner in payload["partner_ligand_ids"]:
                key=payload["anchor_ligand_id"]+"__"+partner
                base = int(hashlib.sha256(key.encode()).hexdigest()[:8], 16) % 101
                means = [sum(by_ligand[x])/len(by_ligand[x]) if x in by_ligand else 50
                         for x in key.split("__")]
                # An arbitrary, labeled emulator demonstrates feedback plumbing.
                # This formula is neither Claude reasoning nor a chemical prediction.
                scores[partner] = round(0.25*base+0.75*sum(means)/2, 3) if measured else base
            self.content = [SimpleNamespace(type="text", text=json.dumps({
                "scores": scores}))]

        def model_dump(self):
            return {"id": self.id, "model": self.model, "synthetic_only": True,
                    "content": [{"type": "text", "text": self.content[0].text}]}

    class Stream:
        def __init__(self, response): self.response = response
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def get_final_message(self): return self.response

    class OfflineClient:
        def __init__(self, **kwargs):
            self.models = SimpleNamespace(retrieve=lambda model: None)
            self.messages = self

        def count_tokens(self, **kwargs):
            return SimpleNamespace(input_tokens=1000)

        def stream(self, **kwargs):
            payload = {}
            for block in kwargs["messages"][0]["content"]:
                payload.update(json.loads(block["text"]))
            calls.append({"candidates": len(payload["partner_ligand_ids"]),
                          "feedback_samples": len(payload["measured_results"]),
                          "single_ligand_yields": sum(row["same_substrate_table_S2_yield_percent"] is not None for row in payload["ligands"]),
                          "includes_reference": any(row["kind"] == "single"
                                                    for row in payload["measured_results"])})
            return Stream(Response(payload))

    with patch.object(anthropic, "Anthropic", OfflineClient), patch.dict(
            os.environ, {"ANTHROPIC_API_KEY": "offline_rehearsal_placeholder"}):
        score_candidates(scoring_config, inventory, pairs, evidence, [], out/"initial_scoring")
        # The hackathon's first batch is already frozen and budgeted. Exercise the
        # initial provider contract above, then rehearse feedback on that actual
        # design rather than inventing a different material demand from mock scores.
        frozen = Path(__file__).resolve().parents[1]/"campaigns/hackathon2026/round1_design.csv"
        design = read_csv(frozen)
        trace = read_csv(str(frozen)+".selection.csv")
        write_csv(out/"round1_design.csv", design)
        write_csv(out/"round1_selection.csv", trace)
        coverage = ligand_coverage(inventory, design)
        write_csv(out/"round1_ligand_coverage.csv", coverage)
        from .preparation import export_stock_preparation
        prep=export_stock_preparation(config,inventory,design,out/"stock-preparation")
        config["automation"]["preparation_manifest_path"]=str(prep/"preparation_manifest.json")
        write_json(out/"campaign.json",config)
        dosing = export(config, inventory, design, out/"round1")
        calibration, peaks = fixtures(config, dosing)
        write_csv(out/"calibration.csv", calibration)
        inbox = out/"inbox"
        write_csv(inbox/"round1.csv", peaks)
        args = (scoring_config, inventory, evidence, inbox, out/"round1/dosing.csv",
                out/"calibration.csv", out/"feedback_loop")
        before = len(calls)
        ignored = watch(*args, once=True)
        if ignored or len(calls) != before:
            raise ValueError("Rehearsal failed: incomplete export triggered scoring")
        from .analytics import complete_export
        complete_export(config, inbox/"round1.csv", out/"round1/dosing.csv", inbox/"round1.ready.json")
        state = watch(*args, once=True)
        if len(state) != 1 or next(iter(state.values()))["status"] != "complete":
            raise ValueError("Rehearsal feedback event did not complete")
        # The watcher records the path supplied to it; use that value directly.
        iteration = Path(next(iter(state.values()))["output"])
        after = len(calls)
        replay = watch(*args, once=True)
        if replay != state or len(calls) != after:
            raise ValueError("Rehearsal failed: duplicate event repeated scoring")

    next_dosing = read_csv(iteration/"next_dosing.csv")
    results = read_csv(iteration/"analysis/results.csv")
    tested = {row["pair_id"] for row in design if row["kind"] == "pair"}
    no_repeats = not tested.intersection(row["pair_id"] for row in next_dosing)
    sm_once = all(float(row["sm_stock_ul"]) == 25 and float(row["substrate_predosed_umol"]) == 0
                  for row in [*dosing, *next_dosing])
    correct_is = all(float(row["internal_standard_added_umol"]) == float(row["internal_standard_total_umol"]) == 2.5 and
                     float(row["internal_standard_workup_umol"]) == 0 and
                     float(row["internal_standard_predosed_umol"]) == 0
                     for row in [*dosing, *next_dosing])
    if len(next_dosing) != config["design"]["round2_total"] or not no_repeats or not sm_once or not correct_is:
        raise ValueError("Rehearsal next batch violated campaign dose constraints")
    export(config,inventory,next_dosing,out/"round2",history=dosing)
    from .analytics import analyze
    _,second_peaks=fixtures(config,next_dosing)
    write_csv(out/"round2_peaks.csv",second_peaks)
    _,second_report=analyze(config,next_dosing,second_peaks,calibration,out/"analysis2")
    from .analytical_practice import run as practice_analytics
    analytical_report=practice_analytics(out/"analytical_practice",config_path)
    report = {"synthetic_only": True, "paid_api_calls": 0, "physical_execution_allowed": False,
              "robot_stock_preparation":True,"robot_calibration_preparation":True,"robot_workup_fluid_preparation":True,
              "robot_R2_refill":(out/"round2/refill_stocks.py").exists(),
              "stock_concentration_basis":"nominal_solvent_addition",
              "prompt_caching_enabled": prompt_cache_settings(scoring_config["llm"])["enabled"],
              "live_cache_hits_verified": False,
              "actual_lm_embeddings": {"pairs": len(features), "dimensions": features.shape[1]},
              "mocked_requests": calls, "round1_pairs": len(tested), "round1_reference_wells": 0,
              "round1_ligands_covered_in_pairs": sum(row["covered"] for row in coverage),
              "round1_missing_ligands": [row["ligand_id"] for row in coverage if not row["covered"]],
              "coverage_floor_overrides": sum(row["llm_floor_override"] in (True,"True") for row in trace),
              "first_batch_source":"frozen real 48-pair campaign; yields and all provider responses remain synthetic",
              "initial_mock_scores_used_for_selection":False,
              "first_round_qc_pass": read_json(iteration/"analysis/qc_report.json")["batch_qc_pass"],
              "feedback_samples": len(results), "remaining_pairs_scored": len(pairs)-len(tested),
              "round2_pairs":sum(row["kind"]=="pair" for row in next_dosing), "round2_reference_wells":1,
              "second_round_qc_pass":second_report["batch_qc_pass"], "no_pair_repeats": no_repeats,
              "analytical_practice_pass":read_json(analytical_report)["all_expected_outcomes_passed"],
              "analytical_practice_report":str(analytical_report.relative_to(out)),
              "substrate_dosed_once_per_round": sm_once, "combined_is_dosed_once_per_round": correct_is,
              "incomplete_export_ignored": not ignored,
              "duplicate_event_ignored": replay == state and len(calls) == after,
              "next_dosing_csv": str((iteration/"next_dosing.csv").relative_to(out)),
              "cache_summaries": ["initial_scoring/cache_summary.json",
                                  str((iteration/"scoring/cache_summary.json").relative_to(out))],
              "result_interpretation": "Synthetic yields and mocked rankings validate data flow only."}
    write_json(out/"rehearsal_report.json", report)
    return out/"rehearsal_report.json"
