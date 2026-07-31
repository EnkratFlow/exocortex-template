#!/usr/bin/env python3
"""Deterministic tests for the read-only release closeout checker."""

from __future__ import annotations

import hashlib
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path


TEMPLATE = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
CHECKER = TEMPLATE / "scripts/check-release-state.sh"


def run(
    *args: str,
    cwd: Path,
    check: bool = True,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        args, cwd=cwd, text=True, capture_output=True, check=False, env=env
    )
    if check and result.returncode != 0:
        raise AssertionError(f"command failed: {args}\n{result.stdout}\n{result.stderr}")
    return result


def snapshot(root: Path) -> tuple[str, str, str, str]:
    safe_env = os.environ.copy()
    safe_env["GIT_OPTIONAL_LOCKS"] = "0"
    index_path = Path(
        run("git", "rev-parse", "--git-path", "index", cwd=root).stdout.strip()
    )
    if not index_path.is_absolute():
        index_path = root / index_path
    index_stat = index_path.stat()
    index_evidence = (
        f"{hashlib.sha256(index_path.read_bytes()).hexdigest()}:"
        f"{index_stat.st_size}:{index_stat.st_mtime_ns}"
    )
    return (
        run("git", "rev-parse", "HEAD", cwd=root).stdout,
        run("git", "show-ref", cwd=root).stdout,
        run(
            "git", "status", "--porcelain=v1", cwd=root, env=safe_env
        ).stdout,
        index_evidence,
    )


def fixture(
    *,
    dirty: bool = False,
    drift: bool = False,
    wrong_tag: bool = False,
    tag_version_mismatch: bool = False,
) -> tuple[tempfile.TemporaryDirectory[str], Path, str]:
    temp = tempfile.TemporaryDirectory(prefix="exo-release-state-")
    root = Path(temp.name) / "repo"
    root.mkdir()
    run("git", "init", "-b", "main", cwd=root)
    run("git", "config", "user.name", "Fixture", cwd=root)
    run("git", "config", "user.email", "fixture@example.invalid", cwd=root)
    initial_version = "3.2.1" if tag_version_mismatch else "3.2.2"
    (root / "VERSION").write_text(f"{initial_version}\n", encoding="utf-8")
    (root / "SHA256SUMS").write_text("fixture sums\n", encoding="utf-8")
    run("git", "add", "VERSION", "SHA256SUMS", cwd=root)
    run("git", "commit", "-m", "fixture release", cwd=root)
    release_commit = run("git", "rev-parse", "HEAD", cwd=root).stdout.strip()
    tag_name = "v9.9.9" if wrong_tag else "v3.2.2"
    run("git", "tag", "-a", tag_name, "-m", "fixture tag", cwd=root)
    if tag_version_mismatch:
        (root / "VERSION").write_text("3.2.2\n", encoding="utf-8")
        run("git", "add", "VERSION", cwd=root)
        run("git", "commit", "-m", "advance packaged version", cwd=root)
    if drift:
        (root / "later.txt").write_text("later\n", encoding="utf-8")
        run("git", "add", "later.txt", cwd=root)
        run("git", "commit", "-m", "local main drift", cwd=root)
    tracking_commit = release_commit if drift else run(
        "git", "rev-parse", "HEAD", cwd=root
    ).stdout.strip()
    run("git", "update-ref", "refs/remotes/origin/main", tracking_commit, cwd=root)
    if dirty:
        (root / "dirty.txt").write_text("dirty\n", encoding="utf-8")
    digest = hashlib.sha256(b"fixture sums\n").hexdigest()
    return temp, root, digest


def main() -> None:
    checker_text = CHECKER.read_text(encoding="utf-8")
    assert "export GIT_OPTIONAL_LOCKS=0" in checker_text
    assert "refs/heads/main:VERSION" in checker_text
    for forbidden in (
        r"\bgit\s+fetch\b",
        r"\bgit\s+pull\b",
        r"\bgit\s+checkout\b",
        r"\bgit\s+reset\b",
        r"\bgit\s+update-ref\b",
        r"\bgit\s+tag\s",
        r"\bgh\s+release\b",
    ):
        assert not re.search(forbidden, checker_text), (
            f"release checker contains mutating/network command: {forbidden}"
        )

    temp, root, digest = fixture()
    try:
        version = root / "VERSION"
        current = version.stat()
        os.utime(
            version,
            ns=(current.st_atime_ns, current.st_mtime_ns + 2_000_000_000),
        )
        before = snapshot(root)
        result = run("bash", str(CHECKER), "--published-digest", digest, cwd=root)
        assert "release_state=pass" in result.stdout
        assert before == snapshot(root), "release checker changed repository state"
    finally:
        temp.cleanup()

    for expected, options in (
        ("MAIN_WORKTREE_DIRTY", {"dirty": True}),
        ("LOCAL_MAIN_DRIFT", {"drift": True}),
        ("TAG_MISSING", {"wrong_tag": True}),
        ("TAG_VERSION_MISMATCH", {"tag_version_mismatch": True}),
    ):
        temp, root, _ = fixture(**options)
        try:
            before = snapshot(root)
            result = run(
                "bash", str(CHECKER), "--published-digest", digest,
                cwd=root, check=False,
            )
            assert result.returncode != 0
            assert f"EXOCORTEX_RELEASE_STATE_{expected}" in result.stderr
            assert before == snapshot(root), f"{expected} case changed repository state"
        finally:
            temp.cleanup()

    temp, root, _ = fixture()
    try:
        missing = run("bash", str(CHECKER), cwd=root, check=False)
        assert missing.returncode == 2
        assert "--published-digest SHA256" in missing.stderr

        result = run(
            "bash",
            str(CHECKER),
            "--published-digest",
            "0" * 64,
            cwd=root,
            check=False,
        )
        assert result.returncode != 0
        assert "EXOCORTEX_RELEASE_STATE_PUBLISHED_DIGEST_MISMATCH" in result.stderr
    finally:
        temp.cleanup()

    temp, root, digest = fixture()
    secondary = Path(temp.name) / "secondary"
    try:
        run("git", "tag", "-a", "v3.2.1", "-m", "older fixture tag", cwd=root)
        run("git", "worktree", "add", "-b", "secondary", str(secondary), "v3.2.1", cwd=root)
        (secondary / "VERSION").write_text("3.2.1\n", encoding="utf-8")
        run("git", "add", "VERSION", cwd=secondary)
        run("git", "commit", "-m", "secondary worktree version", cwd=secondary)
        result = run(
            "bash", str(CHECKER), "--published-digest", digest,
            cwd=secondary,
        )
        assert "release_state=pass" in result.stdout
        assert "version=3.2.2" in result.stdout
    finally:
        temp.cleanup()

    print("release_state_tests=pass")


if __name__ == "__main__":
    main()
