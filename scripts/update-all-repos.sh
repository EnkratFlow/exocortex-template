#!/bin/bash
# update-all-repos.sh — batch-update every exocortex-installed project under a root
#
# USAGE:
#   bash scripts/update-all-repos.sh <root_dir> [--yes] [--dry-run]
#
# EXAMPLES:
#   bash scripts/update-all-repos.sh ~/code
#   bash scripts/update-all-repos.sh ~/code --yes        # no prompts
#   bash scripts/update-all-repos.sh ~/code --dry-run    # list, don't run
#
# WHAT IT DOES:
#   1. Walks <root_dir> looking for any directory that contains a `.exocortex/` subdir.
#   2. For each match, optionally prompts before running install.sh.
#   3. Skips repos with a dirty git working tree (uncommitted changes) — they're shown but skipped to avoid clobbering work in progress.
#   4. Runs install.sh in update mode using EXOCORTEX_LOCAL_SOURCE pointing at this template repo, so all targets get the exact same version.
#   5. Logs each result and prints a summary at the end.
#
# REQUIREMENTS: bash, git, this template repo on disk.

set -u

usage() {
    sed -n '2,/^$/p' "$0" | sed 's/^# \{0,1\}//'
    exit 1
}

ROOT="${1:-}"
[ -z "$ROOT" ] && usage
[ ! -d "$ROOT" ] && { echo "❌ Not a directory: $ROOT"; exit 1; }

shift
YES=false
DRY_RUN=false
for arg in "$@"; do
    case "$arg" in
        --yes|-y)     YES=true ;;
        --dry-run|-n) DRY_RUN=true ;;
        *) echo "❌ Unknown flag: $arg"; usage ;;
    esac
done

# Resolve template repo: this script lives at <template>/scripts/update-all-repos.sh
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEMPLATE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

if [ ! -f "$TEMPLATE_DIR/install.sh" ]; then
    echo "❌ Could not locate install.sh next to scripts/. Expected at: $TEMPLATE_DIR/install.sh"
    exit 1
fi

TEMPLATE_VERSION="unknown"
[ -f "$TEMPLATE_DIR/VERSION" ] && TEMPLATE_VERSION="$(tr -d '[:space:]' < "$TEMPLATE_DIR/VERSION")"

echo ""
echo "🧠 Exocortex batch updater"
echo "   Root:      $ROOT"
echo "   Template:  $TEMPLATE_DIR (v$TEMPLATE_VERSION)"
echo "   Mode:      $([ "$DRY_RUN" = true ] && echo 'DRY RUN' || echo 'live')"
$YES && echo "   Auto-yes:  on"
echo ""

# Find candidates: any dir whose immediate child is .exocortex/
CANDIDATES=()
while IFS= read -r repo; do
    [ -n "$repo" ] && CANDIDATES+=("$repo")
done < <(find "$ROOT" -maxdepth 4 -type d -name '.exocortex' -prune 2>/dev/null \
    | sed 's|/\.exocortex$||' \
    | sort -u)

if [ "${#CANDIDATES[@]}" -eq 0 ]; then
    echo "  No exocortex-installed projects found under $ROOT"
    exit 0
fi

echo "Found ${#CANDIDATES[@]} candidate(s):"
for repo in "${CANDIDATES[@]}"; do
    echo "  • $repo"
done
echo ""

[ "$DRY_RUN" = true ] && { echo "Dry run complete."; exit 0; }

UPDATED=()
SKIPPED_DIRTY=()
SKIPPED_USER=()
FAILED=()

for repo in "${CANDIDATES[@]}"; do
    echo "────────────────────────────────────────"
    echo "📁 $repo"

    # Skip self
    if [ "$repo" = "$TEMPLATE_DIR" ]; then
        echo "  ⊘ skip — this is the template repo itself"
        SKIPPED_USER+=("$repo (template)")
        continue
    fi

    # Skip dirty git repos
    if [ -d "$repo/.git" ]; then
        if [ -n "$(git -C "$repo" status --porcelain 2>/dev/null)" ]; then
            echo "  ⊘ skip — dirty working tree (commit or stash first)"
            SKIPPED_DIRTY+=("$repo")
            continue
        fi
    fi

    INSTALLED_VERSION="unknown"
    if [ -f "$repo/.exocortex/.version" ]; then
        INSTALLED_VERSION="$(tr -d '[:space:]' < "$repo/.exocortex/.version")"
    fi
    echo "  Currently installed: $INSTALLED_VERSION → would update to: $TEMPLATE_VERSION"

    if [ "$YES" = false ]; then
        read -r -p "  Update this repo? [y/N/q] " reply
        case "$reply" in
            q|Q) echo "  Quit requested. Stopping."; break ;;
            y|Y) ;;
            *) echo "  ⊘ skip — user declined"; SKIPPED_USER+=("$repo"); continue ;;
        esac
    fi

    if (cd "$repo" && EXOCORTEX_LOCAL_SOURCE="$TEMPLATE_DIR" bash "$TEMPLATE_DIR/install.sh" 2>&1 | tail -20); then
        echo "  ✓ updated"
        UPDATED+=("$repo")
    else
        echo "  ❌ install.sh failed"
        FAILED+=("$repo")
    fi
done

echo ""
echo "════════════════════════════════════════"
echo "  Summary"
echo "════════════════════════════════════════"
echo "  ✓ Updated:       ${#UPDATED[@]}"
echo "  ⊘ Skipped (dirty): ${#SKIPPED_DIRTY[@]}"
echo "  ⊘ Skipped (other): ${#SKIPPED_USER[@]}"
echo "  ❌ Failed:        ${#FAILED[@]}"
echo ""
[ "${#SKIPPED_DIRTY[@]}" -gt 0 ] && { echo "Dirty repos (commit or stash, then re-run):"; printf '  • %s\n' "${SKIPPED_DIRTY[@]}"; echo ""; }
[ "${#FAILED[@]}" -gt 0 ] && { echo "Failed repos:"; printf '  • %s\n' "${FAILED[@]}"; exit 1; }
exit 0
