#!/usr/bin/env bash
# install-cursor-skills.sh -- Install global Cursor skills to ~/.cursor/skills/
#
# Source of truth: exocortex-template/.cursor/skills/
# Target: ~/.cursor/skills/ (global, available in every project)
#
# Usage:
#   ./install-cursor-skills.sh              (install new, update unchanged, skip modified)
#   ./install-cursor-skills.sh --force      (overwrite everything including modified skills)
#   ./install-cursor-skills.sh --dry-run    (preview without copying)
#   ./install-cursor-skills.sh --list       (show installed vs available)
#
# Safety:
#   - Never deletes existing skills at target
#   - Skips skills you've customized (unless --force)
#   - Updates unmodified skills to the latest version
#   - Creates ~/.cursor/skills/ if it doesn't exist

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_DIR="$(dirname "$SCRIPT_DIR")/.cursor/skills"
TARGET_DIR="$HOME/.cursor/skills"
DRY_RUN=false
LIST_ONLY=false
FORCE=false

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_copy()  { echo -e "  ${GREEN}update${NC}  $1"; }
log_new()   { echo -e "  ${GREEN}new${NC}     $1"; }
log_dry()   { echo -e "  ${BLUE}dry${NC}     $1"; }
log_skip()  { echo -e "  ${YELLOW}skip${NC}    $1 (locally modified, use --force to overwrite)"; }
log_same()  { echo -e "  ${BLUE}current${NC} $1 (already up to date)"; }

show_list() {
    echo ""
    echo "Cursor Skills -- Installed vs Available"
    echo "========================================"
    echo ""

    printf "  %-20s %-12s %-12s\n" "SKILL" "SOURCE" "INSTALLED"
    printf "  %-20s %-12s %-12s\n" "--------------------" "----------" "----------"

    for skill_dir in "$SOURCE_DIR"/*/; do
        [ -d "$skill_dir" ] || continue
        skill_name=$(basename "$skill_dir")

        if [ -f "$TARGET_DIR/$skill_name/SKILL.md" ]; then
            if cmp -s "$skill_dir/SKILL.md" "$TARGET_DIR/$skill_name/SKILL.md" 2>/dev/null; then
                installed="yes"
            else
                installed="yes (modified)"
            fi
        else
            installed="--"
        fi
        printf "  %-20s %-12s %-12s\n" "$skill_name" "yes" "$installed"
    done

    if [ -d "$TARGET_DIR" ]; then
        for installed_dir in "$TARGET_DIR"/*/; do
            [ -d "$installed_dir" ] || continue
            installed_name=$(basename "$installed_dir")
            if [ ! -d "$SOURCE_DIR/$installed_name" ]; then
                printf "  %-20s %-12s %-12s\n" "$installed_name" "--" "yes (custom)"
            fi
        done
    fi

    echo ""
    echo "  Source: $SOURCE_DIR"
    echo "  Target: $TARGET_DIR"
    echo ""
}

install_skills() {
    echo ""
    echo "Cursor Skills -- Install / Update"
    echo "=================================="
    $DRY_RUN && echo "  Mode: DRY RUN"
    $FORCE && echo "  Mode: FORCE (overwriting all)"
    echo ""
    echo "  Source: $SOURCE_DIR"
    echo "  Target: $TARGET_DIR"
    echo ""

    if [ ! -d "$SOURCE_DIR" ]; then
        echo "  ERROR: Source directory not found: $SOURCE_DIR"
        exit 1
    fi

    $DRY_RUN || mkdir -p "$TARGET_DIR"

    local new_count=0
    local update_count=0
    local skip_count=0
    local same_count=0

    for skill_dir in "$SOURCE_DIR"/*/; do
        [ -d "$skill_dir" ] || continue
        skill_name=$(basename "$skill_dir")
        source_file="$skill_dir/SKILL.md"
        target_file="$TARGET_DIR/$skill_name/SKILL.md"

        if [ ! -f "$source_file" ]; then
            continue
        fi

        if $DRY_RUN; then
            if [ -f "$target_file" ]; then
                if cmp -s "$source_file" "$target_file" 2>/dev/null; then
                    log_same "$skill_name"
                    same_count=$((same_count + 1))
                elif $FORCE; then
                    log_dry "$skill_name (would overwrite)"
                    update_count=$((update_count + 1))
                else
                    log_skip "$skill_name"
                    skip_count=$((skip_count + 1))
                fi
            else
                log_dry "$skill_name (would create)"
                new_count=$((new_count + 1))
            fi
        else
            if [ -f "$target_file" ]; then
                if cmp -s "$source_file" "$target_file" 2>/dev/null; then
                    log_same "$skill_name"
                    same_count=$((same_count + 1))
                elif $FORCE; then
                    mkdir -p "$TARGET_DIR/$skill_name"
                    cp "$source_file" "$target_file"
                    log_copy "$skill_name"
                    update_count=$((update_count + 1))
                else
                    log_skip "$skill_name"
                    skip_count=$((skip_count + 1))
                fi
            else
                mkdir -p "$TARGET_DIR/$skill_name"
                cp "$source_file" "$target_file"
                log_new "$skill_name"
                new_count=$((new_count + 1))
            fi
        fi
    done

    echo ""
    echo -e "  ${GREEN}Done.${NC} $new_count new, $update_count updated, $same_count current, $skip_count skipped."
    if [ $skip_count -gt 0 ]; then
        echo "  Skipped skills have local modifications. Use --force to overwrite."
    fi
    echo ""
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --list)
            LIST_ONLY=true
            shift
            ;;
        --force)
            FORCE=true
            shift
            ;;
        *)
            echo "Usage: install-cursor-skills.sh [--dry-run] [--list] [--force]"
            exit 1
            ;;
    esac
done

if $LIST_ONLY; then
    show_list
else
    install_skills
fi
