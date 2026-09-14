"""Opt-in real application server for graph E2E. No service/auth mocks."""

import logging
import os
from pathlib import Path

from scripts.backup_support.graph import endpoint_fingerprint
from scripts.graph_e2e import run_directory


def main():
    run_id = os.environ.get("SKILLGRAPH_E2E_RUN", "")
    directory = run_directory(run_id)
    identity = endpoint_fingerprint(os.environ.get("COGNODB_URI", ""))
    if identity != os.environ.get("SKILLGRAPH_E2E_APPROVED"):
        raise RuntimeError("Use the guarded graph_e2e runner.")
    auth_path = Path(os.environ.get("AUTH_DB_PATH", "")).resolve()
    if auth_path != (directory / "auth.sqlite3").resolve() or auth_path.exists():
        raise RuntimeError("A new run-specific auth database is required.")
    password = os.environ.get("SKILLGRAPH_E2E_PASSWORD", "")
    if len(password) < 30:
        raise RuntimeError("Missing generated test credentials.")
    # Import only AFTER the runner supplied the approved target and auth path.
    import uvicorn

    from app.main import app
    from app.repositories.auth_store import AuthStore

    logging.getLogger("neo4j").setLevel(logging.CRITICAL)
    AuthStore(auth_path).create_user(
        {
            "email": "e2e-admin@example.com",
            "name": f"E2E {run_id} Admin",
            "password": password,
            "role": "ADMIN",
        },
        bootstrap=True,
    )
    uvicorn.run(
        app, host="127.0.0.1", port=18001, access_log=False, proxy_headers=False
    )


if __name__ == "__main__":
    try:
        main()
    except Exception:
        raise SystemExit(
            "Test server refused startup; use the guarded graph_e2e runner."
        ) from None
