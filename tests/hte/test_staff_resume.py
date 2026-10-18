"""The staff command must retain accepted scores and uncertain-attempt guards."""
import json
import runpy
import sys
from pathlib import Path
from types import SimpleNamespace

import anthropic
import pytest

from hte.demo import fixtures, synthetic_config
from hte.inventory import campaign_inventory
from hte.io import digest, file_lock, read_csv, read_json, write_csv, write_json
from hte.planning import dosing_rows


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/hte-lc-results.py"


@pytest.fixture
def staff_run(tmp_path, monkeypatch):
    config = synthetic_config(ROOT / "hte_inputs/campaign.json")
    config["demo"] = False  # Only the mocked provider below can be constructed.
    config["llm"].update(workers=1, iteration_workers=1, repeats=2)
    inventory = campaign_inventory(ROOT / "hte_inputs/ligands.csv", config)
    doses = dosing_rows(config, inventory, read_csv(ROOT / "campaigns/hackathon2026/round1_design.csv"))
    calibration, peaks = fixtures(config, doses)
    write_json(tmp_path / "config.json", config)
    write_csv(tmp_path / "dosing.csv", doses)
    write_csv(tmp_path / "calibration.csv", calibration)
    rows, mapping = [], []
    for injection, dose in enumerate(doses, 1):
        mapping.append({"inj_no": injection, "sample_id": dose["sample_id"],
                        "method_id": config["analytics"]["method_id"]})
        for index, peak in enumerate([p for p in peaks if p["sample_id"] == dose["sample_id"]], 1):
            rows.append({"inj_no": injection, "injection_name": "fixture", "type": "Unknown",
                         "vial_position": str(injection), "inj_volume(uL)": 2,
                         "channel_for_peak_detection": "UV_VIS_1", "number_of_det_peaks": 3,
                         "peak_no": index, "retention_time(min)": peak["retention_time_min"],
                         **{f"area_uvvis{i}(AU*min)": peak["area"] for i in range(1, 5)}})
    write_csv(tmp_path / "export.csv", rows)
    write_csv(tmp_path / "mapping.csv", mapping)
    calls, fail_on_call = [], []

    class Response:
        model = "OFFLINE_STAFF_RESUME_FIXTURE"
        id = "synthetic_response"
        stop_reason = "end_turn"
        usage = SimpleNamespace(model_dump=lambda: {"input_tokens": 1000, "output_tokens": 50})

        def __init__(self, request):
            schema = request["output_config"]["format"]["schema"]
            self.content = [SimpleNamespace(type="text", text=json.dumps({
                "scores": {key: 50 for key in schema["properties"]["scores"]["required"]}}))]

        def model_dump(self):
            return {"synthetic_only": True}

    class Stream:
        def __init__(self, request):
            self.request = request

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def get_final_message(self):
            return Response(self.request)

    class Client:
        def __init__(self, **kwargs):
            self.models = SimpleNamespace(retrieve=lambda model: None)
            self.messages = self

        def count_tokens(self, **kwargs):
            return SimpleNamespace(input_tokens=1000)

        def stream(self, **kwargs):
            calls.append(kwargs)
            if len(calls) in fail_on_call:
                raise TimeoutError("Synthetic uncertain request")
            return Stream(kwargs)

    monkeypatch.setattr(anthropic, "Anthropic", Client)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "offline_staff_resume_fixture")
    output = tmp_path / "decision"

    def invoke():
        argv = [str(SCRIPT), "next", "--config", str(tmp_path / "config.json"),
                "--dosing", str(tmp_path / "dosing.csv"), "--calibration", str(tmp_path / "calibration.csv"),
                "--exports", str(tmp_path / "export.csv"), "--injections", str(tmp_path / "mapping.csv"),
                "--output", str(output)]
        monkeypatch.setattr(sys, "argv", argv)
        return runpy.run_path(str(SCRIPT), run_name="__main__")

    return SimpleNamespace(root=tmp_path, output=output, invoke=invoke, calls=calls, fail_on_call=fail_on_call)


def test_staff_resumes_after_scoring_without_rebuying_and_completed_replay_is_idempotent(staff_run, monkeypatch):
    import hte.workflow as workflow
    original = workflow.make_design
    attempts = []

    def interrupted_selection(*args, **kwargs):
        attempts.append(1)
        if len(attempts) == 1:
            raise RuntimeError("Synthetic process interruption after accepted scoring")
        return original(*args, **kwargs)

    monkeypatch.setattr(workflow, "make_design", interrupted_selection)
    with pytest.raises(RuntimeError, match="interruption"):
        staff_run.invoke()
    count = len(staff_run.calls)
    assert count > 100
    accepted = next(staff_run.output.glob("decision/iteration-*/scoring/ranking.csv"))
    before = digest(accepted)
    staff_run.invoke()
    assert len(staff_run.calls) == count and digest(accepted) == before
    complete = next(staff_run.output.glob("decision/iteration-*/complete.json"))
    finished = digest(complete)
    staff_run.invoke()
    assert len(staff_run.calls) == count and digest(complete) == finished
    assert len(attempts) == 2


def test_staff_resume_preserves_uncertain_request_stop(staff_run, capsys):
    staff_run.fail_on_call.append(2)
    with pytest.raises(TimeoutError, match="uncertain"):
        staff_run.invoke()
    count = len(staff_run.calls)
    ledger = next(staff_run.output.glob("decision/iteration-*/scoring/budget_ledger.json"))
    before = digest(ledger)
    with pytest.raises(SystemExit) as error:
        staff_run.invoke()
    assert error.value.code == 2
    assert "may have been charged" in capsys.readouterr().err
    assert len(staff_run.calls) == count and digest(ledger) == before


@pytest.mark.parametrize("filename", ["config.json", "export.csv", "mapping.csv", "calibration.csv"])
def test_staff_resume_rejects_changed_source_before_paid_call(staff_run, filename, capsys):
    staff_run.invoke()
    count = len(staff_run.calls)
    source = staff_run.root / filename
    source.write_bytes(source.read_bytes() + b"\n")
    with pytest.raises(SystemExit) as error:
        staff_run.invoke()
    assert error.value.code == 2 and "Inputs changed" in capsys.readouterr().err
    assert len(staff_run.calls) == count


@pytest.mark.parametrize("filename", ["ingestion/peaks.csv", "ingestion/sources/part-01-export.csv",
                                      "inputs/calibration.csv"])
def test_staff_resume_rejects_changed_archive_before_paid_call(staff_run, filename, capsys):
    staff_run.invoke()
    count = len(staff_run.calls)
    archived = staff_run.output / filename
    archived.write_bytes(archived.read_bytes() + b"\n")
    with pytest.raises(SystemExit) as error:
        staff_run.invoke()
    assert error.value.code == 2 and "Archived helper input changed" in capsys.readouterr().err
    assert len(staff_run.calls) == count


def test_staff_concurrent_command_stops_before_provider(staff_run, capsys):
    with file_lock(staff_run.output / ".helper.lock"):
        with pytest.raises(SystemExit) as error:
            staff_run.invoke()
    assert error.value.code == 2 and "Another process" in capsys.readouterr().err
    assert not staff_run.calls


def test_staff_legacy_output_cannot_silently_restart_paid_scoring(staff_run, capsys):
    staff_run.output.mkdir()
    write_json(staff_run.output / "old_scoring.json", {"may_have_been_charged": True})
    with pytest.raises(SystemExit) as error:
        staff_run.invoke()
    assert error.value.code == 2 and "inspect any existing scoring records" in capsys.readouterr().err
    assert not staff_run.calls
