import copy
from pathlib import Path

import pytest

from hte.analytics import calibration_from_peaks
from hte.analytical_practice import run, verify
from hte.io import read_csv, read_json, write_csv

ROOT=Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def practice(tmp_path_factory):
    out=tmp_path_factory.mktemp("analytical")/"practice"
    report=run(out,ROOT/"hte_inputs/campaign.json",ROOT/"hte_inputs/calibration_template.csv")
    return out,read_json(report)


def test_raw_calibration_to_pilot_replay_and_hidden_area_biases(practice):
    out,report=practice
    assert report["calibration_injections"]==14 and report["pilot_injections"]==7
    assert report["api_calls"]==0 and not report["real_method_validated"]
    cases={r["scenario"]:r for r in report["scenarios"]}
    assert all(cases[k]["pilot_pass"] for k in ("clean","extra_peak","injection_scale"))
    assert all(not cases[k]["pilot_pass"] for k in ("rt_shift","ambiguous_peak","missing_is","truncated_export"))
    # A known truth check detects biases which pass the unknown-sample area-only checks.
    for name in ("hidden_interference","unreported_area_loss"):
        assert cases[name]["area_only_qc_pass"] and not cases[name]["pilot_pass"]
    recipes=read_csv(out/"pilot_preparation.csv")
    assert all(sum(float(r[k]) for k in ("SM_10mM_ul","product_10mM_ul","mesitylene_5mM_ul","matched_matrix_ul"))==pytest.approx(1000) for r in recipes)
    assert all(not r["method_id"] for r in read_csv(out/"pilot_injection_map.csv"))
    assert len(read_csv(out/"calibration_injection_map.csv"))==14
    native=read_csv(out/"chromeleon_concentrations_template.csv")
    assert len(native)==14 and all(not r["concentration_uM"] for r in native)


@pytest.mark.parametrize("fault",["missing_review","wrong_method","unplanned_absence","blank_peak_conflict"])
def test_calibration_blanks_require_traceable_review_not_invented_peaks(practice,tmp_path,fault):
    out,_=practice;synthetic=out/"synthetic"
    config=read_json(synthetic/"campaign.json")
    reviews=read_csv(synthetic/"calibration-absences.csv")
    if fault=="missing_review":reviews=[]
    elif fault=="wrong_method":reviews[0]["method_id"]="OTHER"
    elif fault=="unplanned_absence":reviews[0]["sample_id"]="CAL-SM-01"
    else:
        peaks=read_csv(synthetic/"calibration-peaks.csv")
        row=copy.deepcopy(peaks[0]);row.update(retention_time_min=0.4,area=1)
        peaks.append(row);write_csv(tmp_path/"peaks.csv",peaks)
    review_path=tmp_path/"review.csv"
    write_csv(review_path,reviews,["sample_id","analyte","method_id","reviewed_by","note"])
    with pytest.raises(ValueError):
        calibration_from_peaks(config,tmp_path/"peaks.csv" if fault=="blank_peak_conflict" else synthetic/"calibration-peaks.csv",
            ROOT/"hte_inputs/calibration_template.csv",tmp_path/"calibration.csv",review_path)
    assert not (tmp_path/"calibration.csv").exists()


@pytest.mark.parametrize("fault",["missing_reviews","nonzero_review","reaction_id","incomplete","repeat_export","bad_is"])
def test_real_pilot_refuses_missing_or_unsafe_inputs(practice,tmp_path,fault):
    out,_=practice;s=out/"synthetic"
    cfg=read_json(s/"campaign.json")
    plan=read_csv(out/"pilot_plan.csv");reviews=read_csv(s/"pilot-absences.csv")
    if fault=="missing_reviews":reviews=[]
    elif fault=="nonzero_review":reviews[0]["sample_id"]="PILOT-03"
    elif fault=="reaction_id":plan[0]["sample_id"]="R1-001"
    elif fault=="incomplete":plan.pop()
    elif fault=="bad_is":plan[0]["internal_standard_uM"]=33
    write_csv(tmp_path/"plan.csv",plan)
    write_csv(tmp_path/"reviews.csv",reviews,["sample_id","analyte","method_id","reviewed_by","note"])
    sources=[s/"clean/vendor.csv"];maps=[s/"clean/map.csv"]
    if fault=="repeat_export":sources*=2;maps*=2
    if fault=="missing_reviews":
        result=verify(cfg,sources,maps,s/"calibration.csv",tmp_path/"plan.csv",tmp_path/"result",tmp_path/"reviews.csv")
        assert not read_json(result)["pilot_pass"]
    else:
        with pytest.raises(ValueError):
            verify(cfg,sources,maps,s/"calibration.csv",tmp_path/"plan.csv",tmp_path/"result",tmp_path/"reviews.csv")


def test_pilot_cli_reports_failure_and_never_constructs_a_paid_client(practice,tmp_path,monkeypatch,capsys):
    import anthropic
    from hte.cli import main
    def forbidden(**kwargs):raise AssertionError("Pilot must not construct an API client")
    monkeypatch.setattr(anthropic,"Anthropic",forbidden)
    out,_=practice;s=out/"synthetic"
    monkeypatch.setattr("sys.argv",["hte","--config",str(s/"campaign.json"),"verify-pilot",
        "--exports",str(s/"hidden_interference/vendor.csv"),"--injections",str(s/"hidden_interference/map.csv"),
        "--calibration",str(s/"calibration.csv"),"--plan",str(out/"pilot_plan.csv"),
        "--reviewed-absences",str(s/"pilot-absences.csv"),"--output",str(tmp_path/"failed")])
    with pytest.raises(SystemExit) as stopped:main()
    assert stopped.value.code==2
    assert not read_json(tmp_path/"failed/pilot_report.json")["pilot_pass"]


@pytest.mark.parametrize("fault",[None,"biased_native_value","wrong_method","missing_native_result"])
def test_optional_chromeleon_concentrations_are_compared_not_recalibrated(practice,tmp_path,fault):
    out,_=practice;s=out/"synthetic";cfg=read_json(s/"campaign.json")
    rows=[{"sample_id":r["sample_id"],"analyte":name,"concentration_uM":r[name+"_uM"],
           "method_id":cfg["analytics"]["method_id"],"channel":cfg["analytics"]["channel"]}
          for r in read_csv(out/"pilot_plan.csv") for name in ("substrate","product")]
    if fault=="biased_native_value":rows[5]["concentration_uM"]=float(rows[5]["concentration_uM"])*1.2
    elif fault=="wrong_method":rows[0]["method_id"]="OTHER"
    elif fault=="missing_native_result":rows.pop()
    write_csv(tmp_path/"native.csv",rows)
    args=(cfg,[s/"clean/vendor.csv"],[s/"clean/map.csv"],s/"calibration.csv",out/"pilot_plan.csv",
          tmp_path/"result",s/"pilot-absences.csv")
    if fault in ("wrong_method","missing_native_result"):
        with pytest.raises(ValueError):verify(*args,native_concentrations_path=tmp_path/"native.csv")
    else:
        report=read_json(verify(*args,native_concentrations_path=tmp_path/"native.csv"))
        assert report["chromeleon_concentrations_compared"]
        assert report["pilot_pass"] is (fault is None)
        product=next(r for r in report["comparisons"] if r["sample_id"]=="PILOT-03" and r["analyte"]=="product")
        assert product["measured_uM"]==pytest.approx(1000/3)
