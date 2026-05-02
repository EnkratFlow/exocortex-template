#!/bin/bash
# safe-update.sh - customer-safe Exocortex update workflow
#
# Run from the project root that contains .exocortex/.
#
# Usage:
#   bash scripts/safe-update.sh [--yes] [--dry-run] [--template /path/to/exocortex-template]
#
# What it does:
#   1. Creates a timestamped restore archive.
#   2. Uses a local template source or downloads the latest template.
#   3. Rehearses the update in /tmp.
#   4. Verifies sovereign data is unchanged in the rehearsal.
#   5. Shows what would change.
#   6. Applies the real update only after approval, unless --yes is used.

set -euo pipefail

REPO_URL="https://github.com/EnkratFlow/exocortex-template.git"
BRANCH="main"

YES=false
DRY_RUN=false
TEMPLATE_SOURCE="${EXOCORTEX_LOCAL_SOURCE:-}"
BACKUP_DIR="${EXOCORTEX_BACKUP_DIR:-$HOME/exocortex-restore-points}"

usage() {
    sed -n '2,/^$/p' "$0" | sed 's/^# \{0,1\}//'
    exit 1
}

while [ "$#" -gt 0 ]; do
    case "$1" in
        --yes|-y)
            YES=true
            shift
            ;;
        --dry-run|-n)
            DRY_RUN=true
            shift
            ;;
        --template)
            TEMPLATE_SOURCE="${2:-}"
            [ -z "$TEMPLATE_SOURCE" ] && { echo "Error: --template requires a path"; exit 1; }
            shift 2
            ;;
        --backup-dir)
            BACKUP_DIR="${2:-}"
            [ -z "$BACKUP_DIR" ] && { echo "Error: --backup-dir requires a path"; exit 1; }
            shift 2
            ;;
        --help|-h)
            usage
            ;;
        *)
            echo "Error: unknown argument: $1"
            usage
            ;;
    esac
done

PROJECT_ROOT="$(pwd)"
PROJECT_NAME="$(basename "$PROJECT_ROOT")"

if [ ! -d "$PROJECT_ROOT/.exocortex" ]; then
    echo "Error: no .exocortex directory found in $PROJECT_ROOT"
    echo "Run this from the root of a project that already has Exocortex installed."
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT_TEMPLATE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

WORK_DIR="$(mktemp -d "${TMPDIR:-/tmp}/exocortex-safe-update.XXXXXX")"
REHEARSAL_DIR="$WORK_DIR/${PROJECT_NAME}-rehearsal"
DIFF_FILE="$WORK_DIR/rehearsal-diff.txt"
PROTECTED_DIFF_FILE="$WORK_DIR/protected-diff.txt"
TEMPLATE_DIR="$WORK_DIR/exocortex-template"

cleanup() {
    if [ "${EXOCORTEX_KEEP_SAFE_UPDATE_TMP:-0}" != "1" ]; then
        rm -rf "$WORK_DIR"
    else
        echo "Temporary work directory kept: $WORK_DIR"
    fi
}
trap cleanup EXIT

resolve_template() {
    if [ -n "$TEMPLATE_SOURCE" ]; then
        if [ ! -d "$TEMPLATE_SOURCE" ] || [ ! -f "$TEMPLATE_SOURCE/install.sh" ]; then
            echo "Error: template source is not a valid exocortex-template directory: $TEMPLATE_SOURCE"
            exit 1
        fi
        TEMPLATE_DIR="$(cd "$TEMPLATE_SOURCE" && pwd)"
        return
    fi

    if [ -f "$SCRIPT_TEMPLATE_DIR/install.sh" ] && [ -f "$SCRIPT_TEMPLATE_DIR/VERSION" ]; then
        TEMPLATE_DIR="$SCRIPT_TEMPLATE_DIR"
        return
    fi

    if ! command -v git >/dev/null 2>&1; then
        echo "Error: git is required to download the latest exocortex-template."
        exit 1
    fi

    git clone --quiet --depth 1 --branch "$BRANCH" "$REPO_URL" "$TEMPLATE_DIR"
}

copy_if_exists() {
    local name="$1"
    if [ -e "$PROJECT_ROOT/$name" ]; then
        mkdir -p "$(dirname "$REHEARSAL_DIR/$name")"
        if command -v rsync >/dev/null 2>&1; then
            rsync -a "$PROJECT_ROOT/$name" "$REHEARSAL_DIR/$(dirname "$name")/" 2>/dev/null
        else
            cp -R "$PROJECT_ROOT/$name" "$REHEARSAL_DIR/$(dirname "$name")/"
        fi
    fi
}

make_restore_point() {
    mkdir -p "$BACKUP_DIR"
    BACKUP_PATH="$BACKUP_DIR/${PROJECT_NAME}-exocortex-before-update-$(date +%Y%m%d-%H%M%S).tar.gz"

    local items=()
    local item
    for item in \
        ".exocortex" \
        ".cursor" \
        ".claude" \
        ".github" \
        "CLAUDE.md" \
        ".windsurfrules" \
        ".rules" \
        ".gitignore"
    do
        [ -e "$PROJECT_ROOT/$item" ] && items+=("$item")
    done

    if [ "${#items[@]}" -eq 0 ]; then
        echo "Error: nothing found to back up."
        exit 1
    fi

    (cd "$PROJECT_ROOT" && tar -czf "$BACKUP_PATH" "${items[@]}")
}

build_rehearsal() {
    mkdir -p "$REHEARSAL_DIR"
    copy_if_exists ".exocortex"
    copy_if_exists ".cursor"
    copy_if_exists ".claude"
    copy_if_exists ".github"
    copy_if_exists "CLAUDE.md"
    copy_if_exists ".windsurfrules"
    copy_if_exists ".rules"
    copy_if_exists ".gitignore"
}

run_installer_in() {
    local target="$1"
    (cd "$target" && EXOCORTEX_LOCAL_SOURCE="$TEMPLATE_DIR" bash "$TEMPLATE_DIR/install.sh")
}

protected_paths=(
    ".exocortex/SESSION_CONTEXT.md"
    ".exocortex/TODO.md"
    ".exocortex/LESSONS.md"
    ".exocortex/PROJECT_MEMORY.md"
    ".exocortex/OPEN_DECISIONS.md"
    ".exocortex/.env"
    ".exocortex/events"
    ".exocortex/local"
    ".exocortex/control/INTERRUPTS.md"
    ".exocortex/control/BACKLOG.md"
    ".exocortex/control/ROADMAP.md"
    ".exocortex/control/ARCH_OVERVIEW.md"
    ".exocortex/control/REPO_ORGANIZATION_REPORT.md"
)

is_allowed_created_stub() {
    local rel="$1"
    local file="$2"

    [ -f "$file" ] || return 1

    case "$rel" in
        ".exocortex/SESSION_CONTEXT.md")
            grep -q "_No active session context yet" "$file"
            ;;
        ".exocortex/TODO.md")
            grep -q "_No tasks captured yet" "$file"
            ;;
        ".exocortex/LESSONS.md")
            grep -q "_No lessons captured yet" "$file"
            ;;
        ".exocortex/PROJECT_MEMORY.md")
            grep -q "_No project-specific memory captured yet" "$file"
            ;;
        ".exocortex/control/INTERRUPTS.md")
            grep -q "_No interrupts captured yet" "$file"
            ;;
        ".exocortex/control/BACKLOG.md")
            grep -q "_No backlog items yet" "$file"
            ;;
        ".exocortex/control/ROADMAP.md")
            grep -q "_No roadmap defined yet" "$file"
            ;;
        *)
            return 1
            ;;
    esac
}

verify_protected_unchanged() {
    local left="$1"
    local right="$2"
    : > "$PROTECTED_DIFF_FILE"

    local path
    for path in "${protected_paths[@]}"; do
        if [ -e "$left/$path" ] && [ -e "$right/$path" ]; then
            diff -rq "$left/$path" "$right/$path" >> "$PROTECTED_DIFF_FILE" 2>&1 || true
        elif [ -e "$left/$path" ] || [ -e "$right/$path" ]; then
            local existing
            if [ -e "$left/$path" ]; then
                existing="$left/$path"
            else
                existing="$right/$path"
            fi

            # Empty protected directories may be created by setup logic and do
            # not represent sovereign data drift. Any missing/present file, or
            # non-empty directory, is still treated as a protected change.
            if [ -d "$existing" ] && [ -z "$(find "$existing" -mindepth 1 -print -quit 2>/dev/null)" ]; then
                continue
            fi

            if is_allowed_created_stub "$path" "$existing"; then
                continue
            fi

            echo "Only one side has protected path: $path" >> "$PROTECTED_DIFF_FILE"
        fi
    done

    if [ -s "$PROTECTED_DIFF_FILE" ]; then
        echo ""
        echo "ERROR: protected Exocortex data would change:"
        sed -n '1,120p' "$PROTECTED_DIFF_FILE"
        echo ""
        echo "Aborting. Restore archive is available at:"
        echo "  $BACKUP_PATH"
        exit 1
    fi
}

print_diff_summary() {
    diff -rq "$PROJECT_ROOT/.exocortex" "$REHEARSAL_DIR/.exocortex" > "$DIFF_FILE" 2>&1 || true

    echo ""
    echo "Rehearsal summary:"
    if [ -s "$DIFF_FILE" ]; then
        sed -n '1,120p' "$DIFF_FILE"
    else
        echo "  No .exocortex file differences detected."
    fi
}

echo ""
echo "Exocortex safe update"
echo "Project:  $PROJECT_ROOT"

CURRENT_VERSION="unknown"
[ -f "$PROJECT_ROOT/.exocortex/.version" ] && CURRENT_VERSION="$(tr -d '[:space:]' < "$PROJECT_ROOT/.exocortex/.version")"
echo "Current:  $CURRENT_VERSION"

resolve_template

TARGET_VERSION="unknown"
[ -f "$TEMPLATE_DIR/VERSION" ] && TARGET_VERSION="$(tr -d '[:space:]' < "$TEMPLATE_DIR/VERSION")"
echo "Template: $TEMPLATE_DIR (v$TARGET_VERSION)"

make_restore_point
echo "Backup:   $BACKUP_PATH"

echo ""
echo "Rehearsing update in: $REHEARSAL_DIR"
build_rehearsal
run_installer_in "$REHEARSAL_DIR"
verify_protected_unchanged "$PROJECT_ROOT" "$REHEARSAL_DIR"
print_diff_summary

echo ""
echo "Protected data check: PASS"
echo "Protected files/directories were unchanged in rehearsal."

if [ "$DRY_RUN" = true ]; then
    echo ""
    echo "Dry run complete. No real project files were changed."
    echo "Restore archive is already available at:"
    echo "  $BACKUP_PATH"
    exit 0
fi

if [ "$YES" != true ]; then
    if [ ! -t 0 ]; then
        echo ""
        echo "No TTY available for approval. Re-run with --yes to apply after rehearsal."
        exit 1
    fi

    echo ""
    read -r -p "Apply this update to the real project now? [y/N] " reply
    case "$reply" in
        y|Y|yes|YES) ;;
        *)
            echo "Stopped before real update. No project files changed."
            echo "Restore archive is available at:"
            echo "  $BACKUP_PATH"
            exit 0
            ;;
    esac
fi

echo ""
echo "Applying real update..."
run_installer_in "$PROJECT_ROOT"
verify_protected_unchanged "$REHEARSAL_DIR" "$PROJECT_ROOT"

NEW_VERSION="unknown"
[ -f "$PROJECT_ROOT/.exocortex/.version" ] && NEW_VERSION="$(tr -d '[:space:]' < "$PROJECT_ROOT/.exocortex/.version")"

echo ""
echo "Exocortex safe update complete."
echo "Version: $CURRENT_VERSION -> $NEW_VERSION"
echo "Backup:  $BACKUP_PATH"
echo ""
echo "Rollback if needed:"
echo "  cd \"$PROJECT_ROOT\""
echo "  tar -xzf \"$BACKUP_PATH\""
