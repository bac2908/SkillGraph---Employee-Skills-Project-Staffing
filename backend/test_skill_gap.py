from app.db.graph import graph_db
from app.services.skill_gap_service import SkillGapService


PROJECT_ID = "PROJ001"

EXPECTED_SKILLS = {
    "Java": {"required_level": 3, "best_team_level": 4, "status": "COVERED"},
    "Spring Boot": {"required_level": 3, "best_team_level": 4, "status": "COVERED"},
    "MySQL": {"required_level": 3, "best_team_level": 4, "status": "COVERED"},
    "Docker": {"required_level": 3, "best_team_level": 2, "status": "GAP"},
    "React": {"required_level": 2, "best_team_level": 4, "status": "COVERED"},
}

EXPECTED_SUMMARY = {
    "total": 5,
    "covered": 4,
    "gap": 1,
    "missing": 0,
    "coverage_percent": 80.0,
}


def validate_result(result: dict) -> None:
    actual_skills = {
        skill["skill"]: {
            "required_level": skill["required_level"],
            "best_team_level": skill["best_team_level"],
            "status": skill["status"],
        }
        for skill in result["skills"]
    }

    if actual_skills != EXPECTED_SKILLS:
        raise AssertionError(
            "Skill Gap result does not match the expected PROJ001 values."
        )

    if result["summary"] != EXPECTED_SUMMARY:
        raise AssertionError(
            "Skill Gap summary does not match the expected PROJ001 totals."
        )


def print_result(result: dict) -> None:
    print("Skill Gap Analysis")
    print("==================")
    print(f"Project: {result['project_id']}")
    print()

    for skill in result["skills"]:
        print(
            f"{skill['skill']:<15} "
            f"required={skill['required_level']} "
            f"best={skill['best_team_level']} "
            f"status={skill['status']}"
        )

    summary = result["summary"]
    print()
    print("Summary")
    print("-------")
    print(f"Total: {summary['total']}")
    print(f"Covered: {summary['covered']}")
    print(f"Gap: {summary['gap']}")
    print(f"Missing: {summary['missing']}")
    print(f"Coverage: {summary['coverage_percent']}%")


def main() -> int:
    try:
        graph_db.verify_connection()
        result = SkillGapService().analyze(PROJECT_ID)
        validate_result(result)
        print_result(result)
        print()
        print("Skill Gap validation: PASS")
        return 0
    except Exception as exc:
        print(f"Skill Gap validation failed: {exc}")
        return 1
    finally:
        graph_db.close()


if __name__ == "__main__":
    raise SystemExit(main())
