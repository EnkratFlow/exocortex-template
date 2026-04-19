# exocortex-reminder

A lightweight OpenClaw skill that sends a Telegram nudge every 90 minutes during
active work hours, reminding the developer to run `/save` to capture rich context
about what they just built.

## Purpose

Auto-snapshot writes raw git state automatically. But a rich `/save` — with
decisions, intent, and next steps — requires a brief active moment from the
developer. This skill fires that nudge so it hits you on your phone, wherever you are.

## Behaviour

When triggered by the OpenClaw cron scheduler, this skill sends a brief Telegram
message to the configured recipient. No external API calls. No memory reads.
Pure fire-and-forget notification.

## Trigger

This skill is designed to be triggered by `openclaw cron` on a schedule.
See SETUP.md for the exact cron command.

## Message

```
⏰ 90 min checkpoint

You've been coding for a while. Take 60 seconds to run /save in your active project.

It captures: what you built, decisions made, what's next.
The auto-snapshots got the raw state — /save adds the context that matters.
```

## Parameters

None. This skill takes no parameters and requires no configuration at call time.
All schedule configuration happens at cron registration time (see SETUP.md).

## Notes

- Works hours: 07:00–22:00 local time on the VPS (configure cron accordingly)
- Safe to run even when the developer is not coding — they'll see it when they return
- The reminder is non-intrusive: single message, no follow-up, no escalation
