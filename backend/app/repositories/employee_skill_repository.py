from neo4j import Transaction

from app.db.graph import graph_db
from app.repositories.errors import RepositoryError

LIST_EMPLOYEE_SKILLS_QUERY = """
MATCH (employee:Employee {employee_id: $employee_id})
      -[employee_skill:HAS_SKILL]->
      (skill:Skill)
RETURN employee.employee_id AS employee_id,
       employee.name AS employee_name,
       skill.skill_id AS skill_id,
       skill.name AS skill_name,
       skill.category AS category,
       employee_skill.level AS level,
       employee_skill.years_experience AS years_experience
ORDER BY toLower(skill.name), skill.skill_id
"""

EMPLOYEE_SKILL_EXISTS_QUERY = """
MATCH (:Employee {employee_id: $employee_id})
      -[employee_skill:HAS_SKILL]->
      (:Skill {skill_id: $skill_id})
RETURN count(employee_skill) > 0 AS relationship_exists
"""

UPSERT_EMPLOYEE_SKILL_QUERY = """
MATCH (employee:Employee {employee_id: $employee_id})
MATCH (skill:Skill {skill_id: $skill_id})
MERGE (employee)-[employee_skill:HAS_SKILL]->(skill)
SET employee_skill.level = $level,
    employee_skill.years_experience = $years_experience
RETURN employee.employee_id AS employee_id,
       employee.name AS employee_name,
       skill.skill_id AS skill_id,
       skill.name AS skill_name,
       skill.category AS category,
       employee_skill.level AS level,
       employee_skill.years_experience AS years_experience
"""

DELETE_EMPLOYEE_SKILL_QUERY = """
MATCH (employee:Employee {employee_id: $employee_id})
      -[employee_skill:HAS_SKILL]->
      (skill:Skill {skill_id: $skill_id})
DELETE employee_skill
RETURN true AS deleted
"""


class EmployeeSkillRepositoryError(RepositoryError):
    pass


def list_employee_skills(employee_id: str) -> list[dict]:
    try:
        with graph_db.driver.session() as session:
            result = session.run(
                LIST_EMPLOYEE_SKILLS_QUERY,
                employee_id=employee_id,
            )
            return [record.data() for record in result]
    except Exception as exc:
        raise EmployeeSkillRepositoryError(
            "Unable to list employee skills."
        ) from exc


def _upsert_employee_skill(
    transaction: Transaction,
    employee_id: str,
    skill_id: str,
    level: int,
    years_experience: float,
) -> tuple[dict, bool]:
    exists_record = transaction.run(
        EMPLOYEE_SKILL_EXISTS_QUERY,
        employee_id=employee_id,
        skill_id=skill_id,
    ).single()
    relationship_exists = bool(
        exists_record and exists_record["relationship_exists"]
    )

    record = transaction.run(
        UPSERT_EMPLOYEE_SKILL_QUERY,
        employee_id=employee_id,
        skill_id=skill_id,
        level=level,
        years_experience=years_experience,
    ).single()
    if record is None:
        raise EmployeeSkillRepositoryError("Employee skill was not saved.")
    return record.data(), not relationship_exists


def upsert_employee_skill(
    employee_id: str,
    skill_id: str,
    level: int,
    years_experience: float,
) -> tuple[dict, bool]:
    try:
        with graph_db.driver.session() as session:
            return session.execute_write(
                _upsert_employee_skill,
                employee_id,
                skill_id,
                level,
                years_experience,
            )
    except RepositoryError:
        raise
    except Exception as exc:
        raise EmployeeSkillRepositoryError(
            "Unable to save employee skill."
        ) from exc


def delete_employee_skill(employee_id: str, skill_id: str) -> bool:
    try:
        with graph_db.driver.session() as session:
            record = session.run(
                DELETE_EMPLOYEE_SKILL_QUERY,
                employee_id=employee_id,
                skill_id=skill_id,
            ).single()
            return bool(record and record["deleted"])
    except Exception as exc:
        raise EmployeeSkillRepositoryError(
            "Unable to delete employee skill."
        ) from exc
