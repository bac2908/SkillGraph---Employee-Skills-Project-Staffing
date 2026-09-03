from app.db.graph import graph_db


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


class ProjectRepositoryError(RuntimeError):
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
