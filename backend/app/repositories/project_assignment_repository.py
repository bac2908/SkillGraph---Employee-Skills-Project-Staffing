from dataclasses import dataclass

from neo4j import Transaction

from app.db.graph import graph_db
from app.repositories.errors import RepositoryError

LIST_PROJECT_ASSIGNMENTS_QUERY = """
MATCH (employee:Employee)
      -[assignment:WORKS_ON]->
      (project:Project {project_id: $project_id})
OPTIONAL MATCH (employee)-[all_assignment:WORKS_ON]->(:Project)
WITH employee, project, assignment,
     coalesce(sum(all_assignment.allocation), 0) AS total_allocation
RETURN project.project_id AS project_id,
       project.name AS project_name,
       employee.employee_id AS employee_id,
       employee.name AS employee_name,
       assignment.role AS role,
       assignment.allocation AS allocation,
       total_allocation AS employee_total_allocation,
       100 - total_allocation AS employee_remaining_allocation
ORDER BY toLower(employee.name), employee.employee_id
"""

LOCK_AND_GET_ALLOCATION_QUERY = """
MATCH (employee:Employee {employee_id: $employee_id})
SET employee.employee_id = employee.employee_id
WITH employee
OPTIONAL MATCH (employee)-[assignment:WORKS_ON]->
               (assigned_project:Project)
RETURN coalesce(
           sum(
               CASE
                   WHEN assigned_project.project_id <> $project_id
                   THEN assignment.allocation
                   ELSE 0
               END
           ),
           0
       ) AS allocated_elsewhere
"""

PROJECT_ASSIGNMENT_EXISTS_QUERY = """
MATCH (:Employee {employee_id: $employee_id})
      -[assignment:WORKS_ON]->
      (:Project {project_id: $project_id})
RETURN count(assignment) > 0 AS relationship_exists
"""

UPSERT_PROJECT_ASSIGNMENT_QUERY = """
MATCH (employee:Employee {employee_id: $employee_id})
MATCH (project:Project {project_id: $project_id})
MERGE (employee)-[assignment:WORKS_ON]->(project)
SET assignment.role = $role,
    assignment.allocation = $allocation
RETURN project.project_id AS project_id,
       project.name AS project_name,
       employee.employee_id AS employee_id,
       employee.name AS employee_name,
       assignment.role AS role,
       assignment.allocation AS allocation
"""

DELETE_PROJECT_ASSIGNMENT_QUERY = """
MATCH (employee:Employee {employee_id: $employee_id})
      -[assignment:WORKS_ON]->
      (project:Project {project_id: $project_id})
DELETE assignment
RETURN true AS deleted
"""


@dataclass(frozen=True, slots=True)
class AssignmentUpsertResult:
    assignment: dict | None
    created: bool
    allocated_elsewhere: int

    @property
    def allocation_exceeded(self) -> bool:
        return self.assignment is None


class ProjectAssignmentRepositoryError(RepositoryError):
    pass


def list_project_assignments(project_id: str) -> list[dict]:
    try:
        with graph_db.driver.session() as session:
            result = session.run(
                LIST_PROJECT_ASSIGNMENTS_QUERY,
                project_id=project_id,
            )
            return [record.data() for record in result]
    except Exception as exc:
        raise ProjectAssignmentRepositoryError(
            "Unable to list project assignments."
        ) from exc


def _upsert_project_assignment(
    transaction: Transaction,
    project_id: str,
    employee_id: str,
    role: str,
    allocation: int,
) -> AssignmentUpsertResult:
    allocation_record = transaction.run(
        LOCK_AND_GET_ALLOCATION_QUERY,
        project_id=project_id,
        employee_id=employee_id,
    ).single()
    if allocation_record is None:
        raise ProjectAssignmentRepositoryError("Employee does not exist.")

    allocated_elsewhere = allocation_record["allocated_elsewhere"]
    if allocated_elsewhere + allocation > 100:
        return AssignmentUpsertResult(
            assignment=None,
            created=False,
            allocated_elsewhere=allocated_elsewhere,
        )

    exists_record = transaction.run(
        PROJECT_ASSIGNMENT_EXISTS_QUERY,
        project_id=project_id,
        employee_id=employee_id,
    ).single()
    relationship_exists = bool(
        exists_record and exists_record["relationship_exists"]
    )

    record = transaction.run(
        UPSERT_PROJECT_ASSIGNMENT_QUERY,
        project_id=project_id,
        employee_id=employee_id,
        role=role,
        allocation=allocation,
    ).single()
    if record is None:
        raise ProjectAssignmentRepositoryError(
            "Project assignment was not saved."
        )

    assignment = record.data()
    total_allocation = allocated_elsewhere + allocation
    assignment["employee_total_allocation"] = total_allocation
    assignment["employee_remaining_allocation"] = 100 - total_allocation
    return AssignmentUpsertResult(
        assignment=assignment,
        created=not relationship_exists,
        allocated_elsewhere=allocated_elsewhere,
    )


def upsert_project_assignment(
    project_id: str,
    employee_id: str,
    role: str,
    allocation: int,
) -> AssignmentUpsertResult:
    try:
        with graph_db.driver.session() as session:
            return session.execute_write(
                _upsert_project_assignment,
                project_id,
                employee_id,
                role,
                allocation,
            )
    except RepositoryError:
        raise
    except Exception as exc:
        raise ProjectAssignmentRepositoryError(
            "Unable to save project assignment."
        ) from exc


def delete_project_assignment(project_id: str, employee_id: str) -> bool:
    try:
        with graph_db.driver.session() as session:
            record = session.run(
                DELETE_PROJECT_ASSIGNMENT_QUERY,
                project_id=project_id,
                employee_id=employee_id,
            ).single()
            return bool(record and record["deleted"])
    except Exception as exc:
        raise ProjectAssignmentRepositoryError(
            "Unable to delete project assignment."
        ) from exc
