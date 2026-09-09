"""Explicit, read-only integration check against the configured graph.

Run this file separately from test_crud_api.py, whose integration test writes
test records. No account, session, schema or graph data is created here.
"""

import pytest

from app.db.graph import graph_db
from app.repositories import employee_repository, project_repository, skill_repository
from app.schemas.dashboard import DashboardRead
from app.services.dashboard_service import DashboardService


@pytest.mark.integration
def test_dashboard_matches_existing_read_apis():
    dashboard = DashboardRead.model_validate(DashboardService.overview())
    assert (
        dashboard.summary.employee_count
        == employee_repository.list_employees(None, None, 1, 0)[1]
    )
    assert (
        dashboard.summary.available_employee_count
        == employee_repository.list_employees(None, "AVAILABLE", 1, 0)[1]
    )
    assert (
        dashboard.summary.project_count
        == project_repository.list_projects(None, None, 1, 0)[1]
    )
    assert (
        dashboard.summary.active_project_count
        == project_repository.list_projects(None, "ACTIVE", 1, 0)[1]
    )
    assert (
        dashboard.summary.skill_count
        == skill_repository.list_skills(None, None, 1, 0)[1]
    )
    assert len(dashboard.capacity) == min(5, dashboard.summary.employee_count)
    if dashboard.summary.project_count:
        assert dashboard.default_project is not None
        if dashboard.summary.active_project_count:
            assert dashboard.default_project.status == "ACTIVE"
    else:
        assert dashboard.default_project is None

    with graph_db.driver.session() as session:
        for employee in dashboard.capacity:
            allocations = session.run(
                """
                MATCH (employee:Employee {employee_id: $employee_id})
                OPTIONAL MATCH (employee)-[assignment:WORKS_ON]->(:Project)
                RETURN assignment.allocation AS allocation
                """,
                employee_id=employee.employee_id,
            )
            expected = sum(row["allocation"] or 0 for row in allocations)
            assert employee.total_allocation == expected
            assert employee.remaining_allocation == 100 - expected
