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
# What this does:
#   1. Clones exocortex-template to a temp directory
#   2. Copies .exocortex/ and editor pointer files to the current directory
#   3. Copies .cursor/ (commands, skills, rules, agents) — safe merge, never overwrites modified files
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
    INSTALLED_VERSION="$(grep -m1 'version' .exocortex/AI_BOOTSTRAP.md 2>/dev/null | awk '{print $NF}' || echo 'unknown')"
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

echo "📦 Downloading exocortex template..."
git clone --quiet --depth 1 --branch "$BRANCH" "$REPO_URL" "$_EXOCORTEX_TMP/exocortex-template" 2>&1 | grep -v "^$" || true
echo "  ✓ Downloaded"

# ── Copy files ────────────────────────────────────────────────────────

echo ""
echo "📁 Installing to $(pwd)/"

# Merge .exocortex/ — system files (commands, scripts, docs, bootstrap) update;
# user data (memory, todos, sessions, lessons) is never overwritten
safe_copy_dir "$_EXOCORTEX_TMP/exocortex-template/.exocortex" ".exocortex" ".exocortex/"

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
echo "  Commands in Cursor or VS Code:"
echo "    /work      — Load context, see what to work on"
echo "    /save      — Save your progress"
echo "    /interrupt — Capture ideas without breaking flow"
echo ""
