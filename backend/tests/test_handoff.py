import hashlib
import json
import subprocess
import zipfile

import pytest

from scripts.handoff import HandoffError, allowed, collect, export, inspect_file


@pytest.mark.parametrize(
    "name",
    [
        "backend/.env",
        "backend/.env.test",
        "backend/data/auth.sqlite3",
        "backend/data/auth.sqlite3-wal",
        "backups/graph.json",
        "frontend/test-results/trace.zip",
        "frontend/node_modules/lib/index.js",
        "../outside.md",
        "C:/outside.md",
        "/outside.md",
        "backend/private.pem",
        ".git/config",
        "docs/secret.zip",
    ],
)
def test_forbidden_paths(name):
    assert not allowed(name)


@pytest.mark.parametrize(
    "name",
    [
        "README.md",
        "backend/.env.example",
        "backend/.env.e2e.example",
        "frontend/.env.example",
        "backend/app/main.py",
        "frontend/package-lock.json",
        "docs/handoff.md",
    ],
)
def test_source_paths(name):
    assert allowed(name)


def test_sensitive_content_and_disguised_database(tmp_path):
    path = tmp_path / "README.md"
    secret = "synthetic-sensitive-value-only"
    path.write_text(secret)
    with pytest.raises(HandoffError, match="Sensitive") as caught:
        inspect_file(tmp_path, "README.md", {secret})
    assert secret not in str(caught.value)
    path.write_bytes(b"SQLite format 3\x00")
    with pytest.raises(HandoffError, match="database"):
        inspect_file(tmp_path, "README.md", set())


def test_env_template_must_be_blank(tmp_path):
    (tmp_path / "backend").mkdir()
    (tmp_path / "backend/.env.example").write_text(
        "COGNODB_PASSWORD=example-but-filled"
    )
    with pytest.raises(HandoffError, match="blank"):
        inspect_file(tmp_path, "backend/.env.example", set())


def test_oversized_file_is_rejected(tmp_path):
    (tmp_path / "README.md").write_bytes(b"x" * (3 * 1024 * 1024 + 1))
    with pytest.raises(HandoffError, match="oversized"):
        inspect_file(tmp_path, "README.md", set())


def test_reviewed_uri_fixture_does_not_exempt_other_secrets(tmp_path):
    relative = "backend/tests/test_backup_restore.py"
    path = tmp_path / relative
    path.parent.mkdir(parents=True)
    fixture = "bolt://" + "user:secret@example.com"
    path.write_text(fixture)
    assert inspect_file(tmp_path, relative, set())
    with pytest.raises(HandoffError, match="Sensitive"):
        inspect_file(tmp_path, relative, {fixture})
    path.write_text(fixture + "\n" + "bolt://" + "different:credential@private.invalid")
    with pytest.raises(HandoffError, match="Sensitive"):
        inspect_file(tmp_path, relative, set())


def test_export_worktree_not_just_head_and_verify_hashes(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    (repo / "README.md").write_text("first", encoding="utf-8")
    subprocess.run(["git", "-C", str(repo), "add", "README.md"], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(repo),
            "-c",
            "user.name=Test",
            "-c",
            "user.email=test@example.com",
            "-c",
            "core.hooksPath=NUL",
            "commit",
            "-qm",
            "test",
        ],
        check=True,
    )
    (repo / "README.md").write_text("final", encoding="utf-8")
    (repo / ".gitignore").write_text(".env\n", encoding="utf-8")
    (repo / ".env").write_text(
        "COGNODB_PASSWORD=test-only-local-sensitive", encoding="utf-8"
    )
    output = tmp_path / "output"
    manifest = export(repo, output)
    assert manifest["includes_worktree_changes"]
    assert manifest["file_count"] == 2
    with zipfile.ZipFile(output / "skillgraph-source.zip") as archive:
        assert archive.read("skillgraph/README.md") == b"final"
        assert all(".env" not in name for name in archive.namelist())
        assert json.loads(archive.read("handoff-manifest.json")) == manifest
        for item in manifest["files"]:
            assert (
                hashlib.sha256(archive.read("skillgraph/" + item["path"])).hexdigest()
                == item["sha256"]
            )
    with pytest.raises(HandoffError, match="never overwritten"):
        export(repo, output)
    (repo / "README.md").write_text("test-only-local-sensitive", encoding="utf-8")
    with pytest.raises(HandoffError, match="Sensitive"):
        collect(repo)


def test_reject_link_escape(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    outside = tmp_path / "outside.md"
    outside.write_text("outside", encoding="utf-8")
    try:
        (root / "README.md").symlink_to(outside)
    except OSError:
        pytest.skip("Symlink creation not available for this Windows account")
    with pytest.raises(HandoffError, match="leaves repository"):
        inspect_file(root, "README.md", set())
