#!/bin/bash

# Exocortex v3 — Project Initialization Script
# Replaces placeholders with your project-specific values
#
# USAGE: Run this script from your PROJECT ROOT directory after copying
#        the .exocortex/ directory and .cursorrules to your project.
#
# This script is run automatically by install.sh, or manually:
#   cd /path/to/your-project
#   bash .exocortex/init-project.sh

set -e

echo ""
echo "🧠 Exocortex v3 — Project Initialization"
echo "========================================="
echo ""

# Find .exocortex directory (could be run from project root or from .exocortex/)
if [ -d ".exocortex" ]; then
    EXOCORTEX_DIR=".exocortex"
elif [ -d "../.exocortex" ] && [ "$(basename "$(pwd)")" = ".exocortex" ]; then
    cd ..
    EXOCORTEX_DIR=".exocortex"
else
    echo "❌ Error: .exocortex directory not found"
    echo ""
    echo "Run this script from your project root:"
    echo "  cd /path/to/your-project"
    echo "  bash .exocortex/init-project.sh"
    echo ""
    exit 1
fi

echo "✓ Found $EXOCORTEX_DIR/"
echo ""

# ── Prompt for project name ────────────────────────────────────────────

if [ -n "$1" ]; then
    PROJECT_NAME="$1"
    echo "📝 Project name: $PROJECT_NAME (from argument)"
else
    read -p "📝 Enter your project name (e.g., my-awesome-app): " PROJECT_NAME
    if [ -z "$PROJECT_NAME" ]; then
        echo "❌ Error: Project name cannot be empty"
        exit 1
    fi
fi

# Get current date
CURRENT_DATE=$(date +%Y-%m-%d)

# Show summary
echo ""
echo "📋 Summary:"
echo "  Project Name:    $PROJECT_NAME"
echo "  Date:            $CURRENT_DATE"
echo ""

# Confirm (skip if project name was passed as argument — means automated install)
if [ -z "$1" ]; then
    read -p "✅ Continue with initialization? (y/n): " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "❌ Initialization cancelled"
        exit 0
    fi
fi

echo ""
echo "🔄 Replacing placeholders..."

# ── Detect OS for sed compatibility ────────────────────────────────────

if [[ "$OSTYPE" == "darwin"* ]]; then
    SED_INPLACE="sed -i .bak"
else
    SED_INPLACE="sed -i.bak"
fi

# ── Replace placeholders in all .md files ──────────────────────────────

FILE_COUNT=0

# Process all .md files recursively in .exocortex/
while IFS= read -r -d '' file; do
    if [ -f "$file" ]; then
        $SED_INPLACE "s/\[PROJECT_NAME\]/$PROJECT_NAME/g" "$file"
        $SED_INPLACE "s/\[DATE\]/$CURRENT_DATE/g" "$file"
        ((FILE_COUNT++))
        echo "  ✓ $file"
    fi
done < <(find "$EXOCORTEX_DIR" -name "*.md" -print0)

# Update .cursorrules if it exists
if [ -f ".cursorrules" ]; then
    $SED_INPLACE "s/\[PROJECT_NAME\]/$PROJECT_NAME/g" ".cursorrules"
    $SED_INPLACE "s/\[DATE\]/$CURRENT_DATE/g" ".cursorrules"
    echo "  ✓ .cursorrules"
fi

echo ""
echo "🧹 Cleaning up backup files..."
find "$EXOCORTEX_DIR" -name "*.bak" -type f -delete 2>/dev/null
find . -maxdepth 1 -name "*.bak" -type f -delete 2>/dev/null
echo "  ✓ Cleaned up"

echo ""
echo "🔧 Making scripts executable..."

# Make ALL scripts in scripts/ executable
if [ -d "$EXOCORTEX_DIR/scripts" ]; then
    chmod +x "$EXOCORTEX_DIR/scripts/"*.sh 2>/dev/null && echo "  ✓ Shell scripts (.sh)" || true
    chmod +x "$EXOCORTEX_DIR/scripts/"*.py 2>/dev/null && echo "  ✓ Python scripts (.py)" || true
fi

# ── API Key setup (optional) ──────────────────────────────────────────

echo ""
echo "🔑 API Key Setup"
echo ""
echo "  The exocortex AI memory features (short-term, long-term, subconscious)"
echo "  require an OpenAI API key. An Anthropic key is optional (fallback)."
echo ""

ENV_FILE="$EXOCORTEX_DIR/.env"

if [ -f "$ENV_FILE" ]; then
    echo "  ⚠️  .env already exists — skipping"
elif [ -z "$1" ]; then
    read -p "  Set up API keys now? (y/n): " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo ""
        read -p "  OpenAI API key (sk-...): " OPENAI_KEY
        read -p "  Anthropic API key (sk-ant-..., or press Enter to skip): " ANTHROPIC_KEY

        if [ -n "$OPENAI_KEY" ] || [ -n "$ANTHROPIC_KEY" ]; then
            echo "OPENAI_API_KEY=${OPENAI_KEY}" > "$ENV_FILE"
            echo "ANTHROPIC_API_KEY=${ANTHROPIC_KEY}" >> "$ENV_FILE"
            echo ""
            echo "  ✓ API keys saved to $ENV_FILE"
            echo "  ℹ️  This file is gitignored — your keys won't be committed"
        fi
    else
        echo ""
        echo "  ℹ️  You can set up keys later by copying .env.example to .env"
    fi
else
    echo "  ℹ️  Skipping API key setup (automated install)"
    echo "  ℹ️  Copy .env.example to .env and add your keys later"
fi

# ── Verify .gitignore covers .env ─────────────────────────────────────

if [ -f "$EXOCORTEX_DIR/.gitignore" ]; then
    if grep -q "\.env" "$EXOCORTEX_DIR/.gitignore"; then
        echo ""
        echo "  ✓ .gitignore protects .env files"
    fi
fi

# ── Done ──────────────────────────────────────────────────────────────

echo ""
echo "════════════════════════════════════════════"
echo "  ✅ Exocortex v3 Initialized!"
echo "════════════════════════════════════════════"
echo ""
echo "📁 Files updated: $FILE_COUNT"
echo ""
echo "🎯 Next Steps:"
echo "  1. Customize .exocortex/PROJECT_MEMORY.md (describe your system)"
echo "  2. Map your files in .exocortex/reference/ESSENTIAL_FILES.md"
echo "  3. Add your first tasks to .exocortex/TODO.md"
echo "  4. Start working with '/work' command"
echo ""
echo "📖 Key Documents:"
echo "  - .exocortex/AI_BOOTSTRAP.md       — Command protocol (start here)"
echo "  - .exocortex/COMMAND_SYSTEM.md      — Full command reference"
echo "  - .exocortex/reference/MEMORY.md    — Memory entry point"
echo "  - .cursorrules                      — Auto-loaded in Cursor"
echo ""
echo "🚀 Happy coding!"
echo ""
