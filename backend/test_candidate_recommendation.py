from app.db.graph import graph_db
from app.services.candidate_recommendation_service import (
    CandidateRecommendationService,
)

PROJECT_ID = "PROJ001"


def validate_result(result: dict) -> None:
    if result["summary"] != {
        "uncovered_skill_count": 1,
        "candidate_count": 2,
    }:
        raise AssertionError("Recommendation summary is incorrect.")

    uncovered_skills = result["uncovered_skills"]
    if len(uncovered_skills) != 1:
        raise AssertionError("PROJ001 must have exactly one uncovered skill.")
    if (
        uncovered_skills[0]["skill"] != "Docker"
        or uncovered_skills[0]["status"] != "GAP"
    ):
        raise AssertionError("Docker must be the PROJ001 gap.")

    candidates = result["candidates"]
    if [candidate["employee_id"] for candidate in candidates] != [
        "EMP001",
        "EMP004",
    ]:
        raise AssertionError("Expected Bac first and Lan second.")

    bac = candidates[0]
    if bac["rank"] != 1 or bac["collaboration_count"] != 1:
        raise AssertionError("Bac must rank first with one collaborator.")
    if bac["collaborators"] != ["An Nguyen"]:
        raise AssertionError("Bac must have collaborated with An Nguyen.")
    if bac["shared_projects"] != ["Cloud Gaming Platform"]:
        raise AssertionError("Bac and An must share Cloud Gaming Platform.")
    if bac["matched_skills"][0]["skill"] != "Docker":
        raise AssertionError("Bac must match the Docker gap.")
    if bac["matched_skills"][0]["level"] != 3:
        raise AssertionError("Bac's Docker level must be 3.")

    lan = candidates[1]
    if lan["rank"] != 2 or lan["collaboration_count"] != 0:
        raise AssertionError("Lan must rank second without collaboration.")
    if lan["matched_skills"][0]["level"] != 4:
        raise AssertionError("Lan's Docker level must be 4.")


def print_result(result: dict) -> None:
    print("Candidate Recommendation")
    print("========================")
    print(f"Project: {result['project_id']}")
    print("Uncovered skill: Docker (required level 3)")
    print()

    for candidate in result["candidates"]:
        docker = candidate["matched_skills"][0]
        collaborators = ", ".join(candidate["collaborators"]) or "None"
        print(
            f"#{candidate['rank']} {candidate['name']} "
            f"Docker={docker['level']} "
            f"collaborations={candidate['collaboration_count']} "
            f"with={collaborators}"
        )

    print()
    print(f"Candidates: {result['summary']['candidate_count']}")


def main() -> int:
    try:
        graph_db.verify_connection()
        result = CandidateRecommendationService().recommend(PROJECT_ID)
        validate_result(result)
        print_result(result)
        print("Candidate Recommendation validation: PASS")
        return 0
    except Exception as exc:
        print(f"Candidate Recommendation validation failed: {exc}")
        return 1
    finally:
        graph_db.close()


if __name__ == "__main__":
    raise SystemExit(main())
