"""Explicit live readiness check. No bootstrap, mutation, or fixture writes."""

from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.mark.integration
def test_live_readiness_and_liveness(monkeypatch):
    import app.main as main

    # This probe owns its async driver, not the repository driver's lifecycle.
    # Do not close a shared driver used by another integration test in this process.
    monkeypatch.setattr(main, "graph_db", SimpleNamespace(close=lambda: None))
    with TestClient(app) as client:
        assert client.get("/health").json() == {"status": "ok"}
        response = client.get("/health/ready")
        assert response.status_code == 200, response.text
        assert response.json() == {"status": "ready"}
        assert response.headers["cache-control"] == "no-store"
