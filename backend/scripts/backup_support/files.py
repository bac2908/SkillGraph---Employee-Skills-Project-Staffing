import csv
import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path

from scripts.backup_support import BackupError

MAX_FILE_BYTES = 64 * 1024 * 1024
MAX_BUNDLE_BYTES = 2 * MAX_FILE_BYTES + 1024 * 1024


def private_directory(path: Path) -> Path:
    path = path.resolve()
    if path.exists():
        raise BackupError("Output directory must not already exist.")
    path.parent.mkdir(parents=True, exist_ok=True)
    if shutil.disk_usage(path.parent).free < MAX_BUNDLE_BYTES + 64 * 1024 * 1024:
        raise BackupError(
            "Insufficient free disk space for the bounded backup/recovery operation."
        )
    path.mkdir(mode=0o700)
    if os.name == "nt":
        # Restrict only our NEW directory, never the user's existing data folder.
        identity = subprocess.run(
            ["whoami", "/user", "/fo", "csv", "/nh"],
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        sid = next(csv.reader(identity.stdout.strip().splitlines()))[1]
        subprocess.run(
            [
                "icacls",
                str(path),
                "/inheritance:r",
                "/grant:r",
                f"*{sid}:(OI)(CI)F",
                "*S-1-5-18:(OI)(CI)F",
            ],
            check=True,
            capture_output=True,
            timeout=5,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
    return path


def reserve_file(path: Path):
    # Exclusive creation prevents accidental overwrite of data or sidecars.
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    os.close(descriptor)


def json_bytes(value) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def write_json(path: Path, value):
    raw = json_bytes(value)
    if len(raw) > MAX_FILE_BYTES:
        raise BackupError("JSON exceeds the local backup size limit.")
    with path.open("xb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


def load_json(path: Path):
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_FILE_BYTES:
        raise BackupError("Backup file is missing, linked, or exceeds the size limit.")
    with path.open("rb") as stream:
        raw = stream.read(MAX_FILE_BYTES + 1)
    if len(raw) > MAX_FILE_BYTES:
        raise BackupError("Backup file exceeds the size limit.")
    return json.loads(raw)


def file_info(path: Path) -> dict:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_FILE_BYTES:
        raise BackupError("Backup file is missing, linked, or exceeds the size limit.")
    size = 0
    checksum = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            size += len(chunk)
            if size > MAX_FILE_BYTES:
                raise BackupError("Backup file exceeds the size limit.")
            checksum.update(chunk)
    return {"bytes": size, "sha256": checksum.hexdigest()}
