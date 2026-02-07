#!/usr/bin/env bash
# migrate-exocortex-v3.sh — ONE-TIME migration script
# 
# Safely upgrades all EnkratFlow projects from exocortex v1/v2 to v3
# 
# What it does:
#   1. Commits current state in every repo (preserves what exists)
#   2. Tags every repo with "pre-exocortex-v3" (rollback point)
#   3. Runs upgrade-exocortex.sh on each target project
#   4. Creates an event in each upgraded project documenting the upgrade
#   5. Commits the upgrade in each repo
#   6. Tags every repo with "exocortex-v3" (post-upgrade marker)
#   7. Pushes tags + commits to remotes
#
# Rollback:
#   cd ~/EnkratFlow/<project> && git reset --hard pre-exocortex-v3
#
# Usage:
#   ./migrate-exocortex-v3.sh              (run for real)
#   ./migrate-exocortex-v3.sh --dry-run    (preview only)

set -euo pipefail

ENKRATFLOW_DIR="$HOME/EnkratFlow"
SOURCE_PROJECT="trading-journal"
TIMESTAMP=$(date +%Y-%m-%d_%H-%M-%S)
TODAY=$(date +%Y-%m-%d)
MACHINE=$(hostname -s | tr '[:upper:]' '[:lower:]' | tr ' ' '-')
DRY_RUN=false
TAG_PRE="pre-exocortex-v3"
TAG_POST="exocortex-v3"

# Target projects to upgrade (not including source or template)
UPGRADE_TARGETS=(
    "exocenter"
    "enkratflow-rag-api"
    "enkratflow-pkb-api"
    "EnkratFlow-Project"
)

# All repos to tag (including source)
ALL_REPOS=(
    "trading-journal"
    "exocenter"
    "enkratflow-rag-api"
    "enkratflow-pkb-api"
    "EnkratFlow-Project"
    "exocortex-template"
)

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

log_phase()  { echo ""; echo -e "${CYAN}══════════════════════════════════════════════════${NC}"; echo -e "${CYAN}  $1${NC}"; echo -e "${CYAN}══════════════════════════════════════════════════${NC}"; echo ""; }
log_repo()   { echo -e "  ${BLUE}[$1]${NC} $2"; }
log_ok()     { echo -e "  ${GREEN}✓${NC} $1"; }
log_warn()   { echo -e "  ${YELLOW}⚠${NC} $1"; }
log_error()  { echo -e "  ${RED}✗${NC} $1"; }
log_dry()    { echo -e "  ${YELLOW}dry${NC} $1"; }

run_cmd() {
    if $DRY_RUN; then
        log_dry "$1"
    else
        eval "$1"
    fi
}

# Parse args
[[ "${1:-}" == "--dry-run" ]] && DRY_RUN=true

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║  Exocortex v3 Migration — Full Ecosystem Upgrade        ║"
echo "║                                                         ║"
echo "║  Source: trading-journal (84 files, latest code)        ║"
echo "║  Targets: exocenter, rag-api, pkb-api, EnkratFlow-Proj ║"
echo "║  Rollback tag: $TAG_PRE                         ║"
echo "╚══════════════════════════════════════════════════════════╝"
$DRY_RUN && echo -e "\n  ${YELLOW}MODE: DRY RUN (no changes will be made)${NC}"
echo ""

# ============================================================
# PHASE 1: Commit current state in all repos
# ============================================================
log_phase "PHASE 1: Commit Current State (preserve everything)"

for repo in "${ALL_REPOS[@]}"; do
    repo_dir="$ENKRATFLOW_DIR/$repo"
    if [ ! -d "$repo_dir/.git" ]; then
        log_warn "$repo — not a git repo, skipping"
        continue
    fi

    cd "$repo_dir"
    uncommitted=$(git status --porcelain | wc -l | tr -d ' ')

    if [ "$uncommitted" -gt 0 ]; then
        log_repo "$repo" "$uncommitted uncommitted files — committing..."
        run_cmd "cd $repo_dir && git add -A && git commit -m 'chore: pre-exocortex-v3 snapshot — preserve current state'"
    else
        log_repo "$repo" "clean — nothing to commit"
    fi
done

# ============================================================
# PHASE 2: Tag all repos (rollback point)
# ============================================================
log_phase "PHASE 2: Tag All Repos ($TAG_PRE)"

for repo in "${ALL_REPOS[@]}"; do
    repo_dir="$ENKRATFLOW_DIR/$repo"
    [ ! -d "$repo_dir/.git" ] && continue

    cd "$repo_dir"

    # Check if tag already exists
    if git rev-parse "$TAG_PRE" >/dev/null 2>&1; then
        log_warn "$repo — tag $TAG_PRE already exists, skipping"
        continue
    fi

    log_repo "$repo" "tagging as $TAG_PRE"
    run_cmd "cd $repo_dir && git tag -a $TAG_PRE -m 'Rollback point: before exocortex v3 upgrade ($TODAY)'"
done

# ============================================================
# PHASE 3: Run upgrade on target projects
# ============================================================
log_phase "PHASE 3: Upgrade Target Projects"

UPGRADE_SCRIPT="$ENKRATFLOW_DIR/$SOURCE_PROJECT/.exocortex/scripts/upgrade-exocortex.sh"

if [ ! -x "$UPGRADE_SCRIPT" ]; then
    log_error "Upgrade script not found or not executable: $UPGRADE_SCRIPT"
    exit 1
fi

for target in "${UPGRADE_TARGETS[@]}"; do
    target_dir="$ENKRATFLOW_DIR/$target"
    if [ ! -d "$target_dir/.exocortex" ]; then
        log_warn "$target — no .exocortex/ found, skipping"
        continue
    fi

    log_repo "$target" "upgrading..."
    if $DRY_RUN; then
        log_dry "Would run: $UPGRADE_SCRIPT $target_dir"
    else
        "$UPGRADE_SCRIPT" "$target_dir"
    fi
done

# ============================================================
# PHASE 4: Create upgrade event in each target project
# ============================================================
log_phase "PHASE 4: Create Upgrade Events"

EVENT_CONTENT="# Exocortex v3 Upgrade

**Date:** $TODAY
**Type:** System Upgrade
**Source:** trading-journal (source of truth)

## What Changed

Upgraded from exocortex v1/v2 (flat files, no commands) to v3:

### New Infrastructure
- **commands/** — 20 JSON command specifications (/work, /save, /subconscious, etc.)
- **scripts/** — 6 Python AI memory scripts (2-pass OpenAI pipeline)
  - RIGHT NOW memory (0-7 days, episodic)
  - SHORT-TERM memory (7-31 days, semantic)
  - LONG-TERM memory (31+ days, compressed)
  - SUBCONSCIOUS (all events, cross-cutting pattern detection)
  - Subconscious NUDGE (single-sentence probe in /work)
  - Drill memory (topic-specific deep dive)
- **docs/** — Architecture, memory system, subconscious neuroscience docs
- **control/** — Workflow system (INTERRUPTS → BACKLOG → TODO)
- **reference/** — Quick reference, memory reference, cheat sheet

### Memory System
- Four-tier memory based on Conway's autobiographical model
- 2-pass Ralph-style self-critique (generate → quality check)
- Subconscious pattern persistence (subconscious_patterns.md)
- Involuntary DMN nudge during /work command

### V1 Artifacts Archived
- AI_INSTRUCTIONS.md → archive/ (replaced by PERSONA_AND_COMMANDS.md + command JSONs)

### Safety
- Rollback tag: \`$TAG_PRE\`
- All project-specific data preserved (events, TODO, LESSONS, SESSION_CONTEXT)
- upgrade-exocortex.sh respects sacred file boundaries
"

for target in "${UPGRADE_TARGETS[@]}"; do
    target_dir="$ENKRATFLOW_DIR/$target"
    events_dir="$target_dir/.exocortex/events"

    [ ! -d "$target_dir/.exocortex" ] && continue

    event_file="${TIMESTAMP}_${MACHINE}-upgrade.md"
    log_repo "$target" "creating event: $event_file"

    if $DRY_RUN; then
        log_dry "Would create $events_dir/$event_file"
    else
        mkdir -p "$events_dir"
        echo "$EVENT_CONTENT" > "$events_dir/$event_file"
    fi
done

# Also create an event in the source (trading-journal)
SOURCE_EVENTS="$ENKRATFLOW_DIR/$SOURCE_PROJECT/.exocortex/events"
SOURCE_EVENT="${TIMESTAMP}_${MACHINE}-upgrade.md"
SOURCE_EVENT_CONTENT="# Exocortex v3 Ecosystem Deployment

**Date:** $TODAY
**Type:** Ecosystem Upgrade
**Scope:** All EnkratFlow projects

## Deployed To
- exocenter
- enkratflow-rag-api
- enkratflow-pkb-api
- EnkratFlow-Project

## What Was Deployed
- 20 command JSON specs
- 6 Python AI memory scripts + subconscious nudge
- Full docs/ and control/ infrastructure
- MEMORY_TIERS.md, COMMAND_SYSTEM.md, PERSONA_AND_COMMANDS.md
- upgrade-exocortex.sh (for future upgrades)
- MEMORY_ISOLATION.md (isolation rules)

## Rollback
\`\`\`bash
cd ~/EnkratFlow/<project> && git reset --hard $TAG_PRE
\`\`\`

## Safety Verification
All project-specific data preserved:
- events/*.md — untouched
- SESSION_CONTEXT.md — untouched
- TODO.md — untouched
- LESSONS.md — untouched
- PROJECT_MEMORY.md — untouched
- .env — untouched
"

log_repo "$SOURCE_PROJECT" "creating deployment event: $SOURCE_EVENT"
if $DRY_RUN; then
    log_dry "Would create $SOURCE_EVENTS/$SOURCE_EVENT"
else
    echo "$SOURCE_EVENT_CONTENT" > "$SOURCE_EVENTS/$SOURCE_EVENT"
fi

# ============================================================
# PHASE 5: Commit upgrades in all repos
# ============================================================
log_phase "PHASE 5: Commit Upgrades"

for repo in "${ALL_REPOS[@]}"; do
    repo_dir="$ENKRATFLOW_DIR/$repo"
    [ ! -d "$repo_dir/.git" ] && continue

    cd "$repo_dir"
    uncommitted=$(git status --porcelain | wc -l | tr -d ' ')

    if [ "$uncommitted" -gt 0 ]; then
        log_repo "$repo" "$uncommitted files changed — committing upgrade..."
        run_cmd "cd $repo_dir && git add -A && git commit -m 'feat: exocortex v3 upgrade — commands, AI memory, subconscious, control system'"
    else
        log_repo "$repo" "no changes (already up to date)"
    fi
done

# ============================================================
# PHASE 6: Tag post-upgrade
# ============================================================
log_phase "PHASE 6: Tag Post-Upgrade ($TAG_POST)"

for repo in "${ALL_REPOS[@]}"; do
    repo_dir="$ENKRATFLOW_DIR/$repo"
    [ ! -d "$repo_dir/.git" ] && continue

    cd "$repo_dir"

    if git rev-parse "$TAG_POST" >/dev/null 2>&1; then
        log_warn "$repo — tag $TAG_POST already exists, skipping"
        continue
    fi

    log_repo "$repo" "tagging as $TAG_POST"
    run_cmd "cd $repo_dir && git tag -a $TAG_POST -m 'Exocortex v3: commands, AI memory, subconscious, control system ($TODAY)'"
done

# ============================================================
# PHASE 7: Push to remotes
# ============================================================
log_phase "PHASE 7: Push to Remotes"

for repo in "${ALL_REPOS[@]}"; do
    repo_dir="$ENKRATFLOW_DIR/$repo"
    [ ! -d "$repo_dir/.git" ] && continue

    cd "$repo_dir"
    branch=$(git branch --show-current)
    has_remote=$(git remote -v | wc -l | tr -d ' ')

    if [ "$has_remote" -eq 0 ]; then
        log_warn "$repo — no remote configured, skipping push"
        continue
    fi

    log_repo "$repo" "pushing $branch + tags..."
    run_cmd "cd $repo_dir && git push origin $branch --tags 2>&1 | tail -3"
done

# ============================================================
# SUMMARY
# ============================================================
log_phase "MIGRATION COMPLETE"

echo "  Rollback any project:"
echo "    cd ~/EnkratFlow/<project>"
echo "    git reset --hard $TAG_PRE"
echo ""
echo "  Verify upgrade:"
echo "    ls ~/EnkratFlow/<project>/.exocortex/commands/  # should have 20 files"
echo "    ls ~/EnkratFlow/<project>/.exocortex/scripts/   # should have Python + Bash"
echo ""

$DRY_RUN && echo -e "  ${YELLOW}This was a DRY RUN. No changes were made.${NC}"
echo ""
