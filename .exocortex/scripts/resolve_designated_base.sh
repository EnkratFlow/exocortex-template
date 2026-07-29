#!/usr/bin/env bash
# Resolve the exact designated base without mutating Git or repository state.

set -euo pipefail

WORK_ITEM=""
BRANCH_POLICY=".exocortex/control/BRANCH_POLICY.md"

usage() {
  echo "Usage: $0 --work-item <public-v2.json> [--branch-policy <path>]" >&2
  exit 2
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --work-item) WORK_ITEM="${2:-}"; shift 2 ;;
    --branch-policy) BRANCH_POLICY="${2:-}"; shift 2 ;;
    *) usage ;;
  esac
done

[[ -n "$WORK_ITEM" && -f "$WORK_ITEM" ]] || usage

read_json_field() {
  local file="$1"
  local expression="$2"
  if command -v jq >/dev/null 2>&1; then
    jq -er "$expression" "$file" 2>/dev/null
  else
    python3 - "$file" "$expression" <<'PY'
import json, sys
path, expression = sys.argv[1:]
with open(path, encoding="utf-8") as handle:
    value = json.load(handle)
if expression == ".designated_base.sha":
    value = value["designated_base"]["sha"]
elif expression == ".designated_base.ref // empty":
    value = value["designated_base"].get("ref") or ""
elif expression == ".designated_base.source":
    value = value["designated_base"]["source"]
else:
    raise SystemExit(2)
print(value)
PY
  fi
}

BASE_SHA="$(read_json_field "$WORK_ITEM" '.designated_base.sha')"
BASE_REF="$(read_json_field "$WORK_ITEM" '.designated_base.ref // empty' || true)"
BASE_SOURCE="$(read_json_field "$WORK_ITEM" '.designated_base.source')"

if [[ ! "$BASE_SHA" =~ ^[a-f0-9]{40}$ ]]; then
  echo '{"ok":false,"code":"invalid_designated_base"}'
  exit 2
fi

if ! git cat-file -e "${BASE_SHA}^{commit}" 2>/dev/null; then
  echo '{"ok":false,"code":"designated_base_missing"}'
  exit 2
fi

RESOLVED_SHA="$(git rev-parse "${BASE_SHA}^{commit}")"
if [[ "$RESOLVED_SHA" != "$BASE_SHA" ]]; then
  echo '{"ok":false,"code":"designated_base_not_exact"}'
  exit 2
fi

if [[ -n "$BASE_REF" ]] && git rev-parse --verify --quiet "${BASE_REF}^{commit}" >/dev/null; then
  REF_SHA="$(git rev-parse "${BASE_REF}^{commit}")"
else
  REF_SHA=""
fi

python3 - "$BASE_SHA" "$BASE_REF" "$REF_SHA" "$BASE_SOURCE" "$BRANCH_POLICY" <<'PY'
import json, sys
sha, ref, ref_sha, source, policy = sys.argv[1:]
print(json.dumps({
    "ok": True,
    "sha": sha,
    "ref": ref or None,
    "ref_sha": ref_sha or None,
    "source": source,
    "branch_policy_observed": policy if policy else None,
}, sort_keys=True))
PY
