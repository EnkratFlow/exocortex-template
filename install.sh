#!/bin/bash

# Exocortex v3 — One-Command Installer
#
# USAGE:
#   curl -sL https://raw.githubusercontent.com/EnkratFlow/exocortex-template/main/install.sh | bash
#   curl -sL https://raw.githubusercontent.com/EnkratFlow/exocortex-template/main/install.sh | bash -s "my-project"
#
# Or clone and run locally:
#   bash install.sh
#   bash install.sh my-project
#
# Offline / vendored install (use a local copy of the template instead of cloning):
#   EXOCORTEX_LOCAL_SOURCE=/path/to/exocortex-template bash /path/to/exocortex-template/install.sh
#
# What this does:
#   1. Clones exocortex-template to a temp directory (or uses $EXOCORTEX_LOCAL_SOURCE if set)
#   2. Copies .exocortex/ and editor pointer files to the current directory
#   3. Copies .cursor/ (commands, skills, rules, agents, hooks) + hooks.json — safe merge, never overwrites modified files
#   4. Copies .github/skills/ — role skills for VS Code Copilot
#   5. Copies .claude/skills/ — workflow commands for VS Code Copilot and Claude CLI
#   6. Runs init-project.sh to replace placeholders and set up API keys
#   7. Cleans up the temp clone
#
# Requirements:
#   - git
#   - bash 4+ (macOS ships with 3.2 but this script is compatible)
#   - Current directory is your project root

set -e

REPO_URL="https://github.com/EnkratFlow/exocortex-template.git"
BRANCH="main"
PROJECT_NAME="${1:-}"

echo ""
echo "🧠 Exocortex v3 — One-Command Installer"
echo "========================================"
echo ""

# ── Preflight checks ──────────────────────────────────────────────────

# Check git is available
if ! command -v git &> /dev/null; then
    echo "❌ Error: git is not installed"
    echo "  Install git first: https://git-scm.com/downloads"
    exit 1
fi

# Check we're in a reasonable directory
if [ "$(pwd)" = "$HOME" ]; then
    echo "❌ Error: Don't run this from your home directory"
    echo "  cd into your project directory first:"
    echo "    cd /path/to/your-project"
    exit 1
fi

# ── Detect: update vs fresh install ─────────────────────────────────
if [ -d ".exocortex" ]; then
    IS_UPDATE=true
    if [ -f .exocortex/.version ]; then
        INSTALLED_VERSION="$(cat .exocortex/.version 2>/dev/null | tr -d '[:space:]')"
    else
        INSTALLED_VERSION="$(grep -m1 'version' .exocortex/AI_BOOTSTRAP.md 2>/dev/null | awk '{print $NF}' || echo 'unknown')"
    fi
    [ -z "$INSTALLED_VERSION" ] && INSTALLED_VERSION="unknown"
    echo "🔄 Mode: UPDATE"
    echo "   Existing installation found."
    echo "   System files will update. Your data is never touched."
else
    IS_UPDATE=false
    echo "✨ Mode: FRESH INSTALL"
    echo "   No existing installation found."
fi

# ── Clone template ────────────────────────────────────────────────────

_EXOCORTEX_TMP=$(mktemp -d)
trap 'rm -rf "$_EXOCORTEX_TMP"' EXIT

MANIFEST=".exocortex/.install-manifest"
MANIFEST_TMP="$_EXOCORTEX_TMP/manifest-new"
touch "$MANIFEST_TMP"

# ── Helper: sha256 hash of a file ────────────────────────────────────
file_hash() {
    shasum -a 256 "$1" 2>/dev/null | awk '{print $1}'
}

is_exocortex_data_path() {
    local target="$1"
    local rel="$2"

    # Only apply data-plane exclusions when merging the .exocortex tree.
    case "$target" in
        .exocortex|*/.exocortex) ;;
        *) return 1 ;;
    esac

    case "$rel" in
        SESSION_CONTEXT.md|TODO.md|LESSONS.md|PROJECT_MEMORY.md|OPEN_DECISIONS.md|subconscious_patterns.md|.env|.hub_enabled|.hub_disabled|.install-manifest)
            return 0
            ;;
        events/*|archive/*|hub/*|planning/*|local/*)
            return 0
            ;;
        control/INTERRUPTS.md|control/BACKLOG.md|control/ROADMAP.md|control/ARCH_OVERVIEW.md|control/REPO_ORGANIZATION_REPORT.md)
            return 0
            ;;
        *)
            return 1
            ;;
    esac
}

# ── Helper: look up installed hash from manifest ─────────────────────
# Uses awk for literal string matching (no regex issues with file paths)
manifest_get() {
    local key="$1 "
    [ -f "$MANIFEST" ] && awk -v k="$key" 'index($0,k)==1{print $2;exit}' "$MANIFEST" || echo ""
}

# ── Helper: safe merge a directory of files ──────────────────────────
# On first install: copies everything, records hash in manifest
# On re-run (update):
#   - file matches template hash                          → already current, skip
#   - file matches manifest hash (user hasn't touched it) → update to latest template
#   - file differs from manifest hash (user modified it)  → skip, preserve their version
#   - file has no manifest entry (unknown history)        → skip, warn
#   - file doesn't exist yet                              → install it
# Usage: safe_copy_dir <src_dir> <target_dir> <label>
safe_copy_dir() {
    local src="$1"
    local target="$2"
    local label="$3"

    [ -d "$src" ] || return 0
    mkdir -p "$target"

    local n_new=0 n_update=0 n_skip=0 n_same=0

    while IFS= read -r src_file; do
        [ -f "$src_file" ] || continue
        local rel="${src_file#$src/}"
        local target_file="$target/$rel"
        mkdir -p "$(dirname "$target_file")"

        if is_exocortex_data_path "$target" "$rel"; then
            # Data-plane files are user/project state. They are created as blank
            # stubs when missing, but never copied from the public template and
            # never manifest-tracked.
            n_skip=$((n_skip + 1))
            continue
        fi

        local src_hash
        src_hash=$(file_hash "$src_file")

        if [ -f "$target_file" ]; then
            local current_hash
            current_hash=$(file_hash "$target_file")
            local installed_hash
            installed_hash=$(manifest_get "$target_file")

            if [ "$src_hash" = "$current_hash" ]; then
                # Already up to date — record and move on
                echo "${target_file} ${src_hash}" >> "$MANIFEST_TMP"
                n_same=$((n_same + 1))
            elif [ -n "$installed_hash" ] && [ "$current_hash" = "$installed_hash" ]; then
                # File matches what we installed last time — user hasn't touched it, safe to update
                cp "$src_file" "$target_file"
                echo "${target_file} ${src_hash}" >> "$MANIFEST_TMP"
                echo "  update  $rel"
                n_update=$((n_update + 1))
            else
                # No manifest entry or user has modified this file — preserve their version
                # Keep old manifest hash so next run can still detect their modification
                if [ -n "$installed_hash" ]; then
                    echo "${target_file} ${installed_hash}" >> "$MANIFEST_TMP"
                fi
                echo "  skip    $rel (user-modified)"
                n_skip=$((n_skip + 1))
            fi
        else
            # New file — install it
            cp "$src_file" "$target_file"
            echo "${target_file} ${src_hash}" >> "$MANIFEST_TMP"
            n_new=$((n_new + 1))
        fi
    done < <(find "$src" -type f | sort)

    local parts=""
    [ $n_new    -gt 0 ] && parts="${parts}${n_new} new, "
    [ $n_update -gt 0 ] && parts="${parts}${n_update} updated, "
    [ $n_same   -gt 0 ] && parts="${parts}${n_same} current, "
    [ $n_skip   -gt 0 ] && parts="${parts}${n_skip} skipped (user-modified)"
    parts="${parts%, }"
    echo "  ✓ $label: ${parts:-nothing to do}"
}

# ── Helper: safe merge a single file ───────────────────────────────────
# Applies the same manifest-aware update semantics as safe_copy_dir.
# Usage: safe_copy_file <src_file> <target_file> <label>
safe_copy_file() {
    local src_file="$1"
    local target_file="$2"
    local label="$3"

    [ -f "$src_file" ] || return 0
    mkdir -p "$(dirname "$target_file")"

    local src_hash
    src_hash=$(file_hash "$src_file")

    if [ -f "$target_file" ]; then
        local current_hash
        current_hash=$(file_hash "$target_file")
        local installed_hash
        installed_hash=$(manifest_get "$target_file")

        if [ "$src_hash" = "$current_hash" ]; then
            echo "${target_file} ${src_hash}" >> "$MANIFEST_TMP"
            echo "  ✓ $label: current"
        elif [ -n "$installed_hash" ] && [ "$current_hash" = "$installed_hash" ]; then
            cp "$src_file" "$target_file"
            echo "${target_file} ${src_hash}" >> "$MANIFEST_TMP"
            echo "  ✓ $label: updated"
        else
            if [ -n "$installed_hash" ]; then
                echo "${target_file} ${installed_hash}" >> "$MANIFEST_TMP"
            fi
            echo "  ✓ $label: skipped (user-modified)"
        fi
    else
        cp "$src_file" "$target_file"
        echo "${target_file} ${src_hash}" >> "$MANIFEST_TMP"
        echo "  ✓ $label: new"
    fi
}

ensure_exocortex_data_stubs() {
    mkdir -p ".exocortex/events" ".exocortex/control"

    if [ ! -f ".exocortex/SESSION_CONTEXT.md" ]; then
        cat > ".exocortex/SESSION_CONTEXT.md" << 'EOF_SESSION'
# Session Context

## RIGHT NOW

_No active session context yet. Run /work or /save to populate this file._
EOF_SESSION
    fi

    if [ ! -f ".exocortex/TODO.md" ]; then
        cat > ".exocortex/TODO.md" << 'EOF_TODO'
# TODO

## Ready

_No tasks captured yet._
EOF_TODO
    fi

    if [ ! -f ".exocortex/LESSONS.md" ]; then
        cat > ".exocortex/LESSONS.md" << 'EOF_LESSONS'
# Lessons

_No lessons captured yet._
EOF_LESSONS
    fi

    if [ ! -f ".exocortex/PROJECT_MEMORY.md" ]; then
        cat > ".exocortex/PROJECT_MEMORY.md" << 'EOF_MEMORY'
# Project Memory

_No project-specific memory captured yet._
EOF_MEMORY
    fi

    if [ ! -f ".exocortex/control/INTERRUPTS.md" ]; then
        cat > ".exocortex/control/INTERRUPTS.md" << 'EOF_INTERRUPTS'
# Interrupts

> Capture lane - things that come up while working on something else.
> Run /groom periodically to move items to BACKLOG or TODO.

_No interrupts captured yet._
EOF_INTERRUPTS
    fi

    if [ ! -f ".exocortex/control/BACKLOG.md" ]; then
        cat > ".exocortex/control/BACKLOG.md" << 'EOF_BACKLOG'
# Backlog

> Items under investigation. Moved here from INTERRUPTS after grooming.
> Run /refine-backlog to promote items to TODO.

_No backlog items yet._
EOF_BACKLOG
    fi

    if [ ! -f ".exocortex/control/ROADMAP.md" ]; then
        cat > ".exocortex/control/ROADMAP.md" << 'EOF_ROADMAP'
# Roadmap

> Strategic planning for this project.
> Updated periodically during reviews.

_No roadmap defined yet._
EOF_ROADMAP
    fi
}

echo "📦 Downloading exocortex template..."
if [ -n "${EXOCORTEX_LOCAL_SOURCE:-}" ]; then
    if [ ! -d "$EXOCORTEX_LOCAL_SOURCE" ]; then
        echo "❌ EXOCORTEX_LOCAL_SOURCE is set but not a directory: $EXOCORTEX_LOCAL_SOURCE"
        exit 1
    fi
    echo "  📂 Using local source: $EXOCORTEX_LOCAL_SOURCE"
    # Copy the directory contents (including .git? no — we only need the working tree)
    mkdir -p "$_EXOCORTEX_TMP/exocortex-template"
    # Use rsync if available (handles dotfiles cleanly), fall back to cp
    if command -v rsync >/dev/null 2>&1; then
        rsync -a --exclude='.git' "$EXOCORTEX_LOCAL_SOURCE/" "$_EXOCORTEX_TMP/exocortex-template/"
    else
        # cp -R with a trailing dot to copy dotfiles
        (cd "$EXOCORTEX_LOCAL_SOURCE" && tar cf - --exclude='.git' . ) | (cd "$_EXOCORTEX_TMP/exocortex-template" && tar xf -)
    fi
    echo "  ✓ Copied"
else
    git clone --quiet --depth 1 --branch "$BRANCH" "$REPO_URL" "$_EXOCORTEX_TMP/exocortex-template" 2>&1 | grep -v "^$" || true
    echo "  ✓ Downloaded"
fi

# ── Integrity check ───────────────────────────────────────────────────
# Verify the cloned content against the published SHA256SUMS file.
# This catches tampering in transit (MITM, CDN compromise, etc.).
# Skipped automatically if SHA256SUMS is missing (e.g. local installs).
SUMS_FILE="$_EXOCORTEX_TMP/exocortex-template/SHA256SUMS"
if [ -f "$SUMS_FILE" ]; then
    echo ""
    echo "🔒 Verifying integrity..."
    _verify_failed=0
    while IFS= read -r line; do
        [[ "$line" =~ ^#.*$ || -z "$line" ]] && continue
        expected_hash="${line%% *}"
        rel_path="${line##* }"
        actual_file="$_EXOCORTEX_TMP/exocortex-template/$rel_path"
        if [ ! -f "$actual_file" ]; then
            echo "  ⚠️  Missing: $rel_path (skipping)"
            continue
        fi
        actual_hash=$(shasum -a 256 "$actual_file" 2>/dev/null | awk '{print $1}')
        if [ "$actual_hash" != "$expected_hash" ]; then
            echo "  ❌ INTEGRITY FAIL: $rel_path"
            echo "     Expected: $expected_hash"
            echo "     Got:      $actual_hash"
            _verify_failed=1
        fi
    done < "$SUMS_FILE"
    if [ "$_verify_failed" -eq 1 ]; then
        echo ""
        echo "❌ Integrity check failed — installation aborted."
        echo "   The downloaded files do not match the published checksums."
        echo "   This could indicate a network issue or tampered content."
        echo "   Try again, or install from a direct git clone:"
        echo "     git clone https://github.com/EnkratFlow/exocortex-template.git"
        echo "     bash exocortex-template/install.sh"
        exit 1
    fi
    echo "  ✓ All files verified"
fi

# ── Read template version ─────────────────────────────────────────────
TEMPLATE_VERSION="unknown"
if [ -f "$_EXOCORTEX_TMP/exocortex-template/VERSION" ]; then
    TEMPLATE_VERSION="$(tr -d '[:space:]' < "$_EXOCORTEX_TMP/exocortex-template/VERSION")"
fi
if [ "$IS_UPDATE" = "true" ]; then
    echo ""
    echo "📌 Version: ${INSTALLED_VERSION:-unknown} → ${TEMPLATE_VERSION}"
fi

# ── Copy files ────────────────────────────────────────────────────────

echo ""
echo "📁 Installing to $(pwd)/"

# Merge .exocortex/ — system files (commands, scripts, docs, bootstrap) update;
# user data (memory, todos, sessions, lessons) is never overwritten
safe_copy_dir "$_EXOCORTEX_TMP/exocortex-template/.exocortex" ".exocortex" ".exocortex/"
ensure_exocortex_data_stubs

# Track installed version
if [ -f "$_EXOCORTEX_TMP/exocortex-template/VERSION" ]; then
    cp "$_EXOCORTEX_TMP/exocortex-template/VERSION" ".exocortex/.version"
fi

# Copy editor pointer files (thin pointers to AI_BOOTSTRAP.md)
for pfile in CLAUDE.md .windsurfrules .rules; do
    if [ -f "$_EXOCORTEX_TMP/exocortex-template/$pfile" ]; then
        if [ -f "$pfile" ]; then
            echo "  ⚠️  $pfile already exists — keeping yours"
        else
            cp "$_EXOCORTEX_TMP/exocortex-template/$pfile" .
            echo "  ✓ Copied $pfile"
        fi
    fi
done

# Copilot instructions go in .github/
if [ -f "$_EXOCORTEX_TMP/exocortex-template/.github/copilot-instructions.md" ]; then
    mkdir -p .github
    if [ -f ".github/copilot-instructions.md" ]; then
        echo "  ⚠️  .github/copilot-instructions.md already exists — keeping yours"
    else
        cp "$_EXOCORTEX_TMP/exocortex-template/.github/copilot-instructions.md" .github/
        echo "  ✓ Copied .github/copilot-instructions.md"
    fi
fi

# ── Cursor (.cursor/) ─────────────────────────────────────────────────

echo ""
echo "⌨️  Installing Cursor files..."
safe_copy_dir "$_EXOCORTEX_TMP/exocortex-template/.cursor/commands" ".cursor/commands" "commands"
safe_copy_dir "$_EXOCORTEX_TMP/exocortex-template/.cursor/skills"   ".cursor/skills"   "skills"
safe_copy_dir "$_EXOCORTEX_TMP/exocortex-template/.cursor/rules"    ".cursor/rules"    "rules"
safe_copy_dir "$_EXOCORTEX_TMP/exocortex-template/.cursor/agents"   ".cursor/agents"   "agents"
safe_copy_dir "$_EXOCORTEX_TMP/exocortex-template/.cursor/hooks"    ".cursor/hooks"    "hooks"
safe_copy_file "$_EXOCORTEX_TMP/exocortex-template/.cursor/hooks.json" ".cursor/hooks.json" "hooks.json"

# Ensure hook scripts stay executable after merge.
if [ -d ".cursor/hooks" ]; then
    while IFS= read -r hook_script; do
        chmod +x "$hook_script"
    done < <(find ".cursor/hooks" -type f -name "*.sh" | sort)
fi

# ── VS Code Copilot role skills (.github/skills/) ─────────────────────

echo ""
echo "🤖 Installing VS Code Copilot skills..."
safe_copy_dir "$_EXOCORTEX_TMP/exocortex-template/.github/skills" ".github/skills" ".github/skills"

# ── Claude / VS Code workflow commands (.claude/skills/) ─────────────

echo ""
echo "🧠 Installing workflow command skills..."
safe_copy_dir "$_EXOCORTEX_TMP/exocortex-template/.claude/skills" ".claude/skills" ".claude/skills"

# Merge .gitignore entries
echo ""
echo "📝 Updating .gitignore..."
GITIGNORE_ENTRIES=(
    "# Exocortex"
    ".exocortex/.env"
    ".exocortex/events/*.md"
    "!.exocortex/events/.gitkeep"
)

if [ -f ".gitignore" ]; then
    if ! grep -q "exocortex" .gitignore 2>/dev/null; then
        echo "" >> .gitignore
        for entry in "${GITIGNORE_ENTRIES[@]}"; do
            echo "$entry" >> .gitignore
        done
        echo "  ✓ Added exocortex entries to existing .gitignore"
    else
        echo "  ✓ .gitignore already has exocortex entries"
    fi
else
    for entry in "${GITIGNORE_ENTRIES[@]}"; do
        echo "$entry" >> .gitignore
    done
    echo "  ✓ Created .gitignore with exocortex entries"
fi

# ── Write install manifest ───────────────────────────────────────────
{
    echo "# Exocortex install manifest — do not edit manually"
    echo "# Tracks which template files were installed so re-runs can update"
    echo "# unmodified files and skip user-modified ones."
    echo "# Format: <filepath> <sha256>"
    sort "$MANIFEST_TMP"
} > "$MANIFEST"
echo "  ✓ Install manifest updated"

# ── Run initialization (fresh install only) ──────────────────────────
# Skip on update — project name and API keys are already configured

if [ "$IS_UPDATE" = "false" ]; then
    echo ""
    echo "🔧 Running initialization..."
    echo ""

    if [ -n "$PROJECT_NAME" ]; then
        bash .exocortex/../init-project.sh 2>/dev/null || bash init-project.sh "$PROJECT_NAME" 2>/dev/null || {
            # init-project.sh might not be at root — copy it temporarily
            cp "$_EXOCORTEX_TMP/exocortex-template/init-project.sh" ./_exo_init_tmp.sh
            bash ./_exo_init_tmp.sh "$PROJECT_NAME"
            rm -f ./_exo_init_tmp.sh
        }
    else
        # Copy init script to project root for interactive use
        cp "$_EXOCORTEX_TMP/exocortex-template/init-project.sh" ./init-project.sh
        bash ./init-project.sh
        rm -f ./init-project.sh
    fi
else
    echo ""
    echo "  ⏭️  Skipping initialization (update mode — your config is preserved)"
fi

# ── Optional: install global plan-orchestrate rule + auto-save hook ───
GLOBAL_PLAN_HOOK_STATUS="skipped (non-interactive)"
if [ -f "$HOME/.cursor/rules/plan-orchestrate.mdc" ]; then
    echo "  ✓ Global plan-orchestrate rule already installed (skipping)"
    GLOBAL_PLAN_HOOK_STATUS="already installed"
elif [ -t 0 ]; then
    read -r -p "Install the plan-orchestrate rule + auto-save hook globally so they apply to non-exocortex projects too? [Y/n] " GLOBAL_INSTALL_REPLY
    if [[ -z "$GLOBAL_INSTALL_REPLY" || "$GLOBAL_INSTALL_REPLY" =~ ^[Yy]$ ]]; then
        mkdir -p "$HOME/.cursor/rules" "$HOME/.cursor/hooks"
        cp ".cursor/rules/plan-orchestrate.mdc" "$HOME/.cursor/rules/plan-orchestrate.mdc"
        cp ".cursor/hooks.json" "$HOME/.cursor/hooks.json"
        cp ".cursor/hooks/auto-save-phase.sh" "$HOME/.cursor/hooks/auto-save-phase.sh"
        chmod +x "$HOME/.cursor/hooks/auto-save-phase.sh"
        echo "  ✓ Global plan-orchestrate rule + auto-save hook installed"
        GLOBAL_PLAN_HOOK_STATUS="installed"
    else
        echo "  ⊘ Skipped global install. Project-level files installed normally."
        GLOBAL_PLAN_HOOK_STATUS="skipped by user"
    fi
fi

# ── Cleanup ───────────────────────────────────────────────────────────
# Temp dir cleaned up by trap

# ── Optional: Install enkratflow-mcp for RAG memory search ──────────────────
if [[ "$IS_UPDATE" != "true" ]] && [[ -z "$1" ]]; then
    if command -v pipx &>/dev/null || command -v pip3 &>/dev/null; then
        echo ""
        echo "  📡 Optional: RAG memory search via enkratflow-mcp"
        echo "  Enables /work, /shortterm, /longterm, /subconscious memory commands."
        echo ""
        read -p "  Install enkratflow-mcp now? [y/N] " -n 1 -r
        echo ""
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            if command -v pipx &>/dev/null; then
                pipx install 'enkratflow-mcp[vault]' && echo "  ✓ enkratflow-mcp installed via pipx"
            else
                pip3 install --user 'enkratflow-mcp[vault]' && echo "  ✓ enkratflow-mcp installed via pip"
            fi
            echo ""
            echo "  Next: add your RAG_API_KEY to .exocortex/.env"
            echo "  Get access at: https://enkratflow.ai"
        fi
    fi
fi

echo ""
if [ "$IS_UPDATE" = "true" ]; then
    echo "════════════════════════════════════════════════════"
    echo "  ✅ Exocortex updated successfully!"
    echo "════════════════════════════════════════════════════"
    echo ""
    echo "  System files updated. Your memory, todos, sessions,"
    echo "  and any customised files are exactly as you left them."
else
    echo "════════════════════════════════════════════════════"
    echo "  🎉 Exocortex v3 installed successfully!"
    echo "════════════════════════════════════════════════════"
    echo ""
    echo "  Your project now has AI-powered memory."
fi
echo ""
# Show release notes if the template ships a WHATSNEW.md
if [ -f "$_EXOCORTEX_TMP/exocortex-template/WHATSNEW.md" ]; then
    echo ""
    echo "📰 What's new in this release:"
    echo "────────────────────────────────"
    cat "$_EXOCORTEX_TMP/exocortex-template/WHATSNEW.md"
    echo "────────────────────────────────"
    echo ""
fi

cat <<'EOF'
🧩 Other IDE / LLM setup
────────────────────────
If your editor is not listed, add this instruction to whatever system prompt,
rules file, project instruction file, command snippet, custom mode, or agent
memory your IDE supports:

When the user types an Exocortex command like /work, /save, /ai-export, work,
save, or ai-export:

1. Read .exocortex/AI_BOOTSTRAP.md first.
2. Find .exocortex/commands/{command}.json.
3. Execute the JSON steps in order.
4. The JSON command is the source of truth if any instruction conflicts.
5. Do not invent extra prompts or duplicate command behavior in the adapter.
6. Never read, print, log, echo, or expose secret values.
7. In a multi-root workspace, identify the target repo before running shell steps.

If slash commands are not supported, use this in the AI chat:

Read .exocortex/AI_BOOTSTRAP.md, then run the Exocortex command /work.

Full adapter examples:
.exocortex/docs/IDE_INTEGRATION_GUIDE.md
EOF

echo "  Commands in Cursor or VS Code:"
echo "    /work      — Load context, see what to work on"
echo "    /save      — Save your progress"
echo "    /interrupt — Capture ideas without breaking flow"
echo "  ✓ Plan orchestration + auto-save hook: project-level installed (global: $GLOBAL_PLAN_HOOK_STATUS)"
echo ""
