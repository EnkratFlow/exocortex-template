# exocortex-reminder — OpenClaw VPS Setup

This guide deploys the `exocortex-reminder` skill to your OpenClaw VPS and
schedules it to fire every 90 minutes during work hours.

## Prerequisites

- OpenClaw running on your VPS (confirmed: `~/.openclaw/` exists)
- Telegram bot configured in OpenClaw
- SSH access to your VPS

## Step 1 — Copy the skill to your VPS

From your local machine (inside any repo with this skill):

```bash
scp .exocortex/skills/exocortex-reminder/SKILL.md \
    root@YOUR_VPS_IP:~/.openclaw/skills/exocortex-reminder/SKILL.md
```

Or manually create the file on the VPS:

```bash
ssh root@YOUR_VPS_IP
mkdir -p ~/.openclaw/skills/exocortex-reminder
# paste the contents of SKILL.md into the file
nano ~/.openclaw/skills/exocortex-reminder/SKILL.md
```

## Step 2 — Register the cron schedule

On your VPS, register the skill to fire every 90 minutes, Mon–Fri, 7am–10pm:

```bash
openclaw cron add \
  --skill exocortex-reminder \
  --schedule "*/90 7-22 * * 1-5" \
  --label "90min-save-nudge"
```

To include weekends (if you code on weekends):

```bash
openclaw cron add \
  --skill exocortex-reminder \
  --schedule "*/90 7-22 * * *" \
  --label "90min-save-nudge"
```

## Step 3 — Verify

```bash
# List all cron jobs
openclaw cron list

# Test the skill fires immediately
openclaw skill run exocortex-reminder
```

You should receive a Telegram message from your OpenClaw bot.

## Managing the schedule

```bash
# Pause
openclaw cron pause 90min-save-nudge

# Resume
openclaw cron resume 90min-save-nudge

# Remove
openclaw cron remove 90min-save-nudge
```

## Adjusting the reminder message

Edit the skill file on the VPS:

```bash
nano ~/.openclaw/skills/exocortex-reminder/SKILL.md
```

No restart required — OpenClaw reads skill files at each trigger.

## Notes

- The `*/90` cron syntax fires every 90 mins from the top of the hour (i.e., :00, :30 offset by 90-min intervals)  
- For exact "every 90 min from work-start" semantics, use `0 7,8,10,11,13,14,16,17,19,20 * * 1-5` instead  
- VPS clock timezone: verify with `timedatectl` and adjust schedule hours accordingly
