"""Bounded dependency probes. Never bootstrap/migrate databases as a health check."""

import asyncio
import sqlite3
from contextlib import closing
from pathlib import Path
from time import monotonic

from neo4j import READ_ACCESS, AsyncGraphDatabase, Query

from app.core.config import settings
from app.db.auth_schema import AUTH_COLUMNS

REQUIRED_CONSTRAINTS = {
    "employee_employee_id_unique",
    "employee_email_unique",
    "skill_skill_id_unique",
    "skill_name_unique",
    "project_project_id_unique",
    "team_team_id_unique",
    "audit_event_id_unique",
}


def probe_auth(path: Path) -> str:
    # mode=rw fails on a missing file; AuthStore() would create one and hide loss.
    deadline = monotonic() + 0.5
    try:
        with closing(
            sqlite3.connect(path.resolve().as_uri() + "?mode=rw", uri=True, timeout=0.2)
        ) as db:
            db.set_progress_handler(lambda: int(monotonic() > deadline), 100)
            for table, columns in AUTH_COLUMNS.items():
                db.execute(f"SELECT {columns} FROM {table} LIMIT 0")
            if not db.execute(
                "SELECT 1 FROM users WHERE role = 'ADMIN' AND is_active = 1 LIMIT 1"
            ).fetchone():
                return "admin_missing"
            # Authentication updates sessions. Check write-lock access without
            # changing a row, creating a table, or running integrity scans.
            db.execute("BEGIN IMMEDIATE")
            db.rollback()
            return "ok"
    except (OSError, sqlite3.Error):
        return "unavailable"


class ReadinessChecker:
    def __init__(
        self, *, driver=None, auth_path=None, timeout=None, cache_seconds=None
    ):
        self.timeout = (
            timeout if timeout is not None else settings.readiness_timeout_seconds
        )
        self.cache_seconds = (
            cache_seconds
            if cache_seconds is not None
            else settings.readiness_cache_seconds
        )
        self.auth_path = auth_path if auth_path is not None else settings.auth_db_path
        self.driver = (
            driver
            if driver is not None
            else AsyncGraphDatabase.driver(
                settings.cognodb_uri,
                auth=(settings.cognodb_user, settings.cognodb_password),
                connection_timeout=min(2, self.timeout),
                connection_acquisition_timeout=self.timeout,
                max_transaction_retry_time=0,
                max_connection_pool_size=1,
            )
        )
        self._lock = asyncio.Lock()
        self._cached = None
        self._expires = 0.0

    async def _graph(self):
        session = self.driver.session(default_access_mode=READ_ACCESS)
        try:
            async with session:
                result = await session.run(
                    Query("RETURN 1 AS ok", timeout=self.timeout)
                )
                record = await result.single()
                if record is None or record["ok"] != 1:
                    return "unavailable"
                result = await session.run(
                    Query(
                        "SHOW CONSTRAINTS YIELD name RETURN name", timeout=self.timeout
                    )
                )
                names = {row["name"] async for row in result}
                return (
                    "ok" if REQUIRED_CONSTRAINTS.issubset(names) else "schema_missing"
                )
        except asyncio.CancelledError:
            session.cancel()  # Force-close an in-flight connection on timeout.
            raise
        except Exception:
            return "unavailable"  # No URI, exception text or credentials in response.

    async def _bounded_graph(self):
        try:
            return await asyncio.wait_for(self._graph(), self.timeout)
        except TimeoutError:
            return "timeout"

    async def _bounded_auth(self):
        try:
            return await asyncio.wait_for(
                asyncio.to_thread(probe_auth, self.auth_path), 0.75
            )
        except TimeoutError:
            return "timeout"

    async def check(self):
        async with self._lock:  # Single flight + short cache avoids probe storms.
            if self._cached is not None and monotonic() < self._expires:
                return dict(self._cached)
            graph, auth = await asyncio.gather(
                self._bounded_graph(), self._bounded_auth()
            )
            self._cached = {"graph": graph, "auth": auth}
            self._expires = monotonic() + self.cache_seconds
            return dict(self._cached)

    async def close(self):
        await self.driver.close()
