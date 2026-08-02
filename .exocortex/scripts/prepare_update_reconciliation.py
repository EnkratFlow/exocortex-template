#!/usr/bin/env python3
"""Prepare and validate an exact, non-mutating update reconciliation plan.

Preparation writes only JSON to stdout. The guarded safe updater imports the
materializer after it has rehearsed the complete effect and consumed a distinct
one-time reconciliation capability.
"""

from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys
from typing import Any, Dict, Iterable, Optional, Sequence


SHA256_RE = re.compile(r"^[a-f0-9]{64}$")
FILE_MODE_RE = re.compile(r"^0(?:644|755)$")
ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,199}$")
SURFACE_PATHS = (
    ".exocortex",
    ".agents",
    ".cursor",
    ".claude",
    ".github",
    ".windsurf",
    "AI_START_HERE.md",
    "AGENTS.md",
    "CLAUDE.md",
    ".cursorrules",
    ".windsurfrules",
    ".rules",
    ".gitignore",
)
PROTECTED_PATHS = (
    ".exocortex/SESSION_CONTEXT.md",
    ".exocortex/SESSION_CONTEXT.md.backup",
    ".exocortex/SESSION_CONTEXT.local.md",
    ".exocortex/TODO.md",
    ".exocortex/LESSONS.md",
    ".exocortex/PROJECT_MEMORY.md",
    ".exocortex/OPEN_DECISIONS.md",
    ".exocortex/subconscious_patterns.md",
    ".exocortex/.env",
    ".exocortex/.project-name",
    ".exocortex/events",
    ".exocortex/archive",
    ".exocortex/hub",
    ".exocortex/local",
    ".exocortex/planning",
    ".exocortex/work-items",
    ".exocortex/control/ACTIVE_WORK.md",
    ".exocortex/control/BRANCH_POLICY.md",
    ".exocortex/control/REPO_STATE.md",
    ".exocortex/control/EXECUTOR_REGISTRY.json",
    ".exocortex/control/EXTERNAL_SYNC_POLICY.json",
    ".exocortex/control/INTERRUPTS.md",
    ".exocortex/control/BACKLOG.md",
    ".exocortex/control/ROADMAP.md",
    ".exocortex/control/ARCH_OVERVIEW.md",
    ".exocortex/control/REPO_ORGANIZATION_REPORT.md",
    ".exocortex/.hub_enabled",
    ".exocortex/.hub_disabled",
)
LEGACY_SESSION_CONTEXT_BACKUP_PREFIX = ".exocortex/SESSION_CONTEXT_BACKUP_"
REVIEWED_OBJECT_PREFIX = ".exocortex/local/update-reconciliation/objects/"
# Protected project data is preserved and verified separately by safe-update.
# It is not part of the mutable template code-plane surface. In particular, a
# reviewed plan stored under .exocortex/local must not invalidate itself.
BOUNDARIES = {
    "commit": False,
    "push": False,
    "deployment": False,
    "external_sync": False,
    "template_promotion": False,
}


class ReconciliationError(RuntimeError):
    """Stable validation error for a reconciliation plan."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def digest_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def file_digest(path: Path) -> str:
    return digest_bytes(path.read_bytes())


def normalized_file_mode(path: Path, label: str) -> str:
    mode = stat.S_IMODE(path.stat().st_mode)
    value = f"{mode:04o}"
    if FILE_MODE_RE.fullmatch(value) is None:
        raise ReconciliationError("invalid_file_mode", f"{label} must use normalized mode 0644 or 0755")
    return value


def path_list_bytes(paths: Iterable[str]) -> bytes:
    return "".join(f"{path}\n" for path in paths).encode("utf-8")


def path_list_digest(paths: Iterable[str]) -> str:
    return digest_bytes(path_list_bytes(paths))


def exact_keys(value: Dict[str, Any], required: Iterable[str], label: str) -> None:
    required_set = set(required)
    missing = sorted(required_set - set(value))
    extra = sorted(set(value) - required_set)
    if missing:
        raise ReconciliationError("missing_field", f"{label} is missing field: {missing[0]}")
    if extra:
        raise ReconciliationError("unexpected_field", f"{label} contains unexpected field: {extra[0]}")


def require_sha(value: object, label: str) -> str:
    if not isinstance(value, str) or SHA256_RE.fullmatch(value) is None:
        raise ReconciliationError("invalid_sha256", f"{label} must be a lowercase SHA-256 digest")
    return value


def require_id(value: object, label: str) -> str:
    if not isinstance(value, str) or ID_RE.fullmatch(value) is None:
        raise ReconciliationError("invalid_id", f"{label} is not a stable identifier")
    return value


def require_timestamp(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ReconciliationError("invalid_timestamp", f"{label} must be a UTC timestamp ending in Z")
    try:
        datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ReconciliationError("invalid_timestamp", f"{label} is invalid") from exc
    return value


def canonical_relative_path(value: object, label: str = "path") -> str:
    if not isinstance(value, str) or not value or value.startswith("/") or "\x00" in value:
        raise ReconciliationError("invalid_path", f"{label} must be a project-relative path")
    path = PurePosixPath(value)
    if value != path.as_posix() or any(part in {"", ".", ".."} for part in path.parts):
        raise ReconciliationError("invalid_path", f"{label} must be canonical and traversal-free")
    return value


def is_under(path: str, parent: str) -> bool:
    return path == parent or path.startswith(parent + "/")


def is_legacy_session_context_backup(path: str) -> bool:
    """Return whether path is the direct legacy session-backup filename family."""
    if not path.startswith(LEGACY_SESSION_CONTEXT_BACKUP_PREFIX) or not path.endswith(".md"):
        return False
    return "/" not in path[len(LEGACY_SESSION_CONTEXT_BACKUP_PREFIX) :]


def is_runtime_state(path: str) -> bool:
    # Editor session worktrees are runtime state at any depth, never part of
    # the template surface; safe-update.sh applies the identical exclusion.
    parts = path.split("/")
    return any(
        parts[index] == ".claude" and parts[index + 1] == "worktrees"
        for index in range(len(parts) - 1)
    )


def is_surface_path(path: str) -> bool:
    return any(is_under(path, surface) for surface in SURFACE_PATHS)


def is_protected_path(path: str) -> bool:
    return is_legacy_session_context_backup(path) or any(
        is_under(path, protected) for protected in PROTECTED_PATHS
    )


def require_safe_effect_path(path: object) -> str:
    value = canonical_relative_path(path, "effect path")
    if not is_surface_path(value):
        raise ReconciliationError("outside_update_surface", f"effect path is outside the update surface: {value}")
    if is_protected_path(value):
        raise ReconciliationError("protected_path", f"reconciliation cannot mutate protected path: {value}")
    return value


def resolve_root(path: Path, label: str) -> Path:
    try:
        resolved = path.resolve(strict=True)
    except OSError as exc:
        raise ReconciliationError("invalid_root", f"{label} is unavailable") from exc
    if not resolved.is_dir():
        raise ReconciliationError("invalid_root", f"{label} must be a directory")
    return resolved


def resolve_file(root: Path, relative: str, label: str, *, allow_absent: bool = False) -> Optional[Path]:
    relative = canonical_relative_path(relative, label)
    candidate = root / relative
    cursor = root
    for part in PurePosixPath(relative).parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise ReconciliationError("invalid_path_type", f"{label} contains a symlink: {relative}")
        if not cursor.exists():
            break
    try:
        resolved = candidate.resolve(strict=not allow_absent)
    except OSError as exc:
        if allow_absent and not candidate.exists() and not candidate.is_symlink():
            return None
        raise ReconciliationError("invalid_path", f"{label} is unavailable: {relative}") from exc
    if allow_absent and not candidate.exists() and not candidate.is_symlink():
        return None
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ReconciliationError("path_escape", f"{label} escapes its root: {relative}") from exc
    if candidate.is_symlink() or not resolved.is_file():
        raise ReconciliationError("invalid_path_type", f"{label} must be a regular non-symlink file: {relative}")
    return resolved


def resolve_absolute_nonsymlink_file(path: Path, label: str) -> Path:
    if not path.is_absolute():
        raise ReconciliationError("invalid_path", f"{label} must be absolute")
    if path.is_symlink():
        raise ReconciliationError("invalid_path_type", f"{label} must not be a symlink")
    try:
        resolved = path.resolve(strict=True)
    except OSError as exc:
        raise ReconciliationError("invalid_path", f"{label} is unavailable") from exc
    if not resolved.is_file():
        raise ReconciliationError("invalid_path_type", f"{label} must be a regular file")
    return resolved


def regular_file_digest_or_none(root: Path, relative: str, label: str) -> Optional[str]:
    path = resolve_file(root, relative, label, allow_absent=True)
    return None if path is None else file_digest(path)


def checksum_map(template: Path, candidate_digest: str) -> Dict[str, str]:
    sums = resolve_file(template, "SHA256SUMS", "candidate checksum inventory")
    assert sums is not None
    if file_digest(sums) != candidate_digest:
        raise ReconciliationError("candidate_digest_mismatch", "template SHA256SUMS does not match candidate_digest")
    result: Dict[str, str] = {}
    for line in sums.read_text(encoding="utf-8").splitlines():
        if not re.fullmatch(r"[a-f0-9]{64}  [^/].*", line):
            raise ReconciliationError("invalid_checksum_inventory", "candidate SHA256SUMS contains a malformed entry")
        digest, relative = line[:64], line[66:]
        relative = canonical_relative_path(relative, "checksum path")
        if relative in result:
            raise ReconciliationError("invalid_checksum_inventory", f"duplicate checksum path: {relative}")
        source = resolve_file(template, relative, "checksum-listed candidate file")
        assert source is not None
        if file_digest(source) != digest:
            raise ReconciliationError("candidate_checksum_mismatch", f"candidate checksum mismatch: {relative}")
        result[relative] = digest
    if list(result) != sorted(result):
        raise ReconciliationError("invalid_checksum_inventory", "candidate SHA256SUMS paths must be sorted")
    return result


def candidate_mode_map(template: Path, checksums: Dict[str, str]) -> Dict[str, str]:
    modes = resolve_file(template, "FILEMODES", "candidate file-mode inventory")
    assert modes is not None
    if checksums.get("FILEMODES") != file_digest(modes):
        raise ReconciliationError("candidate_mode_inventory_mismatch", "FILEMODES is not checksum-bound")
    records: Dict[str, str] = {}
    paths: list[str] = []
    for line in modes.read_text(encoding="utf-8").splitlines():
        match = re.fullmatch(r"(0(?:644|755))  ([^/].*)", line)
        if match is None:
            raise ReconciliationError("invalid_mode_inventory", "candidate FILEMODES contains a malformed entry")
        mode, relative = match.groups()
        relative = canonical_relative_path(relative, "file-mode path")
        if relative in records:
            raise ReconciliationError("invalid_mode_inventory", f"duplicate file-mode path: {relative}")
        records[relative] = mode
        paths.append(relative)
    expected_paths = set(checksums) | {"SHA256SUMS"}
    if paths != sorted(paths) or set(records) != expected_paths:
        raise ReconciliationError(
            "invalid_mode_inventory",
            "FILEMODES must bind the sorted checksum paths plus SHA256SUMS",
        )
    for relative in paths:
        source = resolve_file(template, relative, "file-mode-bound candidate file")
        assert source is not None
        if normalized_file_mode(source, f"candidate file {relative}") != records[relative]:
            raise ReconciliationError("candidate_mode_mismatch", f"candidate file mode mismatch: {relative}")
    return records


def inventory_digest(root: Path) -> str:
    def directory_record(path: Path, relative: str) -> str:
        value = os.lstat(path)
        return f"dir:{stat.S_IMODE(value.st_mode):04o}"

    def file_record(path: Path) -> str:
        value = os.lstat(path)
        return f"file:{stat.S_IMODE(value.st_mode):04o}:{value.st_nlink}:" + file_digest(path)

    def symlink_record(path: Path) -> str:
        value = os.lstat(path)
        return (
            f"symlink:{stat.S_IMODE(value.st_mode):04o}:{value.st_nlink}:"
            + os.readlink(path)
        )

    records: Dict[str, str] = {}
    for relative in SURFACE_PATHS:
        base = root / relative
        if base.is_symlink():
            records[relative] = symlink_record(base)
        elif base.is_file():
            records[relative] = file_record(base)
        elif base.is_dir():
            records[relative] = directory_record(base, relative)
            for dirpath, dirnames, filenames in os.walk(base, followlinks=False):
                dirnames.sort()
                filenames.sort()
                here = Path(dirpath)
                here_relative = here.relative_to(root).as_posix()
                if is_runtime_state(here_relative) or is_protected_path(here_relative):
                    dirnames[:] = []
                    continue
                for name in list(dirnames):
                    path = here / name
                    child = path.relative_to(root).as_posix()
                    if is_runtime_state(child) or is_protected_path(child):
                        continue
                    if path.is_symlink():
                        records[child] = symlink_record(path)
                    else:
                        records[child] = directory_record(path, child)
                dirnames[:] = [
                    name
                    for name in dirnames
                    if not (here / name).is_symlink()
                    and not is_runtime_state((here / name).relative_to(root).as_posix())
                    and not is_protected_path((here / name).relative_to(root).as_posix())
                ]
                for name in filenames:
                    path = here / name
                    child = path.relative_to(root).as_posix()
                    if is_runtime_state(child) or is_protected_path(child):
                        continue
                    if path.is_symlink():
                        records[child] = symlink_record(path)
                    elif path.is_file():
                        records[child] = file_record(path)
        else:
            records[relative] = "absent"
    digest = hashlib.sha256()
    for relative, value in sorted(records.items()):
        digest.update(relative.encode("utf-8") + b"\0" + value.encode("utf-8") + b"\0")
    return digest.hexdigest()


def load_path_list(path: Path) -> list[str]:
    try:
        values = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as exc:
        raise ReconciliationError("invalid_path_list", "standard changed-path list is unavailable") from exc
    for value in values:
        require_safe_effect_path(value)
    if values != sorted(set(values)):
        raise ReconciliationError("invalid_path_list", "standard changed-path list must be sorted and unique")
    return values


def reject_duplicate_keys(pairs: Sequence[tuple[str, Any]]) -> Dict[str, Any]:
    result: Dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ReconciliationError("duplicate_json_key", f"duplicate reconciliation plan key: {key}")
        result[key] = value
    return result


def parse_plan_bytes(raw: bytes) -> Dict[str, Any]:
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=reject_duplicate_keys)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ReconciliationError("invalid_plan_json", "reconciliation plan is invalid JSON") from exc
    if not isinstance(value, dict):
        raise ReconciliationError("invalid_plan_json", "reconciliation plan root must be an object")
    return value


def load_plan(path: Path) -> Dict[str, Any]:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise ReconciliationError("invalid_plan_json", "reconciliation plan is unavailable") from exc
    return parse_plan_bytes(raw)


def validate_plan(
    document: Dict[str, Any],
    *,
    target: Path,
    template: Path,
    candidate_digest: str,
    require_current_target: bool = True,
) -> Dict[str, Any]:
    target = resolve_root(target, "target root")
    template = resolve_root(template, "template root")
    require_sha(candidate_digest, "candidate_digest")
    checksums = checksum_map(template, candidate_digest)
    modes = candidate_mode_map(template, checksums)
    exact_keys(
        document,
        (
            "schema_version",
            "kind",
            "plan_id",
            "work_item",
            "candidate_digest",
            "target_surface_digest",
            "created_at",
            "standard_update_changed_paths",
            "standard_update_changed_paths_digest",
            "entries",
            "effect_paths",
            "effect_paths_digest",
            "boundaries",
        ),
        "reconciliation plan",
    )
    if document["schema_version"] != "public-v2" or document["kind"] != "update_reconciliation_plan":
        raise ReconciliationError("wrong_schema", "plan must use public-v2 update_reconciliation_plan")
    require_id(document["plan_id"], "plan_id")
    if not isinstance(document["work_item"], dict):
        raise ReconciliationError("invalid_work_item", "work_item must be an object")
    exact_keys(document["work_item"], ("id", "revision"), "plan work_item")
    require_id(document["work_item"]["id"], "work_item id")
    revision = document["work_item"]["revision"]
    if not isinstance(revision, int) or isinstance(revision, bool) or revision < 0:
        raise ReconciliationError("invalid_revision", "work_item revision must be non-negative")
    if document["candidate_digest"] != candidate_digest:
        raise ReconciliationError("candidate_digest_mismatch", "plan candidate_digest does not match the supplied candidate")
    require_sha(document["target_surface_digest"], "target_surface_digest")
    require_timestamp(document["created_at"], "created_at")
    if require_current_target and inventory_digest(target) != document["target_surface_digest"]:
        raise ReconciliationError("target_surface_drift", "target surface changed after reconciliation planning")
    if document["boundaries"] != BOUNDARIES:
        raise ReconciliationError("invalid_boundaries", "reconciliation plan must preserve all outward-action boundaries")

    standard_paths = document["standard_update_changed_paths"]
    if not isinstance(standard_paths, list):
        raise ReconciliationError("invalid_path_list", "standard_update_changed_paths must be an array")
    standard_paths = [require_safe_effect_path(path) for path in standard_paths]
    if standard_paths != sorted(set(standard_paths)):
        raise ReconciliationError("invalid_path_list", "standard_update_changed_paths must be sorted and unique")
    if document["standard_update_changed_paths_digest"] != path_list_digest(standard_paths):
        raise ReconciliationError("path_digest_mismatch", "standard update changed-path digest is invalid")

    entries = document["entries"]
    if not isinstance(entries, list) or not entries:
        raise ReconciliationError("invalid_entries", "reconciliation entries must not be empty")
    entry_paths: list[str] = []
    for entry in entries:
        if not isinstance(entry, dict):
            raise ReconciliationError("invalid_entry", "reconciliation entries must be objects")
        exact_keys(
            entry,
            (
                "path",
                "action",
                "current_sha256",
                "candidate_sha256",
                "object_path",
                "object_sha256",
                "expected_mode",
            ),
            "reconciliation entry",
        )
        path = require_safe_effect_path(entry["path"])
        entry_paths.append(path)
        current = regular_file_digest_or_none(target, path, "target effect path")
        if entry["current_sha256"] is not None:
            require_sha(entry["current_sha256"], "entry current_sha256")
        if require_current_target and current != entry["current_sha256"]:
            raise ReconciliationError("target_path_drift", f"target path changed after planning: {path}")
        action = entry["action"]
        if action == "adopt_candidate":
            if entry["object_path"] is not None or entry["object_sha256"] is not None:
                raise ReconciliationError("invalid_entry_binding", f"candidate adoption cannot reference an object: {path}")
            candidate_sha = require_sha(entry["candidate_sha256"], "entry candidate_sha256")
            if checksums.get(path) != candidate_sha:
                raise ReconciliationError("candidate_path_mismatch", f"candidate adoption is not checksum-bound: {path}")
            if entry["expected_mode"] != modes.get(path):
                raise ReconciliationError("candidate_mode_mismatch", f"candidate adoption mode is not bound: {path}")
        elif action == "use_reviewed_object":
            if entry["candidate_sha256"] is not None:
                raise ReconciliationError("invalid_entry_binding", f"reviewed object cannot claim candidate bytes: {path}")
            object_path = canonical_relative_path(entry["object_path"], "reviewed object path")
            if not object_path.startswith(REVIEWED_OBJECT_PREFIX):
                raise ReconciliationError("unsafe_reviewed_object", "reviewed objects must live under protected local reconciliation state")
            object_sha = require_sha(entry["object_sha256"], "reviewed object_sha256")
            source = resolve_file(target, object_path, "reviewed object")
            assert source is not None
            if file_digest(source) != object_sha:
                raise ReconciliationError("reviewed_object_mismatch", f"reviewed object digest mismatch: {object_path}")
            if entry["expected_mode"] != normalized_file_mode(source, f"reviewed object {object_path}"):
                raise ReconciliationError("reviewed_object_mode_mismatch", f"reviewed object mode mismatch: {object_path}")
        elif action == "retire_target":
            if any(
                entry[field] is not None
                for field in ("candidate_sha256", "object_path", "object_sha256", "expected_mode")
            ):
                raise ReconciliationError("invalid_entry_binding", f"retirement cannot reference replacement bytes: {path}")
            if path in checksums or (template / path).exists():
                raise ReconciliationError("unsafe_retirement", f"retirement path is still present in the candidate: {path}")
            if entry["current_sha256"] is None:
                raise ReconciliationError("missing_retirement_target", f"retirement target is already absent: {path}")
        else:
            raise ReconciliationError("invalid_action", f"unsupported reconciliation action: {action}")
    if entry_paths != sorted(set(entry_paths)):
        raise ReconciliationError("invalid_entries", "reconciliation entry paths must be sorted and unique")

    effect_paths = document["effect_paths"]
    if not isinstance(effect_paths, list):
        raise ReconciliationError("invalid_path_list", "effect_paths must be an array")
    effect_paths = [require_safe_effect_path(path) for path in effect_paths]
    expected_effect = sorted(set(standard_paths) | set(entry_paths))
    if effect_paths != expected_effect:
        raise ReconciliationError("effect_path_mismatch", "effect_paths must equal the standard and reconciliation path union")
    if document["effect_paths_digest"] != path_list_digest(effect_paths):
        raise ReconciliationError("path_digest_mismatch", "effect_paths_digest is invalid")
    return document


def build_entry(
    target: Path,
    template: Path,
    checksums: Dict[str, str],
    modes: Dict[str, str],
    action: str,
    path: str,
    object_path: Optional[str],
) -> Dict[str, Any]:
    path = require_safe_effect_path(path)
    current = regular_file_digest_or_none(target, path, "target effect path")
    entry: Dict[str, Any] = {
        "path": path,
        "action": action,
        "current_sha256": current,
        "candidate_sha256": None,
        "object_path": None,
        "object_sha256": None,
        "expected_mode": None,
    }
    if action == "adopt_candidate":
        candidate_sha = checksums.get(path)
        if candidate_sha is None:
            raise ReconciliationError("candidate_path_mismatch", f"candidate does not contain checksum-listed path: {path}")
        entry["candidate_sha256"] = candidate_sha
        entry["expected_mode"] = modes[path]
    elif action == "use_reviewed_object":
        if object_path is None:
            raise ReconciliationError("missing_reviewed_object", f"reviewed object is required: {path}")
        object_path = canonical_relative_path(object_path, "reviewed object path")
        if not object_path.startswith(REVIEWED_OBJECT_PREFIX):
            raise ReconciliationError("unsafe_reviewed_object", "reviewed objects must live under protected local reconciliation state")
        source = resolve_file(target, object_path, "reviewed object")
        assert source is not None
        entry["object_path"] = object_path
        entry["object_sha256"] = file_digest(source)
        entry["expected_mode"] = normalized_file_mode(source, f"reviewed object {object_path}")
    elif action == "retire_target":
        if current is None:
            raise ReconciliationError("missing_retirement_target", f"retirement target is absent: {path}")
        if path in checksums or (template / path).exists():
            raise ReconciliationError("unsafe_retirement", f"retirement path is still present in the candidate: {path}")
    return entry


def prepare_plan(args: argparse.Namespace) -> Dict[str, Any]:
    target = resolve_root(args.target, "target root")
    template = resolve_root(args.template, "template root")
    candidate_digest = require_sha(args.candidate_digest, "candidate_digest")
    checksums = checksum_map(template, candidate_digest)
    modes = candidate_mode_map(template, checksums)
    standard_paths = load_path_list(args.standard_changed_paths)
    requested: Dict[str, tuple[str, Optional[str]]] = {}
    for path in args.adopt:
        path = require_safe_effect_path(path)
        if path in requested:
            raise ReconciliationError("duplicate_entry", f"duplicate reconciliation path: {path}")
        requested[path] = ("adopt_candidate", None)
    for path in args.retire:
        path = require_safe_effect_path(path)
        if path in requested:
            raise ReconciliationError("duplicate_entry", f"duplicate reconciliation path: {path}")
        requested[path] = ("retire_target", None)
    for spec in args.reviewed:
        if "=" not in spec:
            raise ReconciliationError("invalid_reviewed_spec", "--reviewed must use EFFECT_PATH=OBJECT_PATH")
        path, object_path = spec.split("=", 1)
        path = require_safe_effect_path(path)
        if path in requested:
            raise ReconciliationError("duplicate_entry", f"duplicate reconciliation path: {path}")
        requested[path] = ("use_reviewed_object", object_path)
    if not requested:
        raise ReconciliationError("empty_reconciliation", "at least one reconciliation entry is required")
    entries = [
        build_entry(target, template, checksums, modes, action, path, object_path)
        for path, (action, object_path) in sorted(requested.items())
    ]
    effect_paths = sorted(set(standard_paths) | set(requested))
    document = {
        "schema_version": "public-v2",
        "kind": "update_reconciliation_plan",
        "plan_id": require_id(args.plan_id, "plan_id"),
        "work_item": {
            "id": require_id(args.work_item_id, "work_item id"),
            "revision": args.work_item_revision,
        },
        "candidate_digest": candidate_digest,
        "target_surface_digest": inventory_digest(target),
        "created_at": require_timestamp(args.created_at, "created_at"),
        "standard_update_changed_paths": standard_paths,
        "standard_update_changed_paths_digest": path_list_digest(standard_paths),
        "entries": entries,
        "effect_paths": effect_paths,
        "effect_paths_digest": path_list_digest(effect_paths),
        "boundaries": dict(BOUNDARIES),
    }
    return validate_plan(document, target=target, template=template, candidate_digest=candidate_digest)


def ensure_destination_parent(root: Path, relative: str) -> Path:
    destination = root / relative
    current = root
    for part in PurePosixPath(relative).parts[:-1]:
        current = current / part
        if current.is_symlink():
            raise ReconciliationError("target_symlink", f"destination parent contains a symlink: {relative}")
        if current.exists() and not current.is_dir():
            raise ReconciliationError("target_path_type", f"destination parent is not a directory: {relative}")
        current.mkdir(exist_ok=True)
    if destination.is_symlink() or (destination.exists() and not destination.is_file()):
        raise ReconciliationError("target_path_type", f"destination is not a regular file: {relative}")
    try:
        destination.parent.resolve(strict=True).relative_to(root)
    except (OSError, ValueError) as exc:
        raise ReconciliationError("path_escape", f"destination escapes target root: {relative}") from exc
    return destination


def atomic_copy(source: Path, destination: Path, expected_mode: str, expected_digest: str) -> None:
    if not isinstance(expected_mode, str) or FILE_MODE_RE.fullmatch(expected_mode) is None:
        raise ReconciliationError("invalid_file_mode", "materialization mode must be 0644 or 0755")
    require_sha(expected_digest, "materialization source digest")
    temporary = destination.with_name(f".{destination.name}.exocortex-reconcile-{os.getpid()}.tmp")
    if temporary.exists() or temporary.is_symlink():
        raise ReconciliationError("temporary_collision", f"temporary reconciliation path already exists: {destination.name}")
    try:
        with source.open("rb") as reader, temporary.open("xb") as writer:
            source_mode = f"{stat.S_IMODE(os.fstat(reader.fileno()).st_mode):04o}"
            if source_mode != expected_mode:
                raise ReconciliationError("source_mode_mismatch", "materialization source mode changed after planning")
            copied_digest = hashlib.sha256()
            while True:
                chunk = reader.read(1024 * 1024)
                if not chunk:
                    break
                copied_digest.update(chunk)
                writer.write(chunk)
            if copied_digest.hexdigest() != expected_digest:
                raise ReconciliationError(
                    "source_digest_mismatch",
                    "materialization source bytes changed after planning",
                )
            os.fchmod(writer.fileno(), int(expected_mode, 8))
            writer.flush()
            os.fsync(writer.fileno())
        os.replace(temporary, destination)
        if normalized_file_mode(destination, "materialized destination") != expected_mode:
            raise ReconciliationError("destination_mode_mismatch", "materialized destination mode is incorrect")
        directory_fd = os.open(destination.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        if temporary.exists() and not temporary.is_symlink():
            temporary.unlink()


def materialize_plan(
    document: Dict[str, Any],
    *,
    destination_root: Path,
    template: Path,
    baseline_target: Path,
) -> None:
    """Apply prevalidated exact bytes to a rehearsal or guarded live target."""
    destination_root = resolve_root(destination_root, "materialization destination")
    template = resolve_root(template, "template root")
    baseline_target = resolve_root(baseline_target, "baseline target")
    checksums = checksum_map(template, document["candidate_digest"])
    modes = candidate_mode_map(template, checksums)
    for entry in document["entries"]:
        relative = entry["path"]
        action = entry["action"]
        if action == "retire_target":
            destination = destination_root / relative
            if destination.is_symlink() or (destination.exists() and not destination.is_file()):
                raise ReconciliationError("target_path_type", f"retirement destination is not a regular file: {relative}")
            if destination.exists():
                if file_digest(destination) != entry["current_sha256"]:
                    raise ReconciliationError(
                        "target_path_drift",
                        f"retirement target changed after planning: {relative}",
                    )
                destination.unlink()
                directory_fd = os.open(destination.parent, os.O_RDONLY)
                try:
                    os.fsync(directory_fd)
                finally:
                    os.close(directory_fd)
            continue
        destination = ensure_destination_parent(destination_root, relative)
        if action == "adopt_candidate":
            source = resolve_file(template, relative, "candidate adoption source")
            assert source is not None
            if file_digest(source) != checksums[relative] or checksums[relative] != entry["candidate_sha256"]:
                raise ReconciliationError("candidate_path_mismatch", f"candidate adoption source changed: {relative}")
            if modes.get(relative) != entry["expected_mode"]:
                raise ReconciliationError("candidate_mode_mismatch", f"candidate adoption mode changed: {relative}")
        elif action == "use_reviewed_object":
            source = resolve_file(baseline_target, entry["object_path"], "reviewed object")
            assert source is not None
            if file_digest(source) != entry["object_sha256"]:
                raise ReconciliationError("reviewed_object_mismatch", f"reviewed object changed: {entry['object_path']}")
        else:
            raise ReconciliationError("invalid_action", f"unsupported reconciliation action: {action}")
        expected_digest = (
            entry["candidate_sha256"]
            if action == "adopt_candidate"
            else entry["object_sha256"]
        )
        atomic_copy(source, destination, entry["expected_mode"], expected_digest)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    prepare = commands.add_parser("prepare")
    prepare.add_argument("--target", type=Path, required=True)
    prepare.add_argument("--template", type=Path, required=True)
    prepare.add_argument("--candidate-digest", required=True)
    prepare.add_argument("--plan-id", required=True)
    prepare.add_argument("--work-item-id", required=True)
    prepare.add_argument("--work-item-revision", type=int, required=True)
    prepare.add_argument("--created-at", required=True)
    prepare.add_argument("--standard-changed-paths", type=Path, required=True)
    prepare.add_argument("--adopt", action="append", default=[])
    prepare.add_argument("--retire", action="append", default=[])
    prepare.add_argument("--reviewed", action="append", default=[])

    validate = commands.add_parser("validate")
    validate.add_argument("--target", type=Path, required=True)
    validate.add_argument("--template", type=Path, required=True)
    validate.add_argument("--candidate-digest", required=True)
    validate.add_argument("--plan", type=Path, required=True)
    validate.add_argument("--expected-work-item-id")
    validate.add_argument("--expected-work-item-revision", type=int)
    validate.add_argument("--emit", choices=("json", "plan-digest", "effect-paths"), default="json")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "prepare":
            if args.work_item_revision < 0:
                raise ReconciliationError("invalid_revision", "work_item revision must be non-negative")
            result = prepare_plan(args)
            print(json.dumps(result, indent=2, sort_keys=True))
        else:
            target = resolve_root(args.target, "target root")
            template = resolve_root(args.template, "template root")
            plan_path = resolve_absolute_nonsymlink_file(args.plan, "reconciliation plan")
            result = validate_plan(
                load_plan(plan_path),
                target=target,
                template=template,
                candidate_digest=args.candidate_digest,
            )
            if args.expected_work_item_id is not None and result["work_item"]["id"] != args.expected_work_item_id:
                raise ReconciliationError("work_item_mismatch", "plan work_item id does not match apply authority")
            if (
                args.expected_work_item_revision is not None
                and result["work_item"]["revision"] != args.expected_work_item_revision
            ):
                raise ReconciliationError("work_item_mismatch", "plan work_item revision does not match apply authority")
            if args.emit == "plan-digest":
                print(file_digest(plan_path))
            elif args.emit == "effect-paths":
                sys.stdout.buffer.write(path_list_bytes(result["effect_paths"]))
            else:
                print(
                    json.dumps(
                        {
                            "ok": True,
                            "plan_id": result["plan_id"],
                            "plan_digest": file_digest(plan_path),
                            "effect_paths": result["effect_paths"],
                            "effect_paths_digest": result["effect_paths_digest"],
                            "operation": "apply_template_reconciliation",
                            "mutation_permitted": False,
                        },
                        sort_keys=True,
                    )
                )
        return 0
    except (OSError, ReconciliationError) as exc:
        if isinstance(exc, ReconciliationError):
            code, message = exc.code, exc.message
        else:
            code, message = "io_error", "reconciliation evidence could not be read safely"
        print(json.dumps({"ok": False, "code": code, "message": message}, sort_keys=True))
        return 2


if __name__ == "__main__":
    sys.exit(main())
