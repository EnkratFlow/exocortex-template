#!/bin/bash
# Reminder-only compatibility hook. Automatic event/checkpoint creation and
# cross-repository scanning were retired by the public-v2 protocol.

set -euo pipefail
echo "Exocortex reminder: consider an explicitly authorized local narrative save."
echo "No repository, event, checkpoint, credential, provider, or external destination was accessed."
exit 0
