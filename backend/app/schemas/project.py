from enum import StrEnum
from typing import Annotated

from pydantic import Field, StringConstraints

from app.schemas.common import APIModel, PartialUpdateModel

ProjectId = Annotated[
    str,
    StringConstraints(pattern=r"^PROJ[0-9]{3,}$"),
]
ProjectName = Annotated[str, StringConstraints(min_length=1, max_length=150)]
ProjectDescription = Annotated[
    str,
    StringConstraints(min_length=1, max_length=2000),
]


class ProjectStatus(StrEnum):
    PLANNING = "PLANNING"
    ACTIVE = "ACTIVE"
    ON_HOLD = "ON_HOLD"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class ProjectFields(APIModel):
    name: ProjectName = Field(examples=["E-commerce Platform"])
    description: ProjectDescription
    status: ProjectStatus = ProjectStatus.PLANNING


class ProjectCreate(ProjectFields):
    project_id: ProjectId = Field(examples=["PROJ004"])


class ProjectUpdate(PartialUpdateModel):
    name: ProjectName | None = None
    description: ProjectDescription | None = None
    status: ProjectStatus | None = None


class ProjectRead(ProjectFields):
    project_id: ProjectId
