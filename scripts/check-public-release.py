#!/usr/bin/env python3
"""Read-only public-template boundary checker.

The checker deliberately reports only rule identifiers and metadata. Paths are
represented by a coarse class and digest, never raw text, so a sensitive value
in a filename is not echoed. It never prints a matched line, blob, or
credential-shaped value. A current-tree scan
is useful for installer source validation; an explicit Git range additionally
scans every blob newly reachable from the candidate, including blobs that were
added and later deleted inside the range.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Iterable


class CheckError(Exception):
    """A safe, metadata-only validation failure."""


@dataclass(frozen=True)
class Finding:
    rule: str
    path: str
    commit: str
    count: int


def git_environment() -> dict[str, str]:
    """Return Git environment with replacement and repository redirects disabled."""

    value = os.environ.copy()
    for name in (
        "GIT_DIR",
        "GIT_WORK_TREE",
        "GIT_INDEX_FILE",
        "GIT_OBJECT_DIRECTORY",
        "GIT_ALTERNATE_OBJECT_DIRECTORIES",
        "GIT_COMMON_DIR",
        "GIT_NAMESPACE",
    ):
        value.pop(name, None)
    value["GIT_NO_REPLACE_OBJECTS"] = "1"
    value["GIT_OPTIONAL_LOCKS"] = "0"
    return value


# These patterns intentionally prefer false negatives to low-confidence noise.
# They are byte patterns so the checker can scan arbitrary Git blobs without
# decoding their content.  Never include a matched substring in diagnostics.
SECRET_PATTERNS: tuple[tuple[str, re.Pattern[bytes]], ...] = (
    ("ANTHROPIC_KEY", re.compile(rb"sk-ant-[A-Za-z0-9_-]{20,}")),
    ("GITHUB_FINE_GRAINED_TOKEN", re.compile(rb"github_pat_[A-Za-z0-9_]{20,}")),
    ("GITHUB_TOKEN", re.compile(rb"gh[pousr]_[A-Za-z0-9]{20,}")),
    ("GITLAB_TOKEN", re.compile(rb"glpat-[A-Za-z0-9_-]{20,}")),
    ("GOOGLE_API_KEY", re.compile(rb"AIza[0-9A-Za-z_-]{30,}")),
    ("OPENAI_KEY", re.compile(rb"sk-(?:proj-)?[A-Za-z0-9_-]{20,}")),
    ("SLACK_TOKEN", re.compile(rb"xox[baprs]-[A-Za-z0-9-]{20,}")),
    ("AWS_ACCESS_KEY_ID", re.compile(rb"(?:AKIA|ASIA)[0-9A-Z]{16}")),
    (
        "PRIVATE_KEY_BLOCK",
        re.compile(rb"-----BEGIN (?:[A-Z0-9 ]+ )?PRIVATE KEY-----"),
    ),
)

EVENT_EXAMPLES = {
    ".exocortex/events/.gitkeep",
    ".exocortex/events/2000-01-01_00-00-00_example-event.md",
}
ENV_ALLOWLIST = {".exocortex/.env.example"}
DATA_FIXTURE_DIGESTS = {
    ".exocortex/events/.gitkeep": "98a444192b24c433a7239f4b6bb2d32a531184d966665e4c49d155c4741dc74e",
    ".exocortex/events/2000-01-01_00-00-00_example-event.md": "87a39e4d08a515237bc96bdcc2a7cecbc17ab5aa015978c23584097152c154d1",
    ".exocortex/.env.example": "f7b31458dd5095a7fe2d07d093dc7c0e9702d3693faa76af4addad88168601bf",
}
PLANNING_STUB_DIGESTS = {
    ".exocortex/PROJECT_MEMORY.md": "5a904b0ea9fad0bfa1972f0deceaa02eb1cbf1260a9d66b6a91919f528276a12",
    ".exocortex/LESSONS.md": "a5b61ca65dcccb7909525b130c2c70ccb7c6d95cd9ec1321d7269f2b83aa1935",
    ".exocortex/OPEN_DECISIONS.md": "d5b8928eff378fffd4f597af1777284cfe35c937ac6042761f1f068d06b57f7d",
    ".exocortex/TODO.md": "71d66488d522e43cbefdd47a3aeabb410741939326a0fc5365bdb758782dca6f",
    ".exocortex/control/ROADMAP.md": "0bc42d681fe1cfdccc58fc30b2acb920ed0a51452e45b516e1d2219b57340cf8",
    ".exocortex/control/INTERRUPTS.md": "4d9a4219d1d0761ebb26a64c9457330b0922a2fa25fe5ed06a0e1719a1cfa76b",
    ".exocortex/control/BACKLOG.md": "b390e5f4d2b430623b7e6b908cb1f0e97acb5353ee1b7edb772eb925051c92f6",
    ".exocortex/control/ARCH_OVERVIEW.md": "850d17384777a6503b5db25d444a8f4de36b8c2ea8001d264d3645f6845c7eb0",
    ".exocortex/control/REPO_ORGANIZATION_REPORT.md": "80f091c61ec165c139dc2bfa2dbb49d6af1045c62c5c52826e44c8ed62cc4961",
}
PLANNING_RUNTIME_PATHS = set(PLANNING_STUB_DIGESTS)


def git(root: Path, *args: str, input_bytes: bytes | None = None) -> bytes:
    result = subprocess.run(
        ("git", "-C", os.fspath(root), *args),
        input=input_bytes,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        env=git_environment(),
    )
    if result.returncode:
        raise CheckError("GIT_COMMAND_FAILED")
    return result.stdout


def normalize_path(value: str) -> str:
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts:
        raise CheckError("UNSAFE_TRACKED_PATH")
    return path.as_posix()


def is_env_path(path: str) -> bool:
    name = PurePosixPath(path).name
    return name == ".env" or name.startswith(".env.") or name == ".envrc"


def path_rule(path: str) -> str | None:
    """Return a data-plane rule without reading the file."""

    if is_env_path(path) and path not in ENV_ALLOWLIST:
        return "ENV_FILE"
    if path.startswith(".exocortex/SESSION_CONTEXT"):
        return "SESSION_CONTEXT"
    if path.startswith(".exocortex/events/") and path not in EVENT_EXAMPLES:
        return "EVENT_DATA"
    if path.startswith(".exocortex/work-items/"):
        return "WORK_ITEM_DATA"
    if path.startswith(".exocortex/local/"):
        return "LOCAL_PROTOCOL_DATA"
    if path.startswith(".exocortex/planning/"):
        return "PLANNING_RUNTIME_DATA"
    if path.startswith((".exocortex/archive/", ".exocortex/hub/")):
        return "PROJECT_RUNTIME_DATA"
    if path in {
        ".exocortex/.project-name",
        ".exocortex/.install-manifest",
        ".exocortex/.hub_enabled",
        ".exocortex/.hub_disabled",
        ".exocortex/subconscious_patterns.md",
        ".exocortex/control/ACTIVE_WORK.md",
        ".exocortex/control/BRANCH_POLICY.md",
        ".exocortex/control/REPO_STATE.md",
    }:
        return "PROJECT_RUNTIME_DATA"
    if path in {
        ".exocortex/control/EXECUTOR_REGISTRY.json",
        ".exocortex/control/EXTERNAL_SYNC_POLICY.json",
    }:
        return "RUNTIME_CONTROL_REGISTRY"
    return None


def planning_stub_rule(path: str, content: bytes) -> str | None:
    if path not in PLANNING_RUNTIME_PATHS:
        return None
    expected_digest = PLANNING_STUB_DIGESTS.get(path)
    actual_digest = hashlib.sha256(content).hexdigest()
    return None if actual_digest == expected_digest else "PLANNING_RUNTIME_DATA"


def data_fixture_rule(path: str, content: bytes) -> str | None:
    expected_digest = DATA_FIXTURE_DIGESTS.get(path)
    if expected_digest is None:
        return None
    actual_digest = hashlib.sha256(content).hexdigest()
    return None if actual_digest == expected_digest else "DATA_FIXTURE_MODIFIED"


def content_findings(path: str, commit: str, content: bytes) -> list[Finding]:
    findings: list[Finding] = []
    planning_rule = planning_stub_rule(path, content)
    if planning_rule:
        findings.append(Finding(planning_rule, path, commit, 1))
    fixture_rule = data_fixture_rule(path, content)
    if fixture_rule:
        findings.append(Finding(fixture_rule, path, commit, 1))
    for rule, pattern in SECRET_PATTERNS:
        count = len(pattern.findall(content))
        if count:
            findings.append(Finding(rule, path, commit, count))
    return findings


def path_secret_findings(path: str, commit: str) -> list[Finding]:
    """Detect high-confidence credential shapes in Git-visible path bytes."""

    encoded = path.encode("utf-8", errors="surrogateescape")
    findings: list[Finding] = []
    for rule, pattern in SECRET_PATTERNS:
        count = len(pattern.findall(encoded))
        if count:
            findings.append(Finding(rule, path, commit, count))
    return findings


def tracked_paths(root: Path) -> list[str]:
    raw_paths = git(root, "ls-files", "-z")
    return sorted(
        normalize_path(item.decode("utf-8", errors="surrogateescape"))
        for item in raw_paths.split(b"\0")
        if item
    )


def source_tree_paths_lstat(root: Path) -> list[str]:
    """Walk without openat, refusing symlinks and non-regular files at every step.

    Used on platforms that do not expose O_NOFOLLOW/O_DIRECTORY (notably Windows).
    Weaker than the anchored walk against an attacker who can swap a directory
    mid-walk, but it still refuses every symlink and special file, which is what
    the public-release boundary actually asserts about the tree.
    """

    paths: list[str] = []

    def walk(directory: Path, prefix: tuple[str, ...]) -> None:
        try:
            names = sorted(entry.name for entry in os.scandir(directory))
        except OSError as error:
            raise CheckError("SOURCE_TREE_TOPOLOGY_CHANGED") from error
        for name in names:
            if name in {".git", "__pycache__"} or name.endswith((".pyc", ".pyo")):
                continue
            relative = normalize_path(PurePosixPath(*prefix, name).as_posix())
            child = directory / name
            try:
                value = os.lstat(child)
            except OSError as error:
                raise CheckError("SOURCE_TREE_TOPOLOGY_CHANGED") from error
            if stat.S_ISLNK(value.st_mode):
                raise CheckError("SOURCE_TREE_TOPOLOGY_CHANGED")
            if stat.S_ISDIR(value.st_mode):
                walk(child, (*prefix, name))
            elif stat.S_ISREG(value.st_mode):
                paths.append(relative)
            else:
                raise CheckError("SOURCE_TREE_TOPOLOGY_CHANGED")

    walk(root, ())
    return sorted(paths)


def source_tree_paths(root: Path) -> list[str]:
    """Return source paths using anchored, non-following directory descriptors."""

    nofollow = getattr(os, "O_NOFOLLOW", 0)
    directory_flag = getattr(os, "O_DIRECTORY", 0)
    if not nofollow or not directory_flag:
        return source_tree_paths_lstat(root)
    paths: list[str] = []

    def walk(directory_fd: int, prefix: tuple[str, ...]) -> None:
        try:
            names = sorted(os.listdir(directory_fd))
        except OSError as error:
            raise CheckError("SOURCE_TREE_TOPOLOGY_CHANGED") from error
        for name in names:
            if name in {".git", "__pycache__"} or name.endswith((".pyc", ".pyo")):
                continue
            relative = normalize_path(PurePosixPath(*prefix, name).as_posix())
            try:
                value = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
            except OSError as error:
                raise CheckError("SOURCE_TREE_TOPOLOGY_CHANGED") from error
            if stat.S_ISDIR(value.st_mode):
                flags = os.O_RDONLY | directory_flag | nofollow | getattr(os, "O_CLOEXEC", 0)
                try:
                    child_fd = os.open(name, flags, dir_fd=directory_fd)
                except OSError as error:
                    raise CheckError("SOURCE_TREE_TOPOLOGY_CHANGED") from error
                try:
                    walk(child_fd, (*prefix, name))
                finally:
                    os.close(child_fd)
            else:
                paths.append(relative)

    try:
        root_fd = os.open(
            os.fspath(root),
            os.O_RDONLY | directory_flag | nofollow | getattr(os, "O_CLOEXEC", 0),
        )
    except OSError as error:
        raise CheckError("SOURCE_TREE_TOPOLOGY_CHANGED") from error
    try:
        walk(root_fd, ())
    finally:
        os.close(root_fd)
    return sorted(paths)


def classify_anchored_path(parent_fd: int, name: str) -> str:
    """Classify without following a final component; races fail closed."""

    try:
        value = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    except OSError:
        return "PATH_UNREADABLE"
    if stat.S_ISLNK(value.st_mode):
        return "SYMLINK"
    if not stat.S_ISREG(value.st_mode):
        return "SPECIAL_PATH"
    if value.st_nlink != 1:
        return "HARDLINK"
    return "UNSAFE_TOPOLOGY"


def read_regular_lstat(root: Path, path: str) -> tuple[bytes | None, str | None]:
    """Read one root-relative file without openat, refusing symlinked components.

    Fallback for platforms without O_NOFOLLOW/O_DIRECTORY. Every component is
    lstat'd and any symlink, special file or hardlinked file is refused, matching
    the classifications the anchored reader returns.
    """

    parts = PurePosixPath(path).parts
    if not parts:
        return None, "PATH_UNREADABLE"
    current = root
    for component in parts[:-1]:
        current = current / component
        try:
            value = os.lstat(current)
        except OSError:
            return None, "PATH_UNREADABLE"
        if stat.S_ISLNK(value.st_mode):
            return None, "SYMLINK"
        if not stat.S_ISDIR(value.st_mode):
            return None, "SPECIAL_PATH"
    target = current / parts[-1]
    try:
        value = os.lstat(target)
    except OSError:
        return None, "PATH_UNREADABLE"
    if stat.S_ISLNK(value.st_mode):
        return None, "SYMLINK"
    if not stat.S_ISREG(value.st_mode):
        return None, "SPECIAL_PATH"
    if value.st_nlink != 1:
        return None, "HARDLINK"
    try:
        with open(target, "rb") as handle:
            return handle.read(), None
    except OSError:
        return None, "PATH_UNREADABLE"


def secure_read_regular(root: Path, path: str) -> tuple[bytes | None, str | None]:
    """Read one root-relative file through an openat/O_NOFOLLOW fd chain."""

    nofollow = getattr(os, "O_NOFOLLOW", 0)
    directory_flag = getattr(os, "O_DIRECTORY", 0)
    if not nofollow or not directory_flag:
        return read_regular_lstat(root, path)
    parts = PurePosixPath(path).parts
    if not parts:
        return None, "PATH_UNREADABLE"
    directory_fds: list[int] = []
    final_fd: int | None = None
    try:
        root_fd = os.open(
            os.fspath(root),
            os.O_RDONLY | directory_flag | nofollow | getattr(os, "O_CLOEXEC", 0),
        )
        directory_fds.append(root_fd)
        current_fd = root_fd
        directory_flags = os.O_RDONLY | directory_flag | nofollow | getattr(os, "O_CLOEXEC", 0)
        for component in parts[:-1]:
            try:
                next_fd = os.open(component, directory_flags, dir_fd=current_fd)
            except OSError:
                return None, classify_anchored_path(current_fd, component)
            directory_fds.append(next_fd)
            current_fd = next_fd
        try:
            final_fd = os.open(
                parts[-1],
                os.O_RDONLY
                | nofollow
                | getattr(os, "O_CLOEXEC", 0)
                | getattr(os, "O_NONBLOCK", 0),
                dir_fd=current_fd,
            )
        except OSError:
            return None, classify_anchored_path(current_fd, parts[-1])
        value = os.fstat(final_fd)
        if not stat.S_ISREG(value.st_mode):
            return None, "SPECIAL_PATH"
        if value.st_nlink != 1:
            return None, "HARDLINK"
        with os.fdopen(final_fd, "rb", closefd=True) as stream:
            final_fd = None
            return stream.read(), None
    except OSError:
        return None, "PATH_UNREADABLE"
    finally:
        if final_fd is not None:
            os.close(final_fd)
        for directory_fd in reversed(directory_fds):
            os.close(directory_fd)


def current_tree_findings(root: Path, *, include_untracked: bool = False) -> list[Finding]:
    findings: list[Finding] = []
    paths = source_tree_paths(root) if include_untracked else tracked_paths(root)
    for path in paths:
        findings.extend(path_secret_findings(path, "WORKTREE"))
        rule = path_rule(path)
        if rule:
            findings.append(Finding(rule, path, "WORKTREE", 1))
            continue
        content, topology_rule = secure_read_regular(root, path)
        if topology_rule is not None:
            findings.append(Finding(topology_rule, path, "WORKTREE", 1))
            continue
        assert content is not None
        findings.extend(content_findings(path, "WORKTREE", content))
    return findings


def commit_findings(root: Path, revision: str) -> list[Finding]:
    """Scan the complete immutable tree at one exact commit."""

    commit = resolve_commit(root, revision, "TREE")
    findings: list[Finding] = []
    content_cache: dict[str, bytes] = {}
    for path, object_id, mode, object_type in commit_tree_entries(root, commit):
        findings.extend(path_secret_findings(path, commit))
        topology_rule = git_entry_rule(mode, object_type)
        if topology_rule:
            findings.append(Finding(topology_rule, path, commit, 1))
            continue
        rule = path_rule(path)
        if rule:
            findings.append(Finding(rule, path, commit, 1))
            continue
        if object_id not in content_cache:
            content_cache[object_id] = git(root, "cat-file", "blob", object_id)
        findings.extend(content_findings(path, commit, content_cache[object_id]))
    return findings


def resolve_revision_object(root: Path, revision: str, role: str) -> str:
    try:
        object_id = git(root, "rev-parse", "--verify", revision).decode("ascii").strip()
    except CheckError as error:
        raise CheckError(f"{role}_COMMIT_INVALID") from error
    if not re.fullmatch(r"[0-9a-f]{40,64}", object_id):
        raise CheckError(f"{role}_COMMIT_INVALID")
    return object_id


def direct_tag_target_commit(root: Path, object_id: str, role: str) -> tuple[str, bytes]:
    """Validate an annotated tag's immediate target without peeling tag chains."""

    content = git(root, "cat-file", "tag", object_id)
    headers = content.split(b"\n\n", 1)[0].splitlines()
    values: dict[bytes, bytes] = {}
    for line in headers:
        key, separator, value = line.partition(b" ")
        if separator and key in {b"object", b"type"} and key not in values:
            values[key] = value
    target = values.get(b"object", b"")
    declared_type = values.get(b"type", b"")
    if not re.fullmatch(rb"[0-9a-f]{40,64}", target) or declared_type != b"commit":
        raise CheckError(f"{role}_TAG_TARGET_INVALID")
    target_id = target.decode("ascii")
    try:
        actual_type = git(root, "cat-file", "-t", target_id).strip()
    except CheckError as error:
        raise CheckError(f"{role}_TAG_TARGET_INVALID") from error
    if actual_type != b"commit":
        raise CheckError(f"{role}_TAG_TARGET_INVALID")
    return target_id, content


def resolve_commit(root: Path, revision: str, role: str) -> str:
    object_id = resolve_revision_object(root, revision, role)
    try:
        object_type = git(root, "cat-file", "-t", object_id).strip()
    except CheckError as error:
        raise CheckError(f"{role}_COMMIT_INVALID") from error
    if object_type == b"commit":
        return object_id
    if object_type == b"tag":
        target_id, _ = direct_tag_target_commit(root, object_id, role)
        try:
            peeled = git(
                root, "rev-parse", "--verify", f"{revision}^{{commit}}"
            ).decode("ascii").strip()
        except CheckError as error:
            raise CheckError(f"{role}_TAG_TARGET_INVALID") from error
        if peeled != target_id:
            raise CheckError(f"{role}_TAG_TARGET_INVALID")
        return target_id
    raise CheckError(f"{role}_COMMIT_INVALID")


def range_blobs(root: Path, baseline: str, candidate: str) -> dict[str, set[str]]:
    """Return newly reachable blob IDs and Git-reported paths for the range."""

    raw = git(root, "rev-list", "--objects", f"{baseline}..{candidate}")
    object_ids: dict[str, set[str]] = defaultdict(set)
    for line in raw.splitlines():
        object_id, _, encoded_path = line.partition(b" ")
        if not re.fullmatch(rb"[0-9a-f]{40,64}", object_id):
            continue
        object_type = git(root, "cat-file", "-t", object_id.decode("ascii")).strip()
        if object_type != b"blob":
            continue
        path = (
            normalize_path(encoded_path.decode("utf-8", errors="surrogateescape"))
            if encoded_path
            else "<unattributed-blob>"
        )
        object_ids[object_id.decode("ascii")].add(path)
    return object_ids


def range_commits(root: Path, baseline: str, candidate: str) -> list[str]:
    """Return every commit introduced by the range in deterministic order."""

    raw = git(root, "rev-list", "--reverse", "--topo-order", f"{baseline}..{candidate}")
    commits = [item.decode("ascii") for item in raw.splitlines() if item]
    if not all(re.fullmatch(r"[0-9a-f]{40,64}", item) for item in commits):
        raise CheckError("RANGE_COMMIT_INVALID")
    return commits


def commit_tree_entries(root: Path, commit: str) -> list[tuple[str, str, str, str]]:
    """Return every path, object ID, mode, and type in one commit tree."""

    raw = git(root, "ls-tree", "-r", "-z", "--full-tree", commit)
    entries: list[tuple[str, str, str, str]] = []
    for record in raw.split(b"\0"):
        if not record:
            continue
        metadata, separator, encoded_path = record.partition(b"\t")
        fields = metadata.split()
        if separator != b"\t" or len(fields) != 3:
            raise CheckError("RANGE_TREE_INVALID")
        mode, object_type, object_id = fields
        if not re.fullmatch(rb"[0-9a-f]{40,64}", object_id):
            raise CheckError("RANGE_TREE_INVALID")
        path = normalize_path(encoded_path.decode("utf-8", errors="surrogateescape"))
        entries.append(
            (
                path,
                object_id.decode("ascii"),
                mode.decode("ascii"),
                object_type.decode("ascii"),
            )
        )
    return sorted(entries)


def git_entry_rule(mode: str, object_type: str) -> str | None:
    if object_type == "blob" and mode in {"100644", "100755"}:
        return None
    if object_type == "blob" and mode == "120000":
        return "SYMLINK"
    return "SPECIAL_PATH"


def range_path_findings(root: Path, baseline: str, candidate: str) -> list[Finding]:
    """Check every path occurrence, even when its blob predates the baseline."""

    findings: list[Finding] = []
    seen: set[tuple[str, str]] = set()
    content_cache: dict[str, bytes] = {}
    for commit in range_commits(root, baseline, candidate):
        for path, object_id, mode, object_type in commit_tree_entries(root, commit):
            for finding in path_secret_findings(path, commit):
                key = (finding.rule, path)
                if key not in seen:
                    findings.append(finding)
                    seen.add(key)
            topology_rule = git_entry_rule(mode, object_type)
            if topology_rule:
                if (topology_rule, path) not in seen:
                    findings.append(Finding(topology_rule, path, commit, 1))
                    seen.add((topology_rule, path))
                continue
            rule = path_rule(path)
            if rule is None and path in PLANNING_RUNTIME_PATHS:
                content = content_cache.setdefault(
                    object_id, git(root, "cat-file", "blob", object_id)
                )
                rule = planning_stub_rule(path, content)
            if rule is None and path in DATA_FIXTURE_DIGESTS:
                content = content_cache.setdefault(
                    object_id, git(root, "cat-file", "blob", object_id)
                )
                rule = data_fixture_rule(path, content)
            if rule is not None and (rule, path) not in seen:
                findings.append(Finding(rule, path, commit, 1))
                seen.add((rule, path))
    return findings


def range_regular_blob_paths(root: Path, baseline: str, candidate: str) -> dict[str, set[str]]:
    """Map blobs to paths only where a range commit stores a regular file."""

    result: dict[str, set[str]] = defaultdict(set)
    for commit in range_commits(root, baseline, candidate):
        for path, object_id, mode, object_type in commit_tree_entries(root, commit):
            if git_entry_rule(mode, object_type) is None:
                result[object_id].add(path)
    return result


def range_commit_object_findings(root: Path, baseline: str, candidate: str) -> list[Finding]:
    """Scan introduced commit metadata/messages without rendering their bytes."""

    findings: list[Finding] = []
    for commit in range_commits(root, baseline, candidate):
        content = git(root, "cat-file", "commit", commit)
        findings.extend(content_findings("<commit-object>", commit, content))
    return findings


def tag_object_findings(root: Path, revision: str) -> list[Finding]:
    """Scan one exact annotated tag object, including its tagger and message."""

    try:
        object_id = resolve_revision_object(root, revision, "TAG_OBJECT")
        object_type = git(root, "cat-file", "-t", object_id).strip()
    except CheckError as error:
        raise CheckError("TAG_OBJECT_INVALID") from error
    if object_type != b"tag":
        raise CheckError("TAG_OBJECT_INVALID")
    _, content = direct_tag_target_commit(root, object_id, "TAG_OBJECT")
    return content_findings("<tag-object>", object_id, content)


def range_findings(root: Path, baseline: str, candidate: str) -> list[Finding]:
    baseline_commit = resolve_commit(root, baseline, "BASELINE")
    candidate_commit = resolve_commit(root, candidate, "CANDIDATE")
    try:
        subprocess.run(
            ("git", "-C", os.fspath(root), "merge-base", "--is-ancestor", baseline_commit, candidate_commit),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
            env=git_environment(),
        )
    except subprocess.CalledProcessError as error:
        raise CheckError("RANGE_NON_ANCESTOR") from error

    findings = range_path_findings(root, baseline_commit, candidate_commit)
    findings.extend(
        range_commit_object_findings(root, baseline_commit, candidate_commit)
    )
    regular_paths = range_regular_blob_paths(root, baseline_commit, candidate_commit)
    for object_id in sorted(range_blobs(root, baseline_commit, candidate_commit)):
        paths = regular_paths.get(object_id, set())
        if not paths:
            continue
        content = git(root, "cat-file", "blob", object_id)
        for path in sorted(paths):
            findings.extend(content_findings(path, candidate_commit, content))
    return findings


def path_class(finding: Finding) -> str:
    """Return a controlled label that cannot reproduce attacker-chosen text."""

    by_rule = {
        "ENV_FILE": "environment",
        "DATA_FIXTURE_MODIFIED": "data-fixture",
        "EVENT_DATA": "event",
        "LOCAL_PROTOCOL_DATA": "local-protocol",
        "PLANNING_RUNTIME_DATA": "planning",
        "PROJECT_RUNTIME_DATA": "project-runtime",
        "RUNTIME_CONTROL_REGISTRY": "runtime-control",
        "SESSION_CONTEXT": "session-context",
        "SYMLINK": "unsafe-topology",
        "SPECIAL_PATH": "unsafe-topology",
        "HARDLINK": "unsafe-topology",
        "UNSAFE_TOPOLOGY": "unsafe-topology",
        "SAFE_TOPOLOGY_UNSUPPORTED": "unsafe-topology",
        "PATH_UNREADABLE": "unsafe-topology",
        "WORK_ITEM_DATA": "work-item",
    }
    if finding.path == "<unattributed-blob>":
        return "unattributed-blob"
    if finding.path in {"<commit-object>", "<tag-object>"}:
        return "git-object"
    return by_rule.get(finding.rule, "repository")


def path_digest(path: str) -> str:
    return hashlib.sha256(path.encode("utf-8", errors="surrogateescape")).hexdigest()


def render(findings: Iterable[Finding]) -> str:
    ordered = sorted(set(findings), key=lambda item: (item.rule, item.path, item.commit))
    if not ordered:
        return "public_release=pass\n"
    lines = ["public_release=fail"]
    for finding in ordered:
        lines.append(
            "failure "
            + json.dumps(
                {
                    "commit": finding.commit,
                    "count": finding.count,
                    "path_class": path_class(finding),
                    "path_sha256": path_digest(finding.path),
                    "rule": finding.rule,
                },
                sort_keys=True,
            )
        )
    return "\n".join(lines) + "\n"


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Read-only public-template boundary and transient-blob checker."
    )
    parser.add_argument("--root", default=".", help="Git worktree to inspect (default: .)")
    parser.add_argument("--baseline", help="Required with --candidate; ancestor commit")
    parser.add_argument("--candidate", help="Required with --baseline; descendant commit")
    parser.add_argument(
        "--tree",
        help="Scan the complete immutable tree at this commit instead of the worktree",
    )
    parser.add_argument(
        "--tag-object",
        help="Additionally scan this exact annotated tag object's metadata and message",
    )
    parser.add_argument(
        "--source-tree",
        action="store_true",
        help="Scan every regular source file, including untracked files, without requiring Git",
    )
    args = parser.parse_args(argv)
    if bool(args.baseline) != bool(args.candidate):
        parser.error("--baseline and --candidate must be supplied together")
    if args.source_tree and (args.baseline or args.tree or args.tag_object):
        parser.error("--source-tree cannot be combined with Git history options")
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    root = Path(args.root).resolve()
    try:
        if not root.is_dir():
            raise CheckError("ROOT_INVALID")
        if args.source_tree:
            findings = current_tree_findings(root, include_untracked=True)
        else:
            git(root, "rev-parse", "--is-inside-work-tree")
            findings = (
                commit_findings(root, args.tree)
                if args.tree
                else current_tree_findings(root)
            )
        if args.baseline and not args.source_tree:
            findings.extend(range_findings(root, args.baseline, args.candidate))
        if args.tag_object and not args.source_tree:
            findings.extend(tag_object_findings(root, args.tag_object))
    except CheckError as error:
        print(f"public_release=error code={error}", file=sys.stderr)
        return 2
    print(render(findings), end="")
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
