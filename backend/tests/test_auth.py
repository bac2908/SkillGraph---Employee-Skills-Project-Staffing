"""Authentication/RBAC tests use temporary SQLite and never connect to CognoDB."""

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.api.auth_dependencies import COOKIE_NAME, get_auth_store
from app.core.config import settings
from app.core.exceptions import ResourceNotFoundError
from app.db.graph import graph_db
from app.main import app
from app.repositories.auth_store import AuthError, AuthStore, digest

ORIGIN = "http://127.0.0.1:5173"
PASSWORD = "Test-only password 2026!"
NEW_PASSWORD = "New test-only password 2026!"


@pytest.fixture
def setup(tmp_path):
    store = AuthStore(tmp_path / "auth.sqlite3")
    admin = store.create_user(
        {
            "name": "Admin",
            "email": "admin@example.com",
            "password": PASSWORD,
            "role": "ADMIN",
        },
        bootstrap=True,
    )
    app.dependency_overrides[get_auth_store] = lambda: store
    client = TestClient(app, headers={"Origin": ORIGIN})
    yield client, store, admin
    client.close()
    app.dependency_overrides.pop(get_auth_store, None)


def login(client, email="admin@example.com", password=PASSWORD):
    result = client.post("/api/auth/login", json={"email": email, "password": password})
    assert result.status_code == 200, result.text
    client.headers["X-CSRF-Token"] = result.json()["csrf_token"]
    return result


def ready_user(store, role, projects=None):
    user = store.create_user(
        {
            "name": role,
            "email": ("second-admin" if role == "ADMIN" else role.lower())
            + "@example.com",
            "password": PASSWORD,
            "role": role,
            "project_ids": projects or [],
        }
    )
    with store.connection() as db:
        db.execute(
            "UPDATE users SET must_change_password = 0 WHERE user_id = ?",
            (user["user_id"],),
        )
    return user


BUSINESS_ROUTES = [
    (
        method.upper(),
        path.replace("{employee_id}", "EMP001")
        .replace("{skill_id}", "SK001")
        .replace("{project_id}", "PROJ001"),
    )
    for path, operations in app.openapi()["paths"].items()
    if path.startswith("/api/") and not path.startswith("/api/auth/")
    for method in operations
    if method in {"get", "post", "put", "patch", "delete"}
]


@pytest.mark.parametrize("method,path", BUSINESS_ROUTES)
def test_every_business_endpoint_requires_login(setup, method, path):
    client, _, _ = setup
    assert client.request(method, path).status_code == 401


def test_login_cookie_storage_cache_rotation_and_logout(setup):
    client, store, _ = setup
    result = login(client)
    cookie = result.headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=lax" in cookie and "path=/" in cookie
    token = client.cookies.get(COOKIE_NAME)
    with store.connection() as db:
        row = db.execute("SELECT * FROM sessions").fetchone()
        password = db.execute("SELECT password_hash FROM users").fetchone()[0]
    assert row["token_hash"] == digest(token) and token not in str(dict(row))
    assert password.startswith("$argon2id$") and PASSWORD not in password
    assert "password" not in result.json()["user"]
    assert client.get("/api/auth/me").headers["cache-control"] == "no-store"
    login(client)
    assert client.cookies.get(COOKIE_NAME) != token
    with pytest.raises(AuthError):
        store.authenticate(token)
    latest = client.cookies.get(COOKIE_NAME)
    assert client.post("/api/auth/logout").status_code == 204
    assert client.get("/api/auth/me").status_code == 401
    with pytest.raises(AuthError):
        store.authenticate(latest)


def test_login_failure_is_generic_and_rate_limited(setup):
    client, _, _ = setup
    response = client.post(
        "/api/auth/login", json={"email": "nobody@example.com", "password": PASSWORD}
    )
    missing = response.json()
    for _ in range(5):
        response = client.post(
            "/api/auth/login", json={"email": "admin@example.com", "password": "wrong"}
        )
        assert response.status_code == 401 and response.json() == missing
    response = client.post(
        "/api/auth/login", json={"email": "admin@example.com", "password": PASSWORD}
    )
    assert response.status_code == 429 and response.headers["retry-after"] == "900"


def test_origin_and_csrf_are_both_required(setup):
    client, _, _ = setup
    payload = {"email": "admin@example.com", "password": PASSWORD}
    assert (
        client.post(
            "/api/auth/login", json=payload, headers={"Origin": "https://evil.example"}
        ).status_code
        == 403
    )
    result = login(client)
    client.headers.pop("X-CSRF-Token")
    assert client.post("/api/auth/logout").status_code == 403
    client.headers["X-CSRF-Token"] = result.json()["csrf_token"]
    assert (
        client.post("/api/auth/logout", headers={"Origin": "null"}).status_code == 403
    )
    assert client.get("/api/auth/me").status_code == 200


def test_secure_cookie_can_be_enabled(setup, monkeypatch):
    client, _, _ = setup
    monkeypatch.setattr(settings, "auth_cookie_secure", True)
    assert "Secure" in login(client).headers["set-cookie"]


@pytest.mark.parametrize("expired_column", ["expires_at", "last_seen"])
def test_absolute_and_idle_session_expiration(setup, expired_column):
    client, store, _ = setup
    login(client)
    with store.connection() as db:
        if expired_column == "expires_at":
            db.execute("UPDATE sessions SET expires_at = 0")
        else:
            db.execute("UPDATE sessions SET last_seen = 0")
    assert client.get("/api/auth/me").status_code == 401


def test_password_change_required_and_revokes_all_sessions(setup):
    client, store, _ = setup
    user = store.create_user(
        {
            "email": "viewer@example.com",
            "name": "Viewer",
            "password": PASSWORD,
            "role": "VIEWER",
        }
    )
    login(client, user["email"])
    old_token = client.cookies.get(COOKIE_NAME)
    assert client.get("/api/employees").status_code == 403
    response = client.post(
        "/api/auth/password",
        json={"current_password": PASSWORD, "new_password": NEW_PASSWORD},
    )
    assert response.status_code == 204
    with pytest.raises(AuthError):
        store.authenticate(old_token)
    assert not login(client, user["email"], NEW_PASSWORD).json()["user"][
        "must_change_password"
    ]


def test_admin_user_lifecycle_and_no_self_lockout(setup, monkeypatch):
    client, store, admin = setup
    monkeypatch.setattr(
        "app.api.auth.ProjectService.get", lambda self, pid: {"project_id": pid}
    )
    login(client)
    response = client.post(
        "/api/auth/users",
        json={
            "email": "Manager@example.com",
            "name": "Manager",
            "password": PASSWORD,
            "role": "MANAGER",
            "project_ids": ["PROJ001"],
        },
    )
    assert response.status_code == 201, response.text
    user = response.json()
    assert user["email"] == "manager@example.com" and user["must_change_password"]
    assert client.get("/api/auth/users?limit=1").json()["total"] == 2
    assert (
        client.patch(
            f"/api/auth/users/{admin['user_id']}",
            json={"role": "VIEWER", "is_active": True},
        ).status_code
        == 409
    )
    _, token = store.login(user["email"], PASSWORD, "manager-device", None)
    response = client.patch(
        f"/api/auth/users/{user['user_id']}",
        json={"role": "MANAGER", "is_active": True, "project_ids": ["PROJ002"]},
    )
    assert response.status_code == 200
    with pytest.raises(AuthError):
        store.authenticate(token)
    assert (
        client.post(
            f"/api/auth/users/{user['user_id']}/password",
            json={"password": NEW_PASSWORD},
        ).status_code
        == 204
    )
    assert (
        client.patch(
            f"/api/auth/users/{user['user_id']}",
            json={"role": "VIEWER", "is_active": False},
        ).status_code
        == 200
    )
    with pytest.raises(AuthError):
        store.login(user["email"], NEW_PASSWORD, "manager-device", None)


def test_validation_does_not_echo_passwords(setup):
    client, _, _ = setup
    login(client)
    secret = "do-not-echo"
    response = client.post(
        "/api/auth/users",
        json={"email": "v@example.com", "name": "V", "password": secret},
    )
    assert response.status_code == 422 and secret not in response.text
    assert (
        client.post(
            "/api/auth/users",
            json={
                "email": "v@example.com",
                "name": "V",
                "password": PASSWORD,
                "role": "SUPERUSER",
            },
        ).status_code
        == 422
    )


@pytest.mark.parametrize(
    "role,project_id,expected",
    [
        ("VIEWER", "PROJ001", 403),
        ("MANAGER", "PROJ002", 403),
        ("MANAGER", "PROJ001", 404),
        ("ADMIN", "PROJ002", 404),
    ],
)
@pytest.mark.parametrize(
    "method,suffix,payload,service,operation",
    [
        ("PATCH", "", {"description": "Updated"}, "projects.project_service", "update"),
        (
            "PUT",
            "/assignments/EMP001",
            {"role": "Developer", "allocation": 20},
            "project_assignments.service",
            "upsert",
        ),
        (
            "DELETE",
            "/assignments/EMP001",
            None,
            "project_assignments.service",
            "delete",
        ),
        (
            "PUT",
            "/requirements/SK001",
            {"min_level": 3, "priority": "MUST"},
            "project_requirements.service",
            "upsert",
        ),
        (
            "DELETE",
            "/requirements/SK001",
            None,
            "project_requirements.service",
            "delete",
        ),
    ],
)
def test_project_write_permissions(
    setup,
    monkeypatch,
    role,
    project_id,
    expected,
    method,
    suffix,
    payload,
    service,
    operation,
):
    client, store, _ = setup
    if role != "ADMIN":
        user = ready_user(store, role, ["PROJ001"] if role == "MANAGER" else [])
        login(client, user["email"])
    else:
        login(client)
    calls = []

    def reached(*args, **kwargs):
        calls.append(True)
        raise ResourceNotFoundError("Test sentinel", "no-graph")

    monkeypatch.setattr("app.api." + service + "." + operation, reached)
    result = client.request(method, f"/api/projects/{project_id}{suffix}", json=payload)
    assert result.status_code == expected, result.text
    assert bool(calls) == (expected == 404)


@pytest.mark.parametrize("role", ["MANAGER", "VIEWER"])
def test_catalog_and_account_writes_are_admin_only(setup, role):
    client, store, _ = setup
    user = ready_user(store, role, ["PROJ001"] if role == "MANAGER" else [])
    login(client, user["email"])
    for method, path in [
        ("POST", "/api/employees"),
        ("PATCH", "/api/employees/EMP001"),
        ("PUT", "/api/employees/EMP001/skills/SK001"),
        ("POST", "/api/skills"),
        ("DELETE", "/api/skills/SK001"),
        ("POST", "/api/projects"),
        ("DELETE", "/api/projects/PROJ001"),
        ("GET", "/api/auth/users"),
        ("POST", "/api/auth/users"),
    ]:
        assert client.request(method, path).status_code == 403


def test_bootstrap_is_single_use_even_with_concurrency(tmp_path):
    store = AuthStore(tmp_path / "bootstrap.sqlite3")

    def create(index):
        try:
            store.create_user(
                {
                    "name": "Admin",
                    "email": f"a{index}@example.com",
                    "password": PASSWORD,
                    "role": "ADMIN",
                },
                bootstrap=True,
            )
            return True
        except AuthError:
            return False

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sum(pool.map(create, range(2))) == 1
    assert store.list_users(10, 0)["total"] == 1


def test_store_persists_and_health_is_public(setup):
    client, store, _ = setup
    assert AuthStore(Path(store.path)).list_users(10, 0)["total"] == 1
    assert client.get("/health").json() == {"status": "ok"}


@pytest.mark.parametrize("role", ["VIEWER", "MANAGER", "ADMIN"])
def test_authenticated_roles_can_read_shared_data(setup, role, monkeypatch):
    client, store, _ = setup
    if role != "ADMIN":
        user = ready_user(store, role)
        login(client, user["email"])
    else:
        login(client)
    monkeypatch.setattr(
        "app.api.employees.service.list",
        lambda *args: {"items": [], "total": 0, "limit": 20, "offset": 0},
    )
    assert client.get("/api/employees").status_code == 200


def test_session_limit_and_persistent_rate_limit(setup):
    client, store, _ = setup
    tokens = [
        store.login("admin@example.com", PASSWORD, "test-device", None)[1]
        for _ in range(6)
    ]
    with pytest.raises(AuthError):
        store.authenticate(tokens[0])
    with store.connection() as db:
        assert db.execute("SELECT COUNT(*) FROM sessions").fetchone()[0] == 5
    for _ in range(5):
        with pytest.raises(AuthError):
            store.login("missing@example.com", PASSWORD, "another-device", None)
    reopened = AuthStore(store.path)
    with pytest.raises(AuthError) as error:
        reopened.login("missing@example.com", PASSWORD, "another-device", None)
    assert error.value.status == 429


def test_last_admin_guard_survives_concurrent_changes(setup):
    _, store, admin = setup
    second = ready_user(store, "ADMIN")

    def demote(pair):
        target, actor = pair
        try:
            store.update_user(
                target, {"role": "VIEWER", "is_active": True, "project_ids": []}, actor
            )
            return True
        except AuthError:
            return False

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(
            pool.map(
                demote,
                [
                    (admin["user_id"], second["user_id"]),
                    (second["user_id"], admin["user_id"]),
                ],
            )
        )
    assert sum(results) == 1
    assert (
        sum(
            u["role"] == "ADMIN" and u["is_active"]
            for u in store.list_users(10, 0)["items"]
        )
        == 1
    )


def test_tampered_cookie_and_csrf_cannot_authenticate(setup):
    client, _, _ = setup
    login(client)
    assert (
        client.post("/api/auth/logout", headers={"X-CSRF-Token": "0" * 64}).status_code
        == 403
    )
    client.cookies.clear()
    client.cookies.set(COOKIE_NAME, "tampered-token")
    assert client.get("/api/auth/me").status_code == 401


@pytest.mark.parametrize("role", ["VIEWER", "MANAGER"])
def test_rbac_all_business_writes_denied_outside_role_or_grant(
    setup, role, monkeypatch
):
    client, store, _ = setup
    user = ready_user(store, role, ["PROJ001"] if role == "MANAGER" else [])
    login(client, user["email"])
    blocked_graph = MagicMock(side_effect=AssertionError("Graph must not be reached"))
    monkeypatch.setattr(graph_db.driver, "session", blocked_graph)
    for method, path in BUSINESS_ROUTES:
        if method == "GET":
            continue
        target = path.replace("PROJ001", "PROJ002") if role == "MANAGER" else path
        response = client.request(method, target, json={})
        assert response.status_code == 403, (method, target, response.status_code)
        assert response.json()["detail"] == "Bạn không có quyền thay đổi dữ liệu này."
    for method, path, payload in [
        ("GET", "/api/auth/users", None),
        ("GET", "/api/activity", None),
        (
            "POST",
            "/api/auth/users",
            {
                "email": "new@example.com",
                "name": "New",
                "password": PASSWORD,
                "role": "ADMIN",
            },
        ),
        (
            "PATCH",
            f"/api/auth/users/{user['user_id']}",
            {"role": "ADMIN", "is_active": True},
        ),
        (
            "POST",
            f"/api/auth/users/{user['user_id']}/password",
            {"password": NEW_PASSWORD},
        ),
    ]:
        assert client.request(method, path, json=payload).status_code == 403
    blocked_graph.assert_not_called()


@pytest.mark.parametrize("role", ["ADMIN", "MANAGER", "VIEWER"])
def test_rbac_password_gate_covers_all_business_routes(setup, role, monkeypatch):
    client, store, _ = setup
    user = ready_user(store, role, ["PROJ001"] if role == "MANAGER" else [])
    store.reset_password(user["user_id"], NEW_PASSWORD)
    login(client, user["email"], NEW_PASSWORD)
    blocked_graph = MagicMock(side_effect=AssertionError("Graph must not be reached"))
    monkeypatch.setattr(graph_db.driver, "session", blocked_graph)
    for method, path in BUSINESS_ROUTES:
        assert client.request(method, path, json={}).status_code == 403, (method, path)
    assert client.get("/api/auth/users").status_code == 403
    assert client.get("/api/auth/me").json()["user"]["must_change_password"] is True
    blocked_graph.assert_not_called()


def test_rbac_manager_positive_2xx_for_all_five_granted_write_routes(
    setup, monkeypatch
):
    client, store, _ = setup
    user = ready_user(store, "MANAGER", ["PROJ001"])
    login(client, user["email"])
    blocked_graph = MagicMock(side_effect=AssertionError("Use synthetic services only"))
    monkeypatch.setattr(graph_db.driver, "session", blocked_graph)
    project = {
        "project_id": "PROJ001",
        "name": "Test Project",
        "description": "Updated",
        "status": "ACTIVE",
    }
    assignment = {
        "project_id": "PROJ001",
        "project_name": "Test Project",
        "employee_id": "EMP001",
        "employee_name": "Test Employee",
        "role": "Developer",
        "allocation": 20,
        "employee_total_allocation": 20,
        "employee_remaining_allocation": 80,
    }
    requirement = {
        "project_id": "PROJ001",
        "project_name": "Test Project",
        "skill_id": "SK001",
        "skill_name": "Python",
        "category": "Programming",
        "min_level": 3,
        "priority": "MUST",
    }
    cases = [
        (
            "PATCH",
            "",
            {"description": "Updated"},
            "projects.project_service.update",
            project,
            200,
        ),
        (
            "PUT",
            "/assignments/EMP001",
            {"role": "Developer", "allocation": 20},
            "project_assignments.service.upsert",
            (assignment, True),
            201,
        ),
        (
            "DELETE",
            "/assignments/EMP001",
            None,
            "project_assignments.service.delete",
            None,
            204,
        ),
        (
            "PUT",
            "/requirements/SK001",
            {"min_level": 3, "priority": "MUST"},
            "project_requirements.service.upsert",
            (requirement, True),
            201,
        ),
        (
            "DELETE",
            "/requirements/SK001",
            None,
            "project_requirements.service.delete",
            None,
            204,
        ),
    ]
    for method, suffix, payload, service, value, expected in cases:
        operation = MagicMock(return_value=value)
        monkeypatch.setattr("app.api." + service, operation)
        response = client.request(
            method, "/api/projects/PROJ001" + suffix, json=payload
        )
        assert response.status_code == expected, response.text
        assert operation.call_count == 1
        assert operation.call_args.kwargs["actor"].user_id == user["user_id"]
        denied = client.request(method, "/api/projects/PROJ002" + suffix, json=payload)
        assert denied.status_code == 403
        assert operation.call_count == 1, "Denied call must not execute mutation"
    blocked_graph.assert_not_called()
