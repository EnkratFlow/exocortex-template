# AI Persona & Command System - Complete Documentation

**Version:** 1.1  
**Last Updated:** 2026-02-07  
**Purpose:** Comprehensive guide to working with your AI assistant

---

## Table of Contents

1. [How The Persona Works](#how-the-persona-works)
2. [Command Types](#command-types)
3. [When To Use Commands vs. Just Ask](#when-to-use-commands-vs-just-ask)
4. [Workflow Commands Reference](#workflow-commands-reference)
5. [Mode Commands Reference](#mode-commands-reference)
6. [Common Workflows](#common-workflows)
7. [FAQ](#faq)

---

## How The Persona Works

### The Expert Persona Is ALWAYS Active

Your AI assistant has been configured with a **senior multidisciplinary expert persona** that includes:

**Trading & Psychology**
- Professional futures trader (ES/NQ specialist)
- Trading psychology & performance coaching
- Behavioral finance and decision-making under pressure
- Risk management and position sizing

**Data & Analysis**
- PhD-level statistics and data science
- Time series analysis and pattern recognition
- Quantitative research methodology
- A/B testing and experimental design

**Product & Design**
- Senior UX/UI product designer
- User research and behavioral psychology
- Design systems and component libraries
- Data visualization and information architecture

**Engineering**
- Full-stack software architect (React, TypeScript, Node.js, PostgreSQL)
- Database design and optimization
- API design and system integration
- DevOps and deployment automation

### Automatic Domain Switching

**You don't trigger the expertise - it's context-aware.**

When you ask: "Why did this trade fail psychologically?"
→ The AI thinks as a **trading psychologist** with 20 years experience

When you ask: "Fix this database query"
→ The AI thinks as a **senior database engineer**

When you ask: "How should this UI feel?"
→ The AI thinks as a **senior UX designer**

**This happens automatically based on what you're asking about.**

---

## Command Types

There are **two types** of commands:

### Type 1: Workflow Commands
**Purpose:** Interact with the memory/context system

Examples: `/work`, `/save`, `/groom`, `/daily-end`

**When to use:** When you need the AI to load context, save progress, or manage tasks.

---

### Type 2: Mode Commands
**Purpose:** Shift the AI's thinking style

Examples: `/strict_trading`, `/rapid_build`, `/deep_think`, `/design_mode`

**When to use:** When you want the AI to think in a specific way (more careful, faster, deeper, etc.)

---

## When To Use Commands vs. Just Ask

### ✅ Just Ask (90% of the time)

**You DON'T need commands for:**
- Questions: "How does the circuit breaker work?"
- Debugging: "Why is this query slow?"
- Code fixes: "Fix the bulk delete bug"
- Explanations: "Explain tilt risk calculation"
- Design feedback: "Is this UX intuitive?"
- Trade analysis: "Why did I overtrade today?"

**The persona is always active. Just talk normally.**

---

### 📋 Use Workflow Commands When:

**You DO need workflow commands for:**
- `/work` - Starting your day, need to see what you were doing
- `/save` - Before breaks, want to save progress
- `/scrum` - Daily standup review
- `/groom` - Task list is messy, need cleanup
- `/daily-end` - End of day summary
- `/history` - Looking for old work (7+ days ago)

**These interact with the memory system in `.exocortex/`**

---

### 🎛️ Use Mode Commands When:

**You DO need mode commands when you want specific thinking:**

| Situation | Command | Effect |
|-----------|---------|--------|
| Working on critical trading logic | `/strict_trading` | Extra careful, validates assumptions, cites research |
| Need working code FAST | `/rapid_build` | Code first, explain later |
| Big architecture decision | `/deep_think` | Explores alternatives, shows tradeoffs |
| UI/UX design work | `/design_mode` | User psychology focus |

**Mode commands shift HOW the AI thinks, not WHAT it knows.**

---

## Workflow Commands Reference

### `/work` - Load Context & Start Working

**When to use:**
- Starting your day
- After a break or context switch
- When you forget what you were working on

**What it does:**
1. Regenerates `SESSION_CONTEXT.md` from recent events
2. Loads project memory and lessons learned
3. Shows what you were last doing
4. Shows available tasks
5. Asks what you want to work on

**Example:**
```
/work
```

**Output:**
```
📋 Context Loaded

Last Working On:
- Implementing bulk delete for trades
- Status: Working, needs testing

Available Tasks:
- [ ] Add undo functionality
- [ ] Test on production data
- [ ] Document bulk operations

What would you like to work on?
A) Continue bulk delete testing
B) Start undo functionality
C) Something else
```

---

### `/save` - Save Progress Event

**When to use:**
- Before taking a break
- After completing a subtask
- Before switching context
- End of work session (if not using /daily-end)

**What it does:**
- Captures what you did
- Saves to `.exocortex/events/YYYY-MM-DD_HH-MM_event.md`
- Updates session context

**Example:**
```
/save

Implemented bulk delete with confirmation dialog.
Works for selecting multiple trades.
Still needs production testing.
```

**Output:**
```
✅ Progress saved to:
.exocortex/events/2026-01-28_14-30_bulk-delete-progress.md

SESSION_CONTEXT.md updated.
```

---

### `/scrum` - Daily Standup

**When to use:**
- Morning standup
- Start of work day
- Weekly check-in

**What it does:**
1. Reviews what you did yesterday
2. Plans what you'll do today
3. Identifies blockers

**Example:**
```
/scrum
```

**Output:**
```
📊 Daily Standup

Yesterday:
- ✅ Implemented edit trade modal
- ✅ Added delete confirmation
- 🔄 Started bulk delete (in progress)

Today's Plan:
- Complete bulk delete feature
- Test with production data
- Document new features

Blockers:
- None identified
```

---

### `/groom` - Clean Up Task List

**When to use:**
- TODO.md is messy or outdated
- Completed tasks not marked done
- Priorities unclear
- Weekly maintenance

**What it does:**
- Reviews all tasks
- Marks completed items
- Reprioritizes remaining work
- Removes stale tasks

**Example:**
```
/groom
```

---

### `/daily-end` - End of Day Summary

**When to use:**
- End of work day
- Before shutting down

**What it does:**
1. Summarizes what you accomplished
2. Updates task statuses
3. Plans tomorrow
4. Saves comprehensive event

**Example:**
```
/daily-end
```

---

### `/history` - Search Events

**When to use:** Looking for old work, "What did I do last month?"
**What it does:** Searches events by keyword, date range, or browse recent

---

### `/interrupt` - Quick Capture

**When to use:** Mid-task idea, bug, or concern
**What it does:** Captures to INTERRUPTS.md without breaking flow (< 1 minute)

---

### `/brief` - Quick Status

**When to use:** Fast check without full context load
**What it does:** Shows current state without running memory scripts

---

### Memory Commands

These query the AI-powered memory system (OpenAI 2-pass analysis of events):

### `/shortterm` - Semantic Memory (7-31 days)

**When to use:** Need recent context beyond the last week
**What it does:** Runs `get_shortterm_memory.py` — analyzes events from 7-31 days ago, identifies themes and patterns

---

### `/longterm` - Compressed Memory (31+ days)

**When to use:** Need long-term project context
**What it does:** Runs `get_longterm_memory.py` — analyzes events from 31+ days ago, produces compressed insights

---

### `/subconscious` - Pattern Detection (ALL events)

**When to use:** Need cross-cutting patterns, meta-cognitive insights
**What it does:** Runs `get_subconscious_memory.py` — analyzes ALL events with no time filter, detects recurring patterns, blind spots, behavioral trends

---

### `/drill <topic>` - Topic Deep-Dive

**When to use:** Need deep context on a specific topic
**What it does:** Runs `drill_memory.py` — searches ALL events for the given topic, produces focused analysis

**Example:**
```
/drill circuit breaker
```

---

### Planning & Review Commands

### `/prioritize` - Reorder TODO

**When to use:** TODO needs strategic reordering
**What it does:** Guided prioritization — asks 5 strategic questions, proposes new order

---

### `/refine-backlog` - Process Backlog

**When to use:** Backlog items ready for promotion
**What it does:** For each backlog item: promote to TODO, defer, or delete

---

### `/weekly-review` - End of Week

**When to use:** Weekly planning and review
**What it does:** Summarizes week, reviews interrupts by type, proposes next-week focus

---

### `/monthly-review` - Monthly Direction

**When to use:** Monthly strategic review
**What it does:** High-level reflection, trend analysis, directional course correction

---

### System Commands

### `/system-scan` - System Health Check

**When to use:** Onboarding, periodic maintenance
**What it does:** Read-only full system analysis report (6 questions answered)

---

### `/ai-export` - Generate System Doc

**When to use:** Need comprehensive system understanding document
**What it does:** Reads actual code (not planning docs), builds 7-section document

---

### `/ecosystem` - Cross-Project View

**When to use:** Cross-project activity overview
**What it does:** Reads EnkratFlow hub, shows per-project activity and focus suggestions

---

### `/init-exocortex` - Bootstrap New Project

**When to use:** Setting up .exocortex for a new project
**What it does:** Creates full directory structure with template files

---

## Mode Commands Reference

### `/strict_trading` - Maximum Precision Mode

**Use for:**
- Trading logic and rules
- Risk calculations
- Psychology algorithm changes
- Circuit breaker modifications
- Anything affecting trade decisions

**Effect:**
- Validates ALL assumptions
- Highlights edge cases and risks
- Cites research when making claims
- Shows tradeoffs explicitly
- Prioritizes correctness over speed

**Example:**
```
/strict_trading

I want to change the circuit breaker from 2 losses to 3 losses.
What are the implications?
```

**Response Style:**
```
⚠️ Risk Analysis: Circuit Breaker Threshold Change

Psychological Implications:
- Research (Kahneman, 2011) shows 3-loss threshold increases 
  revenge trading probability by 40%
- Current 2-loss threshold based on prop firm data showing 
  optimal balance

Edge Cases:
1. What if 3rd loss is scratched trade? Still counts?
2. What about multi-day sequences?
3. How does this interact with daily loss limits?

Recommendation:
Keep 2-loss threshold. Data supports current setting.

If you still want to change, test with:
- Simulated trading first
- A/B test with one account
- Monitor tilt risk scores daily
```

---

### `/rapid_build` - Fast Implementation Mode

**Use for:**
- Quick features
- Prototypes
- Non-critical updates
- When speed matters

**Effect:**
- Provides working code immediately
- Minimal explanation
- Assumes you're competent
- You can ask for explanation later

**Example:**
```
/rapid_build

Add "Export Selected" button that exports checked trades to CSV.
```

**Response Style:**
```
✅ Here's the code:

[Working implementation with minimal explanation]

Want me to explain anything?
```

---

### `/deep_think` - Multi-Angle Analysis Mode

**Use for:**
- Architecture decisions
- Big refactors
- "Should we build X or Y?"
- Tradeoff analysis

**Effect:**
- Explores multiple approaches
- Shows pros/cons for each
- Considers edge cases
- Reveals reasoning process
- Longer, more thorough responses

**Example:**
```
/deep_think

Should we add an "undo delete" feature for trades, 
or is the confirmation dialog enough?
```

**Response Style:**
```
🤔 Analyzing Multiple Approaches...

Option A: Keep Current (Confirmation Only)
Pros:
- Simpler codebase
- Forces intentional decisions
- Matches trading psychology (no take-backs)
Cons:
- Accidental deletes are permanent
- No recovery from misclicks

Option B: Add Undo (30-second window)
Pros:
- Safety net for mistakes
- Better UX for bulk operations
Cons:
- Adds complexity
- May encourage carelessness

Option C: Soft Delete (Archive for 30 days)
Pros:
- Full recovery capability
- Audit trail preserved
Cons:
- Database bloat
- Ambiguous "deleted" state

Psychology Angle:
Trading is about commitment. Undo teaches bad habits.

Technical Angle:
Soft delete is safest but adds complexity.

Recommendation:
Keep confirmation dialog, add soft delete for imports only.
Manual trades stay permanent (intentional friction).
```

---

### `/design_mode` - UX/Product Thinking Mode

**Use for:**
- UI/UX design
- User flows
- Product decisions
- Visual hierarchy
- Mobile responsiveness

**Effect:**
- Focuses on user psychology
- Proposes UI improvements
- References design patterns
- Considers accessibility
- Mobile-first thinking

**Example:**
```
/design_mode

The bulk delete button feels hidden. 
How should we make it more discoverable?
```

**Response Style:**
```
🎨 UX Analysis: Bulk Delete Discoverability

Current State:
- Button only appears after selection
- Users may not know feature exists

User Psychology:
- Feature discovery requires affordance
- Empty state should hint at possibility

Recommendations:

1. Empty State Hint
   "Select trades to delete, export, or analyze"
   
2. Tooltip on Checkbox Header
   "Select multiple trades for bulk actions"

3. Subtle Action Bar
   Always visible, disabled state shows:
   "Select trades to enable bulk actions"

4. Progressive Disclosure
   First selection shows toast:
   "💡 Tip: Select multiple trades for bulk operations"

5. Keyboard Shortcut
   Cmd+A to select all (show in footer)

My Pick: Combination of #1 + #3
Shows possibility without clutter.
```

---

## Common Workflows

### Workflow 1: Starting Your Day
```
/work
```
→ Shows context, tasks, asks what to work on
→ Pick a task and start working
→ No other commands needed unless you want to change mode

---

### Workflow 2: Deep Work Session
```
1. /work                    ← Morning: Load context
2. [Work 2 hours]
3. /save                    ← Before lunch: Save progress
4. [Work 2 hours]
5. /save                    ← Afternoon: Save progress
6. [Work 2 hours]
7. /daily-end              ← Evening: Wrap up day
```

---

### Workflow 3: Quick Questions (No Commands)
```
"Fix this bug in the delete handler"
→ Just ask, no command needed

"Why does circuit breaker trigger at 2 losses?"
→ Just ask, no command needed

"How should I structure this component?"
→ Just ask, no command needed
```

**The persona handles everything automatically.**

---

### Workflow 4: Critical Trading Work
```
/strict_trading

Review my changes to the tilt risk algorithm.
I changed the weight of "consecutive losses" from 0.4 to 0.5.
Are there edge cases I'm missing?
```
→ AI will be extra careful, validate assumptions, show risks

---

### Workflow 5: Fast Prototyping
```
/rapid_build

Add a "Duplicate Trade" button that copies a trade 
but resets the date to today.
```
→ AI gives working code immediately, minimal explanation

---

## FAQ

### Q: Do I need commands to get expert responses?
**A: No.** The expert persona is always active. Just ask your question normally.

### Q: When should I use commands then?
**A: Two situations:**
1. **Workflow commands** - When working with memory system (`/work`, `/save`, etc.)
2. **Mode commands** - When you want specific thinking style (`/strict_trading`, etc.)

### Q: What if I just want to chat normally?
**A: That's the default.** Just talk. The AI adapts to your question automatically.

### Q: Can I use multiple modes in one conversation?
**A: Yes.** You can switch modes anytime:
```
/rapid_build
Build feature X

[Later]

/strict_trading
Now review the trading logic carefully
```

### Q: Do I need to use mode commands every time?
**A: No.** Only when you want to emphasize a specific thinking style. Normal questions don't need them.

### Q: How do I know which expertise is active?
**A: It's automatic based on your question:**
- Ask about psychology → Psychology expert responds
- Ask about code → Engineering expert responds
- Ask about design → Design expert responds

### Q: What if I forget the commands?
**A: Easy fixes:**
```
"Show me the command reference"
```
Or read `.exocortex/QUICK_REFERENCE.md`

### Q: Can I add my own commands?
**A: Yes.** Add new command JSON specs in `.exocortex/commands/` and reference them in `AI_BOOTSTRAP.md`.

### Q: What's the difference between workflow and mode commands?
**A:**
- **Workflow commands** = Interact with memory/context system
- **Mode commands** = Change thinking style

### Q: Should I use commands more or less?
**A: Less is fine.** Most work doesn't need commands. Use them when you need specific behavior.

---

## Quick Access

**When in doubt:**
```
"Read .exocortex/QUICK_REFERENCE.md"
```

**Emergency reset:**
```
"Read .exocortex/AI_BOOTSTRAP.md"
```

**See full command details:**
```
"Read .exocortex/COMMAND_SYSTEM.md"
```

---

**Remember: The persona is always there. You're already working with a senior expert. Commands just give you more control when you need it.**
