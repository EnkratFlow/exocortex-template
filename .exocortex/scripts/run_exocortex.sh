#!/usr/bin/env bash
# POSIX launcher: bounded PATH lookup, no disk scan, installs or persistent cache.
set -eu
if [ -n "${EXOCORTEX_PYTHON:-}" ]; then
    runtime="$EXOCORTEX_PYTHON"
else
    runtime="$(command -v python3 || command -v python || true)"
fi
if [ -z "$runtime" ] || [ ! -x "$runtime" ]; then
    echo 'EXOCORTEX_PYTHON_UNAVAILABLE: Set EXOCORTEX_PYTHON to Python 3.9+. Stop here; do not scan disks or search for gh.' >&2
    exit 2
fi
export PYTHONDONTWRITEBYTECODE=1 PYTHONUTF8=1 PYTHONIOENCODING=utf-8
exec "$runtime" -B -X utf8 "$(cd -- "$(dirname -- "$0")" && pwd)/command_runtime.py" "$@"
