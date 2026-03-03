# Quick Reference - AI Assistant Commands & Persona

**Last Updated:** 2026-02-07

---

## The Persona (Always Active)

Your AI assistant is a **senior multidisciplinary expert** with 20+ years across:
- Domain Expert (deep knowledge in your project's domain)
- Data Science (PhD-level statistics, quantitative research)
- Product Design (senior UX/UI designer, user research)
- Engineering (full-stack architect, database design, DevOps)

**You don't need commands to activate this.** Just ask your question and the AI will respond with appropriate expertise.

---

## When To Use What

### 🗣️ Just Ask (No Command)
Use for everyday questions and work:

```
"Why did this approach fail?"
"Fix this bug in the delete function"
"How should I design this UI?"
"Explain this error"
```

**The expert persona is already active. No command needed.**

---

### 📋 Workflow Commands (Memory System)

Use when you need the memory/context system:

| Command | When To Use | What It Does |
|---------|-------------|--------------|
| `/work` | Starting work, after breaks | Loads context, shows what you were doing, asks what to work on |
| `/save` | Before breaks, end of task | Saves progress to event system |
| `/scrum` | Daily standup | Reviews yesterday, plans today, identifies blockers |
| `/brief` | Quick status check | Fast status without full context load |
| `/daily-end` | End of day | Captures what you did, plans tomorrow |
| `/interrupt` | Mid-task idea/bug/concern | Quick capture without breaking flow |
| `/groom` | When INTERRUPTS has items | Reviews and moves items to BACKLOG or TODO |

### 🧠 Memory Commands

Use to query the AI-powered memory system:

| Command | When To Use | What It Does |
|---------|-------------|--------------|
| `/shortterm` | Need 7-31 day context | Semantic memory — themes and patterns |
| `/longterm` | Need 31+ day context | Compressed memory — long-term learnings |
| `/subconscious` | Need cross-cutting patterns | Pattern detection across ALL events (no time filter) |
| `/drill <topic>` | Deep-dive a specific topic | Topic-specific search across all events |
| `/history` | Looking for old work | Search events by keyword or date |

### 📊 Planning & Review Commands

Use for task management and periodic reviews:

| Command | When To Use | What It Does |
|---------|-------------|--------------|
| `/prioritize` | TODO needs reordering | Guided strategic reordering of TODO.md |
| `/refine-backlog` | Backlog items ready | Promote, defer, or delete backlog items |
| `/weekly-review` | End of week | Summarize week, triage interrupts, plan next week |
| `/monthly-review` | End of month | Directional review, course correction |

### 🔧 System Commands

Use for system-level operations:

| Command | When To Use | What It Does |
|---------|-------------|--------------|
| `/system-scan` | Onboarding, health check | Full read-only system analysis report |
| `/ai-export` | Generate system doc | Build system understanding document from actual code |
| `/ecosystem` | Cross-project view | Activity view from EnkratFlow hub |
| `/init-exocortex` | New project setup | Bootstrap .exocortex/ directory structure |

**Example:**
```
/work
```

---

### 🎛️ Mode Commands (Thinking Style)

Use when you want to shift HOW the AI thinks:

| Command | When To Use | Effect |
|---------|-------------|--------|
| `/strict_trading` | Working on critical business logic/rules | Maximum precision, validates assumptions, cites research, highlights risks |
| `/rapid_build` | Need something working ASAP | Implementation first, explanation later, assumes competence |
| `/deep_think` | Big architecture decisions | Explores multiple angles, considers edge cases, shows reasoning |
| `/design_mode` | UI/UX work | Focuses on user psychology, proposes design improvements |

**Example:**
```
/strict_trading

Review my risk calculation logic for the circuit breaker.
Are there edge cases I'm missing?
```

---

## Quick Scenarios

### Scenario 1: Starting Your Day
```
/work
```
→ Loads your context, shows what you were doing, asks what to work on today.

---

### Scenario 2: Just Asking Questions (Most Common)
```
Why does the bulk delete sometimes fail?
```
→ No command needed. I'll analyze as a senior engineer.

```
How does the risk assessment algorithm work?
```
→ No command needed. I'll explain as a trading psychologist.

---

### Scenario 3: Building Something Fast
```
/rapid_build

Add a "select all on this page" checkbox to the trades table.
```
→ I'll give you working code immediately, minimal explanation.

---

### Scenario 4: Critical Trading Logic
```
/strict_trading

I want to add a new rule: if threshold > limit within 30 seconds, 
flag as "impulsive entry". Review this for edge cases.
```
→ I'll be extra careful, validate assumptions, show risks.

---

### Scenario 5: Before Taking a Break
```
/save

Just finished implementing bulk delete for trades. 
Works but needs testing on production data.
```
→ Saves your progress to the event system.

---

## Common Patterns

**Pattern 1: Deep Work Session**
```
1. /work                    ← Start of day
2. [Work for 2 hours]
3. /save                    ← Before lunch
4. [Work for 2 hours]
5. /save                    ← Before break
6. /daily-end              ← End of day
```

**Pattern 2: Quick Questions (No Commands)**
```
"Fix this bug"
"Why is this slow?"
"How should I structure this?"
```
→ Just ask. The persona handles it.

**Pattern 3: Switching Modes**
```
/rapid_build
Build X feature quickly

[Later in conversation]

/strict_trading
Now review the critical business logic carefully
```

---

## Pro Tips

1. **Most of the time, no command needed** - Just ask your question
2. **Use `/work` when starting** - It loads your context
3. **Use `/save` before breaks** - Captures progress
4. **Use mode commands sparingly** - Only when you need a specific thinking style
5. **The persona is always there** - It adapts to what you're asking about

---

## Still Confused?

**Question:** Do I need a command to get expert advice?
**Answer:** No. Just ask. The persona is always active.

**Question:** When should I use commands?
**Answer:** 
- Workflow commands (`/work`, `/save`) → When working with the memory system
- Mode commands (`/strict_trading`) → When you want a specific thinking style

**Question:** Can I just talk normally?
**Answer:** Yes! That's the main use case. Commands are for special situations.

---

## Emergency Help

If something seems broken:
```
"Read .exocortex/COMMAND_SYSTEM.md"
```

If you forget commands:
```
"Show me the command reference"
```

Or just read this file again.

**Full command reference:** `.exocortex/COMMAND_SYSTEM.md` (20 commands, schema docs)
