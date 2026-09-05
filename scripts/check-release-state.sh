#!/bin/bash
# Read-only release closeout check. The operator fetches first; this script
# never contacts a remote or changes refs, the index, or a worktree.

set -euo pipefail
export GIT_OPTIONAL_LOCKS=0
export GIT_NO_REPLACE_OBJECTS=1
unset GIT_DIR GIT_WORK_TREE GIT_INDEX_FILE GIT_OBJECT_DIRECTORY \
    GIT_ALTERNATE_OBJECT_DIRECTORIES GIT_COMMON_DIR GIT_NAMESPACE

PUBLISHED_DIGEST=""
BASELINE_TAG=""

usage() {
    echo "Usage: check-release-state.sh --published-digest SHA256 --baseline-tag PREVIOUS_ANNOTATED_TAG" >&2
    exit 2
}

while [ "$#" -gt 0 ]; do
    case "$1" in
        --published-digest) PUBLISHED_DIGEST="${2:-}"; shift 2 ;;
        --baseline-tag) BASELINE_TAG="${2:-}"; shift 2 ;;
        *) usage ;;
    esac
done

[ -n "$PUBLISHED_DIGEST" ] && [ -n "$BASELINE_TAG" ] || usage
if ! [[ "$PUBLISHED_DIGEST" =~ ^[0-9a-f]{64}$ ]]; then
    echo "EXOCORTEX_RELEASE_STATE_INVALID_PUBLISHED_DIGEST" >&2
    exit 1
fi
case "$BASELINE_TAG" in
    v[0-9]*.[0-9]*.[0-9]*) ;;
    *) echo "EXOCORTEX_RELEASE_STATE_INVALID_BASELINE_TAG" >&2; exit 1 ;;
esac

fail_state() {
    local code="$1"
    local detail="${2:-}"
    if [ -n "$detail" ]; then
        echo "EXOCORTEX_RELEASE_STATE_${code}: $detail" >&2
    else
        echo "EXOCORTEX_RELEASE_STATE_${code}" >&2
    fi
    exit 1
}

sha256_stream() {
    if command -v shasum >/dev/null 2>&1; then
        shasum -a 256 | awk '{print $1}'
    elif command -v sha256sum >/dev/null 2>&1; then
        sha256sum | awk '{print $1}'
    else
        fail_state "HASH_TOOL_MISSING" "shasum or sha256sum is required"
    fi
}

ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" \
    || fail_state "NOT_A_GIT_REPOSITORY"
LOCAL_MAIN="$(git -C "$ROOT" rev-parse --verify refs/heads/main 2>/dev/null)" \
    || fail_state "LOCAL_MAIN_MISSING"
TRACKING_MAIN="$(git -C "$ROOT" rev-parse --verify refs/remotes/origin/main 2>/dev/null)" \
    || fail_state "ORIGIN_MAIN_MISSING" "fetch origin before running the closeout check"
[ "$LOCAL_MAIN" = "$TRACKING_MAIN" ] \
    || fail_state "LOCAL_MAIN_DRIFT" "local=$LOCAL_MAIN origin=$TRACKING_MAIN"

MAIN_WORKTREE="$(git -C "$ROOT" worktree list --porcelain | awk '
    /^worktree / { path=substr($0,10) }
    /^branch refs\/heads\/main$/ { print path; exit }
')"
[ -n "$MAIN_WORKTREE" ] && [ -d "$MAIN_WORKTREE" ] \
    || fail_state "MAIN_WORKTREE_MISSING"
[ -z "$(git -C "$MAIN_WORKTREE" status --porcelain=v1)" ] \
    || fail_state "MAIN_WORKTREE_DIRTY" "$MAIN_WORKTREE"

VERSION_VALUE="$(git -C "$ROOT" show refs/heads/main:VERSION 2>/dev/null | sed -n '1p')" \
    || fail_state "VERSION_MISSING" "refs/heads/main:VERSION"
[[ "$VERSION_VALUE" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] \
    || fail_state "VERSION_INVALID" "$VERSION_VALUE"

TAG_NAME="v$VERSION_VALUE"
TAG_OBJECT_TYPE="$(git -C "$ROOT" cat-file -t "refs/tags/$TAG_NAME" 2>/dev/null)" \
    || fail_state "TAG_MISSING" "$TAG_NAME"
[ "$TAG_OBJECT_TYPE" = "tag" ] || fail_state "TAG_NOT_ANNOTATED" "$TAG_NAME"
TAG_OBJECT_ID="$(git -C "$ROOT" rev-parse --verify "refs/tags/$TAG_NAME" 2>/dev/null)" \
    || fail_state "TAG_MISSING" "$TAG_NAME"
TAG_COMMIT="$(git -C "$ROOT" rev-parse --verify "refs/tags/$TAG_NAME^{commit}" 2>/dev/null)" \
    || fail_state "TAG_MISSING" "$TAG_NAME"
[ "$TAG_COMMIT" = "$TRACKING_MAIN" ] \
    || fail_state "TAG_MAIN_MISMATCH" "tag=$TAG_COMMIT origin=$TRACKING_MAIN"

BASELINE_OBJECT_TYPE="$(git -C "$ROOT" cat-file -t "refs/tags/$BASELINE_TAG" 2>/dev/null)" \
    || fail_state "BASELINE_TAG_MISSING" "$BASELINE_TAG"
[ "$BASELINE_OBJECT_TYPE" = "tag" ] \
    || fail_state "BASELINE_TAG_NOT_ANNOTATED" "$BASELINE_TAG"
BASELINE_TAG_OBJECT_ID="$(git -C "$ROOT" rev-parse --verify "refs/tags/$BASELINE_TAG" 2>/dev/null)" \
    || fail_state "BASELINE_TAG_MISSING" "$BASELINE_TAG"
BASELINE_DIRECT_TARGET="$(git -C "$ROOT" cat-file -p "$BASELINE_TAG_OBJECT_ID" \
    | sed -n 's/^object //p' | head -n 1)"
BASELINE_DIRECT_TARGET_TYPE="$(git -C "$ROOT" cat-file -p "$BASELINE_TAG_OBJECT_ID" \
    | sed -n 's/^type //p' | head -n 1)"
[ "$BASELINE_DIRECT_TARGET_TYPE" = "commit" ] \
    && [[ "$BASELINE_DIRECT_TARGET" =~ ^[0-9a-f]{40,64}$ ]] \
    && [ "$(git -C "$ROOT" cat-file -t "$BASELINE_DIRECT_TARGET" 2>/dev/null)" = "commit" ] \
    || fail_state "BASELINE_TAG_DIRECT_TARGET_INVALID" "$BASELINE_TAG"
BASELINE_COMMIT="$BASELINE_DIRECT_TARGET"
[ "$BASELINE_COMMIT" != "$TAG_COMMIT" ] \
    || fail_state "BASELINE_EQUALS_RELEASE" "$BASELINE_TAG"
git -C "$ROOT" merge-base --is-ancestor "$BASELINE_COMMIT" "$TAG_COMMIT" \
    || fail_state "BASELINE_NOT_ANCESTOR" "$BASELINE_TAG"

TAG_VERSION="$(git -C "$ROOT" show "$TAG_COMMIT:VERSION" 2>/dev/null | sed -n '1p')" \
    || fail_state "TAG_VERSION_MISSING" "$TAG_NAME"
[ "$TAG_VERSION" = "$VERSION_VALUE" ] \
    || fail_state "TAG_VERSION_MISMATCH" "tag=$TAG_VERSION worktree=$VERSION_VALUE"

PYTHON_BIN="$(command -v python3)" || fail_state "PYTHON_MISSING"
case "$PYTHON_BIN" in /*) ;; *) fail_state "PYTHON_PATH_INVALID" ;; esac
CHECK_PATH="$(dirname "$PYTHON_BIN"):/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:/opt/homebrew/bin"
CLOSEOUT_TMP="$(mktemp -d "${TMPDIR:-/tmp}/exocortex-release-state.XXXXXX")" \
    || fail_state "PRIVATE_TEMP_FAILED"
chmod 0700 "$CLOSEOUT_TMP"
mkdir -p "$CLOSEOUT_TMP/home" "$CLOSEOUT_TMP/tmp"
trap 'rm -rf "$CLOSEOUT_TMP"' EXIT

TAG_SUMS="$CLOSEOUT_TMP/SHA256SUMS"
TAG_PUBLIC_CHECKER="$CLOSEOUT_TMP/check-public-release.py"
TAG_BASELINE_RECORD="$CLOSEOUT_TMP/release-baseline.json"
git -C "$ROOT" show "$TAG_COMMIT:SHA256SUMS" > "$TAG_SUMS" 2>/dev/null \
    || fail_state "TAG_CHECKSUMS_MISSING" "$TAG_NAME"
chmod 0600 "$TAG_SUMS"
TAG_CANDIDATE_DIGEST="$(sha256_stream < "$TAG_SUMS")" \
    || fail_state "TAG_CHECKSUMS_MISSING" "$TAG_NAME"
[[ "$TAG_CANDIDATE_DIGEST" =~ ^[0-9a-f]{64}$ ]] \
    || fail_state "TAG_CHECKSUMS_INVALID" "$TAG_NAME"
[ "$TAG_CANDIDATE_DIGEST" = "$PUBLISHED_DIGEST" ] \
    || fail_state "PUBLISHED_DIGEST_MISMATCH" "tag=$TAG_CANDIDATE_DIGEST published=$PUBLISHED_DIGEST"

# Bind the previous published baseline to candidate-owned, checksum-covered
# metadata. The caller may name it for clarity but cannot move the scan start.
git -C "$ROOT" show "$TAG_COMMIT:.exocortex/release-baseline.json" > "$TAG_BASELINE_RECORD" 2>/dev/null \
    || fail_state "BASELINE_RECORD_MISSING" "$TAG_NAME"
chmod 0600 "$TAG_BASELINE_RECORD"
EXPECTED_BASELINE_RECORD_HASH="$(awk 'substr($0,67)==".exocortex/release-baseline.json" {print substr($0,1,64)}' "$TAG_SUMS")"
[[ "$EXPECTED_BASELINE_RECORD_HASH" =~ ^[0-9a-f]{64}$ ]] \
    || fail_state "BASELINE_RECORD_UNBOUND" "$TAG_NAME"
ACTUAL_BASELINE_RECORD_HASH="$(sha256_stream < "$TAG_BASELINE_RECORD")"
[ "$ACTUAL_BASELINE_RECORD_HASH" = "$EXPECTED_BASELINE_RECORD_HASH" ] \
    || fail_state "BASELINE_RECORD_DIGEST_MISMATCH" "$TAG_NAME"
BASELINE_RECORD_VALUES="$(
    cd "$CLOSEOUT_TMP"
    env -i PATH="$CHECK_PATH" HOME="$CLOSEOUT_TMP/home" TMPDIR="$CLOSEOUT_TMP/tmp" \
        LC_ALL=C LANG=C PYTHONDONTWRITEBYTECODE=1 \
        "$PYTHON_BIN" - "$TAG_BASELINE_RECORD" "$TAG_VERSION" <<'PY'
import json
import re
import sys

def no_duplicates(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("duplicate key")
        value[key] = item
    return value

with open(sys.argv[1], encoding="utf-8") as stream:
    value = json.load(stream, object_pairs_hook=no_duplicates)
expected = {
    "schema_version",
    "kind",
    "previous_published_tag",
    "previous_published_commit",
}
if set(value) != expected or value["schema_version"] != "public-v1" or value["kind"] != "exocortex_release_baseline":
    raise SystemExit(1)
tag = value["previous_published_tag"]
commit = value["previous_published_commit"]
match = re.fullmatch(r"v([0-9]+)\.([0-9]+)\.([0-9]+)", tag)
release = re.fullmatch(r"([0-9]+)\.([0-9]+)\.([0-9]+)", sys.argv[2])
if match is None or release is None or re.fullmatch(r"[0-9a-f]{40,64}", commit) is None:
    raise SystemExit(1)
if tuple(map(int, match.groups())) >= tuple(map(int, release.groups())):
    raise SystemExit(1)
print(f"{tag}\t{commit}")
PY
)" || fail_state "BASELINE_RECORD_INVALID" "$TAG_NAME"
IFS=$'\t' read -r RECORDED_BASELINE_TAG RECORDED_BASELINE_COMMIT <<< "$BASELINE_RECORD_VALUES"
[ "$BASELINE_TAG" = "$RECORDED_BASELINE_TAG" ] \
    || fail_state "BASELINE_RECORD_TAG_MISMATCH" "requested=$BASELINE_TAG recorded=$RECORDED_BASELINE_TAG"
[ "$BASELINE_COMMIT" = "$RECORDED_BASELINE_COMMIT" ] \
    || fail_state "BASELINE_RECORD_COMMIT_MISMATCH" "$BASELINE_TAG"

# A reviewed release normally lands as a merge commit. Its first parent is the
# already-public main state before the reviewed release slice; the other parent
# carries the reviewed candidate commits. Keep the previous published release
# as the ancestry/version anchor, but do not retroactively classify older public
# Git history as downloadable release content.
RELEASE_RANGE_BASE="$BASELINE_COMMIT"
TAG_PARENT_COUNT="$(git -C "$ROOT" rev-list --parents -n 1 "$TAG_COMMIT" \
    | awk '{print NF - 1}')" \
    || fail_state "TAG_PARENT_COUNT_INVALID" "$TAG_NAME"
[[ "$TAG_PARENT_COUNT" =~ ^[0-9]+$ ]] \
    || fail_state "TAG_PARENT_COUNT_INVALID" "$TAG_NAME"
if [ "$TAG_PARENT_COUNT" -ge 2 ]; then
    RELEASE_RANGE_BASE="$(git -C "$ROOT" rev-parse --verify "$TAG_COMMIT^1" 2>/dev/null)" \
        || fail_state "TAG_RELEASE_RANGE_BASE_INVALID" "$TAG_NAME"
    git -C "$ROOT" merge-base --is-ancestor "$BASELINE_COMMIT" "$RELEASE_RANGE_BASE" \
        || fail_state "TAG_RELEASE_RANGE_BASE_NOT_DESCENDANT" "$BASELINE_TAG..$TAG_NAME"
fi

# Extract the checker from the immutable candidate commit into an owner-private
# directory. Its directory contains no worktree modules that can shadow Python
# standard-library imports.
git -C "$ROOT" show "$TAG_COMMIT:scripts/check-public-release.py" > "$TAG_PUBLIC_CHECKER" 2>/dev/null \
    || fail_state "PUBLIC_CHECKER_MISSING" "$TAG_NAME"
chmod 0600 "$TAG_PUBLIC_CHECKER"
EXPECTED_CHECKER_HASH="$(awk 'substr($0,67)=="scripts/check-public-release.py" {print substr($0,1,64)}' "$TAG_SUMS")"
[[ "$EXPECTED_CHECKER_HASH" =~ ^[0-9a-f]{64}$ ]] \
    || fail_state "PUBLIC_CHECKER_UNBOUND" "$TAG_NAME"
ACTUAL_CHECKER_HASH="$(sha256_stream < "$TAG_PUBLIC_CHECKER")"
[ "$ACTUAL_CHECKER_HASH" = "$EXPECTED_CHECKER_HASH" ] \
    || fail_state "PUBLIC_CHECKER_DIGEST_MISMATCH" "$TAG_NAME"
(
    cd "$CLOSEOUT_TMP"
    env -i PATH="$CHECK_PATH" HOME="$CLOSEOUT_TMP/home" TMPDIR="$CLOSEOUT_TMP/tmp" \
        LC_ALL=C LANG=C PYTHONDONTWRITEBYTECODE=1 \
        "$PYTHON_BIN" "$TAG_PUBLIC_CHECKER" --root "$ROOT" --tree "$TAG_COMMIT" \
        --baseline "$RELEASE_RANGE_BASE" --candidate "$TAG_COMMIT" \
        --tag-object "$TAG_OBJECT_ID" >/dev/null
) || fail_state "PUBLIC_BOUNDARY_FAILED" "$BASELINE_TAG..$TAG_NAME"

# Revalidate all mutable refs and the main worktree after the immutable checks.
FINAL_LOCAL_MAIN="$(git -C "$ROOT" rev-parse --verify refs/heads/main 2>/dev/null)" \
    || fail_state "STATE_CHANGED_DURING_CHECK"
FINAL_TRACKING_MAIN="$(git -C "$ROOT" rev-parse --verify refs/remotes/origin/main 2>/dev/null)" \
    || fail_state "STATE_CHANGED_DURING_CHECK"
FINAL_TAG_OBJECT_ID="$(git -C "$ROOT" rev-parse --verify "refs/tags/$TAG_NAME" 2>/dev/null)" \
    || fail_state "STATE_CHANGED_DURING_CHECK"
FINAL_BASELINE_TAG_OBJECT_ID="$(git -C "$ROOT" rev-parse --verify "refs/tags/$BASELINE_TAG" 2>/dev/null)" \
    || fail_state "STATE_CHANGED_DURING_CHECK"
[ "$FINAL_LOCAL_MAIN" = "$LOCAL_MAIN" ] \
    && [ "$FINAL_TRACKING_MAIN" = "$TRACKING_MAIN" ] \
    && [ "$FINAL_TAG_OBJECT_ID" = "$TAG_OBJECT_ID" ] \
    && [ "$FINAL_BASELINE_TAG_OBJECT_ID" = "$BASELINE_TAG_OBJECT_ID" ] \
    || fail_state "STATE_CHANGED_DURING_CHECK"
FINAL_STATUS="$(git -C "$MAIN_WORKTREE" status --porcelain=v1)" \
    || fail_state "STATE_CHANGED_DURING_CHECK"
[ -z "$FINAL_STATUS" ] || fail_state "MAIN_WORKTREE_DIRTY" "$MAIN_WORKTREE"

echo "release_state=pass"
echo "version=$VERSION_VALUE"
echo "local_main=$LOCAL_MAIN"
echo "origin_main=$TRACKING_MAIN"
echo "baseline_tag=$BASELINE_TAG"
echo "baseline_commit=$BASELINE_COMMIT"
echo "release_range_base=$RELEASE_RANGE_BASE"
echo "tag=$TAG_NAME"
echo "tag_commit=$TAG_COMMIT"
echo "tag_candidate_digest=$TAG_CANDIDATE_DIGEST"
