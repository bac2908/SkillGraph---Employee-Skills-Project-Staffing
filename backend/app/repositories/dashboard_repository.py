"""Bounded dashboard output; five statements per read-transaction attempt.

Aggregate each entity type separately to avoid multiplying counts/allocations
through a Cartesian product. Never fetch every entity or issue a query per project.
"""

from neo4j import Transaction

from app.db.graph import graph_db
from app.repositories.errors import RepositoryError

CAPACITY_LIMIT = 5

EMPLOYEE_SUMMARY_QUERY = """
MATCH (employee:Employee)
RETURN count(employee) AS employee_count,
       coalesce(sum(CASE WHEN employee.status = 'AVAILABLE' THEN 1 ELSE 0 END), 0)
           AS available_employee_count
"""

PROJECT_SUMMARY_QUERY = """
MATCH (project:Project)
RETURN count(project) AS project_count,
       coalesce(sum(CASE WHEN project.status = 'ACTIVE' THEN 1 ELSE 0 END), 0)
           AS active_project_count
"""

SKILL_SUMMARY_QUERY = """
MATCH (skill:Skill)
RETURN count(skill) AS skill_count
"""

CAPACITY_QUERY = """
MATCH (employee:Employee)
OPTIONAL MATCH (employee)-[assignment:WORKS_ON]->(:Project)
WITH employee, coalesce(sum(assignment.allocation), 0) AS total_allocation
RETURN employee.employee_id AS employee_id,
       employee.name AS name,
       employee.title AS title,
       total_allocation,
       100 - total_allocation AS remaining_allocation
ORDER BY total_allocation, toLower(employee.name), employee.employee_id
LIMIT $limit
"""

DEFAULT_PROJECT_QUERY = """
MATCH (project:Project)
RETURN project.project_id AS project_id,
       project.name AS name,
       project.description AS description,
       project.status AS status
ORDER BY CASE WHEN project.status = 'ACTIVE' THEN 0 ELSE 1 END,
         project.project_id
LIMIT 1
"""


class DashboardRepositoryError(RepositoryError):
    pass


def _get_dashboard(transaction: Transaction) -> dict:
    summary = {}
    for query in (
        EMPLOYEE_SUMMARY_QUERY,
        PROJECT_SUMMARY_QUERY,
        SKILL_SUMMARY_QUERY,
    ):
        record = transaction.run(query).single()
        if record is None:
            # Missing aggregate output is not a valid, empty workspace.
            raise DashboardRepositoryError("Dashboard aggregate was not returned.")
        summary.update(record.data())

    capacity = [
        record.data()
        for record in transaction.run(CAPACITY_QUERY, limit=CAPACITY_LIMIT)
    ]
    project = transaction.run(DEFAULT_PROJECT_QUERY).single()
    return {
        "summary": summary,
        "capacity": capacity,
        "default_project": project.data() if project else None,
    }


def get_dashboard() -> dict:
    try:
        with graph_db.driver.session() as session:
            return session.execute_read(_get_dashboard)
    except RepositoryError:
        raise
    except Exception as exc:
        raise DashboardRepositoryError("Unable to retrieve dashboard.") from exc
