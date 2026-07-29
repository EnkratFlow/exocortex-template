#!/bin/bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd -P)"
PYTHONDONTWRITEBYTECODE=1 python3 "$ROOT/tests/phase-b/test_phase_b.py"
