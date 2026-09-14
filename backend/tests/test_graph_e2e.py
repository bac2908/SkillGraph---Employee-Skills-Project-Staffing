"""Offline safety tests. Never connect to a configured graph or real auth DB."""

import argparse
import json
from copy import deepcopy
from unittest.mock import MagicMock

import pytest

from scripts import graph_e2e as e2e
from scripts.backup_support import BackupError

RUN = "260914120000123456"
ACTOR = "synthetic-admin-id"


@pytest.fixture
def environments(tmp_path, monkeypatch):
    source = tmp_path / ".env"
    source.write_text("COGNODB_URI=bolt://live.example:7687\n", encoding="utf-8")
    target = tmp_path / ".env.e2e"
    target.write_text(
        "COGNODB_URI=bolt://test.example:7687\nCOGNODB_USER=test\nCOGNODB_PASSWORD=synthetic-secret\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(e2e, "BACKEND", tmp_path)
    monkeypatch.setattr(e2e, "RUNS", tmp_path / "e2e-runs")
    monkeypatch.delenv("COGNODB_URI", raising=False)
    return source, target


def snapshot():
    nodes = []
    for label, items in e2e.plan(RUN).items():
        key = {"Employee": "employee_id", "Skill": "skill_id", "Project": "project_id"}[
            label
        ]
        nodes += [
            {
                "ref": identity,
                "labels": [label],
                "properties": {key: identity, "name": f"E2E {RUN} {name}"},
            }
            for identity, name in items.items()
        ]
    nodes.append(
        {
            "ref": "audit",
            "labels": ["AuditEvent"],
            "properties": {
                "event_id": "synthetic-event",
                "project_id": f"PROJ{RUN}01",
                "actor_id": ACTOR,
                "actor_name": f"E2E {RUN} Admin",
            },
        }
    )
    return {
        "nodes": nodes,
        "relationships": [
            {"start": start, "type": kind, "end": end, "properties": props}
            for (start, kind, end), props in e2e.expected_relationships(RUN).items()
        ],
    }


def args(**values):
    return argparse.Namespace(
        confirm_empty_test_target=False,
        exclusive_test_target=False,
        initialize_schema=False,
        confirm_cleanup=False,
        run_id=RUN,
        **values,
    )


def test_loads_only_dedicated_graph_fields(environments):
    _, target = environments
    config, identity = e2e.load_target(target)
    assert set(config) == set(e2e.KEYS)
    assert len(identity) == 64


@pytest.mark.parametrize(
    "uri",
    [
        "bolt://live.example",
        "neo4j+s://LIVE.EXAMPLE.:7687/",
        "bolt+ssc://live.example:7687",
    ],
)
def test_same_live_endpoint_is_rejected(environments, uri):
    _, target = environments
    target.write_text(
        f"COGNODB_URI={uri}\nCOGNODB_USER=test\nCOGNODB_PASSWORD=test\n",
        encoding="utf-8",
    )
    with pytest.raises(e2e.SafetyError, match="live endpoint"):
        e2e.load_target(target)


def test_environment_live_endpoint_is_also_protected(environments, monkeypatch):
    _, target = environments
    monkeypatch.setenv("COGNODB_URI", "neo4j+s://test.example")
    with pytest.raises(e2e.SafetyError, match="live endpoint"):
        e2e.load_target(target)


@pytest.mark.parametrize("field", e2e.KEYS)
def test_missing_connection_field_rejected(environments, field):
    _, target = environments
    lines = [
        line
        for line in target.read_text().splitlines()
        if not line.startswith(field + "=")
    ]
    target.write_text("\n".join(lines), encoding="utf-8")
    with pytest.raises(e2e.SafetyError, match="three test"):
        e2e.load_target(target)


def test_live_file_and_unknown_source_are_refused(environments):
    source, target = environments
    with pytest.raises(e2e.SafetyError, match="separate"):
        e2e.load_target(source)
    source.write_text("", encoding="utf-8")
    with pytest.raises(e2e.SafetyError, match="identify the live"):
        e2e.load_target(target)


@pytest.mark.parametrize(
    "uri",
    [
        "https://test.example",
        "bolt://user:secret@test.example",
        "bolt://test.example/db",
        "bolt://test.example?x=1",
    ],
)
def test_ambiguous_or_embedded_secret_uri_is_refused(environments, uri):
    _, target = environments
    target.write_text(
        f"COGNODB_URI={uri}\nCOGNODB_USER=test\nCOGNODB_PASSWORD=test\n",
        encoding="utf-8",
    )
    with pytest.raises(BackupError):
        e2e.load_target(target)


@pytest.mark.parametrize("run_id", ["..", "../auth", "123", "x" * 18, "1" * 19])
def test_run_path_cannot_escape(run_id):
    with pytest.raises(e2e.SafetyError):
        e2e.run_directory(run_id)


@pytest.mark.parametrize(
    "confirm,exclusive", [(False, False), (True, False), (False, True)]
)
def test_no_connection_or_process_without_both_run_approvals(
    monkeypatch, confirm, exclusive
):
    driver, child = MagicMock(), MagicMock()
    monkeypatch.setattr(e2e, "make_driver", driver)
    monkeypatch.setattr(e2e.subprocess, "run", child)
    options = args()
    options.confirm_empty_test_target, options.exclusive_test_target = (
        confirm,
        exclusive,
    )
    with pytest.raises(e2e.SafetyError, match="Confirm"):
        e2e.execute_run({}, "target", options)
    driver.assert_not_called()
    child.assert_not_called()


@pytest.mark.parametrize("empty,schema", [(False, True), (False, False), (True, False)])
def test_nonempty_or_unprepared_target_never_launches(
    environments, monkeypatch, empty, schema
):
    _, path = environments
    target, identity = e2e.load_target(path)
    monkeypatch.setattr(e2e, "make_driver", MagicMock())
    monkeypatch.setattr(
        e2e, "inspect_target", lambda _: {"empty": empty, "schema_ready": schema}
    )
    child = MagicMock()
    monkeypatch.setattr(e2e.subprocess, "run", child)
    options = args()
    options.confirm_empty_test_target = options.exclusive_test_target = True
    with pytest.raises(e2e.SafetyError):
        e2e.execute_run(target, identity, options)
    child.assert_not_called()
    assert not e2e.RUNS.exists()


def test_expected_final_snapshot_passes():
    report = e2e.verify_persistence(snapshot(), RUN, {ACTOR})
    assert (
        report["nodes"] == 16
    )  # 8 employees + 3 skills + 4 projects + synthetic audit.


@pytest.mark.parametrize(
    "change",
    [
        "foreign_label",
        "foreign_name",
        "foreign_id",
        "foreign_actor",
        "foreign_project",
        "extra_node",
    ],
)
def test_cleanup_rejects_any_unowned_data(change):
    graph = snapshot()
    if change == "foreign_label":
        graph["nodes"][0]["labels"] = ["Foreign"]
    elif change == "foreign_name":
        graph["nodes"][0]["properties"]["name"] = "Real employee"
    elif change == "foreign_id":
        graph["nodes"][0]["properties"]["employee_id"] = "EMP001"
    elif change == "foreign_actor":
        graph["nodes"][-1]["properties"]["actor_id"] = "real-user"
    elif change == "foreign_project":
        graph["nodes"][-1]["properties"]["project_id"] = "PROJ001"
    else:
        graph["nodes"].append(
            {"labels": ["Team"], "properties": {"team_id": "TEAM001"}}
        )
    with pytest.raises(e2e.SafetyError):
        e2e.owned_nodes(graph, RUN, {ACTOR})


@pytest.mark.parametrize(
    "change",
    [
        "missing_relation",
        "duplicate_relation",
        "wrong_level",
        "wrong_experience",
        "overallocated",
        "missing_node",
        "missing_audit",
    ],
)
def test_persistence_detects_mismatch(change):
    graph = snapshot()
    if change == "missing_relation":
        graph["relationships"].pop()
    elif change == "duplicate_relation":
        graph["relationships"].append(deepcopy(graph["relationships"][0]))
    elif change in {"wrong_level", "wrong_experience"}:
        key = "level" if change == "wrong_level" else "years_experience"
        graph["relationships"][0]["properties"][key] = 1
    elif change == "overallocated":
        graph["relationships"][-1]["properties"]["allocation"] = 101
    elif change == "missing_node":
        graph["nodes"].pop(0)
    else:
        graph["nodes"].pop()
    with pytest.raises(e2e.SafetyError):
        e2e.verify_persistence(graph, RUN, {ACTOR})


def test_cleanup_requires_explicit_authority_before_reading_manifest(monkeypatch):
    driver = MagicMock()
    monkeypatch.setattr(e2e, "make_driver", driver)
    with pytest.raises(e2e.SafetyError, match="explicit approval"):
        e2e.cleanup({}, "target", args())
    driver.assert_not_called()


def test_cleanup_refuses_mismatched_manifest_before_connecting(
    environments, monkeypatch
):
    directory = e2e.run_directory(RUN)
    directory.mkdir(parents=True)
    (directory / "manifest.json").write_text(
        json.dumps({"run_id": RUN, "target_endpoint_sha256": "wrong"}), encoding="utf-8"
    )
    driver = MagicMock()
    monkeypatch.setattr(e2e, "make_driver", driver)
    options = args()
    options.confirm_cleanup = options.exclusive_test_target = True
    with pytest.raises(e2e.SafetyError, match="do not match"):
        e2e.cleanup({}, "target", options)
    driver.assert_not_called()


def test_cli_errors_do_not_echo_secrets(environments, monkeypatch, capsys):
    _, target = environments
    monkeypatch.setattr(
        e2e,
        "make_driver",
        MagicMock(side_effect=RuntimeError("secret-password@private-host")),
    )
    assert e2e.main(["preflight", "--target-env", str(target)]) == 1
    output = capsys.readouterr().out
    assert "RuntimeError" in output
    assert "secret-password" not in output and "private-host" not in output
