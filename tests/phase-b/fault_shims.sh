#!/bin/bash
# Create deny-network command shims in a caller-owned new directory.
set -euo pipefail
TARGET="${1:-}"
[ -n "$TARGET" ] && [ ! -e "$TARGET" ] || { echo "fault_shims target must be a new path" >&2; exit 2; }
mkdir -p "$TARGET"
for name in curl wget nc ssh scp; do
    printf '#!/bin/bash\necho "network command denied by Phase B harness" >&2\nexit 97\n' > "$TARGET/$name"
    chmod +x "$TARGET/$name"
done
printf '%s\n' "$TARGET"
