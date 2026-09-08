"""Small, persistent authentication store for a single-host deployment.

The graph remains in CognoDB. No plaintext passwords or session tokens are stored.
SQLite transactions serialize role changes, rate limits and session revocation.
"""

import hashlib
import hmac
import json
import secrets
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4

from pwdlib import PasswordHash

password_hash = PasswordHash.recommended()
DUMMY_HASH = password_hash.hash(secrets.token_urlsafe(32))


class AuthError(Exception):
    def __init__(self, status: int, detail: str):
        self.status = status
        self.detail = detail
        super().__init__(detail)


def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def csrf_for(token: str) -> str:
    return hmac.new(token.encode(), b"skillgraph-csrf-v1", hashlib.sha256).hexdigest()


def public_user(row: sqlite3.Row) -> dict:
    return {
        "user_id": row["user_id"],
        "email": row["email"],
        "name": row["name"],
        "role": row["role"],
        "is_active": bool(row["is_active"]),
        "must_change_password": bool(row["must_change_password"]),
        "project_ids": json.loads(row["project_ids"]),
    }


class AuthStore:
    def __init__(
        self, path: Path, session_seconds: int = 28800, idle_seconds: int = 1800
    ):
        self.path = path.resolve()
        self.session_seconds = session_seconds
        self.idle_seconds = idle_seconds
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id TEXT PRIMARY KEY, email TEXT NOT NULL UNIQUE,
                    name TEXT NOT NULL, password_hash TEXT NOT NULL,
                    role TEXT NOT NULL CHECK(role IN ('ADMIN','MANAGER','VIEWER')),
                    is_active INTEGER NOT NULL DEFAULT 1,
                    must_change_password INTEGER NOT NULL DEFAULT 1,
                    project_ids TEXT NOT NULL DEFAULT '[]'
                );
                CREATE TABLE IF NOT EXISTS sessions (
                    token_hash TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
                    created_at REAL NOT NULL, expires_at REAL NOT NULL,
                    last_seen REAL NOT NULL
                );
                CREATE INDEX IF NOT EXISTS sessions_user ON sessions(user_id);
                CREATE TABLE IF NOT EXISTS login_limits (
                    key TEXT PRIMARY KEY, window_start REAL NOT NULL,
                    attempts INTEGER NOT NULL
                );
            """)

    @contextmanager
    def connection(self):
        db = sqlite3.connect(self.path, timeout=10, isolation_level=None)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys = ON")
        try:
            yield db
        except Exception:
            if db.in_transaction:
                db.rollback()
            raise
        finally:
            db.close()

    def create_user(self, data: dict, *, bootstrap: bool = False) -> dict:
        hashed = password_hash.hash(data["password"])
        uid = str(uuid4())
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            if bootstrap and db.execute("SELECT 1 FROM users LIMIT 1").fetchone():
                raise AuthError(409, "Đã có tài khoản. Hãy dùng trang quản trị.")
            try:
                db.execute(
                    "INSERT INTO users VALUES (?, ?, ?, ?, ?, 1, ?, ?)",
                    (
                        uid,
                        data["email"].strip().lower(),
                        data["name"],
                        hashed,
                        "ADMIN" if bootstrap else data["role"],
                        0 if bootstrap else 1,
                        json.dumps(
                            data.get("project_ids", [])
                            if data["role"] == "MANAGER"
                            else []
                        ),
                    ),
                )
            except sqlite3.IntegrityError as exc:
                raise AuthError(409, "Email này đã có tài khoản.") from exc
            row = db.execute("SELECT * FROM users WHERE user_id = ?", (uid,)).fetchone()
            db.commit()
        return public_user(row)

    def list_users(self, limit: int, offset: int) -> dict:
        with self.connection() as db:
            total = db.execute("SELECT COUNT(*) FROM users").fetchone()[0]
            rows = db.execute(
                "SELECT * FROM users ORDER BY email LIMIT ? OFFSET ?", (limit, offset)
            ).fetchall()
        return {
            "items": [public_user(row) for row in rows],
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    def reserve_attempt(self, email: str, address: str):
        now = time.time()
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute("DELETE FROM login_limits WHERE window_start < ?", (now - 900,))
            limits = [("account:" + digest(email), 5), ("ip:" + digest(address), 30)]
            for key, maximum in limits:
                row = db.execute(
                    "SELECT attempts FROM login_limits WHERE key = ?", (key,)
                ).fetchone()
                if row and row["attempts"] >= maximum:
                    raise AuthError(
                        429, "Quá nhiều lần thử. Vui lòng chờ 15 phút rồi thử lại."
                    )
            for key, _ in limits:
                db.execute(
                    "INSERT INTO login_limits VALUES (?, ?, 1) "
                    "ON CONFLICT(key) DO UPDATE SET attempts = attempts + 1",
                    (key, now),
                )
            db.commit()

    def login(
        self, email: str, password: str, address: str, old_token: str | None
    ) -> tuple:
        email = email.strip().lower()
        self.reserve_attempt(email, address)
        with self.connection() as db:
            row = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        valid = password_hash.verify(
            password, row["password_hash"] if row else DUMMY_HASH
        )
        if not row or not valid or not row["is_active"]:
            raise AuthError(401, "Email hoặc mật khẩu không đúng.")
        now, token = time.time(), secrets.token_urlsafe(32)
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            current = db.execute(
                "SELECT * FROM users WHERE user_id = ?", (row["user_id"],)
            ).fetchone()
            if (
                not current["is_active"]
                or current["password_hash"] != row["password_hash"]
            ):
                raise AuthError(401, "Email hoặc mật khẩu không đúng.")
            db.execute(
                "DELETE FROM sessions WHERE expires_at <= ? OR last_seen <= ?",
                (now, now - self.idle_seconds),
            )
            if old_token:
                db.execute(
                    "DELETE FROM sessions WHERE token_hash = ?", (digest(old_token),)
                )
            # Keep at most five active sessions per account.
            db.execute(
                "DELETE FROM sessions WHERE token_hash IN (SELECT token_hash FROM sessions "
                "WHERE user_id = ? ORDER BY created_at DESC LIMIT -1 OFFSET 4)",
                (row["user_id"],),
            )
            db.execute(
                "INSERT INTO sessions VALUES (?, ?, ?, ?, ?)",
                (digest(token), row["user_id"], now, now + self.session_seconds, now),
            )
            db.execute(
                "DELETE FROM login_limits WHERE key = ?", ("account:" + digest(email),)
            )
            db.commit()
        return public_user(current), token

    def authenticate(self, token: str) -> dict:
        now = time.time()
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT u.* FROM sessions s JOIN users u ON u.user_id = s.user_id "
                "WHERE s.token_hash = ? AND s.expires_at > ? AND s.last_seen > ? AND u.is_active = 1",
                (digest(token), now, now - self.idle_seconds),
            ).fetchone()
            if not row:
                raise AuthError(
                    401, "Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại."
                )
            db.execute(
                "UPDATE sessions SET last_seen = ? WHERE token_hash = ?",
                (now, digest(token)),
            )
            db.commit()
        return public_user(row)

    def logout(self, token: str):
        with self.connection() as db:
            db.execute("DELETE FROM sessions WHERE token_hash = ?", (digest(token),))

    def update_user(self, user_id: str, data: dict, actor_id: str) -> dict:
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT * FROM users WHERE user_id = ?", (user_id,)
            ).fetchone()
            if not row:
                raise AuthError(404, "Không tìm thấy tài khoản.")
            if user_id == actor_id and (
                data["role"] != "ADMIN" or not data["is_active"]
            ):
                raise AuthError(
                    409, "Không thể tự khóa hoặc hạ quyền tài khoản đang dùng."
                )
            if (
                row["role"] == "ADMIN"
                and row["is_active"]
                and (data["role"] != "ADMIN" or not data["is_active"])
            ):
                count = db.execute(
                    "SELECT COUNT(*) FROM users WHERE role = 'ADMIN' AND is_active = 1"
                ).fetchone()[0]
                if count <= 1:
                    raise AuthError(409, "Phải giữ ít nhất một Admin đang hoạt động.")
            db.execute(
                "UPDATE users SET role = ?, is_active = ?, project_ids = ? WHERE user_id = ?",
                (
                    data["role"],
                    int(data["is_active"]),
                    json.dumps(
                        data["project_ids"] if data["role"] == "MANAGER" else []
                    ),
                    user_id,
                ),
            )
            # Any permissions/status update revokes existing sessions immediately.
            db.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))
            updated = db.execute(
                "SELECT * FROM users WHERE user_id = ?", (user_id,)
            ).fetchone()
            db.commit()
        return public_user(updated)

    def reset_password(self, user_id: str, password: str):
        hashed = password_hash.hash(password)
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            result = db.execute(
                "UPDATE users SET password_hash = ?, must_change_password = 1 WHERE user_id = ?",
                (hashed, user_id),
            )
            if not result.rowcount:
                raise AuthError(404, "Không tìm thấy tài khoản.")
            db.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))
            db.commit()

    def change_password(self, user_id: str, current: str, new: str, address: str):
        self.reserve_attempt("password-change:" + user_id, address)
        with self.connection() as db:
            row = db.execute(
                "SELECT password_hash FROM users WHERE user_id = ?", (user_id,)
            ).fetchone()
        if not row or not password_hash.verify(current, row["password_hash"]):
            raise AuthError(400, "Mật khẩu hiện tại không đúng.")
        if current == new:
            raise AuthError(400, "Mật khẩu mới phải khác mật khẩu hiện tại.")
        hashed = password_hash.hash(new)
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            result = db.execute(
                "UPDATE users SET password_hash = ?, must_change_password = 0 "
                "WHERE user_id = ? AND password_hash = ? AND is_active = 1",
                (hashed, user_id, row["password_hash"]),
            )
            if not result.rowcount:
                raise AuthError(409, "Tài khoản đã thay đổi. Vui lòng đăng nhập lại.")
            db.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))
            db.commit()
