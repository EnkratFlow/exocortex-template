---
name: save
description: Save current work state checkpoint
disable-model-invocation: true
---

Read `.exocortex/AI_BOOTSTRAP.md` immediately. It contains the complete command protocol and step execution rules.

Then execute `.exocortex/commands/save.json` exactly as written:

- run shell steps
- perform AI steps
- use outputs from previous steps
- present user_choice options if present

Do not invent extra prompts.
Do not manually edit `.exocortex/SESSION_CONTEXT.md` unless the command spec says to.
Never read or expose secret values.
