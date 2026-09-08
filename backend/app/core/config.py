from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    cognodb_uri: str
    cognodb_user: str
    cognodb_password: str
    auth_db_path: Path = BACKEND_DIR / "data" / "auth.sqlite3"
    auth_cookie_secure: bool = False
    auth_session_hours: int = Field(default=8, ge=1, le=24)
    auth_idle_minutes: int = Field(default=30, ge=5, le=120)
    auth_allowed_origins: list[str] = [
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "http://127.0.0.1:4173",
        "http://localhost:4173",
        "http://127.0.0.1:8000",
        "http://localhost:8000",
    ]

    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
    )


settings = Settings()
