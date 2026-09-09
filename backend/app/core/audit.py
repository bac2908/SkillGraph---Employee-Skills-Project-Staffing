"""Explicit actor propagation; never infer identity from client payloads/globals."""

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4


def audit_time(value: datetime) -> str:
    return value.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


@dataclass(frozen=True, slots=True)
class AuditActor:
    user_id: str
    name: str

    @classmethod
    def from_user(cls, user: dict) -> "AuditActor":
        return cls(user_id=user["user_id"], name=user["name"])


@dataclass(frozen=True, slots=True)
class AuditContext:
    event_id: str
    occurred_at: str
    actor: AuditActor

    @classmethod
    def create(cls, actor: AuditActor) -> "AuditContext":
        # Allocate once outside a retryable transaction callback.
        if not actor.user_id or not actor.name:
            raise ValueError("An authenticated audit actor is required.")
        return cls(str(uuid4()), audit_time(datetime.now(UTC)), actor)
