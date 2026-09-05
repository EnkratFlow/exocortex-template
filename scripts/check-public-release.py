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
import ipaddress
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


DEFAULT_GIT_EXECUTABLE = Path("/usr/bin/git")
GIT_EXECUTABLE = DEFAULT_GIT_EXECUTABLE
GIT_EXECUTABLE_SHA256: str | None = None


@dataclass(frozen=True)
class Finding:
    rule: str
    path: str
    commit: str
    count: int


def git_environment() -> dict[str, str]:
    """Return Git environment with replacement and repository redirects disabled."""

    return {
        "PATH": os.defpath,
        "GIT_NO_REPLACE_OBJECTS": "1",
        "GIT_OPTIONAL_LOCKS": "0",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CONFIG": os.devnull,
        "GIT_TERMINAL_PROMPT": "0",
        "PYTHONDONTWRITEBYTECODE": "1",
    }


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
    ("OPENROUTER_KEY", re.compile(rb"sk-or-v1-[A-Za-z0-9_-]{20,}")),
    ("GROQ_KEY", re.compile(rb"gsk_[A-Za-z0-9_-]{20,}")),
    ("XAI_KEY", re.compile(rb"xai-[A-Za-z0-9_-]{20,}")),
    ("HUGGINGFACE_TOKEN", re.compile(rb"hf_[A-Za-z0-9]{20,}")),
    ("STRIPE_LIVE_KEY", re.compile(rb"(?:sk|rk)_live_[A-Za-z0-9]{16,}")),
    ("TAILSCALE_KEY", re.compile(rb"tskey-(?:auth|api|client)-[A-Za-z0-9_-]{16,}")),
    ("SENDGRID_KEY", re.compile(rb"SG\.[A-Za-z0-9_-]{16,}\.[A-Za-z0-9_-]{16,}")),
    ("GOOGLE_OAUTH_TOKEN", re.compile(rb"ya29\.[A-Za-z0-9_-]{20,}")),
    (
        "JWT_TOKEN",
        re.compile(rb"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"),
    ),
    ("SLACK_TOKEN", re.compile(rb"xox[baprs]-[A-Za-z0-9-]{20,}")),
    ("AWS_ACCESS_KEY_ID", re.compile(rb"(?:AKIA|ASIA)[0-9A-Z]{16}")),
    (
        "PRIVATE_KEY_BLOCK",
        re.compile(rb"-----BEGIN (?:[A-Z0-9 ]+ )?PRIVATE KEY-----"),
    ),
    (
        "GENERIC_CREDENTIAL_ASSIGNMENT",
        re.compile(
            rb"(?im)(?:^|[^A-Za-z0-9_])(?:[A-Za-z0-9]+[_.-]){0,4}"
            rb"(?:api[_-]?key|access[_-]?token|"
            rb"auth[_-]?token|client[_-]?secret|password|passwd|private[_-]?token|"
            rb"secret|session[_-]?token|token)[ \t]{0,8}[\"']?[ \t]{0,8}[:=][ \t]{0,8}[\"']?"
            rb"[A-Za-z0-9+/_.~=-]{24,}"
        ),
    ),
    (
        "BEARER_CREDENTIAL",
        re.compile(rb"(?i)\bBearer[ \t]+[A-Za-z0-9._~+/=-]{24,}\b"),
    ),
)

# Public template source and release objects must not disclose the machine or
# network they were prepared on. These checks deliberately use generic shapes;
# no private hostname, account name, address, or downstream project identifier
# belongs in the checker itself. Matches are reported only by rule and digest.
PRIVACY_PATTERNS: tuple[tuple[str, re.Pattern[bytes]], ...] = (
    (
        "TAILNET_HOSTNAME",
        re.compile(
            rb"(?i)\b(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.){1,}"
            rb"ts\.net\b"
        ),
    ),
)

HOME_ACCOUNT_PATTERN = rb"(?P<account>[A-Za-z0-9][A-Za-z0-9._-]{0,63})"
ABSOLUTE_HOME_PATTERN = re.compile(
    rb"(?i)(?<![A-Za-z0-9._/\\-])/(?:Users|home)/" + HOME_ACCOUNT_PATTERN
)
WINDOWS_HOME_PATTERNS: tuple[re.Pattern[bytes], ...] = (
    re.compile(
        rb"(?i)(?<![A-Za-z0-9._-])[A-Z]:[\\/]+"
        rb"(?:Users|Documents[ ]and[ ]Settings)[\\/]+" + HOME_ACCOUNT_PATTERN
    ),
    re.compile(
        rb"(?i)(?<![A-Za-z0-9._-])(?:\\\\|//)"
        rb"[A-Za-z0-9][A-Za-z0-9._-]{0,63}[\\/]+"
        rb"(?:Users|Documents[ ]and[ ]Settings)[\\/]+" + HOME_ACCOUNT_PATTERN
    ),
)
GENERIC_CI_HOME_ACCOUNTS = {b"runner"}

HOST_SUBJECT_PATTERN = rb"[a-z0-9](?:[a-z0-9._-]{0,62}[a-z0-9])?"

HOST_POLICY_PATTERNS: tuple[re.Pattern[bytes], ...] = (
    re.compile(
        rb"(?im)\b(?:do[ ]not|never|avoid)\s+(?:run(?:ning)?\s+)?"
        rb"(?:the\s+)?(?:full|complete)\s+(?:[a-z-]+\s+){0,3}"
        rb"(?:test|safety)\s+suites?\b[^\r\n.]{0,100}"
        rb"\b(?:on|from)\s+(?:(?P<label>host|machine|node|server)\s+)?"
        rb"(?P<subject>" + HOST_SUBJECT_PATTERN + rb")\b"
    ),
    re.compile(
        rb"(?im)\b(?:full|complete)\s+(?:[a-z-]+\s+){0,3}"
        rb"(?:test|safety)\s+suites?\b[^.]{0,120}"
        rb"\b(?:not\s+run|never\s+runs?)\b[^.]{0,80}"
        rb"\bon\s+(?:(?P<label>host|machine|node|server)\s+)?"
        rb"(?P<subject>" + HOST_SUBJECT_PATTERN + rb")\b"
    ),
)
HOST_HARDWARE_PATTERN = re.compile(
    rb"(?im)\b(?:(?P<label>host|machine|node|server)\s+)?"
    rb"(?P<subject>" + HOST_SUBJECT_PATTERN + rb")\s+is\s+(?:an?\s+)?"
    rb"(?:base\s+)?(?:apple\s+)?m[1-9][0-9]?\b"
    rb"[^\r\n.]{0,100}\b(?:mac(?:book)?|mini|studio)\b"
)
HOST_WORKLOAD_PATTERN = re.compile(
    rb"(?i)\b(?:(?P<label>host|machine|node|server)\s+)?"
    rb"(?P<subject>" + HOST_SUBJECT_PATTERN + rb")"
    rb"\s+(?:also\s+)?(?:serves|runs|hosts)\b(?P<body>[^.]{0,240})"
)
WORKLOAD_SIGNAL_PATTERN = re.compile(
    rb"(?i)\b(?:always-on|agent\s+sessions?|remote\s+sessions?|pipeline|journal|"
    rb"application|service)\b"
)
GENERIC_HOST_SUBJECTS = {
    b"agent",
    b"app",
    b"application",
    b"architecture",
    b"backend",
    b"bash",
    b"build",
    b"ci",
    b"client",
    b"cloud",
    b"cluster",
    b"code",
    b"computer",
    b"container",
    b"database",
    b"desktop",
    b"device",
    b"environment",
    b"example",
    b"fixture",
    b"framework",
    b"frontend",
    b"github",
    b"he",
    b"host",
    b"infrastructure",
    b"it",
    b"java",
    b"javascript",
    b"job",
    b"laptop",
    b"library",
    b"linux",
    b"localhost",
    b"macos",
    b"machine",
    b"model",
    b"node",
    b"pipeline",
    b"platform",
    b"process",
    b"program",
    b"pull",
    b"python",
    b"repository",
    b"router",
    b"runtime",
    b"runner",
    b"script",
    b"server",
    b"service",
    b"she",
    b"shell",
    b"software",
    b"system",
    b"template",
    b"test",
    b"that",
    b"this",
    b"suite",
    b"tool",
    b"typescript",
    b"virtual",
    b"vm",
    b"worker",
    b"workstation",
    b"workflow",
    b"windows",
    b"wsl",
}

EMAIL_PATTERN = re.compile(
    rb"(?i)\b[A-Z0-9.!#$%&'*+/=?^_`{|}~-]+@"
    rb"[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?"
    rb"(?:\.[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?)+\b"
)
IPV4_PATTERN = re.compile(rb"(?<![0-9])(?:[0-9]{1,3}\.){3}[0-9]{1,3}(?![0-9])")
IPV6_TOKEN_PATTERN = re.compile(
    rb"(?i)(?<![0-9a-f:])[0-9a-f:]{2,39}(?![0-9a-f:])"
)
PUBLIC_EXAMPLE_EMAIL_DOMAINS = {
    b"example.com",
    b"example.invalid",
    b"example.net",
    b"example.org",
}
PUBLIC_ROLE_EMAILS = {
    (b"noreply", b"github.com"),
    (b"security", b"project.example"),
}
PUBLIC_GIT_IDENTITY_NAMES = {
    b"enkratflow automation",
    b"enkratflow release",
    b"fixture",
    b"github",
    b"github actions",
    b"github-actions[bot]",
    b"web-flow",
}
PUBLIC_GITHUB_ROLE_NAMES = {
    b"enkratflow automation",
    b"enkratflow release",
    b"github",
    b"web-flow",
}
GITHUB_USERNAME_PATTERN = rb"[a-z0-9](?:[a-z0-9-]{0,37}[a-z0-9])?"
GITHUB_NOREPLY_LOCAL_PATTERN = re.compile(
    rb"(?i)(?:[1-9][0-9]{0,19}\+)?"
    + GITHUB_USERNAME_PATTERN
    + rb"(?:\[bot\])?"
)
GIT_IDENTITY_PATTERN = re.compile(
    rb"(?m)^(?:author|committer|tagger) (?P<name>[^\r\n<>]+) "
    rb"<(?P<email>[^\r\n<>]+)> [0-9]+ [+-][0-9]{4}$"
)
PRIVATE_IPV6_NETWORKS = (
    ipaddress.IPv6Network("fc" + "00::/7"),
    ipaddress.IPv6Network("fe" + "80::/10"),
    ipaddress.IPv6Network("fe" + "c0::/10"),
)

EVENT_EXAMPLES = {
    ".exocortex/events/.gitkeep",
    ".exocortex/events/2000-01-01_00-00-00_example-event.md",
}
ENV_ALLOWLIST = {".exocortex/.env.example"}
CREDENTIAL_FIXTURE_ALLOWLIST = {
    ".exocortex/.env.example",
    ".exocortex/key-registry.json",
}
CREDENTIAL_PATH_NAMES = {
    ".env",
    ".envrc",
    "credentials",
    "credentials.json",
    "id_dsa",
    "id_ecdsa",
    "id_ed25519",
    "id_rsa",
    "key-registry.json",
    "secrets.json",
}
CREDENTIAL_PATH_SUFFIXES = (".jks", ".key", ".keystore", ".p12", ".pem", ".pfx")
CREDENTIAL_DIRECTORY_NAMES = {".aws", ".ssh", "credentials", "secrets"}
DATA_FIXTURE_DIGESTS = {
    ".exocortex/events/.gitkeep": "98a444192b24c433a7239f4b6bb2d32a531184d966665e4c49d155c4741dc74e",
    ".exocortex/events/2000-01-01_00-00-00_example-event.md": "87a39e4d08a515237bc96bdcc2a7cecbc17ab5aa015978c23584097152c154d1",
    ".exocortex/.env.example": "f7b31458dd5095a7fe2d07d093dc7c0e9702d3693faa76af4addad88168601bf",
    ".exocortex/key-registry.json": "b1d352104c6479f87ca9040ab2ae0558c8d82bcc0df452cd7a2bdea2faaea7d7",
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


def configure_git_executable(path: str, expected_sha256: str | None) -> None:
    """Bind Git calls to one explicit executable, optionally by exact digest."""

    global GIT_EXECUTABLE, GIT_EXECUTABLE_SHA256
    selected = Path(path)
    if not selected.is_absolute() or selected.is_symlink():
        raise CheckError("GIT_COMMAND_UNTRUSTED")
    try:
        value = selected.stat()
    except OSError as error:
        raise CheckError("GIT_COMMAND_UNAVAILABLE") from error
    if not stat.S_ISREG(value.st_mode) or not os.access(selected, os.X_OK):
        raise CheckError("GIT_COMMAND_UNTRUSTED")
    if expected_sha256 is not None and not re.fullmatch(r"[a-f0-9]{64}", expected_sha256):
        raise CheckError("GIT_COMMAND_DIGEST_INVALID")
    GIT_EXECUTABLE = selected
    GIT_EXECUTABLE_SHA256 = expected_sha256
    verified_git_executable()


def verified_git_executable() -> str:
    """Recheck the configured executable before each child process."""

    try:
        before = GIT_EXECUTABLE.stat()
        descriptor = os.open(
            os.fspath(GIT_EXECUTABLE),
            os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0),
        )
    except OSError as error:
        raise CheckError("GIT_COMMAND_UNAVAILABLE") from error
    try:
        opened = os.fstat(descriptor)
        if (
            not stat.S_ISREG(opened.st_mode)
            or (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
            != (opened.st_dev, opened.st_ino, opened.st_size, opened.st_mtime_ns)
        ):
            raise CheckError("GIT_COMMAND_CHANGED")
        if GIT_EXECUTABLE_SHA256 is not None:
            digest = hashlib.sha256()
            while True:
                chunk = os.read(descriptor, 1024 * 1024)
                if not chunk:
                    break
                digest.update(chunk)
            if digest.hexdigest() != GIT_EXECUTABLE_SHA256:
                raise CheckError("GIT_COMMAND_DIGEST_MISMATCH")
        after = os.stat(GIT_EXECUTABLE, follow_symlinks=False)
        if (
            (opened.st_dev, opened.st_ino, opened.st_size, opened.st_mtime_ns)
            != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
        ):
            raise CheckError("GIT_COMMAND_CHANGED")
    finally:
        os.close(descriptor)
    return os.fspath(GIT_EXECUTABLE)


def git(root: Path, *args: str, input_bytes: bytes | None = None) -> bytes:
    git_executable = verified_git_executable()
    result = subprocess.run(
        (
            git_executable,
            "-c", "core.fsmonitor=false",
            "-c", f"core.hooksPath={os.devnull}",
            "-c", "http.followRedirects=false",
            "-C", os.fspath(root), *args,
        ),
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


def is_credential_path(path: str) -> bool:
    parts = [part.casefold() for part in PurePosixPath(path).parts]
    basename = parts[-1]
    return (
        basename in CREDENTIAL_PATH_NAMES
        or basename.startswith(".env.")
        or basename.endswith(CREDENTIAL_PATH_SUFFIXES)
        or any(part in CREDENTIAL_DIRECTORY_NAMES for part in parts)
    )


def path_rule(path: str) -> str | None:
    """Return a data-plane rule without reading the file."""

    if is_env_path(path) and path not in ENV_ALLOWLIST:
        return "ENV_FILE"
    if is_credential_path(path) and path not in CREDENTIAL_FIXTURE_ALLOWLIST:
        return "CREDENTIAL_PATH"
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


def public_email(email: bytes) -> tuple[bool, bool]:
    """Return (allowed, reserved-example) for one normalized address."""

    local, separator, domain = email.lower().rpartition(b"@")
    if not separator:
        return False, False
    example = any(
        domain == allowed or domain.endswith(b"." + allowed)
        for allowed in PUBLIC_EXAMPLE_EMAIL_DOMAINS
    ) or domain == b"example" or domain.endswith(b".example")
    if example:
        return True, True
    if domain == b"users.noreply.github.com":
        return GITHUB_NOREPLY_LOCAL_PATTERN.fullmatch(local) is not None, False
    return (local, domain) in PUBLIC_ROLE_EMAILS, False


def git_identity_findings(path: str, commit: str, content: bytes) -> list[Finding]:
    """Require both a generic display name and a narrowly public Git address."""

    if path not in {"<commit-object>", "<tag-object>"}:
        return []
    count = 0
    for match in GIT_IDENTITY_PATTERN.finditer(content):
        name = b" ".join(match.group("name").strip().lower().split())
        email = match.group("email").lower()
        allowed, example = public_email(email)
        local, _, domain = email.rpartition(b"@")
        identity_matches_email = example
        if domain == b"github.com" and local == b"noreply":
            identity_matches_email = name in PUBLIC_GITHUB_ROLE_NAMES
        elif domain == b"users.noreply.github.com":
            handle = local.split(b"+", 1)[-1]
            identity_matches_email = name == handle
        if (
            not allowed
            or name not in PUBLIC_GIT_IDENTITY_NAMES
            or not identity_matches_email
        ):
            count += 1
    return [Finding("NON_PUBLIC_GIT_IDENTITY", path, commit, count)] if count else []


def is_windows_drive_slash(content: bytes, start: int) -> bool:
    """Return true when a slash begins a standalone Windows drive path."""

    if start < 2 or re.fullmatch(rb"[A-Za-z]:", content[start - 2 : start]) is None:
        return False
    return start == 2 or re.fullmatch(
        rb"[A-Za-z0-9._-]", content[start - 3 : start - 2]
    ) is None


def home_path_findings(path: str, commit: str, content: bytes) -> list[Finding]:
    """Detect concrete home paths while permitting a narrow CI account fixture."""

    absolute_count = 0
    for match in ABSOLUTE_HOME_PATTERN.finditer(content):
        if match.group("account").lower() in GENERIC_CI_HOME_ACCOUNTS:
            continue
        if is_windows_drive_slash(content, match.start()):
            continue
        absolute_count += 1

    windows_count = sum(
        1 for pattern in WINDOWS_HOME_PATTERNS for _ in pattern.finditer(content)
    )
    findings: list[Finding] = []
    if absolute_count:
        findings.append(Finding("ABSOLUTE_HOME_PATH", path, commit, absolute_count))
    if windows_count:
        findings.append(Finding("WINDOWS_HOME_PATH", path, commit, windows_count))
    return findings


def concrete_host_subject(match: re.Match[bytes]) -> bool:
    """Treat every non-generic subject token as a concrete machine name."""

    subject = match.group("subject").lower()
    return subject not in GENERIC_HOST_SUBJECTS


def strong_workload_host_subject(match: re.Match[bytes]) -> bool:
    """Return true for a labelled name or a hostname-shaped subject token."""

    subject = match.group("subject").lower()
    return bool(match.groupdict().get("label")) or any(
        value in subject for value in b"0123456789._-"
    )


def content_scan_views(content: bytes) -> tuple[bytes, ...]:
    """Return raw bytes plus one high-confidence UTF-16 text representation."""

    encoding: str | None = None
    body = content
    if content.startswith(b"\xff\xfe"):
        encoding = "utf-16-le"
        body = content[2:]
    elif content.startswith(b"\xfe\xff"):
        encoding = "utf-16-be"
        body = content[2:]
    elif len(content) >= 8 and len(content) % 2 == 0:
        pairs = len(content) // 2
        even_zeroes = content[0::2].count(0)
        odd_zeroes = content[1::2].count(0)
        if odd_zeroes / pairs >= 0.6 and even_zeroes / pairs <= 0.2:
            encoding = "utf-16-le"
        elif even_zeroes / pairs >= 0.6 and odd_zeroes / pairs <= 0.2:
            encoding = "utf-16-be"
    if encoding is None:
        return (content,)
    try:
        decoded = body.decode(encoding).encode("utf-8")
    except UnicodeError:
        return (content,)
    return (content, decoded)


def privacy_findings(path: str, commit: str, content: bytes) -> list[Finding]:
    """Detect high-confidence public-template privacy disclosures."""

    findings: list[Finding] = []
    findings.extend(home_path_findings(path, commit, content))
    for rule, pattern in PRIVACY_PATTERNS:
        count = len(pattern.findall(content))
        if count:
            findings.append(Finding(rule, path, commit, count))

    host_policy_count = 0
    for pattern in HOST_POLICY_PATTERNS:
        for match in pattern.finditer(content):
            if concrete_host_subject(match):
                host_policy_count += 1
    if host_policy_count:
        findings.append(
            Finding("HOST_BOUND_TEST_POLICY", path, commit, host_policy_count)
        )

    hardware_count = sum(
        1
        for match in HOST_HARDWARE_PATTERN.finditer(content)
        if concrete_host_subject(match)
    )
    if hardware_count:
        findings.append(
            Finding("HOST_HARDWARE_DISCLOSURE", path, commit, hardware_count)
        )

    workload_count = 0
    for match in HOST_WORKLOAD_PATTERN.finditer(content):
        if not concrete_host_subject(match):
            continue
        signals = len(WORKLOAD_SIGNAL_PATTERN.findall(match.group("body")))
        required_signals = 1 if strong_workload_host_subject(match) else 2
        if signals >= required_signals:
            workload_count += 1
    if workload_count:
        findings.append(
            Finding("LOCAL_WORKLOAD_DISCLOSURE", path, commit, workload_count)
        )

    non_public_email_count = 0
    for match in EMAIL_PATTERN.finditer(content):
        allowed, _ = public_email(match.group(0))
        if allowed:
            continue
        non_public_email_count += 1
    if non_public_email_count:
        findings.append(Finding("NON_PUBLIC_EMAIL", path, commit, non_public_email_count))

    private_count = 0
    cgnat_count = 0
    for match in IPV4_PATTERN.finditer(content):
        octets = tuple(int(value) for value in match.group(0).split(b"."))
        if any(value > 255 for value in octets):
            continue
        first, second, _, _ = octets
        if first == 10 or (first == 172 and 16 <= second <= 31) or (
            first == 192 and second == 168
        ):
            private_count += 1
        elif first == 100 and 64 <= second <= 127:
            cgnat_count += 1
    if private_count:
        findings.append(Finding("PRIVATE_NETWORK_IPV4", path, commit, private_count))
    if cgnat_count:
        findings.append(Finding("CGNAT_NETWORK_IPV4", path, commit, cgnat_count))

    private_ipv6_count = 0
    for match in IPV6_TOKEN_PATTERN.finditer(content):
        token = match.group(0)
        if b":" not in token:
            continue
        try:
            address = ipaddress.IPv6Address(token.decode("ascii"))
        except (UnicodeDecodeError, ipaddress.AddressValueError):
            continue
        if any(address in network for network in PRIVATE_IPV6_NETWORKS):
            private_ipv6_count += 1
    if private_ipv6_count:
        findings.append(
            Finding("PRIVATE_NETWORK_IPV6", path, commit, private_ipv6_count)
        )
    return findings


def content_findings(path: str, commit: str, content: bytes) -> list[Finding]:
    findings: list[Finding] = []
    planning_rule = planning_stub_rule(path, content)
    if planning_rule:
        findings.append(Finding(planning_rule, path, commit, 1))
    fixture_rule = data_fixture_rule(path, content)
    if fixture_rule:
        findings.append(Finding(fixture_rule, path, commit, 1))
    views = content_scan_views(content)
    for rule, pattern in SECRET_PATTERNS:
        count = sum(len(pattern.findall(view)) for view in views)
        if count:
            findings.append(Finding(rule, path, commit, count))
    for view in views:
        findings.extend(privacy_findings(path, commit, view))
        findings.extend(git_identity_findings(path, commit, view))
    return findings


def path_sensitive_findings(path: str, commit: str) -> list[Finding]:
    """Detect high-confidence secret or privacy shapes in Git-visible paths."""

    encoded = path.encode("utf-8", errors="surrogateescape")
    findings: list[Finding] = []
    for rule, pattern in SECRET_PATTERNS:
        count = len(pattern.findall(encoded))
        if count:
            findings.append(Finding(rule, path, commit, count))
    findings.extend(privacy_findings(path, commit, encoded))
    return findings


def tracked_paths(root: Path) -> list[str]:
    raw_paths = git(root, "ls-files", "-z")
    return sorted(
        normalize_path(item.decode("utf-8", errors="surrogateescape"))
        for item in raw_paths.split(b"\0")
        if item
    )


def source_tree_paths(root: Path) -> list[str]:
    """Return source paths using anchored, non-following directory descriptors."""

    nofollow = getattr(os, "O_NOFOLLOW", 0)
    directory_flag = getattr(os, "O_DIRECTORY", 0)
    if not nofollow or not directory_flag:
        raise CheckError("SAFE_TOPOLOGY_UNSUPPORTED")
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


def secure_read_regular(root: Path, path: str) -> tuple[bytes | None, str | None]:
    """Read one root-relative file through an openat/O_NOFOLLOW fd chain."""

    nofollow = getattr(os, "O_NOFOLLOW", 0)
    directory_flag = getattr(os, "O_DIRECTORY", 0)
    if not nofollow or not directory_flag:
        return None, "SAFE_TOPOLOGY_UNSUPPORTED"
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
        findings.extend(path_sensitive_findings(path, "WORKTREE"))
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
        findings.extend(path_sensitive_findings(path, commit))
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
            for finding in path_sensitive_findings(path, commit):
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
        git(root, "merge-base", "--is-ancestor", baseline_commit, candidate_commit)
    except CheckError as error:
        raise CheckError("RANGE_NON_ANCESTOR") from error

    findings = range_path_findings(root, baseline_commit, candidate_commit)
    findings.extend(
        range_commit_object_findings(root, baseline_commit, candidate_commit)
    )
    regular_paths = range_regular_blob_paths(root, baseline_commit, candidate_commit)
    for object_id in sorted(range_blobs(root, baseline_commit, candidate_commit)):
        paths = {
            path
            for path in regular_paths.get(object_id, set())
            if path_rule(path) is None
        }
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
        "CREDENTIAL_PATH": "credential",
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
        "ABSOLUTE_HOME_PATH": "privacy",
        "WINDOWS_HOME_PATH": "privacy",
        "TAILNET_HOSTNAME": "privacy",
        "HOST_BOUND_TEST_POLICY": "privacy",
        "HOST_HARDWARE_DISCLOSURE": "privacy",
        "LOCAL_WORKLOAD_DISCLOSURE": "privacy",
        "NON_PUBLIC_EMAIL": "privacy",
        "PRIVATE_NETWORK_IPV4": "privacy",
        "CGNAT_NETWORK_IPV4": "privacy",
        "PRIVATE_NETWORK_IPV6": "privacy",
        "NON_PUBLIC_GIT_IDENTITY": "privacy",
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
        "--git-executable",
        default=os.fspath(DEFAULT_GIT_EXECUTABLE),
        help="Exact absolute Git executable used for all Git-backed checks",
    )
    parser.add_argument(
        "--git-executable-sha256",
        help="Optional approved SHA-256 for --git-executable; publication supplies it",
    )
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
        configure_git_executable(args.git_executable, args.git_executable_sha256)
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
