"""Final 48-vial campaign: quantities, cap sequencing, small prompts and LC handoff."""
import copy
import json
from pathlib import Path

import pytest

from hte.demo import fixtures, run, synthetic_config
from hte.ingestion import ingest_exports
from hte.io import reaction_wells, read_csv, read_json, write_csv
from hte.planning import analytical_summary, required_validations, schedule, validate_config
from hte.scoring import prompt_context, prompt_jobs
from hte.inventory import campaign_inventory, candidates

ROOT=Path(__file__).resolve().parents[2]


def test_original_coordinates_preserved_and_caps_have_clearance():
    source=read_json(ROOT/"hte_inputs/labware/paradox_48_wellplate_2000ul.json")
    derived=read_json(ROOT/"hte_inputs/labware/paradox_48_wellplate_2000ul_hs.json")
    assert derived["wells"]==source["wells"] and derived["ordering"]==source["ordering"]
    assert len(derived["wells"])==48 and derived["dimensions"]["zDimension"]==45
    assert derived["stackingOffsetWithLabware"]["opentrons_universal_flat_adapter"]=={"x":0,"y":0,"z":0}


def test_acid_dilution_and_headspace_are_explicit():
    c=read_json(ROOT/"hte_inputs/campaign.json")
    a=analytical_summary(c)
    assert a["substrate_umol"]==25 and a["extract_ul"]==750
    assert a["nominal_vial_headspace_ul"]==1250 and a["dilution_factor"]==50
    assert a["maximum_analyte_uM"]==pytest.approx(2000/3)
    assert a["internal_standard_final_uM"]==pytest.approx(200/3)
    assert a["extract_formic_acid_percent"]==pytest.approx(0.1)
    assert a["final_formic_acid_percent"]==pytest.approx(0.1)
    assert a["final_toluene_percent"]==pytest.approx(2/3)
    assert "homogeneous_sampling_validated" not in required_validations(c)


def test_all_small_prompt_queries_use_single_ligand_catalogue_and_known_yields(tmp_path):
    c=read_json(ROOT/"hte_inputs/campaign.json")
    inv=campaign_inventory(ROOT/"hte_inputs/ligands.csv",c)
    pairs=candidates(inv)
    for feedback in ([],[{"sample_id":"R1-001","yield_percent":40,"qc_pass":True}]):
        payload,blocks=prompt_context(c,inv,pairs,read_json(ROOT/"hte_inputs/literature.json"),feedback)
        assert "candidate_catalog" not in payload
        assert sum(r["same_substrate_table_S2_yield_percent"] is not None for r in payload["ligands"])==17
        jobs=prompt_jobs(c["llm"],[r["pair_id"] for r in pairs],blocks,tmp_path)
        assert len(jobs)==340
        for repeat in range(5):
            ids=[key for r,batch,*_ in jobs if r==repeat for key in batch]
            assert len(ids)==len(set(ids))==435
        for _,batch,content,schema,_ in jobs:
            query=json.loads(content[-1]["text"])
            assert 1<=len(batch)<=8 and len(query["partner_ligand_ids"])==len(batch)
            assert "candidate_ids" not in query and "candidate_catalog" not in query
            assert set(schema["properties"]["scores"]["required"])==set(query["partner_ligand_ids"])


@pytest.fixture
def demo48(tmp_path):
    folder=tmp_path/"demo"
    run(folder,ROOT/"hte_inputs/ligands.csv",ROOT/"hte_inputs/campaign.json")
    return folder


def test_deck_loads_include_every_ligand_source_and_all_stage_withdrawals(demo48):
    import math
    c=read_json(demo48/"campaign.json")
    deck=read_csv(demo48/"round1/deck_loads.csv")
    operations=read_json(demo48/"round1/operations.json")
    ligand_rows=[r for r in deck if r["reagent"].startswith("L") and r["reagent"][1:].isdigit()]
    assert len(ligand_rows)==30
    for row in deck:
        stages={"substrate","round2_predose","internal_standard","assembly"} if row["protocol"]=="dose_and_react" else {"workup","dilution"}
        consumed=sum(op["aspirated_ul_per_channel"]*op["channels"] for op in operations
                     if op["stage"] in stages and op["reagent"]==row["reagent"]
                     and op["source_slot"]==int(row["source_slot"]) and op["source_well"]==row["source_well"])
        dead=c["stock_preparation"]["tube_dead_ul" if int(row["source_slot"]) in (1,4) else "reservoir_dead_ul"]
        assert float(row["load_ul"])>=math.ceil((consumed+dead)/10)*10
        if row["reagent"] not in c["automation"]["direct_stock_ids"]:
            assert float(row["load_ul"])==math.ceil((consumed+dead)/10)*10


@pytest.mark.parametrize("fault",[None,"partial","duplicate_batch","overlapping_sample"])
def test_separate_lc_sequences_with_reset_injection_numbers_join_safely(demo48,tmp_path,fault):
    c=read_json(demo48/"campaign.json")
    doses=read_csv(demo48/"round1/dosing.csv")
    _,peaks=fixtures(c,doses)
    exports=[];mappings=[]
    for batch in range(6):
        part=doses[batch*8:(batch+1)*8]
        if fault=="overlapping_sample" and batch==1:part[0]=doses[0]
        mapping=[];rows=[]
        for inj,dose in enumerate(part,1):
            mapping.append({"inj_no":inj,"sample_id":dose["sample_id"],"method_id":c["analytics"]["method_id"]})
            sample=[r for r in peaks if r["sample_id"]==dose["sample_id"]]
            for peak_index,peak in enumerate(sample,1):
                rows.append({"inj_no":inj,"injection_name":"repeated_name","type":"Unknown","vial_position":f"B:A{inj}",
                             "inj_volume(uL)":2,"channel_for_peak_detection":"UV_VIS_1","number_of_det_peaks":3,
                             "peak_no":peak_index,"retention_time(min)":peak["retention_time_min"],
                             **{f"area_uvvis{i}(AU*min)":peak["area"] for i in range(1,5)}})
        source=tmp_path/f"batch{batch}.csv";mapping_path=tmp_path/f"batch{batch}.mapping.csv"
        write_csv(source,rows);write_csv(mapping_path,mapping)
        exports.append(source);mappings.append(mapping_path)
    if fault=="partial":exports.pop();mappings.pop()
    if fault=="duplicate_batch":exports[1]=exports[0]
    if fault:
        message={"partial":"every expected sample", "duplicate_batch":"more than once",
                 "overlapping_sample":"multiple LC batches"}[fault]
        with pytest.raises(ValueError,match=message):ingest_exports(c,exports,mappings,demo48/"round1/dosing.csv",tmp_path/"joined")
        assert not (tmp_path/"joined/peaks.ready.json").exists()
    else:
        combined,ready=ingest_exports(c,exports,mappings,demo48/"round1/dosing.csv",tmp_path/"joined")
        assert len(read_csv(combined))==144 and ready.exists()


def test_unconfirmed_or_impossible_staged_lc_timing_cannot_release():
    c=synthetic_config(ROOT/"hte_inputs/campaign.json")
    assert schedule(c)["planned_total_minutes"]==pytest.approx(804.7)
    c["timing"]["staged_lc_overlap_minutes_by_round"]["1"]=100
    c["timing"]["staged_lc_overlap_minutes"]=100
    with pytest.raises(ValueError,match="preceding injection windows"):schedule(c)


def test_staff_lc_command_selects_next_22_then_analyzes_final_without_paid_calls(demo48,tmp_path,monkeypatch):
    import runpy
    import sys
    import anthropic
    calls=[]
    def no_network(**kwargs):raise AssertionError("Staff rehearsal attempted a paid client")
    monkeypatch.setattr(anthropic,"Anthropic",no_network)
    c=read_json(demo48/"campaign.json");c["demo"]=False
    config_path=tmp_path/"local-campaign.json";config_path.write_text(json.dumps(c))
    def mock_scores(config,inventory,remaining,evidence,observations,output):
        payload,_=prompt_context(config,inventory,remaining,evidence,observations)
        calls.append((len(remaining),len(observations),sum(r["same_substrate_table_S2_yield_percent"] is not None for r in payload["ligands"])))
        return [{"pair_id":r["pair_id"],"mean_score":50,"score_sd":0,"scoring_calls":5} for r in remaining]
    monkeypatch.setattr("hte.workflow.score_candidates",mock_scores)
    for round_number,mode in [(1,"next"),(2,"final")]:
        doses=read_csv(demo48/f"round{round_number}/dosing.csv")
        _,peaks=fixtures(c,doses);exports=[];maps=[]
        for batch,start in enumerate(range(0,len(doses),8),1):
            rows=[];mapping=[]
            for inj,dose in enumerate(doses[start:start+8],1):
                mapping.append({"inj_no":inj,"sample_id":dose["sample_id"],"method_id":c["analytics"]["method_id"]})
                for index,p in enumerate([p for p in peaks if p["sample_id"]==dose["sample_id"]],1):
                    rows.append({"inj_no":inj,"injection_name":"reused","type":"Unknown","vial_position":str(inj),
                                 "inj_volume(uL)":2,"channel_for_peak_detection":"UV_VIS_1","number_of_det_peaks":3,
                                 "peak_no":index,"retention_time(min)":p["retention_time_min"],
                                 **{f"area_uvvis{i}(AU*min)":p["area"] for i in range(1,5)}})
            source=tmp_path/f"r{round_number}-batch{batch}.csv";mp=source.with_suffix(".mapping.csv")
            write_csv(source,rows);write_csv(mp,mapping);exports.append(str(source));maps.append(str(mp))
        out=tmp_path/f"staff-{mode}"
        monkeypatch.setattr(sys,"argv",["hte-lc-results.py",mode,"--config",str(config_path),
            "--dosing",str(demo48/f"round{round_number}/dosing.csv"),"--calibration",str(demo48/"calibration.csv"),
            "--exports",*exports,"--injections",*maps,"--output",str(out)])
        runpy.run_path(str(ROOT/"scripts/hte-lc-results.py"),run_name="__main__")
        assert read_json(out/"inputs/settings.json")["config"]==c
        assert (out/"inputs/calibration.csv").read_bytes()==(demo48/"calibration.csv").read_bytes()
        archived=read_json(out/"ingestion/ingestion.json")["archived_inputs"]
        assert len(archived)==2*len(exports)+1
        for item in archived:
            assert (out/"ingestion"/item["archived"]).read_bytes()==Path(item["source"]).read_bytes()
        if mode=="next":
            next_file=next(out.glob("decision/iteration-*/next_dosing.csv"));new=read_csv(next_file)
            assert len(new)==23 and sum(r["kind"]=="pair" for r in new)==22
            assert sum(r["kind"]=="single" and r["ligand_a"]=="L17" for r in new)==1
        else:
            assert len(read_csv(out/"analysis/results.csv"))==23
            assert read_json(out/"analysis/qc_report.json")["batch_qc_pass"]
    assert calls==[(387,48,17)]
