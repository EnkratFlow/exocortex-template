#!/bin/bash
# Install the exocortex pre-commit hook into the local git repo.
# Run this once from the exocortex-template project root:
#
#   bash tests/install-pre-commit-hook.sh
#
# The hook uses quick checks for documentation-only work and focused local
# checks for code changes. The long complete safety suite remains a once-per-
# candidate review/CI check and never runs from this hook.

set -e

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || {
    echo "❌ Not inside a git repository. Run from the exocortex-template root."
    exit 1
}

HOOK_FILE="$(git rev-parse --git-path hooks/pre-commit)"
case "$HOOK_FILE" in /*) ;; *) HOOK_FILE="$REPO_ROOT/$HOOK_FILE" ;; esac
TESTS_DIR="$REPO_ROOT/tests"

[ -f "$TESTS_DIR/run_tests.sh" ] || {
    echo "❌ tests/run_tests.sh not found. Run from the exocortex-template root."
    exit 1
}

cat > "$HOOK_FILE" << 'HOOK'
#!/bin/bash
# Exocortex pre-commit hook — auto-installed by tests/install-pre-commit-hook.sh
# Runs right-sized local checks when relevant files are staged.

REPO_ROOT="$(git rev-parse --show-toplevel)"
TESTS="$REPO_ROOT/tests/run_tests.sh"

[ -f "$TESTS" ] || exit 0   # hook installed but tests missing — allow commit

changed=$(git diff --cached --name-only 2>/dev/null)
[ -n "$changed" ] || exit 0

verify_checksums() {
    if command -v shasum >/dev/null 2>&1; then
        (cd "$REPO_ROOT" && shasum -a 256 -c SHA256SUMS)
    elif command -v sha256sum >/dev/null 2>&1; then
        (cd "$REPO_ROOT" && sha256sum -c SHA256SUMS)
    else
        echo "No SHA-256 verification tool is available" >&2
        return 1
    fi
}

echo ""
if ! echo "$changed" | grep -qEv '(^|/)[^/]+\.md$|^(SHA256SUMS|FILEMODES|VERSION|LICENSE)$'; then
    echo "🧪 Exocortex: quick documentation and integrity checks (normally under one minute)..."
    python3 "$REPO_ROOT/tests/test_documentation_contract.py" "$REPO_ROOT" \
      && python3 "$REPO_ROOT/.exocortex/scripts/generate_command_adapters.py" --check \
      && verify_checksums \
      && git diff --cached --check
elif ! echo "$changed" | grep -qEv '(^|/)[^/]+\.md$|^(SHA256SUMS|FILEMODES|VERSION|LICENSE)$|^\.exocortex/scripts/(create_event|read_memory_stack|generate_context)\.sh$|^\.exocortex/scripts/tests/test_event_tooling\.sh$'; then
    echo "🧪 Exocortex: focused event/memory checks, then quick contracts (normally under two minutes)..."
    bash "$REPO_ROOT/.exocortex/scripts/tests/test_event_tooling.sh" \
      && python3 "$REPO_ROOT/tests/test_documentation_contract.py" "$REPO_ROOT" \
      && python3 "$REPO_ROOT/.exocortex/scripts/generate_command_adapters.py" --check \
      && verify_checksums \
      && git diff --cached --check
else
    echo "🧪 Exocortex: affected deterministic suite (normally about two minutes)..."
    bash "$TESTS" \
      && python3 "$REPO_ROOT/.exocortex/scripts/generate_command_adapters.py" --check \
      && verify_checksums \
      && git diff --cached --check
fi
result=$?

if [ "$result" -ne 0 ]; then
    echo ""
    echo "❌ Checks failed — commit blocked"
    echo "   Fix the failures above, then commit again."
    echo "   To skip (dangerous): git commit --no-verify"
    echo ""
    exit "$result"
fi

echo ""
echo "✅ Right-sized checks passed — proceeding with commit"
echo ""
HOOK

chmod +x "$HOOK_FILE"

echo ""
echo "✅ Pre-commit hook installed at $HOOK_FILE"
echo ""
echo "   Documentation-only changes get quick checks; event/memory changes get"
echo "   focused checks; other code-plane changes get the affected deterministic"
echo "   suite. The long complete safety suite is never run by this hook."
echo ""
echo "   Bypass with: git commit --no-verify (use sparingly)"
echo ""
