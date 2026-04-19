#!/usr/bin/env bash
# check_keys.sh — thin wrapper around check_keys.py
# SECURITY: Key values are never read or printed. See check_keys.py for implementation.

set -u

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
exec python3 "$SCRIPT_DIR/check_keys.py" "$@"
