"""Interactive, local-only recovery of an existing active Admin.

No AuthStore construction, graph connection, migrations, HTTP route or password
arguments. Filesystem access is the authority boundary; see docs/admin-recovery.md.
"""

import argparse
import hashlib
import json
import sqlite3
import sys
import warnings
from contextlib import contextmanager
from dataclasses import dataclass, field
from getpass import GetPassWarning, getpass
from pathlib import Path
from time import monotonic

from pydantic import EmailStr, TypeAdapter, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.db.auth_schema import AUTH_COLUMNS
from app.repositories.auth_store import digest, password_hash
from app.schemas.auth import PasswordReset

BACKEND_DIR = Path(__file__).resolve().parents[1]
SQLITE_TIMEOUT_SECONDS = 2.0
QUERY_TIMEOUT_SECONDS = 3.0


class RecoveryError(Exception):
    """Only curated, non-secret messages may be shown in the console."""


class RecoverySettings(BaseSettings):
    # Do not import app.core.config: recovery must work with CognoDB offline and
    # without graph credentials. Follow the app's AUTH_DB_PATH precedence only.
    auth_db_path: Path = BACKEND_DIR / "data" / "auth.sqlite3"
    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env", env_file_encoding="utf-8", extra="ignore"
    )


@dataclass(frozen=True)
class RecoveryTarget:
    path: Path
    user_id: str
    email: str
    database_identity: tuple[int, int] = field(repr=False)
    state_fingerprint: str = field(repr=False)


@dataclass(frozen=True)
class RecoveryResult:
    revoked_sessions: int
    cleared_account_limits: int


def _existing_database(path: Path) -> tuple[Path, tuple[int, int]]:
    if path.is_symlink():
        raise RecoveryError("Không dùng file DB là symlink. Hãy chỉ định file thật.")
    try:
        resolved = path.resolve(strict=True)
        if not resolved.is_file():
            raise OSError
        info = resolved.stat()
    except (OSError, ValueError) as exc:
        raise RecoveryError(
            "Không tìm thấy file DB tài khoản hiện có. Không tạo DB mới."
        ) from exc
    return resolved, (info.st_dev, info.st_ino)


@contextmanager
def _connection(path: Path, *, write: bool = False):
    mode = "rw" if write else "ro"
    db = sqlite3.connect(
        path.as_uri() + f"?mode={mode}",
        uri=True,
        timeout=SQLITE_TIMEOUT_SECONDS,
        isolation_level=None,
    )
    db.row_factory = sqlite3.Row
    try:
        deadline = monotonic() + QUERY_TIMEOUT_SECONDS
        db.set_progress_handler(lambda: int(monotonic() > deadline), 1000)
        db.execute("PRAGMA trusted_schema = OFF")
        db.execute("PRAGMA foreign_keys = ON")
        if not write:
            db.execute("PRAGMA query_only = ON")
        yield db
    finally:
        # Closing an uncommitted connection also rolls back on Ctrl+C/errors.
        db.close()


def _validate_schema(db: sqlite3.Connection):
    objects = {
        tuple(row)
        for row in db.execute(
            "SELECT type, name FROM sqlite_master WHERE name NOT GLOB 'sqlite_*'"
        )
    }
    expected = {("table", name) for name in AUTH_COLUMNS} | {("index", "sessions_user")}
    if objects != expected:
        raise RecoveryError("Schema auth không được hỗ trợ. Không tự migration.")
    for table, columns in AUTH_COLUMNS.items():
        # Identifiers come only from the app-owned schema, never console input.
        actual = [row["name"] for row in db.execute(f"PRAGMA table_info({table})")]
        if actual != columns.split(", "):
            raise RecoveryError("Schema auth không được hỗ trợ. Không tự migration.")
    if [tuple(row) for row in db.execute("PRAGMA quick_check(1)")] != [("ok",)]:
        raise RecoveryError("DB không qua kiểm tra toàn vẹn. Cần kiểm tra bản sao lưu.")
    if db.execute("PRAGMA foreign_key_check").fetchone():
        raise RecoveryError(
            "DB có quan hệ auth không hợp lệ. Không tiếp tục khôi phục."
        )


def _require_admin(row: sqlite3.Row | None):
    if row is None:
        raise RecoveryError(
            "Không tìm thấy tài khoản. Công cụ không tạo tài khoản mới."
        )
    if row["role"] != "ADMIN" or row["is_active"] != 1:
        raise RecoveryError(
            "Chỉ khôi phục Admin đang hoạt động; không nâng quyền hoặc mở khóa."
        )


def _fingerprint(row: sqlite3.Row) -> str:
    # Include the password hash and grants without exposing either in previews.
    encoded = json.dumps(dict(row), sort_keys=True, ensure_ascii=True).encode()
    return hashlib.sha256(encoded).hexdigest()


def inspect_admin(path: Path, email: str) -> RecoveryTarget:
    try:
        normalized = str(TypeAdapter(EmailStr).validate_python(email.strip())).lower()
    except ValidationError as exc:
        raise RecoveryError("Email không hợp lệ.") from exc
    resolved, identity = _existing_database(path)
    with _connection(resolved) as db:
        db.execute("BEGIN")
        _validate_schema(db)
        row = db.execute(
            f"SELECT {AUTH_COLUMNS['users']} FROM users WHERE email = ?",
            (normalized,),
        ).fetchone()
        _require_admin(row)
        return RecoveryTarget(
            resolved, row["user_id"], row["email"], identity, _fingerprint(row)
        )


def recover_admin(target: RecoveryTarget, password: str) -> RecoveryResult:
    """Caller must confirm the preview first. Update one account atomically."""
    try:
        validated = PasswordReset(password=password)
    except ValidationError as exc:
        raise RecoveryError(
            "Mật khẩu phải dài 15–128 ký tự, không tự bỏ khoảng trắng."
        ) from exc
    password = validated.password.get_secret_value()
    resolved, identity = _existing_database(target.path)
    if resolved != target.path or identity != target.database_identity:
        raise RecoveryError(
            "File DB đã thay đổi sau khi xem thông tin. Hãy kiểm tra lại."
        )
    # Expensive hashing happens before acquiring the database write lock.
    hashed = password_hash.hash(password)
    with _connection(resolved, write=True) as db:
        db.execute("BEGIN IMMEDIATE")
        _validate_schema(db)
        row = db.execute(
            f"SELECT {AUTH_COLUMNS['users']} FROM users WHERE user_id = ?",
            (target.user_id,),
        ).fetchone()
        _require_admin(row)
        if (
            row["email"] != target.email
            or _fingerprint(row) != target.state_fingerprint
        ):
            raise RecoveryError(
                "Tài khoản đã thay đổi sau khi xác nhận. Hãy kiểm tra lại."
            )
        if password_hash.verify(password, row["password_hash"]):
            raise RecoveryError("Mật khẩu khôi phục phải khác mật khẩu hiện tại.")
        result = db.execute(
            "UPDATE users SET password_hash = ?, must_change_password = 1 "
            "WHERE user_id = ? AND email = ? AND role = 'ADMIN' AND is_active = 1",
            (hashed, target.user_id, target.email),
        )
        if result.rowcount != 1:
            raise RecoveryError("Không xác nhận được đúng một tài khoản cần khôi phục.")
        revoked = db.execute(
            "DELETE FROM sessions WHERE user_id = ?", (target.user_id,)
        ).rowcount
        cleared = db.execute(
            "DELETE FROM login_limits WHERE key IN (?, ?)",
            (
                "account:" + digest(target.email),
                "account:" + digest("password-change:" + target.user_id),
            ),
        ).rowcount
        db.commit()
    return RecoveryResult(revoked, cleared)


class _SafeParser(argparse.ArgumentParser):
    def error(self, message):
        # argparse's default echoes unknown arguments, possibly a pasted password.
        self.exit(
            2, "Tham số không hợp lệ. Dùng --help; không truyền mật khẩu qua lệnh.\n"
        )


def main(argv: list[str] | None = None) -> int:
    parser = _SafeParser(description="Khôi phục một Admin hiện có qua terminal riêng.")
    parser.add_argument(
        "--db-path", type=Path, help="File SQLite hiện có; mặc định theo AUTH_DB_PATH."
    )
    args = parser.parse_args(argv)
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        print(
            "Cần terminal tương tác riêng. Không pipe input hoặc chuyển output vào file."
        )
        return 2
    try:
        path = (
            args.db_path
            if args.db_path is not None
            else RecoverySettings().auth_db_path
        )
        resolved, _ = _existing_database(path)
        print("Công cụ quản trị cục bộ — không đọc lại mật khẩu cũ.")
        print("DB sẽ dùng:", json.dumps(str(resolved), ensure_ascii=False))
        print(
            "Dừng BE/các bên ghi auth và chuẩn bị bản sao lưu an toàn trước khi tiếp tục."
        )
        target = inspect_admin(resolved, input("Email Admin cần khôi phục: "))
        print("Tài khoản:", json.dumps(target.email, ensure_ascii=False))
        print("Mã tài khoản:", json.dumps(target.user_id, ensure_ascii=False))
        print("Role: ADMIN; trạng thái: đang hoạt động.")
        print(
            "Sẽ đổi mật khẩu, thu hồi phiên và xóa bộ đếm thử sai riêng của tài khoản này."
        )
        print("Không xóa giới hạn IP; không sửa tài khoản khác hoặc dữ liệu graph.")
        confirmation = f"KHOI PHUC {target.email}"
        if (
            input(
                f"Đã kiểm tra đúng DB và tạm dừng ghi? Gõ '{confirmation}' để tiếp tục: "
            )
            != confirmation
        ):
            print("Đã hủy trước khi ghi. Không thay đổi tài khoản.")
            return 1
        with warnings.catch_warnings():
            # getpass may otherwise fall back to echoing stdin on unsupported terminals.
            warnings.simplefilter("error", GetPassWarning)
            password = getpass("Mật khẩu khôi phục tạm (15–128 ký tự; nhập ẩn): ")
            repeat = getpass("Nhập lại mật khẩu khôi phục tạm: ")
        if password != repeat:
            print("Hai mật khẩu không khớp. Không thay đổi tài khoản.")
            return 1
        result = recover_admin(target, password)
    except RecoveryError as exc:
        print(str(exc))
        return 1
    except GetPassWarning:
        print(
            "Terminal không hỗ trợ nhập ẩn. Đã dừng; hãy dùng PowerShell/Windows Terminal."
        )
        return 2
    except (EOFError, KeyboardInterrupt):
        print(
            "\nĐã ngắt công cụ. Nếu ngắt lúc đang ghi, kiểm tra trạng thái trước khi thử lại."
        )
        return 130
    except Exception:
        # Never print SQLite/settings/hash exceptions, their inputs or a traceback.
        print(
            "Không hoàn tất khôi phục. Kiểm tra đường dẫn, quyền file, khóa DB và phiên bản schema."
        )
        return 1
    print(f"Đã khôi phục Admin; thu hồi {result.revoked_sessions} phiên cũ.")
    print(
        "Khởi động lại BE, đăng nhập bằng mật khẩu tạm rồi bắt buộc đổi mật khẩu trên giao diện."
    )
    print(
        "Giới hạn thử sai theo IP vẫn giữ nguyên; nếu gặp 429, chờ hết cửa sổ giới hạn."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
