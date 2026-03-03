#!/bin/bash
# Install the exocortex pre-commit hook into the local git repo.
# Run this once from the exocortex-template project root:
#
#   bash tests/install-pre-commit-hook.sh
#
# The hook blocks commits that touch install.sh or tests/ unless the
# full test suite passes first. Takes ~2 minutes on first run.

set -e

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || {
    echo "❌ Not inside a git repository. Run from the exocortex-template root."
    exit 1
}

HOOK_FILE="$REPO_ROOT/.git/hooks/pre-commit"
TESTS_DIR="$REPO_ROOT/tests"

[ -f "$TESTS_DIR/run_tests.sh" ] || {
    echo "❌ tests/run_tests.sh not found. Run from the exocortex-template root."
    exit 1
}

cat > "$HOOK_FILE" << 'HOOK'
#!/bin/bash
# Exocortex pre-commit hook — auto-installed by tests/install-pre-commit-hook.sh
# Runs the install.sh test suite when relevant files are staged.

REPO_ROOT="$(git rev-parse --show-toplevel)"
TESTS="$REPO_ROOT/tests/run_tests.sh"

[ -f "$TESTS" ] || exit 0   # hook installed but tests missing — allow commit

# Only run when install.sh, tests/, or template content is staged
changed=$(git diff --cached --name-only 2>/dev/null)
if echo "$changed" | grep -qE "^install\.sh$|^tests/|^\.exocortex/|^\.cursor/|^\.claude/|^\.github/skills/"; then
    echo ""
    echo "🧪 Exocortex: running install.sh test suite (changed files affect install logic)..."
    echo ""
    if bash "$TESTS"; then
        echo ""
        echo "✅ Tests passed — proceeding with commit"
        echo ""
    else
        echo ""
        echo "❌ Tests FAILED — commit blocked"
        echo "   Fix the failures above, then commit again."
        echo "   To skip (dangerous): git commit --no-verify"
        echo ""
        exit 1
    fi
fi
HOOK

chmod +x "$HOOK_FILE"

echo ""
echo "✅ Pre-commit hook installed at $HOOK_FILE"
echo ""
echo "   It will run 'bash tests/run_tests.sh' automatically when you"
echo "   stage changes to: install.sh, tests/, .exocortex/, .cursor/,"
echo "   .claude/, or .github/skills/"
echo ""
echo "   Bypass with: git commit --no-verify (use sparingly)"
echo ""
