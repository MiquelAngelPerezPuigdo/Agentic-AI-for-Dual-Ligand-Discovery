import copy
import json
from pathlib import Path
from types import SimpleNamespace

import anthropic
import pytest

from hte.inventory import candidates, load_inventory
from hte.io import object_digest, read_json
from hte.scoring import (cost_breakdown, export_prompt_preview, parse_scores,
                         prompt_cache_settings, prompt_context, score_candidates)


ROOT = Path(__file__).resolve().parents[2]


def install_mock(monkeypatch):
    calls, counted, warmed = [], [], {}

    class Response:
        model = "MOCK_ONLY"
        id = "mock_cache_response"
        stop_reason = "end_turn"

        def __init__(self, request, hit):
            schema = request["output_config"]["format"]["schema"]
            self.content = [SimpleNamespace(type="text", text=json.dumps({
                "scores": {key: 42 for key in schema["properties"]["scores"]["required"]}}))]
            self.usage = SimpleNamespace(model_dump=lambda: {
                "input_tokens": 100, "output_tokens": 100,
                "cache_creation_input_tokens": 0 if hit else 2000,
                "cache_read_input_tokens": 2000 if hit else 0,
                "cache_creation": {"ephemeral_5m_input_tokens": 0,
                                   "ephemeral_1h_input_tokens": 0 if hit else 2000}})

        def model_dump(self): return {"synthetic_only": True}

    class Stream:
        def __init__(self, request, key, hit): self.request, self.key, self.hit = request, key, hit
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def get_final_message(self):
            warmed[self.key] = True
            return Response(self.request, self.hit)

    class Client:
        def __init__(self, **kwargs):
            self.models = SimpleNamespace(retrieve=lambda model: None)
            self.messages = self
        def count_tokens(self, **kwargs):
            counted.append(copy.deepcopy(kwargs))
            return SimpleNamespace(input_tokens=1000)
        def stream(self, **kwargs):
            key = object_digest(kwargs["output_config"]["format"]["schema"])
            if key in warmed and not warmed[key]:
                raise AssertionError("Duplicate cold request started before the first response completed")
            hit = warmed.get(key, False)
            warmed[key] = hit
            calls.append(copy.deepcopy(kwargs))
            return Stream(kwargs, key, hit)

    monkeypatch.setattr(anthropic, "Anthropic", Client)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "synthetic_cache_fixture")
    return calls, counted


def inputs():
    config = read_json(ROOT/"hte_inputs/campaign.json")
    config["llm"]["repeats"] = 3
    inventory = load_inventory(ROOT/"hte_inputs/ligands.csv", confirmed=True)
    return config, inventory, candidates(inventory)[:6]


def test_cache_prefix_schema_usage_cost_and_resume(tmp_path, monkeypatch):
    calls, counted = install_mock(monkeypatch)
    config, inventory, pairs = inputs()
    feedback = [{"sample_id": "SYNTHETIC", "yield_percent": 42}]
    score_candidates(config, inventory, pairs, {}, feedback, tmp_path)
    assert len(calls) == len(counted) == 3
    prefix = calls[0]["messages"][0]["content"][:2]
    schema = calls[0]["output_config"]["format"]["schema"]
    orders = []
    for request in calls:
        blocks = request["messages"][0]["content"]
        assert blocks[:2] == prefix
        assert all(b["cache_control"] == {"type": "ephemeral", "ttl": "1h"} for b in blocks[:2])
        assert "cache_control" not in blocks[-1]
        assert json.loads(blocks[1]["text"])["measured_results"] == feedback
        assert request["output_config"]["format"]["schema"] == schema
        orders.append(tuple(json.loads(blocks[-1]["text"])["candidate_ids"]))
    assert len(set(orders)) > 1
    assert all(r["system"] == calls[0]["system"] and r["thinking"] == {"type": "disabled"}
               and r["output_config"]["format"]["schema"] == schema for r in counted)
    summary = read_json(tmp_path/"cache_summary.json")
    assert summary["cache_creation_input_tokens"] == 2000
    assert summary["cache_read_input_tokens"] == 4000 and summary["cache_hit_requests"] == 2
    assert summary["total_cost_usd"] == pytest.approx(0.031)
    saved = read_json(tmp_path/"repeat-00-batch-0000.json")
    assert saved["cost_breakdown"]["cache_write_usd"] == pytest.approx(0.02)
    score_candidates(config, inventory, pairs, {}, feedback, tmp_path)
    assert len(calls) == len(counted) == 3


def test_cached_batches_keep_same_cohort_and_schema_across_repeats(tmp_path, monkeypatch):
    calls, _ = install_mock(monkeypatch)
    config, inventory, pairs = inputs()
    config["llm"]["batch_size"] = 2
    score_candidates(config, inventory, pairs, {}, [], tmp_path)
    schemas = {}
    for request in calls:
        schema = request["output_config"]["format"]["schema"]
        schemas.setdefault(object_digest(schema), []).append(schema)
        batch = json.loads(request["messages"][0]["content"][-1]["text"])["candidate_ids"]
        assert set(batch) == set(schema["properties"]["scores"]["required"])
    assert len(schemas) == 3 and all(len(group) == 3 for group in schemas.values())
    assert read_json(tmp_path/"cache_summary.json")["cache_hit_requests"] == 6


def test_budget_includes_cache_write_premium_before_paid_calls(tmp_path, monkeypatch):
    calls, _ = install_mock(monkeypatch)
    config, inventory, pairs = inputs()
    config["llm"].update(repeats=2, max_output_tokens=100, budget_usd=0.1)
    with pytest.raises(ValueError, match="exceeds budget"):
        score_candidates(config, inventory, pairs, {}, [], tmp_path)
    assert not calls
    assert read_json(tmp_path/"cost_preflight.json")["worst_case_usd"] == pytest.approx(0.13)


def test_cost_counts_mixed_ttl_writes_reads_and_uncached_input_separately():
    config, _, _ = inputs()
    usage = {"input_tokens": 100, "output_tokens": 50, "cache_creation_input_tokens": 1200,
             "cache_read_input_tokens": 2000,
             "cache_creation": {"ephemeral_5m_input_tokens": 400, "ephemeral_1h_input_tokens": 800}}
    result = cost_breakdown(usage, config["llm"], prompt_cache_settings(config["llm"]))
    assert result["total_usd"] == pytest.approx(0.01325)
    assert result["unclassified_cache_write_tokens"] == 0
    usage.pop("cache_creation")
    assert cost_breakdown(usage, config["llm"], prompt_cache_settings(config["llm"]))["cache_write_usd"] == pytest.approx(0.012)


def test_disabled_cache_omits_breakpoints(tmp_path, monkeypatch):
    calls, _ = install_mock(monkeypatch)
    config, inventory, pairs = inputs()
    config["llm"]["workers"] = 1
    config["llm"]["prompt_cache"]["enabled"] = False
    score_candidates(config, inventory, pairs, {}, [], tmp_path)
    assert all("cache_control" not in block for request in calls
               for block in request["messages"][0]["content"])


def test_inventory_ids_structures_and_extracted_si_values_are_explicit():
    config, inventory, pairs = inputs()
    evidence = read_json(ROOT/"hte_inputs/literature.json")
    evidence["additional_literature_narrative"] = "DO_NOT_SEND_LITERATURE_NARRATIVE"
    payload, _ = prompt_context(config, inventory, pairs, evidence, [])
    assert "literature_evidence" not in payload
    assert "DO_NOT_SEND_LITERATURE_NARRATIVE" not in json.dumps(payload)
    assert "thesis_method" not in json.dumps(payload) and "air_precedent" not in json.dumps(payload)
    assert payload["target_conditions"]["substrate"] == "pyridine-2-sulfonyl fluoride / PyFluor"
    assert payload["target_conditions"]["product"] == "2-fluoropyridine"
    assert payload["target_conditions"]["solvent"] == "toluene"
    ligands = {row["ligand_id"]: row for row in payload["ligands"]}
    expected = {"L01":77, "L03":63, "L04":62, "L05":78, "L06":72, "L07":1,
                "L08":0, "L10":0, "L11":61, "L12":0, "L13":0, "L14":3,
                "L17":77, "L21":1, "L22":1, "L23":1, "L24":14, "L25":22}
    assert len(ligands) == 31 and len(evidence["yields"]) == 18
    for key, row in ligands.items():
        assert row["name"] == inventory[key]["name"] and row["smiles"] == inventory[key]["smiles"]
        assert row["same_substrate_table_S2_yield_percent"] == expected.get(key)
    assert ligands["L08"]["same_substrate_table_S2_yield_percent"] == 0
    assert ligands["L09"]["same_substrate_table_S2_yield_percent"] is None
    for row in pairs:
        assert payload["candidate_catalog"][row["pair_id"]] == {
            "ligand_a": row["ligand_a"], "ligand_b": row["ligand_b"]}


def test_prompt_preview_matches_real_sdk_contract_without_using_credentials(tmp_path, monkeypatch):
    calls, counted = install_mock(monkeypatch)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    config, inventory, pairs = inputs()
    evidence = read_json(ROOT/"hte_inputs/literature.json")
    export_prompt_preview(config, inventory, pairs, evidence, [], tmp_path/"preview")
    assert not calls and not counted
    monkeypatch.setenv("ANTHROPIC_API_KEY", "synthetic_cache_fixture")
    score_candidates(config, inventory, pairs, evidence, [], tmp_path/"scoring")
    exported = []
    for index in range(len(calls)):
        filename = f"repeat-{index:02d}-batch-0000.request.json"
        request = read_json(tmp_path/"preview"/filename)
        assert read_json(tmp_path/"scoring"/filename) == request
        exported.append(request)
    assert all(call in exported for call in calls)
    for call in calls:
        assert call["thinking"] == {"type": "disabled"}
        assert set(call["output_config"]) == {"format"}
        assert call["output_config"]["format"]["schema"]["required"] == ["scores"]
        candidates_block = json.loads(call["messages"][0]["content"][-1]["text"])
        assert candidates_block["candidate_count"] == len(pairs)
    assert read_json(tmp_path/"preview/preview_manifest.json")["api_calls"] == 0


def test_strict_output_contract_rejects_unusable_responses():
    invalid = [[], {"scores":{"a":"42"}}, {"scores":{"a":True}},
               {"scores":{"a":None}}, {"hypothesis":"unwanted", "scores":{"a":42}},
               {"scores":[]}, {"scores":{"a":42}, "extra":"field"},
               {"scores":{"a":101}}, {"scores":{"a":-1}},
               {"scores":{"a":float('nan')}}, {"scores":{"a":float('inf')}},
               {"scores":{}}, {"scores":{"a":42,"b":50}}]
    for value in invalid:
        with pytest.raises(ValueError):
            parse_scores(json.dumps(value), ["a"])
    with pytest.raises(ValueError, match="Duplicate"):
        parse_scores('{"scores":{"a":42,"a":50}}', ["a"])
    values, _ = parse_scores('{"scores":{"a":42.5}}', ["a"])
    assert values == {"a":42.5}


def test_identity_mismatch_and_bad_pair_mapping_stop_prompt_construction():
    config, inventory, pairs = inputs()
    evidence = read_json(ROOT/"hte_inputs/literature.json")
    evidence["yields"][0]["ligand_id"] = "L01"
    with pytest.raises(ValueError, match="ID/CAS"):
        prompt_context(config, inventory, pairs, evidence, [])
    bad_pairs = copy.deepcopy(pairs)
    bad_pairs[0]["ligand_a"] = "L31"
    with pytest.raises(ValueError, match="Candidate pair"):
        prompt_context(config, inventory, bad_pairs, {}, [])
