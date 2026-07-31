#!/bin/bash
# Read-only release closeout check. The operator fetches first; this script
# never contacts a remote or changes refs, the index, or a worktree.

set -euo pipefail
export GIT_OPTIONAL_LOCKS=0

[ "${1:-}" = "--published-digest" ] && [ -n "${2:-}" ] && [ "$#" -eq 2 ] \
    || { echo "Usage: check-release-state.sh --published-digest SHA256" >&2; exit 2; }
PUBLISHED_DIGEST="$2"
if ! [[ "$PUBLISHED_DIGEST" =~ ^[0-9a-f]{64}$ ]]; then
    echo "EXOCORTEX_RELEASE_STATE_INVALID_PUBLISHED_DIGEST" >&2
    exit 1
fi

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
TAG_COMMIT="$(git -C "$ROOT" rev-parse --verify "refs/tags/$TAG_NAME^{commit}" 2>/dev/null)" \
    || fail_state "TAG_MISSING" "$TAG_NAME"
git -C "$ROOT" merge-base --is-ancestor "$TAG_COMMIT" "$TRACKING_MAIN" \
    || fail_state "TAG_NOT_ON_ORIGIN_MAIN" "$TAG_NAME"
TAG_VERSION="$(git -C "$ROOT" show "$TAG_NAME:VERSION" 2>/dev/null | sed -n '1p')" \
    || fail_state "TAG_VERSION_MISSING" "$TAG_NAME"
[ "$TAG_VERSION" = "$VERSION_VALUE" ] \
    || fail_state "TAG_VERSION_MISMATCH" "tag=$TAG_VERSION worktree=$VERSION_VALUE"

TAG_CANDIDATE_DIGEST="$(git -C "$ROOT" show "$TAG_NAME:SHA256SUMS" 2>/dev/null | sha256_stream)" \
    || fail_state "TAG_CHECKSUMS_MISSING" "$TAG_NAME"
[[ "$TAG_CANDIDATE_DIGEST" =~ ^[0-9a-f]{64}$ ]] \
    || fail_state "TAG_CHECKSUMS_INVALID" "$TAG_NAME"
if [ "$TAG_CANDIDATE_DIGEST" != "$PUBLISHED_DIGEST" ]; then
    fail_state "PUBLISHED_DIGEST_MISMATCH" "tag=$TAG_CANDIDATE_DIGEST published=$PUBLISHED_DIGEST"
fi

echo "release_state=pass"
echo "version=$VERSION_VALUE"
echo "local_main=$LOCAL_MAIN"
echo "origin_main=$TRACKING_MAIN"
echo "tag=$TAG_NAME"
echo "tag_commit=$TAG_COMMIT"
echo "tag_candidate_digest=$TAG_CANDIDATE_DIGEST"
