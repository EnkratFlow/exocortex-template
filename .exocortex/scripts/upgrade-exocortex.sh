#!/usr/bin/env bash
# upgrade-exocortex.sh — Safely propagate CODE files to target project
# 
# Source of truth: exocortex-template/.exocortex/
# NEVER overwrites DATA files (events, SESSION_CONTEXT, TODO, LESSONS, etc.)
#
# Usage:
#   ./upgrade-exocortex.sh <target-project-path>
#   ./upgrade-exocortex.sh ~/code/my-project
#   ./upgrade-exocortex.sh --all   (upgrades all hub-enabled projects)
#   ./upgrade-exocortex.sh --dry-run <target>   (preview without copying)
#
# Safety:
#   - Creates backup in target/.exocortex/archive/pre-upgrade-YYYY-MM-DD/
#   - Archives AI_INSTRUCTIONS.md if found (old v1 artifact)
#   - Creates missing directories (commands/, docs/, control/, reference/)
#   - NEVER touches events/, .env, SESSION_CONTEXT.md, TODO.md, etc.

set -euo pipefail

# --- Config ---
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SOURCE_EXOCORTEX="$(dirname "$SCRIPT_DIR")"  # .exocortex/ (parent of scripts/)
SOURCE_PROJECT="$(dirname "$SOURCE_EXOCORTEX")"  # project root
TODAY=$(date +%Y-%m-%d)
DRY_RUN=false

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# --- Sacred files — NEVER overwrite ---
SACRED_FILES=(
    "SESSION_CONTEXT.md"
    "TODO.md"
    "LESSONS.md"
    "OPEN_DECISIONS.md"
    "PROJECT_MEMORY.md"
    "subconscious_patterns.md"
    ".env"
    ".hub_enabled"
    ".hub_disabled"
)

SACRED_DIRS=(
    "events"
    "hub"
    "archive"
    "planning"
)

# Control files: create from template if missing, never overwrite if exists
CONTROL_TEMPLATE_ONLY=(
    "control/INTERRUPTS.md"
    "control/BACKLOG.md"
    "control/ROADMAP.md"
    "control/ARCH_OVERVIEW.md"
    "control/REPO_ORGANIZATION_REPORT.md"
)

# Control files: always safe to overwrite (generic workflow docs)
CONTROL_OVERWRITE=(
    "control/README.md"
    "control/SNIPPETS.md"
    "control/DAILY_WORKFLOW.md"
    "control/QA_STRATEGY.md"
    "control/END_SESSION_PROMPT.md"
)

# --- Functions ---

log_info()  { echo -e "${BLUE}ℹ${NC}  $1"; }
log_ok()    { echo -e "${GREEN}✓${NC}  $1"; }
log_warn()  { echo -e "${YELLOW}⚠${NC}  $1"; }
log_error() { echo -e "${RED}✗${NC}  $1"; }
log_skip()  { echo -e "  ${YELLOW}skip${NC} $1"; }
log_copy()  { echo -e "  ${GREEN}copy${NC} $1"; }
log_new()   { echo -e "  ${GREEN}new${NC}  $1"; }
log_dry()   { echo -e "  ${BLUE}dry${NC}  $1"; }

is_sacred_file() {
    local filename="$1"
    for sacred in "${SACRED_FILES[@]}"; do
        [[ "$filename" == "$sacred" ]] && return 0
    done
    return 1
}

is_sacred_dir() {
    local dirname="$1"
    for sacred in "${SACRED_DIRS[@]}"; do
        [[ "$dirname" == "$sacred" ]] && return 0
    done
    return 1
}

is_template_only() {
    local filepath="$1"
    for tmpl in "${CONTROL_TEMPLATE_ONLY[@]}"; do
        [[ "$filepath" == "$tmpl" ]] && return 0
    done
    return 1
}

safe_copy() {
    local src="$1"
    local dst="$2"
    local label="$3"

    if $DRY_RUN; then
        log_dry "$label"
        return
    fi

    mkdir -p "$(dirname "$dst")"
    cp "$src" "$dst"
    log_copy "$label"
}

create_blank_stub() {
    # Creates a BLANK stub file instead of copying from source (prevents memory contamination)
    local filepath="$1"
    local label="$2"

    if [ -f "$filepath" ]; then
        log_skip "$label (exists — won't overwrite)"
        return
    fi

    if $DRY_RUN; then
        log_dry "$label (new — would create blank stub)"
        return
    fi

    mkdir -p "$(dirname "$filepath")"

    # Generate appropriate blank content based on filename
    local filename
    filename=$(basename "$filepath")
    case "$filename" in
        INTERRUPTS.md)
            cat > "$filepath" << 'STUB'
# Interrupts

> Capture lane — things that come up while working on something else.
> Run `/groom` periodically to move items to BACKLOG or TODO.

_No interrupts captured yet._
STUB
            ;;
        BACKLOG.md)
            cat > "$filepath" << 'STUB'
# Backlog

> Items under investigation. Moved here from INTERRUPTS after grooming.
> Run `/refine-backlog` to promote items to TODO.

_No backlog items yet._
STUB
            ;;
        ROADMAP.md)
            cat > "$filepath" << 'STUB'
# Roadmap

> Strategic planning for this project.
> Updated periodically during reviews.

_No roadmap defined yet. Run `/weekly-review` or `/monthly-review` to start planning._
STUB
            ;;
        ARCH_OVERVIEW.md)
            cat > "$filepath" << 'STUB'
# Architecture Overview

> Project-specific architecture documentation.
> Update this as the system evolves.

_Architecture not yet documented for this project._
STUB
            ;;
        REPO_ORGANIZATION_REPORT.md)
            cat > "$filepath" << 'STUB'
# Repository Organization Report

> Analysis of repo structure and recommended improvements.

_No report generated yet. Run `/system-scan` to analyze._
STUB
            ;;
        *)
            echo "# $(basename "$filepath" .md)" > "$filepath"
            echo "" >> "$filepath"
            echo "_Created by exocortex upgrade. Edit as needed._" >> "$filepath"
            ;;
    esac

    log_new "$label (created blank stub)"
}

backup_target() {
    local target="$1"
    local backup_dir="$target/archive/pre-upgrade-$TODAY"

    if $DRY_RUN; then
        log_info "Would backup to $backup_dir/"
        return
    fi

    if [ -d "$backup_dir" ]; then
        log_warn "Backup already exists: $backup_dir/ (skipping backup)"
        return
    fi

    mkdir -p "$backup_dir"

    # Back up key files that will be overwritten
    for f in MEMORY_TIERS.md COMMAND_SYSTEM.md PERSONA_AND_COMMANDS.md README.md; do
        [ -f "$target/$f" ] && cp "$target/$f" "$backup_dir/"
    done

    # Back up AI_INSTRUCTIONS.md if it exists (v1 artifact)
    if [ -f "$target/AI_INSTRUCTIONS.md" ]; then
        cp "$target/AI_INSTRUCTIONS.md" "$backup_dir/"
        log_warn "AI_INSTRUCTIONS.md found — will be archived"
    fi

    log_ok "Backup created: $backup_dir/"
}

archive_v1_artifacts() {
    local target="$1"

    # Archive AI_INSTRUCTIONS.md (v1 era — replaced by PERSONA_AND_COMMANDS.md + command JSONs)
    if [ -f "$target/AI_INSTRUCTIONS.md" ]; then
        if $DRY_RUN; then
            log_dry "Would archive AI_INSTRUCTIONS.md"
            return
        fi
        mkdir -p "$target/archive"
        mv "$target/AI_INSTRUCTIONS.md" "$target/archive/AI_INSTRUCTIONS.md"
        log_ok "Archived AI_INSTRUCTIONS.md → archive/"
    fi
}

upgrade_project() {
    local target_exocortex="$1"
    local project_name
    project_name=$(basename "$(dirname "$target_exocortex")")

    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  Upgrading: $project_name"
    echo "  Target:    $target_exocortex"
    echo "  Source:    $SOURCE_EXOCORTEX"
    $DRY_RUN && echo "  Mode:      DRY RUN (no changes)"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""

    # Verify target has .exocortex
    if [ ! -d "$target_exocortex" ]; then
        log_error "No .exocortex/ found at $target_exocortex"
        return 1
    fi

    # --- Step 1: Backup ---
    log_info "Step 1: Backup"
    backup_target "$target_exocortex"

    # --- Step 2: Archive v1 artifacts ---
    log_info "Step 2: Archive v1 artifacts"
    archive_v1_artifacts "$target_exocortex"

    # --- Step 3: Create directories ---
    log_info "Step 3: Create directories"
    for dir in commands docs control reference scripts; do
        if [ ! -d "$target_exocortex/$dir" ]; then
            if $DRY_RUN; then
                log_dry "Would create $dir/"
            else
                mkdir -p "$target_exocortex/$dir"
                log_new "$dir/"
            fi
        fi
    done

    # --- Step 3b: Ensure .env exists (same owner, same API keys) ---
    log_info "Step 3b: Environment"
    safe_copy "$SOURCE_EXOCORTEX/.env.example" "$target_exocortex/.env.example" ".env.example"
    safe_copy "$SOURCE_EXOCORTEX/.gitignore" "$target_exocortex/.gitignore" ".gitignore (protects .env)"
    if [ -f "$SOURCE_EXOCORTEX/.env" ] && [ ! -f "$target_exocortex/.env" ]; then
        safe_copy "$SOURCE_EXOCORTEX/.env" "$target_exocortex/.env" ".env (copied — same owner, same keys)"
    elif [ -f "$target_exocortex/.env" ]; then
        log_ok ".env exists (untouched)"
    else
        log_warn "No .env in source — target will need manual setup"
    fi

    # --- Step 4: Copy scripts (Python + Bash) ---
    log_info "Step 4: Scripts"
    for script in "$SOURCE_EXOCORTEX/scripts/"*.py "$SOURCE_EXOCORTEX/scripts/"*.sh; do
        [ -f "$script" ] || continue
        local basename
        basename=$(basename "$script")
        safe_copy "$script" "$target_exocortex/scripts/$basename" "scripts/$basename"
    done

    # Make Python scripts executable
    if ! $DRY_RUN; then
        chmod +x "$target_exocortex/scripts/"*.py 2>/dev/null || true
        chmod +x "$target_exocortex/scripts/"*.sh 2>/dev/null || true
    fi

    # --- Step 5: Copy commands (all 20 JSON specs) ---
    log_info "Step 5: Commands"
    for cmd in "$SOURCE_EXOCORTEX/commands/"*.json; do
        [ -f "$cmd" ] || continue
        local basename
        basename=$(basename "$cmd")
        safe_copy "$cmd" "$target_exocortex/commands/$basename" "commands/$basename"
    done

    # --- Step 6: Copy root-level CODE docs ---
    log_info "Step 6: Root docs"
    for doc in MEMORY_TIERS.md COMMAND_SYSTEM.md PERSONA_AND_COMMANDS.md README.md AI_BOOTSTRAP.md; do
        [ -f "$SOURCE_EXOCORTEX/$doc" ] || continue
        safe_copy "$SOURCE_EXOCORTEX/$doc" "$target_exocortex/$doc" "$doc"
    done

    # --- Step 7: Copy reference/ ---
    log_info "Step 7: Reference"
    for ref in "$SOURCE_EXOCORTEX/reference/"*.md; do
        [ -f "$ref" ] || continue
        local basename
        basename=$(basename "$ref")
        safe_copy "$ref" "$target_exocortex/reference/$basename" "reference/$basename"
    done

    # --- Step 8: Copy docs/ (generic documentation) ---
    log_info "Step 8: Docs"
    for doc in "$SOURCE_EXOCORTEX/docs/"*.md; do
        [ -f "$doc" ] || continue
        local basename
        basename=$(basename "$doc")

        # Skip project-specific docs that shouldn't propagate
        case "$basename" in
            SYSTEM_LOGIC_DOCUMENTATION.md|SCENARIO_VERIFICATION_PROTOCOL_V2.md|PROGRESSIVE_TEACHING_MEMORY.md|LESSONS.md)
                log_skip "docs/$basename (project-specific)"
                continue
                ;;
        esac

        safe_copy "$doc" "$target_exocortex/docs/$basename" "docs/$basename"
    done

    # --- Step 9: Copy control/ (mixed — some overwrite, some template-only) ---
    log_info "Step 9: Control"
    for ctl in "${CONTROL_OVERWRITE[@]}"; do
        [ -f "$SOURCE_EXOCORTEX/$ctl" ] || continue
        safe_copy "$SOURCE_EXOCORTEX/$ctl" "$target_exocortex/$ctl" "$ctl"
    done

    for ctl in "${CONTROL_TEMPLATE_ONLY[@]}"; do
        create_blank_stub "$target_exocortex/$ctl" "$ctl"
    done

    # --- Step 10: Verify sacred files untouched ---
    log_info "Step 10: Sacred file verification"
    local sacred_ok=true
    for sacred in "${SACRED_FILES[@]}"; do
        if [ -f "$target_exocortex/$sacred" ]; then
            log_ok "$sacred (untouched)"
        fi
    done
    for sacred_dir in "${SACRED_DIRS[@]}"; do
        if [ -d "$target_exocortex/$sacred_dir" ]; then
            log_ok "$sacred_dir/ (untouched)"
        fi
    done

    # --- Step 11: Copy editor pointer files to project root ---
    log_info "Step 11: Editor pointer files"
    local target_project
    target_project="$(dirname "$target_exocortex")"

    for pfile in CLAUDE.md .windsurfrules .rules; do
        if [ -f "$SOURCE_PROJECT/$pfile" ]; then
            safe_copy "$SOURCE_PROJECT/$pfile" "$target_project/$pfile" "$pfile (thin pointer)"
        fi
    done

    # .github/copilot-instructions.md
    if [ -f "$SOURCE_PROJECT/.github/copilot-instructions.md" ]; then
        mkdir -p "$target_project/.github"
        safe_copy "$SOURCE_PROJECT/.github/copilot-instructions.md" "$target_project/.github/copilot-instructions.md" ".github/copilot-instructions.md (thin pointer)"
    fi

    # --- Step 12: Copy .cursor/ directory (commands + rules) ---
    log_info "Step 12: Cursor commands and rules"
    local target_project
    target_project="$(dirname "$target_exocortex")"

    for cursor_subdir in commands rules; do
        local src_cursor="$SOURCE_PROJECT/.cursor/$cursor_subdir"
        local dst_cursor="$target_project/.cursor/$cursor_subdir"

        if [ -d "$src_cursor" ]; then
            if $DRY_RUN; then
                log_dry ".cursor/$cursor_subdir/"
            else
                mkdir -p "$dst_cursor"
            fi
            for f in "$src_cursor"/*; do
                [ -f "$f" ] || continue
                local basename
                basename=$(basename "$f")
                safe_copy "$f" "$dst_cursor/$basename" ".cursor/$cursor_subdir/$basename"
            done
        fi
    done

    # Remove legacy .cursorrules if .cursor/rules/ now exists
    if [ -f "$target_project/.cursorrules" ] && [ -d "$target_project/.cursor/rules" ]; then
        if $DRY_RUN; then
            log_dry "Would remove legacy .cursorrules"
        else
            rm "$target_project/.cursorrules"
            log_ok "Removed legacy .cursorrules (replaced by .cursor/rules/)"
        fi
    fi

    echo ""
    log_ok "Upgrade complete: $project_name"
    echo ""
}

# --- Main ---

# Parse arguments
if [ $# -eq 0 ]; then
    echo "Usage: upgrade-exocortex.sh [--dry-run] <target-path|--all>"
    echo ""
    echo "Examples:"
    echo "  ./upgrade-exocortex.sh ~/code/my-project"
    echo "  ./upgrade-exocortex.sh --dry-run ~/code/my-project"
    echo "  ./upgrade-exocortex.sh --all"
    echo "  ./upgrade-exocortex.sh --dry-run --all"
    exit 1
fi

# ── Safety gate: run test suite before any live upgrade ─────────────────
# Skip on --dry-run (no data will change) or if tests dir is missing.
if [[ "$*" != *"--dry-run"* ]]; then
    TESTS_SCRIPT="$(dirname "$SCRIPT_DIR")/../tests/run_tests.sh"
    # Resolve: upgrade script lives in .exocortex/scripts/, tests/ is at project root
    TEMPLATE_ROOT="$(cd "$(dirname "$SCRIPT_DIR")/.." && pwd)"
    TESTS_SCRIPT="$TEMPLATE_ROOT/tests/run_tests.sh"

    if [ -f "$TESTS_SCRIPT" ]; then
        echo ""
        echo "🧪 Running test suite before upgrade..."
        echo "   (Protects live project data — skip with --dry-run for preview)"
        echo ""
        if bash "$TESTS_SCRIPT"; then
            echo ""
            log_ok "Tests passed — proceeding with upgrade"
            echo ""
        else
            echo ""
            log_error "Tests FAILED — upgrade aborted to protect live project data"
            echo ""
            echo "  Fix the failures in tests/run_tests.sh, then re-run."
            echo "  To preview without running tests: --dry-run"
            echo ""
            exit 1
        fi
    else
        log_warn "tests/run_tests.sh not found — skipping pre-upgrade test gate"
        log_warn "(expected at: $TESTS_SCRIPT)"
    fi
fi

# Parse flags
while [[ $# -gt 0 ]]; do
    case "$1" in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --all)
            # Find all hub-enabled projects (excluding self)
            echo "╔══════════════════════════════════════════════════╗"
            echo "║  Exocortex Upgrade — ALL Hub-Enabled Projects   ║"
            echo "╚══════════════════════════════════════════════════╝"
            $DRY_RUN && echo "  Mode: DRY RUN"
            echo ""

            ENKRATFLOW_DIR="$(dirname "$SOURCE_PROJECT")"
            for project_dir in "$ENKRATFLOW_DIR"/*/; do
                project_name=$(basename "$project_dir")
                target="$project_dir.exocortex"

                # Skip self
                [[ "$project_name" == "$(basename "$SOURCE_PROJECT")" ]] && continue

                # Skip projects without .exocortex
                [ -d "$target" ] || continue

                # Skip projects without hub_enabled (hub host project should have .hub_enabled)
                if [ ! -f "$target/.hub_enabled" ]; then
                    log_warn "Skipping $project_name (no .hub_enabled flag)"
                    continue
                fi

                upgrade_project "$target"
            done

            echo ""
            echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            log_ok "All projects upgraded"
            echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            exit 0
            ;;
        *)
            # Single project path
            TARGET_PATH="$1"

            # Add .exocortex if not already specified
            if [[ ! "$TARGET_PATH" == *".exocortex"* ]]; then
                TARGET_PATH="$TARGET_PATH/.exocortex"
            fi

            echo "╔══════════════════════════════════════════════════╗"
            echo "║  Exocortex Upgrade — Single Project             ║"
            echo "╚══════════════════════════════════════════════════╝"

            upgrade_project "$TARGET_PATH"
            exit 0
            ;;
    esac
done
