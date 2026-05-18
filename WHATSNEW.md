# What's New in 3.1.9

This release switches the Anthropic fallback model from haiku to sonnet across the memory scripts.

What changed:

- `.exocortex/scripts/check_keys.py`, `get_rightnow_memory.sh`, `get_shortterm_memory.sh`, `get_longterm_memory.sh`, and `_api_helpers.py` now default `ANTHROPIC_MODEL` to `claude-sonnet-4-6`
- `MEMORY_TIERS.md`, `docs/architecture.md`, `docs/implementation.md`, `docs/SUBCONSCIOUS_ARCHITECTURE.md`, and `docs/memory-system.md` updated to match
- Primary path (OpenAI `gpt-4o-mini`) is unchanged
- Override remains via `.exocortex/.env`: set `ANTHROPIC_MODEL=claude-3-haiku-20240307` to keep the old fallback

Heads up on cost: the Anthropic fallback now costs roughly 3x more per call (sonnet ~$3/$15 per MTok input/output vs haiku ~$1/$5). The fallback only fires when no `OPENAI_API_KEY` is set or OpenAI returns an error, so for most users the bill impact is minimal. If you rely on the Anthropic side, pin haiku via `.env`.

---

# Previous: 3.1.8

Bug fix in `generate_context.sh`. The event loop used `for FILE in $EVENTS`, which word-splits on whitespace, so any project path containing a space silently produced a `SESSION_CONTEXT.md` with the correct event count but all event bodies blank. Switched to `while IFS= read -r FILE; ... done <<< "$EVENTS"`. Added T19 regression test.

---

# Previous: 3.1.7

This release adds a safer customer update path.

What changed:

- Added `scripts/safe-update.sh`
- The safe updater creates a restore archive before touching anything
- It rehearses the update in a temporary copy first
- It verifies protected Exocortex memory/data files are unchanged
- It shows the rehearsal diff and asks before applying the real update
- It supports `--dry-run`, `--yes`, `--template`, and `--backup-dir`

This is the foundation for future npm/npx update tooling.

---

# Previous: 3.1.6

This release cleans up public documentation so it matches the current template.

What changed:

- Updated README command counts, test counts, backlog flow, and editor support notes
- Clarified that Codex works today through the universal adapter prompt, while native `.agents/skills/*` bridges are planned
- Updated the command system reference to describe all 23 commands and the editor-neutral JSON command protocol
- Added a regression test that catches stale README claims about command counts, test counts, Codex, and unknown IDE setup

This is a documentation-only release. It does not add native Codex bridge files yet.
