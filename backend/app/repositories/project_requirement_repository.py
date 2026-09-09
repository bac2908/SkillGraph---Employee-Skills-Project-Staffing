from neo4j import Transaction

from app.core.audit import AuditActor, AuditContext
from app.db.graph import graph_db
from app.repositories.activity_repository import write_event
from app.repositories.errors import RepositoryError

LIST_PROJECT_REQUIREMENTS_QUERY = """
MATCH (project:Project {project_id: $project_id})
      -[requirement:REQUIRES_SKILL]->
      (skill:Skill)
RETURN project.project_id AS project_id,
       project.name AS project_name,
       skill.skill_id AS skill_id,
       skill.name AS skill_name,
       skill.category AS category,
       requirement.min_level AS min_level,
       requirement.priority AS priority
ORDER BY toLower(skill.name), skill.skill_id
"""

LOCK_PROJECT_REQUIREMENT_QUERY = """
MATCH (project:Project {project_id: $project_id})
SET project.project_id = project.project_id
WITH project
MATCH (skill:Skill {skill_id: $skill_id})
OPTIONAL MATCH (project)-[requirement:REQUIRES_SKILL]->(skill)
RETURN properties(requirement) AS before
"""

UPSERT_PROJECT_REQUIREMENT_QUERY = """
MATCH (project:Project {project_id: $project_id})
MATCH (skill:Skill {skill_id: $skill_id})
MERGE (project)-[requirement:REQUIRES_SKILL]->(skill)
SET requirement.min_level = $min_level,
    requirement.priority = $priority
RETURN project.project_id AS project_id,
       project.name AS project_name,
       skill.skill_id AS skill_id,
       skill.name AS skill_name,
       skill.category AS category,
       requirement.min_level AS min_level,
       requirement.priority AS priority
"""

DELETE_PROJECT_REQUIREMENT_QUERY = """
MATCH (project:Project {project_id: $project_id})
      -[requirement:REQUIRES_SKILL]->
      (skill:Skill {skill_id: $skill_id})
DELETE requirement
RETURN true AS deleted
"""


class ProjectRequirementRepositoryError(RepositoryError):
    pass


def list_project_requirements(project_id: str) -> list[dict]:
    try:
        with graph_db.driver.session() as session:
            result = session.run(
                LIST_PROJECT_REQUIREMENTS_QUERY,
                project_id=project_id,
            )
            return [record.data() for record in result]
    except Exception as exc:
        raise ProjectRequirementRepositoryError(
            "Unable to list project requirements."
        ) from exc


def _upsert_project_requirement(
    transaction: Transaction,
    project_id: str,
    skill_id: str,
    min_level: int,
    priority: str,
    audit: AuditContext,
) -> tuple[dict, bool]:
    exists_record = transaction.run(
        LOCK_PROJECT_REQUIREMENT_QUERY,
        project_id=project_id,
        skill_id=skill_id,
    ).single()
    if exists_record is None:
        raise ProjectRequirementRepositoryError("Project or skill does not exist.")
    before = (
        {**exists_record["before"], "project_id": project_id, "skill_id": skill_id}
        if exists_record["before"] is not None
        else None
    )

    record = transaction.run(
        UPSERT_PROJECT_REQUIREMENT_QUERY,
        project_id=project_id,
        skill_id=skill_id,
        min_level=min_level,
        priority=priority,
    ).single()
    if record is None:
        raise ProjectRequirementRepositoryError("Project requirement was not saved.")
    requirement = record.data()
    write_event(
        transaction,
        audit,
        project_id,
        "REQUIRES_SKILL",
        f"{project_id}/{skill_id}",
        before,
        requirement,
    )
    return requirement, before is None


def upsert_project_requirement(
    project_id: str,
    skill_id: str,
    min_level: int,
    priority: str,
    *,
    actor: AuditActor,
) -> tuple[dict, bool]:
    audit = AuditContext.create(actor)
    try:
        with graph_db.driver.session() as session:
            return session.execute_write(
                _upsert_project_requirement,
                project_id,
                skill_id,
                min_level,
                priority,
                audit,
            )
    except RepositoryError:
        raise
    except Exception as exc:
        raise ProjectRequirementRepositoryError(
            "Unable to save project requirement."
        ) from exc


def _delete_project_requirement(
    transaction: Transaction, project_id: str, skill_id: str, audit: AuditContext
) -> bool:
    existing = transaction.run(
        LOCK_PROJECT_REQUIREMENT_QUERY, project_id=project_id, skill_id=skill_id
    ).single()
    if not existing or existing["before"] is None:
        return False
    record = transaction.run(
        DELETE_PROJECT_REQUIREMENT_QUERY, project_id=project_id, skill_id=skill_id
    ).single()
    if not record or not record["deleted"]:
        raise ProjectRequirementRepositoryError("Project requirement was not deleted.")
    before = {**existing["before"], "project_id": project_id, "skill_id": skill_id}
    write_event(
        transaction,
        audit,
        project_id,
        "REQUIRES_SKILL",
        f"{project_id}/{skill_id}",
        before,
        None,
    )
    return True


def delete_project_requirement(
    project_id: str, skill_id: str, *, actor: AuditActor
) -> bool:
    audit = AuditContext.create(actor)
    try:
        with graph_db.driver.session() as session:
            return session.execute_write(
                _delete_project_requirement, project_id, skill_id, audit
            )
    except Exception as exc:
        raise ProjectRequirementRepositoryError(
            "Unable to delete project requirement."
        ) from exc
