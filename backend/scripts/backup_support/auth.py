import hashlib
import json
import sqlite3
from contextlib import closing
from pathlib import Path
from time import monotonic

from app.db.auth_schema import AUTH_COLUMNS
from scripts.backup_support import BackupError
from scripts.backup_support.files import MAX_FILE_BYTES, json_bytes, reserve_file


def connect(path: Path, mode="ro"):
    return sqlite3.connect(
        path.resolve().as_uri() + f"?mode={mode}", uri=True, timeout=0.5
    )


def inspect_auth(path: Path) -> dict:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_FILE_BYTES:
        raise BackupError("Auth database is missing, linked, or too large.")
    deadline = monotonic() + 15
    with closing(connect(path)) as db:
        db.set_progress_handler(lambda: int(monotonic() > deadline), 1000)
        db.execute("PRAGMA trusted_schema = OFF")
        if db.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
            raise BackupError("SQLite integrity check failed.")
        if db.execute("PRAGMA foreign_key_check").fetchone():
            raise BackupError("SQLite foreign-key check failed.")
        objects = set(
            db.execute(
                "SELECT type, name FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'"
            )
        )
        expected = {("table", table) for table in AUTH_COLUMNS} | {
            ("index", "sessions_user")
        }
        if objects != expected:
            raise BackupError(
                "Unsupported auth schema; use a matching application version."
            )
        for table, columns in AUTH_COLUMNS.items():
            db.execute(f"SELECT {columns} FROM {table} LIMIT 0")
        rows = db.execute(
            f"SELECT {AUTH_COLUMNS['users']} FROM users ORDER BY user_id"
        ).fetchall()
        if not any(row[4] == "ADMIN" and row[5] == 1 for row in rows):
            raise BackupError("Auth backup has no active Admin.")
        grants = []
        for row in rows:
            ids = json.loads(row[7])
            if not isinstance(ids, list) or any(
                not isinstance(value, str) for value in ids
            ):
                raise BackupError("Invalid project grants in auth backup.")
            if row[4] == "MANAGER":
                grants.extend(ids)
        return {
            "users": len(rows),
            "users_sha256": hashlib.sha256(json_bytes(rows)).hexdigest(),
            "sessions": db.execute("SELECT count(*) FROM sessions").fetchone()[0],
            "login_limits": db.execute("SELECT count(*) FROM login_limits").fetchone()[
                0
            ],
            "manager_project_ids": grants,
        }


def copy_auth(source: Path, destination: Path, *, revoke_sessions=False):
    if source.resolve() == destination.resolve() or destination.exists():
        raise BackupError("Refusing to overwrite an existing auth database.")
    if any(
        Path(str(destination) + suffix).exists()
        for suffix in ("-wal", "-shm", "-journal")
    ):
        raise BackupError("Auth destination has existing SQLite sidecars.")
    # Online backup includes committed WAL contents; copying the main file does not.
    deadline = monotonic() + 15

    def progress(status, remaining, total):
        if monotonic() > deadline:
            raise BackupError("SQLite backup deadline exceeded.")
        if total * page_size > MAX_FILE_BYTES:
            raise BackupError("Auth database exceeds the local backup size limit.")

    with closing(connect(source)) as src:
        page_size = src.execute("PRAGMA page_size").fetchone()[0]
        if src.execute("PRAGMA page_count").fetchone()[0] * page_size > MAX_FILE_BYTES:
            raise BackupError("Auth database exceeds the local backup size limit.")
        reserve_file(destination)
        with closing(connect(destination, "rw")) as target:
            src.backup(target, pages=128, progress=progress, sleep=0.05)
            target.execute("PRAGMA journal_mode = DELETE")
    original = inspect_auth(destination)
    if revoke_sessions:
        with closing(connect(destination, "rw")) as db:
            db.execute("DELETE FROM sessions")
            db.execute("DELETE FROM login_limits")
            db.commit()
        restored = inspect_auth(destination)
        if (
            restored["users_sha256"] != original["users_sha256"]
            or restored["sessions"]
            or restored["login_limits"]
        ):
            raise BackupError("Restored auth verification failed.")
    return inspect_auth(destination)
