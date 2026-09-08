from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, SecretStr, field_validator

Role = Literal["ADMIN", "MANAGER", "VIEWER"]


class AuthModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Login(AuthModel):
    email: EmailStr
    password: SecretStr = Field(min_length=1, max_length=128)


class UserCreate(AuthModel):
    email: EmailStr
    name: str = Field(min_length=1, max_length=100)
    password: SecretStr = Field(min_length=15, max_length=128)
    role: Role = "VIEWER"
    project_ids: list[str] = Field(default_factory=list, max_length=100)

    @field_validator("name")
    @classmethod
    def valid_name(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Name cannot be blank.")
        return value.strip()

    @field_validator("project_ids")
    @classmethod
    def valid_projects(cls, values: list[str]) -> list[str]:
        import re

        if any(not re.fullmatch(r"PROJ[0-9]{3,}", value) for value in values):
            raise ValueError("Invalid project ID.")
        return sorted(set(values))


class UserUpdate(AuthModel):
    role: Role
    is_active: bool
    project_ids: list[str] = Field(default_factory=list, max_length=100)

    _validate_projects = field_validator("project_ids")(
        UserCreate.valid_projects.__func__
    )


class PasswordChange(AuthModel):
    current_password: SecretStr = Field(min_length=1, max_length=128)
    new_password: SecretStr = Field(min_length=15, max_length=128)


class PasswordReset(AuthModel):
    password: SecretStr = Field(min_length=15, max_length=128)


class UserRead(AuthModel):
    user_id: str
    email: str
    name: str
    role: Role
    is_active: bool
    must_change_password: bool
    project_ids: list[str]


class SessionRead(AuthModel):
    user: UserRead
    csrf_token: str
