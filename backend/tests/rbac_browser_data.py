"""Synthetic in-memory business data; real RBAC/auth are never overridden.

Installed only by the isolated browser test server. No reset/control HTTP routes.
This is deliberately NOT a graph engine or a persistence/integration test.
"""

from copy import deepcopy
from threading import RLock

from app.core.exceptions import ResourceNotFoundError

RBAC_PASSWORD = "RBAC-only personal password 2026!"
TEMP_PASSWORD = "RBAC-only temporary password 2026!"


class Catalogue:
    def __init__(self, resource, key, rows, filter_key="status"):
        self.resource, self.key, self.filter_key = resource, key, filter_key
        self.rows = {row[key]: deepcopy(row) for row in rows}
        self.lock = RLock()

    def get(self, identity):
        with self.lock:
            if identity not in self.rows:
                raise ResourceNotFoundError(self.resource, identity)
            return deepcopy(self.rows[identity])

    def list(self, search, state, limit, offset):
        with self.lock:
            items = [
                deepcopy(row)
                for row in self.rows.values()
                if (not search or search.casefold() in str(row).casefold())
                and (not state or row.get(self.filter_key) == state)
            ]
        return {
            "items": items[offset : offset + limit],
            "total": len(items),
            "limit": limit,
            "offset": offset,
        }

    def create(self, data, **kwargs):
        with self.lock:
            assert data[self.key] not in self.rows, "Duplicate synthetic fixture ID"
            self.rows[data[self.key]] = deepcopy(data)
            return deepcopy(data)

    def update(self, identity, updates, **kwargs):
        with self.lock:
            self.get(identity)
            self.rows[identity].update(deepcopy(updates))
            return self.get(identity)

    def delete(self, identity, **kwargs):
        with self.lock:
            self.get(identity)
            del self.rows[identity]


def install_rbac_data(store):
    from app.api import (
        employee_skills,
        employees,
        project_assignments,
        project_requirements,
        projects,
        skills,
    )
    from app.db.graph import graph_db
    from app.repositories import project_repository

    def forbidden_graph(*args, **kwargs):
        raise AssertionError("Graph access is forbidden in isolated RBAC acceptance")

    graph_db.driver.session = forbidden_graph

    project_data = Catalogue(
        "Project",
        "project_id",
        [
            {
                "project_id": "PROJ101",
                "name": "RBAC Granted Project",
                "description": "Synthetic granted project",
                "status": "ACTIVE",
            },
            {
                "project_id": "PROJ102",
                "name": "RBAC Other Project",
                "description": "Synthetic outside-grant project",
                "status": "ACTIVE",
            },
        ],
    )
    employee_data = Catalogue(
        "Employee",
        "employee_id",
        [
            {
                "employee_id": "EMP101",
                "name": "RBAC Employee",
                "email": "employee@example.com",
                "title": "Developer",
                "seniority": "Senior",
                "status": "AVAILABLE",
                "location": "Test location",
            },
        ],
    )
    skill_data = Catalogue(
        "Skill",
        "skill_id",
        [
            {"skill_id": "SK101", "name": "RBAC Python", "category": "Programming"},
        ],
        "category",
    )
    for service, data in (
        (projects.project_service, project_data),
        (employees.service, employee_data),
        (skills.service, skill_data),
    ):
        for operation in ("get", "list", "create", "update", "delete"):
            setattr(service, operation, getattr(data, operation))
    # Account grant validation constructs ProjectService separately.
    project_repository.get_project = lambda project_id: deepcopy(
        project_data.rows.get(project_id)
    )
    for service in (
        project_assignments.service,
        project_requirements.service,
        employee_skills.service,
    ):
        service.list = lambda identity: {"items": [], "total": 0}
    projects.skill_gap_service.analyze = lambda pid: {
        "project_id": pid,
        "summary": {
            "total": 0,
            "covered": 0,
            "gap": 0,
            "missing": 0,
            "coverage_percent": 0,
        },
        "skills": [],
    }
    projects.candidate_recommendation_service.recommend = lambda pid: {
        "project_id": pid,
        "summary": {"uncovered_skill_count": 0, "candidate_count": 0},
        "uncovered_skills": [],
        "candidates": [],
    }
    fixtures = [
        ("manager", "MANAGER", False),
        ("viewer", "VIEWER", False),
        ("locked", "VIEWER", False),
        ("reset", "VIEWER", False),
        ("regranted", "MANAGER", False),
        ("forced-admin", "ADMIN", True),
        ("forced-manager", "MANAGER", True),
        ("forced-viewer", "VIEWER", True),
    ]
    for label, role, forced in fixtures:
        user = store.create_user(
            {
                "email": f"rbac-{label}@example.com",
                "name": f"RBAC {label}",
                "password": TEMP_PASSWORD,
                "role": role,
                "project_ids": ["PROJ101"] if role == "MANAGER" else [],
            }
        )
        if not forced:
            store.change_password(
                user["user_id"], TEMP_PASSWORD, RBAC_PASSWORD, "rbac-fixture-setup"
            )
