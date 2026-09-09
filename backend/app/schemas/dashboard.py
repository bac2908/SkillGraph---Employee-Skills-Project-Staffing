from datetime import datetime

from pydantic import Field

from app.schemas.common import APIModel
from app.schemas.employee import EmployeeId
from app.schemas.project import ProjectRead


class DashboardSummary(APIModel):
    employee_count: int = Field(ge=0)
    available_employee_count: int = Field(ge=0)
    project_count: int = Field(ge=0)
    active_project_count: int = Field(ge=0)
    skill_count: int = Field(ge=0)


class DashboardCapacity(APIModel):
    employee_id: EmployeeId
    name: str
    title: str
    total_allocation: int = Field(ge=0)
    # Keep negative capacity visible if legacy/direct DB writes exceeded the cap.
    remaining_allocation: int


class DashboardRead(APIModel):
    generated_at: datetime
    summary: DashboardSummary
    capacity: list[DashboardCapacity] = Field(max_length=5)
    default_project: ProjectRead | None
