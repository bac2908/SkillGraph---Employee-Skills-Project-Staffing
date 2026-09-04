from pydantic import BaseModel

from app.schemas.skill_gap import (
    SkillCoverageStatus,
    SkillGapItem,
    SkillPriority,
)


class CandidateRecommendationSummary(BaseModel):
    uncovered_skill_count: int
    candidate_count: int


class MatchedSkill(BaseModel):
    skill_id: str
    skill: str
    level: int
    years_experience: int | float
    required_level: int
    priority: SkillPriority
    gap_status: SkillCoverageStatus


class Candidate(BaseModel):
    employee_id: str
    name: str
    email: str
    title: str
    seniority: str
    status: str
    location: str
    matched_skills: list[MatchedSkill]
    matched_skill_count: int
    collaboration_count: int
    collaborators: list[str]
    shared_projects: list[str]
    rank: int


class CandidateRecommendationResponse(BaseModel):
    project_id: str
    summary: CandidateRecommendationSummary
    uncovered_skills: list[SkillGapItem]
    candidates: list[Candidate]
