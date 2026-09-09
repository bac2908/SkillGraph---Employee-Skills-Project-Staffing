"""Additive migration: only AuditEvent constraint/indexes, no business data writes."""

from app.db.graph import graph_db

STATEMENTS = (
    """CREATE CONSTRAINT audit_event_id_unique IF NOT EXISTS
       FOR (event:AuditEvent) REQUIRE event.event_id IS UNIQUE""",
    """CREATE INDEX audit_event_time IF NOT EXISTS
       FOR (event:AuditEvent) ON (event.occurred_at, event.event_id)""",
    """CREATE INDEX audit_event_project_time IF NOT EXISTS
       FOR (event:AuditEvent) ON (event.project_id, event.occurred_at)""",
)


def setup_activity_schema(session) -> None:
    for statement in STATEMENTS:
        session.run(statement).consume()
    constraints = {
        row["name"] for row in session.run("SHOW CONSTRAINTS YIELD name RETURN name")
    }
    indexes = {
        row["name"] for row in session.run("SHOW INDEXES YIELD name RETURN name")
    }
    if "audit_event_id_unique" not in constraints or not {
        "audit_event_time",
        "audit_event_project_time",
    }.issubset(indexes):
        raise RuntimeError("Activity schema was not created.")


def main() -> int:
    try:
        with graph_db.driver.session() as session:
            setup_activity_schema(session)
        print("Activity schema ready. Existing business data was not changed.")
        return 0
    except Exception as exc:
        print(
            f"Activity schema setup failed ({type(exc).__name__}). Check database compatibility and permissions."
        )
        return 1
    finally:
        graph_db.close()


if __name__ == "__main__":
    raise SystemExit(main())
