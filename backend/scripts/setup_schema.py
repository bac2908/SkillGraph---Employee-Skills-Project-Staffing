from app.db.graph import graph_db
from scripts.setup_activity_schema import setup_activity_schema

CONSTRAINTS = {
    "employee_employee_id_unique": """
        CREATE CONSTRAINT employee_employee_id_unique IF NOT EXISTS
        FOR (employee:Employee)
        REQUIRE employee.employee_id IS UNIQUE
    """,
    "employee_email_unique": """
        CREATE CONSTRAINT employee_email_unique IF NOT EXISTS
        FOR (employee:Employee)
        REQUIRE employee.email IS UNIQUE
    """,
    "skill_skill_id_unique": """
        CREATE CONSTRAINT skill_skill_id_unique IF NOT EXISTS
        FOR (skill:Skill)
        REQUIRE skill.skill_id IS UNIQUE
    """,
    "skill_name_unique": """
        CREATE CONSTRAINT skill_name_unique IF NOT EXISTS
        FOR (skill:Skill)
        REQUIRE skill.name IS UNIQUE
    """,
    "project_project_id_unique": """
        CREATE CONSTRAINT project_project_id_unique IF NOT EXISTS
        FOR (project:Project)
        REQUIRE project.project_id IS UNIQUE
    """,
    "team_team_id_unique": """
        CREATE CONSTRAINT team_team_id_unique IF NOT EXISTS
        FOR (team:Team)
        REQUIRE team.team_id IS UNIQUE
    """,
}

SHOW_CONSTRAINTS_QUERY = """
SHOW CONSTRAINTS
YIELD name
RETURN name
ORDER BY name
"""


class SchemaSetupError(RuntimeError):
    pass


def _create_constraints(session):
    for query in CONSTRAINTS.values():
        session.run(query).consume()


def _verify_constraints(session):
    result = session.run(SHOW_CONSTRAINTS_QUERY)
    actual_names = {record["name"] for record in result}
    missing_names = set(CONSTRAINTS) - actual_names
    if missing_names:
        missing = ", ".join(sorted(missing_names))
        raise SchemaSetupError(f"Missing constraints: {missing}")
    return sorted(actual_names)


def main():
    try:
        graph_db.verify_connection()
        print("CognoDB connectivity verified.")

        with graph_db.driver.session() as session:
            _create_constraints(session)
            constraint_names = _verify_constraints(session)
            setup_activity_schema(session)

        print("Schema constraints ready:")
        for constraint_name in constraint_names:
            print(f"  {constraint_name}")
        return 0

    except SchemaSetupError as exc:
        print(f"Schema validation failed: {exc}")
        return 1

    except Exception as exc:
        print(
            f"Schema setup failed ({type(exc).__name__}). "
            "Check CognoDB compatibility, connectivity, and existing data."
        )
        return 1

    finally:
        graph_db.close()


if __name__ == "__main__":
    raise SystemExit(main())
