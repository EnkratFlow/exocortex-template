# exocortex-reminder

<!-- EXOCORTEX_ENTRY: public-v2 -->
Read `AI_START_HERE.md` before substantive action. It is the canonical,
provider-neutral entry contract. This reminder never grants project, system,
schedule, or egress authority.
<!-- /EXOCORTEX_ENTRY -->

## Status

This is a manual integration design, not an enabled automation. Repository
installation does not deploy it, register a schedule, access OpenClaw, or send
a message.

Telegram delivery is external egress and is disabled unless the owner grants a
separate destination-specific external-system approval. OpenClaw/VPS setup is
also a separate system mutation outside the project-local writer capability.

## Intended reminder

After both external-system setup and Telegram delivery have been separately
approved outside this template, an operator may configure a short reminder to
ask the developer whether they want to run `/save`. The reminder is not a save,
checkpoint, lifecycle transition, or approval.

Suggested message:

```text
90-minute reminder

If this is a useful stopping point, consider requesting a local narrative save.
Nothing has been saved or synchronized automatically.
```

## Safety conditions

- An AI must stop before SSH, SCP, cron registration, OpenClaw deployment, or
  Telegram delivery and request the exact separate approval.
- No project credential, event, memory, or payload is read for a reminder.
- No reminder retries, escalates, records a checkpoint, or creates repository
  state.
- A future automated adapter requires its own approved transport, policy,
  capability binding, tests, and rollback procedure; this template does not
  provide one.
