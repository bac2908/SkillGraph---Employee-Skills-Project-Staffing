from neo4j import Transaction
from neo4j.exceptions import ConstraintError

from app.core.audit import AuditActor, AuditContext
from app.db.graph import graph_db
from app.repositories.activity_repository import write_event
from app.repositories.errors import DuplicateRecordError, RepositoryError

PROJECT_EXISTS_QUERY = """
MATCH (project:Project {project_id: $project_id})
RETURN count(project) > 0 AS project_exists
"""

REQUIRED_SKILLS_QUERY = """
MATCH (project:Project {project_id: $project_id})
      -[requirement:REQUIRES_SKILL]->
      (skill:Skill)
RETURN skill.skill_id AS skill_id,
       skill.name AS skill,
       requirement.min_level AS required_level,
       requirement.priority AS priority
ORDER BY skill.name
"""

TEAM_SKILL_LEVELS_QUERY = """
MATCH (project:Project {project_id: $project_id})
      <-[:WORKS_ON]-
      (employee:Employee)
      -[employee_skill:HAS_SKILL]->
      (skill:Skill)
RETURN skill.skill_id AS skill_id,
       skill.name AS skill,
       max(employee_skill.level) AS best_team_level,
       count(DISTINCT employee) AS employee_count
ORDER BY skill.name
"""

PROJECT_FIELDS = """
project.project_id AS project_id,
project.name AS name,
project.description AS description,
project.status AS status
"""

GET_PROJECT_QUERY = f"""
MATCH (project:Project {{project_id: $project_id}})
RETURN {PROJECT_FIELDS}
"""

LIST_PROJECTS_QUERY = f"""
MATCH (project:Project)
WHERE ($search IS NULL
       OR toLower(project.project_id) CONTAINS toLower($search)
       OR toLower(project.name) CONTAINS toLower($search)
       OR toLower(project.description) CONTAINS toLower($search))
  AND ($status IS NULL OR project.status = $status)
RETURN {PROJECT_FIELDS}
ORDER BY toLower(project.name), project.project_id
SKIP $offset
LIMIT $limit
"""

COUNT_PROJECTS_QUERY = """
MATCH (project:Project)
WHERE ($search IS NULL
       OR toLower(project.project_id) CONTAINS toLower($search)
       OR toLower(project.name) CONTAINS toLower($search)
       OR toLower(project.description) CONTAINS toLower($search))
  AND ($status IS NULL OR project.status = $status)
RETURN count(project) AS total
"""

CREATE_PROJECT_QUERY = f"""
CREATE (project:Project)
SET project = $properties
RETURN {PROJECT_FIELDS}
"""

UPDATE_PROJECT_QUERY = f"""
MATCH (project:Project {{project_id: $project_id}})
SET project += $updates
RETURN {PROJECT_FIELDS}
"""

PROJECT_RELATIONSHIP_COUNT_QUERY = """
MATCH (project:Project {project_id: $project_id})
SET project.project_id = project.project_id
WITH project
OPTIONAL MATCH (project)-[relationship]-()
RETURN count(relationship) AS relationship_count, properties(project) AS before
"""

LOCK_PROJECT_QUERY = """
MATCH (project:Project {project_id: $project_id})
SET project.project_id = project.project_id
RETURN properties(project) AS before
"""

DELETE_PROJECT_QUERY = """
MATCH (project:Project {project_id: $project_id})
DELETE project
"""


class ProjectRepositoryError(RepositoryError):
    pass


def project_exists(project_id: str) -> bool:
    try:
        with graph_db.driver.session() as session:
            record = session.run(
                PROJECT_EXISTS_QUERY,
                project_id=project_id,
            ).single()
        return bool(record and record["project_exists"])
    except Exception as exc:
        raise ProjectRepositoryError(
            "Unable to check whether the project exists."
        ) from exc


def get_required_skills(project_id: str) -> list[dict]:
    try:
        with graph_db.driver.session() as session:
            result = session.run(
                REQUIRED_SKILLS_QUERY,
                project_id=project_id,
            )
            return [record.data() for record in result]
    except Exception as exc:
        raise ProjectRepositoryError(
            "Unable to retrieve the project's required skills."
        ) from exc


def get_team_skill_levels(project_id: str) -> list[dict]:
    try:
        with graph_db.driver.session() as session:
            result = session.run(
                TEAM_SKILL_LEVELS_QUERY,
                project_id=project_id,
            )
            return [record.data() for record in result]
    except Exception as exc:
        raise ProjectRepositoryError(
            "Unable to retrieve the project team's skill levels."
        ) from exc


def _list_projects(
    transaction: Transaction,
    search: str | None,
    project_status: str | None,
    limit: int,
    offset: int,
) -> tuple[list[dict], int]:
    parameters = {
        "search": search,
        "status": project_status,
        "limit": limit,
        "offset": offset,
    }
    total_record = transaction.run(
        COUNT_PROJECTS_QUERY,
        **parameters,
    ).single()
    items = [
        record.data() for record in transaction.run(LIST_PROJECTS_QUERY, **parameters)
    ]
    return items, total_record["total"] if total_record else 0


def list_projects(
    search: str | None,
    project_status: str | None,
    limit: int,
    offset: int,
) -> tuple[list[dict], int]:
    try:
        with graph_db.driver.session() as session:
            return session.execute_read(
                _list_projects,
                search,
                project_status,
                limit,
                offset,
            )
    except Exception as exc:
        raise ProjectRepositoryError("Unable to list projects.") from exc


def get_project(project_id: str) -> dict | None:
    try:
        with graph_db.driver.session() as session:
            record = session.run(
                GET_PROJECT_QUERY,
                project_id=project_id,
            ).single()
            return record.data() if record else None
    except Exception as exc:
        raise ProjectRepositoryError("Unable to retrieve project.") from exc


def _create_project(
    transaction: Transaction, properties: dict, audit: AuditContext
) -> dict:
    record = transaction.run(CREATE_PROJECT_QUERY, properties=properties).single()
    if record is None:
        raise ProjectRepositoryError("Project was not created.")
    project = record.data()
    write_event(
        transaction,
        audit,
        project["project_id"],
        "PROJECT",
        project["project_id"],
        None,
        project,
    )
    return project


def create_project(properties: dict, *, actor: AuditActor) -> dict:
    audit = AuditContext.create(actor)
    try:
        with graph_db.driver.session() as session:
            return session.execute_write(_create_project, properties, audit)
    except ConstraintError as exc:
        raise DuplicateRecordError("Project already exists.") from exc
    except RepositoryError:
        raise
    except Exception as exc:
        raise ProjectRepositoryError("Unable to create project.") from exc


def _update_project(
    transaction: Transaction, project_id: str, updates: dict, audit: AuditContext
) -> dict | None:
    locked = transaction.run(LOCK_PROJECT_QUERY, project_id=project_id).single()
    if locked is None:
        return None
    record = transaction.run(
        UPDATE_PROJECT_QUERY, project_id=project_id, updates=updates
    ).single()
    if record is None:
        raise ProjectRepositoryError("Project update was not saved.")
    project = record.data()
    write_event(
        transaction, audit, project_id, "PROJECT", project_id, locked["before"], project
    )
    return project


def update_project(project_id: str, updates: dict, *, actor: AuditActor) -> dict | None:
    audit = AuditContext.create(actor)
    try:
        with graph_db.driver.session() as session:
            return session.execute_write(_update_project, project_id, updates, audit)
    except ConstraintError as exc:
        raise DuplicateRecordError("Project update is not unique.") from exc
    except Exception as exc:
        raise ProjectRepositoryError("Unable to update project.") from exc


def _delete_project(
    transaction: Transaction,
    project_id: str,
    audit: AuditContext,
) -> int | None:
    record = transaction.run(
        PROJECT_RELATIONSHIP_COUNT_QUERY,
        project_id=project_id,
    ).single()
    if record is None:
        return None

    relationship_count = record["relationship_count"]
    if relationship_count == 0:
        transaction.run(
            DELETE_PROJECT_QUERY,
            project_id=project_id,
        ).consume()
        write_event(
            transaction,
            audit,
            project_id,
            "PROJECT",
            project_id,
            record["before"],
            None,
        )
    return relationship_count


def delete_project(project_id: str, *, actor: AuditActor) -> int | None:
    audit = AuditContext.create(actor)
    try:
        with graph_db.driver.session() as session:
            return session.execute_write(_delete_project, project_id, audit)
    except Exception as exc:
        raise ProjectRepositoryError("Unable to delete project.") from exc
