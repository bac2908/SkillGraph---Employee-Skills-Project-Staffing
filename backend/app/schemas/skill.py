from typing import Annotated

from pydantic import Field, StringConstraints

from app.schemas.common import APIModel, PartialUpdateModel

SkillId = Annotated[
    str,
    StringConstraints(pattern=r"^SK[0-9]{3,}$"),
]
SkillName = Annotated[str, StringConstraints(min_length=1, max_length=100)]
SkillCategory = Annotated[
    str,
    StringConstraints(min_length=1, max_length=100),
]


class SkillFields(APIModel):
    name: SkillName = Field(examples=["Python"])
    category: SkillCategory = Field(examples=["Backend"])


class SkillCreate(SkillFields):
    skill_id: SkillId = Field(examples=["SK013"])


class SkillUpdate(PartialUpdateModel):
    name: SkillName | None = None
    category: SkillCategory | None = None


class SkillRead(SkillFields):
    skill_id: SkillId
