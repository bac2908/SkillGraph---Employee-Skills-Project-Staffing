from neo4j import Transaction
from neo4j.exceptions import ConstraintError

from app.db.graph import graph_db
from app.repositories.errors import DuplicateRecordError, RepositoryError

SKILL_FIELDS = """
skill.skill_id AS skill_id,
skill.name AS name,
skill.category AS category
"""

GET_SKILL_QUERY = f"""
MATCH (skill:Skill {{skill_id: $skill_id}})
RETURN {SKILL_FIELDS}
"""

LIST_SKILLS_QUERY = f"""
MATCH (skill:Skill)
WHERE ($search IS NULL
       OR toLower(skill.skill_id) CONTAINS toLower($search)
       OR toLower(skill.name) CONTAINS toLower($search))
  AND ($category IS NULL
       OR toLower(skill.category) = toLower($category))
RETURN {SKILL_FIELDS}
ORDER BY toLower(skill.name), skill.skill_id
SKIP $offset
LIMIT $limit
"""

COUNT_SKILLS_QUERY = """
MATCH (skill:Skill)
WHERE ($search IS NULL
       OR toLower(skill.skill_id) CONTAINS toLower($search)
       OR toLower(skill.name) CONTAINS toLower($search))
  AND ($category IS NULL
       OR toLower(skill.category) = toLower($category))
RETURN count(skill) AS total
"""

SKILL_NAME_EXISTS_QUERY = """
MATCH (skill:Skill)
WHERE toLower(skill.name) = toLower($name)
  AND ($exclude_skill_id IS NULL OR skill.skill_id <> $exclude_skill_id)
RETURN count(skill) > 0 AS name_exists
"""

CREATE_SKILL_QUERY = f"""
CREATE (skill:Skill)
SET skill = $properties
RETURN {SKILL_FIELDS}
"""

UPDATE_SKILL_QUERY = f"""
MATCH (skill:Skill {{skill_id: $skill_id}})
SET skill += $updates
RETURN {SKILL_FIELDS}
"""

SKILL_RELATIONSHIP_COUNT_QUERY = """
MATCH (skill:Skill {skill_id: $skill_id})
OPTIONAL MATCH (skill)-[relationship]-()
RETURN count(relationship) AS relationship_count
"""

DELETE_SKILL_QUERY = """
MATCH (skill:Skill {skill_id: $skill_id})
DELETE skill
"""


class SkillRepositoryError(RepositoryError):
    pass


def _list_skills(
    transaction: Transaction,
    search: str | None,
    category: str | None,
    limit: int,
    offset: int,
) -> tuple[list[dict], int]:
    parameters = {
        "search": search,
        "category": category,
        "limit": limit,
        "offset": offset,
    }
    total_record = transaction.run(
        COUNT_SKILLS_QUERY,
        **parameters,
    ).single()
    items = [
        record.data()
        for record in transaction.run(LIST_SKILLS_QUERY, **parameters)
    ]
    return items, total_record["total"] if total_record else 0


def list_skills(
    search: str | None,
    category: str | None,
    limit: int,
    offset: int,
) -> tuple[list[dict], int]:
    try:
        with graph_db.driver.session() as session:
            return session.execute_read(
                _list_skills,
                search,
                category,
                limit,
                offset,
            )
    except Exception as exc:
        raise SkillRepositoryError("Unable to list skills.") from exc


def get_skill(skill_id: str) -> dict | None:
    try:
        with graph_db.driver.session() as session:
            record = session.run(
                GET_SKILL_QUERY,
                skill_id=skill_id,
            ).single()
            return record.data() if record else None
    except Exception as exc:
        raise SkillRepositoryError("Unable to retrieve skill.") from exc


def skill_name_exists(
    name: str,
    exclude_skill_id: str | None = None,
) -> bool:
    try:
        with graph_db.driver.session() as session:
            record = session.run(
                SKILL_NAME_EXISTS_QUERY,
                name=name,
                exclude_skill_id=exclude_skill_id,
            ).single()
            return bool(record and record["name_exists"])
    except Exception as exc:
        raise SkillRepositoryError(
            "Unable to check skill name uniqueness."
        ) from exc


def create_skill(properties: dict) -> dict:
    try:
        with graph_db.driver.session() as session:
            record = session.run(
                CREATE_SKILL_QUERY,
                properties=properties,
            ).single()
            if record is None:
                raise SkillRepositoryError("Skill was not created.")
            return record.data()
    except ConstraintError as exc:
        raise DuplicateRecordError("Skill already exists.") from exc
    except RepositoryError:
        raise
    except Exception as exc:
        raise SkillRepositoryError("Unable to create skill.") from exc


def update_skill(skill_id: str, updates: dict) -> dict | None:
    try:
        with graph_db.driver.session() as session:
            record = session.run(
                UPDATE_SKILL_QUERY,
                skill_id=skill_id,
                updates=updates,
            ).single()
            return record.data() if record else None
    except ConstraintError as exc:
        raise DuplicateRecordError("Skill update is not unique.") from exc
    except Exception as exc:
        raise SkillRepositoryError("Unable to update skill.") from exc


def _delete_skill(
    transaction: Transaction,
    skill_id: str,
) -> int | None:
    record = transaction.run(
        SKILL_RELATIONSHIP_COUNT_QUERY,
        skill_id=skill_id,
    ).single()
    if record is None:
        return None

    relationship_count = record["relationship_count"]
    if relationship_count == 0:
        transaction.run(DELETE_SKILL_QUERY, skill_id=skill_id).consume()
    return relationship_count


def delete_skill(skill_id: str) -> int | None:
    try:
        with graph_db.driver.session() as session:
            return session.execute_write(_delete_skill, skill_id)
    except Exception as exc:
        raise SkillRepositoryError("Unable to delete skill.") from exc
