"""Spreadsheet parity and stable-input publication at every LC entry point."""
from pathlib import Path

import pytest

import hte.analytics as analytics
from hte.demo import fixtures, synthetic_config
from hte.ingestion import ingest_exports
from hte.io import digest, read_csv, read_json, write_csv


ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def inputs(tmp_path):
    config = synthetic_config(ROOT / "hte_inputs/campaign.json")
    config["analytics"]["export_sheet"] = "Peaks"
    rows = [{"inj_no": 1, "injection_name": "sample", "type": "Unknown",
             "vial_position": 1, "inj_volume(uL)": 2,
             "channel_for_peak_detection": "UV_VIS_1", "number_of_det_peaks": 1,
             "peak_no": 1, "retention_time(min)": 0.4,
             **{f"area_uvvis{i}(AU*min)": 1 for i in range(1, 5)}}]
    mapping = [{"inj_no": 1, "sample_id": "R1-001",
                "method_id": config["analytics"]["method_id"], "vial_position": 1}]
    source = tmp_path / "vendor.csv"
    map_path = tmp_path / "map.csv"
    write_csv(source, rows)
    write_csv(map_path, mapping)
    return config, rows, mapping, source, map_path


def test_htel_xlsx_numeric_identifiers_and_empty_padding_match_csv(inputs, tmp_path):
    from openpyxl import Workbook
    config, rows, _, source, mapping = inputs
    expected = tmp_path / "from-csv.csv"
    analytics.normalize_export(config, source, expected, mapping)
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Peaks"
    sheet.append(list(rows[0]))
    sheet.append(list(rows[0].values()))
    # An Excel table can preserve injection metadata while all peak cells are empty.
    padding = {**rows[0], "peak_no": None, "retention_time(min)": None,
               **{f"area_uvvis{i}(AU*min)": None for i in range(1, 5)}}
    sheet.append(list(padding.values()))
    xlsx = tmp_path / "vendor.xlsx"
    workbook.save(xlsx)
    workbook.close()
    output = tmp_path / "from-xlsx.csv"
    analytics.normalize_export(config, xlsx, output, mapping)
    assert read_csv(output) == read_csv(expected)
    report = read_json(str(output) + ".normalization.json")
    assert report["placeholder_rows_omitted"] == 1
    assert report["source_sha256"] == digest(xlsx)


def test_injection_aliases_cannot_map_the_same_number_twice(inputs, tmp_path):
    config, _, mapping, source, map_path = inputs
    mapping.append({**mapping[0], "inj_no": "01", "sample_id": "R1-002"})
    write_csv(map_path, mapping)
    with pytest.raises(ValueError, match="unique positive inj_no"):
        analytics.normalize_export(config, source, tmp_path / "out.csv", map_path)


@pytest.mark.parametrize("number", [0, -1, 1.5, "NaN", True])
def test_invalid_numeric_injection_identifiers_are_rejected(inputs, number):
    config, rows, _, _, mapping = inputs
    rows[0]["inj_no"] = number
    with pytest.raises(ValueError):
        analytics.normalize_chromeleon(config, rows, mapping)


def mutate_after_read(monkeypatch, target):
    original = analytics.read_csv

    def changed(path):
        rows = original(path)
        if Path(path) == target:
            target.write_bytes(target.read_bytes() + b"\n")
        return rows

    monkeypatch.setattr(analytics, "read_csv", changed)


@pytest.mark.parametrize("role", ["export", "mapping"])
def test_normalization_cannot_certify_a_file_replaced_after_reading(inputs, tmp_path, monkeypatch, role):
    config, _, _, source, mapping = inputs
    mutate_after_read(monkeypatch, source if role == "export" else mapping)
    output = tmp_path / "out.csv"
    with pytest.raises(ValueError, match="changed during normalization"):
        analytics.normalize_export(config, source, output, mapping)
    assert not output.exists()
    assert not Path(str(output) + ".normalization.json").exists()


@pytest.mark.parametrize("role", ["peaks", "plan", "reviews"])
def test_calibration_cannot_certify_replaced_inputs(inputs, tmp_path, monkeypatch, role):
    config = inputs[0]
    calibration, _ = fixtures(config, [])
    peaks, reviews = [], []
    for row in calibration:
        for name, area in ((row["analyte"], row["area"]),
                           ("internal_standard", row["internal_standard_area"])):
            if name == row["analyte"] and row["concentration_uM"] == 0:
                reviews.append({"sample_id": row["sample_id"], "analyte": name,
                                "method_id": row["method_id"], "reviewed_by": "synthetic review",
                                "note": "Synthetic absent blank"})
            else:
                peaks.append({"sample_id": row["sample_id"], "area": area,
                              "retention_time_min": config["analytics"]["references"][name]["retention_time_min"],
                              "channel": row["channel"], "method_id": row["method_id"], "qc_flag": "ok"})
    paths = {name: tmp_path / (name + ".csv") for name in ("peaks", "plan", "reviews")}
    write_csv(paths["peaks"], peaks)
    write_csv(paths["plan"], calibration)
    write_csv(paths["reviews"], reviews)
    mutate_after_read(monkeypatch, paths[role])
    output = tmp_path / "calibration.csv"
    with pytest.raises(ValueError, match="Calibration input changed"):
        analytics.calibration_from_peaks(config, paths["peaks"], paths["plan"], output, paths["reviews"])
    assert not output.exists()
    assert not Path(str(output) + ".inputs.json").exists()


@pytest.mark.parametrize("role", ["peaks", "dosing"])
def test_completion_cannot_certify_replaced_inputs(inputs, tmp_path, monkeypatch, role):
    config = inputs[0]
    paths = {name: tmp_path / (name + ".csv") for name in ("peaks", "dosing")}
    write_csv(paths["dosing"], [{"sample_id": "R1-001"}])
    write_csv(paths["peaks"], [{"sample_id": "R1-001", "channel": config["analytics"]["channel"],
                               "method_id": config["analytics"]["method_id"]}])
    mutate_after_read(monkeypatch, paths[role])
    output = tmp_path / "peaks.ready.json"
    with pytest.raises(ValueError, match="changed during completion"):
        analytics.complete_export(config, paths["peaks"], paths["dosing"], output)
    assert not output.exists()


def test_copied_exports_cannot_be_mapped_to_different_reaction_samples(inputs, tmp_path):
    config, _, mapping, source, first_map = inputs
    copied = tmp_path / "copied-vendor.csv"
    copied.write_bytes(source.read_bytes())
    second_map = tmp_path / "second-map.csv"
    write_csv(second_map, [{**mapping[0], "sample_id": "R1-002"}])
    dosing = tmp_path / "dosing.csv"
    write_csv(dosing, [{"sample_id": key} for key in ("R1-001", "R1-002")])
    output = tmp_path / "ingestion"
    with pytest.raises(ValueError, match="identical file content"):
        ingest_exports(config, [source, copied], [first_map, second_map], dosing, output)
    assert not output.exists()
