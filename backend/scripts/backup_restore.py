"""Bounded local backup and isolated restore drill. Never replaces the live DBs."""

import argparse
import json
import os
from datetime import UTC, datetime
from pathlib import Path

from dotenv import dotenv_values

from scripts.backup_support import BackupError
from scripts.backup_support.auth import copy_auth, inspect_auth
from scripts.backup_support.files import (
    file_info,
    load_json,
    private_directory,
    write_json,
)
from scripts.backup_support.graph import (
    endpoint_fingerprint,
    export_graph,
    graph_summary,
    make_driver,
    restore_graph,
)

FORMAT_VERSION = 1
BACKEND = Path(__file__).resolve().parents[1]


def now():
    return datetime.now(UTC).isoformat()


def guard_auth_output(output: Path):
    # Works even without valid graph configuration during disaster recovery.
    configured = os.environ.get("AUTH_DB_PATH") or dotenv_values(BACKEND / ".env").get(
        "AUTH_DB_PATH"
    )
    live = (
        Path(configured).resolve() if configured else BACKEND / "data" / "auth.sqlite3"
    )
    target = output.resolve()
    if live == target or live.is_relative_to(target):
        raise BackupError("Refusing an output directory containing the live auth path.")


def verify_bundle(directory: Path):
    directory = directory.resolve()
    manifest = load_json(directory / "manifest.json")
    if (
        not isinstance(manifest, dict)
        or manifest.get("format") != "skillgraph-logical-backup"
        or manifest.get("version") != FORMAT_VERSION
        or manifest.get("complete") is not True
    ):
        raise BackupError("Incomplete or unsupported backup manifest.")
    files = manifest.get("files", {})
    if not isinstance(files, dict) or set(files) != {"graph.json", "auth.sqlite3"}:
        raise BackupError("Unexpected files in backup manifest.")
    for name in files:
        if file_info(directory / name) != files[name]:
            raise BackupError("Backup checksum/size mismatch. Refusing recovery.")
    graph = load_json(directory / "graph.json")
    if graph_summary(graph) != manifest.get("graph"):
        raise BackupError("Graph logical checksum/count mismatch.")
    auth = inspect_auth(directory / "auth.sqlite3")
    if {key: auth[key] for key in ("users", "users_sha256")} != manifest.get("auth"):
        raise BackupError("Auth logical checksum/count mismatch.")
    project_ids = {
        n["properties"]["project_id"]
        for n in graph["nodes"]
        if n["labels"] == ["Project"]
    }
    missing_grants = len(set(auth["manager_project_ids"]) - project_ids)
    return manifest, graph, {"missing_manager_project_grants": missing_grants}


def backup(directory: Path, *, writes_paused: bool):
    from app.core.config import settings

    if not writes_paused:
        raise BackupError(
            "Pause the backend and all direct graph writers, then explicitly pass --writes-paused."
        )
    # Validate configuration/source existence before creating any output.
    identity = endpoint_fingerprint(settings.cognodb_uri)
    if not settings.auth_db_path.is_file():
        raise BackupError(
            "Live auth database does not exist. Refusing an incomplete backup."
        )
    started = now()
    output = private_directory(directory)
    with make_driver(
        settings.cognodb_uri, settings.cognodb_user, settings.cognodb_password
    ) as driver:
        graph = export_graph(driver)
    write_json(output / "graph.json", graph)
    auth = copy_auth(settings.auth_db_path, output / "auth.sqlite3")
    manifest = {
        "format": "skillgraph-logical-backup",
        "version": FORMAT_VERSION,
        "complete": True,
        "started_at": started,
        "finished_at": now(),
        "consistency": "operator-confirmed-writers-paused",
        "source_endpoint_sha256": identity,
        "graph": graph_summary(graph),
        "auth": {key: auth[key] for key in ("users", "users_sha256")},
        "files": {
            name: file_info(output / name) for name in ("graph.json", "auth.sqlite3")
        },
    }
    write_json(output / "manifest.json", manifest)  # Completion marker written last.
    _, _, warnings = verify_bundle(output)
    return {
        "status": "verified",
        "backup": str(output),
        "graph": manifest["graph"],
        "users": auth["users"],
        "warnings": warnings,
    }


def restore_auth_only(directory: Path, output: Path):
    manifest, _, warnings = verify_bundle(directory)
    guard_auth_output(output)
    target = private_directory(output)
    restored = copy_auth(
        directory / "auth.sqlite3", target / "auth.sqlite3", revoke_sessions=True
    )
    if restored["users_sha256"] != manifest["auth"]["users_sha256"]:
        raise BackupError("Restored users do not match the verified backup.")
    report = {
        "status": "auth_verified_graph_not_restored",
        "checked_at": now(),
        "users": restored["users"],
        "sessions": restored["sessions"],
        "warnings": warnings,
    }
    write_json(target / "restore-report.json", report)
    return {**report, "output": str(target)}


def restore(
    directory: Path, output: Path, target_env: Path, *, confirm_empty_target: bool
):
    from app.core.config import settings

    if not confirm_empty_target:
        raise BackupError(
            "Use a dedicated empty instance and explicitly pass --confirm-empty-target."
        )
    manifest, graph, warnings = verify_bundle(directory)
    if target_env.resolve() == (BACKEND / ".env").resolve():
        raise BackupError(
            "Refusing to use the live environment file as restore target."
        )
    if not target_env.is_file():
        raise BackupError("Restore environment file is missing.")
    config = dotenv_values(target_env, interpolate=False)
    uri, user, password = (
        config.get(key) for key in ("COGNODB_URI", "COGNODB_USER", "COGNODB_PASSWORD")
    )
    if not uri or not user or not password:
        raise BackupError(
            "Fill the dedicated test instance values in .env.restore locally."
        )
    identity = endpoint_fingerprint(uri)
    if identity in {
        manifest.get("source_endpoint_sha256"),
        endpoint_fingerprint(settings.cognodb_uri),
    }:
        raise BackupError(
            "Restore target matches a source/live endpoint. Refusing to continue."
        )
    # Graph import has its own empty check before schema and again in transaction.
    # No file/URI in this command ever switches the running application's config.
    guard_auth_output(output)
    if settings.auth_db_path.resolve().is_relative_to(output.resolve()):
        raise BackupError("Refusing to write under the configured live auth path.")
    target = private_directory(output)
    auth = copy_auth(
        directory / "auth.sqlite3", target / "auth.sqlite3", revoke_sessions=True
    )
    if auth["users_sha256"] != manifest["auth"]["users_sha256"]:
        raise BackupError("Restored users do not match the verified backup.")
    with make_driver(uri, user, password) as driver:
        restore_graph(driver, graph)
    report = {
        "status": "restore_verified",
        "checked_at": now(),
        "target_endpoint_sha256": identity,
        "graph": graph_summary(graph),
        "users": auth["users"],
        "sessions": auth["sessions"],
        "warnings": warnings,
        "source_backup_finished_at": manifest["finished_at"],
    }
    write_json(target / "restore-report.json", report)
    return {**report, "output": str(target)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    create = commands.add_parser(
        "backup", help="Pause all writers first; creates a NEW private directory"
    )
    create.add_argument("--output", type=Path, required=True)
    create.add_argument("--writes-paused", action="store_true")
    verify = commands.add_parser(
        "verify", help="Offline checksum, schema and integrity verification"
    )
    verify.add_argument("--backup", type=Path, required=True)
    for name in ("restore-auth", "restore"):
        command = commands.add_parser(
            name, help="Isolated recovery only; output must not exist"
        )
        command.add_argument("--backup", type=Path, required=True)
        command.add_argument("--output", type=Path, required=True)
        if name == "restore":
            command.add_argument(
                "--target-env", type=Path, default=BACKEND / ".env.restore"
            )
            command.add_argument("--confirm-empty-target", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.command == "backup":
            result = backup(args.output, writes_paused=args.writes_paused)
        elif args.command == "verify":
            manifest, _, warnings = verify_bundle(args.backup)
            result = {
                "status": "verified",
                "graph": manifest["graph"],
                "users": manifest["auth"]["users"],
                "warnings": warnings,
            }
        elif args.command == "restore-auth":
            result = restore_auth_only(args.backup, args.output)
        else:
            result = restore(
                args.backup,
                args.output,
                args.target_env,
                confirm_empty_target=args.confirm_empty_target,
            )
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except BackupError as exc:
        print(f"Recovery operation stopped: {exc}")
    except Exception as exc:
        # Driver exceptions may contain connection details. Never dump them here.
        print(
            f"Recovery operation failed ({type(exc).__name__}). Output may be incomplete; do not promote it."
        )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
