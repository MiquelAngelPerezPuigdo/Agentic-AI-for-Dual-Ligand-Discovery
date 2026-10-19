"""HTEL export/schema and revised campaign regressions. All values are synthetic."""
import copy
from pathlib import Path

import pytest
from opentrons_shared_data.labware import load_definition

from hte.analytics import calibration_from_peaks, normalize_export
from hte.demo import fixtures, run, synthetic_config
from hte.design import validate_design
from hte.inventory import candidates, campaign_inventory, load_inventory
from hte.io import read_csv, read_json, write_csv
from hte.planning import required_validations, schedule_scenarios, validate_config
from hte.protocols import export, validate_definition_geometry
from hte.scoring import prompt_context

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize("single", ["p20_single_gen2", "p300_single_gen2"])
def test_toluene_and_combined_is_are_retained_in_both_rounds(tmp_path, single):
    from hte.planning import dosing_rows, transfer_operations
    from opentrons.simulate import simulate
    run(tmp_path/"demo",ROOT/"hte_inputs/ligands.csv",ROOT/"hte_inputs/campaign.json")
    config = read_json(tmp_path/"demo/campaign.json")
    config["robot"]["single"] = single
    inv = campaign_inventory(ROOT/"hte_inputs/ligands.csv",config)
    for round_number in (1,2):
        design = read_csv(tmp_path/f"demo/round{round_number}_design.csv")
        rows = dosing_rows(config,inv,design)
        for row in rows:
            assert row["sm_stock_ul"] == 25 and row["substrate_predosed_ul"] == 0
            assert row["internal_standard_added_umol"] == 2.5 and row["internal_standard_predosed_umol"] == 0
            assert 25+sum(row[key] for key in ("internal_standard_stock_ul","ligand_a_ul","ligand_b_ul","pd_ul","toluene_ul")) == 250
            assert row["toluene_ul"] == row["internal_standard_stock_ul"] == 0 and row["pd_ul"] == 75
        ops = transfer_operations(config,inv,rows)
        if "p300" in single:
            assert all(op["volume_ul_per_channel"] >= 20 for op in ops)
        out = tmp_path/f"r{round_number}"
        export(config,inv,design,out)
        with (out/"dose_and_react.py").open() as handle:
            commands,_ = simulate(handle)
        heating = [c["payload"].get("text", "") for c in commands
                   if "Setting Target Temperature of Heater-Shaker" in c["payload"].get("text", "")]
        assert len(heating) == 1 and "95" in heating[0]
        assert not (out/"round2_predose.csv").exists()


def test_dilute_catalysts_cannot_overfill_the_reaction(tmp_path):
    from hte.planning import dosing_rows
    run(tmp_path/"demo",ROOT/"hte_inputs/ligands.csv",ROOT/"hte_inputs/campaign.json")
    config = read_json(tmp_path/"demo/campaign.json")
    config["liquids"].update(ligand_stock_mM=18,pd_stock_mM=36)
    inv = campaign_inventory(ROOT/"hte_inputs/ligands.csv",config)
    for round_number in (1,2):
        with pytest.raises(ValueError,match="too dilute"):
            dosing_rows(config,inv,read_csv(tmp_path/f"demo/round{round_number}_design.csv"))


def test_exclusion_preserves_master_ids_and_removes_candidates_and_si_context():
    config = read_json(ROOT/"hte_inputs/campaign.json")
    master = load_inventory(ROOT/"hte_inputs/ligands.csv")
    inv = campaign_inventory(ROOT/"hte_inputs/ligands.csv", config, confirmed=True)
    assert len(master) == 31 and master["L07"]["cas"] == "224311-55-1"
    assert len(inv) == 30 and "L07" not in inv and inv["L08"] == master["L08"]
    pairs = candidates(inv)
    assert len(pairs) == 435 and all("L07" not in row["pair_id"] for row in pairs)
    payload, _ = prompt_context(config, inv, pairs, read_json(ROOT/"hte_inputs/literature.json"), [])
    assert len(payload["ligands"]) == 30
    assert sum(row["same_substrate_table_S2_yield_percent"] is not None for row in payload["ligands"]) == 17
    with pytest.raises(ValueError, match="excluded"):
        validate_design(config, master, [{"ligand_a": "L07", "ligand_b": "L01"}])


@pytest.mark.parametrize("fault", ["wrong_cas", "unknown_id", "duplicate", "reference"])
def test_invalid_availability_exclusions_fail(fault):
    config = read_json(ROOT/"hte_inputs/campaign.json")
    entry = config["design"]["excluded_ligands"][0]
    if fault == "wrong_cas": entry["cas"] = "224311-49-3"
    elif fault == "unknown_id": entry["ligand_id"] = "L99"
    elif fault == "duplicate": config["design"]["excluded_ligands"].append(copy.deepcopy(entry))
    else: config["design"]["round2_controls"][0]["ligand_a"] = "L07"
    with pytest.raises(ValueError):
        campaign_inventory(ROOT/"hte_inputs/ligands.csv", config)


def test_lc_scenarios_include_short_method_and_fail_longer_serial_plan():
    config = read_json(ROOT/"hte_inputs/campaign.json")
    rows = schedule_scenarios(config)
    # 480 min reaction +264 min handling allowances +71 full sample cycles.
    assert [row["serial_total_minutes"] for row in rows] == pytest.approx([864.7,886,957,1099,1170])
    assert [row["fits_serial_estimate"] for row in rows] == [False, False, False, False, False]
    assert not config["validation"]["injection_cycle_validated"]


@pytest.mark.parametrize("parameter", ["aspirate_height_mm", "sample_aspirate_height_mm"])
def test_htel_requires_more_than_one_mm_clearance(parameter):
    config = read_json(ROOT/"hte_inputs/campaign.json")
    config["pipetting"][parameter] = 1
    with pytest.raises(ValueError, match="greater than 1 mm"):
        validate_config(config)


@pytest.mark.parametrize("fault", ["24_positions", "pitch", "capacity"])
def test_incompatible_labware_definition_fails_before_export(fault):
    config = synthetic_config(ROOT/"hte_inputs/campaign.json")
    definition = copy.deepcopy(load_definition("nest_96_wellplate_2ml_deep", 1))
    from hte.io import reaction_wells,wells
    rows=[{"well":w,"lc_well":wells()[i]} for i,w in enumerate(reaction_wells(config))]
    if fault=="pitch": config["robot"]["reaction_multichannel"]=True
    if fault == "24_positions": definition["wells"] = {k:v for k,v in definition["wells"].items() if k[0] in "ABCD" and int(k[1:]) <= 6}
    elif fault == "pitch": definition["wells"]["B1"]["y"] -= 9
    else: definition["wells"]["A1"]["totalLiquidVolume"] = 50
    with pytest.raises(ValueError, match="well addresses|geometry|capacity"):
        validate_definition_geometry(config, {"lc" if fault=="pitch" else "reaction":definition}, rows)


@pytest.fixture
def vendor_export(tmp_path):
    config = read_json(ROOT/"hte_inputs/campaign.json")
    config["analytics"].update(method_id="SYNTHETIC_VENDOR_METHOD", channel="UV_VIS_1")
    rows = []
    for inj in (1, 2, 3):
        for peak in (1, 2):
            rows.append({"inj_no":str(inj), "injection_name":"repeated_name", "type":"Unknown",
                "vial_position":f"B:A{inj}", "inj_volume(uL)":5,
                "channel_for_peak_detection":"UV_VIS_2", "number_of_det_peaks":2,
                "peak_no":peak, "retention_time(min)":peak*0.4,
                "area_uvvis1(AU*min)":0 if inj==1 and peak==1 else inj*100+peak,
                "area_uvvis2(AU*min)":9000+peak, "area_uvvis3(AU*min)":"n.a.",
                "area_uvvis4(AU*min)":"n.a.", "area_tic(counts*min)":123456})
    rows.pop()  # Truncated injection 3 is flagged, never called a nondetection.
    rows.append({**rows[0], "inj_no":"", "peak_no":"n.a.", "retention_time(min)":"n.a.",
                 "area_uvvis1(AU*min)":"n.a."})
    mapping = [{"inj_no":i, "sample_id":f"SYNTHETIC-{i}", "method_id":"SYNTHETIC_VENDOR_METHOD",
                "injection_name":"repeated_name", "vial_position":f"B:A{i}"} for i in (1,2,3)]
    source, injections = tmp_path/"vendor.csv", tmp_path/"injections.csv"
    write_csv(source, rows);write_csv(injections, mapping)
    return config, source, injections, rows, mapping


def test_chromeleon_maps_by_injection_selects_one_channel_preserves_zero_and_flags_truncation(vendor_export, tmp_path):
    config, source, mapping, *_ = vendor_export
    output = tmp_path/"normalized.csv"
    normalize_export(config, source, output, injections_path=mapping)
    rows = read_csv(output)
    assert len(rows) == 5 and rows[0]["area"] == "0.0"
    assert {row["sample_id"] for row in rows} == {"SYNTHETIC-1","SYNTHETIC-2","SYNTHETIC-3"}
    assert all(row["channel"] == "UV_VIS_1" for row in rows)
    assert rows[2]["area"] == "201.0" and rows[-1]["qc_flag"] == "incomplete_peak_export"
    report = read_json(str(output)+".normalization.json")
    assert report["placeholder_rows_omitted"] == 1
    assert report["peak_count_mismatches"] == {"3":{"reported":2,"exported":1}}


@pytest.mark.parametrize("fault", ["no_mapping", "unset_method", "unset_channel", "missing_area", "unmapped_injection", "duplicate_peak", "duplicate_sample", "wrong_method", "wrong_vial"])
def test_chromeleon_never_guesses_identity_or_quantitative_data(vendor_export, tmp_path, fault):
    config, source, injections, rows, mapping = vendor_export
    if fault == "no_mapping": injections = None
    elif fault == "unset_method": config["analytics"]["method_id"] = None
    elif fault == "unset_channel": config["analytics"]["channel"] = None
    elif fault == "missing_area": rows[0]["area_uvvis1(AU*min)"] = "n.a."
    elif fault == "unmapped_injection": rows[0]["inj_no"] = 99
    elif fault == "duplicate_peak": rows[1]["peak_no"] = 1
    elif fault == "duplicate_sample": mapping[1]["sample_id"] = mapping[0]["sample_id"]
    elif fault == "wrong_method": mapping[0]["method_id"] = "OTHER"
    else: mapping[0]["vial_position"] = "B:H12"
    write_csv(source,rows)
    if injections: write_csv(injections,mapping)
    output = tmp_path/"normalized.csv"
    with pytest.raises(ValueError):
        normalize_export(config,source,output,injections_path=injections)
    assert not output.exists()


@pytest.mark.parametrize("fault", [None, "missing_blank_peak", "duplicate_peak", "bad_qc"])
def test_build_calibration_from_measured_peaks_requires_verified_blank_and_checks(tmp_path, fault):
    config = synthetic_config(ROOT/"hte_inputs/campaign.json")
    calibration, _ = fixtures(config, [])
    peaks = []
    for row in calibration:
        for name, value in [(row["analyte"], row["area"]), ("internal_standard",row["internal_standard_area"])]:
            peaks.append({"sample_id":row["sample_id"],"area":value,"retention_time_min":config["analytics"]["references"][name]["retention_time_min"],
                          "channel":row["channel"],"method_id":row["method_id"],"qc_flag":"ok"})
    if fault == "missing_blank_peak": peaks.pop(0)
    elif fault == "duplicate_peak": peaks.append(copy.deepcopy(peaks[0]))
    elif fault == "bad_qc": peaks[0]["qc_flag"] = "incomplete_peak_export"
    plan = [{**row,"area":"","internal_standard_area":""} for row in calibration]
    write_csv(tmp_path/"peaks.csv",peaks);write_csv(tmp_path/"plan.csv",plan)
    output = tmp_path/"calibration.csv"
    if fault:
        with pytest.raises(ValueError): calibration_from_peaks(config,tmp_path/"peaks.csv",tmp_path/"plan.csv",output)
        assert not output.exists()
    else:
        calibration_from_peaks(config,tmp_path/"peaks.csv",tmp_path/"plan.csv",output)
        rows = read_csv(output)
        assert len(rows) == 14 and rows[0]["area"] == "0.0"
        assert sum(row["role"] == "check" for row in rows) == 2


def test_first_reaction_only_release_allows_parallel_calibration_but_workup_and_r2_remain_gated(tmp_path,actual_stock_preparation):
    run(tmp_path/"demo",ROOT/"hte_inputs/ligands.csv",ROOT/"hte_inputs/campaign.json")
    config = read_json(tmp_path/"demo/campaign.json")
    config["demo"] = False
    config["analytics"].update(method_id="HTEL_CONFIRMED_TEST_METHOD",channel=None,references=None,
                               quantification_limit_uM={"substrate":None,"product":None})
    for key in required_validations(config): config["validation"][key] = True
    config["validation"]["lc_calibration_validated"] = False
    config["timing"]["workup_total_minutes"] = 35  # Fictional release-test timing only.
    inv = campaign_inventory(ROOT/"hte_inputs/ligands.csv",config)
    first, second = [read_csv(tmp_path/f"demo/round{i}_design.csv") for i in (1,2)]
    actual_stock_preparation(config,inv,first)
    export(config,inv,first,tmp_path/"first_reaction",live=True,stage="dose_and_react")
    assert (tmp_path/"first_reaction/dose_and_react.py").exists()
    assert not (tmp_path/"first_reaction/workup.py").exists()
    manifest = read_json(tmp_path/"first_reaction/export_manifest.json")
    assert manifest["released_stages"] == ["dose_and_react"] and manifest["validation_scope"] == "first_reaction"
    for stage in ("workup","all"):
        with pytest.raises(ValueError,match="lc_calibration_validated"):
            export(config,inv,first,tmp_path/stage,live=True,stage=stage)
    with pytest.raises(ValueError,match="lc_calibration_validated"):
        export(config,inv,second,tmp_path/"second",live=True,stage="dose_and_react",history=read_csv(tmp_path/"first_reaction/dosing.csv"))
    config["validation"]["simultaneous_heating_capacity_validated"] = False
    with pytest.raises(ValueError,match="simultaneous_heating_capacity"):
        export(config,inv,first,tmp_path/"unvalidated_hardware",live=True,stage="dose_and_react")


@pytest.mark.parametrize("fault", [None, "workup_one_channel", "diluent_one_channel", "duplicate_channel"])
def test_scaled_workup_and_dilution_use_separate_capacity_checked_reservoir_channels(tmp_path, fault):
    config = synthetic_config(ROOT/"hte_inputs/campaign.json")
    pools = config["stock_preparation"]["reservoir_source_pools"]
    if fault == "workup_one_channel": pools["workup"] = ["A4"]
    elif fault == "diluent_one_channel": pools["LC_diluent"] = ["A5"]
    elif fault == "duplicate_channel": pools["workup"] = ["A4","A5"]
    from hte.io import write_json
    write_json(tmp_path/"config.json",config)
    if fault:
        with pytest.raises(ValueError,match="capacity exceeded|distinct valid"):
            run(tmp_path/"demo",ROOT/"hte_inputs/ligands.csv",tmp_path/"config.json")
    else:
        run(tmp_path/"demo",ROOT/"hte_inputs/ligands.csv",tmp_path/"config.json")
        deck = read_csv(tmp_path/"demo/round1/deck_loads.csv")
        assert {row["source_well"] for row in deck if row["reagent"] == "workup"} == {"A4","A6","A9"}
        assert {row["source_well"] for row in deck if row["reagent"] == "LC_diluent"} == {"A5","A7","A10","A11","A12"}
        assert all(float(row["load_ul"]) <= 11900 for row in deck if row["source_slot"] == "2")
        stocks = read_csv(tmp_path/"demo/round1/stock_preparation.csv")
        assert sum(float(row["protocol_consumption_ul"]) for row in stocks if row["reagent"] == "workup") > 48*500
