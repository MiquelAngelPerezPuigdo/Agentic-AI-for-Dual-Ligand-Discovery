"""Self-contained run inputs and a private, credential-free return archive."""
from __future__ import annotations

import hashlib
import importlib.metadata
import json
import os
import platform
import re
import subprocess
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from .io import digest, write_json

SOURCE_PATHS = ("hte", "hte_inputs", "campaigns", "docs", "scripts", "tests", ".github",
                "README.md", "LICENSE", "pyproject.toml", "uv.lock", ".gitignore", ".gitattributes",
                "software_validation.json", "anthropic.key.example")
TOKEN = re.compile(rb"sk-ant-[A-Za-z0-9_-]{20,}")
FAKE_TOKEN = b"sk-ant-SYNTHETIC_KEY_FILE_FIXTURE"
PACKAGES = ("catalyst-hte", "anthropic", "numpy", "rdkit", "opentrons", "openpyxl", "pypdf")


def software_record(root):
    """Record the local source revision and installed versions, never the environment."""
    record = {"created_utc": datetime.now(timezone.utc).isoformat(),
              "python": platform.python_version(), "platform": platform.platform(), "versions": {}}
    for name in PACKAGES:
        try:
            record["versions"][name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            pass
    try:
        def git(*args):
            return subprocess.check_output(["git", "-C", str(root), *args],
                                           stderr=subprocess.DEVNULL, timeout=10).decode().strip()
        if Path(git("rev-parse", "--show-toplevel")).resolve() == Path(root).resolve():
            record.update(git_commit=git("rev-parse", "HEAD"),
                          git_tracked_changes=bool(git("status", "--porcelain", "--untracked-files=no")))
    except (OSError, subprocess.SubprocessError):
        pass  # The standalone HTE handoff intentionally works without Git.
    return record


def copy_verified(source, destination, expected=None):
    """Save exact input bytes; a changing source cannot produce a valid snapshot."""
    source, destination = Path(source), Path(destination)
    expected = expected or digest(source)
    data = source.read_bytes()
    if hashlib.sha256(data).hexdigest() != expected or digest(source) != expected:
        raise ValueError(f"Input changed while being archived: {source}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(data)
    return {"source": str(source), "sha256": expected}


def snapshot_settings(root, output, config, inventory, evidence, calibration):
    """Persist effective settings even if the operator later edits local_data."""
    output = Path(output)
    write_json(output / "settings.json", {"config": config, "inventory": inventory,
                                         "evidence": evidence, "software": software_record(root)})
    saved = output / "calibration.csv"
    provenance = copy_verified(calibration, saved)
    write_json(output / "calibration.inputs.json", provenance)
    return saved


def _excluded(path):
    name = path.name.lower()
    if name == "anthropic.key.example":
        return False
    return (path.is_symlink() or name == ".ds_store" or name.endswith((".pyc", ".pyo", ".pem", ".key"))
            or ".key." in name or name.startswith((".env", "credentials", "secrets", ".writing-"))
            or name in {".iteration.lock", ".watcher.lock"})


def _files(folder):
    if folder.is_symlink():
        yield folder
    elif folder.is_file():
        yield folder
    else:
        for child in sorted(folder.iterdir()):
            if child.name in {".git", ".venv", "__pycache__", ".pytest_cache"}:
                continue
            yield from _files(child)


def _stream_digest(path):
    checksum = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            checksum.update(chunk)
    return checksum.hexdigest()


def return_package(root, data, runs, destination):
    """Bundle code, local data and run outputs; include large raw-file directories.

    Run only when writers have stopped. No API or robot connection is made. An
    existing archive is never overwritten; incomplete temporary archives are removed.
    """
    root, data, destination = Path(root).resolve(), Path(data).resolve(), Path(destination).resolve()
    runs = [Path(path).resolve() for path in runs]
    if destination.exists():
        raise ValueError("Return archive already exists; choose a new filename")
    for folder in [data, *runs]:
        if not folder.is_dir():
            raise ValueError(f"Missing data/run directory: {folder}")
        if destination.is_relative_to(folder):
            raise ValueError("Place the return archive outside local_data and the run directories")
    for index, folder in enumerate([data, *runs]):
        if any(folder.is_relative_to(other) or other.is_relative_to(folder)
               for other in [data, *runs][index+1:]):
            raise ValueError("Data/run directories must not overlap")
    selected = [(root / name, "source/" + name) for name in SOURCE_PATHS if (root / name).exists()]
    selected.append((data, "local_data"))
    selected.extend((path, path.relative_to(root).as_posix() if path.is_relative_to(root)
                     else f"runs/{index:02d}-{path.name}") for index, path in enumerate(runs, 1))
    files, excluded = {}, []
    for path, prefix in selected:
        for source in _files(path):
            name = prefix if path.is_file() else prefix + "/" + source.relative_to(path).as_posix()
            if _excluded(source):
                excluded.append(name)
                continue
            if name in files:
                raise ValueError("Duplicate archive entry: " + name)
            files[name] = source
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".hte-transfer-", suffix=".zip", dir=destination.parent)
    os.close(fd)
    try:
        records = {}
        with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6,
                             allowZip64=True) as archive:
            for name, source in sorted(files.items()):
                checksum, size, tail = hashlib.sha256(), 0, b""
                before = source.stat()
                with source.open("rb") as stream, archive.open(name, "w", force_zip64=True) as target:
                    while chunk := stream.read(1024 * 1024):
                        # Also catch a key pasted into a renamed text file. Never print the token.
                        scan = (tail + chunk).replace(FAKE_TOKEN, b"")
                        if TOKEN.search(scan):
                            raise ValueError("Possible Claude key in " + name + "; remove it before sharing")
                        tail = (tail + chunk)[-256:]
                        checksum.update(chunk)
                        size += len(chunk)
                        target.write(chunk)
                after = source.stat()
                if (before.st_size, before.st_mtime_ns, before.st_ino) != (after.st_size, after.st_mtime_ns, after.st_ino):
                    raise ValueError("File changed during packaging: " + name + "; stop writers and retry")
                records[name] = {"sha256": checksum.hexdigest(), "bytes": size}
            # Catch additions/removals and late changes while the rest of the archive was written.
            current = {prefix if path.is_file() else prefix + "/" + source.relative_to(path).as_posix()
                       for path, prefix in selected for source in _files(path) if not _excluded(source)}
            if current != set(files):
                raise ValueError("Files added or removed during packaging; stop writers and retry")
            for name, source in files.items():
                if not source.is_file() or _stream_digest(source) != records[name]["sha256"]:
                    raise ValueError("File changed during packaging: " + name + "; stop writers and retry")
            external = {"robot_logs": any(name.startswith("local_data/robot_logs/") for name in files),
                        "instrument_raw": any(name.startswith("local_data/instrument_raw/") for name in files),
                        "run_notes": "local_data/run-notes.txt" in files}
            manifest = {"schema_version": 1, "software": software_record(root),
                        "contents": "Source snapshot, local_data and selected output folders; not proof of experimental completion",
                        "external_records_present": external, "excluded": sorted(excluded), "files": records}
            archive.writestr("TRANSFER_MANIFEST.json", json.dumps(manifest, indent=2) + "\n")
            archive.writestr("TRANSFER_README.txt", "PRIVATE HTE RETURN PACKAGE\n\n"
                "source/ contains the code, inputs, frozen first batch and operating instructions.\n"
                "local_data/ contains local settings, standards, original exports and supplied external records.\n"
                "output/ (or runs/) contains generated protocols, yields/QC and Claude decision records.\n"
                "The manifest lists SHA-256 hashes and external-record presence; it does not certify a complete experiment.\n"
                "Robot JSON logs, raw LC/MS files and run notes must be copied from the instruments by staff.\n"
                "Credentials are excluded. Do not upload this experimental archive to the public repository.\n\n"
                "To replay, extract, copy local_data and output alongside source/ contents, and follow\n"
                "docs/start-here.md. Keep original outputs; use new output directories for reanalysis.\n"
                "Claude responses/ranking are saved: they can be inspected without another paid request.\n")
        # Exclusive creation also prevents a second process silently replacing this package.
        os.link(temporary, destination)
    finally:
        Path(temporary).unlink(missing_ok=True)
    return manifest
