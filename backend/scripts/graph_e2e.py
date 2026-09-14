"""Opt-in real graph acceptance. No source writes or automatic graph cleanup."""

import argparse
import json
import os
import re
import secrets
import sqlite3
import subprocess
import sys
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path

from dotenv import dotenv_values
from neo4j import Query

from scripts.backup_support.files import private_directory, write_json
from scripts.backup_support.graph import (
    endpoint_fingerprint,
    export_graph,
    graph_summary,
    make_driver,
)

BACKEND = Path(__file__).resolve().parents[1]
RUNS = BACKEND / "e2e-runs"
KEYS = ("COGNODB_URI", "COGNODB_USER", "COGNODB_PASSWORD")
CONSTRAINTS = {
    "employee_employee_id_unique",
    "employee_email_unique",
    "skill_skill_id_unique",
    "skill_name_unique",
    "project_project_id_unique",
    "team_team_id_unique",
    "audit_event_id_unique",
}
INDEXES = {"audit_event_time", "audit_event_project_time"}


class SafetyError(RuntimeError):
    pass


def load_target(path):
    source_path = (BACKEND / ".env").resolve()
    if path.resolve() == source_path or not path.is_file():
        raise SafetyError("A separate local .env.e2e file is required.")
    values = dotenv_values(path, interpolate=False)
    if not all(values.get(key) for key in KEYS):
        raise SafetyError("Fill all three test graph connection fields locally.")
    target = {key: values[key] for key in KEYS}
    identity = endpoint_fingerprint(target["COGNODB_URI"])
    # Check BOTH file and environment sources, even if one overrides the other.
    sources = [
        dotenv_values(source_path, interpolate=False).get("COGNODB_URI"),
        os.environ.get("COGNODB_URI"),
    ]
    if not any(sources):
        raise SafetyError(
            "Cannot identify the live endpoint for the safety comparison."
        )
    if any(endpoint_fingerprint(uri) == identity for uri in sources if uri):
        raise SafetyError("Test target matches a live endpoint; refusing access.")
    return target, identity


def inspect_target(driver):
    with driver.session() as session:
        total = session.run(
            Query("MATCH (n) RETURN count(n) AS total", timeout=10)
        ).single()["total"]
        constraints = {
            row["name"]
            for row in session.run(
                Query("SHOW CONSTRAINTS YIELD name RETURN name", timeout=10)
            )
        }
        indexes = {
            row["name"]
            for row in session.run(
                Query("SHOW INDEXES YIELD name RETURN name", timeout=10)
            )
        }
    return {
        "empty": total == 0,
        "schema_ready": CONSTRAINTS <= constraints and INDEXES <= indexes,
    }


def plan(run_id):
    if not re.fullmatch(r"[0-9]{18}", run_id):
        raise SafetyError("Invalid run ID.")
    return {
        "Employee": {
            f"EMP{run_id}{i:02}": name
            for i, name in enumerate(
                [
                    "Member",
                    "Both",
                    "Collaborator",
                    "Higher",
                    "Tie",
                    "Unavailable",
                    "Low",
                    "Race",
                ],
                1,
            )
        },
        "Skill": {
            f"SK{run_id}{i:02}": name
            for i, name in enumerate(["Covered", "Gap", "Missing"], 1)
        },
        "Project": {
            f"PROJ{run_id}{i:02}": name
            for i, name in enumerate(["Main", "Shared", "Race A", "Race B"], 1)
        },
    }


def run_directory(run_id):
    plan(run_id)
    directory = RUNS / run_id
    if directory.resolve().parent != RUNS.resolve() or directory.is_symlink():
        raise SafetyError("Run directory must remain directly inside e2e-runs.")
    return directory


def owned_nodes(graph, run_id, actor_ids):
    """Fail closed on ANY foreign data; do not detach an unowned neighbour."""
    if len(graph["nodes"]) > 500 or len(graph["relationships"]) > 500:
        raise SafetyError("Unexpected graph size; manual review required.")
    expected = plan(run_id)
    prefix = f"E2E {run_id} "
    keys = {
        "Employee": "employee_id",
        "Skill": "skill_id",
        "Project": "project_id",
        "AuditEvent": "event_id",
    }
    owned = []
    for node in graph["nodes"]:
        labels, props = node["labels"], node["properties"]
        if len(labels) != 1 or labels[0] not in keys:
            raise SafetyError("Foreign graph node detected; cleanup refused.")
        label = labels[0]
        identity = props.get(keys[label])
        if label == "AuditEvent":
            valid = (
                props.get("project_id") in expected["Project"]
                and props.get("actor_id") in actor_ids
                and props.get("actor_name", "").startswith(prefix)
            )
        else:
            name = expected[label].get(identity)
            valid = name is not None and props.get("name") == prefix + name
        if not valid or not identity:
            raise SafetyError(
                "Graph data does not belong to this run; cleanup refused."
            )
        owned.append((label, keys[label], identity, props))
    return owned


def actor_ids_at(directory):
    path = directory / "auth.sqlite3"
    if path.is_symlink() or path.resolve().parent != directory.resolve():
        raise SafetyError(
            "Run auth path must not point outside its evidence directory."
        )
    with closing(sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)) as db:
        return {row[0] for row in db.execute("SELECT user_id FROM users")}


def expected_relationships(run_id):
    def identity(prefix, index):
        return f"{prefix}{run_id}{index:02}"

    expected = {}
    for employee, capability, level in [
        (1, 1, 4),
        (1, 2, 2),
        (2, 2, 4),
        (2, 3, 3),
        (3, 2, 3),
        (4, 2, 5),
        (5, 2, 5),
        (6, 2, 5),
        (6, 3, 5),
        (7, 2, 2),
        (7, 3, 1),
    ]:
        expected[
            (identity("EMP", employee), "HAS_SKILL", identity("SK", capability))
        ] = {
            "level": level,
            "years_experience": 2.5,
        }
    for capability, priority in enumerate(["MUST", "SHOULD", "NICE"], 1):
        expected[
            (identity("PROJ", 1), "REQUIRES_SKILL", identity("SK", capability))
        ] = {
            "min_level": 3,
            "priority": priority,
        }
    for employee, project, allocation in [
        (1, 1, 70),
        (1, 2, 30),
        (2, 2, 80),
        (3, 2, 5),
    ]:
        expected[(identity("EMP", employee), "WORKS_ON", identity("PROJ", project))] = {
            "role": "E2E Engineer",
            "allocation": allocation,
        }
    return expected


def verify_persistence(graph, run_id, actors):
    owned_nodes(graph, run_id, actors)
    expected = plan(run_id)
    for label, key in [
        ("Employee", "employee_id"),
        ("Skill", "skill_id"),
        ("Project", "project_id"),
    ]:
        actual = {
            n["properties"][key] for n in graph["nodes"] if n["labels"] == [label]
        }
        if actual != set(expected[label]):
            raise SafetyError("Persisted catalogue does not match the full scenario.")
    refs = {n["ref"]: n for n in graph["nodes"]}

    def business_id(ref):
        node = refs[ref]
        key = {
            "Employee": "employee_id",
            "Skill": "skill_id",
            "Project": "project_id",
        }.get(node["labels"][0])
        if key is None:
            raise SafetyError("Unexpected relationship endpoint.")
        return node["properties"][key]

    actual_relationships = {
        (business_id(r["start"]), r["type"], business_id(r["end"])): r["properties"]
        for r in graph["relationships"]
    }
    if len(actual_relationships) != len(
        graph["relationships"]
    ) or actual_relationships != expected_relationships(run_id):
        raise SafetyError(
            "Persisted relationships/properties differ from the expected final state."
        )
    types = {r["type"] for r in graph["relationships"]}
    if types != {"HAS_SKILL", "WORKS_ON", "REQUIRES_SKILL"}:
        raise SafetyError("Expected relationship types were not persisted.")
    totals = {}
    for rel in graph["relationships"]:
        if rel["type"] == "WORKS_ON":
            employee = refs[rel["start"]]["properties"]["employee_id"]
            allocation = rel["properties"].get("allocation")
            if type(allocation) is not int or not 1 <= allocation <= 100:
                raise SafetyError("Invalid persisted allocation.")
            totals[employee] = totals.get(employee, 0) + allocation
    if any(value > 100 for value in totals.values()):
        raise SafetyError("Persisted allocation exceeds 100%.")
    if not any(n["labels"] == ["AuditEvent"] for n in graph["nodes"]):
        raise SafetyError("No audit events persisted.")
    return graph_summary(graph)


def execute_run(target, identity, args):
    if not args.confirm_empty_test_target or not args.exclusive_test_target:
        raise SafetyError(
            "Confirm an empty disposable test instance and exclusive access first."
        )
    with make_driver(*(target[key] for key in KEYS)) as driver:
        before = inspect_target(driver)
        if not before["empty"]:
            raise SafetyError(
                "Target must be empty; existing data will not be removed."
            )
        if not before["schema_ready"] and not args.initialize_schema:
            raise SafetyError(
                "Test schema is missing; review --initialize-schema for this target only."
            )
    run_id = (
        datetime.now(UTC).strftime("%y%m%d%H%M%S")
        + f"{secrets.randbelow(1_000_000):06}"
    )
    directory = private_directory(run_directory(run_id))
    manifest = {
        "run_id": run_id,
        "target_endpoint_sha256": identity,
        "plan": plan(run_id),
    }
    write_json(directory / "manifest.json", manifest)
    env = {
        **os.environ,
        **target,
        "AUTH_DB_PATH": str(directory / "auth.sqlite3"),
        "AUTH_COOKIE_SECURE": "false",
        "AUTH_ALLOWED_ORIGINS": '["http://127.0.0.1:5175"]',
        "SKILLGRAPH_E2E_RUN": run_id,
        "SKILLGRAPH_E2E_APPROVED": identity,
        "SKILLGRAPH_E2E_PASSWORD": secrets.token_urlsafe(32),
    }
    print(
        f"Test run: {run_id}. Only synthetic data; retained until explicit cleanup.",
        flush=True,
    )
    report = {
        "run_id": run_id,
        "status": "failed_or_interrupted",
        "cleanup": "not_requested",
    }
    try:
        if args.initialize_schema:
            completed = subprocess.run(
                [sys.executable, "-B", "-m", "scripts.setup_schema"],
                cwd=BACKEND,
                env=env,
                check=False,
            )
            if completed.returncode:
                raise SafetyError(
                    "Test schema setup failed; inspect the dedicated instance."
                )
        with make_driver(*(target[key] for key in KEYS)) as driver:
            if inspect_target(driver) != {"empty": True, "schema_ready": True}:
                raise SafetyError(
                    "Target changed or schema is incomplete before launch."
                )
        frontend = BACKEND.parent / "frontend"
        completed = subprocess.run(
            [
                "node",
                "node_modules/@playwright/test/cli.js",
                "test",
                "--config",
                "playwright.graph.config.ts",
            ],
            cwd=frontend,
            env=env,
            check=False,
        )
        report["playwright_exit_code"] = completed.returncode
        if completed.returncode:
            raise SafetyError(
                "Browser acceptance failed; test data retained for investigation."
            )
        # Fresh driver after the app/test processes exit: evidence is not FE cache.
        with make_driver(*(target[key] for key in KEYS)) as driver:
            snapshot = export_graph(driver)
        report["graph"] = verify_persistence(snapshot, run_id, actor_ids_at(directory))
        write_json(directory / "graph-after.json", snapshot)
        report["status"] = "passed_data_retained"
        return report
    finally:
        report["finished_at"] = datetime.now(UTC).isoformat()
        write_json(directory / "report.json", report)


def cleanup(target, identity, args):
    if not args.confirm_cleanup or not args.exclusive_test_target:
        raise SafetyError(
            "Cleanup requires explicit approval and exclusive test target access."
        )
    directory = run_directory(args.run_id)
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    if (
        manifest.get("run_id") != args.run_id
        or manifest.get("target_endpoint_sha256") != identity
    ):
        raise SafetyError("Run manifest and target do not match.")
    marker = directory / "cleanup-report.json"
    if marker.exists():
        raise SafetyError("This run already has a cleanup report; review it first.")
    actors = actor_ids_at(directory)
    with make_driver(*(target[key] for key in KEYS)) as driver:
        graph = export_graph(driver)
        owned = owned_nodes(graph, args.run_id, actors)

        def remove(transaction):
            # Re-read inside the write transaction; abort on a new/foreign node.
            current = list(
                transaction.run(
                    Query(
                        "MATCH (n) RETURN labels(n) AS labels, properties(n) AS properties LIMIT 501",
                        timeout=10,
                    )
                )
            )
            checked = owned_nodes(
                {"nodes": [dict(row) for row in current], "relationships": []},
                args.run_id,
                actors,
            )
            if checked != owned:
                # Query order may vary. Compare full properties rather than order.
                def normalize(rows):
                    return sorted(json.dumps(row, sort_keys=True) for row in rows)

                if normalize(checked) != normalize(owned):
                    raise SafetyError(
                        "Graph changed during cleanup; no deletion committed."
                    )
            for label, key, value, props in checked:
                # Label/key are from the fixed allowlist, never user-provided Cypher.
                result = transaction.run(
                    Query(
                        f"MATCH (n:{label} {{{key}: $value}}) WHERE properties(n) = $props DETACH DELETE n RETURN count(*) AS removed",
                        timeout=10,
                    ),
                    value=value,
                    props=props,
                ).single()
                if result is None or result["removed"] != 1:
                    raise SafetyError("Cleanup target changed; rolling back.")

        with driver.session() as session:
            session.execute_write(remove)
        if not inspect_target(driver)["empty"]:
            raise SafetyError(
                "Graph is not empty after cleanup; manual review required."
            )
    result = {
        "run_id": args.run_id,
        "status": "test_graph_cleaned",
        "removed_nodes": len(owned),
        "schema": "retained",
        "local_evidence": "retained",
    }
    write_json(marker, result)
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["preflight", "run", "cleanup"])
    parser.add_argument("--target-env", type=Path, default=BACKEND / ".env.e2e")
    parser.add_argument("--confirm-empty-test-target", action="store_true")
    parser.add_argument("--exclusive-test-target", action="store_true")
    parser.add_argument("--initialize-schema", action="store_true")
    parser.add_argument("--run-id")
    parser.add_argument("--confirm-cleanup", action="store_true")
    args = parser.parse_args(argv)
    try:
        target, identity = load_target(args.target_env)
        if args.command == "run":
            result = execute_run(target, identity, args)
        elif args.command == "cleanup":
            result = cleanup(target, identity, args)
        else:
            with make_driver(*(target[key] for key in KEYS)) as driver:
                result = inspect_target(driver)
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except SafetyError as exc:
        print(str(exc))
        return 1
    except Exception as exc:
        # Never print connection errors, URIs, passwords or a traceback.
        print(
            f"Graph E2E stopped ({type(exc).__name__}); review local test configuration/evidence."
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
