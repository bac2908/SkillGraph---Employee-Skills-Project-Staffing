from typing import Annotated

from pydantic import Field, StringConstraints

from app.schemas.common import APIModel
from app.schemas.employee import EmployeeId
from app.schemas.project import ProjectId
from app.schemas.skill import SkillId
from app.schemas.skill_gap import SkillPriority

SkillLevel = Annotated[int, Field(ge=1, le=5)]
YearsExperience = Annotated[float, Field(ge=0, le=80)]
AllocationPercent = Annotated[int, Field(ge=1, le=100)]
AssignmentRole = Annotated[
    str,
    StringConstraints(min_length=1, max_length=100),
]


class EmployeeSkillWrite(APIModel):
    level: SkillLevel = Field(examples=[4])
    years_experience: YearsExperience = Field(examples=[2])


class EmployeeSkillRead(EmployeeSkillWrite):
    employee_id: EmployeeId
    employee_name: str
    skill_id: SkillId
    skill_name: str
    category: str


class EmployeeSkillList(APIModel):
    items: list[EmployeeSkillRead]
    total: int


class ProjectAssignmentWrite(APIModel):
    role: AssignmentRole = Field(examples=["Backend Developer"])
    allocation: AllocationPercent = Field(
        description="Percentage of the employee's capacity assigned here.",
        examples=[80],
    )


class ProjectAssignmentRead(ProjectAssignmentWrite):
    project_id: ProjectId
    project_name: str
    employee_id: EmployeeId
    employee_name: str
    employee_total_allocation: int
    employee_remaining_allocation: int


class ProjectAssignmentList(APIModel):
    items: list[ProjectAssignmentRead]
    total: int


class ProjectRequirementWrite(APIModel):
    min_level: SkillLevel = Field(examples=[3])
    priority: SkillPriority = Field(examples=["MUST"])


class ProjectRequirementRead(ProjectRequirementWrite):
    project_id: ProjectId
    project_name: str
    skill_id: SkillId
    skill_name: str
    category: str


class ProjectRequirementList(APIModel):
    items: list[ProjectRequirementRead]
    total: int
