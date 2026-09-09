import json

from neo4j import Transaction

from app.core.audit import AuditContext
from app.db.graph import graph_db
from app.repositories.errors import RepositoryError

# Explicit allowlists exclude passwords, email, tokens and unrelated node fields.
SNAPSHOT_FIELDS = {
    "PROJECT": ("project_id", "name", "description", "status"),
    "WORKS_ON": ("project_id", "employee_id", "role", "allocation"),
    "REQUIRES_SKILL": ("project_id", "skill_id", "min_level", "priority"),
}

WRITE_EVENT_QUERY = """
CREATE (event:AuditEvent)
SET event = $properties
RETURN event.event_id AS event_id
"""

LIST_EVENTS_QUERY = """
MATCH (event:AuditEvent)
WHERE ($project_id IS NULL OR event.project_id = $project_id)
  AND ($action IS NULL OR event.action = $action)
  AND ($resource_type IS NULL OR event.resource_type = $resource_type)
  AND ($actor IS NULL OR toLower(event.actor_name) CONTAINS toLower($actor)
       OR event.actor_id = $actor)
  AND ($since IS NULL OR event.occurred_at >= $since)
  AND ($until IS NULL OR event.occurred_at <= $until)
  AND ($cursor_time IS NULL OR event.occurred_at < $cursor_time
       OR (event.occurred_at = $cursor_time AND event.event_id < $cursor_id))
RETURN event.event_id AS event_id, event.occurred_at AS occurred_at,
       event.actor_id AS actor_id, event.actor_name AS actor_name,
       event.project_id AS project_id, event.action AS action,
       event.resource_type AS resource_type, event.resource_id AS resource_id,
       event.before_json AS before_json, event.after_json AS after_json
ORDER BY event.occurred_at DESC, event.event_id DESC
LIMIT $fetch_limit
"""


class ActivityRepositoryError(RepositoryError):
    pass


def snapshot(kind: str, value: dict | None) -> dict | None:
    if value is None:
        return None
    return {key: value[key] for key in SNAPSHOT_FIELDS[kind] if key in value}


def write_event(
    transaction: Transaction,
    context: AuditContext,
    project_id: str,
    resource_type: str,
    resource_id: str,
    before: dict | None,
    after: dict | None,
) -> None:
    before = snapshot(resource_type, before)
    after = snapshot(resource_type, after)
    if before == after:
        return  # A no-op PUT/PATCH is not a data change.
    properties = {
        "event_id": context.event_id,
        "occurred_at": context.occurred_at,
        "actor_id": context.actor.user_id,
        "actor_name": context.actor.name,
        "project_id": project_id,
        "resource_type": resource_type,
        "resource_id": resource_id,
        "action": "CREATED"
        if before is None
        else "DELETED"
        if after is None
        else "UPDATED",
        "before_json": json.dumps(before, ensure_ascii=False, sort_keys=True),
        "after_json": json.dumps(after, ensure_ascii=False, sort_keys=True),
    }
    # Called INSIDE the business transaction. Never swallow failures here.
    record = transaction.run(WRITE_EVENT_QUERY, properties=properties).single()
    if record is None or record["event_id"] != context.event_id:
        raise ActivityRepositoryError("Activity record was not saved.")


def list_events(parameters: dict) -> list[dict]:
    def read(transaction):
        events = []
        for record in transaction.run(LIST_EVENTS_QUERY, **parameters):
            item = record.data()
            kind = item["resource_type"]
            # Apply the allowlist again on read, including legacy/imported data.
            item["before"] = snapshot(kind, json.loads(item.pop("before_json")))
            item["after"] = snapshot(kind, json.loads(item.pop("after_json")))
            events.append(item)
        return events

    try:
        with graph_db.driver.session() as session:
            return session.execute_read(read)
    except Exception as exc:
        raise ActivityRepositoryError("Unable to read project activity.") from exc
