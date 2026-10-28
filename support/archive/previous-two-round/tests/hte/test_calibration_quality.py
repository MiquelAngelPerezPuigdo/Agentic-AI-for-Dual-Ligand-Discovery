"""Low-level quantification must not be concealed by a broad-range global R2."""
from pathlib import Path

import numpy as np
import pytest

from hte.analytics import analyze, fit_calibration
from hte.demo import fixtures, synthetic_config


ROOT = Path(__file__).resolve().parents[2]


def calibration():
    config = synthetic_config(ROOT / "hte_inputs/campaign.json")
    rows, _ = fixtures(config, [])
    return config, rows


def test_low_level_failure_is_rejected_despite_excellent_r2_and_high_check():
    config, rows = calibration()
    point = next(row for row in rows if row["analyte"] == "product"
                 and row["concentration_uM"] == 10)
    point["area"] *= 0.1
    points = [row for row in rows if row["analyte"] == "product" and row["role"] == "calibration"]
    x = np.array([row["concentration_uM"] for row in points])
    y = np.array([row["area"] / row["internal_standard_area"] for row in points])
    slope, intercept = np.linalg.lstsq(np.c_[x, np.ones(len(x))], y, rcond=None)[0]
    r2 = 1 - np.sum((y - (slope*x + intercept))**2) / np.sum((y-y.mean())**2)
    check = next(row for row in rows if row["analyte"] == "product" and row["role"] == "check")
    measured_check = (check["area"] / check["internal_standard_area"] - intercept) / slope
    assert r2 > 0.9998
    assert abs(measured_check/check["concentration_uM"] - 1) < 0.001
    with pytest.raises(ValueError, match="back-calculation failed for product at 10 uM"):
        fit_calibration(config, rows)


def test_each_fit_level_is_reported_and_blank_has_no_relative_error():
    config, rows = calibration()
    models = fit_calibration(config, rows)
    for model in models.values():
        assert model["minimum_uM"] == 0
        assert model["minimum_nonzero_uM"] == 10
        checks = model["fit_level_checks"]
        assert len(checks) == 6
        blank = next(row for row in checks if row["expected_uM"] == 0)
        assert blank["relative_error"] is None and blank["tolerance_fraction"] is None
        assert abs(blank["measured_uM"]) < 1e-9
        nonzero = [row for row in checks if row["expected_uM"] > 0]
        assert all(row["relative_error"] < 1e-9 for row in nonzero)
        assert next(row for row in nonzero if row["expected_uM"] == 10)["tolerance_fraction"] == 0.20
        assert all(row["tolerance_fraction"] == 0.15 for row in nonzero if row["expected_uM"] != 10)


def test_lowest_level_tolerance_is_configurable_without_weakening_other_levels():
    config, rows = calibration()
    point = next(row for row in rows if row["analyte"] == "product"
                 and row["concentration_uM"] == 10)
    point["area"] *= 1.25
    model = fit_calibration(config, rows)["product"]
    low = next(row for row in model["fit_level_checks"] if row["expected_uM"] == 10)
    assert 0.15 < low["relative_error"] < 0.20
    config["analytics"]["calibration_lowest_level_tolerance_fraction"] = 0.15
    with pytest.raises(ValueError, match="back-calculation failed for product at 10 uM"):
        fit_calibration(config, rows)


@pytest.mark.parametrize("measured_loq,product_uM,effective_bound,censored", [
    (1, 5, 10, True),
    (1, None, 10, True),
    (25, 20, 25, True),
    (1, 20, 10, False),
])
def test_blank_does_not_extend_the_quantitative_range(
        tmp_path, measured_loq, product_uM, effective_bound, censored):
    config, calibration_rows = calibration()
    config["analytics"]["quantification_limit_uM"]["product"] = measured_loq
    dose = {"sample_id": "AUDIT-01", "round": 1, "well": "A1", "kind": "pair",
            "pair_id": "L01__L02", "ligand_a": "L01", "ligand_b": "L02",
            "reaction_volume_ul": 250, "workup_ul": 500,
            "aliquot_ul": 20, "diluent_ul": 980, "substrate_umol": 25,
            "internal_standard_final_uM": config["analytics"]["internal_standard_final_uM"]}
    concentrations = {"substrate": 600, "internal_standard": 1000}
    if product_uM is not None:
        concentrations["product"] = product_uM
    peaks = [{"sample_id": dose["sample_id"],
              "retention_time_min": config["analytics"]["references"][name]["retention_time_min"],
              "area": concentration*10, "channel": config["analytics"]["channel"],
              "method_id": config["analytics"]["method_id"], "qc_flag": "ok"}
             for name, concentration in concentrations.items()]
    results, report = analyze(config, [dose], peaks, calibration_rows, tmp_path)
    result = results[0]
    assert report["batch_qc_pass"] and result["qc_pass"]
    assert report["quantification_limits_uM"]["product"] == {
        "measured_loq": measured_loq, "lowest_nonzero_calibrator": 10,
        "effective_lower_bound": effective_bound}
    if censored:
        assert result["yield_percent"] is None and result["product_umol"] is None
        assert result["censored_analytes"] == "product"
        assert result["yield_upper_bound_percent"] == pytest.approx(effective_bound*0.15)
    else:
        assert result["yield_percent"] == pytest.approx(product_uM*0.15)
        assert result["yield_upper_bound_percent"] is None
