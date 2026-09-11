import copy
import json
import sqlite3
from contextlib import closing
from unittest.mock import MagicMock

import pytest

from app.core.config import settings
from app.repositories.auth_store import AuthStore
from scripts import backup_restore as cli
from scripts.backup_support import BackupError, auth, files, graph


def sample_graph():
    return {
        "nodes": [
            {
                "ref": "1",
                "labels": ["Employee"],
                "properties": {
                    "employee_id": "EMP001",
                    "name": "Synthetic",
                    "tags": ["a", "b"],
                },
            },
            {
                "ref": "2",
                "labels": ["Project"],
                "properties": {"project_id": "PROJ001", "name": "Backup test"},
            },
            {
                "ref": "3",
                "labels": ["AuditEvent"],
                "properties": {
                    "event_id": "test-event",
                    "before_json": "null",
                    "after_json": "{}",
                },
            },
        ],
        "relationships": [
            {
                "start": "1",
                "end": "2",
                "type": "WORKS_ON",
                "properties": {"allocation": 40, "role": "Engineer"},
            }
        ],
    }


@pytest.fixture
def auth_source(tmp_path):
    path = tmp_path / "source.sqlite3"
    store = AuthStore(path)
    store.create_user(
        {
            "email": "backup@example.com",
            "name": "Backup test",
            "password": "Backup tests only password!",
            "role": "ADMIN",
        },
        bootstrap=True,
    )
    store.login("backup@example.com", "Backup tests only password!", "test", None)
    return path


@pytest.fixture
def bundle(monkeypatch, tmp_path, auth_source):
    monkeypatch.setattr(settings, "auth_db_path", auth_source)
    monkeypatch.setattr(settings, "cognodb_uri", "bolt://source.invalid:7687")
    monkeypatch.setattr(cli, "make_driver", MagicMock())
    monkeypatch.setattr(cli, "export_graph", lambda driver: sample_graph())
    output = tmp_path / "bundle"
    result = cli.backup(output, writes_paused=True)
    assert result["status"] == "verified"
    return output


def test_pair_backup_checksums_and_schema(bundle):
    manifest, data, warnings = cli.verify_bundle(bundle)
    assert manifest["complete"] is True
    assert manifest["graph"]["nodes"] == 3 and manifest["graph"]["relationships"] == 1
    assert data == sample_graph()
    assert warnings == {"missing_manager_project_grants": 0}
    assert "password" not in (bundle / "manifest.json").read_text()


def test_auth_restore_revokes_sessions_preserves_users_and_source(
    bundle, auth_source, tmp_path
):
    before = auth.inspect_auth(auth_source)
    assert before["sessions"] == 1
    result = cli.restore_auth_only(bundle, tmp_path / "drill")
    after = auth.inspect_auth(tmp_path / "drill" / "auth.sqlite3")
    assert result["status"] == "auth_verified_graph_not_restored"
    assert after["users_sha256"] == before["users_sha256"]
    assert after["sessions"] == after["login_limits"] == 0
    assert auth.inspect_auth(auth_source) == before


def test_sqlite_online_backup_includes_committed_wal(auth_source, tmp_path):
    target = tmp_path / "wal-copy.sqlite3"
    with closing(sqlite3.connect(auth_source)) as writer:
        writer.execute("PRAGMA journal_mode=WAL")
        writer.execute("UPDATE users SET name='Committed WAL value'")
        writer.commit()
        auth.copy_auth(auth_source, target)
        assert (
            auth.inspect_auth(target)["users_sha256"]
            == auth.inspect_auth(auth_source)["users_sha256"]
        )


@pytest.mark.parametrize("filename", ["graph.json", "auth.sqlite3"])
def test_tampered_payload_refuses_restore(bundle, tmp_path, filename):
    with (bundle / filename).open("ab") as stream:
        stream.write(b"tampered")
    with pytest.raises(BackupError, match="checksum"):
        cli.restore_auth_only(bundle, tmp_path / "must-not-exist")
    assert not (tmp_path / "must-not-exist").exists()


@pytest.mark.parametrize("change", ["version", "complete", "filename", "graph_count"])
def test_invalid_manifest_fails(bundle, change):
    path = bundle / "manifest.json"
    manifest = json.loads(path.read_text())
    if change == "version":
        manifest["version"] = 999
    elif change == "complete":
        manifest["complete"] = False
    elif change == "filename":
        manifest["files"]["../../outside.sqlite3"] = manifest["files"].pop(
            "auth.sqlite3"
        )
    else:
        manifest["graph"]["nodes"] += 1
    path.write_text(json.dumps(manifest))
    with pytest.raises(BackupError):
        cli.verify_bundle(bundle)


def test_existing_outputs_are_never_overwritten(bundle, tmp_path):
    before = (bundle / "auth.sqlite3").read_bytes()
    with pytest.raises(BackupError):
        cli.restore_auth_only(bundle, bundle)
    with pytest.raises(BackupError):
        auth.copy_auth(bundle / "auth.sqlite3", bundle / "auth.sqlite3")
    assert (bundle / "auth.sqlite3").read_bytes() == before
    with pytest.raises(BackupError):
        cli.backup(tmp_path / "unconfirmed", writes_paused=False)
    assert not (tmp_path / "unconfirmed").exists()


def test_missing_auth_not_created(tmp_path):
    with pytest.raises(sqlite3.Error):
        auth.copy_auth(tmp_path / "missing.sqlite3", tmp_path / "out.sqlite3")
    assert not (tmp_path / "missing.sqlite3").exists()
    assert not (tmp_path / "out.sqlite3").exists()


@pytest.mark.parametrize(
    "change",
    [
        "label",
        "multiple_labels",
        "duplicate_ref",
        "duplicate_key",
        "no_key",
        "dangling",
        "direction",
        "type",
        "null_property",
        "nested_property",
        "nan",
    ],
)
def test_unsupported_graph_never_silently_loses_data(change):
    data = sample_graph()
    if change == "label":
        data["nodes"][0]["labels"] = ["UserSuppliedLabel"]
    elif change == "multiple_labels":
        data["nodes"][0]["labels"].append("Other")
    elif change in {"duplicate_ref", "duplicate_key"}:
        item = copy.deepcopy(data["nodes"][0])
        if change == "duplicate_key":
            item["ref"] = "different"
        data["nodes"].append(item)
    elif change == "no_key":
        data["nodes"][0]["properties"].pop("employee_id")
    elif change == "dangling":
        data["relationships"][0]["end"] = "missing"
    elif change == "direction":
        data["relationships"][0].update(start="2", end="1")
    elif change == "type":
        data["relationships"][0]["type"] = "UNTRUSTED_TYPE"
    else:
        data["nodes"][0]["properties"]["unsupported"] = {
            "null_property": None,
            "nested_property": {},
            "nan": float("nan"),
        }[change]
    with pytest.raises(BackupError):
        graph.validate_graph(data)


def test_logical_digest_ignores_internal_ids_and_order():
    data = sample_graph()
    modified = copy.deepcopy(data)
    modified["nodes"].reverse()
    for node in modified["nodes"]:
        node["ref"] = "new-" + node["ref"]
    for rel in modified["relationships"]:
        rel["start"], rel["end"] = "new-" + rel["start"], "new-" + rel["end"]
    assert graph.graph_summary(data) == graph.graph_summary(modified)
    modified["relationships"][0]["properties"]["allocation"] = 80
    assert graph.graph_summary(data) != graph.graph_summary(modified)


def test_endpoint_guard_normalizes_scheme_case_and_default_port():
    assert graph.endpoint_fingerprint(
        "bolt+s://Example.COM."
    ) == graph.endpoint_fingerprint("neo4j://example.com:7687/")
    with pytest.raises(BackupError):
        graph.endpoint_fingerprint("bolt://user:secret@example.com")


def test_restore_rejects_same_live_target_before_output(bundle, tmp_path, monkeypatch):
    env = tmp_path / ".env.restore"
    env.write_text(
        "COGNODB_URI=bolt+s://source.invalid\nCOGNODB_USER=test\nCOGNODB_PASSWORD=test-only\n"
    )
    with pytest.raises(BackupError, match="source/live"):
        cli.restore(bundle, tmp_path / "drill", env, confirm_empty_target=True)
    assert not (tmp_path / "drill").exists()


def test_nonempty_graph_target_rejected_before_schema_or_writes():
    driver = MagicMock()
    session = driver.session.return_value.__enter__.return_value
    session.run.return_value.single.return_value = {"total": 3}
    with pytest.raises(BackupError, match="not empty"):
        graph.restore_graph(driver, sample_graph())
    assert session.run.call_count == 1
    assert session.run.call_args.args[0].text.startswith("MATCH")


def test_cli_unknown_failure_does_not_leak_details(monkeypatch, capsys, tmp_path):
    def fail(*args, **kwargs):
        raise RuntimeError("bolt://private-instance secret-password")

    monkeypatch.setattr(cli, "backup", fail)
    assert (
        cli.main(["backup", "--output", str(tmp_path / "out"), "--writes-paused"]) == 1
    )
    output = capsys.readouterr().out
    assert "secret-password" not in output and "private-instance" not in output


def test_size_limits_and_low_disk_space_fail(monkeypatch, tmp_path):
    path = tmp_path / "small.json"
    path.write_bytes(b"{}" * 10)
    monkeypatch.setattr(files, "MAX_FILE_BYTES", 5)
    with pytest.raises(BackupError):
        files.load_json(path)
    monkeypatch.setattr(
        files.shutil, "disk_usage", lambda path: type("Disk", (), {"free": 1})()
    )
    with pytest.raises(BackupError):
        files.private_directory(tmp_path / "out")
    assert not (tmp_path / "out").exists()


def test_restore_cannot_create_a_missing_live_auth_database(
    bundle, tmp_path, monkeypatch
):
    output = tmp_path / "missing-live-directory"
    monkeypatch.setenv("AUTH_DB_PATH", str(output / "auth.sqlite3"))
    with pytest.raises(BackupError, match="live auth"):
        cli.restore_auth_only(bundle, output)
    assert not output.exists()


@pytest.mark.parametrize("failure", [None, "count", "post_commit"])
def test_graph_import_uses_one_transaction_and_checks_content(monkeypatch, failure):
    data = sample_graph()
    data["nodes"].extend(
        [
            {"ref": "4", "labels": ["Skill"], "properties": {"skill_id": "SK001"}},
            {"ref": "5", "labels": ["Team"], "properties": {"team_id": "TEAM001"}},
        ]
    )
    data["relationships"].extend(
        [
            {"start": "1", "end": "4", "type": "HAS_SKILL", "properties": {"level": 3}},
            {
                "start": "2",
                "end": "4",
                "type": "REQUIRES_SKILL",
                "properties": {"min_level": 3},
            },
            {"start": "1", "end": "5", "type": "MEMBER_OF", "properties": {}},
            {"start": "2", "end": "5", "type": "OWNED_BY", "properties": {}},
        ]
    )
    monkeypatch.setattr(
        "scripts.setup_activity_schema.setup_activity_schema", lambda session: None
    )
    driver = MagicMock()
    session = driver.session.return_value.__enter__.return_value
    session.run.return_value.single.return_value = {"total": 0}
    transaction = session.begin_transaction.return_value.__enter__.return_value

    def run(query, **params):
        result = MagicMock()
        count = len(params.get("rows", []))
        if failure == "count" and "CREATE (a)-[r:" in query:
            count = 0
        result.single.return_value = {"total": count}
        return result

    transaction.run.side_effect = run
    exporter = MagicMock(
        return_value=sample_graph() if failure == "post_commit" else data
    )
    monkeypatch.setattr(graph, "export_graph", exporter)
    if failure:
        with pytest.raises(BackupError):
            graph.restore_graph(driver, data)
    else:
        graph.restore_graph(driver, data)
        queries = [call.args[0] for call in transaction.run.call_args_list]
        assert sum("CREATE (n:" in query for query in queries) == 5
        assert sum("CREATE (a)-[r:" in query for query in queries) == 5
    session.begin_transaction.assert_called_once()
    exit_error = session.begin_transaction.return_value.__exit__.call_args.args[0]
    assert exit_error is (BackupError if failure == "count" else None)
    if failure == "count":
        exporter.assert_not_called()
    else:
        exporter.assert_called_once_with(driver)


def test_isolated_full_restore_writes_report_after_success(
    bundle, tmp_path, monkeypatch
):
    env = tmp_path / ".env.restore"
    env.write_text(
        "COGNODB_URI=bolt://test-target.invalid\nCOGNODB_USER=test\nCOGNODB_PASSWORD=test-only\n"
    )
    importer = MagicMock()
    monkeypatch.setattr(cli, "restore_graph", importer)
    output = tmp_path / "full-drill"
    result = cli.restore(bundle, output, env, confirm_empty_target=True)
    assert result["status"] == "restore_verified" and result["sessions"] == 0
    assert (output / "restore-report.json").is_file()
    assert importer.call_args.args[1] == sample_graph()


def test_failed_graph_restore_has_no_success_report(bundle, tmp_path, monkeypatch):
    env = tmp_path / ".env.restore"
    env.write_text(
        "COGNODB_URI=bolt://test-target.invalid\nCOGNODB_USER=test\nCOGNODB_PASSWORD=test-only\n"
    )
    monkeypatch.setattr(
        cli, "restore_graph", MagicMock(side_effect=BackupError("Test failure"))
    )
    output = tmp_path / "failed-drill"
    with pytest.raises(BackupError):
        cli.restore(bundle, output, env, confirm_empty_target=True)
    assert not (output / "restore-report.json").exists()
    assert (bundle / "auth.sqlite3").is_file()
