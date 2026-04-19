# Exocortex Auto-Snapshot Agent

Automatically writes a raw git state event every 60 minutes while you're coding —
no `/save` discipline required. Works across all your repos without any per-repo
configuration.

## What it does

Every 60 minutes, the agent wakes up and:

1. Checks if VS Code, Cursor, or Claude Code is running — if not, does nothing
2. Scans every directory under `PROJECTS_ROOT` that has a `.exocortex/` folder
3. For each repo: checks if there are uncommitted changes or recent commits
4. If active, writes a minimal `.exocortex/events/*_autosave.md` with:
   - Current branch
   - Number of uncommitted files
   - Last 3 commit messages
   - List of modified files
   - Claude Code message count (last 2h)
5. Shows a macOS notification listing which repos were snapshotted

These events are consumed by `/daily-end` to give it raw material even if you
never ran `/save`.

---

## Install

**Run from inside any repo that has `.exocortex/`:**

```bash
cd ~/code/my-project    # ← must be inside a repo that has .exocortex/, not from ~
bash .exocortex/scripts/launchd/install_autosave.sh
```

When prompted for `PROJECTS_ROOT`, enter the **parent folder** of all your repos:

```
PROJECTS_ROOT [~/code]: ~/code
```

> **Important:** Include the `~/` prefix. If you type a bare name like `EnkratFlow`
> the installer will now auto-correct it to `~/EnkratFlow` and confirm what it
> expanded to — but it's clearer to type the full path.

The installer:
- Creates `~/.exocortex/config` with your settings (outside any repo — never committed)
- Copies `auto_snapshot.sh` to `~/.exocortex/scripts/` (stable path, survives repo moves)
- Generates `~/Library/LaunchAgents/com.exocortex.autosave.plist`
- Loads the agent with `launchctl` — starts immediately, persists across reboots

**One-time install only.** New repos under `PROJECTS_ROOT` are picked up automatically —
no per-repo steps needed.

---

## Configuration

Edit `~/.exocortex/config` (not inside any repo):

```bash
# Root directory scanned for repos with .exocortex/ folders
PROJECTS_ROOT=~/code

# Minimum minutes between snapshots per repo (prevents duplicates)
SNAPSHOT_INTERVAL_MIN=50

# Active hours — no snapshots outside this window (24h, local time)
ACTIVE_HOURS_START=7
ACTIVE_HOURS_END=23
```

After editing, reload the agent:

```bash
launchctl unload ~/Library/LaunchAgents/com.exocortex.autosave.plist
launchctl load   ~/Library/LaunchAgents/com.exocortex.autosave.plist
```

---

## Verify it's running

```bash
launchctl list | grep exocortex
# Should show: -  0  com.exocortex.autosave
```

Check recent activity:

```bash
# View agent logs
tail -50 ~/.exocortex/logs/autosave.log

# See generated snapshots in a repo
ls -lt ~/code/my-project/.exocortex/events/ | head -10
```

---

## Common mistakes

| Problem | Cause | Fix |
|---------|-------|-----|
| `No such file or directory` | Ran from `~` instead of inside a repo | `cd ~/code/my-project` first |
| Agent runs but no events appear | Wrong `PROJECTS_ROOT` (relative path) | Edit `~/.exocortex/config`, set `PROJECTS_ROOT=~/EnkratFlow`, reload agent |
| No events in a specific repo | No IDE detected, or repo is idle | Check `launchctl list | grep exocortex` and `tail ~/.exocortex/logs/autosave.log` |
| Want to add a new project root | Currently one root supported | Set `PROJECTS_ROOT` to the common parent, e.g. `~` to scan all, or symlink repos into one folder |

---

## Uninstall

```bash
# Run from inside any repo
bash .exocortex/scripts/launchd/uninstall_autosave.sh
```

This removes the launchd agent and plist. It does **not** delete:
- `~/.exocortex/config`
- `~/.exocortex/scripts/auto_snapshot.sh`
- Any existing `*_autosave.md` events in your repos

To reinstall cleanly, just run `install_autosave.sh` again.

---

## Files

| File | Purpose |
|------|---------|
| `install_autosave.sh` | One-time installer — run this |
| `uninstall_autosave.sh` | Clean removal |
| `com.exocortex.autosave.plist.template` | Plist template (do not edit directly) |
| `~/.exocortex/scripts/auto_snapshot.sh` | The installed agent script |
| `~/.exocortex/config` | Your machine-level config |
| `~/Library/LaunchAgents/com.exocortex.autosave.plist` | Generated plist (do not edit directly) |
| `~/.exocortex/logs/autosave.log` | Agent stdout/stderr |
