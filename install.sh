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
#   3. Runs init-project.sh to replace placeholders and set up API keys
#   4. Cleans up the temp clone
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

# Check if .exocortex already exists
if [ -d ".exocortex" ]; then
    echo "⚠️  .exocortex/ already exists in this directory"
    read -p "  Overwrite? This will replace all exocortex files. (y/n): " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "❌ Installation cancelled"
        exit 0
    fi
    echo "  Removing existing .exocortex/..."
    rm -rf .exocortex
fi

# ── Clone template ────────────────────────────────────────────────────

TMPDIR=$(mktemp -d)
trap "rm -rf $TMPDIR" EXIT

echo "📦 Downloading exocortex template..."
git clone --quiet --depth 1 --branch "$BRANCH" "$REPO_URL" "$TMPDIR/exocortex-template" 2>&1 | grep -v "^$"
echo "  ✓ Downloaded"

# ── Copy files ────────────────────────────────────────────────────────

echo ""
echo "📁 Installing to $(pwd)/"

# Copy .exocortex directory
cp -r "$TMPDIR/exocortex-template/.exocortex" .
echo "  ✓ Copied .exocortex/"

# Copy editor pointer files (thin pointers to AI_BOOTSTRAP.md)
for pfile in .cursorrules CLAUDE.md .windsurfrules; do
    if [ -f "$TMPDIR/exocortex-template/$pfile" ]; then
        if [ -f "$pfile" ]; then
            echo "  ⚠️  $pfile already exists — keeping yours"
        else
            cp "$TMPDIR/exocortex-template/$pfile" .
            echo "  ✓ Copied $pfile"
        fi
    fi
done

# Copilot instructions go in .github/
if [ -f "$TMPDIR/exocortex-template/.github/copilot-instructions.md" ]; then
    mkdir -p .github
    if [ -f ".github/copilot-instructions.md" ]; then
        echo "  ⚠️  .github/copilot-instructions.md already exists — keeping yours"
    else
        cp "$TMPDIR/exocortex-template/.github/copilot-instructions.md" .github/
        echo "  ✓ Copied .github/copilot-instructions.md"
    fi
fi

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

# ── Run initialization ────────────────────────────────────────────────

echo ""
echo "🔧 Running initialization..."
echo ""

if [ -n "$PROJECT_NAME" ]; then
    bash .exocortex/../init-project.sh 2>/dev/null || bash init-project.sh "$PROJECT_NAME" 2>/dev/null || {
        # init-project.sh might not be at root — copy it temporarily
        cp "$TMPDIR/exocortex-template/init-project.sh" ./_exo_init_tmp.sh
        bash ./_exo_init_tmp.sh "$PROJECT_NAME"
        rm -f ./_exo_init_tmp.sh
    }
else
    # Copy init script to project root for interactive use
    cp "$TMPDIR/exocortex-template/init-project.sh" ./init-project.sh
    bash ./init-project.sh
    rm -f ./init-project.sh
fi

# ── Cleanup ───────────────────────────────────────────────────────────
# Temp dir cleaned up by trap

echo ""
echo "════════════════════════════════════════════════════"
echo "  🎉 Exocortex v3 installed successfully!"
echo "════════════════════════════════════════════════════"
echo ""
echo "  Your project now has AI-powered memory."
echo ""
echo "  Try these commands in Cursor or VS Code:"
echo "    /work      — Load context, see what to work on"
echo "    /save      — Save your progress"
echo "    /interrupt — Capture ideas without breaking flow"
echo ""
