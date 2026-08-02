#!/usr/bin/env python3
"""Deterministic contract checks for active installation documentation."""

from __future__ import annotations

import json
import re
import stat
import sys
from pathlib import Path


ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
FAILURES: list[str] = []


def read(relative: str) -> str:
    path = ROOT / relative
    if not path.is_file():
        FAILURES.append(f"missing required documentation: {relative}")
        return ""
    return path.read_text(encoding="utf-8")


def require(relative: str, *needles: str) -> None:
    text = read(relative)
    for needle in needles:
        if needle not in text:
            FAILURES.append(f"{relative}: missing required text: {needle}")


def require_compact(relative: str, *needles: str) -> None:
    text = " ".join(read(relative).split())
    for needle in needles:
        compact_needle = " ".join(needle.split())
        if compact_needle not in text:
            FAILURES.append(
                f"{relative}: missing required normalized text: {compact_needle}"
            )


def forbid(relative: str, *patterns: str) -> None:
    text = read(relative)
    for pattern in patterns:
        if re.search(pattern, text, flags=re.IGNORECASE | re.MULTILINE):
            FAILURES.append(f"{relative}: forbidden active guidance matched: {pattern}")


PACKAGED_VERSION = read("VERSION").strip()
if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", PACKAGED_VERSION):
    FAILURES.append(f"VERSION: expected SemVer, found {PACKAGED_VERSION!r}")


require(
    ".exocortex/docs/AI_INSTALLATION.md",
    "Copy-paste prompt: clean installation",
    "Copy-paste prompt: existing-repository update",
    "Guarded apply contract",
    "Human-facing installation decisions",
    "Internal cooperative authority mechanics",
    ".exocortex/schemas/orchestration.schema.json",
    ".exocortex/schemas/executor-registry.schema.json",
    ".exocortex/schemas/authorization.schema.json",
    "orchestrate_work_item.py",
    "reserve",
    "Complete disposable update evidence",
    "Legacy protected-default preflight",
    "missing-default bootstrap",
    "never overwrite an existing",
    "non-following path metadata",
    "real regular file, never a symlink",
    "`ensure_data_stubs` function",
    "project-specific value must be supplied and approved",
    "`.exocortex/events` and `.exocortex/control`",
    "one --dry-run does not apply the update",
    "WSL evidence required before support",
    "GitHub is a later gate",
    "Bash 3.2+, Python 3.9+, `shasum` or\n`sha256sum`",
    "`mkdir`, `rm`, `basename`, `dirname`, `cat`",
    "Unix-only `fcntl` module",
    "record mechanics are internal",
    "Native Windows PowerShell or Command Prompt",
    "human_uat_pending",
    "disposable-rehearsal decision",
    "inventories only the manifest-defined install surfaces",
    "controlled write failure",
    "shared or primary checkout",
    "rollback boundary is therefore isolation",
    "not separate human decisions",
    "changed-path list is not final",
    "mandatory post-bootstrap dry",
    "Never edit the lane",
    "The orchestrator alone",
    "capability is consumed",
    "remains consumed and cannot be replayed",
    "internally materialize the current",
    "separate disposable fault fixtures",
    "--capability <project-relative-capability-path>",
    "--work-item-revision <exact-current-revision>",
    "Never read or display .env or credential values",
    "Target-specific reconciliation contract",
    "apply_template_reconciliation",
    "`scope.payload_digest`",
    "Protected project data is excluded from that digest and verified separately",
    "duplicate JSON keys",
    "An `apply_template_update` capability cannot authorize this",
    "checksum-bound `FILEMODES`",
    "expected `0644`/`0755` mode",
    "unique private `0600` code-plane-only",
    "all `.exocortex/local` authority and evidence paths",
    "one `publication` decision",
    "simple accept or reject",
    "Existing Git-tracked backup sidecars",
    "Git-ignore rules affect only files Git does not\nalready track",
    "EXOCORTEX_TRACKED_PROTECTED_SIDECAR",
    "EXOCORTEX_TRACKED_LEGACY_SESSION_CONTEXT_BACKUP",
    "SESSION_CONTEXT_BACKUP_*.md",
    "never\nperform it automatically",
)
require(
    "README.md",
    "Install with a coding AI",
    ".exocortex/docs/AI_INSTALLATION.md",
    "compatible_pending_candidate_CI",
    "human_uat_pending",
    "Git Bash or native Windows PowerShell/Command Prompt",
    "Private staging remains beneath `${TMPDIR:-/tmp}`",
    "metadata-only protected-default",
    "clean isolated Git worktree",
    "shared or primary checkout",
    "HOME=<absolute-disposable-home>",
    "Source-backed model freshness",
    "zero route-eligible models",
    "apply_template_reconciliation",
    "`FILEMODES` is checksum-bound",
    "collision-resistant `0600` code-plane-only restore archive",
    "external hard-linked mutable files",
    "exact prior code plane before durable publication",
    "Customized bytes or modes",
    "complete non-protected code plane",
    "four business-level envelopes",
    "not separate human approvals",
    f"--branch v{PACKAGED_VERSION}",
    f"exocortex-template-v{PACKAGED_VERSION}",
    "EXOCORTEX_COMMAND_AUTHORITY_COLLISION_PRESERVED",
    "EXOCORTEX_COMMAND_RECONCILIATION_REQUIRED",
    "Git-ignore rules cannot untrack it",
    "SESSION_CONTEXT_BACKUP_*.md",
)
require(
    ".exocortex/docs/AI_INSTALLATION.md",
    f"--branch v{PACKAGED_VERSION}",
    f"exocortex-template-v{PACKAGED_VERSION}",
    "EXOCORTEX_COMMAND_AUTHORITY_COLLISION_PRESERVED",
    "EXOCORTEX_STALE_COMMAND_GUIDANCE_PRESERVED",
    "EXOCORTEX_COMMAND_RECONCILIATION_REQUIRED",
)
require_compact(
    ".exocortex/docs/AI_INSTALLATION.md",
    "peeled 40-character commit SHA",
)
for command_authority_doc in (
    "AI_START_HERE.md",
    ".exocortex/AI_BOOTSTRAP.md",
    ".exocortex/COMMAND_SYSTEM.md",
    "CLAUDE.md",
    "AGENTS.md",
):
    require_compact(
        command_authority_doc,
        "sole command-flow behavior source",
        "without combining",
    )
require(
    "AI_START_HERE.md",
    "Use four human-facing gate classes",
    "`local_delivery`",
    "`publication`",
    "`integration_rollout`",
    "`production_egress`",
    "Human UAT is an observable accept/reject decision",
    "internal safety mechanics",
)
require(
    ".exocortex/control/DELIVERY_WORKFLOW.md",
    "Human-facing approval envelopes",
    "not each require a new human approval",
)
require(
    ".exocortex/docs/user-guide.md",
    "Approve understandable business outcomes",
    "Do not\napprove work-item bookkeeping",
)
forbid(
    ".exocortex/docs/AI_INSTALLATION.md",
    r"Stop for my exact bootstrap approval",
    r"receive a new exact apply approval",
    r"separately approved record mutations",
    r"Push and pull-request creation require another explicit approval",
)
require(
    ".exocortex/control/MODEL_ROUTING.md",
    "configured_official_sources_only",
    "explicit_external_read",
    "auto_activation=false",
    "Absence from a complete listing means `not_observed`",
    "A partial observation\nproduces no missing-model finding",
    "Only `eligible` models can route",
    "current_surface_session",
    "--current-surface-session-id",
    "at most 15",
    "independently of the availability file",
    "not a deterministic routing\ncriterion",
    "normative_model_pin=false",
    "zero eligible models",
    "selected evaluation evidence digests",
    "discovery result binds the supplied normalized observation digests",
)
require(
    ".exocortex/docs/UPGRADE_MANIFEST.md",
    "Preserve reviewed source executable bits",
    "unreported mode-only mutations",
    "Candidate modes come only from",
    "55 replacement-backed paths",
    "project-owned and ordinary updates retain it",
    "Archive only the code plane",
    "reviewed legacy text mode `0644`",
    "complete non-protected code-plane path types",
    "it cannot remove an existing Git index entry",
)
require(
    "SECURITY.md",
    "unique private `0600` code-plane-only restore",
    "Reject every candidate-source symlink",
    "external hard-linked mutable",
    "maximum 15-minute",
    "presence, bytes, and mode",
)
require(
    "CONTRIBUTING.md",
    "candidate and target symlink/path safety",
    "hard-link\n  denial",
    "exact in-place code-plane rollback",
)
require(
    ".exocortex/README.md",
    "docs/AI_INSTALLATION.md",
    "../CONTRIBUTING.md",
    "Deny-by-default egress",
    "primary checkout is unsupported",
)
require(
    ".exocortex/docs/getting-started.md",
    ".exocortex/docs/AI_INSTALLATION.md",
    "WSL requires",
    "clean isolated Git worktree",
    "legacy protected-default preflight",
)
require(
    ".exocortex/docs/user-guide.md",
    ".exocortex/docs/UPGRADE_MANIFEST.md",
    ".exocortex/docs/AI_INSTALLATION.md",
    "primary checkout is unsupported",
    "legacy protected-default",
)
require(
    ".exocortex/docs/implementation.md",
    "--adapter-version <registered-adapter-version>",
    "native Windows shells are unsupported",
    "clean isolated Git worktree",
    "legacy protected-default preflight",
    "HOME=<absolute-disposable-home>",
)
require(
    ".exocortex/docs/IDE_INTEGRATION_GUIDE.md",
    "Installation capability is separate",
    ".exocortex/docs/AI_INSTALLATION.md",
    "cumulative migration inventory is 80 paths",
    "26 prior Cursor/GitHub",
    "24 Claude command wrappers",
    "Root `.cursorrules` is not a retirement path",
)
require(
    "init-project.sh",
    "never normalizes or broadens permissions",
    "intentionally non-executable compatibility helpers remain untouched",
)
forbid(
    "init-project.sh",
    r"\bchmod\b",
    r"find\s+\.exocortex/scripts",
)
require(
    ".exocortex/docs/UPGRADE_MANIFEST.md",
    ".exocortex/docs/AI_INSTALLATION.md",
    "WSL remains Human-UAT-pending",
    "legacy protected defaults",
    "Existing paths are never overwritten",
    "project-specific value supplied and approved",
    "`events`, `control`",
    "zero eligible models",
    ".exocortex/local/model-routing/**",
    "apply_template_reconciliation",
)
require(
    "SECURITY.md",
    "Never pipe a remote installer into a shell",
    "Installation does not require an API key",
    "Native Windows is unsupported",
    "model registry covers configured official sources only",
)
require(
    "CONTRIBUTING.md",
    "Every deterministic group must pass",
    "active documentation and AI-installation contract drift",
    "Preserve the documented runtime baseline",
    "runs only `bash tests/run_tests.sh`",
    "does not trigger for",
    "scripts/check-release-state.sh",
    "peeled commit SHA",
    "published-digest",
)
require(
    "CHANGELOG.md",
    "AI-guided installation and update",
    "Provider-neutral entry and delivery protocol",
    "Historical release entries below preserve",
    "Preserved 26 earlier Cursor/GitHub retirement mappings",
    "durable identity-verified private code-plane-only\n  restore archives",
    "reviewed legacy text mode",
)
require(
    "WHATSNEW.md",
    "commands are retained",
    "provider-neutral AI installation guide",
    "Everything below this line is preserved historical release documentation",
    "zero eligible models",
    "apply_template_reconciliation",
    "retain 51 manifest-byte-and-mode-gated migration",
    "durable identity-verified private code-plane-only\n  rollback archives",
)

forbid(
    ".exocortex/README.md",
    r"cp\s+templates/\*",
    r"OPENAI_API_KEY\s*=\s*sk-",
)
forbid(
    "SECURITY.md",
    r"`curl\s*\|\s*bash`\s+is\s+convenient",
    r"installer\s+clones\s+from\s+GitHub",
)
forbid(
    "CONTRIBUTING.md",
    r"\ball\s+8\s+tests\b",
    r"\b8\s+tests\s+passing\b",
    r"what\s+the\s+8\s+tests\s+cover",
    r"hook\s+runs\s+the\s+full\s+test\s+suite",
)
forbid(
    ".exocortex/control/README.md",
    r"/save[^\n]*checkpoint\s+your\s+work\s+state",
)
forbid(
    ".exocortex/docs/user-guide.md",
    r"root\s+`README\.md`\s+and\s+`UPGRADE_MANIFEST\.md`",
)
forbid(
    "WHATSNEW.md",
    r"canonical\s+command\s+JSON\s+files\s+remain\s+unchanged",
)

for relative in (
    "README.md",
    "SECURITY.md",
    ".exocortex/README.md",
    ".exocortex/docs/AI_INSTALLATION.md",
):
    forbid(relative, r"curl[^\n|]*\|[^\n]*bash", r"\bsk-[A-Za-z0-9_-]+")

forbid("README.md", r"native\s+Windows[^\n]*\bis\s+supported\b")
for relative in ("README.md", ".exocortex/docs/AI_INSTALLATION.md"):
    forbid(
        relative,
        r"newest\s+release",
        r"--branch\s+(?:main|latest)\b",
        r"releases/latest",
    )
for relative in (
    "README.md",
    ".exocortex/control/MODEL_ROUTING.md",
    ".exocortex/docs/AI_INSTALLATION.md",
    ".exocortex/docs/UPGRADE_MANIFEST.md",
):
    forbid(
        relative,
        r"automatically\s+(?:uses?|selects?|routes?\s+to)\s+(?:the\s+)?newest\s+model",
        r"(?:covers?|discovers?|checks?)\s+(?:all|every)\s+models?\s+worldwide",
        r"missing\s+(?:models?|observations?)\s+(?:means?|are)\s+deprecated",
        r"(?:refresh|discovery)[^\n]*(?:uses|requires)[^\n]*credentials",
    )
forbid(
    ".exocortex/docs/AI_INSTALLATION.md",
    r"bare\s+[\"“]?yes[\"”]?[^\n]*authoriz",
    r"installation[^\n]*(?:authorizes|includes)[^\n]*(?:commit|push|pull request)",
    r"capability\s+and\s+transaction\s+paths\s+were\s+excluded",
    r"after\s+(?:install|apply)[^\n]*(?:write|record)[^\n]*handoff",
    r"ask\s+for\s+my\s+exact\s+local-install\s+approval",
    r"materialize\s+(?:one\s+)?(?:current,\s+)?one-time\s+`?apply_template_update`?\s+capability[^\n]*before[^\n]*approval",
)
forbid(
    "CONTRIBUTING.md",
    r"do\s+not\s+add\s+external\s+runtime\s+dependencies\s+beyond\s+`?git`?\s+and\s+`?bash`?",
)


def check_local_links(relative: str) -> None:
    path = ROOT / relative
    text = read(relative)
    targets = re.findall(r"\[[^\]]+\]\(([^)]+)\)", text)
    definitions = {
        key.casefold(): value.strip("<>")
        for key, value in re.findall(
            r"^[ ]{0,3}\[([^\]]+)\]:\s*(\S+)", text, flags=re.MULTILINE
        )
    }
    for label, key in re.findall(r"\[([^\]]+)\]\[([^\]]*)\]", text):
        reference = key or label
        if reference.casefold() in definitions:
            targets.append(definitions[reference.casefold()])
    for target in targets:
        clean = target.split("#", 1)[0]
        if not clean or "://" in clean or clean.startswith(("mailto:", "#")):
            continue
        destination = (path.parent / clean).resolve()
        try:
            destination.relative_to(ROOT)
        except ValueError:
            FAILURES.append(f"{relative}: link escapes repository: {target}")
            continue
        if not destination.exists():
            FAILURES.append(f"{relative}: broken local link: {target}")


for linked_doc in (
    "README.md",
    "SECURITY.md",
    "CONTRIBUTING.md",
    "CHANGELOG.md",
    "WHATSNEW.md",
    ".exocortex/README.md",
    ".exocortex/control/README.md",
    ".exocortex/docs/AI_INSTALLATION.md",
    ".exocortex/docs/IDE_INTEGRATION_GUIDE.md",
    ".exocortex/docs/UPGRADE_MANIFEST.md",
    ".exocortex/docs/getting-started.md",
    ".exocortex/docs/implementation.md",
    ".exocortex/docs/user-guide.md",
):
    check_local_links(linked_doc)

whatsnew = read("WHATSNEW.md")
historical_boundary = whatsnew.find(
    "Everything below this line is preserved historical release documentation"
)
if historical_boundary < 0:
    FAILURES.append("WHATSNEW.md: missing historical/current boundary")
else:
    for obsolete in ("--yes", "asks before applying the real update"):
        position = whatsnew.find(obsolete)
        if 0 <= position < historical_boundary:
            FAILURES.append(
                f"WHATSNEW.md: obsolete guidance appears as current: {obsolete}"
            )

manifest = read("SHA256SUMS")
if not re.search(
    r"^[0-9a-f]{64}  \.exocortex/docs/AI_INSTALLATION\.md$",
    manifest,
    flags=re.MULTILINE,
):
    FAILURES.append("SHA256SUMS: AI_INSTALLATION.md is not integrity-bound")

for required_integrity_path in (
    "FILEMODES",
    ".exocortex/model-source-registry.json",
    ".exocortex/model-routing-catalog.json",
    ".exocortex/schemas/model-source-registry.schema.json",
    ".exocortex/schemas/model-routing-catalog.schema.json",
    ".exocortex/schemas/model-observation.schema.json",
    ".exocortex/schemas/model-availability.schema.json",
    ".exocortex/schemas/update-reconciliation-plan.schema.json",
    ".exocortex/scripts/model_registry.py",
    ".exocortex/scripts/prepare_update_reconciliation.py",
):
    if not re.search(
        rf"^[0-9a-f]{{64}}  {re.escape(required_integrity_path)}$",
        manifest,
        flags=re.MULTILINE,
    ):
        FAILURES.append(
            f"SHA256SUMS: C5 path is not integrity-bound: {required_integrity_path}"
        )

checksum_paths = []
for line in manifest.splitlines():
    match = re.fullmatch(r"[0-9a-f]{64}  ([^/].*)", line)
    if match is not None:
        checksum_paths.append(match.group(1))
mode_records = {}
mode_paths = []
for line in read("FILEMODES").splitlines():
    match = re.fullmatch(r"(0644|0755)  ([^/].*)", line)
    if match is None:
        FAILURES.append("FILEMODES: malformed entry")
        continue
    mode_text, relative = match.groups()
    if relative in mode_records:
        FAILURES.append(f"FILEMODES: duplicate path: {relative}")
    mode_records[relative] = int(mode_text, 8)
    mode_paths.append(relative)
expected_mode_paths = set(checksum_paths) | {"SHA256SUMS"}
if (
    checksum_paths != sorted(checksum_paths)
    or mode_paths != sorted(mode_paths)
    or set(mode_records) != expected_mode_paths
):
    FAILURES.append("FILEMODES: path set must match sorted SHA256SUMS paths plus SHA256SUMS")
else:
    for relative in sorted(expected_mode_paths):
        path = ROOT / relative
        if path.is_symlink() or not path.is_file():
            FAILURES.append(f"FILEMODES: path is not a regular file: {relative}")
        elif stat.S_IMODE(path.stat().st_mode) != mode_records[relative]:
            FAILURES.append(f"FILEMODES: mode mismatch: {relative}")

version = PACKAGED_VERSION
if not re.search(
    rf"^## \[{re.escape(version)}\] - \d{{4}}-\d{{2}}-\d{{2}}$",
    read("CHANGELOG.md"),
    flags=re.MULTILINE,
):
    FAILURES.append("CHANGELOG.md: packaged VERSION entry is missing")
if f"# What's New in {version} " not in whatsnew:
    FAILURES.append("WHATSNEW.md: packaged VERSION heading is missing")
if historical_boundary >= 0 and "does not prove" not in whatsnew[:historical_boundary]:
    FAILURES.append("WHATSNEW.md: candidate publication boundary is missing")

try:
    catalog = json.loads(read(".exocortex/model-routing-catalog.json"))
except json.JSONDecodeError:
    FAILURES.append(".exocortex/model-routing-catalog.json: invalid JSON")
else:
    if any(
        model.get("routing_status") == "eligible"
        for model in catalog.get("models", [])
    ):
        FAILURES.append("model catalog: packaged candidate must have zero eligible models")
    if any(model.get("evaluation_profiles") for model in catalog.get("models", [])):
        FAILURES.append("model catalog: packaged candidate must have zero evaluation profiles")

if FAILURES:
    for failure in FAILURES:
        print(f"FAIL: {failure}", file=sys.stderr)
    raise SystemExit(1)

print("documentation_contract=pass")
