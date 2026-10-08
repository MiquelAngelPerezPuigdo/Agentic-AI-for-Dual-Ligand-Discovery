"""Offline LC-to-next-batch rehearsal using real embeddings and a mocked SDK client."""
from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from .adapters import load_embeddings
from .demo import fixtures, synthetic_config
from .design import consensus_select, make_design
from .inventory import candidates, load_inventory
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
    inventory = load_inventory(inventory_path, confirmed=True)
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
            for key in payload["candidate_ids"]:
                base = int(hashlib.sha256(key.encode()).hexdigest()[:8], 16) % 101
                means = [sum(by_ligand[x])/len(by_ligand[x]) if x in by_ligand else 50
                         for x in key.split("__")]
                # An arbitrary, labeled emulator demonstrates feedback plumbing.
                # This formula is neither Claude reasoning nor a chemical prediction.
                scores[key] = round(0.25*base+0.75*sum(means)/2, 3) if measured else base
            self.content = [SimpleNamespace(type="text", text=json.dumps({
                "hypothesis": "OFFLINE SYNTHETIC EMULATOR; no chemical prediction or Claude inference.",
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
            calls.append({"candidates": len(payload["candidate_ids"]),
                          "feedback_samples": len(payload["measured_results"]),
                          "includes_reference": any(row["kind"] == "single"
                                                    for row in payload["measured_results"])})
            return Stream(Response(payload))

    with patch.object(anthropic, "Anthropic", OfflineClient), patch.dict(
            os.environ, {"ANTHROPIC_API_KEY": "offline_rehearsal_placeholder"}):
        ranking = score_candidates(scoring_config, inventory, pairs, evidence, [], out/"initial_scoring")
        selected, trace = consensus_select(pairs, ranking, features, 65,
            config["design"]["consensus_weight_llm"], config["design"]["minimum_llm_percentile"])
        design = make_design(config, inventory, pairs, ranking, selected, 1)
        write_csv(out/"round1_design.csv", design)
        write_csv(out/"round1_selection.csv", trace)
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
    no_redose = all(float(row["sm_DCM_ul"]) == 0 for row in next_dosing)
    if len(next_dosing) != 10 or not no_repeats or not no_redose:
        raise ValueError("Rehearsal next batch violated campaign constraints")
    report = {"synthetic_only": True, "paid_api_calls": 0, "physical_execution_allowed": False,
              "prompt_caching_enabled": prompt_cache_settings(scoring_config["llm"])["enabled"],
              "live_cache_hits_verified": False,
              "actual_lm_embeddings": {"pairs": len(features), "dimensions": features.shape[1]},
              "mocked_requests": calls, "round1_pairs": len(tested), "round1_reference_wells": 1,
              "first_round_qc_pass": read_json(iteration/"analysis/qc_report.json")["batch_qc_pass"],
              "feedback_samples": len(results), "remaining_pairs_scored": 465-len(tested),
              "round2_pairs": len(next_dosing), "no_pair_repeats": no_repeats,
              "no_substrate_redose": no_redose, "incomplete_export_ignored": not ignored,
              "duplicate_event_ignored": replay == state and len(calls) == after,
              "next_dosing_csv": str((iteration/"next_dosing.csv").relative_to(out)),
              "cache_summaries": ["initial_scoring/cache_summary.json",
                                  str((iteration/"scoring/cache_summary.json").relative_to(out))],
              "result_interpretation": "Synthetic yields and mocked rankings validate data flow only."}
    write_json(out/"rehearsal_report.json", report)
    return out/"rehearsal_report.json"
