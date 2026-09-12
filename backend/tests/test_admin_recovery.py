"""Local recovery tests: only synthetic accounts in tmp_path SQLite databases."""

import sqlite3
import sys
import warnings
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager

import pytest
from fastapi.testclient import TestClient

from app.api.auth_dependencies import get_auth_store
from app.main import app
from app.repositories.auth_store import AuthError, AuthStore, digest, password_hash
from scripts import recover_admin as recovery

PASSWORD = "Synthetic old password 2026!"
RECOVERY_PASSWORD = "Synthetic recovery password 2026!"
FINAL_PASSWORD = "Synthetic final password 2026!"
EMAIL = "recovery-admin@example.com"


@pytest.fixture
def account(tmp_path):
    store = AuthStore(tmp_path / "auth.sqlite3")
    admin = store.create_user(
        {"email": EMAIL, "name": "Test Admin", "password": PASSWORD, "role": "ADMIN"},
        bootstrap=True,
    )
    return store, admin


def snapshot(store):
    with store.connection() as db:
        return {
            table: [
                tuple(row) for row in db.execute(f"SELECT * FROM {table} ORDER BY 1")
            ]
            for table in ("users", "sessions", "login_limits")
        }


def seed_session(store, user_id, token):
    with store.connection() as db:
        db.execute(
            "INSERT INTO sessions VALUES (?, ?, 1, 9999999999, 9999999999)",
            (digest(token), user_id),
        )


def test_recovery_changes_only_target_revokes_sessions_and_preserves_ip_limits(account):
    store, admin = account
    manager = store.create_user(
        {
            "email": "manager@example.com",
            "name": "Manager",
            "password": PASSWORD,
            "role": "MANAGER",
            "project_ids": ["PROJ001"],
        }
    )
    seed_session(store, admin["user_id"], "old-admin-session-1")
    seed_session(store, admin["user_id"], "old-admin-session-2")
    seed_session(store, manager["user_id"], "other-session")
    own_keys = {
        "account:" + digest(EMAIL),
        "account:" + digest("password-change:" + admin["user_id"]),
    }
    preserved_keys = {
        "ip:" + digest("127.0.0.1"),
        "account:" + digest(manager["email"]),
    }
    with store.connection() as db:
        for key in own_keys | preserved_keys:
            db.execute("INSERT INTO login_limits VALUES (?, 9999999999, 5)", (key,))
    before = snapshot(store)
    target = recovery.inspect_admin(store.path, f"  {EMAIL.upper()}  ")
    assert "$argon2" not in repr(target) and PASSWORD not in repr(target)
    result = recovery.recover_admin(target, RECOVERY_PASSWORD)
    assert result.revoked_sessions == 2 and result.cleared_account_limits == 2
    after = snapshot(store)
    old_users = {row[0]: row for row in before["users"]}
    new_users = {row[0]: row for row in after["users"]}
    assert new_users[manager["user_id"]] == old_users[manager["user_id"]]
    old_admin, new_admin = old_users[admin["user_id"]], new_users[admin["user_id"]]
    assert new_admin[:3] == old_admin[:3]
    assert new_admin[4:6] == old_admin[4:6]
    assert new_admin[7:] == old_admin[7:]
    assert new_admin[6] == 1
    assert new_admin[3].startswith("$argon2id$")
    assert password_hash.verify(RECOVERY_PASSWORD, new_admin[3])
    assert not password_hash.verify(PASSWORD, new_admin[3])
    assert after["sessions"] == [
        row for row in before["sessions"] if row[1] == manager["user_id"]
    ]
    assert after["login_limits"] == [
        row for row in before["login_limits"] if row[0] in preserved_keys
    ]
    for token in ("old-admin-session-1", "old-admin-session-2"):
        with pytest.raises(AuthError) as error:
            store.authenticate(token)
        assert error.value.status == 401
    assert store.authenticate("other-session")["user_id"] == manager["user_id"]


def test_recovered_login_forces_password_change_then_allows_business_routes(
    account, monkeypatch
):
    store, _ = account
    recovery.recover_admin(recovery.inspect_admin(store.path, EMAIL), RECOVERY_PASSWORD)
    app.dependency_overrides[get_auth_store] = lambda: store
    monkeypatch.setattr(
        "app.api.employees.service.list",
        lambda *args: {"items": [], "total": 0, "limit": 20, "offset": 0},
    )
    client = TestClient(app, headers={"Origin": "http://127.0.0.1:5173"})
    try:
        assert (
            client.post(
                "/api/auth/login", json={"email": EMAIL, "password": PASSWORD}
            ).status_code
            == 401
        )
        response = client.post(
            "/api/auth/login", json={"email": EMAIL, "password": RECOVERY_PASSWORD}
        )
        assert (
            response.status_code == 200
            and response.json()["user"]["must_change_password"]
        )
        client.headers["X-CSRF-Token"] = response.json()["csrf_token"]
        assert client.get("/api/employees").status_code == 403
        assert (
            client.post(
                "/api/auth/password",
                json={
                    "current_password": RECOVERY_PASSWORD,
                    "new_password": FINAL_PASSWORD,
                },
            ).status_code
            == 204
        )
        assert client.get("/api/auth/me").status_code == 401
        response = client.post(
            "/api/auth/login", json={"email": EMAIL, "password": FINAL_PASSWORD}
        )
        assert (
            response.status_code == 200
            and not response.json()["user"]["must_change_password"]
        )
        assert client.get("/api/employees").status_code == 200
    finally:
        client.close()
        app.dependency_overrides.pop(get_auth_store, None)


@pytest.mark.parametrize("role,active", [("VIEWER", 1), ("MANAGER", 1), ("ADMIN", 0)])
def test_cannot_promote_or_unlock(account, role, active):
    store, _ = account
    with store.connection() as db:
        db.execute("UPDATE users SET role = ?, is_active = ?", (role, active))
    before = snapshot(store)
    with pytest.raises(recovery.RecoveryError, match="Chỉ khôi phục"):
        recovery.inspect_admin(store.path, EMAIL)
    assert snapshot(store) == before


@pytest.mark.parametrize("email", ["unknown@example.com", "invalid", "' OR 1=1 --"])
def test_missing_or_invalid_email_does_not_write(account, email):
    store, _ = account
    before = snapshot(store)
    with pytest.raises(recovery.RecoveryError):
        recovery.inspect_admin(store.path, email)
    assert snapshot(store) == before


def test_missing_database_does_not_bootstrap(tmp_path):
    path = tmp_path / "missing-parent" / "auth.sqlite3"
    with pytest.raises(recovery.RecoveryError, match="Không tạo DB mới"):
        recovery.inspect_admin(path, EMAIL)
    assert not path.parent.exists()


@pytest.mark.parametrize("payload", [b"", b"not a sqlite database"])
def test_empty_or_corrupt_database_not_modified(tmp_path, payload):
    path = tmp_path / "invalid.sqlite3"
    path.write_bytes(payload)
    with pytest.raises((recovery.RecoveryError, sqlite3.DatabaseError)):
        recovery.inspect_admin(path, EMAIL)
    assert path.read_bytes() == payload


@pytest.mark.parametrize(
    "statement",
    [
        "DROP TABLE sessions",
        "ALTER TABLE users ADD COLUMN unknown TEXT",
        "CREATE VIEW extra_view AS SELECT user_id FROM users",
        "CREATE TRIGGER extra_trigger AFTER UPDATE ON users BEGIN DELETE FROM sessions; END",
        "CREATE TRIGGER sqliteX_trigger AFTER UPDATE ON users BEGIN DELETE FROM sessions; END",
    ],
)
def test_unknown_schema_rejected_without_migration(account, statement):
    store, _ = account
    with store.connection() as db:
        db.execute(statement)
    before = store.path.read_bytes()
    with pytest.raises(recovery.RecoveryError, match="Schema"):
        recovery.inspect_admin(store.path, EMAIL)
    assert store.path.read_bytes() == before


def test_foreign_key_corruption_rejected(account):
    store, _ = account
    with sqlite3.connect(store.path) as db:
        db.execute("INSERT INTO sessions VALUES ('orphan', 'missing-user', 1, 2, 3)")
    before = snapshot(store)
    with pytest.raises(recovery.RecoveryError, match="quan hệ auth"):
        recovery.inspect_admin(store.path, EMAIL)
    assert snapshot(store) == before


@pytest.mark.parametrize("password", ["", "short", "x" * 14, "x" * 129, PASSWORD])
def test_invalid_or_unchanged_password_preserves_state(account, password):
    store, admin = account
    seed_session(store, admin["user_id"], "unchanged-session")
    target = recovery.inspect_admin(store.path, EMAIL)
    before = snapshot(store)
    with pytest.raises(recovery.RecoveryError):
        recovery.recover_admin(target, password)
    assert snapshot(store) == before


@pytest.mark.parametrize(
    "password", ["x" * 15, "y" * 128, "  Mật khẩu thử nghiệm mới!  "]
)
def test_password_boundaries_and_spaces_preserved(account, password):
    store, _ = account
    recovery.recover_admin(recovery.inspect_admin(store.path, EMAIL), password)
    with store.connection() as db:
        hashed = db.execute("SELECT password_hash FROM users").fetchone()[0]
    assert password_hash.verify(password, hashed)
    if password != password.strip():
        assert not password_hash.verify(password.strip(), hashed)


@pytest.mark.parametrize(
    "update",
    [
        "role = 'VIEWER'",
        "is_active = 0",
        "email = 'changed@example.com'",
        "name = 'Changed after preview'",
        "password_hash = 'changed after preview'",
        "project_ids = '[\"PROJ002\"]'",
    ],
)
def test_changed_account_after_preview_is_not_overwritten(account, update):
    store, _ = account
    target = recovery.inspect_admin(store.path, EMAIL)
    with store.connection() as db:
        db.execute(f"UPDATE users SET {update}")
    before = snapshot(store)
    with pytest.raises(recovery.RecoveryError):
        recovery.recover_admin(target, RECOVERY_PASSWORD)
    assert snapshot(store) == before


def test_removed_database_after_preview_is_not_recreated(account, tmp_path):
    store, _ = account
    target = recovery.inspect_admin(store.path, EMAIL)
    original = tmp_path / "original.sqlite3"
    store.path.rename(original)
    with pytest.raises(recovery.RecoveryError):
        recovery.recover_admin(target, RECOVERY_PASSWORD)
    assert not store.path.exists() and original.is_file()


def test_replaced_database_after_preview_is_not_changed(account, tmp_path):
    store, _ = account
    target = recovery.inspect_admin(store.path, EMAIL)
    store.path.rename(tmp_path / "original.sqlite3")
    replacement = AuthStore(store.path)
    before = snapshot(replacement)
    with pytest.raises(recovery.RecoveryError, match="File DB đã thay đổi"):
        recovery.recover_admin(target, RECOVERY_PASSWORD)
    assert snapshot(replacement) == before


@pytest.mark.parametrize("stage", ["sessions", "limits", "commit", "interrupt"])
def test_mid_transaction_failure_rolls_back_every_change(account, monkeypatch, stage):
    store, admin = account
    seed_session(store, admin["user_id"], "rollback-session")
    with store.connection() as db:
        db.execute(
            "INSERT INTO login_limits VALUES (?, 1, 5)", ("account:" + digest(EMAIL),)
        )
    target = recovery.inspect_admin(store.path, EMAIL)
    before = snapshot(store)
    original = recovery._connection

    class Fault:
        def __init__(self, db):
            self.db = db

        def execute(self, statement, *args):
            if stage == "interrupt" and statement.startswith("DELETE FROM sessions"):
                raise KeyboardInterrupt
            if (
                stage == "sessions" and statement.startswith("DELETE FROM sessions")
            ) or (
                stage == "limits" and statement.startswith("DELETE FROM login_limits")
            ):
                raise sqlite3.OperationalError("Synthetic failure")
            return self.db.execute(statement, *args)

        def commit(self):
            if stage == "commit":
                raise sqlite3.OperationalError("Synthetic pre-commit failure")
            self.db.commit()

    @contextmanager
    def faulty_connection(path, *, write=False):
        with original(path, write=write) as db:
            yield Fault(db) if write else db

    monkeypatch.setattr(recovery, "_connection", faulty_connection)
    with pytest.raises(
        KeyboardInterrupt if stage == "interrupt" else sqlite3.OperationalError
    ):
        recovery.recover_admin(target, RECOVERY_PASSWORD)
    assert snapshot(store) == before


def test_locked_database_fails_without_changes(account, monkeypatch):
    store, _ = account
    target = recovery.inspect_admin(store.path, EMAIL)
    before = snapshot(store)
    monkeypatch.setattr(recovery, "SQLITE_TIMEOUT_SECONDS", 0.01)
    with store.connection() as lock:
        lock.execute("BEGIN IMMEDIATE")
        with pytest.raises(sqlite3.OperationalError):
            recovery.recover_admin(target, RECOVERY_PASSWORD)
        lock.rollback()
    assert snapshot(store) == before


def test_two_recoveries_from_same_preview_only_one_commits(account):
    store, _ = account
    target = recovery.inspect_admin(store.path, EMAIL)

    def attempt(password):
        try:
            recovery.recover_admin(target, password)
            return password
        except recovery.RecoveryError:
            return None

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(attempt, [RECOVERY_PASSWORD, FINAL_PASSWORD]))
    winners = [password for password in results if password]
    assert len(winners) == 1
    with store.connection() as db:
        hashed = db.execute("SELECT password_hash FROM users").fetchone()[0]
    assert password_hash.verify(winners[0], hashed)


def interactive(monkeypatch, inputs, passwords):
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr(sys.stdout, "isatty", lambda: True)
    answers, secrets = iter(inputs), iter(passwords)
    monkeypatch.setattr("builtins.input", lambda prompt: next(answers))
    monkeypatch.setattr(recovery, "getpass", lambda prompt: next(secrets))


def test_cli_success_has_no_secret_output_and_explicit_path_needs_no_graph_config(
    account, monkeypatch, capsys
):
    store, _ = account
    interactive(monkeypatch, [EMAIL, f"KHOI PHUC {EMAIL}"], [RECOVERY_PASSWORD] * 2)
    monkeypatch.setattr(
        recovery,
        "RecoverySettings",
        lambda: pytest.fail("Explicit path must skip settings"),
    )
    assert recovery.main(["--db-path", str(store.path)]) == 0
    output = capsys.readouterr().out
    assert "Đã khôi phục Admin" in output and "bắt buộc đổi mật khẩu" in output
    assert (
        PASSWORD not in output
        and RECOVERY_PASSWORD not in output
        and "$argon2" not in output
    )


@pytest.mark.parametrize("confirmation", ["", "yes", "KHOI PHUC wrong@example.com"])
def test_cli_requires_exact_confirmation(account, monkeypatch, confirmation, capsys):
    store, _ = account
    interactive(monkeypatch, [EMAIL, confirmation], [])
    before = snapshot(store)
    assert recovery.main(["--db-path", str(store.path)]) == 1
    assert "Đã hủy trước khi ghi" in capsys.readouterr().out
    assert snapshot(store) == before


@pytest.mark.parametrize(
    "passwords", [(RECOVERY_PASSWORD, FINAL_PASSWORD), ("short", "short")]
)
def test_cli_password_errors_do_not_write_or_echo(
    account, monkeypatch, capsys, passwords
):
    store, _ = account
    interactive(monkeypatch, [EMAIL, f"KHOI PHUC {EMAIL}"], passwords)
    before = snapshot(store)
    assert recovery.main(["--db-path", str(store.path)]) == 1
    output = capsys.readouterr().out
    assert all(password not in output for password in passwords)
    assert snapshot(store) == before


def test_cli_getpass_fallback_is_disabled(account, monkeypatch, capsys):
    store, _ = account
    interactive(monkeypatch, [EMAIL, f"KHOI PHUC {EMAIL}"], [])

    def unsafe_getpass(prompt):
        warnings.warn(
            "Synthetic sensitive warning", recovery.GetPassWarning, stacklevel=2
        )
        pytest.fail("Must stop before fallback input")

    monkeypatch.setattr(recovery, "getpass", unsafe_getpass)
    before = snapshot(store)
    assert recovery.main(["--db-path", str(store.path)]) == 2
    output = capsys.readouterr().out
    assert "không hỗ trợ nhập ẩn" in output and "Synthetic sensitive" not in output
    assert snapshot(store) == before


@pytest.mark.parametrize("exception", [KeyboardInterrupt, EOFError])
def test_cli_interrupts_before_write_are_safe(account, monkeypatch, exception):
    store, _ = account
    interactive(monkeypatch, [], [])

    def interrupt(prompt):
        raise exception

    monkeypatch.setattr("builtins.input", interrupt)
    before = snapshot(store)
    assert recovery.main(["--db-path", str(store.path)]) == 130
    assert snapshot(store) == before


def test_cli_unexpected_errors_are_sanitized(account, monkeypatch, capsys):
    store, _ = account
    interactive(monkeypatch, [EMAIL, f"KHOI PHUC {EMAIL}"], [RECOVERY_PASSWORD] * 2)

    def fail(*args):
        raise RuntimeError("Synthetic sensitive " + RECOVERY_PASSWORD)

    monkeypatch.setattr(recovery, "recover_admin", fail)
    before = snapshot(store)
    assert recovery.main(["--db-path", str(store.path)]) == 1
    output = capsys.readouterr().out
    assert RECOVERY_PASSWORD not in output and "Traceback" not in output
    assert snapshot(store) == before


@pytest.mark.parametrize("stream", ["stdin", "stdout"])
def test_cli_refuses_redirection_before_reading_configuration(
    monkeypatch, capsys, stream
):
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr(sys.stdout, "isatty", lambda: True)
    monkeypatch.setattr(getattr(sys, stream), "isatty", lambda: False)
    monkeypatch.setattr(
        recovery, "RecoverySettings", lambda: pytest.fail("Must not load settings")
    )
    assert recovery.main([]) == 2
    assert "Cần terminal tương tác" in capsys.readouterr().out


def test_unknown_password_argument_is_not_echoed(capsys):
    with pytest.raises(SystemExit) as error:
        recovery.main(["--password", RECOVERY_PASSWORD])
    assert error.value.code == 2
    output = capsys.readouterr()
    assert RECOVERY_PASSWORD not in output.out + output.err


def test_help_does_not_read_configuration(monkeypatch, capsys):
    monkeypatch.setattr(
        recovery, "RecoverySettings", lambda: pytest.fail("Must not load settings")
    )
    with pytest.raises(SystemExit) as error:
        recovery.main(["--help"])
    assert error.value.code == 0
    assert "--db-path" in capsys.readouterr().out


def test_path_settings_precedence_and_no_graph_credentials(tmp_path, monkeypatch):
    monkeypatch.delenv("AUTH_DB_PATH", raising=False)
    env_file = tmp_path / ".env"
    file_db, environment_db = (
        tmp_path / "file.sqlite3",
        tmp_path / "environment.sqlite3",
    )
    env_file.write_text(
        f'AUTH_DB_PATH="{file_db.as_posix()}"\nCOGNODB_USER=ignored\n', encoding="utf-8"
    )
    assert recovery.RecoverySettings(_env_file=env_file).auth_db_path == file_db
    monkeypatch.setenv("AUTH_DB_PATH", str(environment_db))
    assert recovery.RecoverySettings(_env_file=env_file).auth_db_path == environment_db
    monkeypatch.delenv("AUTH_DB_PATH")
    assert (
        recovery.RecoverySettings(_env_file=None).auth_db_path
        == recovery.BACKEND_DIR / "data" / "auth.sqlite3"
    )
