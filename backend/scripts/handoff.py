"""Offline, source-only handoff audit/export. Never imports application settings."""

import argparse
import hashlib
import json
import re
import subprocess
import zipfile
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[2]
ROOT_FILES = {"README.md", "AGENTS.md", ".gitignore", ".gitattributes"}
ENV_TEMPLATES = {
    "backend/.env.example",
    "backend/.env.e2e.example",
    "backend/.env.restore.example",
    "frontend/.env.example",
}
SUFFIXES = {
    ".py",
    ".md",
    ".txt",
    ".toml",
    ".ini",
    ".ts",
    ".tsx",
    ".css",
    ".json",
    ".html",
    ".svg",
}
BLOCKED_PARTS = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "data",
    "backups",
    "restore-drills",
    "e2e-runs",
    "test-results",
    "playwright-report",
    "dist",
    "__pycache__",
    ".handoff",
}
PATTERNS = (
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"(?:bolt|neo4j|https?)(?:\+s|\+ssc)?://[^\s/:]+:[^\s/@]+@"),
    re.compile(
        r"\b(?:ghp_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,}|AKIA[A-Z0-9]{16})\b"
    ),
    re.compile(r"\$argon2id\$v=\d+\$m=[^\s\"']{60,}"),
)


class HandoffError(ValueError):
    pass


def allowed(name: str) -> bool:
    path = PurePosixPath(name)
    if path.is_absolute() or ".." in path.parts or "\\" in name or ":" in name:
        return False
    if any(part.lower() in BLOCKED_PARTS for part in path.parts):
        return False
    if name in ROOT_FILES or name in ENV_TEMPLATES:
        return True
    if any(part.startswith(".") for part in path.parts):
        return name in {"frontend/.prettierignore", "frontend/.prettierrc.json"}
    if path.suffix not in SUFFIXES:
        return False
    if path.parts[0] == "docs":
        return path.suffix == ".md"
    if path.parts[0] == "backend":
        return len(path.parts) == 2 or path.parts[1] in {"app", "scripts", "tests"}
    if path.parts[0] == "frontend":
        return len(path.parts) == 2 or path.parts[1] in {"src", "public", "tests"}
    return False


def local_sensitive_values(root: Path) -> set[str]:
    """Match existing local config values without printing/storing them in reports."""
    values = set()
    for folder in (root, root / "backend", root / "frontend"):
        for name in (".env", ".env.local", ".env.restore", ".env.e2e"):
            path = folder / name
            if not path.is_file() or path.is_symlink():
                continue
            for line in path.read_text(encoding="utf-8-sig").splitlines():
                key, separator, value = line.strip().partition("=")
                if not separator or key.startswith("#"):
                    continue
                value = value.strip().strip("\"'")
                if len(value) >= 8 and (
                    key == "COGNODB_URI" or re.search(r"PASSWORD|TOKEN|SECRET", key)
                ):
                    values.add(value)
    return values


def inspect_file(root: Path, name: str, sensitive: set[str]) -> bytes:
    if not allowed(name):
        raise HandoffError(f"Path not allowed in source handoff: {name}")
    path = root / name
    if not path.resolve().is_relative_to(root.resolve()):
        raise HandoffError(f"Path leaves repository: {name}")
    if any(
        p.is_symlink() or p.is_junction()
        for p in (path, *path.parents)
        if p != root.parent
    ):
        raise HandoffError(f"Linked path rejected: {name}")
    if not path.is_file() or path.stat().st_size > 3 * 1024 * 1024:
        raise HandoffError(f"Missing or oversized source file: {name}")
    with path.open("rb") as source:
        data = source.read(3 * 1024 * 1024 + 1)
    if len(data) > 3 * 1024 * 1024:
        raise HandoffError(f"Oversized source file: {name}")
    try:
        content = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise HandoffError(f"Non-text payload rejected: {name}") from None
    if "\x00" in content or data.startswith(b"SQLite format 3"):
        raise HandoffError(f"Binary/database payload rejected: {name}")
    scan_content = content
    # Reviewed negative-test fixture, not a live credential. Only this exact
    # value in this exact test may bypass the generic URI heuristic.
    if name == "backend/tests/test_backup_restore.py":
        scan_content = scan_content.replace("bolt://" + "user:secret@example.com", "")
    if name == "backend/tests/test_graph_e2e.py":
        scan_content = scan_content.replace("bolt://" + "user:secret@test.example", "")
    if any(value in content for value in sensitive) or any(
        p.search(scan_content) for p in PATTERNS
    ):
        raise HandoffError(f"Sensitive content suspected; inspect locally: {name}")
    if name in ENV_TEMPLATES:
        for line in content.splitlines():
            key, _, value = line.strip().partition("=")
            if key in {"COGNODB_URI", "COGNODB_PASSWORD"} and value.strip():
                raise HandoffError(
                    f"Graph template must have blank secrets/URI: {name}"
                )
    return data


def collect(root: Path) -> tuple[dict, dict[str, bytes]]:
    def git(*args):
        return subprocess.check_output(
            ["git", "-C", str(root), *args], stderr=subprocess.DEVNULL
        )

    if (
        Path(git("rev-parse", "--show-toplevel").decode().strip()).resolve()
        != root.resolve()
    ):
        raise HandoffError("Git root does not match the SkillGraph directory.")
    names = sorted(
        set(
            git("ls-files", "-z", "--cached", "--others", "--exclude-standard")
            .decode("utf-8")
            .strip("\0")
            .split("\0")
        )
    )
    if not names or len(names) > 2000:
        raise HandoffError("Unexpected source file count.")
    sensitive = local_sensitive_values(root)
    payload = {}
    total = 0
    for name in names:
        data = inspect_file(root, name, sensitive)
        total += len(data)
        if total > 20 * 1024 * 1024:
            raise HandoffError("Source handoff exceeds 20 MiB; inspect the file list.")
        payload[name] = data
    files = [
        {"path": name, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
        for name, data in payload.items()
    ]
    fingerprint = hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest()
    manifest = {
        "format_version": 1,
        "created_at": datetime.now(UTC).isoformat(),
        "base_commit": git("rev-parse", "HEAD").decode().strip(),
        "includes_worktree_changes": bool(git("status", "--porcelain")),
        "source_fingerprint_sha256": fingerprint,
        "file_count": len(files),
        "total_bytes": total,
        "files": files,
        "scope": "source-only; no Git history, runtime data, dependencies or backups",
        "scan_limit": "Path/content heuristics and current local env matches; not a full security audit.",
    }
    return manifest, payload


def export(root: Path, output: Path) -> dict:
    manifest, payload = collect(root)  # Validate all bytes before writing any output.
    output = output.absolute()
    if output.exists() or output.is_symlink():
        raise HandoffError(
            "Output must be a new directory; existing output is never overwritten."
        )
    output.mkdir(parents=True, exist_ok=False)
    raw_manifest = json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8")
    with zipfile.ZipFile(
        output / "skillgraph-source.zip", "x", zipfile.ZIP_DEFLATED
    ) as archive:
        for name, data in payload.items():
            archive.writestr("skillgraph/" + name, data)
        archive.writestr("handoff-manifest.json", raw_manifest)
    (output / "handoff-manifest.json").write_bytes(raw_manifest)
    with zipfile.ZipFile(output / "skillgraph-source.zip") as archive:
        if archive.testzip() is not None:
            raise HandoffError(
                "Archive verification failed; output retained for inspection."
            )
        for item in manifest["files"]:
            data = archive.read("skillgraph/" + item["path"])
            if hashlib.sha256(data).hexdigest() != item["sha256"]:
                raise HandoffError("Archive checksum mismatch.")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["check", "export"])
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        if args.command == "export":
            if args.output is None:
                raise HandoffError("export requires --output.")
            manifest = export(ROOT, args.output)
        else:
            manifest, _ = collect(ROOT)
        print(json.dumps({k: v for k, v in manifest.items() if k != "files"}, indent=2))
        return 0
    except (HandoffError, OSError, subprocess.CalledProcessError) as exc:
        # Only controlled validation errors may include a relative filename; never echo file contents.
        print(
            str(exc)
            if isinstance(exc, HandoffError)
            else f"Handoff failed ({type(exc).__name__})."
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
