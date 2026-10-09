from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import re
import tempfile
from contextlib import contextmanager
from pathlib import Path


def finite(value, name, minimum=None, maximum=None):
    if isinstance(value, bool):
        raise ValueError(f"{name}: Boolean is not a number")
    try:
        number = float(value)
    except (ValueError, TypeError):
        raise ValueError(f"{name}: a numeric value is required") from None
    if not math.isfinite(number):
        raise ValueError(f"{name}: must be finite")
    if minimum is not None and number < minimum:
        raise ValueError(f"{name}: must be >= {minimum}")
    if maximum is not None and number > maximum:
        raise ValueError(f"{name}: must be <= {maximum}")
    return number


def read_json(path):
    def reject(value):
        raise ValueError(f"Nonfinite JSON number: {value}")
    def unique(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError(f"Duplicate JSON key: {key}")
            result[key] = value
        return result
    return json.loads(Path(path).read_text(), parse_constant=reject, object_pairs_hook=unique)


def atomic_text(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=".writing-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def write_json(path, data):
    atomic_text(path, json.dumps(data, indent=2, allow_nan=False) + "\n")


def read_csv(path):
    with Path(path).open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if (not reader.fieldnames or any(not name or not name.strip() for name in reader.fieldnames)
                or len(reader.fieldnames) != len(set(reader.fieldnames))):
            raise ValueError("Missing or duplicate CSV headers")
        rows = list(reader)
        if any(None in row or any(value is None for value in row.values()) for row in rows):
            raise ValueError("CSV row field count differs from its header")
        return rows


def write_csv(path, rows, fields=None):
    import io
    rows = list(rows)
    if fields is None:
        fields = list(rows[0]) if rows else []
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fields, extrasaction="raise")
    writer.writeheader()
    writer.writerows(rows)
    atomic_text(path, stream.getvalue())


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def object_digest(data):
    return hashlib.sha256(json.dumps(data, sort_keys=True, allow_nan=False).encode()).hexdigest()


def well_name(value):
    value = str(value).strip().upper()
    if not re.fullmatch(r"[A-H](?:[1-9]|1[0-2])", value):
        raise ValueError(f"Invalid 96-well address: {value}")
    return value


def wells():
    return [f"{row}{col}" for col in range(1, 13) for row in "ABCDEFGH"]


def new_output(path):
    path = Path(path)
    try:
        path.mkdir(parents=True)
    except FileExistsError:
        raise ValueError(f"Output already exists: {path}. Use a new run directory.") from None
    return path


@contextmanager
def file_lock(path):
    """One local process per run; OS releases the lock even after a crash.

    Leave the lock file in place so another process cannot lock a new inode while
    the original is still open. Neither credentials nor inputs are stored here.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+b") as stream:
        if os.name == "nt":
            import msvcrt
            if path.stat().st_size == 0:
                stream.write(b"0")
                stream.flush()
            stream.seek(0)
            try:
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError:
                raise ValueError(f"Another process is already using this run: {path}") from None
            try:
                yield
            finally:
                stream.seek(0)
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            try:
                fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise ValueError(f"Another process is already using this run: {path}") from None
            try:
                yield
            finally:
                fcntl.flock(stream, fcntl.LOCK_UN)
