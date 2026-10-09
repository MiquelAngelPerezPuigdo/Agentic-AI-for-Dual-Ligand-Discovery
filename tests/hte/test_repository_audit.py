"""Regression checks for defects found in the full repository review."""
import copy
from pathlib import Path
from types import SimpleNamespace

import anthropic
import pytest

from hte.analytics import (complete_export, fit_calibration, normalize_export,
                           read_completed_inputs)
from hte.demo import run
from hte.design import consensus_select, rank_percentiles, validate_design
from hte.inventory import candidates, load_inventory
from hte.io import file_lock, read_csv, read_json, write_csv
from hte.planning import (dosing_rows, required_validations, schedule,
                          validate_config, validate_dosing)
from hte.protocols import export
from hte.scoring import score_candidates
from hte.workflow import iterate, watch

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def files(tmp_path_factory):
    folder = tmp_path_factory.mktemp("audit")/"demo"
    run(folder, ROOT/"hte_inputs/ligands.csv", ROOT/"hte_inputs/campaign.json")
    return folder


@pytest.fixture
def data(files):
    return (read_json(files/"campaign.json"), load_inventory(ROOT/"hte_inputs/ligands.csv"),
            read_csv(files/"round1/dosing.csv"))


def released_fixture(config):
    """Software fixture only; these names/times are not measured bench settings."""
    config = copy.deepcopy(config)
    config["demo"] = False
    for name in required_validations(config):
        config["validation"][name] = True
    config["analytics"].update(method_id="VALIDATED_TEST_METHOD", channel="VALIDATED_TEST_DAD")
    config["timing"]["dosing_total_minutes"] = 20
    return config


@pytest.mark.parametrize("fault", ["duplicate_pair", "wrong_reference", "missing_reference"])
def test_edited_design_cannot_change_the_campaign(data, fault):
    config, inv, doses = data
    pairs = [row for row in doses if row["kind"] == "pair"]
    reference = next(row for row in doses if row["kind"] == "single")
    if fault == "duplicate_pair":
        for name in ("pair_id", "ligand_a", "ligand_b"):
            pairs[-1][name] = pairs[0][name]
        message = "distinct"
    elif fault == "wrong_reference":
        reference["ligand_a"] = "L01"
        message = "controls differ"
    else:
        reference.update(kind="pair", pair_id="L01__L02", ligand_a="L01", ligand_b="L02", selection_method="llm")
        message = "controls differ"
    with pytest.raises(ValueError, match=message):
        dosing_rows(config, inv, doses)


@pytest.mark.parametrize("field,value", [("substrate_umol", 10), ("pd_ul", 20),
                                         ("reaction_volume_ul", 100), ("internal_standard_final_uM", 25)])
def test_stale_or_edited_doses_cannot_enter_quantification(data, field, value):
    config, inv, doses = data
    doses[0][field] = value
    with pytest.raises(ValueError, match="Dosing value differs"):
        validate_dosing(config, inv, doses)


def test_invalid_dosing_is_rejected_before_any_scoring(files, data, tmp_path, monkeypatch):
    config, inv, doses = data
    config["demo"] = False
    doses[0]["substrate_umol"] = "10"
    write_csv(tmp_path/"dosing.csv", doses)
    complete_export(config, files/"round1_peaks.csv", tmp_path/"dosing.csv", tmp_path/"peaks.ready.json")
    def no_scoring(*args, **kwargs):
        pytest.fail("Invalid doses reached paid scoring")
    monkeypatch.setattr("hte.workflow.score_candidates", no_scoring)
    with pytest.raises(ValueError, match="Dosing value differs"):
        iterate(config, inv, {}, tmp_path/"dosing.csv", files/"round1_peaks.csv",
                tmp_path/"peaks.ready.json", files/"calibration.csv", tmp_path/"iteration")


def test_tied_scores_do_not_create_ligand_id_preferences():
    assert rank_percentiles({"z": 80, "a": 80, "m": 20}) == {"a": 0.75, "z": 0.75, "m": 0.0}
    pairs = [{"pair_id": f"L01__L{i:02d}", "ligand_a": "L01", "ligand_b": f"L{i:02d}"}
             for i in range(2, 6)]
    ranking = [{"pair_id": row["pair_id"], "mean_score": 50, "score_sd": 0} for row in pairs]
    _, trace = consensus_select(pairs, ranking, [[0], [1], [2], [3]], 2)
    assert all(row["llm_percentile"] == 0.5 for row in trace)


@pytest.mark.parametrize("fault", ["missing_method", "missing_loq", "over_deadline", "synthetic_method"])
def test_live_export_requires_analytics_and_a_plan_within_the_deadline(data, fault):
    config = released_fixture(data[0])
    if fault == "missing_method":
        config["analytics"]["method_id"] = None
        message = "Configure LC"
    elif fault == "missing_loq":
        config["analytics"]["quantification_limit_uM"]["product"] = None
        message = "LOQ"
    elif fault == "over_deadline":
        config["timing"]["dosing_total_minutes"] = 30
        message = "deadline"
    else:
        config["analytics"]["method_id"] = "SYNTHETIC_2MIN"
        message = "Synthetic LC"
    with pytest.raises(ValueError, match=message):
        validate_config(config, live=True)


def test_equilibration_cannot_be_omitted_from_timing(data):
    config = data[0]
    config["chemistry"]["thermal_equilibration_minutes"] = 8
    with pytest.raises(ValueError, match="equilibration"):
        schedule(config)


def test_live_round2_export_requires_history_and_excludes_round1_pairs(files, data, tmp_path):
    config, inv, history = data
    config = released_fixture(config)
    second = read_csv(files/"round2_design.csv")
    with pytest.raises(ValueError, match="requires the first-round dosing history"):
        export(config, inv, second, tmp_path/"missing-history", live=True)
    first_pair = next(row for row in history if row["kind"] == "pair")
    for name in ("pair_id", "ligand_a", "ligand_b"):
        second[0][name] = first_pair[name]
    with pytest.raises(ValueError, match="repeats a first-round"):
        export(config, inv, second, tmp_path/"repeated", live=True, history=history)
    assert not (tmp_path/"repeated").exists()


def test_live_round2_export_uses_the_complete_verified_history(files, data, tmp_path):
    config, inv, history = data
    config = released_fixture(config)
    second = read_csv(files/"round2_design.csv")
    export(config, inv, second, tmp_path/"round2", live=True, history=history)
    manifest = read_json(tmp_path/"round2/export_manifest.json")
    assert manifest["live"] and manifest["history_digest"]
    assert {path.name for path in (tmp_path/"round2").iterdir() if path.name != "export_manifest.json"} == set(manifest["files"])
    assert all(float(row["sm_DCM_ul"]) == 0 for row in read_csv(tmp_path/"round2/dosing.csv"))


@pytest.mark.parametrize("fault,message", [("no_check", "independent calibration check"),
    ("no_blank", "zero-analyte"), ("too_few_levels", "5 distinct nonzero"),
    ("duplicate_id", "unique"), ("unknown_analyte", "analyte labels")])
def test_calibration_cannot_silently_skip_the_promised_validation(files, data, fault, message):
    config = data[0]
    rows = read_csv(files/"calibration.csv")
    if fault == "no_check":
        rows = [row for row in rows if row["role"] != "check"]
    elif fault == "no_blank":
        rows = [row for row in rows if float(row["concentration_uM"]) != 0]
    elif fault == "too_few_levels":
        rows = [row for row in rows if float(row["concentration_uM"]) != 100]
    elif fault == "duplicate_id":
        rows[1]["sample_id"] = rows[0]["sample_id"]
    else:
        rows[0]["analyte"] = "Product"
    with pytest.raises(ValueError, match=message):
        fit_calibration(config, rows)


@pytest.mark.parametrize("text", ["a,b\n1\n", "a,b\n1,2,3\n", ",b\n1,2\n"])
def test_malformed_csv_rows_do_not_become_missing_values(tmp_path, text):
    path = tmp_path/"bad.csv"
    path.write_text(text)
    with pytest.raises(ValueError, match="CSV"):
        read_csv(path)


def test_export_never_overwrites_an_interrupted_handoff(data, tmp_path):
    config, inv, doses = data
    folder = tmp_path/"partial"
    folder.mkdir()
    (folder/"dose_and_react.py").write_text("previous partial export")
    with pytest.raises(ValueError, match="already exists"):
        export(config, inv, doses, folder)
    assert (folder/"dose_and_react.py").read_text() == "previous partial export"


def test_files_changed_during_lc_ingestion_are_rejected(files, data, tmp_path, monkeypatch):
    import hte.analytics as analytics
    config, _, _ = data
    peaks = tmp_path/"peaks.csv"
    peaks.write_bytes((files/"round1_peaks.csv").read_bytes())
    original = analytics.read_csv
    def mutate_after_read(path):
        rows = original(path)
        if Path(path) == peaks:
            peaks.write_bytes(peaks.read_bytes()+b"\n")
        return rows
    monkeypatch.setattr(analytics, "read_csv", mutate_after_read)
    with pytest.raises(ValueError, match="changed during ingestion"):
        read_completed_inputs(config, files/"round1/dosing.csv", peaks,
                              files/"round1_peaks.ready.json", files/"calibration.csv")


def test_concurrent_scoring_and_watcher_launches_are_blocked_before_network(data, tmp_path, monkeypatch):
    config, inv, _ = data
    config["demo"] = False
    def no_client(**kwargs):
        pytest.fail("A concurrent launch reached the API")
    monkeypatch.setattr(anthropic, "Anthropic", no_client)
    scoring = tmp_path/"scoring"
    with file_lock(scoring/".scoring.lock"):
        with pytest.raises(ValueError, match="Another process"):
            score_candidates(config, inv, candidates(inv), {}, [], scoring)
    with file_lock(scoring/".scoring.lock"):
        pass  # The previous lock was released.
    watcher = tmp_path/"watcher"
    with file_lock(watcher/".watcher.lock"):
        with pytest.raises(ValueError, match="Another process"):
            watch(config, inv, {}, tmp_path/"inbox", "unused", "unused", watcher, once=True)


def test_an_interrupted_api_request_is_never_automatically_bought_again(data, tmp_path, monkeypatch):
    config, inv, _ = data
    config["demo"] = False
    config["llm"].update(repeats=2, workers=1)
    calls = []
    class Client:
        def __init__(self, **kwargs):
            self.models = SimpleNamespace(retrieve=lambda model: None)
            self.messages = self
        def count_tokens(self, **kwargs):
            return SimpleNamespace(input_tokens=1000)
        def stream(self, **kwargs):
            calls.append(1)
            raise TimeoutError("Synthetic timeout after sending the request")
    monkeypatch.setattr(anthropic, "Anthropic", Client)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "offline_audit_fixture")
    arguments = (config, inv, candidates(inv)[:3], {}, [], tmp_path/"scoring")
    with pytest.raises(TimeoutError):
        score_candidates(*arguments)
    with pytest.raises(ValueError, match="may have been charged"):
        score_candidates(*arguments)
    assert len(calls) == 1


def test_iteration_checks_analysis_and_source_snapshots_on_replay(files, data, tmp_path, monkeypatch):
    config, inv, _ = data
    config["demo"] = False
    calls = []
    def fake_score(cfg, inventory, pairs, evidence, feedback, output):
        calls.append(1)
        return [{"pair_id": row["pair_id"], "mean_score": 50, "score_sd": 0} for row in pairs]
    monkeypatch.setattr("hte.workflow.score_candidates", fake_score)
    args = (config, inv, {}, files/"round1/dosing.csv", files/"round1_peaks.csv",
            files/"round1_peaks.ready.json", files/"calibration.csv", tmp_path)
    folder = iterate(*args)
    (folder/"source_tables.json").write_text("{}\n")
    with pytest.raises(ValueError, match="changed"):
        iterate(*args)
    assert calls == [1]


@pytest.mark.parametrize("extension", ["csv", "xlsx"])
def test_vendor_normalization_preserves_zero_areas_and_verified_metadata(data, tmp_path, extension):
    config = data[0]
    headers = ["Sample", "RT", "Area", "Detector", "Method"]
    row = ["R1-001", 0.9, 0, "SYNTHETIC_UV", "SYNTHETIC_2MIN"]
    config["analytics"].update(column_mapping=dict(zip(
        ["sample_id", "retention_time_min", "area", "channel", "method_id"], headers)), export_sheet="Peaks")
    source = tmp_path/f"vendor.{extension}"
    if extension == "csv":
        write_csv(source, [dict(zip(headers, row))])
    else:
        from openpyxl import Workbook
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Peaks"
        sheet.append(headers)
        sheet.append(row)
        workbook.save(source)
        workbook.close()
    output = tmp_path/"normalized.csv"
    normalize_export(config, source, output)
    normalized = read_csv(output)
    assert normalized[0]["area"] == "0" and normalized[0]["sample_id"] == "R1-001"
    assert normalized[0]["channel"] == config["analytics"]["channel"]


@pytest.mark.parametrize("fault", ["missing_header", "missing_value", "empty_export"])
def test_vendor_normalization_stops_on_incomplete_exports(data, tmp_path, fault):
    config = data[0]
    config["analytics"]["column_mapping"] = {key: key for key in
        ("sample_id", "retention_time_min", "area", "channel", "method_id")}
    rows = [{"sample_id": "R1-001", "retention_time_min": 0.9, "area": 10,
             "channel": "SYNTHETIC_UV", "method_id": "SYNTHETIC_2MIN"}]
    if fault == "missing_header":
        del rows[0]["method_id"]
    elif fault == "missing_value":
        rows[0]["method_id"] = ""
    else:
        rows = []
    source = tmp_path/"vendor.csv"
    write_csv(source, rows, list(config["analytics"]["column_mapping"]) if not rows else None)
    with pytest.raises(ValueError, match="missing|no peak"):
        normalize_export(config, source, tmp_path/"normalized.csv")
    assert not (tmp_path/"normalized.csv").exists()
