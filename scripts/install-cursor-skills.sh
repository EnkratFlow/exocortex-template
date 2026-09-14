#!/bin/bash
# Global editor-home installation is not part of project-local template install.

set -euo pipefail
echo "No global Cursor skill was installed or updated." >&2
echo "Use repository-local adapters, or create a separately approved guarded global-install work item." >&2
exit 2
