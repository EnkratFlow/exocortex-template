#!/bin/bash
# External reminder installation mutates another system and is not implicit.

set -euo pipefail
echo "No OpenClaw or Telegram change was made." >&2
echo "A destination-specific installation work item, exact approval, and guarded executor are required." >&2
exit 2
