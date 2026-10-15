import copy
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from hte.analytics import analyze, fit_calibration, observations, validate_completion
from hte.demo import run
from hte.design import consensus_select, make_design, pair_features
from hte.inventory import candidates, campaign_inventory, load_inventory
from hte.io import object_digest, read_csv, read_json
from hte.planning import dosing_rows, required_validations, schedule, stock_plan, transfer_operations, validate_config
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
    return campaign_inventory(ROOT/"hte_inputs/ligands.csv", read_json(ROOT/"hte_inputs/campaign.json"), confirmed=True)


def test_inventory_corrections_and_unique_pairs(inventory):
    assert "O" in inventory["L11"]["smiles"]
    assert float(inventory["L11"]["molecular_weight_g_mol"]) == pytest.approx(496.759, abs=0.02)
    assert inventory["L27"]["name"] == "tris(3-chlorophenyl)phosphine"
    pairs = candidates(inventory)
    assert len(pairs) == len({c["pair_id"] for c in pairs}) == 435


def test_two_rounds_and_reference_stoichiometry(demo, cfg, inventory):
    first,second=[read_csv(demo/f"round{i}_design.csv") for i in (1,2)]
    assert len(first)==48 and len(second)==23
    assert all(row["kind"]=="pair" for row in first)
    assert sum(row["kind"]=="pair" for row in second)==22
    assert not {r["pair_id"] for r in first}.intersection(r["pair_id"] for r in second)
    for design in (first,second):
        for r in dosing_rows(cfg,inventory,design):
            assert r["substrate_umol"]==25 and r["pd_umol"]==3
            assert r["internal_standard_total_umol"]==r["internal_standard_added_umol"]==2.5
            assert r["internal_standard_predosed_umol"]==r["internal_standard_workup_umol"]==0
            assert r["substrate_solvent_retained_ul"]==0 and r["substrate_solvent_evaporated_ul"]==50
            assert r["internal_standard_final_uM"]==pytest.approx(200/3)
            assert r["ligand_a_umol"]+r["ligand_b_umol"]==3
            assert sum(r[k] for k in ("internal_standard_stock_ul","ligand_a_ul","ligand_b_ul","pd_ul","toluene_ul"))==250
            assert r["workup_ul"]==500 and r["aliquot_ul"]==20 and r["diluent_ul"]==980
    second_rows=dosing_rows(cfg,inventory,second)
    ref=next(r for r in second_rows if r["kind"]=="single")
    assert ref["ligand_a"]=="L17" and ref["ligand_a_ul"]==75 and ref["ligand_b_ul"]==0
    assert all(r["sm_stock_ul"]==0 and r["substrate_predosed_umol"]==25 for r in second_rows)
    manifest=read_csv(demo/"round1/round2_predose.csv")
    assert [r["well"] for r in manifest]==[r["well"] for r in second]
    assert all(float(r["internal_standard_predosed_umol"])==0 and float(r["sm_stock_ul"])==50 for r in manifest)
    deck_stock=next(r for r in read_csv(demo/"round1/deck_loads.csv") if r["reagent"]=="substrate_stock")
    assert float(deck_stock["load_ul"])==3910


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
    assert not predose  # One block: round-two SM is hand-dosed off deck during round one.
    assert sum(op["volume_ul_per_channel"]*op["channels"] for op in ops if op["stage"] == "sampling") == 48*20
    plan = stock_plan(cfg, inventory, ops)
    assert all(r["capacity_ok"] for r in plan)
    assert all(r["prepare_ul"] >= r["protocol_consumption_ul"]+r["round2_reserve_ul"]+r["dead_ul"] for r in plan)
    assert "NO mesitylene" in next(r for r in plan if r["reagent"] == "LC_diluent")["solvent"]
    workup=next(r for r in plan if r["reagent"] == "workup")
    assert workup["stock_mM"] == 0
    assert workup["mass_mg"] == 0
    mixed = next(r for r in plan if r["reagent"] == "substrate_stock")
    assert mixed["prepare_ul"] == 10000
    assert mixed["mass_mg"] == pytest.approx(805.8)
    standard=next(r for r in plan if r["reagent"]=="internal_standard")
    assert standard["stock_mM"]==100 and standard["mass_mg"]==pytest.approx(60.095)
    assert mixed["source_slot"] == 2 and mixed["source_well"] == "A1"
    assert "glass" in mixed["storage_container"]


def test_consensus_all_wells_combine_ranks(demo, inventory):
    pairs = candidates(inventory)
    ranking = read_csv(demo/"SYNTHETIC_ranking.csv")
    selection, trace = consensus_select(pairs, ranking, pair_features(inventory, pairs), 59)
    assert len(set(selection)) == 59
    assert all(r["llm_percentile"] >= 0.25 for r in trace)
    assert all(r["consensus_score"] == pytest.approx((r["llm_percentile"]+r["exploration_percentile"])/2) for r in trace)


def test_timing_calibrations_overlap_and_deadline_warning(cfg):
    timing = schedule(cfg)
    assert timing["lc_minutes"] == pytest.approx(120.7)
    assert timing["reaction_minutes"] == 480
    assert timing["serial_total_minutes"] == pytest.approx(752.7)
    assert timing["planned_total_minutes"] == pytest.approx(717.7)
    assert not timing["fits_serial_estimate"] and timing["fits_planned_estimate"]
    cfg["timing"]["calibration_injections_during_round1_reaction"] = 0
    assert schedule(cfg)["serial_total_minutes"] == pytest.approx(776.5)


def test_real_export_requires_bench_validation(cfg):
    cfg["demo"] = False
    with pytest.raises(ValueError, match="reuse"):
        validate_config(cfg, live=True)
    cfg["pipetting"]["reuse_tips"] = False
    with pytest.raises(ValueError, match="Bench"):
        validate_config(cfg, live=True)


def test_preloaded_is_bench_validation_is_required(cfg):
    cfg["demo"] = False
    cfg["pipetting"]["reuse_tips"] = False
    for key in required_validations(cfg):
        cfg["validation"][key] = key != "pre_reaction_internal_standard_validated"
    with pytest.raises(ValueError, match="pre_reaction_internal_standard_validated"):
        validate_config(cfg, live=True)
    cfg["validation"]["pre_reaction_internal_standard_validated"] = True
    cfg["analytics"].update(method_id="VALIDATED_TEST_METHOD", channel="VALIDATED_TEST_DAD")
    cfg["timing"]["dosing_total_minutes"] = 20  # Within the deadline in this unit-test fixture.
    validate_config(cfg, live=True)


def test_separate_stock_assays_apply_to_each_solute(demo, cfg, inventory):
    cfg["stock_preparation"]["assay_fractions"] = {"substrate_stock": 0.95, "internal_standard": 0.98}
    rows = dosing_rows(cfg, inventory, read_csv(demo/"round1_design.csv"))
    mixed = next(r for r in stock_plan(cfg, inventory, transfer_operations(cfg, inventory, rows))
                 if r["reagent"] == "substrate_stock")
    assert mixed["mass_mg"] == pytest.approx(805.8/0.95)
    standard=next(r for r in stock_plan(cfg,inventory,transfer_operations(cfg,inventory,rows)) if r["reagent"]=="internal_standard")
    assert standard["mass_mg"]==pytest.approx(60.095/0.98)


def test_combined_stock_rejects_duplicate_is_in_workup(cfg):
    cfg["liquids"]["internal_standard_workup_mM"] = 1
    with pytest.raises(ValueError, match="zero workup IS"):
        validate_config(cfg)


def test_greater_sample_dilution_changes_both_analyte_and_is(cfg, demo, inventory):
    cfg["liquids"].update(aliquot_ul=5, diluent_ul=495)
    cfg["robot"]["single"] = "p20_single_gen2"
    with pytest.raises(ValueError, match="final IS concentration"):
        validate_config(cfg)
    cfg["analytics"]["internal_standard_final_uM"] = 100/3
    rows = dosing_rows(cfg, inventory, read_csv(demo/"round1_design.csv"))
    assert all(r["internal_standard_final_uM"] == pytest.approx(100/3) for r in rows)
    ops = transfer_operations(cfg, inventory, rows)
    assert all(op["pipette"] == "p20" for op in ops if op["stage"] == "sampling")
    assert all(op["source_well"] in cfg["stock_preparation"]["reservoir_source_pools"]["LC_diluent"] and op["volume_ul_per_channel"] == 247.5
               for op in ops if op["stage"] == "dilution" and op["pipette"] == "p300")


def test_calibration_checks_are_held_out_of_fit(demo, cfg):
    cal = read_csv(demo/"calibration.csv")
    baseline = fit_calibration(cfg, cal)
    assert all(model["fit_measurements"] == 6 and len(model["independent_checks"]) == 1
               for model in baseline.values())
    check = next(r for r in cal if r["analyte"] == "product" and r["role"] == "check")
    check["area"] = float(check["area"])*1.1
    shifted = fit_calibration(cfg, cal)
    assert shifted["product"]["slope"] == baseline["product"]["slope"]
    assert shifted["product"]["independent_checks"][0]["relative_error"] == pytest.approx(0.1)
    check["area"] = float(check["area"])*2
    with pytest.raises(ValueError, match="Independent calibration check failed"):
        fit_calibration(cfg, cal)


def test_analysis_rejects_dosing_calibration_is_mismatch(demo, cfg, tmp_path):
    doses = read_csv(demo/"round1/dosing.csv")
    doses[0]["internal_standard_final_uM"] = 12.5
    with pytest.raises(ValueError, match="different final IS concentrations"):
        analyze(cfg, doses, read_csv(demo/"round1_peaks.csv"), read_csv(demo/"calibration.csv"), tmp_path)


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
    assert results[0]["yield_upper_bound_percent"] == pytest.approx(1.5)
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
        assert len(feedback) == 48 and all(r["kind"] == "pair" for r in feedback)
        return [{"pair_id": c["pair_id"], "mean_score": i % 100, "score_sd": 1} for i,c in enumerate(pairs)]
    monkeypatch.setattr(workflow, "score_candidates", fake_score)
    args = (cfg, inventory, {}, demo/"round1/dosing.csv", demo/"round1_peaks.csv", demo/"round1_peaks.ready.json", demo/"calibration.csv", tmp_path)
    out = workflow.iterate(*args)
    assert len(read_csv(out/"next_dosing.csv")) == 23
    assert all(float(r["sm_stock_ul"]) == 0 for r in read_csv(out/"next_dosing.csv"))
    assert workflow.iterate(*args) == out and calls == [387]
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
            self.content = [SimpleNamespace(type="text", text=json.dumps({"scores":{key:42 for key in schema["properties"]["scores"]["required"]}}))]
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
            assert kwargs["thinking"] == {"type":"disabled"}
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


@pytest.mark.parametrize('field,value', [
    ('sample_prewet_cycles', -1), ('sample_prewet_cycles', 6),
    ('sample_prewet_cycles', True), ('sample_flow_rate_multiplier', 0),
    ('sample_flow_rate_multiplier', 1.1), ('sample_flow_rate_multiplier', float('nan')),
    ('sample_air_gap_rate', 0), ('sample_air_gap_rate', 1.1),
    ('sample_aspirate_height_mm', 0), ('sample_pause_seconds', -1),
])
def test_invalid_analytical_handling_settings_stop_export(cfg, field, value):
    cfg['pipetting'][field] = value
    with pytest.raises(ValueError):
        validate_config(cfg)


def test_sample_surplus_must_not_exhaust_the_extract(cfg):
    cfg['liquids']['aliquot_ul'] = 750
    with pytest.raises(ValueError, match='exhausts the extract'):
        validate_config(cfg)


@pytest.mark.parametrize('round_name,cycles', [('round1', 2), ('round2', 0)])
def test_sample_conditioning_conserves_volume_and_stays_in_its_own_well(
        demo, cfg, inventory, tmp_path, round_name, cycles):
    import re
    from hte.protocols import export
    from opentrons.simulate import simulate

    cfg['pipetting'].update(sample_prewet_cycles=cycles, sample_aspirate_height_mm=2)
    out = tmp_path/round_name
    export(cfg, inventory, read_csv(demo/(round_name+'_design.csv')), out)
    operations = [r for r in read_json(out/'operations.json') if r['stage'] == 'sampling']
    with (out/'workup.py').open() as handle:
        commands, _ = simulate(handle)
    starts = [i for i, c in enumerate(commands)
              if re.match(r'(reaction_samples|R[12]-\d+):', c['payload'].get('text', ''))]
    assert len(starts) == len(operations)
    for n, op in enumerate(operations):
        end = starts[n+1] if n+1 < len(starts) else len(commands)
        payloads = [c['payload'] for c in commands[starts[n]:end]]
        stop=next(i for i,p in enumerate(payloads) if p.get('text','').startswith('Dropping tip'))
        payloads=payloads[:stop+1]
        liquid = [p for p in payloads if p.get('text', '').startswith('Aspirating')
                  and p['location'].point.z < p['location'].labware.as_well().top().point.z]
        dispenses = [p for p in payloads if p.get('text', '').startswith('Dispensing')]
        assert len(liquid) == cycles+1
        assert len(dispenses) == cycles+1
        source = liquid[0]['location'].labware.as_well()
        assert source.well_name == op['source_well']
        assert all(p['location'].labware.as_well() == source for p in liquid)
        assert all(p['location'].point.z == pytest.approx(source.bottom(2).point.z) for p in liquid)
        returns = dispenses[:-1]
        assert all(p['location'].labware.as_well() == source for p in returns)
        assert all(p['location'].point == source.bottom(2).point for p in returns)
        assert sum(p['volume'] for p in liquid)-sum(p['volume'] for p in returns) == pytest.approx(
            op['volume_ul_per_channel']+cfg['pipetting']['surplus_ul'])
        destination = dispenses[-1]['location'].labware.as_well()
        assert destination.well_name == op['destination_wells'][0]
        assert destination.parent != source.parent
        assert dispenses[-1]['volume']-cfg['pipetting']['air_gap_ul'] == pytest.approx(
            op['volume_ul_per_channel'])
        assert not op['retained_tip_from_previous'] and not op['retain_tip_for_next']
        assert any(p.get('text', '').startswith('Dropping tip') for p in payloads)
        flow = cfg['pipetting'][op['pipette']+'_aspirate_ul_s']*cfg['pipetting']['sample_flow_rate_multiplier']
        assert all(float(re.search(r'at ([\d.]+) uL/sec', p['text'])[1]) == pytest.approx(flow) for p in liquid)
        air = [p for p in payloads if p.get('text', '').startswith('Aspirating') and p not in liquid]
        assert len(air) == 1
        assert float(re.search(r'at ([\d.]+) uL/sec', air[0]['text'])[1]) == pytest.approx(
            flow*cfg['pipetting']['sample_air_gap_rate'])
