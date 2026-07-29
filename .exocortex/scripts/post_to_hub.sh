#!/bin/bash
# Hub publication is external sync and uses the same exact egress protocol.

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ $# -eq 0 ]]; then
  echo "Denied: automatic hub posting is retired." >&2
  echo "Use: $0 inspect|stage|send <egress_guard arguments>" >&2
  exit 2
fi
if [[ "$1" != "inspect" && "$1" != "stage" && "$1" != "send" ]]; then
  echo "Denied: automatic hub posting is retired." >&2
  echo "Use: $0 inspect|stage|send <egress_guard arguments>" >&2
  exit 2
fi

exec python3 "$SCRIPT_DIR/egress_guard.py" "$@"
