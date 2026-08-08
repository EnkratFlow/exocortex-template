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
PUBLIC_CHECKER = TEMPLATE / "scripts/check-public-release.py"
CANARY = "gh" + "p_" + "0123456789ABCDEFGHIJKL"


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
    lightweight_tag: bool = False,
    tag_main_mismatch: bool = False,
    forbidden_range: bool = False,
    import_shadow: bool = False,
    tag_message_canary: bool = False,
) -> tuple[tempfile.TemporaryDirectory[str], Path, str]:
    temp = tempfile.TemporaryDirectory(prefix="exo-release-state-")
    root = Path(temp.name) / "repo"
    root.mkdir()
    run("git", "init", "-b", "main", cwd=root)
    run("git", "config", "user.name", "Fixture", cwd=root)
    run("git", "config", "user.email", "fixture@example.invalid", cwd=root)
    (root / "scripts").mkdir()
    (root / "scripts" / "check-public-release.py").write_bytes(
        PUBLIC_CHECKER.read_bytes()
    )
    (root / "VERSION").write_text("3.2.1\n", encoding="utf-8")
    (root / "SHA256SUMS").write_text("baseline sums\n", encoding="utf-8")
    run("git", "add", "VERSION", "SHA256SUMS", "scripts", cwd=root)
    run("git", "commit", "-m", "fixture baseline", cwd=root)
    baseline_commit = run("git", "rev-parse", "HEAD", cwd=root).stdout.strip()
    run("git", "tag", "-a", "v3.2.1", "-m", "fixture baseline tag", cwd=root)
    if forbidden_range:
        (root / "transient.txt").write_text(CANARY + "\n", encoding="utf-8")
        run("git", "add", "transient.txt", cwd=root)
        run("git", "commit", "-m", "transient fictional canary", cwd=root)
        (root / "transient.txt").unlink()
        run("git", "add", "-u", cwd=root)
        run("git", "commit", "-m", "remove transient fictional canary", cwd=root)
    if import_shadow:
        (root / "scripts" / "hashlib.py").write_text(
            "raise RuntimeError('worktree import shadow executed')\n", encoding="utf-8"
        )
    baseline_record = root / ".exocortex" / "release-baseline.json"
    baseline_record.parent.mkdir(parents=True, exist_ok=True)
    baseline_record.write_text(
        "{\n"
        '  "schema_version": "public-v1",\n'
        '  "kind": "exocortex_release_baseline",\n'
        '  "previous_published_tag": "v3.2.1",\n'
        f'  "previous_published_commit": "{baseline_commit}"\n'
        "}\n",
        encoding="utf-8",
    )
    checker_hash = hashlib.sha256(PUBLIC_CHECKER.read_bytes()).hexdigest()
    record_hash = hashlib.sha256(baseline_record.read_bytes()).hexdigest()
    sums_text = (
        f"{record_hash}  .exocortex/release-baseline.json\n"
        f"{checker_hash}  scripts/check-public-release.py\n"
    )
    (root / "VERSION").write_text("3.2.2\n", encoding="utf-8")
    (root / "SHA256SUMS").write_text(sums_text, encoding="utf-8")
    run("git", "add", "VERSION", "SHA256SUMS", "scripts", ".exocortex", cwd=root)
    run("git", "commit", "-m", "fixture release", cwd=root)
    tag_name = "v9.9.9" if wrong_tag else "v3.2.2"
    if lightweight_tag:
        run("git", "tag", tag_name, cwd=root)
    else:
        tag_message = f"fixture tag {CANARY}" if tag_message_canary else "fixture tag"
        run("git", "tag", "-a", tag_name, "-m", tag_message, cwd=root)
    if drift or tag_main_mismatch:
        (root / "later.txt").write_text("later\n", encoding="utf-8")
        run("git", "add", "later.txt", cwd=root)
        run("git", "commit", "-m", "advance main", cwd=root)
    head_commit = run("git", "rev-parse", "HEAD", cwd=root).stdout.strip()
    tracking_commit = (
        run("git", "rev-parse", "HEAD^", cwd=root).stdout.strip()
        if drift else head_commit
    )
    run("git", "update-ref", "refs/remotes/origin/main", tracking_commit, cwd=root)
    if dirty:
        (root / "dirty.txt").write_text("dirty\n", encoding="utf-8")
    digest = hashlib.sha256(sums_text.encode("utf-8")).hexdigest()
    return temp, root, digest


def main() -> None:
    checker_text = CHECKER.read_text(encoding="utf-8")
    assert "export GIT_OPTIONAL_LOCKS=0" in checker_text
    assert "export GIT_NO_REPLACE_OBJECTS=1" in checker_text
    assert "refs/heads/main:VERSION" in checker_text
    assert "BASELINE_TAG_DIRECT_TARGET_INVALID" in checker_text
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
        result = run(
            "bash", str(CHECKER), "--published-digest", digest,
            "--baseline-tag", "v3.2.1", cwd=root,
        )
        assert "release_state=pass" in result.stdout
        assert before == snapshot(root), "release checker changed repository state"
    finally:
        temp.cleanup()

    temp, root, digest = fixture(import_shadow=True)
    try:
        result = run(
            "bash", str(CHECKER), "--published-digest", digest,
            "--baseline-tag", "v3.2.1", cwd=root,
        )
        assert "release_state=pass" in result.stdout
    finally:
        temp.cleanup()

    temp, root, digest = fixture(tag_message_canary=True)
    try:
        result = run(
            "bash", str(CHECKER), "--published-digest", digest,
            "--baseline-tag", "v3.2.1", cwd=root, check=False,
        )
        assert result.returncode != 0
        assert "EXOCORTEX_RELEASE_STATE_PUBLIC_BOUNDARY_FAILED" in result.stderr
        assert CANARY not in result.stdout + result.stderr
    finally:
        temp.cleanup()

    for expected, options in (
        ("MAIN_WORKTREE_DIRTY", {"dirty": True}),
        ("LOCAL_MAIN_DRIFT", {"drift": True}),
        ("TAG_MISSING", {"wrong_tag": True}),
        ("TAG_NOT_ANNOTATED", {"lightweight_tag": True}),
        ("TAG_MAIN_MISMATCH", {"tag_main_mismatch": True}),
        ("PUBLIC_BOUNDARY_FAILED", {"forbidden_range": True}),
    ):
        temp, root, case_digest = fixture(**options)
        try:
            before = snapshot(root)
            result = run(
                "bash", str(CHECKER), "--published-digest", case_digest,
                "--baseline-tag", "v3.2.1",
                cwd=root, check=False,
            )
            assert result.returncode != 0
            assert f"EXOCORTEX_RELEASE_STATE_{expected}" in result.stderr
            assert before == snapshot(root), f"{expected} case changed repository state"
        finally:
            temp.cleanup()

    temp, root, case_digest = fixture()
    try:
        missing = run("bash", str(CHECKER), cwd=root, check=False)
        assert missing.returncode == 2
        assert "--published-digest SHA256 --baseline-tag" in missing.stderr

        result = run(
            "bash",
            str(CHECKER),
            "--published-digest",
            "0" * 64,
            "--baseline-tag",
            "v3.2.1",
            cwd=root,
            check=False,
        )
        assert result.returncode != 0
        assert "EXOCORTEX_RELEASE_STATE_PUBLISHED_DIGEST_MISMATCH" in result.stderr

        missing_baseline = run(
            "bash", str(CHECKER), "--published-digest", case_digest,
            "--baseline-tag", "v0.0.0", cwd=root, check=False,
        )
        assert "EXOCORTEX_RELEASE_STATE_BASELINE_TAG_MISSING" in missing_baseline.stderr
    finally:
        temp.cleanup()

    temp, root, digest = fixture(forbidden_range=True)
    try:
        post_deletion = run("git", "rev-parse", "HEAD^", cwd=root).stdout.strip()
        run(
            "git", "tag", "-a", "v3.2.1.1", "-m", "unreviewed late baseline",
            post_deletion, cwd=root,
        )
        result = run(
            "bash", str(CHECKER), "--published-digest", digest,
            "--baseline-tag", "v3.2.1.1", cwd=root, check=False,
        )
        assert result.returncode != 0
        assert "EXOCORTEX_RELEASE_STATE_BASELINE_RECORD_TAG_MISMATCH" in result.stderr
    finally:
        temp.cleanup()

    temp, root, digest = fixture()
    try:
        baseline_commit = run(
            "git", "rev-parse", "v3.2.1^{commit}", cwd=root
        ).stdout.strip()
        run(
            "git", "tag", "-a", "v3.2.1-inner", "-m", "nested inner baseline",
            baseline_commit, cwd=root,
        )
        run(
            "git", "tag", "-a", "-f", "v3.2.1", "-m", "nested outer baseline",
            "v3.2.1-inner", cwd=root,
        )
        result = run(
            "bash", str(CHECKER), "--published-digest", digest,
            "--baseline-tag", "v3.2.1", cwd=root, check=False,
        )
        assert result.returncode != 0
        assert "EXOCORTEX_RELEASE_STATE_BASELINE_TAG_DIRECT_TARGET_INVALID" in result.stderr
    finally:
        temp.cleanup()

    temp, root, digest = fixture()
    secondary = Path(temp.name) / "secondary"
    try:
        run("git", "worktree", "add", "-b", "secondary", str(secondary), "v3.2.1", cwd=root)
        result = run(
            "bash", str(CHECKER), "--published-digest", digest,
            "--baseline-tag", "v3.2.1",
            cwd=secondary,
        )
        assert "release_state=pass" in result.stdout
        assert "version=3.2.2" in result.stdout
    finally:
        temp.cleanup()

    print("release_state_tests=pass")


if __name__ == "__main__":
    main()
