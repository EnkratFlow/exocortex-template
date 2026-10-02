#!/usr/bin/env bash
# Legacy POSIX entry; native Windows uses run_exocortex.ps1 directly.
set -eu
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
exec bash "$SCRIPT_DIR/run_exocortex.sh" save "$@"
