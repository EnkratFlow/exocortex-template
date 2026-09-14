#!/usr/bin/env python3
"""Deterministic contract checks for active installation documentation."""

from __future__ import annotations

import re
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


def forbid(relative: str, *patterns: str) -> None:
    text = read(relative)
    for pattern in patterns:
        if re.search(pattern, text, flags=re.IGNORECASE | re.MULTILINE):
            FAILURES.append(f"{relative}: forbidden active guidance matched: {pattern}")


require(
    ".exocortex/docs/AI_INSTALLATION.md",
    "Copy-paste prompt: clean installation",
    "Copy-paste prompt: existing-repository update",
    "Guarded apply contract",
    "Cooperative authority bootstrap",
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
    "Bash 3.2+, Python 3.9+, `shasum`",
    "`mkdir`, `rm`, `basename`, `dirname`, `cat`",
    "Unix-only `fcntl` module",
    "separately approved record mutations",
    "Native Windows PowerShell or Command Prompt",
    "human_uat_pending",
    "exact disposable-rehearsal approval",
    "inventories only the manifest-defined install surfaces",
    "controlled write failure",
    "shared or primary checkout",
    "rollback boundary is therefore isolation",
    "`scope.target_sha` exactly equal",
    "changed-path list is not final",
    "mandatory post-bootstrap dry",
    "Never edit the lane",
    "The orchestrator alone",
    "capability is consumed",
    "remains consumed and cannot be replayed",
    "Only after the owner gives exact apply approval",
    "separate disposable fault fixtures",
    "--capability <project-relative-capability-path>",
    "--work-item-revision <exact-current-revision>",
    "Never read or display .env or credential values",
)
require(
    "README.md",
    "Install with a coding AI",
    ".exocortex/docs/AI_INSTALLATION.md",
    "compatible_pending_candidate_CI",
    "human_uat_pending",
    "Git Bash or native Windows PowerShell/Command Prompt",
    "private staging beneath `${TMPDIR:-/tmp}`",
    "metadata-only protected-default",
    "clean isolated Git worktree",
    "shared or primary checkout",
    "HOME=<absolute-disposable-home>",
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
)
require(
    ".exocortex/docs/UPGRADE_MANIFEST.md",
    ".exocortex/docs/AI_INSTALLATION.md",
    "WSL remains Human-UAT-pending",
    "legacy protected defaults",
    "Existing paths are never overwritten",
    "project-specific value supplied and approved",
    "`events`, `control`",
)
require(
    "SECURITY.md",
    "Never pipe a remote installer into a shell",
    "Installation does not require an API key",
    "Native Windows is unsupported",
)
require(
    "CONTRIBUTING.md",
    "Every deterministic group must pass",
    "active documentation and AI-installation contract drift",
    "Preserve the documented runtime baseline",
    "runs only `bash tests/run_tests.sh`",
    "does not trigger for",
)
require(
    "CHANGELOG.md",
    "AI-guided installation and update",
    "Provider-neutral entry and delivery protocol",
    "Historical release entries below preserve",
)
require(
    "WHATSNEW.md",
    "commands are retained",
    "provider-neutral AI installation guide",
    "Everything below this line is preserved historical release documentation",
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

if FAILURES:
    for failure in FAILURES:
        print(f"FAIL: {failure}", file=sys.stderr)
    raise SystemExit(1)

print("documentation_contract=pass")
