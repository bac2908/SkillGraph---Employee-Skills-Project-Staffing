from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import AwareDatetime, Field

from app.schemas.common import APIModel


class ActivityAction(StrEnum):
    CREATED = "CREATED"
    UPDATED = "UPDATED"
    DELETED = "DELETED"


class ActivityKind(StrEnum):
    PROJECT = "PROJECT"
    WORKS_ON = "WORKS_ON"
    REQUIRES_SKILL = "REQUIRES_SKILL"


class ActivityRead(APIModel):
    event_id: UUID
    occurred_at: AwareDatetime
    actor_id: str
    actor_name: str
    project_id: str
    action: ActivityAction
    resource_type: ActivityKind
    resource_id: str
    before: dict[str, Any] | None
    after: dict[str, Any] | None


class ActivityPage(APIModel):
    items: list[ActivityRead] = Field(max_length=100)
    next_cursor: str | None
