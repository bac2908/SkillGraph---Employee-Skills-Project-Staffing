"""Dashboard contract/RBAC/repository tests; no production database access."""

from copy import deepcopy
from datetime import datetime
from unittest.mock import MagicMock

import pytest
from neo4j import Record

from app.api.auth_dependencies import get_auth_store
from app.main import app
from app.repositories import dashboard_repository as repository


def overview_data():
    return {
        "summary": {
            "employee_count": 1250,
            "available_employee_count": 400,
            "project_count": 120,
            "active_project_count": 90,
            "skill_count": 250,
        },
        "capacity": [
            {
                "employee_id": "EMP001",
                "name": "Employee One",
                "title": "Engineer",
                "total_allocation": 0,
                "remaining_allocation": 100,
            }
        ],
        "default_project": {
            "project_id": "PROJ001",
            "name": "Project One",
            "description": "Dashboard test project.",
            "status": "ACTIVE",
        },
    }


@pytest.fixture(autouse=True)
def no_real_graph(monkeypatch):
    session = MagicMock(side_effect=AssertionError("Real graph access forbidden."))
    monkeypatch.setattr(repository.graph_db.driver, "session", session)
    return session


@pytest.fixture
def overview_mock(monkeypatch):
    operation = MagicMock(side_effect=lambda: deepcopy(overview_data()))
    monkeypatch.setattr(repository, "get_dashboard", operation)
    return operation


@pytest.mark.parametrize("role", ["ADMIN", "MANAGER", "VIEWER"])
def test_dashboard_all_roles_read_global_counts(
    authenticated_client, overview_mock, role
):
    client = authenticated_client
    store = app.dependency_overrides[get_auth_store]()
    user_id = client.get("/api/auth/me").json()["user"]["user_id"]
    # Test setup only: simulate each role without sharing real accounts.
    with store.connection() as db:
        db.execute("UPDATE users SET role = ? WHERE user_id = ?", (role, user_id))
    before = datetime.now().astimezone()
    response = client.get("/api/dashboard")
    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"] == overview_data()["summary"]
    assert payload["capacity"] == overview_data()["capacity"]
    assert payload["default_project"] == overview_data()["default_project"]
    generated_at = datetime.fromisoformat(payload["generated_at"])
    assert before <= generated_at <= datetime.now().astimezone()
    assert response.headers["cache-control"] == "no-store"
    assert "email" not in response.text and "password" not in response.text
    overview_mock.assert_called_once_with()


def test_dashboard_requires_login(authenticated_client, overview_mock):
    authenticated_client.cookies.clear()
    assert authenticated_client.get("/api/dashboard").status_code == 401
    overview_mock.assert_not_called()


def test_dashboard_blocks_forced_password_change(authenticated_client, overview_mock):
    store = app.dependency_overrides[get_auth_store]()
    with store.connection() as db:
        db.execute("UPDATE users SET must_change_password = 1")
    assert authenticated_client.get("/api/dashboard").status_code == 403
    overview_mock.assert_not_called()


def test_empty_workspace_is_zero_not_an_error(authenticated_client, overview_mock):
    data = overview_data()
    data["summary"] = dict.fromkeys(data["summary"], 0)
    data["capacity"] = []
    data["default_project"] = None
    overview_mock.side_effect = None
    overview_mock.return_value = data
    response = authenticated_client.get("/api/dashboard")
    assert response.status_code == 200
    assert response.json()["summary"] == data["summary"]
    assert response.json()["capacity"] == []
    assert response.json()["default_project"] is None


def test_graph_failure_is_503_not_fabricated_zero(authenticated_client, overview_mock):
    overview_mock.side_effect = repository.DashboardRepositoryError(
        "private connection details must not reach the client"
    )
    response = authenticated_client.get("/api/dashboard")
    assert response.status_code == 503
    assert response.json() == {"detail": "The graph database is currently unavailable."}
    assert "private" not in response.text and "summary" not in response.json()


def test_legacy_overallocation_remains_visible(authenticated_client, overview_mock):
    data = overview_data()
    data["capacity"][0].update(total_allocation=120, remaining_allocation=-20)
    overview_mock.side_effect = None
    overview_mock.return_value = data
    response = authenticated_client.get("/api/dashboard")
    assert response.status_code == 200
    assert response.json()["capacity"][0]["remaining_allocation"] == -20


def result(rows):
    response = MagicMock()
    records = [Record(row) for row in rows]
    response.single.return_value = records[0] if records else None
    response.__iter__.side_effect = lambda: iter(records)
    return response


@pytest.fixture
def read_transaction(no_real_graph):
    no_real_graph.side_effect = None
    session = no_real_graph.return_value.__enter__.return_value
    transaction = MagicMock()
    session.execute_read.side_effect = lambda callback: callback(transaction)
    data = overview_data()
    summary = data["summary"]
    rows = {
        repository.EMPLOYEE_SUMMARY_QUERY: [
            {
                key: summary[key]
                for key in ("employee_count", "available_employee_count")
            }
        ],
        repository.PROJECT_SUMMARY_QUERY: [
            {key: summary[key] for key in ("project_count", "active_project_count")}
        ],
        repository.SKILL_SUMMARY_QUERY: [{"skill_count": summary["skill_count"]}],
        repository.CAPACITY_QUERY: data["capacity"],
        repository.DEFAULT_PROJECT_QUERY: [data["default_project"]],
    }
    transaction.run.side_effect = lambda query, **kwargs: result(rows[query])
    return transaction, session, rows


def test_repository_fixed_five_queries_one_read_transaction(
    read_transaction, no_real_graph
):
    transaction, session, _ = read_transaction
    assert repository.get_dashboard() == overview_data()
    no_real_graph.assert_called_once_with()
    session.execute_read.assert_called_once_with(repository._get_dashboard)
    assert transaction.run.call_count == 5
    transaction.run.assert_any_call(repository.CAPACITY_QUERY, limit=5)
    assert "LIMIT $limit" in repository.CAPACITY_QUERY
    assert "LIMIT 1" in repository.DEFAULT_PROJECT_QUERY
    session.execute_write.assert_not_called()
    no_real_graph.return_value.__exit__.assert_called_once()


def test_repository_empty_aggregations(read_transaction):
    _, _, rows = read_transaction
    for query in (
        repository.EMPLOYEE_SUMMARY_QUERY,
        repository.PROJECT_SUMMARY_QUERY,
        repository.SKILL_SUMMARY_QUERY,
    ):
        rows[query] = [dict.fromkeys(rows[query][0], 0)]
    rows[repository.CAPACITY_QUERY] = []
    rows[repository.DEFAULT_PROJECT_QUERY] = []
    data = repository.get_dashboard()
    assert all(value == 0 for value in data["summary"].values())
    assert data["capacity"] == [] and data["default_project"] is None


@pytest.mark.parametrize(
    "missing_query",
    [
        repository.EMPLOYEE_SUMMARY_QUERY,
        repository.PROJECT_SUMMARY_QUERY,
        repository.SKILL_SUMMARY_QUERY,
    ],
)
def test_missing_aggregate_is_not_silently_zero(read_transaction, missing_query):
    _, _, rows = read_transaction
    rows[missing_query] = []
    with pytest.raises(repository.DashboardRepositoryError):
        repository.get_dashboard()


@pytest.mark.parametrize("failure_at", range(5))
def test_query_failure_closes_session_and_never_returns_partial_dashboard(
    read_transaction, no_real_graph, failure_at
):
    transaction, _, rows = read_transaction
    answers = [result(value) for value in rows.values()]
    failure = RuntimeError("Simulated connection failure")
    answers[failure_at] = failure
    transaction.run.side_effect = answers
    with pytest.raises(repository.DashboardRepositoryError) as caught:
        repository.get_dashboard()
    assert caught.value.__cause__ is failure
    no_real_graph.return_value.__exit__.assert_called_once()
