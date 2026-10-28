"""An internal-standard switch requires new, chemically identified calibration."""
from pathlib import Path

import pytest

from hte.analytics import (analyze, calibration_from_peaks, calibration_identity,
                           fit_calibration)
from hte.demo import fixtures, synthetic_config
from hte.io import read_csv, read_json, write_csv


ROOT = Path(__file__).resolve().parents[2]


def naphthalene_calibration():
    config = synthetic_config(ROOT / "hte_inputs/campaign.json")
    config["schema_version"] = 6
    config["analytics"]["internal_standard"] = "naphthalene"
    config["chemistry"]["preloaded_internal_standard"].update(
        identity="naphthalene", cas="91-20-3", smiles="c1ccc2ccccc2c1",
        molecular_weight_g_mol=128.17)
    calibration, _ = fixtures(config, [])
    identity = calibration_identity(config)
    for row in calibration:
        row.update(identity)
    return config, calibration


@pytest.mark.parametrize("fault", ["unlabelled", "mesitylene", "wrong_cas", "mixed_check"])
def test_legacy_or_mixed_internal_standard_calibration_is_rejected(fault):
    config, rows = naphthalene_calibration()
    if fault == "unlabelled":
        for row in rows:
            row.pop("internal_standard_identity")
            row.pop("internal_standard_cas")
    elif fault == "mesitylene":
        for row in rows:
            row.update(internal_standard_identity="mesitylene", internal_standard_cas="108-67-8")
    elif fault == "wrong_cas":
        rows[0]["internal_standard_cas"] = "108-67-8"
    else:
        next(row for row in rows if row["role"] == "check")["internal_standard_identity"] = "mesitylene"
    with pytest.raises(ValueError, match="acquire a fresh calibration"):
        fit_calibration(config, rows)


def test_reaction_and_analytical_identity_must_agree():
    config, rows = naphthalene_calibration()
    config["analytics"]["internal_standard"] = "mesitylene"
    with pytest.raises(ValueError, match="matching reaction/analytical"):
        fit_calibration(config, rows)


@pytest.mark.parametrize("legacy_plan", [False, True])
def test_calibration_publication_preserves_identity_and_rejects_old_plan(tmp_path, legacy_plan):
    config, rows = naphthalene_calibration()
    peaks = []
    for row in rows:
        for analyte, area in ((row["analyte"], row["area"]),
                              ("internal_standard", row["internal_standard_area"])):
            peaks.append({"sample_id": row["sample_id"], "area": area,
                          "retention_time_min": config["analytics"]["references"][analyte]["retention_time_min"],
                          "channel": row["channel"], "method_id": row["method_id"], "qc_flag": "ok"})
    if legacy_plan:
        for row in rows:
            row.update(internal_standard_identity="mesitylene", internal_standard_cas="108-67-8")
    write_csv(tmp_path / "peaks.csv", peaks)
    write_csv(tmp_path / "plan.csv", rows)
    output = tmp_path / "calibration.csv"
    if legacy_plan:
        with pytest.raises(ValueError, match="Do not relabel legacy"):
            calibration_from_peaks(config, tmp_path / "peaks.csv", tmp_path / "plan.csv", output)
        assert not output.exists()
    else:
        calibration_from_peaks(config, tmp_path / "peaks.csv", tmp_path / "plan.csv", output)
        identity = calibration_identity(config)
        assert all({key: row[key] for key in identity} == identity for row in read_csv(output))
        assert read_json(str(output) + ".inputs.json")["calibration_identity"] == identity


def test_quantification_report_identifies_the_standard(tmp_path):
    config, calibration = naphthalene_calibration()
    dose = {"sample_id": "IS-AUDIT", "round": 1, "well": "A1", "kind": "pair",
            "pair_id": "L01__L02", "ligand_a": "L01", "ligand_b": "L02",
            "reaction_volume_ul": 250, "workup_ul": 500, "aliquot_ul": 20,
            "diluent_ul": 980, "substrate_umol": 25,
            "internal_standard_final_uM": config["analytics"]["internal_standard_final_uM"]}
    _, peaks = fixtures(config, [dose])
    _, report = analyze(config, [dose], peaks, calibration, tmp_path)
    assert report["batch_qc_pass"]
    assert report["calibration_identity"] == {
        "internal_standard_identity": "naphthalene", "internal_standard_cas": "91-20-3"}


def test_generated_pilot_plan_preserves_standard_identity(tmp_path):
    from hte.analytical_practice import prepare
    config, _ = naphthalene_calibration()
    prepare(config, tmp_path)
    identity = calibration_identity(config)
    for filename in ("pilot_plan.csv", "pilot_preparation.csv"):
        rows = read_csv(tmp_path / filename)
        assert len(rows) == 7
        assert all({field: row[field] for field in identity} == identity for row in rows)


@pytest.mark.parametrize("fault", ["unlabelled", "mesitylene", "wrong_cas"])
def test_legacy_pilot_identity_rejected_before_ingestion_or_publication(tmp_path, fault):
    from hte.analytical_practice import prepare, verify
    config, _ = naphthalene_calibration()
    plan = prepare(config, tmp_path / "inputs")
    if fault == "unlabelled":
        for row in plan:
            row.pop("internal_standard_identity")
            row.pop("internal_standard_cas")
    elif fault == "mesitylene":
        for row in plan:
            row.update(internal_standard_identity="mesitylene", internal_standard_cas="108-67-8")
    else:
        plan[0]["internal_standard_cas"] = "108-67-8"
    plan_path = tmp_path / "pilot-plan.csv"
    write_csv(plan_path, plan)
    output = tmp_path / "published"
    # Missing source files are deliberate: identity must fail before any ingestion.
    with pytest.raises(ValueError, match="acquire a fresh calibration"):
        verify(config, [tmp_path / "absent-export.csv"], [tmp_path / "absent-map.csv"],
               tmp_path / "absent-calibration.csv", plan_path, output)
    assert not output.exists()


@pytest.mark.parametrize("fault", ["old_schema", "reaction_mw", "liquid_mw"])
def test_old_schema_and_legacy_molecular_weight_cannot_release_new_campaign(fault):
    from hte.planning import validate_config
    config, _ = naphthalene_calibration()
    if fault == "old_schema":
        config["schema_version"] = 5
    elif fault == "reaction_mw":
        config["chemistry"]["preloaded_internal_standard"]["molecular_weight_g_mol"] = 120.19
    else:
        config["liquids"]["internal_standard_molecular_weight_g_mol"] = 120.19
    with pytest.raises(ValueError, match="schema_version 6|requires naphthalene"):
        validate_config(config)
