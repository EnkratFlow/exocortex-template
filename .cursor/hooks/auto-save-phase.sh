#!/bin/bash
# auto-save-phase.sh
#
# Fires on subagentStop. If the subagent looks like a plan-orchestrate phase,
# inject a follow-up message telling the parent agent to run /save before
# starting the next phase. This enforces the "always /save after every phase"
# rule from ~/.cursor/rules/plan-orchestrate.mdc.
#
# Phase detection: the subagent's description (or any prominent label field)
# matches one of:
#   - "Phase N:" or "Phase N -" (e.g. "Phase 2: scaffold alerts")
#   - "phase-N-" prefix (e.g. "phase-2-scaffold")
#   - Contains "phase" as a standalone word AND a digit
#
# Non-phase subagents (exploration, quick lookups, browser automation) get
# no follow-up — the hook silently exits 0.
#
# Defensive against unknown stdin shapes: tries several common field names
# and uses jq if available, falls back to grep otherwise. Never blocks.

set -u

# Read stdin once. If empty (manual run, debug), exit cleanly.
input="$(cat)"
if [[ -z "$input" ]]; then
  exit 0
fi

# Pull a description string from whatever field shape the event uses.
# Tries jq first (cleanest), falls back to grep on raw JSON.
desc=""
if command -v jq >/dev/null 2>&1; then
  desc="$(printf '%s' "$input" | jq -r '
    .description
    // .subagent_description
    // .agent_description
    // .task_description
    // .name
    // .subagent.description
    // .input.description
    // empty
  ' 2>/dev/null || true)"
fi

# Fallback: pull the first description-like value via grep.
if [[ -z "$desc" ]]; then
  desc="$(printf '%s' "$input" \
    | grep -oE '"(description|subagent_description|name)"[[:space:]]*:[[:space:]]*"[^"]*"' \
    | head -1 \
    | sed -E 's/^[^:]*:[[:space:]]*"([^"]*)"$/\1/')"
fi

# Phase heuristic. Cheap regex; if it doesn't match, this isn't a phase
# subagent and we exit silently.
is_phase=0
if [[ "$desc" =~ [Pp]hase[[:space:]]*[0-9]+[:[:space:]\-] ]]; then
  is_phase=1
elif [[ "$desc" =~ phase-[0-9]+- ]]; then
  is_phase=1
fi

if [[ "$is_phase" -ne 1 ]]; then
  exit 0
fi

# Sanitize the description for the followup message (strip quotes/newlines).
clean_desc="$(printf '%s' "$desc" | tr -d '\n\r"' | head -c 200)"

# Inject the follow-up. loop_limit:1 in hooks.json prevents this from
# infinite-looping if /save itself spawns subagents.
cat <<EOF
{
  "followup_message": "Phase complete (subagent stopped): \"${clean_desc}\". Per plan-orchestrate.mdc Step 5a, run /save now to checkpoint this phase BEFORE starting the next one. Use Step 5b hybrid pattern: (1) one-line 'checkpointing X' for the user, (2) spawn a Task subagent (model=claude-4.5-haiku-thinking, description='phase-save-format') to draft the full event body to /tmp/save_event.md, (3) run the shell steps of save.json yourself. Header format: 'Phase checkpoint — ${clean_desc}'. If this was the final phase, after /save also write the end-of-plan model-routing summary."
}
EOF
exit 0
