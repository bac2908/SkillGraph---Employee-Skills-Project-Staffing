import secrets

import pytest
from fastapi.testclient import TestClient

from app.api.auth_dependencies import get_auth_store
from app.main import app
from app.repositories.auth_store import AuthStore


@pytest.fixture
def authenticated_client(tmp_path):
    """Real login, but auth records are isolated from the user's accounts."""
    store = AuthStore(tmp_path / "integration-auth.sqlite3")
    password = secrets.token_urlsafe(32)
    store.create_user(
        {
            "email": "integration@example.com",
            "name": "Integration Test",
            "password": password,
            "role": "ADMIN",
        },
        bootstrap=True,
    )
    app.dependency_overrides[get_auth_store] = lambda: store
    try:
        with TestClient(app, headers={"Origin": "http://127.0.0.1:5173"}) as client:
            response = client.post(
                "/api/auth/login",
                json={"email": "integration@example.com", "password": password},
            )
            assert response.status_code == 200
            client.headers["X-CSRF-Token"] = response.json()["csrf_token"]
            yield client
    finally:
        app.dependency_overrides.pop(get_auth_store, None)
