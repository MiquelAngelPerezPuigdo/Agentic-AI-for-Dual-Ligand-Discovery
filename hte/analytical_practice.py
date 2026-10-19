"""Known-mixture pilot replay and offline analytical challenges. No robot or LLM calls."""
from __future__ import annotations

import copy
from pathlib import Path

from .analytics import (analyze, calibration_from_peaks, normalize_export,
                        reviewed_absences, validate_analytics_settings)
from .io import (digest, finite, new_output, object_digest, read_csv, read_json,
                 write_csv, write_json)


def prepare(config, output):
    """Seven optional pilot injections, separate from the campaign/calibration."""
    out = Path(output)
    from .analytical_stocks import preparation
    write_csv(out/"analytical_stock_preparation.csv", preparation(config))
    from .preparation import pilot_recipes
    plan,recipes,mapping=[],[],[]
    for i,row in enumerate(pilot_recipes(config),1):
        plan.append({key:row[key] for key in ("sample_id","role","substrate_uM","product_uM","internal_standard_uM")})
        recipes.append(dict(row,final_ul=1000,preparation="Robot preparation from independent CHECK masters; enable automation.prepare_optional_pilot BEFORE stock preparation"))
        mapping.append(dict(inj_no=i,sample_id=row["sample_id"],method_id=config["analytics"].get("method_id") or "",lc_plate_id=row["plate_id"],well=row["well"]))
    write_csv(out/"pilot_plan.csv",plan)
    write_csv(out/"pilot_preparation.csv",recipes)
    write_csv(out/"pilot_injection_map.csv",mapping)
    write_csv(out/"absence_review_template.csv",[],
              ["sample_id","analyte","method_id","reviewed_by","note"])
    return plan


def verify(config, exports, mappings, calibration_path, plan_path, output,
           reviewed_absences_path=None, tolerance=0.15):
    """Replay real pilot exports against known concentrations; never optimizer feedback."""
    validate_analytics_settings(config)
    tolerance = finite(tolerance,"pilot relative-error tolerance",1e-9,1)
    if (not exports or len(exports)!=len(mappings)
            or len({str(Path(p).resolve()) for p in exports})!=len(exports)):
        raise ValueError("Supply distinct pilot exports and one injection map per export")
    plan = read_csv(plan_path)
    ids = [row["sample_id"] for row in plan]
    if not ids or len(ids)!=len(set(ids)) or any(not key.startswith("PILOT-") for key in ids):
        raise ValueError("Pilot plan needs unique PILOT- sample IDs, separate from reaction samples")
    for row in plan:
        for name in ("substrate","product","internal_standard"):
            finite(row[name+"_uM"],"pilot "+name,0)
        if abs(float(row["internal_standard_uM"])-config["analytics"]["internal_standard_final_uM"])>1e-6:
            raise ValueError("Pilot and calibration must use the same final IS concentration")
    absences = reviewed_absences(reviewed_absences_path,config["analytics"]["method_id"])
    allowed = {(r["sample_id"],name) for r in plan for name in ("substrate","product")
               if float(r[name+"_uM"])==0}
    if not set(absences)<=allowed:
        raise ValueError("Pilot absence reviews are allowed only for expected-zero analytes")
    inputs = {"config_digest":object_digest(config),"plan_sha256":digest(plan_path),
              "calibration_sha256":digest(calibration_path),
              "reviewed_absences_sha256":digest(reviewed_absences_path) if reviewed_absences_path else None,
              "sources":[{"export_sha256":digest(p),"mapping_sha256":digest(m)} for p,m in zip(exports,mappings)]}
    paths=[plan_path,calibration_path,*exports,*mappings]
    if reviewed_absences_path:paths.append(reviewed_absences_path)
    hashes={str(p):digest(p) for p in paths}
    if len({hashes[str(p)] for p in exports}) != len(exports):
        raise ValueError("Pilot exports contain identical file content; supply each measured sequence only once")
    out = new_output(output)
    peaks, seen = [], set()
    for i,(source,mapping) in enumerate(zip(exports,mappings),1):
        normalized=out/f"part-{i:02d}.csv"
        normalize_export(config,source,normalized,injections_path=mapping)
        rows=read_csv(normalized);samples={r["sample_id"] for r in rows}
        if samples & seen:raise ValueError("Pilot samples occur in multiple exports")
        seen.update(samples);peaks.extend(rows)
    if seen!=set(ids):raise ValueError("Pilot exports must cover exactly the planned sample IDs")
    local=copy.deepcopy(config)
    # Bound handling is restricted to explicit reviews; live configuration stays unchanged.
    local["analytics"]["missing_analyte_policy"]="censor"
    doses=[]
    for row in plan:
        doses.append({"sample_id":row["sample_id"],"round":0,"well":"","kind":"analytical_pilot",
                      "pair_id":"","ligand_a":"","ligand_b":"",
                      "reaction_volume_ul":config["chemistry"]["reaction_volume_ul"],
                      "workup_ul":config["liquids"]["workup_ul"],"aliquot_ul":config["liquids"]["aliquot_ul"],
                      "diluent_ul":config["liquids"]["diluent_ul"],
                      "substrate_umol":config["chemistry"]["reaction_volume_ul"]*config["chemistry"]["substrate_molarity_M"],
                      "internal_standard_final_uM":float(row["internal_standard_uM"])})
    results,qc=analyze(local,doses,peaks,read_csv(calibration_path),out/"analysis")
    by_id={r["sample_id"]:r for r in results}
    comparisons=[]
    for row in plan:
        result=by_id[row["sample_id"]]
        for name,amount_key in (("product","product_umol"),("substrate","substrate_remaining_umol")):
            expected=float(row[name+"_uM"])
            amount=result[amount_key]
            volume=config["chemistry"]["reaction_volume_ul"]+config["liquids"]["workup_ul"]
            dilution=(config["liquids"]["aliquot_ul"]+config["liquids"]["diluent_ul"])/config["liquids"]["aliquot_ul"]
            measured=amount*1e6/(volume*dilution) if amount is not None else None
            ref=config["analytics"]["references"][name]
            matches=[p for p in peaks if p["sample_id"]==row["sample_id"] and p["channel"]==config["analytics"]["channel"]
                     and abs(float(p["retention_time_min"])-ref["retention_time_min"])<=ref["window_min"]]
            reviewed=(row["sample_id"],name) in absences
            relative=abs(measured-expected)/expected if measured is not None and expected>0 else None
            if expected==0:
                passed=result["qc_pass"] and reviewed and not matches
                reason="reviewed nondetection" if passed else "zero-analyte pilot requires reviewed absence and no detected peak"
            else:
                passed=result["qc_pass"] and not reviewed and measured is not None and relative<=tolerance
                reason="within tolerance" if passed else "QC, nondetection or concentration error"
            comparisons.append({"sample_id":row["sample_id"],"analyte":name,"expected_uM":expected,
                                "measured_uM":measured,"relative_error":relative,"pass":bool(passed),"reason":reason,
                                "qc_flags":result["qc_flags"]})
    passed=qc["batch_qc_pass"] and all(r["pass"] for r in comparisons)
    if any(digest(path)!=value for path,value in hashes.items()):
        raise ValueError("Pilot inputs changed during analysis; use stable completed exports")
    report={"pilot_pass":passed,"synthetic_only":bool(config.get("demo")),
            "samples":len(plan),"relative_error_tolerance":tolerance,
            "quantification_qc_pass":qc["batch_qc_pass"],"comparisons":comparisons,"inputs":inputs,
            "reviewed_absences":list(absences.values()),"api_calls":0,"optimizer_feedback":False,
            "scope":"Known-mixture concentration checks; no automated peak-purity, saturation or extraction-recovery proof."}
    write_csv(out/"comparisons.csv",comparisons)
    write_json(out/"pilot_report.json",report)
    return out/"pilot_report.json"


def _vendor(config, rows, output, mapping):
    """Mock Chromeleon wide tables; intentionally omit truly absent analytes."""
    result=[]
    for inj,sample in enumerate(rows,1):
        for peak,p in enumerate(sample["peaks"],1):
            result.append({"inj_no":inj,"injection_name":"SYNTHETIC_PILOT","type":"Unknown","vial_position":str(inj),
                           "inj_volume(uL)":2,"channel_for_peak_detection":"UV_VIS_2",
                           "number_of_det_peaks":sample.get("reported_count",len(sample["peaks"])),
                           "peak_no":peak,"retention_time(min)":p["rt"],"area_uvvis1(AU*min)":p["area"],
                           "area_uvvis2(AU*min)":p["area"]*100,"area_uvvis3(AU*min)":"n.a.","area_uvvis4(AU*min)":"n.a."})
    write_csv(output,result)
    write_csv(mapping,[{"inj_no":i,"sample_id":r["sample_id"],"method_id":config["analytics"]["method_id"]}
                       for i,r in enumerate(rows,1)])


def run(output,config_path,calibration_plan="hte_inputs/calibration_template.csv"):
    """Build pilot recipes and exercise the real importer/calibration/quantifier offline."""
    from .demo import synthetic_config
    source=read_json(config_path)
    out=new_output(output)
    prepare(source,out)
    config=synthetic_config(config_path)
    config["analytics"]["missing_analyte_policy"]="reject"
    synthetic=out/"synthetic";synthetic.mkdir()
    write_json(synthetic/"SYNTHETIC_ONLY.json",{"synthetic_only":True,"api_calls":0,"physical_execution_allowed":False})
    write_json(synthetic/"campaign.json",config)
    cal_plan=read_csv(calibration_plan)
    write_csv(out/"calibration_injection_map.csv",[{"inj_no":i,"sample_id":r["sample_id"],
              "method_id":source["analytics"].get("method_id") or ""} for i,r in enumerate(cal_plan,1)])
    slopes={"substrate":0.0012,"product":0.0009}
    refs=config["analytics"]["references"]
    def sample(key,sm,product,index):
        is_area=10000*(0.9+0.02*(index%8))
        peaks=[{"name":name,"rt":refs[name]["retention_time_min"],"area":slopes[name]*value*is_area}
               for name,value in (("substrate",sm),("product",product)) if value>0]
        peaks.append({"name":"internal_standard","rt":refs["internal_standard"]["retention_time_min"],"area":is_area})
        return {"sample_id":key,"peaks":peaks}
    def review(key,name):
        return {"sample_id":key,"analyte":name,"method_id":config["analytics"]["method_id"],
                "reviewed_by":"SYNTHETIC_REVIEW","note":"Simulated known absent analyte; not a real chromatogram review"}
    cal_rows=[];cal_absences=[]
    for i,r in enumerate(cal_plan):
        values={"substrate":0,"product":0};values[r["analyte"]]=float(r["concentration_uM"])
        cal_rows.append(sample(r["sample_id"],values["substrate"],values["product"],i))
        if float(r["concentration_uM"])==0:cal_absences.append(review(r["sample_id"],r["analyte"]))
    _vendor(config,cal_rows,synthetic/"calibration-vendor.csv",synthetic/"calibration-map.csv")
    write_csv(synthetic/"calibration-absences.csv",cal_absences)
    normalize_export(config,synthetic/"calibration-vendor.csv",synthetic/"calibration-peaks.csv",synthetic/"calibration-map.csv")
    calibration_from_peaks(config,synthetic/"calibration-peaks.csv",calibration_plan,synthetic/"calibration.csv",
                           synthetic/"calibration-absences.csv")
    pilot=read_csv(out/"pilot_plan.csv")
    rows=[sample(r["sample_id"],float(r["substrate_uM"]),float(r["product_uM"]),i) for i,r in enumerate(pilot)]
    write_csv(synthetic/"pilot-absences.csv",[review(r["sample_id"],name) for r in pilot
              for name in ("substrate","product") if float(r[name+"_uM"])==0])
    scenarios=[]
    for name in ("clean","rt_shift","ambiguous_peak","missing_is","truncated_export","extra_peak",
                 "injection_scale","hidden_interference","unreported_area_loss"):
        folder=synthetic/name;folder.mkdir()
        changed=copy.deepcopy(rows);target=changed[2]
        product=next(p for p in target["peaks"] if p["name"]=="product")
        if name=="rt_shift":product["rt"]+=0.08
        elif name=="ambiguous_peak":target["peaks"].append({"rt":product["rt"]+0.01,"area":100})
        elif name=="missing_is":target["peaks"]=[p for p in target["peaks"] if p["name"]!="internal_standard"]
        elif name=="truncated_export":target["reported_count"]=4
        elif name=="extra_peak":target["peaks"].append({"rt":1.2,"area":1e5})
        elif name=="injection_scale":
            for p in target["peaks"]:p["area"]*=0.8
        elif name=="hidden_interference":product["area"]*=1.18
        elif name=="unreported_area_loss":product["area"]*=0.8
        _vendor(config,changed,folder/"vendor.csv",folder/"map.csv")
        report_path=verify(config,[folder/"vendor.csv"],[folder/"map.csv"],synthetic/"calibration.csv",
                           out/"pilot_plan.csv",folder/"replay",synthetic/"pilot-absences.csv")
        report=read_json(report_path)
        expected=name in ("clean","extra_peak","injection_scale")
        if report["pilot_pass"]!=expected:raise ValueError("Analytical practice failed: "+name)
        scenarios.append({"scenario":name,"expected_pilot_pass":expected,"pilot_pass":report["pilot_pass"],
                          "area_only_qc_pass":report["quantification_qc_pass"]})
    result={"synthetic_only":True,"api_calls":0,"physical_execution_allowed":False,
            "calibration_injections":len(cal_plan),"pilot_injections":len(pilot),"scenarios":scenarios,
            "all_expected_outcomes_passed":True,"real_method_validated":False,
            "scope":"Merged interference/area loss can pass unknown-sample QC; known pilot truth detects these simulated biases. Real chromatograms still need identity/separation review."}
    write_json(out/"practice_report.json",result)
    return out/"practice_report.json"
