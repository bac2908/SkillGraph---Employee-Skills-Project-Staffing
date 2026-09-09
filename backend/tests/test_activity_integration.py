"""Explicit graph integration, using uniquely marked disposable fixtures only.

Lifecycle/concurrency tests commit tiny fixtures like separate API requests and
remove only their own marked nodes/events in finally. Failure probes roll back.
Requires scripts.setup_activity_schema. Do not run on production.
"""

from concurrent.futures import ThreadPoolExecutor
from time import time_ns
from uuid import uuid4

import pytest

from app.core.audit import AuditActor, AuditContext
from app.db.graph import graph_db
from app.repositories import project_assignment_repository as assignments
from app.repositories import project_repository as projects
from app.repositories import project_requirement_repository as requirements
from app.services.activity_service import ActivityService

pytestmark = pytest.mark.integration


class RollbackProbe(Exception):
    pass


def assert_absent(project_id, employee_id=None, skill_id=None):
    with graph_db.driver.session() as session:
        for label, key, value in (
            ("Project", "project_id", project_id),
            ("AuditEvent", "project_id", project_id),
            ("Employee", "employee_id", employee_id),
            ("Skill", "skill_id", skill_id),
        ):
            if value:
                assert (
                    session.run(
                        f"MATCH (n:{label} {{{key}: $id}}) RETURN count(n) AS total",
                        id=value,
                    ).single()["total"]
                    == 0
                )


@pytest.fixture
def graph_fixture():
    suffix = str(time_ns())
    marker = "activity-integration-" + uuid4().hex
    project_id, second_id, employee_id, skill_id = (
        "PROJ" + suffix,
        "PROJ9" + suffix,
        "EMP" + suffix,
        "SK" + suffix,
    )
    actor = AuditActor(marker, "Activity Test Actor")
    properties = {
        "project_id": project_id,
        "name": "Activity integration test",
        "description": "Disposable test record",
        "status": "ACTIVE",
        "activity_test_run": marker,
    }

    def setup(transaction):
        transaction.run(
            "CREATE (:Employee {employee_id: $id, name: 'Activity test', activity_test_run: $marker})",
            id=employee_id,
            marker=marker,
        ).consume()
        transaction.run(
            "CREATE (:Skill {skill_id: $id, name: $name, category: 'Test', activity_test_run: $marker})",
            id=skill_id,
            name="Activity test " + suffix,
            marker=marker,
        ).consume()
        transaction.run(
            "CREATE (:Project {project_id: $id, name: 'Other test', activity_test_run: $marker})",
            id=second_id,
            marker=marker,
        ).consume()
        projects._create_project(transaction, properties, AuditContext.create(actor))

    try:
        with graph_db.driver.session() as session:
            session.execute_write(setup)
        yield project_id, second_id, employee_id, skill_id, actor
    finally:
        # Exact IDs AND this run's random marker: never delete pre-existing data.
        with graph_db.driver.session() as session:
            for label, key, ids in (
                ("Project", "project_id", [project_id, second_id]),
                ("Employee", "employee_id", [employee_id]),
                ("Skill", "skill_id", [skill_id]),
            ):
                session.run(
                    f"MATCH (n:{label}) WHERE n.{key} IN $ids AND n.activity_test_run = $marker DETACH DELETE n",
                    ids=ids,
                    marker=marker,
                ).consume()
            session.run(
                "MATCH (event:AuditEvent) WHERE event.project_id IN $ids AND event.actor_id IN $actors DELETE event",
                ids=[project_id, second_id],
                actors=[actor.user_id, actor.user_id + "-peer"],
            ).consume()
        assert_absent(project_id, employee_id, skill_id)
        assert_absent(second_id)


def history(project_id, **filters):
    parameters = dict(
        project_id=project_id,
        limit=100,
        action=None,
        resource_type=None,
        actor=None,
        since=None,
        until=None,
        cursor=None,
    )
    return ActivityService.list(**{**parameters, **filters})


def test_graph_activity_lifecycle_and_cursor(graph_fixture):
    project_id, second_id, employee_id, skill_id, actor = graph_fixture
    projects.update_project(project_id, {"name": "Updated test"}, actor=actor)
    projects.update_project(project_id, {"name": "Updated test"}, actor=actor)
    assert len(history(project_id)["items"]) == 2
    created = assignments.upsert_project_assignment(
        project_id, employee_id, "Engineer", 60, actor=actor
    )
    assert created.created
    updated = assignments.upsert_project_assignment(
        project_id, employee_id, "Engineer", 40, actor=actor
    )
    assert not updated.created
    assignments.upsert_project_assignment(
        project_id, employee_id, "Engineer", 40, actor=actor
    )
    conflict = assignments.upsert_project_assignment(
        second_id, employee_id, "Engineer", 70, actor=actor
    )
    assert conflict.allocation_exceeded
    assert history(second_id)["items"] == []
    assert len(history(project_id)["items"]) == 4
    assert requirements.upsert_project_requirement(
        project_id, skill_id, 3, "MUST", actor=actor
    )[1]
    assert not requirements.upsert_project_requirement(
        project_id, skill_id, 4, "MUST", actor=actor
    )[1]
    requirements.upsert_project_requirement(
        project_id, skill_id, 4, "MUST", actor=actor
    )
    assert projects.delete_project(project_id, actor=actor) == 2
    assert len(history(project_id)["items"]) == 6
    assert requirements.delete_project_requirement(project_id, skill_id, actor=actor)
    assert assignments.delete_project_assignment(project_id, employee_id, actor=actor)
    assert projects.delete_project(project_id, actor=actor) == 0

    events = history(project_id)["items"]
    assert len(events) == len({row["event_id"] for row in events}) == 9
    assert all(row["actor_id"] == actor.user_id for row in events)
    assert events[0]["action"] == "DELETED"
    assert events[0]["before"]["name"] == "Updated test"
    assert events[0]["after"] is None
    assignment_events = history(
        project_id, resource_type="WORKS_ON", action="UPDATED", actor="Test Actor"
    )["items"]
    assert len(assignment_events) == 1
    assert assignment_events[0]["before"]["allocation"] == 60
    assert assignment_events[0]["after"]["allocation"] == 40
    first = history(project_id, limit=2)
    remaining = history(project_id, cursor=first["next_cursor"])
    assert [row["event_id"] for row in first["items"] + remaining["items"]] == [
        row["event_id"] for row in events
    ]


def test_concurrent_assignment_has_one_success_and_matching_actor(graph_fixture):
    project_id, second_id, employee_id, _, actor = graph_fixture
    actors = {
        project_id: actor,
        second_id: AuditActor(actor.user_id + "-peer", "Peer Test Actor"),
    }

    def assign(target):
        return assignments.upsert_project_assignment(
            target, employee_id, "Concurrent test", 60, actor=actors[target]
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(assign, [project_id, second_id]))
    assert sorted(result.allocation_exceeded for result in results) == [False, True]
    events = (
        history(project_id, resource_type="WORKS_ON")["items"]
        + history(second_id, resource_type="WORKS_ON")["items"]
    )
    assert len(events) == 1
    assert events[0]["actor_id"] == actors[events[0]["project_id"]].user_id
    assert events[0]["after"]["allocation"] == 60


def test_concurrent_updates_capture_a_continuous_before_after_chain(graph_fixture):
    project_id, _, employee_id, _, actor = graph_fixture
    peer = AuditActor(actor.user_id + "-peer", "Peer Test Actor")
    assignments.upsert_project_assignment(
        project_id, employee_id, "Engineer", 20, actor=actor
    )

    def update(change):
        allocation, who = change
        return assignments.upsert_project_assignment(
            project_id, employee_id, "Engineer", allocation, actor=who
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(update, [(40, actor), (60, peer)]))
    assert all(not result.created for result in results)
    events = history(project_id, resource_type="WORKS_ON", action="UPDATED")["items"]
    assert len(events) == 2
    assert {row["after"]["allocation"]: row["actor_id"] for row in events} == {
        40: actor.user_id,
        60: peer.user_id,
    }
    first = next(row for row in events if row["before"]["allocation"] == 20)
    last = next(row for row in events if row is not first)
    assert last["before"]["allocation"] == first["after"]["allocation"]
    assert (
        assignments.list_project_assignments(project_id)[0]["allocation"]
        == last["after"]["allocation"]
    )


@pytest.mark.parametrize("failing_kind", ["project", "assignment", "requirement"])
def test_real_transaction_rolls_back_when_audit_fails(
    monkeypatch, graph_fixture, failing_kind
):
    project_id, _, employee_id, skill_id, actor = graph_fixture
    before_events = history(project_id)

    def fail(*args):
        raise RollbackProbe("Simulated audit failure")

    module = {
        "project": projects,
        "assignment": assignments,
        "requirement": requirements,
    }[failing_kind]
    monkeypatch.setattr(module, "write_event", fail)

    def scenario(transaction):
        context = AuditContext.create(actor)
        if failing_kind == "project":
            projects._update_project(
                transaction, project_id, {"name": "Must roll back"}, context
            )
        elif failing_kind == "assignment":
            assignments._upsert_project_assignment(
                transaction, project_id, employee_id, "Engineer", 40, context
            )
        else:
            requirements._upsert_project_requirement(
                transaction, project_id, skill_id, 3, "MUST", context
            )

    with graph_db.driver.session() as session, pytest.raises(RollbackProbe):
        session.execute_write(scenario)
    assert history(project_id) == before_events
    assert projects.get_project(project_id)["name"] == "Activity integration test"
    assert assignments.list_project_assignments(project_id) == []
    assert requirements.list_project_requirements(project_id) == []
