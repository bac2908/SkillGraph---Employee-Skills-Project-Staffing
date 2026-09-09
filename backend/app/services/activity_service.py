import base64
import binascii
import json
from datetime import datetime
from uuid import UUID

from app.core.audit import audit_time
from app.repositories import activity_repository


class InvalidActivityCursor(ValueError):
    pass


def encode_cursor(item: dict) -> str:
    raw = json.dumps([item["occurred_at"], item["event_id"]]).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def decode_cursor(cursor: str | None) -> tuple[str | None, str | None]:
    if cursor is None:
        return None, None
    try:
        raw = base64.b64decode(
            cursor + "=" * (-len(cursor) % 4), altchars=b"-_", validate=True
        )
        values = json.loads(raw)
        if not isinstance(values, list) or len(values) != 2:
            raise ValueError("Invalid cursor shape")
        timestamp, event_id = values
        parsed = datetime.fromisoformat(timestamp)
        if parsed.tzinfo is None:
            raise ValueError("Cursor requires timezone")
        return audit_time(parsed), str(UUID(event_id))
    except (ValueError, TypeError, AttributeError, binascii.Error) as exc:
        raise InvalidActivityCursor("Invalid activity cursor.") from exc


class ActivityService:
    @staticmethod
    def list(
        project_id: str | None,
        action: str | None,
        resource_type: str | None,
        actor: str | None,
        since: datetime | None,
        until: datetime | None,
        cursor: str | None,
        limit: int,
    ) -> dict:
        cursor_time, cursor_id = decode_cursor(cursor)
        items = activity_repository.list_events(
            {
                "project_id": project_id,
                "action": action,
                "resource_type": resource_type,
                "actor": actor.strip() or None if actor else None,
                "since": audit_time(since) if since else None,
                "until": audit_time(until) if until else None,
                "cursor_time": cursor_time,
                "cursor_id": cursor_id,
                "fetch_limit": limit + 1,
            }
        )
        return {
            "items": items[:limit],
            "next_cursor": encode_cursor(items[limit - 1])
            if len(items) > limit
            else None,
        }
