"""Isolated browser test server. Never points at the user's graph/auth databases."""

import os
from pathlib import Path
from tempfile import TemporaryDirectory

os.environ["COGNODB_URI"] = "bolt://127.0.0.1:1"
os.environ["COGNODB_USER"] = "browser-test"
os.environ["COGNODB_PASSWORD"] = "not-a-real-credential"


def main():
    import uvicorn

    from app.api import dashboard, employees, projects, skills
    from app.api.auth_dependencies import get_auth_store
    from app.core.config import settings
    from app.main import app
    from app.repositories.auth_store import AuthStore

    settings.auth_cookie_secure = False
    settings.auth_allowed_origins = ["http://127.0.0.1:5174"]

    # Graph reads are stubbed. Authentication is the real implementation.
    def empty_list(search, state, limit, offset):
        return {"items": [], "total": 0, "limit": limit, "offset": offset}

    employees.service.list = empty_list
    projects.project_service.list = empty_list
    skills.service.list = empty_list
    from datetime import UTC, datetime

    dashboard.service.overview = lambda: {
        "generated_at": datetime.now(UTC),
        "summary": {
            "employee_count": 0,
            "available_employee_count": 0,
            "project_count": 0,
            "active_project_count": 0,
            "skill_count": 0,
        },
        "capacity": [],
        "default_project": None,
    }
    with TemporaryDirectory(prefix="skillgraph-auth-browser-") as directory:
        store = AuthStore(Path(directory) / "auth.sqlite3")
        store.create_user(
            {
                "email": "browser-admin@example.com",
                "name": "Browser Admin",
                "password": "Browser-only initial password!",
                "role": "ADMIN",
            },
            bootstrap=True,
        )
        app.dependency_overrides[get_auth_store] = lambda: store
        uvicorn.run(
            app, host="127.0.0.1", port=18000, access_log=False, proxy_headers=False
        )


if __name__ == "__main__":
    main()
