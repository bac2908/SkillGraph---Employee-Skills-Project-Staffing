from enum import StrEnum
from typing import Annotated

from pydantic import EmailStr, Field, StringConstraints, field_validator

from app.schemas.common import APIModel, PartialUpdateModel

EmployeeId = Annotated[
    str,
    StringConstraints(pattern=r"^EMP[0-9]{3,}$"),
]
EmployeeName = Annotated[str, StringConstraints(min_length=1, max_length=100)]
ShortText = Annotated[str, StringConstraints(min_length=1, max_length=100)]


class EmployeeStatus(StrEnum):
    AVAILABLE = "AVAILABLE"
    ASSIGNED = "ASSIGNED"
    UNAVAILABLE = "UNAVAILABLE"
    ON_LEAVE = "ON_LEAVE"


class EmployeeSeniority(StrEnum):
    INTERN = "Intern"
    JUNIOR = "Junior"
    MIDDLE = "Middle"
    SENIOR = "Senior"
    LEAD = "Lead"
    PRINCIPAL = "Principal"


class EmployeeFields(APIModel):
    name: EmployeeName = Field(examples=["Nguyen Van Bac"])
    email: EmailStr = Field(examples=["bac@example.com"])
    title: ShortText = Field(examples=["Backend Developer"])
    seniority: EmployeeSeniority = EmployeeSeniority.JUNIOR
    status: EmployeeStatus = EmployeeStatus.AVAILABLE
    location: ShortText = Field(examples=["Ho Chi Minh City"])

    @field_validator("email", mode="after")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        return str(value).lower()


class EmployeeCreate(EmployeeFields):
    employee_id: EmployeeId = Field(examples=["EMP009"])


class EmployeeUpdate(PartialUpdateModel):
    name: EmployeeName | None = None
    email: EmailStr | None = None
    title: ShortText | None = None
    seniority: EmployeeSeniority | None = None
    status: EmployeeStatus | None = None
    location: ShortText | None = None

    @field_validator("email", mode="after")
    @classmethod
    def normalize_email(cls, value: EmailStr | None) -> str | None:
        return str(value).lower() if value is not None else None


class EmployeeRead(EmployeeFields):
    employee_id: EmployeeId
