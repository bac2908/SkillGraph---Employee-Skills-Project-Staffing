import asyncio
import socket
import sqlite3
import threading
from contextlib import closing
from time import monotonic
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient
from neo4j import AsyncGraphDatabase

from app.main import app
from app.repositories.auth_store import AuthStore
from app.services import readiness_service as readiness


@pytest.fixture
def auth_path(tmp_path):
    path = tmp_path / "auth.sqlite3"
    AuthStore(path).create_user(
        {
            "email": "ready@example.com",
            "name": "Readiness test",
            "password": "Readiness test only password!",
            "role": "ADMIN",
        },
        bootstrap=True,
    )
    return path


class Result:
    def __init__(self, records):
        self.records = records

    async def single(self):
        return self.records[0] if self.records else None

    def __aiter__(self):
        async def rows():
            for row in self.records:
                yield row

        return rows()


class Session:
    def __init__(self, mode="ok"):
        self.mode, self.cancelled, self.calls = mode, False, []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass

    def cancel(self):
        self.cancelled = True

    async def run(self, query):
        self.calls.append(query)
        if self.mode == "hang":
            await asyncio.Event().wait()
        if self.mode == "error":
            raise RuntimeError("secret URI and password must not leak")
        if query.text.startswith("RETURN"):
            return Result([{"ok": 1}])
        names = readiness.REQUIRED_CONSTRAINTS if self.mode == "ok" else []
        return Result([{"name": name} for name in names])


class Driver:
    def __init__(self, mode="ok"):
        self.value = Session(mode)
        self.close = AsyncMock()

    def session(self, **kwargs):
        return self.value


def test_auth_probe_existing_is_non_mutating(auth_path):
    before = auth_path.read_bytes()
    assert readiness.probe_auth(auth_path) == "ok"
    assert auth_path.read_bytes() == before


def test_missing_auth_is_not_created(tmp_path):
    path = tmp_path / "missing.sqlite3"
    assert readiness.probe_auth(path) == "unavailable"
    assert not path.exists()


@pytest.mark.parametrize(
    "condition,expected",
    [
        ("empty", "admin_missing"),
        ("missing_table", "unavailable"),
        ("locked", "unavailable"),
    ],
)
def test_auth_unusable_is_not_ready(auth_path, condition, expected):
    with closing(sqlite3.connect(auth_path)) as db:
        if condition == "empty":
            db.execute("DELETE FROM users")
            db.commit()
        elif condition == "missing_table":
            db.execute("DROP TABLE login_limits")
            db.commit()
        else:
            db.execute("BEGIN IMMEDIATE")
        assert readiness.probe_auth(auth_path) == expected


@pytest.mark.parametrize(
    "mode,expected",
    [
        ("ok", "ok"),
        ("schema", "schema_missing"),
        ("error", "unavailable"),
        ("hang", "timeout"),
    ],
)
def test_graph_status_timeout_and_cleanup(monkeypatch, tmp_path, mode, expected):
    driver = Driver(mode)
    monkeypatch.setattr(readiness, "probe_auth", lambda path: "ok")

    async def run():
        checker = readiness.ReadinessChecker(
            driver=driver, timeout=0.03, auth_path=tmp_path
        )
        result = await checker.check()
        await checker.close()
        return result

    assert asyncio.run(run()) == {"graph": expected, "auth": "ok"}
    assert driver.value.cancelled == (mode == "hang")
    driver.close.assert_awaited_once()


def test_single_flight_cache_and_expiry(monkeypatch):
    driver = Driver()
    monkeypatch.setattr(readiness, "probe_auth", lambda path: "ok")

    async def run():
        checker = readiness.ReadinessChecker(driver=driver, cache_seconds=0.01)
        results = await asyncio.gather(*(checker.check() for _ in range(20)))
        assert all(item == {"graph": "ok", "auth": "ok"} for item in results)
        assert len(driver.value.calls) == 2
        results[0]["graph"] = "forged"
        assert (await checker.check())["graph"] == "ok"
        await asyncio.sleep(0.02)
        await checker.check()
        assert len(driver.value.calls) == 4
        await checker.close()

    asyncio.run(run())


@pytest.mark.parametrize(
    "checks,status,body",
    [
        ({"graph": "ok", "auth": "ok"}, 200, "ready"),
        ({"graph": "timeout", "auth": "ok"}, 503, "not_ready"),
        ({"graph": "ok", "auth": "unavailable"}, 503, "not_ready"),
    ],
)
def test_public_probe_is_minimal_uncached_and_liveness_stays_independent(
    monkeypatch, checks, status, body
):
    import app.main as main

    checker = type(
        "Stub", (), {"check": AsyncMock(return_value=checks), "close": AsyncMock()}
    )()
    monkeypatch.setattr(main, "ReadinessChecker", lambda: checker)
    with TestClient(app) as client:
        live = client.get("/health")
        assert live.status_code == 200 and live.json() == {"status": "ok"}
        checker.check.assert_not_called()
        response = client.get("/health/ready")
        assert response.status_code == status
        assert response.json() == {"status": body}
        assert response.headers["cache-control"] == "no-store"
        assert "graph" not in response.text and "auth" not in response.text
    checker.close.assert_awaited_once()


def test_real_driver_cancels_a_nonresponding_local_bolt_peer(monkeypatch):
    monkeypatch.setattr(readiness, "probe_auth", lambda path: "ok")
    stopped = threading.Event()
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    listener.listen(1)
    listener.settimeout(2)
    port = listener.getsockname()[1]

    def peer():
        try:
            connection, _ = listener.accept()
            with connection:
                connection.settimeout(0.1)
                while not stopped.is_set():
                    try:
                        if not connection.recv(1024):
                            break
                    except TimeoutError:
                        pass
        except (OSError, TimeoutError):
            pass

    thread = threading.Thread(target=peer, daemon=True)
    thread.start()

    async def run():
        driver = AsyncGraphDatabase.driver(
            f"bolt://127.0.0.1:{port}", auth=("test", "test")
        )
        checker = readiness.ReadinessChecker(driver=driver, timeout=0.15)
        try:
            started = monotonic()
            result = await checker.check()
            assert result["graph"] == "timeout"
            assert monotonic() - started < 1.5
        finally:
            await checker.close()

    try:
        asyncio.run(run())
    finally:
        stopped.set()
        listener.close()
        thread.join(timeout=2)
    assert not thread.is_alive()
