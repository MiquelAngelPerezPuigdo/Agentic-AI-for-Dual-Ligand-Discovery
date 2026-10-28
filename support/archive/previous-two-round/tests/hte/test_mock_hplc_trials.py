"""End-to-end export challenges: valid recovery, blocked faults and invisible biases."""
import importlib.util
from pathlib import Path

import anthropic
import numpy as np
import pytest

from hte.io import digest, read_csv, read_json

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("mock_hplc_trials", ROOT / "scripts/mock-hplc-trials.py")
mock = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mock)


@pytest.fixture(scope="module")
def trials(tmp_path_factory):
    folder = tmp_path_factory.mktemp("chromatograms") / "trial"
    source_hash = digest(ROOT / "hte_inputs/campaign.json")
    original = anthropic.Anthropic
    def forbidden(*args, **kwargs):
        raise AssertionError("Mock chromatography must never construct a paid client")
    anthropic.Anthropic = forbidden
    try:
        report = mock.run(folder, render=False)
    finally:
        anthropic.Anthropic = original
    assert digest(ROOT / "hte_inputs/campaign.json") == source_hash
    return folder, report, {r["scenario"]: r for r in report["trials"]}


def test_noisy_standards_through_real_importer_and_yield_calculation(trials):
    folder, report, cases = trials
    assert report["all_expected_outcomes_passed"] and len(cases) == 14
    assert report["calibration_injections"] == 14 and report["pilot_injections_per_trial"] == 7
    assert report["api_calls"] == 0 and not report["optimizer_feedback"]
    assert not report["real_method_validated"] and not report["raw_trace_integration_executed"]
    assert not report["chromeleon_executed"] and not report["physical_execution_allowed"]
    for key, truth in (("clean", 50), ("low_yield", 10), ("high_yield", 90)):
        assert cases[key]["usable_yield_percent"] == pytest.approx(truth, abs=0.5)
    assert cases["injection_scale"]["usable_yield_percent"] == pytest.approx(cases["clean"]["usable_yield_percent"])
    assert cases["extra_impurity"]["usable_yield_percent"] == pytest.approx(cases["clean"]["usable_yield_percent"])
    cal = read_json(folder / "clean/unknown-sample-analysis/qc_report.json")["calibration"]
    assert all(r["r2"] > 0.995 for r in cal.values())


def test_detectable_failures_never_leave_numeric_feedback(trials):
    folder, report, cases = trials
    for key in ("rt_outside", "split_product", "missing_is", "is_outlier", "truncated_export", "missing_area"):
        assert not cases[key]["unknown_sample_qc_pass"]
        assert not cases[key]["known_mixture_pass"]
        assert cases[key]["usable_yield_percent"] is None
        assert cases[key]["qc_flags"]
    assert not cases["missing_area"]["import_pass"]
    # Nonselected channels still carry values: silently falling back would turn this into a false success.
    raw = read_csv(folder / "missing_area/vendor.csv")
    broken = next(r for r in raw if r["inj_no"] == "3" and r["area_uvvis1(AU*min)"] == "n.a." and r["peak_no"] != "n.a.")
    assert float(broken["area_uvvis2(AU*min)"]) > 0


def test_hidden_bias_is_reported_as_unknown_sample_failure_to_detect(trials):
    folder, report, cases = trials
    for key, biased in (("coelution_bias", 59), ("integration_loss", 40)):
        r = cases[key]
        assert r["unknown_sample_qc_pass"] and not r["known_mixture_pass"]
        assert r["true_yield_percent"] == 50
        assert r["usable_yield_percent"] == pytest.approx(biased, abs=0.5)
        assert r["outcome"] == "Hidden bias"
    for key in ("clean", "coelution_bias", "integration_loss"):
        p = read_csv(folder / key / "peaks.csv")
        assert sum(r["sample_id"] == "PILOT-03" and 0.85 <= float(r["retention_time_min"]) <= 0.95 for r in p) == 1


def test_trace_areas_padding_and_repeated_names_match_export_contract(trials):
    folder, report, cases = trials
    raw = read_csv(folder / "clean/vendor.csv")
    assert list(raw[0]) == mock.HEADERS
    assert len({r["injection_name"] for r in raw}) == 1
    normalized = read_json(folder / "clean/peaks.csv.normalization.json")
    assert normalized["placeholder_rows_omitted"] > 0
    assert normalized["injections"] == 7
    assert normalized["selected_area_column"] == "area_uvvis1(AU*min)"
    for key in cases:
        truth = read_json(folder / key / "trace_truth.json")
        assert all(r["numerical_area_AU_min"] == pytest.approx(r["imposed_area_AU_min"], rel=1e-6)
                   for r in truth["area_verification"])
    clean = read_csv(folder / "clean/trace.csv")
    lost = read_csv(folder / "integration_loss/trace.csv")
    # Signal shape/area is not changed to disguise deliberately incorrect integrated exports.
    for name in ("clean", "integration_loss"):
        components = read_json(folder / name / "trace_truth.json")["components"]
        assert components == read_json(folder / "clean/trace_truth.json")["components"]
    assert len(clean) == len(lost) == 1701


def test_synthetic_generation_is_deterministic_at_fixed_seed():
    config = mock.synthetic_config(ROOT / "hte_inputs/campaign.json")
    a = mock.sample(config, "PILOT-TEST", 100, 200, np.random.default_rng(1707))
    b = mock.sample(config, "PILOT-TEST", 100, 200, np.random.default_rng(1707))
    assert a == b
    assert mock.trace(a, np.random.default_rng(7)) == mock.trace(b, np.random.default_rng(7))
