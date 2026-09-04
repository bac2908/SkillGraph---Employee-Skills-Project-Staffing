from app.db.graph import graph_db
from app.repositories.errors import RepositoryError

PROJECT_MEMBER_IDS_QUERY = """
MATCH (employee:Employee)-[:WORKS_ON]->
      (project:Project {project_id: $project_id})
RETURN employee.employee_id AS employee_id
ORDER BY employee.employee_id
"""

AVAILABLE_CANDIDATE_SKILLS_QUERY = """
MATCH (candidate:Employee)-[employee_skill:HAS_SKILL]->(skill:Skill)
WHERE candidate.status = $employee_status
  AND skill.skill_id IN $skill_ids
RETURN candidate.employee_id AS employee_id,
       candidate.name AS name,
       candidate.email AS email,
       candidate.title AS title,
       candidate.seniority AS seniority,
       candidate.status AS status,
       candidate.location AS location,
       skill.skill_id AS skill_id,
       skill.name AS skill,
       employee_skill.level AS level,
       employee_skill.years_experience AS years_experience
ORDER BY candidate.employee_id, skill.name
"""

COLLABORATION_QUERY = """
MATCH (candidate:Employee)-[:WORKS_ON]->
      (shared_project:Project)<-[:WORKS_ON]-
      (member:Employee)-[:WORKS_ON]->
      (target_project:Project {project_id: $project_id})
WHERE candidate.employee_id IN $candidate_ids
  AND candidate.employee_id <> member.employee_id
  AND shared_project.project_id <> $project_id
RETURN candidate.employee_id AS employee_id,
       count(DISTINCT member) AS collaboration_count,
       collect(DISTINCT member.name) AS collaborators,
       collect(DISTINCT shared_project.name) AS shared_projects
ORDER BY candidate.employee_id
"""


class CandidateRepositoryError(RepositoryError):
    pass


def get_project_member_ids(project_id: str) -> set[str]:
    try:
        with graph_db.driver.session() as session:
            result = session.run(
                PROJECT_MEMBER_IDS_QUERY,
                project_id=project_id,
            )
            return {record["employee_id"] for record in result}
    except Exception as exc:
        raise CandidateRepositoryError(
            "Unable to retrieve the project's current members."
        ) from exc


def get_available_candidate_skills(skill_ids: list[str]) -> list[dict]:
    if not skill_ids:
        return []

    try:
        with graph_db.driver.session() as session:
            result = session.run(
                AVAILABLE_CANDIDATE_SKILLS_QUERY,
                employee_status="AVAILABLE",
                skill_ids=skill_ids,
            )
            return [record.data() for record in result]
    except Exception as exc:
        raise CandidateRepositoryError(
            "Unable to retrieve available candidates."
        ) from exc


def get_previous_collaborations(
    project_id: str,
    candidate_ids: list[str],
) -> list[dict]:
    if not candidate_ids:
        return []

    try:
        with graph_db.driver.session() as session:
            result = session.run(
                COLLABORATION_QUERY,
                project_id=project_id,
                candidate_ids=candidate_ids,
            )
            return [record.data() for record in result]
    except Exception as exc:
        raise CandidateRepositoryError(
            "Unable to retrieve previous collaborations."
        ) from exc
