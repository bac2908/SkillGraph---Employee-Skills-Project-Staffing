from neo4j import Transaction

from app.db.graph import graph_db
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

PROJECT_REQUIREMENT_EXISTS_QUERY = """
MATCH (:Project {project_id: $project_id})
      -[requirement:REQUIRES_SKILL]->
      (:Skill {skill_id: $skill_id})
RETURN count(requirement) > 0 AS relationship_exists
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
) -> tuple[dict, bool]:
    exists_record = transaction.run(
        PROJECT_REQUIREMENT_EXISTS_QUERY,
        project_id=project_id,
        skill_id=skill_id,
    ).single()
    relationship_exists = bool(
        exists_record and exists_record["relationship_exists"]
    )

    record = transaction.run(
        UPSERT_PROJECT_REQUIREMENT_QUERY,
        project_id=project_id,
        skill_id=skill_id,
        min_level=min_level,
        priority=priority,
    ).single()
    if record is None:
        raise ProjectRequirementRepositoryError(
            "Project requirement was not saved."
        )
    return record.data(), not relationship_exists


def upsert_project_requirement(
    project_id: str,
    skill_id: str,
    min_level: int,
    priority: str,
) -> tuple[dict, bool]:
    try:
        with graph_db.driver.session() as session:
            return session.execute_write(
                _upsert_project_requirement,
                project_id,
                skill_id,
                min_level,
                priority,
            )
    except RepositoryError:
        raise
    except Exception as exc:
        raise ProjectRequirementRepositoryError(
            "Unable to save project requirement."
        ) from exc


def delete_project_requirement(project_id: str, skill_id: str) -> bool:
    try:
        with graph_db.driver.session() as session:
            record = session.run(
                DELETE_PROJECT_REQUIREMENT_QUERY,
                project_id=project_id,
                skill_id=skill_id,
            ).single()
            return bool(record and record["deleted"])
    except Exception as exc:
        raise ProjectRequirementRepositoryError(
            "Unable to delete project requirement."
        ) from exc
