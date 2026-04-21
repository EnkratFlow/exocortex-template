# Exocortex v3

> ⚠️ **Public Beta** — works well but may have rough edges. Use at your own risk. Feedback welcome via [Issues](https://github.com/EnkratFlow/exocortex-template/issues).

> A portable memory system for developers and AI assistants that never forgets context.

## What is This?

The **Exocortex** is an external memory system for your development projects. It helps you (and AI coding assistants) maintain context, track decisions, capture lessons, and manage daily work -- across sessions, machines, and editors.

**Think of it as:** Your project's external brain that remembers what you're working on, what you've learned, and what needs to be done.

---

## Install

Run this once inside any project you want exocortex to manage:

```bash
cd /path/to/your-project
curl -sL https://raw.githubusercontent.com/EnkratFlow/exocortex-template/main/install.sh | bash
```

The memory system will be named **exocortex** by default. You can override this with your own name:

```bash
curl -sL https://raw.githubusercontent.com/EnkratFlow/exocortex-template/main/install.sh | bash -s "my-project"
```

**Local install** (if you have the template cloned, or for private repos without HTTPS access):

```bash
cd /path/to/your-project
bash /path/to/exocortex-template/install.sh "my-project"
```

Example if the template lives at `~/EnkratFlow/exocortex-template`:

```bash
cd ~/EnkratFlow/my-new-project
bash ~/EnkratFlow/exocortex-template/install.sh "my-new-project"
```

**The installer will:**
1. Download the latest exocortex template
2. Copy `.exocortex/` and editor pointer files to your project
3. Copy `.cursor/commands/` (Cursor slash commands like `/work`, `/save`, `/onboard`)
4. Replace all placeholders with your project name
5. Make scripts executable
6. Optionally set up API keys for AI memory features
7. Update `.gitignore` to protect secrets

**Safe for existing projects:** The installer detects whether this is a first install or an update and behaves accordingly.

- **First install** — copies all template files, creates `.exocortex/.install-manifest` (a SHA-256 hash of every installed file)
- **Update** — reads the manifest to drive a three-way merge per file:
  - Template file unchanged since last install → skip (already current)
  - File present in manifest and unmodified by you → update to latest template version
  - File modified by you since install → **preserve your version, never overwrite**
  - File not in manifest (new user-created file) → skip
- **User data files always preserved:** `PROJECT_MEMORY.md`, `LESSONS.md`, `TODO.md`, `SESSION_CONTEXT.md`, and everything under `events/` are hardcoded as untouchable regardless of manifest state.

---

## Cursor Setup (One-Time, Cursor Users Only)

This section is only relevant if you use Cursor. Skip it entirely if you use VS Code + Copilot, Claude Code, or Windsurf — those editors pick up the pointer files installed above automatically.

Cursor uses **user rules** and **global skills** instead of per-project files. You need to do **both steps below once** — the skills give the AI domain expertise, and the user rules tell it to follow the exocortex command protocol. Without the user rules, the AI won't know what `/work`, `/save`, or any other command means, even if the skills are installed.

### 1. Install Specialist Skills

The exocortex includes 16 specialist skills (devops, architect, ux-designer, etc.) that give the AI domain expertise when you need it.

```bash
# Clone the template (if you haven't already)
git clone https://github.com/EnkratFlow/exocortex-template.git /tmp/exocortex

# Preview what will be installed
bash /tmp/exocortex/scripts/install-cursor-skills.sh --list

# Install skills
bash /tmp/exocortex/scripts/install-cursor-skills.sh

# Clean up
rm -rf /tmp/exocortex
```

Skills install to `~/.cursor/skills/` (global, not per-project).

**Safe for existing setups:**
- New skills are added without touching your existing ones
- Skills you haven't modified are updated to the latest version
- Skills you've customized are skipped (use `--force` to overwrite all)
- Custom skills not in the template are never deleted

**Available skills:**

| Category | Skills |
|----------|--------|
| Build | architect, engineer, devops, sre, security, ai-architect |
| Product | product-manager, project-planner, ux-designer, cx-strategist, behavioral |
| Quality | qa-strategist, technical-writer, data-engineer |
| Strategy | chief-of-staff, deep-agent |
| Orientation | onboard |

### 2. Add User Rules (manual, in Cursor settings)

Add these two rules in **Cursor Settings > General > Rules for AI**:

**Rule 1 (Exocortex commands):**

```
All projects use the exocortex system. When the user types a command (/work, /save, /daily-end, etc.), read .exocortex/AI_BOOTSTRAP.md in the relevant repo for the full command protocol. In a multi-root workspace, determine the target repo FIRST: (1) user specified a repo, (2) a file is focused in the IDE, (3) session touched repos - list them, offer "all" or pick, WAIT for answer, (4) none - ask which repo, WAIT. Do NOT run shell steps until the target repo is confirmed. When starting work on a project, read .exocortex/reference/MEMORY.md for project context and reading order.
```

**Rule 2 (Specialist skills):**

```
Before starting any non-trivial task, read the matching specialist skill from ~/.cursor/skills/ based on the topic (CI/CD/deploy/Docker/nginx = devops, UI/UX/design = ux-designer, system design/API/scaling = architect, RAG/embeddings/AI = ai-architect, code quality/refactoring = engineer, auth/secrets = security, monitoring/logging = sre, tests/QA = qa-strategist, data pipelines/ETL = data-engineer, requirements/MVP = product-manager, planning/roadmap = project-planner, customer journey/retention = cx-strategist, habits/engagement = behavioral, strategy/priorities = chief-of-staff, docs/guides = technical-writer, complex/ambiguous = deep-agent). Read the skill file FIRST before doing any work. If unsure which skill, read ~/.cursor/skills/roster/SKILL.md.
```

**Note:** The AI may not always follow user rules automatically. If it skips a command or doesn't load a skill, prompt it directly: "read .exocortex/AI_BOOTSTRAP.md" or "read the devops skill".

---

## Other Editors

For non-Cursor editors, thin pointer files are created in your project during install:

- `CLAUDE.md` -- Claude Code (auto-loads)
- `.github/copilot-instructions.md` -- VS Code Copilot (auto-loads)
- `.windsurfrules` -- Windsurf (auto-loads)

All point to `.exocortex/AI_BOOTSTRAP.md` as the single source of truth.

---

## Upgrading

When a new version of the template is released, use `upgrade-exocortex.sh` to propagate code changes to your installed projects without touching your data.

```bash
# Upgrade one project
bash .exocortex/scripts/upgrade-exocortex.sh ~/path/to/your-project

# Preview what would change (no writes)
bash .exocortex/scripts/upgrade-exocortex.sh --dry-run ~/path/to/your-project

# Upgrade all hub-enabled projects at once
bash .exocortex/scripts/upgrade-exocortex.sh --all
```

**What the upgrade script does:**
- Runs the full test suite first — aborts immediately if any test fails
- Archives the current `.exocortex/` to `.exocortex/archive/pre-upgrade-YYYY-MM-DD/` (backup)
- Copies updated system files (commands, docs, scripts, skills)
- **Never touches:** `events/`, `.env`, `SESSION_CONTEXT.md`, `TODO.md`, `LESSONS.md`, `PROJECT_MEMORY.md`
- Updates `.install-manifest` to reflect the new hashes

The test-guard means a broken template can never reach your live projects.

---

## What's Included

```
CLAUDE.md                                 <-- Thin pointer (Claude Code auto-loads)
.windsurfrules                            <-- Thin pointer (Windsurf auto-loads)
.github/copilot-instructions.md           <-- Thin pointer (VS Code Copilot auto-loads)
.exocortex/
  |-- AI_BOOTSTRAP.md                     <-- Single source of truth for commands
  |-- COMMAND_SYSTEM.md                   <-- Schema reference & full command index
  |-- PERSONA_AND_COMMANDS.md             <-- AI persona & mode documentation
  |-- MEMORY_TIERS.md                     <-- Memory tier architecture
  |-- PROJECT_MEMORY.md                   <-- [CUSTOMIZE] System purpose & constraints
  |-- SESSION_CONTEXT.md                  <-- Current work state (auto-generated)
  |-- TODO.md                             <-- [CUSTOMIZE] Daily task board
  |-- LESSONS.md                          <-- Lessons learned
  |-- OPEN_DECISIONS.md                   <-- Unresolved decisions
  |-- .install-manifest                   <-- SHA-256 hashes of installed files (safe to commit)
  |-- commands/                           <-- 20 JSON command specs
  |-- control/                            <-- Project control center
  |-- docs/                               <-- System documentation
  |-- events/                             <-- Append-only work events
  |-- reference/                          <-- Quick reference files
  |-- scripts/                            <-- Automation (memory, events, etc.)
```

**Cursor-specific (per-project, installed by installer):**

```
.cursor/commands/                         <-- Cursor slash command triggers
  |-- work.md                             <-- /work command
  |-- save.md                             <-- /save command
  |-- onboard.md                          <-- /onboard command
  |-- ...                                 <-- 18 more command triggers
```

**Cursor-specific (global, installed separately):**

```
~/.cursor/skills/                         <-- 17 specialist skills (global)
  |-- roster/SKILL.md                     <-- Skill selection guide
  |-- onboard/SKILL.md                    <-- Codebase onboarding
  |-- devops/SKILL.md                     <-- Docker, CI/CD, VPS, nginx
  |-- architect/SKILL.md                  <-- System design, API contracts
  |-- engineer/SKILL.md                   <-- Code quality, patterns
  |-- ...                                 <-- 12 more specialist skills
```

---

## 20 Workflow Commands

### Daily
| Command | Purpose |
|---------|---------|
| `/work` | Load context, see what to work on (includes QMD cross-project results if installed) |
| `/scrum` | Daily standup |
| `/save` | Save progress before breaks |
| `/daily-end` | End of day review |
| `/interrupt` | Capture ideas without breaking flow |
| `/brief` | Quick status check |

### Memory (AI-powered)
| Command | Purpose |
|---------|---------|
| `/shortterm` | 7-31 day semantic memory |
| `/longterm` | 31+ day compressed memory |
| `/subconscious` | Cross-cutting pattern detection |
| `/drill <topic>` | Deep-dive on a specific topic |
| `/history` | Search older events |

### Planning
| Command | Purpose |
|---------|---------|
| `/groom` | Process interrupts |
| `/refine-backlog` | Promote backlog to TODO |
| `/prioritize` | Reorder TODO |
| `/weekly-review` | Weekly planning |
| `/monthly-review` | Monthly strategic review |

### System
| Command | Purpose |
|---------|---------|
| `/onboard` | Read and understand the codebase before working |
| `/system-scan` | Repository health check |
| `/ai-export` | Generate system doc |
| `/ecosystem` | Cross-project view |
| `/init-exocortex` | Bootstrap new project |

### Codebase Onboarding

`/onboard` scans the project and produces a structured summary: stack, structure, entry points, key modules, data layer, deployment, and current context from exocortex files. Caps at ~20 file reads so it stays fast and token-efficient.

For projects without exocortex, the same behavior is available as the `onboard` skill. Say "onboard to this project" or "read the codebase" and the AI will follow the same structured scan.

---

## Four-Tier Memory System

| Tier | Window | Purpose | Script |
|------|--------|---------|--------|
| **RIGHT NOW** | 0-7 days | Current work events | `get_rightnow_memory.py` |
| **SHORT-TERM** | 7-31 days | Semantic themes & patterns | `get_shortterm_memory.py` |
| **LONG-TERM** | 31+ days | Compressed context | `get_longterm_memory.py` |
| **SUBCONSCIOUS** | All events | Cross-cutting patterns, emotional valence | `get_subconscious_memory.py` |

Memory scripts use OpenAI (primary) with Anthropic fallback. API keys are loaded from `~/.exocortex/.env` (global, works for all projects) with `.exocortex/.env` in each project as an optional override. See [API Key Setup](#api-key-setup) below.

---

## Daily Workflow

### Morning (2 minutes)
1. Type `/work` -- loads context, shows next task
2. Pick ONE task from TODO
3. Start coding

### During Work
- Focus on your task
- Got an idea? `/interrupt` (< 1 minute capture, keep working)
- Before a break? `/save`

### End of Day (5 minutes)
1. Type `/daily-end`
2. Review proposed updates
3. Approve structural changes only

### Weekly
- `/groom` -- process interrupts
- `/refine-backlog` -- promote ready items
- `/prioritize` -- reorder TODO

---

## After Installation

1. **Customize** `.exocortex/PROJECT_MEMORY.md` -- describe your system
2. **Map files** in `.exocortex/reference/ESSENTIAL_FILES.md`
3. **Add tasks** to `.exocortex/TODO.md`
4. **Start working** with `/work`

---

## Contributing / Testing

The install logic is tested with a full suite before any change can be merged.

### Run the test suite

```bash
git clone https://github.com/EnkratFlow/exocortex-template.git
cd exocortex-template
bash tests/run_tests.sh
```

Expected output: `8 passed, 0 failed` with 49 assertions covering:

| Test | What it verifies |
|------|-----------------|
| T01 fresh install | Skeleton files created, manifest written |
| T02 update no manifest | User data preserved, new template files added |
| T03 system file updates | Manifest-tracked files updated when template changes |
| T04 user-modified preserved | Files you've edited are never overwritten |
| T05 idempotent | Running install twice produces identical results |
| T06 critical data files | SESSION\_CONTEXT, TODO, LESSONS, PROJECT\_MEMORY untouched |
| T07 events preserved | Event files byte-for-byte identical after update |
| T08 events not in manifest | Event files never added to the hash manifest |

### Pre-commit hook (contributor setup, one-time)

If you're contributing to the template itself, install the git hook once after cloning:

```bash
bash tests/install-pre-commit-hook.sh
```

The hook runs the full test suite before any commit that touches `install.sh`, `tests/`, `.exocortex/`, `.cursor/`, `.claude/`, or `.github/skills/`. The commit is blocked if any test fails.

Bypass when needed: `git commit --no-verify`

### CI

GitHub Actions runs the same test suite on every push and pull request that modifies those paths. See `.github/workflows/test.yml`. On failure, test output is uploaded as an artifact (7-day retention).

---

## API Key Setup

**Keys are optional.** The system works without them — `/save`, `/daily-end`, `/interrupt`, and all planning commands work with no key at all. Your events are stored as plain markdown files on your machine.

The commands that need a key are the AI memory summarisers: `/work`, `/shortterm`, `/longterm`, `/subconscious`, and `/drill`. Without a key, these commands display your raw event files. With a key, they send your events to an LLM and return a readable, compressed summary of what you've been working on.

### What data leaves your machine

When you run a memory command, the content of your event files (your work journal entries) is sent to OpenAI or Anthropic over HTTPS. This includes whatever you wrote in `/save` and `/daily-end` — typically: what you worked on, decisions made, git state. **Do not use AI memory features if your work is under NDA or you are uncomfortable with work logs leaving your machine.**

### What it costs

Keys are billed to your own account — exocortex has no subscription and takes no cut. The default model is `gpt-4o-mini`, one of OpenAI's cheapest. A typical `/work` call costs less than $0.01. Most developers running this daily spend **under $1/month**.

### Setup (one-time, covers all your projects)

```bash
mkdir -p ~/.exocortex
nano ~/.exocortex/.env   # or open in your editor
```

Add your keys:

```bash
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...   # optional — used as fallback if OpenAI fails
```

Every exocortex project on your machine reads this one file automatically. When you rotate a key, update it here and all projects are fixed instantly.

If you need a project-specific key (separate billing account, different rate limit), add it to `.exocortex/.env` inside that project — it overrides the global one for that project only.

Get keys: [OpenAI](https://platform.openai.com/api-keys) · [Anthropic](https://console.anthropic.com/settings/keys)

### Keys are never committed

`.exocortex/.env` and `~/.exocortex/.env` are both gitignored. Your keys stay on your machine. The repo contains no credentials of any kind.

---

## Requirements

- **git** (for installation)
- **bash** (macOS/Linux, Windows WSL works too)
- **OpenAI or Anthropic API key** (optional, for AI memory features — see [API Key Setup](#api-key-setup))
- **qmd** (optional, for cross-project context in `/work`) — if `qmd` is installed and on your PATH, `/work` automatically surfaces the top 3 related documents from your knowledge base. Silently skipped if not available.
- **Works with:** Cursor, VS Code + Copilot, Claude Code, Windsurf, any AI that reads files

---

## License

MIT — use freely, modify freely, no attribution required (but appreciated).

See [LICENSE](LICENSE) for the full text.

---

## Verifying the Installer

The installer runs a built-in integrity check automatically — it verifies every downloaded script against the published `SHA256SUMS` file before copying anything to your project. If anything fails, the install is aborted.

If you want to verify manually before running:

```bash
# Download the script and checksums separately
curl -sL https://raw.githubusercontent.com/EnkratFlow/exocortex-template/main/install.sh -o install.sh
curl -sL https://raw.githubusercontent.com/EnkratFlow/exocortex-template/main/SHA256SUMS -o SHA256SUMS

# Inspect the script yourself
less install.sh

# Verify the script hash matches
shasum -a 256 install.sh
# Compare against the install.sh line in SHA256SUMS

# Run when satisfied
bash install.sh "my-project"
```

Alternatively, clone the repo directly — git's transfer protocol is integrity-verified end-to-end:

```bash
git clone https://github.com/EnkratFlow/exocortex-template.git
bash exocortex-template/install.sh "my-project"
```

---

## Disclaimer

This software is provided **"as is"**, without warranty of any kind. By installing or using this software you accept full responsibility for any consequences. The author(s) are not liable for data loss, security issues, unexpected behaviour, or any other outcome resulting from use of this software.

This is a developer productivity tool. It writes files to your project directory and runs shell scripts. Review the code before running it if you have any concerns — everything is plain text and open for inspection.
