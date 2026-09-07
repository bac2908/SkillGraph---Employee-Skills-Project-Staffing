from app.db.graph import graph_db

TEAMS = [
    {"team_id": "TEAM001", "name": "Backend Team", "description": "Backend services and APIs"},
    {"team_id": "TEAM002", "name": "Frontend Team", "description": "Web frontend development"},
    {"team_id": "TEAM003", "name": "Platform Team", "description": "Infrastructure, DevOps and cloud platform"},
]

SKILLS = [
    {"skill_id": "SK001", "name": "Python", "category": "Backend"},
    {"skill_id": "SK002", "name": "FastAPI", "category": "Backend"},
    {"skill_id": "SK003", "name": "Java", "category": "Backend"},
    {"skill_id": "SK004", "name": "Spring Boot", "category": "Backend"},
    {"skill_id": "SK005", "name": "MySQL", "category": "Database"},
    {"skill_id": "SK006", "name": "PostgreSQL", "category": "Database"},
    {"skill_id": "SK007", "name": "Docker", "category": "DevOps"},
    {"skill_id": "SK008", "name": "React", "category": "Frontend"},
    {"skill_id": "SK009", "name": "TypeScript", "category": "Frontend"},
    {"skill_id": "SK010", "name": "AWS", "category": "Cloud"},
    {"skill_id": "SK011", "name": "Linux", "category": "DevOps"},
    {"skill_id": "SK012", "name": "Redis", "category": "Database"},
]

EMPLOYEES = [
    {"employee_id": "EMP001", "name": "Nguyen Van Bac", "email": "bac@example.com", "title": "Backend Developer", "seniority": "Junior", "status": "AVAILABLE", "location": "Ho Chi Minh City"},
    {"employee_id": "EMP002", "name": "An Nguyen", "email": "an@example.com", "title": "Backend Developer", "seniority": "Middle", "status": "ASSIGNED", "location": "Ho Chi Minh City"},
    {"employee_id": "EMP003", "name": "Minh Tran", "email": "minh@example.com", "title": "Frontend Developer", "seniority": "Junior", "status": "ASSIGNED", "location": "Ho Chi Minh City"},
    {"employee_id": "EMP004", "name": "Lan Le", "email": "lan@example.com", "title": "DevOps Engineer", "seniority": "Middle", "status": "AVAILABLE", "location": "Da Nang"},
    {"employee_id": "EMP005", "name": "Huy Pham", "email": "huy@example.com", "title": "Backend Developer", "seniority": "Middle", "status": "ASSIGNED", "location": "Ho Chi Minh City"},
    {"employee_id": "EMP006", "name": "Mai Vo", "email": "mai@example.com", "title": "Full-stack Developer", "seniority": "Junior", "status": "AVAILABLE", "location": "Ho Chi Minh City"},
    {"employee_id": "EMP007", "name": "Khoa Nguyen", "email": "khoa@example.com", "title": "Backend Developer", "seniority": "Junior", "status": "AVAILABLE", "location": "Ha Noi"},
    {"employee_id": "EMP008", "name": "Thao Tran", "email": "thao@example.com", "title": "Data Engineer", "seniority": "Middle", "status": "AVAILABLE", "location": "Ho Chi Minh City"},
]

PROJECTS = [
    {"project_id": "PROJ001", "name": "E-commerce Platform", "description": "Online commerce platform for customers and administrators", "status": "ACTIVE"},
    {"project_id": "PROJ002", "name": "Cloud Gaming Platform", "description": "Cloud gaming and remote gaming infrastructure platform", "status": "ACTIVE"},
    {"project_id": "PROJ003", "name": "Analytics Platform", "description": "Internal analytics and reporting platform", "status": "PLANNING"},
]

TEAM_MEMBERSHIPS = [
    {"employee_id": "EMP001", "team_id": "TEAM001"},
    {"employee_id": "EMP002", "team_id": "TEAM001"},
    {"employee_id": "EMP003", "team_id": "TEAM002"},
    {"employee_id": "EMP004", "team_id": "TEAM003"},
    {"employee_id": "EMP005", "team_id": "TEAM001"},
    {"employee_id": "EMP006", "team_id": "TEAM002"},
    {"employee_id": "EMP007", "team_id": "TEAM001"},
    {"employee_id": "EMP008", "team_id": "TEAM003"},
]

EMPLOYEE_SKILLS = [
    {"employee_id": "EMP001", "skill_id": "SK001", "level": 4, "years_experience": 2},
    {"employee_id": "EMP001", "skill_id": "SK002", "level": 4, "years_experience": 2},
    {"employee_id": "EMP001", "skill_id": "SK003", "level": 3, "years_experience": 1},
    {"employee_id": "EMP001", "skill_id": "SK004", "level": 2, "years_experience": 1},
    {"employee_id": "EMP001", "skill_id": "SK005", "level": 3, "years_experience": 1},
    {"employee_id": "EMP001", "skill_id": "SK006", "level": 3, "years_experience": 2},
    {"employee_id": "EMP001", "skill_id": "SK007", "level": 3, "years_experience": 1},
    {"employee_id": "EMP002", "skill_id": "SK003", "level": 4, "years_experience": 4},
    {"employee_id": "EMP002", "skill_id": "SK004", "level": 4, "years_experience": 3},
    {"employee_id": "EMP002", "skill_id": "SK005", "level": 4, "years_experience": 3},
    {"employee_id": "EMP002", "skill_id": "SK007", "level": 2, "years_experience": 1},
    {"employee_id": "EMP003", "skill_id": "SK008", "level": 4, "years_experience": 3},
    {"employee_id": "EMP003", "skill_id": "SK009", "level": 4, "years_experience": 3},
    {"employee_id": "EMP003", "skill_id": "SK007", "level": 2, "years_experience": 1},
    {"employee_id": "EMP004", "skill_id": "SK007", "level": 4, "years_experience": 4},
    {"employee_id": "EMP004", "skill_id": "SK010", "level": 4, "years_experience": 3},
    {"employee_id": "EMP004", "skill_id": "SK011", "level": 4, "years_experience": 4},
    {"employee_id": "EMP004", "skill_id": "SK001", "level": 3, "years_experience": 2},
    {"employee_id": "EMP005", "skill_id": "SK005", "level": 4, "years_experience": 4},
    {"employee_id": "EMP005", "skill_id": "SK003", "level": 3, "years_experience": 2},
    {"employee_id": "EMP005", "skill_id": "SK006", "level": 3, "years_experience": 2},
    {"employee_id": "EMP006", "skill_id": "SK003", "level": 3, "years_experience": 2},
    {"employee_id": "EMP006", "skill_id": "SK004", "level": 3, "years_experience": 2},
    {"employee_id": "EMP006", "skill_id": "SK008", "level": 2, "years_experience": 1},
    {"employee_id": "EMP006", "skill_id": "SK009", "level": 3, "years_experience": 2},
    {"employee_id": "EMP007", "skill_id": "SK012", "level": 4, "years_experience": 2},
    {"employee_id": "EMP007", "skill_id": "SK007", "level": 2, "years_experience": 1},
    {"employee_id": "EMP007", "skill_id": "SK001", "level": 3, "years_experience": 2},
    {"employee_id": "EMP007", "skill_id": "SK002", "level": 3, "years_experience": 1},
    {"employee_id": "EMP008", "skill_id": "SK006", "level": 4, "years_experience": 4},
    {"employee_id": "EMP008", "skill_id": "SK001", "level": 3, "years_experience": 3},
    {"employee_id": "EMP008", "skill_id": "SK002", "level": 3, "years_experience": 2},
    {"employee_id": "EMP008", "skill_id": "SK010", "level": 3, "years_experience": 2},
]

WORK_ASSIGNMENTS = [
    {"employee_id": "EMP002", "project_id": "PROJ001", "role": "Backend Developer", "allocation": 80},
    {"employee_id": "EMP003", "project_id": "PROJ001", "role": "Frontend Developer", "allocation": 100},
    {"employee_id": "EMP005", "project_id": "PROJ001", "role": "Backend Developer", "allocation": 80},
    {"employee_id": "EMP001", "project_id": "PROJ002", "role": "Backend Developer", "allocation": 80},
    {"employee_id": "EMP002", "project_id": "PROJ002", "role": "Backend Developer", "allocation": 20},
    {"employee_id": "EMP004", "project_id": "PROJ003", "role": "DevOps Engineer", "allocation": 40},
    {"employee_id": "EMP007", "project_id": "PROJ003", "role": "Backend Developer", "allocation": 50},
    {"employee_id": "EMP008", "project_id": "PROJ003", "role": "Data Engineer", "allocation": 80},
]

PROJECT_SKILLS = [
    {"project_id": "PROJ001", "skill_id": "SK003", "min_level": 3, "priority": "MUST"},
    {"project_id": "PROJ001", "skill_id": "SK004", "min_level": 3, "priority": "MUST"},
    {"project_id": "PROJ001", "skill_id": "SK005", "min_level": 3, "priority": "MUST"},
    {"project_id": "PROJ001", "skill_id": "SK007", "min_level": 3, "priority": "SHOULD"},
    {"project_id": "PROJ001", "skill_id": "SK008", "min_level": 2, "priority": "SHOULD"},
    {"project_id": "PROJ002", "skill_id": "SK001", "min_level": 3, "priority": "MUST"},
    {"project_id": "PROJ002", "skill_id": "SK002", "min_level": 3, "priority": "MUST"},
    {"project_id": "PROJ002", "skill_id": "SK006", "min_level": 3, "priority": "MUST"},
    {"project_id": "PROJ002", "skill_id": "SK007", "min_level": 2, "priority": "SHOULD"},
    {"project_id": "PROJ003", "skill_id": "SK001", "min_level": 3, "priority": "MUST"},
    {"project_id": "PROJ003", "skill_id": "SK006", "min_level": 3, "priority": "MUST"},
    {"project_id": "PROJ003", "skill_id": "SK010", "min_level": 3, "priority": "SHOULD"},
    {"project_id": "PROJ003", "skill_id": "SK012", "min_level": 2, "priority": "NICE"},
]

PROJECT_OWNERS = [
    {"project_id": "PROJ001", "team_id": "TEAM001"},
    {"project_id": "PROJ002", "team_id": "TEAM001"},
    {"project_id": "PROJ003", "team_id": "TEAM003"},
]

TEAM_QUERY = """
UNWIND $rows AS row
MERGE (team:Team {team_id: row.team_id})
SET team.name = row.name, team.description = row.description
"""
SKILL_QUERY = """
UNWIND $rows AS row
MERGE (skill:Skill {skill_id: row.skill_id})
SET skill.name = row.name, skill.category = row.category
"""
EMPLOYEE_QUERY = """
UNWIND $rows AS row
MERGE (employee:Employee {employee_id: row.employee_id})
SET employee.name = row.name, employee.email = row.email,
    employee.title = row.title, employee.seniority = row.seniority,
    employee.status = row.status, employee.location = row.location
"""
PROJECT_QUERY = """
UNWIND $rows AS row
MERGE (project:Project {project_id: row.project_id})
SET project.name = row.name, project.description = row.description,
    project.status = row.status
"""
MEMBER_OF_QUERY = """
UNWIND $rows AS row
MATCH (employee:Employee {employee_id: row.employee_id})
MATCH (team:Team {team_id: row.team_id})
MERGE (employee)-[:MEMBER_OF]->(team)
"""
HAS_SKILL_QUERY = """
UNWIND $rows AS row
MATCH (employee:Employee {employee_id: row.employee_id})
MATCH (skill:Skill {skill_id: row.skill_id})
MERGE (employee)-[relationship:HAS_SKILL]->(skill)
SET relationship.level = row.level,
    relationship.years_experience = row.years_experience
"""
WORKS_ON_QUERY = """
UNWIND $rows AS row
MATCH (employee:Employee {employee_id: row.employee_id})
MATCH (project:Project {project_id: row.project_id})
MERGE (employee)-[relationship:WORKS_ON]->(project)
SET relationship.role = row.role,
    relationship.allocation = row.allocation
"""
REQUIRES_SKILL_QUERY = """
UNWIND $rows AS row
MATCH (project:Project {project_id: row.project_id})
MATCH (skill:Skill {skill_id: row.skill_id})
MERGE (project)-[relationship:REQUIRES_SKILL]->(skill)
SET relationship.min_level = row.min_level,
    relationship.priority = row.priority
"""
OWNED_BY_QUERY = """
UNWIND $rows AS row
MATCH (project:Project {project_id: row.project_id})
MATCH (team:Team {team_id: row.team_id})
MERGE (project)-[:OWNED_BY]->(team)
"""

NODE_COUNT_QUERIES = {
    "Teams": "MATCH (node:Team) RETURN count(node) AS count",
    "Skills": "MATCH (node:Skill) RETURN count(node) AS count",
    "Employees": "MATCH (node:Employee) RETURN count(node) AS count",
    "Projects": "MATCH (node:Project) RETURN count(node) AS count",
}
RELATIONSHIP_COUNT_QUERIES = {
    "MEMBER_OF": "MATCH ()-[relationship:MEMBER_OF]->() RETURN count(relationship) AS count",
    "HAS_SKILL": "MATCH ()-[relationship:HAS_SKILL]->() RETURN count(relationship) AS count",
    "WORKS_ON": "MATCH ()-[relationship:WORKS_ON]->() RETURN count(relationship) AS count",
    "REQUIRES_SKILL": "MATCH ()-[relationship:REQUIRES_SKILL]->() RETURN count(relationship) AS count",
    "OWNED_BY": "MATCH ()-[relationship:OWNED_BY]->() RETURN count(relationship) AS count",
}
EXPECTED_COUNTS = {
    "Teams": 3, "Skills": 12, "Employees": 8, "Projects": 3, "Nodes": 26,
    "MEMBER_OF": 8, "HAS_SKILL": 33, "WORKS_ON": 8,
    "REQUIRES_SKILL": 13, "OWNED_BY": 3, "Relationships": 65,
}

BAC_SKILLS_QUERY = """
MATCH (employee:Employee {employee_id: $employee_id})
      -[relationship:HAS_SKILL]->(skill:Skill)
RETURN skill.name AS name, relationship.level AS level
"""
ECOMMERCE_REQUIREMENTS_QUERY = """
MATCH (project:Project {project_id: $project_id})
      -[relationship:REQUIRES_SKILL]->(skill:Skill)
RETURN skill.name AS name, relationship.min_level AS min_level,
       relationship.priority AS priority
"""
PROJECT_MEMBERS_QUERY = """
MATCH (employee:Employee)-[:WORKS_ON]->(project:Project {project_id: $project_id})
RETURN employee.name AS name
"""
COLLABORATION_TRAVERSAL_QUERY = """
MATCH (bac:Employee {employee_id: $bac_id})-[:WORKS_ON]->
      (cloud:Project {project_id: $cloud_project_id})<-[:WORKS_ON]-
      (an:Employee {employee_id: $an_id})-[:WORKS_ON]->
      (ecommerce:Project {project_id: $ecommerce_project_id})
RETURN count(*) > 0 AS traversal_exists
"""
DOCKER_GAP_SCENARIO_QUERY = """
MATCH (project:Project {project_id: $project_id})
MATCH (docker:Skill {skill_id: $docker_skill_id})
MATCH (bac:Employee {employee_id: $bac_id})
MATCH (project)-[requirement:REQUIRES_SKILL]->(docker)
MATCH (bac)-[bac_skill:HAS_SKILL]->(docker)
MATCH (member:Employee)-[:WORKS_ON]->(project)
MATCH (member)-[member_skill:HAS_SKILL]->(docker)
RETURN requirement.min_level AS required_level,
       requirement.priority AS priority,
       max(member_skill.level) AS current_team_level,
       bac_skill.level AS bac_level
"""
BAC_ECOMMERCE_ASSIGNMENT_COUNT_QUERY = """
MATCH (bac:Employee {employee_id: $bac_id})
      -[assignment:WORKS_ON]->
      (project:Project {project_id: $project_id})
RETURN count(assignment) AS count
"""
OVERALLOCATED_EMPLOYEES_QUERY = """
MATCH (employee:Employee)-[assignment:WORKS_ON]->(:Project)
WITH employee, sum(assignment.allocation) AS total_allocation
WHERE total_allocation > 100
RETURN employee.employee_id AS employee_id,
       total_allocation
ORDER BY employee.employee_id
"""


class SeedValidationError(RuntimeError):
    pass


def _consume_write(transaction, query, rows):
    transaction.run(query, rows=rows).consume()


def _seed_graph(transaction):
    for query, rows in (
        (TEAM_QUERY, TEAMS),
        (SKILL_QUERY, SKILLS),
        (EMPLOYEE_QUERY, EMPLOYEES),
        (PROJECT_QUERY, PROJECTS),
        (MEMBER_OF_QUERY, TEAM_MEMBERSHIPS),
        (HAS_SKILL_QUERY, EMPLOYEE_SKILLS),
        (WORKS_ON_QUERY, WORK_ASSIGNMENTS),
        (REQUIRES_SKILL_QUERY, PROJECT_SKILLS),
        (OWNED_BY_QUERY, PROJECT_OWNERS),
    ):
        _consume_write(transaction, query, rows)


def _read_count(session, query):
    record = session.run(query).single()
    if record is None:
        raise SeedValidationError("A count query returned no result.")
    return record["count"]


def _database_summary(session):
    summary = {name: _read_count(session, query) for name, query in NODE_COUNT_QUERIES.items()}
    summary["Nodes"] = _read_count(session, "MATCH (node) RETURN count(node) AS count")
    summary.update({name: _read_count(session, query) for name, query in RELATIONSHIP_COUNT_QUERIES.items()})
    summary["Relationships"] = _read_count(
        session, "MATCH ()-[relationship]->() RETURN count(relationship) AS count"
    )
    return summary


def _validate_expected_counts(summary):
    mismatches = [
        f"{name}: expected {expected}, got {summary[name]}"
        for name, expected in EXPECTED_COUNTS.items()
        if summary[name] != expected
    ]
    if mismatches:
        raise SeedValidationError("Count mismatch: " + "; ".join(mismatches))


def _validate_bac_skills(session):
    result = session.run(BAC_SKILLS_QUERY, employee_id="EMP001")
    actual = {record["name"]: record["level"] for record in result}
    expected = {
        "Python": 4, "FastAPI": 4, "Java": 3, "Spring Boot": 2,
        "MySQL": 3, "PostgreSQL": 3, "Docker": 3,
    }
    if actual != expected:
        raise SeedValidationError("EMP001 skill validation failed.")


def _validate_ecommerce_requirements(session):
    result = session.run(ECOMMERCE_REQUIREMENTS_QUERY, project_id="PROJ001")
    actual = {
        record["name"]: (record["min_level"], record["priority"])
        for record in result
    }
    expected = {
        "Java": (3, "MUST"), "Spring Boot": (3, "MUST"),
        "MySQL": (3, "MUST"), "Docker": (3, "SHOULD"),
        "React": (2, "SHOULD"),
    }
    if actual != expected:
        raise SeedValidationError("PROJ001 requirement validation failed.")


def _validate_ecommerce_members(session):
    result = session.run(PROJECT_MEMBERS_QUERY, project_id="PROJ001")
    actual = {record["name"] for record in result}
    if actual != {"An Nguyen", "Minh Tran", "Huy Pham"}:
        raise SeedValidationError("PROJ001 member validation failed.")


def _validate_collaboration_traversal(session):
    record = session.run(
        COLLABORATION_TRAVERSAL_QUERY,
        bac_id="EMP001",
        cloud_project_id="PROJ002",
        an_id="EMP002",
        ecommerce_project_id="PROJ001",
    ).single()
    if record is None or not record["traversal_exists"]:
        raise SeedValidationError("Collaboration traversal validation failed.")


def _validate_docker_gap_scenario(session):
    record = session.run(
        DOCKER_GAP_SCENARIO_QUERY,
        project_id="PROJ001",
        docker_skill_id="SK007",
        bac_id="EMP001",
    ).single()
    expected = {
        "required_level": 3,
        "priority": "SHOULD",
        "current_team_level": 2,
        "bac_level": 3,
    }
    if record is None or record.data() != expected:
        raise SeedValidationError("Docker gap business scenario validation failed.")

    assignment_record = session.run(
        BAC_ECOMMERCE_ASSIGNMENT_COUNT_QUERY,
        bac_id="EMP001",
        project_id="PROJ001",
    ).single()
    if assignment_record is None or assignment_record["count"] != 0:
        raise SeedValidationError("EMP001 must not be assigned to PROJ001.")


def _validate_allocation_limits(session):
    overallocated = [
        record.data()
        for record in session.run(OVERALLOCATED_EMPLOYEES_QUERY)
    ]
    if overallocated:
        raise SeedValidationError(
            f"Employee allocation exceeds 100%: {overallocated}"
        )


def _validate_seed(session, summary):
    _validate_expected_counts(summary)
    _validate_bac_skills(session)
    _validate_ecommerce_requirements(session)
    _validate_ecommerce_members(session)
    _validate_collaboration_traversal(session)
    _validate_docker_gap_scenario(session)
    _validate_allocation_limits(session)


def _print_summary(summary):
    print("Database summary:")
    for name in ("Teams", "Skills", "Employees", "Projects", "Nodes"):
        print(f"  {name}: {summary[name]}")
    for name in (
        "MEMBER_OF", "HAS_SKILL", "WORKS_ON", "REQUIRES_SKILL",
        "OWNED_BY", "Relationships",
    ):
        print(f"  {name}: {summary[name]}")


def main():
    try:
        graph_db.verify_connection()
        print("CognoDB connectivity verified.")
        with graph_db.driver.session() as session:
            session.execute_write(_seed_graph)
            summary = _database_summary(session)
            _validate_seed(session, summary)
            _print_summary(summary)
        print("Seed completed and all validations passed.")
        print("Traversal verified: Bac -> Cloud Gaming <- An -> E-commerce.")
        return 0
    except SeedValidationError as exc:
        print(f"Seed validation failed: {exc}")
        return 1
    except Exception as exc:
        print(
            f"Seeding failed ({type(exc).__name__}). "
            "Check CognoDB connectivity, credentials, and seed data."
        )
        return 1
    finally:
        graph_db.close()


if __name__ == "__main__":
    raise SystemExit(main())
