from typing import Literal

from pydantic import BaseModel

SkillPriority = Literal["MUST", "SHOULD", "NICE"]
SkillCoverageStatus = Literal["COVERED", "GAP", "MISSING"]


class SkillGapSummary(BaseModel):
    total: int
    covered: int
    gap: int
    missing: int
    coverage_percent: float


class SkillGapItem(BaseModel):
    skill_id: str
    skill: str
    required_level: int
    best_team_level: int
    employee_count: int
    priority: SkillPriority
    status: SkillCoverageStatus


class SkillGapResponse(BaseModel):
    project_id: str
    summary: SkillGapSummary
    skills: list[SkillGapItem]
