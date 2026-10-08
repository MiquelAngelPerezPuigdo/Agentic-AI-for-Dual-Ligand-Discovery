import copy
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from hte.analytics import analyze, observations, validate_completion
from hte.demo import run
from hte.design import consensus_select, make_design, pair_features
from hte.inventory import candidates, load_inventory
from hte.io import object_digest, read_csv, read_json
from hte.planning import dosing_rows, schedule, stock_plan, transfer_operations, validate_config
from hte.scoring import aggregate, parse_scores, score_candidates

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def demo(tmp_path_factory):
    out = tmp_path_factory.mktemp("campaign")/"demo"
    run(out, ROOT/"hte_inputs/ligands.csv")
    return out


@pytest.fixture
def cfg(demo):
    return read_json(demo/"campaign.json")


@pytest.fixture
def inventory():
    return load_inventory(ROOT/"hte_inputs/ligands.csv", confirmed=True)


def test_inventory_corrections_and_unique_pairs(inventory):
    assert "O" in inventory["L11"]["smiles"]
    assert float(inventory["L11"]["molecular_weight_g_mol"]) == pytest.approx(496.759, abs=0.02)
    assert inventory["L27"]["name"] == "tris(3-chlorophenyl)phosphine"
    pairs = candidates(inventory)
    assert len(pairs) == len({c["pair_id"] for c in pairs}) == 465


def test_two_rounds_and_reference_stoichiometry(demo, cfg, inventory):
    first = read_csv(demo/"round1_design.csv")
    second = read_csv(demo/"round2_design.csv")
    rows = dosing_rows(cfg, inventory, first)
    assert len(first) == 66 and len(second) == 10
    assert len({r["pair_id"] for r in first if r["kind"] == "pair"}) == 65
    assert not {r["pair_id"] for r in first}.intersection(r["pair_id"] for r in second)
    for r in rows:
        assert r["substrate_umol"] == 5
        assert r["pd_umol"] == pytest.approx(0.6)
        assert r["ligand_a_umol"]+r["ligand_b_umol"] == pytest.approx(0.6)
        assert r["ligand_a_ul"]+r["ligand_b_ul"]+r["pd_ul"]+r["toluene_ul"] == 50
    ref = next(r for r in rows if r["kind"] == "single")
    assert ref["ligand_a"] == "L17" and ref["ligand_a_ul"] == 20 and ref["ligand_b_ul"] == 0
    second_rows = dosing_rows(cfg, inventory, second)
    assert all(r["sm_DCM_ul"] == 0 and r["substrate_predosed_umol"] == 5 for r in second_rows)
    assert [r["well"] for r in read_csv(demo/"round1/round2_predose.csv")] == [r["well"] for r in second]


@pytest.mark.parametrize("reuse", [True, False])
def test_tip_capacity_source_ledger_and_predose(demo, cfg, inventory, reuse):
    cfg["pipetting"]["reuse_tips"] = reuse
    rows = dosing_rows(cfg, inventory, read_csv(demo/"round1_design.csv"))
    ops = transfer_operations(cfg, inventory, rows)
    p = cfg["pipetting"]
    for op in ops:
        residual = p["surplus_ul"] if op["retained_tip_from_previous"] else 0
        assert op["aspirated_ul_per_channel"]+residual+p["air_gap_ul"] <= (20 if op["pipette"] == "p20" else 300)
        assert op["aspirated_ul_per_channel"]+residual == op["volume_ul_per_channel"]+p["surplus_ul"]
        assert op["source_slot"] != 3 or not op["retain_tip_for_next"]
    predose = [op for op in ops if op["stage"] == "round2_predose"]
    assert sum(op["volume_ul_per_channel"]*op["channels"] for op in predose) == 200
    assert sum(op["volume_ul_per_channel"]*op["channels"] for op in ops if op["stage"] == "sampling") == 66*20
    plan = stock_plan(cfg, inventory, ops)
    assert all(r["capacity_ok"] for r in plan)
    assert all(r["prepare_ul"] >= r["round1_consumption_ul"]+r["round2_reserve_ul"]+r["dead_ul"] for r in plan)
    assert "NO naphthalene" in next(r for r in plan if r["reagent"] == "LC_diluent")["solvent"]
    workup=next(r for r in plan if r["reagent"] == "workup")
    assert workup["stock_mM"] == 1
    assert workup["mass_mg"] == pytest.approx(workup["prepare_ul"]*0.12817/1000)


def test_consensus_all_wells_combine_ranks(demo, inventory):
    pairs = candidates(inventory)
    ranking = read_csv(demo/"SYNTHETIC_ranking.csv")
    selection, trace = consensus_select(pairs, ranking, pair_features(inventory, pairs), 65)
    assert len(set(selection)) == 65
    assert all(r["llm_percentile"] >= 0.25 for r in trace)
    assert all(r["consensus_score"] == pytest.approx((r["llm_percentile"]+r["exploration_percentile"])/2) for r in trace)


def test_timing_calibrations_overlap_and_deadline_warning(cfg):
    timing = schedule(cfg)
    assert timing["lc_minutes"] == 152
    assert timing["reaction_minutes"] == 480
    assert timing["serial_total_minutes"] == 729
    cfg["timing"]["calibration_injections_during_round1_reaction"] = 0
    assert schedule(cfg)["serial_total_minutes"] == 757


def test_real_export_requires_bench_validation(cfg):
    cfg["demo"] = False
    with pytest.raises(ValueError, match="reuse"):
        validate_config(cfg, live=True)
    cfg["pipetting"]["reuse_tips"] = False
    with pytest.raises(ValueError, match="Bench"):
        validate_config(cfg, live=True)


def test_ready_manifest_rejects_mutated_export(demo, cfg, tmp_path):
    peaks = tmp_path/"peaks.csv"
    peaks.write_bytes((demo/"round1_peaks.csv").read_bytes()+b"\n")
    with pytest.raises(ValueError, match="sha256"):
        validate_completion(demo/"round1_peaks.ready.json", peaks, demo/"round1/dosing.csv", cfg)


def test_calibrated_yields_and_censoring(demo, cfg, tmp_path):
    results, report = analyze(cfg, read_csv(demo/"round1/dosing.csv"), read_csv(demo/"round1_peaks.csv"),
                              read_csv(demo/"calibration.csv"), tmp_path)
    assert report["batch_qc_pass"]
    assert results[1]["yield_percent"] == pytest.approx(5)
    assert results[0]["yield_percent"] is None
    assert results[0]["yield_upper_bound_percent"] == pytest.approx(0.2)
    assert results[0]["qc_pass"]


@pytest.mark.parametrize("fault", ["missing_is", "ambiguous_product", "wrong_method", "wrong_channel"])
def test_lc_bad_data_never_silently_yields_zero(demo, cfg, tmp_path, fault):
    dosing = read_csv(demo/"round1/dosing.csv")
    peaks = read_csv(demo/"round1_peaks.csv")
    sample = dosing[1]["sample_id"]
    if fault == "missing_is":
        peaks = [p for p in peaks if not (p["sample_id"] == sample and float(p["retention_time_min"]) == 1.5)]
    elif fault == "ambiguous_product":
        peaks.append(next(p.copy() for p in peaks if p["sample_id"] == sample and float(p["retention_time_min"]) == 0.9))
    else:
        for p in peaks:
            if p["sample_id"] == sample:
                p["method_id" if fault == "wrong_method" else "channel"] = "OTHER"
    if fault == "wrong_method":
        with pytest.raises(ValueError, match="method mismatch"):
            analyze(cfg, dosing, peaks, read_csv(demo/"calibration.csv"), tmp_path)
    else:
        results, report = analyze(cfg, dosing, peaks, read_csv(demo/"calibration.csv"), tmp_path)
        assert not report["batch_qc_pass"]
        assert observations(results)[1]["yield_percent"] is None


@pytest.mark.parametrize("bad", ['{"scores":{"a":1,"a":2}}', '{"scores":{"a":NaN}}', '{"scores":{"b":2}}'])
def test_model_response_validation(bad):
    with pytest.raises(ValueError):
        parse_scores(bad, ["a"])


def test_iterate_is_idempotent_and_does_not_repeat_pairs(demo, cfg, inventory, tmp_path, monkeypatch):
    import hte.workflow as workflow
    cfg["demo"] = False
    calls = []
    def fake_score(config, inv, pairs, evidence, feedback, output):
        calls.append(len(pairs))
        assert len(feedback) == 66 and any(r["kind"] == "single" for r in feedback)
        return [{"pair_id": c["pair_id"], "mean_score": i % 100, "score_sd": 1} for i,c in enumerate(pairs)]
    monkeypatch.setattr(workflow, "score_candidates", fake_score)
    args = (cfg, inventory, {}, demo/"round1/dosing.csv", demo/"round1_peaks.csv", demo/"round1_peaks.ready.json", demo/"calibration.csv", tmp_path)
    out = workflow.iterate(*args)
    assert len(read_csv(out/"next_dosing.csv")) == 10
    assert all(float(r["sm_DCM_ul"]) == 0 for r in read_csv(out/"next_dosing.csv"))
    assert workflow.iterate(*args) == out and calls == [400]
    (out/"next_dosing.csv").write_text("tampered")
    with pytest.raises(ValueError, match="changed"):
        workflow.iterate(*args)


def test_watcher_waits_for_complete_export_and_runs_once(demo, cfg, inventory, tmp_path, monkeypatch):
    import hte.workflow as workflow
    cfg["demo"] = False
    calls=[]
    def fake_score(config, inv, pairs, evidence, feedback, output):
        calls.append(1)
        return [{"pair_id":c["pair_id"],"mean_score":50,"score_sd":1} for c in pairs]
    monkeypatch.setattr(workflow,"score_candidates",fake_score)
    inbox=tmp_path/"inbox"
    inbox.mkdir()
    (inbox/"round1.csv").write_bytes((demo/"round1_peaks.csv").read_bytes())
    args=(cfg, inventory, {}, inbox, demo/"round1/dosing.csv", demo/"calibration.csv", tmp_path/"out")
    assert workflow.watch(*args,once=True) == {} and not calls
    (inbox/"round1.ready.json").write_bytes((demo/"round1_peaks.ready.json").read_bytes())
    first=workflow.watch(*args,once=True)
    assert len(first)==1 and calls==[1]
    assert workflow.watch(*args,once=True)==first and calls==[1]


def test_both_analytes_nondetected_still_requires_valid_is(demo, cfg, tmp_path):
    dosing=read_csv(demo/"round1/dosing.csv")
    target=dosing[1]["sample_id"]
    peaks=[p for p in read_csv(demo/"round1_peaks.csv") if p["sample_id"]!=target or float(p["retention_time_min"])==1.5]
    for p in peaks:
        if p["sample_id"]==target: p["area"]=10000000
    results,report=analyze(cfg,dosing,peaks,read_csv(demo/"calibration.csv"),tmp_path)
    assert not report["batch_qc_pass"] and not results[1]["qc_pass"]
    assert "internal_standard_area_outlier" in results[1]["qc_flags"]


@pytest.mark.parametrize("round_name,stage", [("round1","dose_and_react"),("round1","workup"),("round2","dose_and_react"),("round2","workup")])
def test_opentrons_real_simulator(demo, round_name, stage):
    from opentrons.simulate import simulate
    with (demo/round_name/(stage+".py")).open() as stream:
        commands, _ = simulate(stream)
    assert len(commands) > 20
    liquid_aspirates = [c["payload"]["location"] for c in commands if c["payload"].get("text", "").startswith("Aspirating")]
    assert liquid_aspirates
    assert all(location.point.z > location.labware.as_well().bottom().point.z for location in liquid_aspirates)


def test_fresh_tip_mode_and_tip_replacement_simulate(demo, cfg, inventory, tmp_path):
    from hte.protocols import export
    from opentrons.simulate import simulate
    cfg["pipetting"]["reuse_tips"] = False
    export(cfg,inventory,read_csv(demo/"round1_design.csv"),tmp_path/"fresh")
    with (tmp_path/"fresh/dose_and_react.py").open() as handle:
        commands,_=simulate(handle)
    assert any("Replace ALL empty tip racks" in c["payload"].get("text", "") for c in commands)


def test_paid_call_schema_resume_and_cap(cfg, inventory, tmp_path, monkeypatch):
    import anthropic
    calls = []
    class Response:
        model = "claude-opus-4-8"
        id = "synthetic_response"
        stop_reason = "end_turn"
        usage = SimpleNamespace(model_dump=lambda: {"input_tokens": 1000,"output_tokens":100})
        def __init__(self, schema):
            self.content = [SimpleNamespace(type="text", text=json.dumps({"hypothesis":"fixture", "scores":{key:42 for key in schema["properties"]["scores"]["required"]}}))]
        def model_dump(self):
            return {"id":self.id,"synthetic":True}
    class Stream:
        def __init__(self, response): self.response=response
        def __enter__(self): return self
        def __exit__(self,*args): pass
        def get_final_message(self): return self.response
    class Client:
        def __init__(self, **kwargs):
            self.models=SimpleNamespace(retrieve=lambda model: None)
            self.messages=self
        def count_tokens(self, **kwargs): return SimpleNamespace(input_tokens=1000)
        def stream(self, **kwargs):
            assert kwargs["thinking"] == {"type":"adaptive"}
            calls.append(kwargs)
            return Stream(Response(kwargs["output_config"]["format"]["schema"]))
    monkeypatch.setattr(anthropic,"Anthropic",Client)
    monkeypatch.setenv("ANTHROPIC_API_KEY","synthetic_fixture_only")
    cfg["demo"]=False
    cfg["llm"]["repeats"]=2
    pairs=candidates(inventory)[:3]
    ranked=score_candidates(cfg,inventory,pairs,{},[],tmp_path/"score")
    assert len(ranked)==3 and len(calls)==2
    score_candidates(cfg,inventory,pairs,{},[],tmp_path/"score")
    assert len(calls)==2
    cfg["llm"]["budget_usd"]=0.01
    with pytest.raises(ValueError,match="exceeds budget"):
        score_candidates(cfg,inventory,pairs,{},[],tmp_path/"capped")
    assert len(calls)==2
