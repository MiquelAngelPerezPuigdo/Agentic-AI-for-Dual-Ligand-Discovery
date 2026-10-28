"""Exercise the staff guide without lab hardware, real credentials or paid calls."""
import importlib.util
import json
from pathlib import Path

import pytest

from hte.io import digest, read_json, write_json
from hte.planning import required_validations


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("hte_operator_guide", ROOT / "scripts/hte-guide.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


@pytest.fixture
def local_project(tmp_path):
    for name in ("hte", "hte_inputs", "campaigns"):
        (tmp_path / name).symlink_to(ROOT / name, target_is_directory=True)
    (tmp_path / "anthropic.key.example").write_text("PASTE_YOUR_ANTHROPIC_API_KEY_HERE\n")
    return tmp_path


def answers(*items):
    iterator = iter(items)
    return lambda prompt: next(iterator)


def test_setup_preserves_existing_config_calibration_and_key(local_project):
    guide = MODULE.Guide(local_project, say=lambda *a: None)
    guide.setup()
    config = local_project / "local_data/campaign.json"
    calibration = local_project / "local_data/calibration-plan.csv"
    key = local_project / "anthropic.key"
    key.write_text("private test sentinel")
    before = (config.read_bytes(), calibration.read_bytes(), key.read_bytes())
    guide.setup()
    assert before == (config.read_bytes(), calibration.read_bytes(), key.read_bytes())


def test_round_two_retry_uses_the_same_files_and_output(local_project):
    export = local_project / "export.csv"; export.write_text("test")
    mapping = local_project / "map.csv"; mapping.write_text("test")
    guide = MODULE.Guide(local_project, say=lambda *a: None)
    guide.setup()
    dosing = local_project / "output/r1-dose/dosing.csv"; dosing.parent.mkdir(parents=True); dosing.write_text("test")
    (local_project / "local_data/calibration.csv").write_text("test")
    calls = []
    guide.run = lambda *args: calls.append(args) or True
    for _ in range(2):
        guide.ask = answers(str(export), str(mapping), "n")
        guide.next_round()
    assert calls[0] == calls[1]
    assert calls[0][-2:] == ("--output", "output/r1-decision")
    assert "--exports" in calls[0] and "--injections" in calls[0]


def test_settings_record_only_explicit_local_checks(local_project):
    output = []
    guide = MODULE.Guide(local_project, ask=answers("REAL_METHOD", "1", "", "", "", "n", "n"), say=lambda *a: output.append(a))
    guide.setup()
    before = read_json(guide.config)
    guide.settings()
    after = read_json(guide.config)
    assert after["analytics"]["method_id"] == "REAL_METHOD"
    assert after["analytics"]["channel"] == "UV_VIS_1"
    assert after["validation"] == before["validation"]
    assert (local_project / "anthropic.key").read_text().startswith("PASTE_YOUR_")


def test_measured_cycle_and_residual_are_saved_before_stock_preparation(local_project):
    guide = MODULE.Guide(local_project, ask=answers("REAL_METHOD", "2", "", "2.1", "550", "n", "n"), say=lambda *a: None)
    guide.setup(); guide.settings()
    config = read_json(guide.config)
    assert config["timing"]["injection_cycle_minutes"] == 2.1
    assert config["automation"]["bulk_dead_ul"] == 550
    saved = guide.config.read_bytes()
    manifest = local_project / "local_data/stock-prep/preparation_manifest.json"
    manifest.parent.mkdir(parents=True); manifest.write_text("{}")
    guide.ask = answers("", "", "", "", "600")
    with pytest.raises(ValueError, match="already recorded"):
        guide.settings()
    assert guide.config.read_bytes() == saved


def test_preview_really_generates_safe_stock_protocol_without_masses(local_project):
    guide = MODULE.Guide(local_project, say=lambda *a: None)
    guide.setup()
    guide.prepare()
    out = local_project / "output/prep-preview"
    manifest = read_json(out / "preparation_manifest.json")
    assert manifest["weighing_basis"] == "nominal_target" and not manifest["live_export"]
    assert (out / "prepare_stocks.py").is_file() and (out / "bulk_carriers.csv").is_file()
    assert (local_project / "output/r1-preview/dose_and_react.py").is_file()
    assert (local_project / "output/r1-preview/workup.py").is_file()
    assert not (out / "weighed_charges_template.csv").exists()
    before = digest(out / "preparation_manifest.json")
    guide.prepare()  # Never overwrites an existing run.
    assert digest(out / "preparation_manifest.json") == before


def test_guide_generates_live_stock_and_r1_files_without_mass_entry(local_project):
    guide = MODULE.Guide(local_project, say=lambda *a: None)
    guide.setup()
    config = read_json(guide.config)
    config["analytics"]["method_id"] = "TEST_ONLY_METHOD"
    for key in required_validations(config):
        config["validation"][key] = True  # Fictional test fixture; never a physical sign-off.
    write_json(guide.config, config)
    guide.prepare(live=True)
    guide.r1("dose_and_react")
    assert (local_project / "local_data/stock-prep/prepare_stocks.py").is_file()
    assert (local_project / "output/r1-dose/dose_and_react.py").is_file()
    assert not (local_project / "local_data/charges.csv").exists()


def test_unfinished_paid_decision_locks_settings_and_completed_output_is_checked(local_project):
    guide = MODULE.Guide(local_project, ask=lambda prompt: pytest.fail("Must not ask to edit"), say=lambda *a: None)
    guide.setup()
    folder = local_project / "output/r1-decision/decision/iteration-test"
    folder.mkdir(parents=True)
    before = guide.config.read_bytes()
    guide.settings()
    assert guide.config.read_bytes() == before
    design = folder / "next_design.csv"
    design.write_text("pair_id\nL01__L02\n")
    (folder / "complete.json").write_text(json.dumps({"output_sha256": {"next_design.csv": digest(design)}}))
    assert guide.decision() == folder
    design.write_text("changed\n")
    with pytest.raises(ValueError, match="changed or disappeared"):
        guide.decision()


def test_lc_inputs_with_spaces_are_passed_as_distinct_files(local_project):
    first = local_project / "LC export.csv"; first.write_text("export")
    mapping = local_project / "LC map.csv"; mapping.write_text("map")
    guide = MODULE.Guide(local_project, ask=answers(str(first), str(mapping), "n"), say=lambda *a: None)
    exports, maps = guide.input_pairs(1)
    assert exports == [str(first)] and maps == [str(mapping)]


def test_final_analysis_rejects_dosing_from_another_decision(local_project):
    guide = MODULE.Guide(local_project, ask=lambda prompt: pytest.fail("Must stop before asking for LC files"), say=lambda *a: None)
    guide.setup()
    folder = local_project / "output/r1-decision/decision/iteration-test"
    folder.mkdir(parents=True)
    design = folder / "next_design.csv"; design.write_text("pair_id\nL01__L02\n")
    expected = folder / "next_dosing.csv"; expected.write_text("sample_id,pair_id\nR2-001,L01__L02\n")
    (folder / "complete.json").write_text(json.dumps({"output_sha256": {
        "next_design.csv": digest(design), "next_dosing.csv": digest(expected)}}))
    other = local_project / "output/r2-live/dosing.csv"; other.parent.mkdir(parents=True)
    other.write_text("sample_id,pair_id\nR2-001,L01__L03\n")
    with pytest.raises(ValueError, match="differs from the completed decision"):
        guide.final()
