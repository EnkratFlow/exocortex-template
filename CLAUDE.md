# Claude Code Instructions

---
## ⛔ SECURITY RULE — NEVER VIOLATE

**NEVER read, print, log, echo, grep, cat, or include the VALUE of any API key, secret, or token in any chat message, code snippet, tool output, or terminal command output.**

This includes:
- Running `cat`, `grep`, `echo`, or any command that outputs key values to stdout
- Hardcoding key values into any Python, shell, or JS snippet you write
- Reading `.env` files with tools that return their contents

To test a key: write a shell script to `/tmp/`, run it, return only `valid`/`invalid`. The key value must never appear in your context or output.

If you are about to read or display a key value — **stop and refuse**.

---

**Read `.exocortex/AI_BOOTSTRAP.md` immediately.** It contains the complete command protocol, all 20 commands, memory system, and file structure for this project.

Then read `.exocortex/reference/MEMORY.md` for the project memory entry point.

These two files give you everything you need to operate this project's exocortex.
