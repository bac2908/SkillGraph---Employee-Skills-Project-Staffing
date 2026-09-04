from app.repositories import candidate_repository
from app.services.skill_gap_service import SkillGapService


class CandidateRecommendationService:
    def __init__(self) -> None:
        self.skill_gap_service = SkillGapService()

    def recommend(self, project_id: str) -> dict:
        skill_gap_result = self.skill_gap_service.analyze(project_id)
        uncovered_skills = [
            skill
            for skill in skill_gap_result["skills"]
            if skill["status"] in {"GAP", "MISSING"}
        ]

        if not uncovered_skills:
            return self._empty_result(project_id)

        uncovered_skill_map = {
            skill["skill_id"]: skill
            for skill in uncovered_skills
        }
        current_member_ids = candidate_repository.get_project_member_ids(
            project_id
        )
        candidate_skill_rows = (
            candidate_repository.get_available_candidate_skills(
                list(uncovered_skill_map)
            )
        )

        candidates = self._build_eligible_candidates(
            candidate_skill_rows,
            uncovered_skill_map,
            current_member_ids,
        )
        self._attach_collaboration_data(project_id, candidates)
        ranked_candidates = self._rank_candidates(candidates)

        return {
            "project_id": project_id,
            "summary": {
                "uncovered_skill_count": len(uncovered_skills),
                "candidate_count": len(ranked_candidates),
            },
            "uncovered_skills": uncovered_skills,
            "candidates": ranked_candidates,
        }

    @staticmethod
    def _empty_result(project_id: str) -> dict:
        return {
            "project_id": project_id,
            "summary": {
                "uncovered_skill_count": 0,
                "candidate_count": 0,
            },
            "uncovered_skills": [],
            "candidates": [],
        }

    @staticmethod
    def _build_eligible_candidates(
        candidate_skill_rows: list[dict],
        uncovered_skill_map: dict[str, dict],
        current_member_ids: set[str],
    ) -> dict[str, dict]:
        candidates = {}

        for row in candidate_skill_rows:
            if row["employee_id"] in current_member_ids:
                continue

            requirement = uncovered_skill_map[row["skill_id"]]
            if row["level"] < requirement["required_level"]:
                continue

            candidate = candidates.setdefault(
                row["employee_id"],
                {
                    "employee_id": row["employee_id"],
                    "name": row["name"],
                    "email": row["email"],
                    "title": row["title"],
                    "seniority": row["seniority"],
                    "status": row["status"],
                    "location": row["location"],
                    "matched_skills": [],
                    "matched_skill_count": 0,
                    "collaboration_count": 0,
                    "collaborators": [],
                    "shared_projects": [],
                },
            )
            candidate["matched_skills"].append(
                {
                    "skill_id": row["skill_id"],
                    "skill": row["skill"],
                    "level": row["level"],
                    "years_experience": row["years_experience"],
                    "required_level": requirement["required_level"],
                    "priority": requirement["priority"],
                    "gap_status": requirement["status"],
                }
            )

        for candidate in candidates.values():
            candidate["matched_skills"].sort(
                key=lambda skill: skill["skill"]
            )
            candidate["matched_skill_count"] = len(
                candidate["matched_skills"]
            )

        return candidates

    @staticmethod
    def _attach_collaboration_data(
        project_id: str,
        candidates: dict[str, dict],
    ) -> None:
        collaboration_rows = candidate_repository.get_previous_collaborations(
            project_id,
            list(candidates),
        )

        for row in collaboration_rows:
            candidate = candidates[row["employee_id"]]
            candidate["collaboration_count"] = row["collaboration_count"]
            candidate["collaborators"] = sorted(row["collaborators"])
            candidate["shared_projects"] = sorted(row["shared_projects"])

    @staticmethod
    def _rank_candidates(candidates: dict[str, dict]) -> list[dict]:
        ranked_candidates = sorted(
            candidates.values(),
            key=lambda candidate: (
                -candidate["matched_skill_count"],
                -candidate["collaboration_count"],
                -sum(
                    skill["level"]
                    for skill in candidate["matched_skills"]
                ),
                candidate["employee_id"],
            ),
        )

        for rank, candidate in enumerate(ranked_candidates, start=1):
            candidate["rank"] = rank

        return ranked_candidates
