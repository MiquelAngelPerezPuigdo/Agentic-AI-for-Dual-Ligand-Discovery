"""Knowledge transfer must survive moved inputs without losing files or sharing keys."""
import hashlib
import json
import zipfile
from pathlib import Path

import pytest

from hte.io import read_json
from hte.transfer import copy_verified, return_package, snapshot_settings


@pytest.fixture
def campaign(tmp_path):
    root = tmp_path / "handoff"
    for folder in ("hte", "local_data/robot_logs", "local_data/instrument_raw", "output/r1-decision"):
        (root / folder).mkdir(parents=True, exist_ok=True)
    (root / "README.md").write_text("Source snapshot without a Git checkout\n")
    (root / "hte/fixture.py").write_text("print('offline')\n")
    for path, data in {
        "local_data/calibration.csv": b"analyte,concentration\nproduct,50\n",
        "local_data/robot_logs/run.json": b'{"status":"completed"}',
        "local_data/instrument_raw/sample.raw/trace.bin": b"raw bytes\x00\xff",
        "local_data/run-notes.txt": b"Actual stock masses, timestamps and deviations\n",
        "output/r1-decision/prompt.txt": b"score these ligand partners\n",
        "output/r1-decision/response.json": b'{"L01-L02":80}',
        "output/r1-decision/next_dosing.csv": b"sample_id\nR2-001\n",
    }.items():
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    return root


def package(root):
    return return_package(root, root / "local_data", [root / "output"], root / "transfer/results.zip")


def test_return_archive_round_trip_hashes_raw_directory_and_no_git(campaign):
    report = package(campaign)
    assert report["external_records_present"] == dict(robot_logs=True, instrument_raw=True, run_notes=True)
    with zipfile.ZipFile(campaign / "transfer/results.zip") as archive:
        assert archive.testzip() is None
        saved = json.loads(archive.read("TRANSFER_MANIFEST.json"))
        assert saved == report
        for name, metadata in saved["files"].items():
            data = archive.read(name)
            assert hashlib.sha256(data).hexdigest() == metadata["sha256"]
            assert len(data) == metadata["bytes"]
            original = campaign / name.removeprefix("source/")
            assert data == original.read_bytes()
        assert "local_data/instrument_raw/sample.raw/trace.bin" in archive.namelist()
    before = (campaign / "transfer/results.zip").read_bytes()
    with pytest.raises(ValueError, match="already exists"):
        package(campaign)
    assert (campaign / "transfer/results.zip").read_bytes() == before


def test_archive_skips_credentials_and_symlinks_without_reading_them(campaign):
    secret_paths = ("anthropic.key", "local_data/.env", "local_data/backup.key.txt", "output/secrets.json")
    for name in secret_paths:
        (campaign / name).write_bytes(b"sk-ant-" + b"private" * 10)
    (campaign / "output/link.txt").symlink_to(campaign / "anthropic.key")
    report = package(campaign)
    assert not any(".key" in name or name.endswith(".env") for name in report["files"])
    assert "output/link.txt" in report["excluded"]
    assert "output/secrets.json" in report["excluded"]


def test_renamed_key_blocks_archive_and_removes_incomplete_zip(campaign):
    (campaign / "local_data/accident.txt").write_bytes(b"sk-ant-" + b"private" * 10)
    with pytest.raises(ValueError, match="Possible Claude key") as error:
        package(campaign)
    assert "private" not in str(error.value)
    assert list((campaign / "transfer").iterdir()) == []


def test_missing_external_records_are_reported_not_claimed_complete(campaign):
    import shutil
    shutil.rmtree(campaign / "local_data/robot_logs")
    shutil.rmtree(campaign / "local_data/instrument_raw")
    (campaign / "local_data/run-notes.txt").unlink()
    report = package(campaign)
    assert report["external_records_present"] == dict(robot_logs=False, instrument_raw=False, run_notes=False)


def test_archive_rejects_recursive_destination_and_overlapping_run_roots(campaign):
    with pytest.raises(ValueError, match="outside"):
        return_package(campaign, campaign / "local_data", [campaign / "output"], campaign / "output/self.zip")
    with pytest.raises(ValueError, match="overlap"):
        return_package(campaign, campaign / "local_data", [campaign / "output", campaign / "output/r1-decision"],
                       campaign / "transfer/results.zip")


def test_settings_snapshot_retains_effective_config_and_calibration(campaign):
    config = {"analytics": {"method_id": "TEST-METHOD"}}
    source = campaign / "local_data/calibration.csv"
    original = source.read_bytes()
    output = campaign / "output/r1-decision/inputs"
    saved = snapshot_settings(campaign, output, config, [{"id": "L01"}], {"yield": 50}, source)
    source.write_text("later edit\n")
    config["analytics"]["method_id"] = "LATER-EDIT"
    assert saved.read_bytes() == original
    settings = read_json(output / "settings.json")
    assert settings["config"]["analytics"]["method_id"] == "TEST-METHOD"
    assert settings["evidence"] == {"yield": 50}
    assert settings["software"]["python"]
    with pytest.raises(ValueError, match="changed"):
        copy_verified(source, output / "invalid.csv", hashlib.sha256(original).hexdigest())
    assert not (output / "invalid.csv").exists()


def test_changed_file_during_packaging_cannot_publish_an_archive(campaign, monkeypatch):
    import hte.transfer
    original = hte.transfer._stream_digest
    def change(path):
        if path.name == "next_dosing.csv":
            path.write_text("edited after being archived\n")
        return original(path)
    monkeypatch.setattr(hte.transfer, "_stream_digest", change)
    with pytest.raises(ValueError, match="changed during packaging"):
        package(campaign)
    assert not (campaign / "transfer/results.zip").exists()
