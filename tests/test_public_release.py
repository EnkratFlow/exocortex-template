#!/usr/bin/env python3
"""Focused fictional-only tests for scripts/check-public-release.py."""

from __future__ import annotations

import hashlib
import os
import subprocess
import sys
import tempfile
from pathlib import Path


TEMPLATE = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
CHECKER = TEMPLATE / "scripts/check-public-release.py"
FIXTURE_EMAIL = "fixture@example.invalid"
CANARY = "gh" + "p_" + "0123456789ABCDEFGHIJKL"
FINE_GRAINED_CANARY = "github" + "_pat_" + "0123456789ABCDEFGHIJKL_mnopqrstuvwxyz"


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

    temp, root, baseline = fixture()
    try:
        clean = run("python3", str(CHECKER), "--root", str(root), cwd=root)
        assert clean.stdout == "public_release=pass\n"

        for relative in (
            ".exocortex/events/.gitkeep",
            ".exocortex/events/2000-01-01_00-00-00_example-event.md",
            ".exocortex/.env.example",
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
        ".exocortex/.env.example",
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
