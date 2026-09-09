"""Activity API/security/unit tests. Never connect to a real graph."""

import json
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from neo4j import Record

from app.api.auth_dependencies import get_auth_store
from app.core.audit import AuditActor, AuditContext
from app.core.exceptions import ResourceNotFoundError
from app.main import app
from app.repositories import activity_repository as activity
from app.repositories import project_assignment_repository as assignments
from app.repositories import project_repository as projects
from app.repositories import project_requirement_repository as requirements
from app.services.activity_service import decode_cursor, encode_cursor


def event(**updates):
    return {
        "event_id": str(uuid4()),
        "occurred_at": "2026-09-10T03:00:00.000000Z",
        "actor_id": "actor-test",
        "actor_name": "Test Admin",
        "project_id": "PROJ001",
        "action": "UPDATED",
        "resource_type": "WORKS_ON",
        "resource_id": "PROJ001/EMP001",
        "before": {"allocation": 40},
        "after": {"allocation": 60},
        **updates,
    }


@pytest.fixture(autouse=True)
def block_graph(monkeypatch):
    factory = MagicMock(side_effect=AssertionError("Real graph access forbidden"))
    monkeypatch.setattr(activity.graph_db.driver, "session", factory)
    return factory


@pytest.fixture
def read_events(monkeypatch):
    operation = MagicMock(return_value=[event()])
    monkeypatch.setattr(activity, "list_events", operation)
    return operation


@pytest.mark.parametrize("role", ["MANAGER", "VIEWER"])
def test_history_is_admin_only(authenticated_client, read_events, role):
    store = app.dependency_overrides[get_auth_store]()
    with store.connection() as db:
        db.execute("UPDATE users SET role = ?", (role,))
    assert (
        authenticated_client.get("/api/activity?project_id=PROJ001").status_code == 403
    )
    read_events.assert_not_called()


def test_admin_can_read_deleted_project_history_with_filters(
    authenticated_client, read_events
):
    response = authenticated_client.get(
        "/api/activity",
        params={
            "project_id": "PROJ001",
            "action": "UPDATED",
            "resource_type": "WORKS_ON",
            "actor": "  Test Admin  ",
            "since": "2026-09-10T08:00:00+07:00",
            "until": "2026-09-10T23:00:00+07:00",
            "limit": 2,
        },
    )
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert response.json()["items"][0]["before"] == {"allocation": 40}
    assert response.json()["next_cursor"] is None
    parameters = read_events.call_args.args[0]
    assert parameters["fetch_limit"] == 3
    assert parameters["since"] == "2026-09-10T01:00:00.000000Z"
    assert parameters["until"] == "2026-09-10T16:00:00.000000Z"
    assert parameters["actor"] == "Test Admin"
    # No graph project-existence query: historical IDs may no longer exist.


def test_cursor_page_has_no_offset_and_round_trips(authenticated_client, read_events):
    rows = [
        event(event_id=f"00000000-0000-0000-0000-{index:012d}") for index in (3, 2, 1)
    ]
    read_events.return_value = rows
    response = authenticated_client.get("/api/activity?limit=2").json()
    assert len(response["items"]) == 2
    assert decode_cursor(response["next_cursor"]) == (
        rows[1]["occurred_at"],
        rows[1]["event_id"],
    )
    read_events.return_value = rows[2:]
    second = authenticated_client.get(
        "/api/activity", params={"limit": 2, "cursor": response["next_cursor"]}
    )
    assert second.status_code == 200
    assert second.json()["next_cursor"] is None
    assert read_events.call_args.args[0]["cursor_id"] == rows[1]["event_id"]


@pytest.mark.parametrize(
    "parameters",
    [
        {"limit": 0},
        {"limit": 101},
        {"cursor": "!!!"},
        {"cursor": "W10"},
        {"cursor": "a" * 513},
        {"project_id": "arbitrary"},
        {"action": "LOGIN"},
        {"resource_type": "USER"},
        {"actor": "a" * 101},
        {"since": "2026-09-10T00:00:00"},
        {"since": "2026-09-11T00:00:00Z", "until": "2026-09-10T00:00:00Z"},
    ],
)
def test_invalid_filters_never_reach_graph(
    authenticated_client, read_events, parameters
):
    assert (
        authenticated_client.get("/api/activity", params=parameters).status_code == 422
    )
    read_events.assert_not_called()


def test_empty_and_failure_are_distinct(authenticated_client, read_events):
    read_events.return_value = []
    assert authenticated_client.get("/api/activity").json() == {
        "items": [],
        "next_cursor": None,
    }
    read_events.side_effect = activity.ActivityRepositoryError("private details")
    response = authenticated_client.get("/api/activity")
    assert response.status_code == 503 and "private" not in response.text


WRITE_ROUTES = [
    (
        "POST",
        "/api/projects",
        {"project_id": "PROJ001", "name": "Project", "description": "Test"},
        "projects.project_service.create",
    ),
    (
        "PATCH",
        "/api/projects/PROJ001",
        {"name": "Changed"},
        "projects.project_service.update",
    ),
    ("DELETE", "/api/projects/PROJ001", None, "projects.project_service.delete"),
    (
        "PUT",
        "/api/projects/PROJ001/assignments/EMP001",
        {"role": "Engineer", "allocation": 40},
        "project_assignments.service.upsert",
    ),
    (
        "DELETE",
        "/api/projects/PROJ001/assignments/EMP001",
        None,
        "project_assignments.service.delete",
    ),
    (
        "PUT",
        "/api/projects/PROJ001/requirements/SK001",
        {"min_level": 3, "priority": "MUST"},
        "project_requirements.service.upsert",
    ),
    (
        "DELETE",
        "/api/projects/PROJ001/requirements/SK001",
        None,
        "project_requirements.service.delete",
    ),
]


@pytest.mark.parametrize("method,path,payload,operation", WRITE_ROUTES)
def test_write_actor_comes_from_authenticated_session(
    authenticated_client, monkeypatch, method, path, payload, operation
):
    user = authenticated_client.get("/api/auth/me").json()["user"]
    seen = []

    def capture(*args, actor):
        seen.append(actor)
        raise ResourceNotFoundError("Test sentinel", "no graph")

    monkeypatch.setattr("app.api." + operation, capture)
    response = authenticated_client.request(
        method, path, json=payload, headers={"X-Actor-Id": "forged"}
    )
    assert response.status_code == 404
    assert seen == [AuditActor(user["user_id"], user["name"])]
    if payload:
        response = authenticated_client.request(
            method, path, json={**payload, "actor_id": "forged"}
        )
        assert response.status_code == 422


@pytest.mark.parametrize(
    "kind,before,after",
    [
        (
            "PROJECT",
            None,
            {"project_id": "PROJ001", "name": "New", "password": "secret"},
        ),
        (
            "WORKS_ON",
            {"allocation": 40, "session_token": "secret"},
            {"allocation": 60, "email": "secret"},
        ),
        ("REQUIRES_SKILL", {"min_level": 3, "csrf_token": "secret"}, None),
    ],
)
def test_write_event_allowlist_and_same_transaction(kind, before, after):
    context = AuditContext.create(AuditActor("user-one", "Admin"))
    transaction = MagicMock()
    transaction.run.return_value.single.return_value = Record(
        {"event_id": context.event_id}
    )
    activity.write_event(
        transaction, context, "PROJ001", kind, "resource", before, after
    )
    transaction.run.assert_called_once()
    props = transaction.run.call_args.kwargs["properties"]
    assert "secret" not in json.dumps(props)
    assert props["actor_id"] == "user-one"
    assert props["action"] == (
        "CREATED" if before is None else "DELETED" if after is None else "UPDATED"
    )
    assert props["event_id"] == context.event_id


def test_noop_does_not_add_history_and_missing_write_fails():
    context = AuditContext.create(AuditActor("user-one", "Admin"))
    transaction = MagicMock()
    activity.write_event(
        transaction,
        context,
        "PROJ001",
        "PROJECT",
        "PROJ001",
        {"name": "Same"},
        {"name": "Same"},
    )
    transaction.run.assert_not_called()
    transaction.run.return_value.single.return_value = None
    with pytest.raises(activity.ActivityRepositoryError):
        activity.write_event(
            transaction, context, "PROJ001", "PROJECT", "PROJ001", None, {"name": "New"}
        )


def result(data):
    value = MagicMock()
    value.single.return_value = Record(data) if data is not None else None
    return value


@pytest.mark.parametrize(
    "module,callback,args,answers",
    [
        (
            projects,
            projects._create_project,
            ({"project_id": "PROJ001"},),
            [{"project_id": "PROJ001", "name": "New"}],
        ),
        (
            projects,
            projects._update_project,
            ("PROJ001", {"name": "New"}),
            [{"before": {"name": "Old"}}, {"project_id": "PROJ001", "name": "New"}],
        ),
        (
            projects,
            projects._delete_project,
            ("PROJ001",),
            [{"relationship_count": 0, "before": {"name": "Old"}}, {}],
        ),
        (
            assignments,
            assignments._upsert_project_assignment,
            ("PROJ001", "EMP001", "Engineer", 40),
            [
                {"allocated_elsewhere": 0},
                None,
                {
                    "project_id": "PROJ001",
                    "employee_id": "EMP001",
                    "allocation": 40,
                    "role": "Engineer",
                },
            ],
        ),
        (
            assignments,
            assignments._delete_project_assignment,
            ("PROJ001", "EMP001"),
            [{}, {"before": {"allocation": 40}}, {"deleted": True}],
        ),
        (
            requirements,
            requirements._upsert_project_requirement,
            ("PROJ001", "SK001", 3, "MUST"),
            [
                {"before": None},
                {"project_id": "PROJ001", "skill_id": "SK001", "min_level": 3},
            ],
        ),
        (
            requirements,
            requirements._delete_project_requirement,
            ("PROJ001", "SK001"),
            [{"before": {"min_level": 3}}, {"deleted": True}],
        ),
    ],
)
def test_all_callbacks_propagate_audit_failure_in_business_transaction(
    monkeypatch, module, callback, args, answers
):
    transaction = MagicMock()
    transaction.run.side_effect = [result(row) for row in answers]
    failure = RuntimeError("Audit store failure")
    writer = MagicMock(side_effect=failure)
    monkeypatch.setattr(module, "write_event", writer)
    context = AuditContext.create(AuditActor("actor", "Name"))
    with pytest.raises(RuntimeError) as caught:
        callback(transaction, *args, context)
    assert caught.value is failure
    assert writer.call_args.args[0] is transaction
    assert writer.call_args.args[1] is context


def test_allocation_conflict_never_writes_history(monkeypatch):
    transaction = MagicMock()
    transaction.run.return_value = result({"allocated_elsewhere": 80})
    writer = MagicMock()
    monkeypatch.setattr(assignments, "write_event", writer)
    response = assignments._upsert_project_assignment(
        transaction,
        "PROJ001",
        "EMP001",
        "Engineer",
        40,
        AuditContext.create(AuditActor("actor", "Name")),
    )
    assert response.allocation_exceeded
    writer.assert_not_called()
    assert transaction.run.call_count == 1


def test_retry_reuses_context_without_global_actor_state(block_graph, monkeypatch):
    block_graph.side_effect = None
    session = block_graph.return_value.__enter__.return_value
    contexts = []

    def callback(transaction, properties, context):
        contexts.append(context)
        return properties

    monkeypatch.setattr(projects, "_create_project", callback)

    def retry(operation, *args):
        operation(MagicMock(), *args)
        return operation(MagicMock(), *args)

    session.execute_write.side_effect = retry
    projects.create_project({"project_id": "PROJ001"}, actor=AuditActor("one", "First"))
    projects.create_project(
        {"project_id": "PROJ002"}, actor=AuditActor("two", "Second")
    )
    assert contexts[0] is contexts[1] and contexts[2] is contexts[3]
    assert contexts[0].event_id != contexts[2].event_id
    assert contexts[0].actor.user_id == "one" and contexts[2].actor.user_id == "two"


def test_read_allowlist_and_parameterization(block_graph):
    block_graph.side_effect = None
    transaction = MagicMock()
    item = event()
    item["before_json"] = json.dumps({"allocation": 40, "password": "secret"})
    item["after_json"] = json.dumps(item.pop("after"))
    item.pop("before")
    transaction.run.return_value = [Record(item)]
    session = block_graph.return_value.__enter__.return_value
    session.execute_read.side_effect = lambda callback: callback(transaction)
    injection = "' MATCH (n) DETACH DELETE n //"
    rows = activity.list_events({"actor": injection, "fetch_limit": 21})
    assert rows[0]["before"] == {"allocation": 40}
    assert "secret" not in json.dumps(rows)
    assert injection not in transaction.run.call_args.args[0]
    assert transaction.run.call_args.kwargs["actor"] == injection
    assert decode_cursor(encode_cursor(event()))[0] == "2026-09-10T03:00:00.000000Z"
