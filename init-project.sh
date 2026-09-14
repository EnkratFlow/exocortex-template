#!/bin/bash
# Minimal project-local initializer. It never reads credentials, rewrites
# memory, installs packages, or changes editor/system state.

set -euo pipefail

PROJECT_NAME="${1:-$(basename "$PWD")}"
[ -d .exocortex ] || { echo "ERROR: .exocortex directory not found" >&2; exit 1; }
[ "$PWD" != "${HOME:-/__no_home__}" ] || { echo "ERROR: refusing to initialize user home" >&2; exit 1; }

if [ ! -e .exocortex/.project-name ]; then
    printf '%s\n' "$PROJECT_NAME" > .exocortex/.project-name
fi

if [ -d .exocortex/scripts ]; then
    find .exocortex/scripts -type f \( -name '*.sh' -o -name '*.py' \) -exec chmod +x {} \;
fi
if [ -d .cursor/hooks ]; then
    find .cursor/hooks -type f -name '*.sh' -exec chmod +x {} \;
fi

echo "Project-local initialization complete for: $PROJECT_NAME"
echo "Credentials, providers, packages, global editor state, services, and external sync: not accessed."
