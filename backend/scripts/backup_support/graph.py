"""Versioned SkillGraph logical export. Never silently drop unsupported data."""

import hashlib
import math
from urllib.parse import urlsplit

from neo4j import READ_ACCESS, GraphDatabase, Query

from scripts.backup_support import BackupError
from scripts.backup_support.files import MAX_FILE_BYTES, json_bytes

NODE_KEYS = {
    "Employee": "employee_id",
    "Skill": "skill_id",
    "Project": "project_id",
    "Team": "team_id",
    "AuditEvent": "event_id",
}
REL_TYPES = {
    "HAS_SKILL": ("Employee", "Skill"),
    "WORKS_ON": ("Employee", "Project"),
    "REQUIRES_SKILL": ("Project", "Skill"),
    "MEMBER_OF": ("Employee", "Team"),
    "OWNED_BY": ("Project", "Team"),
}
MAX_NODES = 100_000
MAX_RELATIONSHIPS = 250_000
NODES_QUERY = "MATCH (n) RETURN id(n) AS ref, labels(n) AS labels, properties(n) AS properties LIMIT $limit"
RELS_QUERY = "MATCH (a)-[r]->(b) RETURN id(a) AS start, id(b) AS end, type(r) AS type, properties(r) AS properties LIMIT $limit"


def endpoint_fingerprint(uri: str) -> str:
    parsed = urlsplit(uri)
    if (
        parsed.scheme
        not in {"bolt", "bolt+s", "bolt+ssc", "neo4j", "neo4j+s", "neo4j+ssc"}
        or not parsed.hostname
    ):
        raise BackupError("Invalid graph connection URI.")
    if (
        parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or parsed.path not in {"", "/"}
    ):
        raise BackupError(
            "URI must not contain embedded credentials, paths or query parameters."
        )
    address = f"{parsed.hostname.lower().rstrip('.')}:{parsed.port or 7687}"
    return hashlib.sha256(address.encode()).hexdigest()


def make_driver(uri, user, password):
    endpoint_fingerprint(uri)
    if not user or not password:
        raise BackupError(
            "Graph credentials are missing; fill the local environment file."
        )
    return GraphDatabase.driver(
        uri,
        auth=(user, password),
        connection_timeout=3,
        connection_acquisition_timeout=5,
        max_transaction_retry_time=0,
        max_connection_pool_size=1,
    )


def validate_properties(properties):
    if not isinstance(properties, dict) or any(
        not isinstance(key, str) for key in properties
    ):
        raise BackupError("Unsupported graph property map.")

    def scalar(value):
        return (
            isinstance(value, (str, bool))
            or (type(value) is int and -(2**63) <= value < 2**63)
            or (type(value) is float and math.isfinite(value))
        )

    for value in properties.values():
        if not scalar(value) and not (
            isinstance(value, list) and all(scalar(item) for item in value)
        ):
            raise BackupError(
                "Unsupported property type; use native engine backup for this data."
            )


def validate_graph(data):
    if not isinstance(data, dict) or set(data) != {"nodes", "relationships"}:
        raise BackupError("Invalid graph archive structure.")
    nodes, relationships = data["nodes"], data["relationships"]
    if (
        not isinstance(nodes, list)
        or not isinstance(relationships, list)
        or len(nodes) > MAX_NODES
        or len(relationships) > MAX_RELATIONSHIPS
    ):
        raise BackupError("Graph archive exceeds supported record limits.")
    refs, keys = {}, set()
    for node in nodes:
        if not isinstance(node, dict) or set(node) != {"ref", "labels", "properties"}:
            raise BackupError("Invalid graph node structure.")
        if not isinstance(node["ref"], str) or node["ref"] in refs:
            raise BackupError("Duplicate or invalid node reference.")
        labels = node["labels"]
        if (
            not isinstance(labels, list)
            or len(labels) != 1
            or labels[0] not in NODE_KEYS
        ):
            raise BackupError(
                "Unsupported graph labels; no data was silently excluded."
            )
        label = labels[0]
        props = node["properties"]
        validate_properties(props)
        identity = props.get(NODE_KEYS[label])
        if not isinstance(identity, str) or not identity:
            raise BackupError("Node is missing its stable SkillGraph identifier.")
        if (label, identity) in keys:
            raise BackupError("Duplicate stable identifier in graph.")
        keys.add((label, identity))
        refs[node["ref"]] = (label, identity)
    for rel in relationships:
        if not isinstance(rel, dict) or set(rel) != {
            "start",
            "end",
            "type",
            "properties",
        }:
            raise BackupError("Invalid graph relationship structure.")
        if not all(isinstance(rel[key], str) for key in ("start", "end", "type")):
            raise BackupError("Invalid graph relationship reference.")
        if (
            rel["start"] not in refs
            or rel["end"] not in refs
            or rel["type"] not in REL_TYPES
        ):
            raise BackupError("Dangling or unsupported graph relationship.")
        if (refs[rel["start"]][0], refs[rel["end"]][0]) != REL_TYPES[rel["type"]]:
            raise BackupError(
                "Relationship endpoints do not match the SkillGraph schema."
            )
        validate_properties(rel["properties"])
    return refs


def export_graph(driver):
    data = {"nodes": [], "relationships": []}
    byte_count = 0
    with (
        driver.session(default_access_mode=READ_ACCESS) as session,
        session.begin_transaction(timeout=30) as tx,
    ):
        for field, query, maximum in (
            ("nodes", NODES_QUERY, MAX_NODES),
            ("relationships", RELS_QUERY, MAX_RELATIONSHIPS),
        ):
            for record in tx.run(query, limit=maximum + 1):
                item = record.data()
                for key in ("ref",) if field == "nodes" else ("start", "end"):
                    item[key] = str(item[key])
                byte_count += len(json_bytes(item)) + 1
                if byte_count > MAX_FILE_BYTES - 1024 or len(data[field]) >= maximum:
                    raise BackupError("Graph exceeds the bounded local export limits.")
                data[field].append(item)
    validate_graph(data)
    return data


def graph_summary(data):
    refs = validate_graph(data)
    canonical = {
        "nodes": sorted(
            [[*refs[node["ref"]], node["properties"]] for node in data["nodes"]],
            key=json_bytes,
        ),
        "relationships": sorted(
            [
                [*refs[rel["start"]], rel["type"], *refs[rel["end"]], rel["properties"]]
                for rel in data["relationships"]
            ],
            key=json_bytes,
        ),
    }
    return {
        "nodes": len(data["nodes"]),
        "relationships": len(data["relationships"]),
        "logical_sha256": hashlib.sha256(json_bytes(canonical)).hexdigest(),
    }


def require_empty(session):
    result = session.run(
        Query("MATCH (n) RETURN count(n) AS total", timeout=10)
    ).single()
    if result is None or result["total"] != 0:
        raise BackupError(
            "Restore target is not empty. Nothing will be overwritten or cleared."
        )


def restore_graph(driver, data):
    from scripts.setup_activity_schema import setup_activity_schema
    from scripts.setup_schema import CONSTRAINTS

    refs = validate_graph(data)
    with driver.session() as session:
        require_empty(session)
        # Only application-owned, fixed DDL; never execute DDL from an archive.
        for statement in CONSTRAINTS.values():
            session.run(statement).consume()
        setup_activity_schema(session)
        with session.begin_transaction(timeout=60) as tx:
            if tx.run("MATCH (n) RETURN count(n) AS total").single()["total"] != 0:
                raise BackupError("Restore target changed before import; aborting.")
            for label in NODE_KEYS:
                rows = [
                    node["properties"]
                    for node in data["nodes"]
                    if node["labels"] == [label]
                ]
                if rows:
                    count = tx.run(
                        f"UNWIND $rows AS props CREATE (n:{label}) SET n = props RETURN count(n) AS total",
                        rows=rows,
                    ).single()["total"]
                    if count != len(rows):
                        raise BackupError(
                            "Graph node import count mismatch; rolling back."
                        )
            for kind, (start_label, end_label) in REL_TYPES.items():
                rows = [
                    {
                        "start": refs[rel["start"]][1],
                        "end": refs[rel["end"]][1],
                        "properties": rel["properties"],
                    }
                    for rel in data["relationships"]
                    if rel["type"] == kind
                ]
                if rows:
                    query = (
                        f"UNWIND $rows AS row MATCH (a:{start_label} {{{NODE_KEYS[start_label]}: row.start}}) "
                        f"MATCH (b:{end_label} {{{NODE_KEYS[end_label]}: row.end}}) "
                        f"CREATE (a)-[r:{kind}]->(b) SET r = row.properties RETURN count(r) AS total"
                    )
                    if tx.run(query, rows=rows).single()["total"] != len(rows):
                        raise BackupError(
                            "Graph relationship import count mismatch; rolling back."
                        )
    # Deliberately after COMMIT: the configured engine's in-transaction readback
    # of newly created relationships is not assumed to be supported.
    if graph_summary(export_graph(driver)) != graph_summary(data):
        raise BackupError(
            "Post-commit graph verification failed. Leave test target isolated; do not switch the app."
        )
