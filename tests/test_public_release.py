#!/usr/bin/env python3
"""Focused fictional-only tests for scripts/check-public-release.py."""

from __future__ import annotations

import hashlib
import os
import subprocess
import sys
import tempfile
from pathlib import Path, PurePosixPath


TEMPLATE = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
CHECKER = TEMPLATE / "scripts/check-public-release.py"
FIXTURE_EMAIL = "fixture@example.invalid"
CANARY = "gh" + "p_" + "0123456789ABCDEFGHIJKL"
FINE_GRAINED_CANARY = "github" + "_pat_" + "0123456789ABCDEFGHIJKL_mnopqrstuvwxyz"
MAC_HOME_CANARY = "/" + "Users" + "/" + "fictional-private-user" + "/workspace"
DELIMITED_HOME_CANARY = "location:" + MAC_HOME_CANARY
WINDOWS_HOME_CANARY = "C:" + "\\" + "Users" + "\\" + "fictional-private-user"
WINDOWS_FORWARD_HOME_CANARY = "D:" + "/" + "Users" + "/" + "fictional-private-user"
WINDOWS_UNC_HOME_CANARY = (
    "\\\\" + "fictional-server" + "\\" + "Users" + "\\" + "fictional-private-user"
)
WINDOWS_UNC_FORWARD_HOME_CANARY = (
    "//" + "fictional-server" + "/" + "Users" + "/" + "fictional-private-user"
)
PRIVATE_IPV4_CANARY = ".".join(("192", "168", "44", "21"))
CGNAT_IPV4_CANARY = ".".join(("100", "95", "12", "8"))
PRIVATE_IPV6_CANARY = ":".join(("fd71", "2222", "3333", "", "9"))
LINK_LOCAL_IPV6_CANARY = ":".join(("fe80", "", "9"))
SITE_LOCAL_IPV6_CANARY = ":".join(("fec0", "", "9"))
TAILNET_CANARY = ".".join(("fictional-node", "fictional-tailnet", "ts", "net"))
SHORT_TAILNET_CANARY = ".".join(("fictional-node", "ts", "net"))
PERSONAL_EMAIL_CANARY = "private-person" + "@" + "mail-provider" + ".com"
NOREPLY_EMAIL_CANARY = "123+fictional" + "@" + "users.noreply.github.com"
INVALID_NOREPLY_EMAIL_CANARY = "0+fictional" + "@" + "users.noreply.github.com"
PRIVATE_GIT_EMAIL_CANARY = "fixture" + "@" + "privatehost"
PERSONAL_NAME_CANARY = "Fictional" + " Private Person"
HOST_POLICY_CANARY = "Do not run full test suites on " + "fictional-node"
ALPHA_HOST_POLICY_CANARY = "Do not run full test suites on " + "fictionalalpha"
HOST_HARDWARE_CANARY = (
    "fictional-node" + " is a base M4 Mac mini: 12 cores, 48GB RAM."
)
ALPHA_HOST_HARDWARE_CANARY = (
    "fictionalalpha" + " is a base M4 Mac mini: 12 cores, 48GB RAM."
)
WORKLOAD_CANARY = "fictional-node" + " serves the " + "pipeline."
ALPHA_HOST_WORKLOAD_CANARY = (
    "fictionalalpha" + " serves the " + "pipeline and agent sessions."
)
DIGIT_HOST_WORKLOAD_CANARY = "7" + "fictional-node" + " runs the " + "journal."
LABELED_HOST_WORKLOAD_CANARY = (
    "host " + "fictionalalpha" + " runs the " + "application."
)
GENERIC_ASSIGNMENT_CANARY = "z9" * 24
BEARER_CANARY = "r8" * 24
CREDENTIAL_ADJACENT_FIXTURES = {
    ".exocortex/.env.example",
    ".exocortex/key-registry.json",
}


def run(
    *args: str,
    cwd: Path,
    check: bool = True,
    timeout: float | None = None,
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        args, cwd=cwd, text=True, capture_output=True, check=False, timeout=timeout
    )
    if check and result.returncode:
        raise AssertionError(f"command failed: {args!r}: {result.stderr}")
    return result


def write(root: Path, relative: str, content: str = "fictional fixture\n") -> None:
    target = root / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


def write_bytes(root: Path, relative: str, content: bytes) -> None:
    target = root / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(content)


def credential_adjacent_path(relative: str) -> bool:
    for part in PurePosixPath(relative).parts:
        name = part.lower()
        if (
            name == ".env"
            or name.startswith(".env.")
            or name == ".envrc"
            or name == "key-registry.json"
        ):
            return True
    return False


def materialize_credential_blind_candidate(source: Path, target: Path) -> set[str]:
    """Copy tracked and ordinary untracked source without opening credentials."""

    result = subprocess.run(
        (
            "git",
            "-C",
            os.fspath(source),
            "ls-files",
            "-z",
            "--cached",
            "--others",
            "--exclude-standard",
        ),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode:
        raise AssertionError("candidate source inventory failed")
    copied: set[str] = set()
    for encoded in result.stdout.split(b"\0"):
        if not encoded:
            continue
        relative = encoded.decode("utf-8", errors="surrogateescape")
        path = PurePosixPath(relative)
        if path.is_absolute() or ".." in path.parts:
            raise AssertionError("unsafe candidate source path")
        if credential_adjacent_path(relative):
            continue
        source_path = source / relative
        target_path = target / relative
        target_path.parent.mkdir(parents=True, exist_ok=True)
        if source_path.is_symlink():
            os.symlink(os.readlink(source_path), target_path)
        elif source_path.is_file():
            target_path.write_bytes(source_path.read_bytes())
        else:
            raise AssertionError("candidate source entry is not a regular file")
        copied.add(relative)
    return copied


def commit(root: Path, message: str) -> str:
    run("git", "add", ".", cwd=root)
    run("git", "commit", "-m", message, cwd=root)
    return run("git", "rev-parse", "HEAD", cwd=root).stdout.strip()


def fixture() -> tuple[tempfile.TemporaryDirectory[str], Path, str]:
    temp = tempfile.TemporaryDirectory(prefix="exo-public-release-")
    root = Path(temp.name) / "repo"
    root.mkdir()
    run("git", "init", "-b", "main", cwd=root)
    run("git", "config", "user.name", "Fixture", cwd=root)
    run("git", "config", "user.email", FIXTURE_EMAIL, cwd=root)
    write(root, "README.md")
    return temp, root, commit(root, "initial fixture")


def assert_rule(result: subprocess.CompletedProcess[str], rule: str) -> None:
    assert_redacted_rule(result, rule, CANARY)


def assert_redacted_rule(
    result: subprocess.CompletedProcess[str], rule: str, canary: str
) -> None:
    assert result.returncode == 1, result.stderr
    assert f'"rule": "{rule}"' in result.stdout
    assert canary not in result.stdout
    assert canary not in result.stderr


def path_digest(relative: str) -> str:
    return hashlib.sha256(relative.encode("utf-8")).hexdigest()


def annotated_tag_workflow_arguments(
    root: Path, ref_name: str, event_candidate_sha: str
) -> subprocess.CompletedProcess[str]:
    """Exercise the tag-resolution shell used by CI with fictional local Git."""

    script = r'''
CANDIDATE_TAG_REF="refs/exocortex-release-tags/$REF_NAME"
git fetch --no-tags --force origin "refs/tags/$REF_NAME:$CANDIDATE_TAG_REF"
TAG_OBJECT="$(git rev-parse --verify "$CANDIDATE_TAG_REF")"
[ "$(git cat-file -t "$TAG_OBJECT")" = tag ]
PEELED_CANDIDATE="$(git rev-parse --verify "$TAG_OBJECT^{commit}")"
EVENT_CANDIDATE_COMMIT="$(git rev-parse --verify "$CANDIDATE_SHA^{commit}")"
[ "$EVENT_CANDIDATE_COMMIT" = "$PEELED_CANDIDATE" ]
BASELINE_RECORD_VALUES="$(python3 -I - "$REF_NAME" <<'PY'
import json
import re
import sys
from pathlib import Path

def no_duplicates(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("duplicate key")
        value[key] = item
    return value

try:
    value = json.loads(
        Path('.exocortex/release-baseline.json').read_text(encoding='utf-8'),
        object_pairs_hook=no_duplicates,
    )
except (OSError, TypeError, ValueError):
    raise SystemExit(1)
expected = {
    'schema_version',
    'kind',
    'previous_published_tag',
    'previous_published_commit',
}
if not isinstance(value, dict) or set(value) != expected \
    or value['schema_version'] != 'public-v1' \
    or value['kind'] != 'exocortex_release_baseline':
    raise SystemExit(1)
tag = value['previous_published_tag']
commit = value['previous_published_commit']
if not isinstance(tag, str) or not isinstance(commit, str):
    raise SystemExit(1)
baseline = re.fullmatch(r'v([0-9]+)\.([0-9]+)\.([0-9]+)', tag)
candidate = re.fullmatch(r'v([0-9]+)\.([0-9]+)\.([0-9]+)', sys.argv[1])
if baseline is None or candidate is None \
    or re.fullmatch(r'[0-9a-f]{40,64}', commit) is None:
    raise SystemExit(1)
if tuple(map(int, baseline.groups())) >= tuple(map(int, candidate.groups())):
    raise SystemExit(1)
print(f'{tag}\t{commit}')
PY
)"
[ -n "$BASELINE_RECORD_VALUES" ]
IFS=$'\t' read -r RECORDED_BASELINE_TAG RECORDED_BASELINE <<< "$BASELINE_RECORD_VALUES"
[ -n "$RECORDED_BASELINE_TAG" ] && [ -n "$RECORDED_BASELINE" ]
RECORDED_BASELINE_TAG_REF="refs/exocortex-release-tags/$RECORDED_BASELINE_TAG"
git fetch --no-tags --force origin "refs/tags/$RECORDED_BASELINE_TAG:$RECORDED_BASELINE_TAG_REF"
RECORDED_BASELINE_TAG_OBJECT="$(git rev-parse --verify "$RECORDED_BASELINE_TAG_REF")"
[ "$(git cat-file -t "$RECORDED_BASELINE_TAG_OBJECT")" = tag ]
RECORDED_BASELINE_TARGET="$(git cat-file -p "$RECORDED_BASELINE_TAG_OBJECT" | sed -n 's/^object //p' | head -n 1)"
RECORDED_BASELINE_TARGET_TYPE="$(git cat-file -p "$RECORDED_BASELINE_TAG_OBJECT" | sed -n 's/^type //p' | head -n 1)"
[ "$RECORDED_BASELINE_TARGET_TYPE" = commit ]
[[ "$RECORDED_BASELINE_TARGET" =~ ^[0-9a-f]{40,64}$ ]]
[ "$(git cat-file -t "$RECORDED_BASELINE_TARGET")" = commit ]
[ "$RECORDED_BASELINE_TARGET" = "$RECORDED_BASELINE" ]
[ "$RECORDED_BASELINE" != "$PEELED_CANDIDATE" ]
git merge-base --is-ancestor "$RECORDED_BASELINE" "$PEELED_CANDIDATE"
printf '%s\n%s\n' "$PEELED_CANDIDATE" "$TAG_OBJECT"
'''
    environment = os.environ.copy()
    environment.update(
        {
            "REF_NAME": ref_name,
            "CANDIDATE_SHA": event_candidate_sha,
            "GIT_NO_REPLACE_OBJECTS": "1",
        }
    )
    return subprocess.run(
        ("bash", "-ceu", script),
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
        env=environment,
    )


def main() -> None:
    source = CHECKER.read_text(encoding="utf-8")
    assert "subprocess.run" in source
    assert '"fetch"' not in source
    assert '"push"' not in source
    workflow = (TEMPLATE / ".github/workflows/checksums.yml").read_text(encoding="utf-8")
    for expected in (
        "REF_NAME: ${{ github.ref_name }}",
        "REF_TYPE: ${{ github.ref_type }}",
        'GIT_NO_REPLACE_OBJECTS: "1"',
        'elif [ "$REF_TYPE" = tag ] && [[ "$REF_NAME" == v* ]]; then',
        'CANDIDATE_TAG_REF="refs/exocortex-release-tags/$REF_NAME"',
        'git fetch --no-tags --force origin',
        '"refs/tags/$REF_NAME:$CANDIDATE_TAG_REF"',
        'git rev-parse --verify "$CANDIDATE_TAG_REF"',
        '[ "$(git cat-file -t "$TAG_OBJECT")" = tag ]',
        'git rev-parse --verify "$TAG_OBJECT^{commit}"',
        'git rev-parse --verify "$CANDIDATE_SHA^{commit}"',
        "object_pairs_hook=no_duplicates",
        "'schema_version',",
        "'kind',",
        "'previous_published_tag',",
        "'previous_published_commit',",
        'RECORDED_BASELINE_TAG_REF="refs/exocortex-release-tags/$RECORDED_BASELINE_TAG"',
        '"refs/tags/$RECORDED_BASELINE_TAG:$RECORDED_BASELINE_TAG_REF"',
        "TAG_BASELINE_DIRECT_TARGET_INVALID",
        "TAG_BASELINE_COMMIT_MISMATCH",
        "TAG_BASELINE_EQUALS_CANDIDATE",
        "TAG_BASELINE_NOT_ANCESTOR",
        '--baseline "$RECORDED_BASELINE" --candidate "$PEELED_CANDIDATE"',
        '--tag-object "$TAG_OBJECT"',
    ):
        assert expected in workflow
    assert workflow.index('elif [ "$REF_TYPE" = tag ]') < workflow.index(
        'elif [ -n "$PUSH_BEFORE_SHA" ]'
    )

    with tempfile.TemporaryDirectory(prefix="exo-public-source-tree-") as raw:
        source_root = Path(raw)
        write(source_root, "README.md")
        source_only = run(
            "python3", str(CHECKER), "--root", str(source_root), "--source-tree",
            cwd=source_root,
        )
        assert source_only.stdout == "public_release=pass\n"

    with tempfile.TemporaryDirectory(prefix="exo-public-source-fifo-") as raw:
        source_root = Path(raw)
        write(source_root, "README.md")
        os.mkfifo(source_root / "blocking-input")
        fifo = run(
            "python3", str(CHECKER), "--root", str(source_root), "--source-tree",
            cwd=source_root, check=False, timeout=5,
        )
        assert_rule(fifo, "SPECIAL_PATH")

    with tempfile.TemporaryDirectory(prefix="exo-public-source-path-secret-") as raw:
        source_root = Path(raw)
        write(source_root, f"ordinary-{CANARY}.txt")
        result = run(
            "python3", str(CHECKER), "--root", str(source_root), "--source-tree",
            cwd=source_root, check=False,
        )
        assert_rule(result, "GITHUB_TOKEN")
        assert CANARY not in result.stdout + result.stderr

    for relative in (
        "credentials.json",
        "config/secrets.json",
        "keys/private.pem",
        ".ssh/config",
    ):
        with tempfile.TemporaryDirectory(prefix="exo-public-credential-path-") as raw:
            source_root = Path(raw)
            write(source_root, relative, "fictional opaque value\n")
            result = run(
                "python3", str(CHECKER), "--root", str(source_root), "--source-tree",
                cwd=source_root, check=False,
            )
            assert_rule(result, "CREDENTIAL_PATH")
            assert relative not in result.stdout + result.stderr
            assert path_digest(relative) in result.stdout
            assert '"path_class": "credential"' in result.stdout

    temp, root, baseline = fixture()
    try:
        relative = "config/credentials.json"
        write(root, relative, CANARY + "\n")
        candidate = commit(root, "credential path content remains unread")
        result = run(
            "python3", str(CHECKER), "--root", str(root), "--baseline", baseline,
            "--candidate", candidate, cwd=root, check=False,
        )
        assert_rule(result, "CREDENTIAL_PATH")
        assert '"rule": "GITHUB_TOKEN"' not in result.stdout
        assert CANARY not in result.stdout + result.stderr
    finally:
        temp.cleanup()

    with tempfile.TemporaryDirectory(prefix="exo-public-generic-secret-") as raw:
        source_root = Path(raw)
        relative = "ordinary-config.txt"
        write(source_root, relative, f"service_api_key={GENERIC_ASSIGNMENT_CANARY}\n")
        result = run(
            "python3", str(CHECKER), "--root", str(source_root), "--source-tree",
            cwd=source_root, check=False,
        )
        assert_redacted_rule(
            result, "GENERIC_CREDENTIAL_ASSIGNMENT", GENERIC_ASSIGNMENT_CANARY
        )

    with tempfile.TemporaryDirectory(prefix="exo-public-bearer-secret-") as raw:
        source_root = Path(raw)
        relative = "request-example.txt"
        write(source_root, relative, f"Authorization: Bearer {BEARER_CANARY}\n")
        result = run(
            "python3", str(CHECKER), "--root", str(source_root), "--source-tree",
            cwd=source_root, check=False,
        )
        assert_redacted_rule(result, "BEARER_CREDENTIAL", BEARER_CANARY)

    with tempfile.TemporaryDirectory(prefix="exo-public-git-digest-") as raw:
        source_root = Path(raw)
        write(source_root, "README.md")
        result = run(
            "python3", str(CHECKER), "--root", str(source_root), "--source-tree",
            "--git-executable", "/usr/bin/git",
            "--git-executable-sha256", "0" * 64,
            cwd=source_root, check=False,
        )
        assert result.returncode == 2
        assert "GIT_COMMAND_DIGEST_MISMATCH" in result.stderr

    with tempfile.TemporaryDirectory(prefix="exo-public-source-fine-grained-") as raw:
        source_root = Path(raw)
        relative = "fine-grained-source.txt"
        write(source_root, relative, f"fixture={FINE_GRAINED_CANARY}\n")
        result = run(
            "python3", str(CHECKER), "--root", str(source_root), "--source-tree",
            cwd=source_root, check=False,
        )
        assert_redacted_rule(result, "GITHUB_FINE_GRAINED_TOKEN", FINE_GRAINED_CANARY)
        assert path_digest(relative) in result.stdout
        assert '"path_class": "repository"' in result.stdout

    for rule, canary in (
        ("ABSOLUTE_HOME_PATH", MAC_HOME_CANARY),
        ("ABSOLUTE_HOME_PATH", DELIMITED_HOME_CANARY),
        ("WINDOWS_HOME_PATH", WINDOWS_HOME_CANARY),
        ("WINDOWS_HOME_PATH", WINDOWS_UNC_HOME_CANARY),
        ("WINDOWS_HOME_PATH", WINDOWS_UNC_FORWARD_HOME_CANARY),
        ("PRIVATE_NETWORK_IPV4", PRIVATE_IPV4_CANARY),
        ("CGNAT_NETWORK_IPV4", CGNAT_IPV4_CANARY),
        ("PRIVATE_NETWORK_IPV6", PRIVATE_IPV6_CANARY),
        ("PRIVATE_NETWORK_IPV6", LINK_LOCAL_IPV6_CANARY),
        ("PRIVATE_NETWORK_IPV6", SITE_LOCAL_IPV6_CANARY),
        ("TAILNET_HOSTNAME", TAILNET_CANARY),
        ("TAILNET_HOSTNAME", SHORT_TAILNET_CANARY),
        ("NON_PUBLIC_EMAIL", PERSONAL_EMAIL_CANARY),
        ("HOST_BOUND_TEST_POLICY", HOST_POLICY_CANARY),
        ("HOST_BOUND_TEST_POLICY", ALPHA_HOST_POLICY_CANARY),
        ("HOST_HARDWARE_DISCLOSURE", HOST_HARDWARE_CANARY),
        ("HOST_HARDWARE_DISCLOSURE", ALPHA_HOST_HARDWARE_CANARY),
        ("LOCAL_WORKLOAD_DISCLOSURE", WORKLOAD_CANARY),
        ("LOCAL_WORKLOAD_DISCLOSURE", ALPHA_HOST_WORKLOAD_CANARY),
        ("LOCAL_WORKLOAD_DISCLOSURE", DIGIT_HOST_WORKLOAD_CANARY),
        ("LOCAL_WORKLOAD_DISCLOSURE", LABELED_HOST_WORKLOAD_CANARY),
    ):
        with tempfile.TemporaryDirectory(prefix="exo-public-source-privacy-") as raw:
            source_root = Path(raw)
            write(source_root, "README.md", f"fictional fixture: {canary}\n")
            result = run(
                "python3", str(CHECKER), "--root", str(source_root), "--source-tree",
                cwd=source_root, check=False,
            )
            assert_redacted_rule(result, rule, canary)

    with tempfile.TemporaryDirectory(prefix="exo-public-source-windows-forward-") as raw:
        source_root = Path(raw)
        write(source_root, "README.md", f"fictional fixture: {WINDOWS_FORWARD_HOME_CANARY}\n")
        result = run(
            "python3", str(CHECKER), "--root", str(source_root), "--source-tree",
            cwd=source_root, check=False,
        )
        assert_redacted_rule(result, "WINDOWS_HOME_PATH", WINDOWS_FORWARD_HOME_CANARY)
        assert '"rule": "ABSOLUTE_HOME_PATH"' not in result.stdout

    for encoding, prefix, rule, canary in (
        ("utf-16-le", b"", "PRIVATE_NETWORK_IPV4", PRIVATE_IPV4_CANARY),
        ("utf-16-be", b"\xfe\xff", "NON_PUBLIC_EMAIL", PERSONAL_EMAIL_CANARY),
    ):
        with tempfile.TemporaryDirectory(prefix="exo-public-utf16-") as raw:
            source_root = Path(raw)
            write_bytes(
                source_root,
                "windows-text.txt",
                prefix + f"fictional fixture: {canary}\n".encode(encoding),
            )
            result = run(
                "python3", str(CHECKER), "--root", str(source_root), "--source-tree",
                cwd=source_root, check=False,
            )
            assert_redacted_rule(result, rule, canary)

    for private_address in (
        ".".join(("10", "0", "0", "0")),
        ".".join(("10", "255", "255", "255")),
        ".".join(("172", "16", "0", "0")),
        ".".join(("172", "31", "255", "255")),
        ".".join(("192", "168", "0", "0")),
        ".".join(("192", "168", "255", "255")),
    ):
        with tempfile.TemporaryDirectory(prefix="exo-public-private-boundary-") as raw:
            source_root = Path(raw)
            write(source_root, "README.md", f"fictional endpoint: {private_address}\n")
            result = run(
                "python3", str(CHECKER), "--root", str(source_root), "--source-tree",
                cwd=source_root, check=False,
            )
            assert_redacted_rule(result, "PRIVATE_NETWORK_IPV4", private_address)

    for cgnat_address in (
        ".".join(("100", "64", "0", "0")),
        ".".join(("100", "127", "255", "255")),
    ):
        with tempfile.TemporaryDirectory(prefix="exo-public-cgnat-boundary-") as raw:
            source_root = Path(raw)
            write(source_root, "README.md", f"fictional endpoint: {cgnat_address}\n")
            result = run(
                "python3", str(CHECKER), "--root", str(source_root), "--source-tree",
                cwd=source_root, check=False,
            )
            assert_redacted_rule(result, "CGNAT_NETWORK_IPV4", cgnat_address)

    with tempfile.TemporaryDirectory(prefix="exo-public-allowed-privacy-") as raw:
        source_root = Path(raw)
        allowed_examples = "\n".join(
            (
                "/Users/<username>/project",
                "%USERPROFILE%\\project",
                "$HOME/project",
                "/path/to/project",
                "/home/runner/work/project",
                "127.0.0.1",
                "192.0.2.1",
                "198.51.100.1",
                "203.0.113.1",
                "2001:db8::1",
                "2001:20::1",
                ".ts.net",
                "fixture@example.com",
                "fixture@example.invalid",
                "fixture@example.net",
                "fixture@example.org",
                "support@docs.example.invalid",
                "support@docs.example.com",
                "support@nested.example",
                "123+bot@users.noreply.github.com",
                "noreply@github.com",
                "security@project.example",
                "Do not run full test suites on Windows.",
                "runner is an M2 Mac mini used for a public fixture.",
                "runner also runs the release pipeline.",
                "This machine runs the release pipeline.",
                "The application runs the release pipeline and service checks.",
                "Do not run full test suites on pull requests.",
                "Do not run complete test suites on server.",
                "The architecture runs the service.",
                "The device hosts an application.",
                "The server runs the release pipeline.",
                "The laptop is an M3 MacBook used for a public fixture.",
                "It runs the application.",
                "This runs the service.",
                "Python runs the application.",
                "This is an M3 MacBook used for a public fixture.",
                ".".join(("9", "255", "255", "255")),
                ".".join(("11", "0", "0", "0")),
                ".".join(("172", "15", "255", "255")),
                ".".join(("172", "32", "0", "0")),
                ".".join(("100", "63", "255", "255")),
                ".".join(("100", "128", "0", "0")),
            )
        )
        write(source_root, "README.md", allowed_examples + "\n")
        result = run(
            "python3", str(CHECKER), "--root", str(source_root), "--source-tree",
            cwd=source_root,
        )
        assert result.stdout == "public_release=pass\n"

    temp, source_root, _ = fixture()
    try:
        write(
            source_root,
            ".gitignore",
            ".exocortex/local/\n.env*\nkey-registry.json\n",
        )
        commit(source_root, "ignore fictional local runtime")
        unreadable_paths = {
            ".exocortex/.env.example",
            ".exocortex/.env/private.txt",
            ".exocortex/key-registry.json",
            "nested/.envrc",
            "nested/config/key-registry.json",
        }
        for relative in unreadable_paths:
            write(source_root, relative, "synthetic credential-adjacent fixture\n")
        run("git", "add", "-f", *sorted(unreadable_paths), cwd=source_root)
        run("git", "commit", "-m", "track synthetic credential path shapes", cwd=source_root)
        for relative in unreadable_paths:
            (source_root / relative).chmod(0)
        write(source_root, "ordinary-untracked.txt", "ordinary public source\n")
        write(
            source_root,
            ".exocortex/local/protocol/runtime.json",
            "fictional ignored runtime\n",
        )
        candidate_root = Path(temp.name) / "candidate"
        copied = materialize_credential_blind_candidate(source_root, candidate_root)
        assert "ordinary-untracked.txt" in copied
        assert (candidate_root / "ordinary-untracked.txt").read_text(
            encoding="utf-8"
        ) == "ordinary public source\n"
        assert ".exocortex/local/protocol/runtime.json" not in copied
        assert unreadable_paths.isdisjoint(copied)
        assert not any((candidate_root / relative).exists() for relative in unreadable_paths)
    finally:
        temp.cleanup()

    with tempfile.TemporaryDirectory(prefix="exo-public-self-scan-") as raw:
        source_root = Path(raw)
        copied = materialize_credential_blind_candidate(TEMPLATE, source_root)
        assert "scripts/check-public-release.py" in copied
        assert "tests/test_public_release.py" in copied
        assert CREDENTIAL_ADJACENT_FIXTURES.isdisjoint(copied)
        self_scan = run(
            "python3", str(CHECKER), "--root", str(source_root), "--source-tree",
            cwd=source_root,
        )
        assert self_scan.stdout == "public_release=pass\n"

    temp, root, baseline = fixture()
    try:
        clean = run("python3", str(CHECKER), "--root", str(root), cwd=root)
        assert clean.stdout == "public_release=pass\n"

        for relative in (
            ".exocortex/events/.gitkeep",
            ".exocortex/events/2000-01-01_00-00-00_example-event.md",
        ):
            write(root, relative, (TEMPLATE / relative).read_text(encoding="utf-8"))
        commit(root, "exact public examples")
        allowed = run("python3", str(CHECKER), "--root", str(root), cwd=root)
        assert allowed.stdout == "public_release=pass\n"
        assert baseline
    finally:
        temp.cleanup()

    temp, root, baseline = fixture()
    try:
        run("git", "config", "user.name", PERSONAL_NAME_CANARY, cwd=root)
        run("git", "config", "user.email", NOREPLY_EMAIL_CANARY, cwd=root)
        write(root, "identity-only.txt")
        candidate = commit(root, "fictional public identity check")
        result = run(
            "python3", str(CHECKER), "--root", str(root), "--baseline", baseline,
            "--candidate", candidate, cwd=root, check=False,
        )
        assert_redacted_rule(result, "NON_PUBLIC_GIT_IDENTITY", PERSONAL_NAME_CANARY)
        assert '"rule": "NON_PUBLIC_EMAIL"' not in result.stdout
        assert '"path_class": "git-object"' in result.stdout
    finally:
        temp.cleanup()

    for name, email in (
        (PERSONAL_NAME_CANARY, "fixture@example.org"),
        ("Fixture", PRIVATE_GIT_EMAIL_CANARY),
        ("Fixture", INVALID_NOREPLY_EMAIL_CANARY),
        ("Fixture", NOREPLY_EMAIL_CANARY),
    ):
        temp, root, baseline = fixture()
        try:
            run("git", "config", "user.name", name, cwd=root)
            run("git", "config", "user.email", email, cwd=root)
            write(root, "identity-boundary.txt")
            candidate = commit(root, "fictional rejected identity")
            result = run(
                "python3", str(CHECKER), "--root", str(root), "--baseline", baseline,
                "--candidate", candidate, cwd=root, check=False,
            )
            assert_redacted_rule(result, "NON_PUBLIC_GIT_IDENTITY", name)
            assert '"path_class": "git-object"' in result.stdout
        finally:
            temp.cleanup()

    temp, root, baseline = fixture()
    try:
        run("git", "config", "user.name", "EnkratFlow Automation", cwd=root)
        run("git", "config", "user.email", "noreply@github.com", cwd=root)
        write(root, "automation-identity.txt")
        candidate = commit(root, "fictional automation identity")
        result = run(
            "python3", str(CHECKER), "--root", str(root), "--baseline", baseline,
            "--candidate", candidate, cwd=root,
        )
        assert result.stdout == "public_release=pass\n"
    finally:
        temp.cleanup()

    temp, root, baseline = fixture()
    try:
        run("git", "config", "user.name", "github-actions[bot]", cwd=root)
        run(
            "git", "config", "user.email",
            "41898282+github-actions[bot]@users.noreply.github.com", cwd=root,
        )
        write(root, "github-automation-identity.txt")
        candidate = commit(root, "fictional GitHub automation identity")
        result = run(
            "python3", str(CHECKER), "--root", str(root), "--baseline", baseline,
            "--candidate", candidate, cwd=root,
        )
        assert result.stdout == "public_release=pass\n"
    finally:
        temp.cleanup()

    temp, root, baseline = fixture()
    try:
        write(root, "message-only.txt")
        candidate = commit(root, f"fictional contact {PERSONAL_EMAIL_CANARY}")
        result = run(
            "python3", str(CHECKER), "--root", str(root), "--baseline", baseline,
            "--candidate", candidate, cwd=root, check=False,
        )
        assert_redacted_rule(result, "NON_PUBLIC_EMAIL", PERSONAL_EMAIL_CANARY)
        assert '"path_class": "git-object"' in result.stdout
    finally:
        temp.cleanup()

    temp, root, baseline = fixture()
    try:
        write(root, "message-only.txt")
        candidate = commit(root, f"fictional commit message {CANARY}")
        result = run(
            "python3", str(CHECKER), "--root", str(root), "--baseline", baseline,
            "--candidate", candidate, cwd=root, check=False,
        )
        assert_rule(result, "GITHUB_TOKEN")
        assert '"path_class": "git-object"' in result.stdout
        assert CANARY not in result.stdout + result.stderr
    finally:
        temp.cleanup()

    temp, root, _ = fixture()
    try:
        run(
            "git", "tag", "-a", "v1.0.1", "-m",
            f"fictional build host {TAILNET_CANARY}", cwd=root,
        )
        result = run(
            "python3", str(CHECKER), "--root", str(root),
            "--tag-object", "v1.0.1", cwd=root, check=False,
        )
        assert_redacted_rule(result, "TAILNET_HOSTNAME", TAILNET_CANARY)
        assert '"path_class": "git-object"' in result.stdout
    finally:
        temp.cleanup()

    temp, root, _ = fixture()
    try:
        run("git", "tag", "-a", "v1.0.0", "-m", f"fictional tag {CANARY}", cwd=root)
        result = run(
            "python3", str(CHECKER), "--root", str(root),
            "--tag-object", "v1.0.0", cwd=root, check=False,
        )
        assert_rule(result, "GITHUB_TOKEN")
        assert '"path_class": "git-object"' in result.stdout
        assert CANARY not in result.stdout + result.stderr
    finally:
        temp.cleanup()

    temp, root, baseline = fixture()
    try:
        write(root, "candidate.txt")
        candidate = commit(root, "candidate")
        run("git", "tag", "-a", "direct", "-m", "direct commit tag", candidate, cwd=root)
        direct = run(
            "python3", str(CHECKER), "--root", str(root), "--baseline", baseline,
            "--candidate", "direct", cwd=root,
        )
        assert direct.stdout == "public_release=pass\n"

        run("git", "tag", "-a", "inner", "-m", "inner commit tag", candidate, cwd=root)
        run("git", "tag", "-a", "outer", "-m", "outer nested tag", "inner", cwd=root)
        outer_headers = run("git", "cat-file", "-p", "outer", cwd=root).stdout
        assert "type tag\n" in outer_headers

        nested_range = run(
            "python3", str(CHECKER), "--root", str(root), "--baseline", baseline,
            "--candidate", "outer", cwd=root, check=False,
        )
        assert nested_range.returncode == 2
        assert "CANDIDATE_TAG_TARGET_INVALID" in nested_range.stderr

        nested_tag = run(
            "python3", str(CHECKER), "--root", str(root), "--tag-object", "outer",
            cwd=root, check=False,
        )
        assert nested_tag.returncode == 2
        assert "TAG_OBJECT_TAG_TARGET_INVALID" in nested_tag.stderr
    finally:
        temp.cleanup()

    temp, root, _ = fixture()
    try:
        relative = f"ordinary-{CANARY}.txt"
        write(root, relative)
        candidate = commit(root, "credential-shaped fictional path")
        result = run(
            "python3", str(CHECKER), "--root", str(root), "--tree", candidate,
            cwd=root, check=False,
        )
        assert_rule(result, "GITHUB_TOKEN")
        assert path_digest(relative) in result.stdout
        assert CANARY not in result.stdout + result.stderr
    finally:
        temp.cleanup()

    for relative in (
        ".exocortex/events/.gitkeep",
        ".exocortex/events/2000-01-01_00-00-00_example-event.md",
    ):
        temp, root, _ = fixture()
        try:
            public_fixture = (TEMPLATE / relative).read_text(encoding="utf-8")
            write(root, relative, public_fixture + "\nPersonalized fictional detail.\n")
            commit(root, "modified data-adjacent public fixture")
            assert_rule(
                run(
                    "python3", str(CHECKER), "--root", str(root), cwd=root,
                    check=False,
                ),
                "DATA_FIXTURE_MODIFIED",
            )
        finally:
            temp.cleanup()

    for relative in sorted(CREDENTIAL_ADJACENT_FIXTURES):
        temp, root, _ = fixture()
        try:
            write(root, relative, "fictional modified metadata fixture\n")
            commit(root, "modified credential-adjacent public fixture")
            assert_rule(
                run(
                    "python3", str(CHECKER), "--root", str(root), cwd=root,
                    check=False,
                ),
                "DATA_FIXTURE_MODIFIED",
            )
        finally:
            temp.cleanup()

    for relative, rule in (
        (".exocortex/SESSION_CONTEXT.md", "SESSION_CONTEXT"),
        (".exocortex/events/2026-08-08_10-00-00_event.md", "EVENT_DATA"),
        (".exocortex/work-items/EXO-1.json", "WORK_ITEM_DATA"),
        (".exocortex/local/protocol/capabilities/grant.json", "LOCAL_PROTOCOL_DATA"),
        (".exocortex/planning/private.md", "PLANNING_RUNTIME_DATA"),
        (".exocortex/SESSION_CONTEXT.md.backup", "SESSION_CONTEXT"),
        (".exocortex/archive/private.md", "PROJECT_RUNTIME_DATA"),
        (".exocortex/control/EXECUTOR_REGISTRY.json", "RUNTIME_CONTROL_REGISTRY"),
        (".env", "ENV_FILE"),
        ("nested/.env.local", "ENV_FILE"),
        ("nested/.envrc", "ENV_FILE"),
    ):
        temp, root, _ = fixture()
        try:
            write(root, relative)
            commit(root, f"fixture {rule}")
            assert_rule(
                run(
                    "python3", str(CHECKER), "--root", str(root), cwd=root,
                    check=False,
                ),
                rule,
            )
        finally:
            temp.cleanup()

    temp, root, _ = fixture()
    try:
        write(root, "nested/.env.production", CANARY + "\n")
        source_tree = run(
            "python3", str(CHECKER), "--root", str(root), "--source-tree",
            cwd=root, check=False,
        )
        assert_rule(source_tree, "ENV_FILE")
        assert "nested/.env.production" not in source_tree.stdout
        assert path_digest("nested/.env.production") in source_tree.stdout
        tracked_only = run("python3", str(CHECKER), "--root", str(root), cwd=root)
        assert tracked_only.stdout == "public_release=pass\n"
    finally:
        temp.cleanup()

    temp, root, baseline = fixture()
    try:
        relative = "transient-private-location.txt"
        write(root, relative, f"fictional location={MAC_HOME_CANARY}\n")
        commit(root, "add transient fictional private location")
        (root / relative).unlink()
        candidate = commit(root, "remove transient fictional private location")
        result = run(
            "python3", str(CHECKER), "--root", str(root), "--baseline", baseline,
            "--candidate", candidate, cwd=root, check=False,
        )
        assert_redacted_rule(result, "ABSOLUTE_HOME_PATH", MAC_HOME_CANARY)
        assert path_digest(relative) in result.stdout
    finally:
        temp.cleanup()

    temp, root, _ = fixture()
    try:
        relative = f"artifact-{PERSONAL_EMAIL_CANARY}.txt"
        write(root, relative)
        candidate = commit(root, "fictional private-address path")
        result = run(
            "python3", str(CHECKER), "--root", str(root), "--tree", candidate,
            cwd=root, check=False,
        )
        assert_redacted_rule(result, "NON_PUBLIC_EMAIL", PERSONAL_EMAIL_CANARY)
        assert path_digest(relative) in result.stdout
    finally:
        temp.cleanup()

    temp, root, _ = fixture()
    try:
        relative = "immutable-private-network.txt"
        write(root, relative, f"fictional endpoint={PRIVATE_IPV4_CANARY}\n")
        candidate = commit(root, "fictional immutable privacy fixture")
        result = run(
            "python3", str(CHECKER), "--root", str(root), "--tree", candidate,
            cwd=root, check=False,
        )
        assert_redacted_rule(result, "PRIVATE_NETWORK_IPV4", PRIVATE_IPV4_CANARY)
        assert path_digest(relative) in result.stdout
    finally:
        temp.cleanup()

    temp, root, _ = fixture()
    try:
        write(root, ".exocortex/TODO.md", "# TODO - a real project\n")
        commit(root, "runtime planning data")
        assert_rule(
            run(
                "python3", str(CHECKER), "--root", str(root), cwd=root,
                check=False,
            ),
            "PLANNING_RUNTIME_DATA",
        )
    finally:
        temp.cleanup()

    for relative in (
        ".exocortex/control/ARCH_OVERVIEW.md",
        ".exocortex/control/REPO_ORGANIZATION_REPORT.md",
    ):
        temp, root, _ = fixture()
        try:
            public_stub = (TEMPLATE / relative).read_text(encoding="utf-8")
            write(root, relative, public_stub)
            commit(root, "exact public planning stub")
            allowed = run("python3", str(CHECKER), "--root", str(root), cwd=root)
            assert allowed.stdout == "public_release=pass\n"

            write(root, relative, public_stub + "\nProject-specific detail.\n")
            commit(root, "personalized planning data")
            assert_rule(
                run(
                    "python3", str(CHECKER), "--root", str(root), cwd=root,
                    check=False,
                ),
                "PLANNING_RUNTIME_DATA",
            )
        finally:
            temp.cleanup()

    temp, root, _ = fixture()
    try:
        write(root, "safe-looking.txt", f"fixture={CANARY}\n")
        commit(root, "current fictional canary")
        assert_rule(
            run(
                "python3", str(CHECKER), "--root", str(root), cwd=root,
                check=False,
            ),
            "GITHUB_TOKEN",
        )
    finally:
        temp.cleanup()

    temp, root, _ = fixture()
    try:
        outside = Path(temp.name) / "outside-canary.txt"
        outside.write_text(CANARY + "\n", encoding="utf-8")
        (root / "README.md").unlink()
        os.symlink(outside, root / "README.md")
        result = run(
            "python3", str(CHECKER), "--root", str(root), cwd=root, check=False,
        )
        assert_rule(result, "SYMLINK")
        assert '"rule": "GITHUB_TOKEN"' not in result.stdout
        assert CANARY not in result.stdout + result.stderr
    finally:
        temp.cleanup()

    temp, root, baseline = fixture()
    try:
        write(root, "transient.txt", f"fixture={CANARY}\n")
        canary_commit = commit(root, "add transient fictional canary")
        (root / "transient.txt").unlink()
        candidate = commit(root, "remove transient fictional canary")
        baseline_tree = run(
            "git", "rev-parse", f"{baseline}^{{tree}}", cwd=root
        ).stdout.strip()
        replacement = run(
            "git", "commit-tree", baseline_tree, "-p", baseline,
            "-m", "replacement fixture",
            cwd=root, check=False,
        )
        if replacement.returncode != 0:
            raise AssertionError(replacement.stderr)
        replacement_commit = replacement.stdout.strip()
        run("git", "replace", canary_commit, replacement_commit, cwd=root)
        result = run(
            "python3", str(CHECKER), "--root", str(root), "--baseline", baseline,
            "--candidate", candidate, cwd=root, check=False,
        )
        assert_rule(result, "GITHUB_TOKEN")
        assert "transient.txt" not in result.stdout
        assert path_digest("transient.txt") in result.stdout
        assert candidate in result.stdout
    finally:
        temp.cleanup()

    temp, root, baseline = fixture()
    try:
        relative = "fine-grained-transient.txt"
        write(root, relative, f"fixture={FINE_GRAINED_CANARY}\n")
        commit(root, "add transient fine-grained fictional canary")
        (root / relative).unlink()
        candidate = commit(root, "remove transient fine-grained fictional canary")
        result = run(
            "python3", str(CHECKER), "--root", str(root), "--baseline", baseline,
            "--candidate", candidate, cwd=root, check=False,
        )
        assert_redacted_rule(result, "GITHUB_FINE_GRAINED_TOKEN", FINE_GRAINED_CANARY)
        assert path_digest(relative) in result.stdout
        assert candidate in result.stdout
    finally:
        temp.cleanup()

    temp, root, baseline = fixture()
    try:
        relative = f"transient-{CANARY}.txt"
        write(root, relative)
        commit(root, "transient credential-shaped fictional path")
        (root / relative).unlink()
        candidate = commit(root, "remove credential-shaped fictional path")
        result = run(
            "python3", str(CHECKER), "--root", str(root), "--baseline", baseline,
            "--candidate", candidate, cwd=root, check=False,
        )
        assert_rule(result, "GITHUB_TOKEN")
        assert path_digest(relative) in result.stdout
        assert CANARY not in result.stdout + result.stderr
    finally:
        temp.cleanup()

    temp, root, baseline = fixture()
    try:
        os.symlink(CANARY, root / "transient-link")
        commit(root, "transient fictional symlink")
        (root / "transient-link").unlink()
        candidate = commit(root, "remove transient fictional symlink")
        result = run(
            "python3", str(CHECKER), "--root", str(root), "--baseline", baseline,
            "--candidate", candidate, cwd=root, check=False,
        )
        assert_rule(result, "SYMLINK")
        assert '"rule": "GITHUB_TOKEN"' not in result.stdout
        assert CANARY not in result.stdout + result.stderr
    finally:
        temp.cleanup()

    temp, root, baseline = fixture()
    try:
        write(root, "tag-only.txt", f"fixture={CANARY}\n")
        candidate = commit(root, "immutable candidate tree canary")
        (root / "tag-only.txt").unlink()
        tree_result = run(
            "python3", str(CHECKER), "--root", str(root), "--tree", candidate,
            cwd=root, check=False,
        )
        assert_rule(tree_result, "GITHUB_TOKEN")
        assert path_digest("tag-only.txt") in tree_result.stdout
        assert baseline
    finally:
        temp.cleanup()

    temp, root, baseline = fixture()
    try:
        # Reuse bytes that were already reachable at the baseline under a safe
        # path. Path-history validation must still catch the transient env name.
        existing = (root / "README.md").read_text(encoding="utf-8")
        write(root, ".env", existing)
        commit(root, "transient forbidden path reusing baseline blob")
        (root / ".env").unlink()
        candidate = commit(root, "remove transient reused blob")
        result = run(
            "python3", str(CHECKER), "--root", str(root), "--baseline", baseline,
            "--candidate", candidate, cwd=root, check=False,
        )
        assert_rule(result, "ENV_FILE")
        assert ".env" not in result.stdout
        assert path_digest(".env") in result.stdout
    finally:
        temp.cleanup()

    temp, root, baseline = fixture()
    try:
        existing = (root / "README.md").read_text(encoding="utf-8")
        write(root, ".exocortex/.env.example", existing)
        commit(root, "transient modified fixture reusing baseline blob")
        (root / ".exocortex/.env.example").unlink()
        candidate = commit(root, "remove transient modified fixture")
        result = run(
            "python3", str(CHECKER), "--root", str(root), "--baseline", baseline,
            "--candidate", candidate, cwd=root, check=False,
        )
        assert_rule(result, "DATA_FIXTURE_MODIFIED")
        assert path_digest(".exocortex/.env.example") in result.stdout
    finally:
        temp.cleanup()

    temp, root, _ = fixture()
    try:
        sensitive_relative = f".exocortex/events/{CANARY}.md"
        write(root, sensitive_relative)
        commit(root, "credential-shaped fictional filename")
        result = run(
            "python3", str(CHECKER), "--root", str(root), cwd=root, check=False,
        )
        assert_rule(result, "EVENT_DATA")
        assert sensitive_relative not in result.stdout
        assert path_digest(sensitive_relative) in result.stdout
    finally:
        temp.cleanup()

    temp, root, _ = fixture()
    try:
        write(root, "historical.txt", f"fixture={CANARY}\n")
        historical = commit(root, "old fictional canary")
        write(root, "later.txt")
        baseline = commit(root, "baseline after historical fixture")
        write(root, "candidate.txt")
        candidate = commit(root, "safe candidate")
        # Remove the historical canary. Its blob is reachable from the baseline,
        # so a range scan must grandfather it rather than claim old history clean.
        (root / "historical.txt").unlink()
        candidate = commit(root, "remove historical canary")
        result = run(
            "python3", str(CHECKER), "--root", str(root), "--baseline", baseline,
            "--candidate", candidate, cwd=root,
        )
        assert result.stdout == "public_release=pass\n"
        assert CANARY not in result.stdout
        assert historical
    finally:
        temp.cleanup()

    temp, root, baseline = fixture()
    try:
        write(root, "candidate.txt")
        candidate = commit(root, "candidate")
        missing = run(
            "python3", str(CHECKER), "--root", str(root), "--baseline", "missing",
            "--candidate", candidate, cwd=root, check=False,
        )
        assert missing.returncode == 2
        assert "BASELINE_COMMIT_INVALID" in missing.stderr

        missing_candidate = run(
            "python3", str(CHECKER), "--root", str(root), "--baseline", baseline,
            "--candidate", "missing", cwd=root, check=False,
        )
        assert missing_candidate.returncode == 2
        assert "CANDIDATE_COMMIT_INVALID" in missing_candidate.stderr

        one_sided = run(
            "python3", str(CHECKER), "--root", str(root), "--baseline", baseline,
            cwd=root, check=False,
        )
        assert one_sided.returncode == 2
        assert "--candidate" in one_sided.stderr

        run("git", "checkout", "-b", "side", baseline, cwd=root)
        write(root, "side.txt")
        side = commit(root, "side candidate")
        run("git", "checkout", "main", cwd=root)
        non_ancestor = run(
            "python3", str(CHECKER), "--root", str(root), "--baseline", side,
            "--candidate", candidate, cwd=root, check=False,
        )
        assert non_ancestor.returncode == 2
        assert "RANGE_NON_ANCESTOR" in non_ancestor.stderr
    finally:
        temp.cleanup()

    temp, root, baseline = fixture()
    try:
        run(
            "git", "tag", "-a", "v1.2.2", "-m", "fictional baseline release",
            baseline, cwd=root,
        )
        baseline_tag_object = run(
            "git", "rev-parse", "v1.2.2", cwd=root
        ).stdout.strip()
        write(root, "cleanup.txt")
        cleanup_commit = commit(root, "fictional cleanup after baseline tag")
        write(
            root,
            ".exocortex/release-baseline.json",
            "{\n"
            '  "schema_version": "public-v1",\n'
            '  "kind": "exocortex_release_baseline",\n'
            '  "previous_published_tag": "v1.2.2",\n'
            f'  "previous_published_commit": "{baseline}"\n'
            "}\n",
        )
        write(root, "release.txt")
        release_commit = commit(root, "fictional release commit")
        run(
            "git", "tag", "-a", "v1.2.3", "-m", "fictional annotated release",
            release_commit, cwd=root,
        )
        tag_object = run("git", "rev-parse", "v1.2.3", cwd=root).stdout.strip()
        remote = Path(temp.name) / "remote.git"
        run("git", "init", "--bare", str(remote), cwd=root)
        run("git", "remote", "add", "origin", str(remote), cwd=root)
        run(
            "git", "push", "origin", "main", "refs/tags/v1.2.2",
            "refs/tags/v1.2.3", cwd=root,
        )
        run("git", "update-ref", "refs/tags/v1.2.3", release_commit, cwd=root)
        assert run("git", "cat-file", "-t", "refs/tags/v1.2.3", cwd=root).stdout.strip() == "commit"

        resolved = annotated_tag_workflow_arguments(root, "v1.2.3", release_commit)
        assert resolved.returncode == 0, resolved.stderr
        assert resolved.stdout.splitlines() == [release_commit, tag_object]

        run(
            "git", "tag", "-a", "rewritten-baseline", "-m",
            "fictional rewritten baseline", cleanup_commit, cwd=root,
        )
        rewritten_baseline_tag_object = run(
            "git", "rev-parse", "rewritten-baseline", cwd=root
        ).stdout.strip()
        run(
            "git", "push", "--force", "origin",
            f"{rewritten_baseline_tag_object}:refs/tags/v1.2.2", cwd=root,
        )
        run(
            "git", "replace", rewritten_baseline_tag_object,
            baseline_tag_object, cwd=root,
        )
        replacement_bypass = annotated_tag_workflow_arguments(
            root, "v1.2.3", release_commit
        )
        assert replacement_bypass.returncode != 0
        run("git", "replace", "-d", rewritten_baseline_tag_object, cwd=root)
        run(
            "git", "push", "--force", "origin",
            f"{baseline_tag_object}:refs/tags/v1.2.2", cwd=root,
        )

        mismatched = annotated_tag_workflow_arguments(root, "v1.2.3", baseline)
        assert mismatched.returncode != 0

        write(
            root,
            ".exocortex/release-baseline.json",
            "{\n"
            '  "schema_version": "public-v1",\n'
            '  "kind": "exocortex_release_baseline",\n'
            '  "previous_published_tag": "v1.2.2",\n'
            f'  "previous_published_commit": "{cleanup_commit}"\n'
            "}\n",
        )
        forged_late = annotated_tag_workflow_arguments(root, "v1.2.3", tag_object)
        assert forged_late.returncode != 0

        write(
            root,
            ".exocortex/release-baseline.json",
            "{\n"
            '  "schema_version": "public-v1",\n'
            '  "kind": "exocortex_release_baseline",\n'
            '  "previous_published_tag": "v1.2.2",\n'
            '  "previous_published_tag": "v1.2.2",\n'
            f'  "previous_published_commit": "{baseline}"\n'
            "}\n",
        )
        duplicate_key = annotated_tag_workflow_arguments(root, "v1.2.3", tag_object)
        assert duplicate_key.returncode != 0
    finally:
        temp.cleanup()

    print("public_release_tests=pass")


if __name__ == "__main__":
    main()
