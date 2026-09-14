#!/bin/bash
# Legacy direct SESSION_CONTEXT mutation is retired.

set -euo pipefail
echo "No state was saved. Use the canonical /save flow for an explicitly authorized local narrative event." >&2
echo "A narrative save is not a lifecycle checkpoint and never implies external sync." >&2
exit 2
