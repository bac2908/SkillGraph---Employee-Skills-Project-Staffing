from app.core.exceptions import ResourceNotFoundError
from app.repositories import project_repository


class ProjectNotFoundError(ResourceNotFoundError):
    def __init__(self, project_id: str) -> None:
        super().__init__("Project", project_id)


class SkillGapService:
    def analyze(self, project_id: str) -> dict:
        if not project_id or not project_id.strip():
            raise ValueError("project_id is required.")

        if not project_repository.project_exists(project_id):
            raise ProjectNotFoundError(project_id)

        required_skills = project_repository.get_required_skills(project_id)
        team_skill_levels = project_repository.get_team_skill_levels(project_id)
        team_skill_map = {
            row["skill_id"]: row
            for row in team_skill_levels
        }

        skills = []
        covered_count = 0
        gap_count = 0
        missing_count = 0

        for requirement in required_skills:
            team_skill = team_skill_map.get(requirement["skill_id"])

            if team_skill is None:
                best_team_level = 0
                employee_count = 0
                status = "MISSING"
                missing_count += 1
            else:
                best_team_level = team_skill["best_team_level"]
                employee_count = team_skill["employee_count"]

                if best_team_level >= requirement["required_level"]:
                    status = "COVERED"
                    covered_count += 1
                else:
                    status = "GAP"
                    gap_count += 1

            skills.append(
                {
                    "skill_id": requirement["skill_id"],
                    "skill": requirement["skill"],
                    "required_level": requirement["required_level"],
                    "best_team_level": best_team_level,
                    "employee_count": employee_count,
                    "priority": requirement["priority"],
                    "status": status,
                }
            )

        total = len(required_skills)
        coverage_percent = round(
            covered_count / total * 100,
            2,
        ) if total else 0

        return {
            "project_id": project_id,
            "summary": {
                "total": total,
                "covered": covered_count,
                "gap": gap_count,
                "missing": missing_count,
                "coverage_percent": coverage_percent,
            },
            "skills": skills,
        }
