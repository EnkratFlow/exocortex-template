# Cursor Rules for [PROJECT_NAME]

## Workflow Commands

All workflows are triggered by typing the command in chat. Each workflow has detailed steps below.

---

## `/work` - Work Entry Point

**Triggers:** `"work"`, `"read memory"`, or `"start session"`

**Purpose:** Load context, show what to work on, confirm direction, start work. Works anytime: morning, after break, context switch, mid-day.

**Event System:** Regenerates SESSION_CONTEXT from events before displaying.

**Safety:**
- Read-only context scan (no file modifications except regenerating SESSION_CONTEXT)
- Show what you should work on
- You decide what to do next

**Workflow:**

1. **Regenerate Context from Events:**
   - Run: `.exocortex/scripts/generate_context.sh`
   - This rebuilds SESSION_CONTEXT.md from event files (last 7 days)
   - Ensures you see the latest work across all editors/machines

2. **Load Current State (in order):**
   - `.exocortex/MEMORY.md` (entry point to project memory)
   - `.exocortex/PROJECT_MEMORY.md` (system purpose, philosophy, constraints)
   - `.exocortex/LESSONS.md` (if exists - project-specific lessons, scan for relevant anti-patterns)
   - `.exocortex/SESSION_CONTEXT.md` (focus on 🟢 RIGHT NOW section - what were you doing?)
   - `.exocortex/TODO.md` (what tasks are available? what's incomplete?)
   - `docs/control/INTERRUPTS.md` (any urgent/important interrupts?)

2. **Produce Brief:**
   Show user:
   - What you were last working on (from RIGHT NOW)
   - Current state of that work (done | paused | blocked)
   - Next uncompleted task in TODO (if different)
   - Any high-priority interrupts
   - Any relevant lessons for today's work

3. **Routing Decision:**
   Ask clearly: "What would you like to work on?"
   
   Options:
   - A) Continue what you were doing (from RIGHT NOW)
   - B) Start next task from TODO
   - C) Handle an interrupt first
   - D) Need to explore/clarify something first

4. **Confirm & Start:**
   Based on their choice:
   
   - **A) If CONTINUING previous work:**
     - Show the context again
     - Confirm: "Starting on [task]. Run 'save' before breaks."
   
   - **B) If STARTING new task:**
     - Show the task details from TODO
     - Show any relevant context
     - Confirm: "Ready to start [task]?"
   
   - **C) If HANDLING interrupt:**
     - Show the interrupt
     - Ask: "How do you want to handle this?"
   
   - **D) If EXPLORING:**
     - Ask: "What do you need to understand?"
     - Help gather info (read docs, analyze code, etc.)
     - Once clarity achieved, return to Step 3

5. **Work:**
   User works on chosen task.
   
   During work:
   - Before any break: run `save`
   - At end of day: run `daily-end`

---

## `/scrum` - Daily Standup

**Triggers:** `"scrum"`, `"standup"`, `"daily scrum"`, or `"dsu"`

**Purpose:** Daily scrum/standup to review yesterday, plan today, identify blockers. Follows classic scrum format: What did I do yesterday? What will I do today? Any blockers?

**Safety:**
- Read-only context scan (no file modifications)
- Show scrum status
- Optionally update status if needed
- Nothing written without approval

**Workflow:**

1. **What Did I Do Yesterday?**
   Read:
   - `.exocortex/SESSION_CONTEXT.md` (RECENT WORK section - last 7 days)
   - `.exocortex/TODO.md` (check for completed items in Done section)
   - Git log (commits since last scrum or last 24 hours)
   
   Show:
   - Completed tasks (from TODO Done section)
   - Work in progress (from SESSION_CONTEXT RIGHT NOW)
   - Any commits/changes detected
   - Summary: "Yesterday I completed [X] and worked on [Y]"

2. **What Will I Do Today?**
   Read:
   - `.exocortex/TODO.md` (Ready and In Progress sections)
   - `.exocortex/SESSION_CONTEXT.md` (RIGHT NOW section)
   
   Show:
   - Current task (if in In Progress)
   - Next task (if in Ready, show top priority)
   - All Ready tasks (prioritized list)
   - Summary: "Today I will work on [X] and plan to [Y]"

3. **Any Blockers?**
   Check:
   - `.exocortex/OPEN_DECISIONS.md` (pending decisions that block work)
   - `docs/control/INTERRUPTS.md` (urgent items)
   - `.exocortex/TODO.md` (tasks marked as blocked)
   - `.exocortex/SESSION_CONTEXT.md` (status: blocked)
   
   Show:
   - Decisions needed (from OPEN_DECISIONS.md)
   - Urgent interrupts (from INTERRUPTS.md)
   - Blocked tasks (from TODO or SESSION_CONTEXT)
   - Summary: "Blockers: [X] or None"

4. **Scrum Summary:**
   Display formatted scrum report:
   
   ```
   📊 Daily Scrum - [Date]
   
   ✅ Yesterday:
   - [Completed task 1]
   - [Completed task 2]
   - Worked on: [In progress task]
   
   🎯 Today:
   - [Current/Next task]
   - Plan: [What you'll accomplish]
   
   🚧 Blockers:
   - [Blocker 1] or None
   ```

5. **Update Status (Optional):**
   Ask: "Any status changes to record?"
   
   If yes:
   - Ask: "Which task status changed?"
   - Options:
     - Move Ready → In Progress (starting new task)
     - Move In Progress → Review (completed, needs review)
     - Move Review → Done (verified complete)
     - Mark as Blocked (add blocker note)
   
   Show proposed TODO.md updates
   Ask: "Ready to update TODO status?"
   
   If approved:
   - Update `.exocortex/TODO.md` (move items between sections)
   - Update `.exocortex/SESSION_CONTEXT.md` (RIGHT NOW section if starting new task)
   - Confirm: "✅ Status updated"

6. **Start Work:**
   Ask: "Ready to start work on [task]?"
   
   If yes:
   - Confirm: "Starting on [task]. Run 'save' before breaks, 'daily-end' at end of day."
   - Transition to work mode
   
   If no:
   - Ask: "What would you like to do instead?"
   - Options: Handle blocker, review something, explore, etc.

---

## `/interrupt` - Quick Capture

**Triggers:** `"interrupt"`

**Purpose:** Capture ideas, bugs, concerns, questions without stopping work. Save to INTERRUPTS.md and continue working.

**Safety:**
- Read-only capture (just write to INTERRUPTS.md)
- Minimal questions (under 1 minute)
- No analysis, no decisions, no execution

**Workflow:**

1. **Type:**
   Ask: "What type of interrupt?"
   
   Options:
   - A) Bug — Something is broken or not working right
   - B) New Idea — Feature or improvement idea
   - C) Wild Thought — Random idea, might explore later
   - D) Concern — Something feels wrong or risky
   - E) Question — Need an answer before proceeding

2. **Capture (type-specific):**
   
   **If BUG:**
   - Ask: "What's broken?"
   - User answers in 1-2 sentences
   - Ask: "How urgent?"
     - A) Blocking (fix today)
     - B) Important (fix soon)
     - C) Low priority (nice to fix)
   
   **If NEW IDEA:**
   - Ask: "What's the idea?"
   - User answers in 1-2 sentences
   - Ask: "Why would this be valuable?"
   - User explains briefly
   
   **If WILD THOUGHT:**
   - Ask: "What's the thought?"
   - User captures it
   - Ask: "Worth exploring?"
     - A) Yes, investigate later
     - B) No, just parking
   
   **If CONCERN:**
   - Ask: "What are you worried about?"
   - User describes the concern
   - Ask: "What risk does it represent?"
   - User explains briefly
   
   **If QUESTION:**
   - Ask: "What's the question?"
   - User asks it
   - Ask: "When do you need an answer?"
     - A) Before proceeding
     - B) Eventually

3. **Save:**
   Save to `docs/control/INTERRUPTS.md` with:
   - Date timestamp
   - Type
   - User's captured text

4. **Continue Work:**
   Confirm: "✅ Saved to INTERRUPTS.md"
   "Back to work. Run 'groom' when ready to review."

---

## `/groom` - Process Interrupts

**Triggers:** `"groom"`

**Purpose:** Review captured interrupts, decide what matters, move to BACKLOG or TODO.

**Safety:**
- Read INTERRUPTS.md
- Show each item and ask: what should we do?
- Propose changes before writing
- Nothing written without approval

**Workflow:**

1. **Load Interrupts:**
   Read `docs/control/INTERRUPTS.md`
   Show all items captured since last groom
   Group by type:
   - Bugs
   - Ideas
   - Wild Thoughts
   - Concerns
   - Questions

2. **Process Each Item:**
   For each interrupt, ask: "[Type] - [Title]: What should we do?"
   
   Options:
   - A) Add to BACKLOG for investigation
   - B) Add to TODO (urgent/clear enough to work on)
   - C) Delete (not relevant)
   - D) Keep in INTERRUPTS (decide later)
   
   User chooses for each item

3. **Propose Changes:**
   Show exactly what will be written:
   
   **BACKLOG.md additions:**
   - Item 1: [title and captured details]
   - Item 2: [title and captured details]
   
   **TODO.md additions:**
   - Item X: [as new task]
   
   **INTERRUPTS.md changes:**
   - Remove processed items
   - Keep deferred items
   
   Ask: "Ready to apply these changes?"

4. **Write:**
   If approved:
   1. Update BACKLOG.md (add new items)
   2. Update TODO.md (add urgent items)
   3. Update INTERRUPTS.md (remove processed)
   4. Confirm all writes successful
   
   Show summary:
   "✅ Grooming complete
   [X] items moved to BACKLOG
   [Y] items moved to TODO
   [Z] items deleted
   [W] items deferred
   
   Next: 'refine-backlog' to promote ready items"

---

## `/refine-backlog` - Refine Backlog

**Triggers:** `"refine-backlog"`

**Purpose:** Review BACKLOG items, promote ready ones to TODO, mark completed tasks.

**Safety:**
- Read BACKLOG.md and TODO.md
- Propose all changes before writing
- Nothing written without approval

**Workflow:**

1. **Load Backlogs:**
   Read:
   - `docs/control/BACKLOG.md`
   - `.exocortex/TODO.md`
   
   Show summary of each

2. **Refine Backlog Items:**
   For each BACKLOG item (one at a time):
   
   Ask: "Is [Item Title] ready to promote to TODO?"
   
   User answers:
   - A) Yes, promote to TODO
   - B) Not yet, still investigating
   - C) Defer (decide later)
   - D) Delete (not relevant)
   
   **If YES - PROMOTE:**
   - Ask: "What's the executable task title?"
   - Ask: "What's the scope (what needs to be done)?"
   - Save as new TODO item
   
   **If NOT YET:**
   - Ask: "What needs to happen before it's ready?"
   - Update BACKLOG item with notes

3. **Mark Completed:**
   Check TODO.md for [x] marked items
   
   For each completed item:
   Ask: "Should I remove [Item] from TODO?"
   
   If yes: remove it

4. **Propose Changes:**
   Show exactly what will be updated:
   
   **BACKLOG.md:**
   - Promoted items removed
   - Deferred items updated with notes
   - Remaining items shown
   
   **TODO.md:**
   - New promoted items added
   - Completed [x] items removed
   - Current list shown
   
   Ask: "Ready to apply these changes?"

5. **Write:**
   If approved:
   1. Update BACKLOG.md
   2. Update TODO.md
   3. Confirm writes successful
   
   Summary: "✅ Backlog refined"
   
   Next: `prioritize` to reorder TODO

---

## `/save` - Save Work State

**Triggers:** `"save"`

**Purpose:** Automated memory checkpoint. Captures what you've been working on since last save. Use for: breaks, interruptions, context switches, end of work session.

**Event System:** Creates append-only event files (no overwrites). Multiple editors can save simultaneously.

**Philosophy:** ZERO questions. Fully automated. Show complete proposed event, user reviews and approves.

**Workflow:**

1. **Auto-Detect Everything:**
   Silently gather:
   - Last 3-5 commits (git log)
   - Uncommitted changes (git status, git diff --stat)
   - Current branch
   - Timestamp (current UTC time)

   **Machine detection:**
   - Check `uname -a` for system info
   - Darwin + ARM64 = "macbook"
   - Darwin + x86_64 = "macbook" or "imac" (check hostname if possible)
   - Linux = "server" or "desktop" (check hostname)
   - If unclear, ask: "Which machine? (macbook / desktop / laptop / server)"

   **Editor detection:**
   - Check environment variables or process info
   - VS Code, Cursor, Claude Desktop, or other
   - If unclear, ask: "Which editor? (vscode / cursor / other)"

2. **Deep Analysis of Changes:**

   **CRITICAL:** Events must be COMPREHENSIVE enough to resume work weeks/months later. Shallow summaries are useless for long-term memory.

   **Step 1: Analyze git diff for implementation details**
   - Run `git diff --stat` for file-level changes
   - Run `git diff` (or sample key files) to understand WHAT was implemented
   - For new files: identify their purpose (component? utility? doc?)
   - For modified files: understand what changed (new function? schema field? UI element?)

   **Step 2: Group changes by area**
   Organize into categories:
   - **Database/Schema** - schema changes, migrations, new fields/tables
   - **Backend/API** - new endpoints, logic functions, services
   - **Frontend/UI** - new components, UI changes, styling
   - **Documentation** - READMEs, architecture docs, guides
   - **Configuration** - build configs, environment, scripts
   - **Tests** - new tests, test fixtures

   **Step 3: Extract implementation details**
   For each changed file, capture:
   - **What was added**: New functions, components, fields, features
   - **What was modified**: Changed behavior, refactors, bug fixes
   - **Why it changed**: Purpose or problem it solves
   - **Status**: Complete, in-progress, or pending

   **Step 4: Identify incomplete work**
   Look for indicators:
   - Uncommitted files (work in progress)
   - TODO comments in code
   - Schema changes without migrations
   - Components without tests
   - Features documented but not implemented

   **Step 5: Capture architectural decisions**
   If conversation included key decisions, capture:
   - Technology choices (why X over Y)
   - Design patterns chosen
   - Trade-offs made
   - Constraints discovered

   **Step 6: Generate comprehensive focus**
   Structure the focus section with:

   ```markdown
   # Work Focus

   [High-level summary: 1-2 sentences describing the main work]

   ## Implementation Details

   ### Database/Schema
   - Added `emotionalGrade` field (A/B/C/F) to JournalEntry
   - Added `consecutiveLosses` tracking to DailyReportCard
   - Schema updated but migration pending

   ### Backend/API
   - Created `emotionalGrading.ts` with `calculateEmotionalGrade()` function
   - Integrated grading logic into POST /api/journal/entry/:id/post-trade
   - Added consecutive loss detection in analyzePostTradeCoaching()

   ### Frontend/UI
   - Created CircuitBreakerModal component with 15-min countdown timer
   - Updated ConsoleCard to display dual grades (Technical + Discipline)
   - Modified PostTradeCapture to show emotional grade after save
   - Added Risk Management section to Settings page

   ### Documentation
   - Created PSYCHOLOGICAL_ACCOUNTABILITY.md (architecture)
   - Created EMOTIONAL_GRADING_GUIDE.md (user guide)
   - Created PSYCHOLOGICAL_ACCOUNTABILITY_UX.md (Figma specs)
   - Created prototypes and component specs

   ## Status

   **Complete:**
   - ✅ Emotional grading calculation logic
   - ✅ Circuit breaker modal UI
   - ✅ Dual grade display in ConsoleCard
   - ✅ Complete documentation suite

   **In Progress:**
   - 🔄 Schema migration (needs: npx prisma migrate dev)
   - 🔄 Frontend integration testing

   **Pending:**
   - ⏳ Circuit breaker testing (need 2+ consecutive losing trades)
   - ⏳ Emotional grade display in Trade History table
   - ⏳ Daily loss limit feature (documented but not implemented)

   ## Key Decisions

   - Grade criteria: A (excellent), B (good), C (fair), F (poor) based on emotions + ratings + mistakes
   - Circuit breaker triggers at 2 consecutive losses (configurable)
   - Mandatory 15-minute pause (not optional, prevents revenge trading)
   - Schema fields nullable for backward compatibility

   ## Next Steps

   1. Run prisma migration to update database schema
   2. Test emotional grading in full trade flow (pre-trade → post-trade)
   3. Test circuit breaker with consecutive losing trades
   4. Verify dual grades display correctly in Trade History
   5. Implement daily loss limit feature (if needed)
   ```

   **Quality bar:** If you can't resume work from this event in 3 months, it's not detailed enough.

3. **Show Complete Proposed Event:**
   Display FULL event content that will be saved:

   ```
   📝 Proposed Event: .exocortex/events/2026-01-25_15-30-45_macbook-vscode.md

   ═══════════════════════════════════════════════════════════════

   <!-- Event Metadata -->
   timestamp: 2026-01-25T15:30:45Z
   machine: macbook
   editor: vscode
   project: [PROJECT_NAME]
   branch: feat/trade-data-import

   ---

   # Work Focus

   [High-level summary of main work]

   ## Implementation Details

   ### Database/Schema
   - [Specific schema changes]
   - [New fields/tables added]
   - [Migration status]

   ### Backend/API
   - [New endpoints or functions]
   - [Logic changes]
   - [Services updated]

   ### Frontend/UI
   - [New components created]
   - [UI modifications]
   - [Styling changes]

   ### Documentation
   - [Docs created or updated]
   - [Architecture decisions documented]

   ### Configuration
   - [Config changes]
   - [Build updates]

   ## Status

   **Complete:**
   - ✅ [Feature/task completed]
   - ✅ [Feature/task completed]

   **In Progress:**
   - 🔄 [Task currently working on]
   - 🔄 [Task partially done]

   **Pending:**
   - ⏳ [Task not started but planned]
   - ⏳ [Blocker or dependency]

   ## Key Decisions

   - [Architectural decision made]
   - [Technology choice and rationale]
   - [Trade-off accepted]

   ## Next Steps

   1. [Immediate next action]
   2. [Second priority]
   3. [Testing needed]

   ## Git State

   **Last Commits:**
   - [hash] - [commit message]
   - [hash] - [commit message]
   - [hash] - [commit message]

   **Branch:** [current branch]

   **Uncommitted Changes:**
   - [file path] (modified) - [why]
   - [file path] (new file) - [purpose]
   - [file path] (deleted) - [reason]

   ═══════════════════════════════════════════════════════════════
   ```

   **Format Notes:**
   - Use ✅ for complete items
   - Use 🔄 for in-progress items
   - Use ⏳ for pending items
   - Include WHY for uncommitted changes, not just file names

4. **Review & Approve:**
   Ask: "Ready to save this event? (or type 'edit' to modify focus description)"

   **If user says "yes" or "save" or "ok":**
   - Write event file with proper timestamp (MUST be actual ISO 8601 timestamp, NOT shell command)
   - Run `.exocortex/scripts/generate_context.sh`
   - Confirm: "✅ Event saved. SESSION_CONTEXT regenerated."

   **If user says "edit":**
   - Ask: "What should the focus description be?"
   - Update focus in proposed event
   - Show updated event
   - Ask for approval again

   **If user says "no" or "cancel":**
   - Don't write anything
   - Confirm: "Event not saved."

5. **Write Event File:**
   **CRITICAL:** When writing timestamp field, you MUST calculate the actual timestamp value first.

   ❌ **WRONG** (this will break date parsing):
   ```
   timestamp: $(date -u +%Y-%m-%dT%H:%M:%SZ)
   ```

   ✅ **CORRECT** (calculate first, then write):
   ```
   timestamp: 2026-01-25T15:30:45Z
   ```

   **How to do this:**
   - Get current UTC time in ISO 8601 format
   - Write the actual timestamp value to the file
   - Do NOT write shell commands or placeholders

**Event Format Template (Comprehensive Example):**
```markdown
<!-- Event Metadata -->
timestamp: 2026-01-25T15:30:45Z
machine: macbook
editor: cursor
project: [PROJECT_NAME]
branch: feat/psychological-accountability

---

# Work Focus

Implemented psychological accountability system to track trader discipline alongside technical setup quality. System includes emotional grading (A/B/C/F), circuit breaker for consecutive losses, and risk management settings.

## Implementation Details

### Database/Schema
- Added `emotionalGrade` field (A/B/C/F) to JournalEntry schema
- Added `emotionalZone` field (SUCCESS/WARNING/DANGER) to JournalEntry
- Added `consecutiveLosses` counter to DailyReportCard
- Added `circuitBreakerHits` counter to DailyReportCard (tracks daily trigger count)
- Added `dailyLossLimit`, `lossLimitWarning`, `lossLimitReached` fields to DailyReportCard
- Schema changes committed but migration NOT run yet (pending)

### Backend/API
- Created `server/src/emotionalGrading.ts` with `calculateEmotionalGrade()` function
- Grade logic: A (excellent), B (good), C (fair), F (poor) based on emotions + state rating + trade quality + mistakes
- Integrated grading into POST /api/journal/entry/:id/post-trade endpoint
- Added consecutive loss detection in `analyzePostTradeCoaching()` function
- Circuit breaker triggers at 2+ consecutive losses, sets resetRequired=true, resetDuration=15 minutes

### Frontend/UI
- Created `client/src/components/CircuitBreakerModal.tsx` component
  - Modal with countdown timer (15 minutes)
  - Shows last 2 trades for review
  - Optional reflection prompt textarea
  - Button disabled until timer completes
- Updated `client/src/components/ConsoleCard.tsx`
  - Dual grade badge display (Technical + Discipline)
  - Color-coded: A (emerald), B (cyan), C (amber), F (rose)
- Updated `client/src/components/PostTradeCapture.tsx`
  - Shows emotional grade after saving post-trade data
  - Displays grade breakdown (emotions, ratings, mistakes)
  - Triggers CircuitBreakerModal if 2+ consecutive losses
- Updated `client/src/components/Settings.tsx`
  - Added Risk Management section
  - Daily loss limit input ($500 default)
  - Circuit breaker configuration (consecutive losses threshold, pause duration)
  - Enable/disable toggles
- Replaced `client/src/components/TradeHistory.tsx` with `Trades.tsx`
  - Added "Discipline" column showing emotional grade
  - Added "State" column showing state rating (★★★★☆ format)

### Documentation
- Created `docs/architecture/PSYCHOLOGICAL_ACCOUNTABILITY.md` - full system architecture, grade criteria, circuit breaker logic, API changes
- Created `docs/guides/EMOTIONAL_GRADING_GUIDE.md` - user guide explaining how grading works and how to improve
- Created `docs/ux-ui/PSYCHOLOGICAL_ACCOUNTABILITY_UX.md` - complete UX spec with wireframes, Figma component specs, user flows
- Created `docs/PSYCHOLOGICAL_ACCOUNTABILITY_README.md` - overview and quick links
- Created `docs/requirements/Why_Disciplined_Traders_Fail_Prop_Firms.md` - requirements analysis from Drysdale paper

### Configuration
- Updated `.gitignore` - tracking event files during Phase 1 (git-based sync)
- Updated `client/vite.config.ts` - (minor config adjustments)

## Status

**Complete:**
- ✅ Emotional grading calculation logic (emotionalGrading.ts)
- ✅ Circuit breaker modal UI with countdown timer
- ✅ Dual grade display in ConsoleCard (Technical + Discipline badges)
- ✅ Risk management settings UI
- ✅ Complete documentation suite (architecture, user guide, UX specs)
- ✅ Schema fields defined and committed

**In Progress:**
- 🔄 Database migration (schema updated but not migrated: need `npx prisma migrate dev`)
- 🔄 Frontend integration testing (need to test full trade flow)

**Pending:**
- ⏳ Circuit breaker testing - need to create 2 consecutive losing trades to trigger modal
- ⏳ Emotional grade display verification in Trade History table
- ⏳ Daily loss limit feature implementation (documented in plan but not coded yet)
- ⏳ Loss limit warning banner (75% threshold)

## Key Decisions

- **Grade criteria:** A requires CALM/FOCUSED emotions, 4-5 ratings, no mistakes. F if TILTED/FRUSTRATED or 1-2 ratings or includes REVENGE_TRADE/FOMO/IGNORED_STOP
- **Circuit breaker threshold:** 2 consecutive losses (configurable in Settings)
- **Mandatory pause:** 15 minutes (not optional - prevents revenge trading spiral)
- **Schema nullable fields:** All new psychological fields are optional for backward compatibility with existing trades
- **Dual grade display:** Technical grade (from AI analysis) + Discipline grade (from emotional execution) shown side-by-side
- **Database strategy:** Phase 1 uses git for event sync (1-2 months), Phase 2 switches to RAG API

## Next Steps

1. Run database migration: `cd server && npx prisma migrate dev --name "add_psychological_accountability"`
2. Restart servers to pick up schema changes
3. Test emotional grading flow: create trade → pre-trade emotions → post-trade assessment → verify grade appears
4. Test circuit breaker: create 2 consecutive losing trades → verify modal appears with countdown
5. Test dual grades in Trade History: verify both Technical and Discipline columns show correctly
6. (Optional) Implement daily loss limit feature if needed

## Git State

**Last Commits:**
- 9106645 - Improve machine detection in /save workflow
- 89b6cfc - Improve /save workflow: fully automated, zero questions
- 44c5e23 - Implement Option 4: Hybrid .cursorrules + AI_INSTRUCTIONS.md system
- 30b067d - feat: add Claude command and skill definitions

**Branch:** feat/psychological-accountability

**Uncommitted Changes:**
- server/prisma/schema.prisma (modified) - added 6 psychological accountability fields
- server/src/emotionalGrading.ts (new) - grade calculation logic
- server/src/index.ts (modified) - integrated grading into post-trade endpoint
- client/src/components/CircuitBreakerModal.tsx (new) - countdown modal
- client/src/components/ConsoleCard.tsx (modified) - dual grade display
- client/src/components/PostTradeCapture.tsx (modified) - emotional grade shown after save
- client/src/components/Settings.tsx (modified) - risk management section
- client/src/components/Trades.tsx (new) - replaces TradeHistory.tsx with new columns
- client/src/components/TradeHistory.tsx (deleted) - replaced by Trades.tsx
- docs/architecture/PSYCHOLOGICAL_ACCOUNTABILITY.md (new)
- docs/guides/EMOTIONAL_GRADING_GUIDE.md (new)
- docs/ux-ui/PSYCHOLOGICAL_ACCOUNTABILITY_UX.md (new)
- docs/PSYCHOLOGICAL_ACCOUNTABILITY_README.md (new)
- docs/requirements/Why_Disciplined_Traders_Fail_Prop_Firms.md (new)
- .exocortex/events/ (new directory) - event system implementation
- .exocortex/scripts/generate_context.sh (new)
- .gitignore (modified) - track events during Phase 1
```

**IMPORTANT:** Timestamp MUST be an actual ISO 8601 datetime value (e.g., `2026-01-25T15:30:45Z`), NOT a shell command or placeholder.

**Quality Standard:** If you can't resume this work in 3 months from this event alone, it's not detailed enough.

---

## `/history` - Search Older Work

**Triggers:** `"history"`, `"show history"`, `"search events"`

**Purpose:** Search work events older than 7 days (long-term memory) or search by keyword across all events.

**Workflow:**

1. **Ask Search Criteria:**
   - "What do you want to search for? (keyword/phrase or date range)"
   - Examples:
     - "authentication"
     - "circuit breaker"
     - "last month"
     - "December 2025"
     - "all"

2. **Search Events:**
   Based on user input:

   **For keyword/phrase:**
   ```bash
   grep -r "keyword" .exocortex/events/ | grep -v "archive" | sort -r
   ```

   **For date range:**
   ```bash
   find .exocortex/events/ -name "*YYYY-MM*" | sort -r
   ```

   **For "all":**
   ```bash
   ls -lt .exocortex/events/ | head -50
   ```

3. **Display Results:**
   Show matching events with:
   - Timestamp
   - Machine + Editor
   - Work focus (first line of content)
   - File path (so user can read full event)

4. **Offer Actions:**
   - "Read full event?" → Display entire event file
   - "Search again?" → Return to step 1
   - "Back to work?" → Run `/work` command

**Phase 2 Note:** When RAG API integration is complete, this command will query semantically:
- Natural language: "What did I work on related to authentication?"
- Cross-project: "Show all work on RAG API across projects"
- Time-based: "What was I doing last Tuesday?"

---

## `/daily-end` - End of Day

**Triggers:** `"end session"`, `"daily-end"`, or `"end session confirm"`

**Purpose:** Complete end-of-day workflow review. Close the current work session by detecting what was done, validating it, and updating memory files.

**Safety:**
- Detect work from git history (non-destructive)
- Show proposed changes BEFORE writing
- Nothing is written unless you explicitly approve
- Multi-repo awareness (updates both repo-level and project-level memory)

**Workflow:**

1. **Detect Work:**
   Read current git state and show:
   - Git log since last SESSION_CONTEXT update (commits, changed files)
   - Current branch
   - Any uncommitted changes
   
   Ask: "Here's what I detected you worked on. Does this look right?"
   [Show detected work]
   - Can you add anything else?
   - Should I remove anything?

2. **Understand Context:**
   Ask (one at a time):
   - A. What is the current state of this work? (done | paused | blocked)
   - B. Did anything important change in direction, scope, or understanding?
   - C. Are you mentally done with this work for now?

3. **Handle Interrupts:**
   Read `docs/control/INTERRUPTS.md` (READ-ONLY)
   Group any new interrupts by type:
   - idea, bug, concern, refactor, feels wrong / not now
   
   PROPOSE (do not apply):
   - Promote to TODO
   - Update SESSION_CONTEXT
   - Leave parked

4. **Capture Lessons:**
   Ask: "Did you learn anything today worth capturing for future sessions?"
   - Anti-patterns discovered
   - Working patterns confirmed
   - Gotchas to avoid
   
   If yes:
   - Add to repo-level `.exocortex/LESSONS.md` (project-specific)
   - Add to EnkratFlow-Project/docs/WORKFLOWS/LESSONS_LEARNED.md (global, if broadly applicable)
   - Format: **LESSON N: [Title] (Date)** with Context, Pattern, Fix
   
   If no:
   - Move on

5. **Propose Memory Updates:**
   Show EXACTLY what will be written to memory files:
   
   **FOR REPO-LEVEL .exocortex/SESSION_CONTEXT.md:**
   - Add today's work to 📅 RECENT WORK section
   - Update 🟢 RIGHT NOW with current state
   - Update 🚀 NEXT UP based on feedback
   
   **FOR PROJECT-LEVEL EnkratFlow-Project/.exocortex/SESSION_CONTEXT.md:**
   - Add today's work to 📅 RECENT WORK (cross-repo summary)
   - Update 🔗 CROSS-REPO STATUS if multi-repo work
   - Preserve all history below
   
   **FOR .exocortex/TODO.md (if applicable):**
   - Mark completed tasks as [x]
   - Add any new items from interrupts
   
   **FOR .exocortex/LESSONS.md (if lesson captured):**
   - Append new lesson with date and context
   
   **FOR .exocortex/PROJECT_MEMORY.md:**
   - Add new constraints discovered (if any)
   
   **FOR .exocortex/OPEN_DECISIONS.md (if exists):**
   - Add new decisions needed OR remove resolved decisions
   
   **Focus on Structural Changes Only:**
   - ✅ Completed TODO items
   - ✅ New constraints discovered
   - ✅ Execution slice changes
   - ✅ Resolved decisions
   - ❌ Normal code changes
   - ❌ Bug fixes
   - ❌ Test additions
   - ❌ Routine refactoring
   
   Ask: "Ready to approve these memory updates?"

6. **Write Updates:**
   If approved:
   1. Update repo-level `.exocortex/SESSION_CONTEXT.md`
   2. Update repo-level `.exocortex/TODO.md`
   3. Update repo-level `.exocortex/LESSONS.md` (if lesson captured)
   4. Update repo-level `.exocortex/PROJECT_MEMORY.md` (if constraints added)
   5. Update project-level `.exocortex/SESSION_CONTEXT.md`
   6. Update project-level LESSONS_LEARNED.md (if global lesson)
   7. Update `.exocortex/OPEN_DECISIONS.md` (if applicable)
   8. Confirm all writes successful
   9. Summarize what was captured

7. **Close:**
   Ask: "Ready to close the session?"
   If yes:
   - Acknowledge closure and what was captured
   - Stop completely
   - Next session: start with `work`

---

## `/prioritize` - Prioritize TODO

**Triggers:** `"prioritize"`

**Purpose:** Reorder TODO items by strategic importance.

**Safety:**
- Read TODO.md
- Ask strategic questions
- Show proposed new order
- Nothing written without approval

**Workflow:**

1. **Load TODO:**
   Read `.exocortex/TODO.md`
   Show current TODO order:
   
   Current Priority Order:
   1. [Item 1]
   2. [Item 2]
   3. [Item 3]
   ...

2. **Ask Strategic Questions:**
   
   Question 1: "What's blocking other work?"
   Show items and ask: which ones block progress?
   User identifies blockers
   
   Question 2: "What has the highest business/product value?"
   User ranks by value
   
   Question 3: "What's most urgent (time-sensitive)?"
   User identifies time-sensitive items
   
   Question 4: "Are there dependencies?"
   Ask: "Does anything need to be done before something else?"
   User identifies prerequisites
   
   Question 5: "What should come first given all factors?"
   User decides final priority order

3. **Propose New Order:**
   Based on user's answers, show proposed new order:
   
   Proposed Priority Order:
   1. [Item X] - reason: blocks other work
   2. [Item Y] - reason: highest value
   3. [Item Z] - reason: prerequisite for Y
   ...
   
   Ask: "Does this order feel right?"
   
   If no: "What should change?"
   User adjusts, repeat

4. **Write:**
   If approved:
   1. Reorder TODO.md with new priority
   2. Confirm write successful
   
   Summary: "✅ TODO reordered"
   
   Next: `work` to see prioritized list

---

## `/weekly-review` - Weekly Review

**Triggers:** `"weekly-review"`

**Purpose:** Weekly planning and review.

**Workflow:**

1. **Summarize the Week:**
   - What did I actually work on?
   - What shipped or materially moved forward?
   - What stalled or felt heavy?

2. **Review INTERRUPTS.md:**
   Review `docs/control/INTERRUPTS.md` for the week and group by type:
   - idea
   - bug
   - concern
   - refactor
   - feels wrong / not now

3. **Ask:**
   - A. Do any of these now deserve focus next week?
   - B. Anything that should explicitly stay parked?
   - C. Anything that no longer matters and can be ignored?

4. **Propose Updates (do not write yet):**
   - `.exocortex/TODO.md` (next-week focus only)
   - `.exocortex/SESSION_CONTEXT.md` (if direction changed)

5. **Rules:**
   - No rewriting history
   - No retroactive perfection
   - Promote only what earns attention

6. **Approve:**
   End by asking: "Approve these changes for next week?"
   
   If approved, write updates.

---

## `/monthly-review` - Monthly Review

**Triggers:** `"monthly-review"`

**Purpose:** Monthly planning and review.

**Workflow:**

1. **High-level Reflection:**
   - What did I actually build or learn this month?
   - What felt aligned with the vision?
   - What felt heavy, noisy, or wasteful?

2. **Review Trends:**
   - Repeated interrupt themes
   - Repeated blockers or friction
   - Energy vs output mismatch

3. **Ask:**
   - A. What should I stop doing next month?
   - B. What deserves more focus?
   - C. Is the current direction still correct?

4. **Propose Updates (do not write yet):**
   - `.exocortex/PROJECT_MEMORY.md` (only if direction changed)
   - `.exocortex/SESSION_CONTEXT.md`
   - High-level TODO priorities

5. **Rules:**
   - This is about direction, not productivity
   - No task-level micromanagement
   - Fewer priorities is better

6. **Approve:**
   End by asking: "Approve these directional updates?"
   
   If approved, write updates.

---

## `/system-scan` - System Health Check

**Triggers:** `"system-scan"`

**Purpose:** Read repository end-to-end and produce system report.

**Workflow:**

1. **Read Repository:**
   You must read:
   - Application code
   - Architecture and design documents
   - Requirements and specifications
   - QA and testing documentation
   - Project memory and control files

2. **Produce Report:**
   Single markdown report that answers:
   1. What this system is and what problem it solves
   2. What is implemented and considered complete
   3. What is currently in progress
   4. What is explicitly planned next (based only on existing docs and memory)
   5. Where that next work belongs (which repo / folder)
   6. Any documented risks, gaps, or open decisions

3. **Constraints:**
   - Do not modify files
   - Do not update memory or TODO
   - Do not invent work or roadmap items
   - Do not speculate beyond documented evidence

4. **Output:**
   - One markdown document
   - Written for a senior engineer new to the system
   - Clear, factual, and actionable

---

## `/ai-export` - Export System Understanding

**Triggers:** `"ai-export"` or `"ai system export"`

**Purpose:** Read this repository and produce a portable system understanding document for use by another AI.

**Workflow:**

1. **Scope:**
   Read:
   - Application code
   - Architecture documentation
   - Requirements and specifications
   - QA and testing documentation
   - Project memory (.exocortex/MEMORY.md and referenced files)

2. **Tasks:**
   1. Explain what the system is and what problem it solves
   2. Describe the high-level architecture and major components
   3. Identify core responsibilities and boundaries
   4. Summarize how data flows through the system
   5. Describe QA strategy and validation approach (automated + human)
   6. Note explicit constraints, invariants, and governance rules from memory
   7. Call out known risks, gaps, or intentional omissions if documented

3. **Rules:**
   - Do not change any files
   - Do not update memory or TODO
   - Do not propose refactors
   - Do not speculate beyond documented evidence
   - If confidence is low, say so explicitly

4. **Output:**
   - Produce a single markdown document
   - Use clear section headings
   - Write for an external AI unfamiliar with the project
   - Keep it factual and concise
   
   This output will be copied into another AI for analysis.

---

## `/init-exocortex` - Initialize Exocortex

**Triggers:** `"init-exocortex"` or `"init exocortex"`

**Purpose:** Initialize exocortex structure for new project. This will set up a complete project memory system.

**Workflow:**

1. **Create Folder Structure:**
   - Create `.exocortex/` directory at project root
   - Create `docs/control/` directory

2. **Create Memory Files:**
   
   **Create `.exocortex/MEMORY.md` (Entry Point - REQUIRED):**
   ```
   # Project Memory – [Your Project Name]
   
   This folder contains the canonical memory for this project.
   
   **Governance:** [Your Project Name] does not define its own QA or Architecture governance. All such rules are inherited from [parent-project]:
   - QA governance: `[parent-project]/qa/QA_MEMORY.md`
   - Architecture governance: `[parent-project]/docs/architecture/ARCHITECTURE_MEMORY.md`
   - Integration contracts: `[parent-project]/integrations/brain.md` (system-level)
   
   Local memory files below are project-specific only.
   
   Before making any changes, read these files in order:
   
   1. PROJECT_MEMORY.md  
      System purpose, philosophy, and non-obvious constraints.
   
   2. SESSION_CONTEXT.md  
      Current focus, open questions, and frozen areas.
   
   3. ESSENTIAL_FILES.md  
      Where core truth lives vs reference vs tests.
   
   4. LESSONS.md  
      Project-specific lessons learned and anti-patterns to avoid.
   
   5. OPEN_DECISIONS.md (if exists)  
      Unresolved decisions affecting architecture, logic, QA strategy, or product direction.
   
   For cross-project lessons, see:  
   `[parent-project]/docs/WORKFLOWS/LESSONS_LEARNED.md`
   
   If work involves cross-system behavior or synchronization, read the system-level integration contract: `[parent-project]/integrations/brain.md`.
   
   Rule:
   If you have not read these, do not make changes.
   
   If work discovers new tasks, risks, or follow-ups, the agent MUST update `.exocortex/TODO.md`.
   
   Note:
   If an agent is instructed to "read memory", "load memory", "use project memory", or similar,
   this file is the intended entry point.
   
   Global system context and canonical integrations live in [parent-project].
   
   ---
   ```
   
   **Create `.exocortex/PROJECT_MEMORY.md` (System Constraints - REQUIRED):**
   ```
   # Project Memory
   
   **Last Updated:** [Today's date]  
   **Purpose:** Durable orientation for future contributors (human or AI)
   
   ---
   
   ## What This System Is
   
   [Describe what the system is and what problem it solves]
   
   ---
   
   ## What This System Is Not
   
   [Describe what it is NOT to prevent scope creep]
   
   ---
   
   ## Core Design Philosophy
   
   1. **[Principle 1]**
      [Explanation]
   
   2. **[Principle 2]**
      [Explanation]
   
   ---
   
   ## Non-Obvious Constraints
   
   | Constraint | Reason |
   |------------|--------|
   | [Constraint 1] | [Why it exists] |
   | [Constraint 2] | [Why it exists] |
   
   ---
   
   ## Intentional Trade-offs
   
   | Trade-off | Why |
   |-----------|-----|
   | [Trade-off 1] | [Rationale] |
   
   ---
   
   ## What Not to Break
   
   - [Invariant 1]
   - [Invariant 2]
   
   ---
   ```
   
   **Create `.exocortex/SESSION_CONTEXT.md`:**
   ```
   # SESSION_CONTEXT – [Your Project Name]
   
   **Last Updated:** [Today's date]
   
   ## 🟢 RIGHT NOW
   
   **Active Work:** [What you're working on]
   **Status:** 🟢 Active
   
   ## 📅 RECENT WORK (Last 7 Days)
   
   [Document what you've accomplished]
   
   ## 🚀 NEXT UP
   
   - [What's next]
   - [What comes after]
   
   ---
   ```
   
   **Create `.exocortex/TODO.md` (with board structure):**
   ```
   # TODO – [Your Project Name]
   
   **Last Updated:** [Today's date]
   
   **Purpose:** Your daily task board. This is where you track what needs to be done, what you're working on, and what's complete.
   
   **How it works:**
   - Tasks move through columns as their status changes
   - Only ONE item in In Progress at a time (focus!)
   - Work from Ready column when starting new tasks
   - Move completed work to Review, then Done
   
   **Rules:**
   - Only ONE item in In Progress at a time
   - Discovery items get promoted to Ready when executable
   - Ready items are prioritized by strategic importance
   - Review items get moved to Done after verification
   - Done items can be removed at end of week/month
   
   ---
   
   ## 🟦 Discovery
   (Items being explored, investigated, or clarified. Not executable yet.)
   
   *Items here come from BACKLOG.md when they need investigation before becoming executable tasks.*
   
   - *(empty)*
   
   ---
   
   ## 🟨 Ready
   (Well-defined work ready to execute. Prioritized by strategic importance.)
   
   - [ ] Task 1 — [What needs to be done]
   - [ ] Task 2 — [What needs to be done]
   
   ---
   
   ## 🟧 In Progress
   (Exactly ONE item at a time. Current focus.)
   
   - *(empty)*
   
   ---
   
   ## 🟩 Review
   (Work completed, pending verification, decision, or cleanup.)
   
   - *(empty)*
   
   ---
   
   ## ✅ Done
   (Completed work. Moved here at end of day. Can be removed at end of week/month.)
   
   - *(empty)*
   
   ---
   ```
   
   **Create `.exocortex/LESSONS.md` (can start empty):**
   ```
   # Project Lessons – [Your Project Name]
   
   **Last Updated:** [Today's date]  
   **Purpose:** Prevent repeating mistakes in this codebase
   
   ---
   
   ## How to Use This File
   
   1. **Before major changes:** Scan relevant lessons
   2. **After painful debugging:** Add new lesson
   3. **When stuck:** Check if similar problem happened before
   
   For cross-project lessons, see:  
   `[parent-project]/docs/WORKFLOWS/LESSONS_LEARNED.md`
   
   ---
   
   ## [Month Year] Lessons
   
   *(Add lessons here as you learn them)*
   
   ---
   ```
   
   **Create `.exocortex/ESSENTIAL_FILES.md` (can start empty):**
   ```
   # Essential Files – [Your Project Name]
   
   **Purpose:** Map of where core truth lives vs reference vs tests
   
   ---
   
   ## Core Truth (Source of Truth)
   
   | File | Purpose | Don't Change Without |
   |------|---------|---------------------|
   | [file] | [purpose] | [approval needed] |
   
   ---
   
   ## Reference (Documentation)
   
   | File | Purpose |
   |------|---------|
   | [file] | [purpose] |
   
   ---
   
   ## Tests (Validation)
   
   | File | Purpose |
   |------|---------|
   | [file] | [purpose] |
   
   ---
   ```
   
   **Create `.exocortex/OPEN_DECISIONS.md` (can start empty):**
   ```
   # Open Decisions – [Your Project Name]
   
   **Last Updated:** [Today's date]  
   **Purpose:** Track unresolved decisions affecting architecture, logic, QA strategy, or product direction.
   
   ---
   
   ## Architecture & Logic Decisions
   
   *(Add decisions here as they arise)*
   
   ---
   
   ## Maintenance
   
   - **Remove resolved decisions:** When a decision is made, remove it from this file
   - **Do not keep resolved decisions:** This file tracks only unresolved decisions
   - **Document resolution elsewhere:** Resolved decisions may be documented in `.exocortex/PROJECT_MEMORY.md` if they establish new constraints
   
   ---
   ```
   
   **Create `.exocortex/README.md` (Human Guide):**
   ```
   # Exocortex Memory System
   
   **Last Updated:** [Today's date]  
   **Purpose:** Human-readable guide to the project memory system
   
   ---
   
   ## What is the Exocortex?
   
   The **Exocortex** is your project's memory system. It helps you (and AI assistants) remember what you're working on, what needs to be done, and what you've learned. Think of it as an external brain that never forgets.
   
   **Why it matters:** Without it, you waste time re-explaining context, repeating mistakes, and losing track of decisions. With it, you can pick up exactly where you left off, even after days or weeks away.
   
   ---
   
   ## How It Works
   
   ### The Core Concept
   
   Instead of relying on memory or scattered notes, the Exocortex stores:
   - **What you're working on** (SESSION_CONTEXT.md)
   - **What needs to be done** (TODO.md)
   - **What the system is** (PROJECT_MEMORY.md)
   - **What you've learned** (LESSONS.md)
   - **What decisions are pending** (OPEN_DECISIONS.md)
   - **Where things live** (ESSENTIAL_FILES.md)
   
   ### The Flow
   
   ```
   Daily Start → Read Memory → Work → Capture Interrupts → End of Day → Update Memory
   ```
   
   1. **Morning:** Read SESSION_CONTEXT.md and TODO.md to know what to work on
   2. **During Work:** Focus on TODO items only, capture interruptions quickly
   3. **End of Day:** Review what changed, update memory files if needed
   
   ---
   
   ## File Structure
   
   ### `.exocortex/` Directory
   
   All memory files live in `.exocortex/` at the project root:
   
   ```
   .exocortex/
   ├── README.md              ← You are here (this file)
   ├── MEMORY.md              ← Entry point for AI (read this first)
   ├── PROJECT_MEMORY.md      ← System constraints and invariants
   ├── SESSION_CONTEXT.md     ← Current work state
   ├── TODO.md                ← Executable tasks
   ├── LESSONS.md             ← Project-specific lessons learned
   ├── ESSENTIAL_FILES.md     ← Where core truth lives
   ├── OPEN_DECISIONS.md      ← Unresolved decisions
   └── TEMPLATE_STRUCTURE.md  ← Portable template for new projects
   ```
   
   ---
   
   ## Daily Workflow
   
   ### Morning (5 minutes)
   1. Run `/scrum` or `/dsu` for daily standup (or `/work` for quick start)
      - Review: Yesterday's work, Today's plan, Blockers
      - Update task status (Ready → In Progress)
   2. Start working on the In Progress task
   
   ### During Work
   - Work only from TODO.md
   - Use `/interrupt` to capture ideas/bugs (don't act on them)
   - Use `/save` before breaks to checkpoint state
   
   ### End of Day (5-10 minutes)
   1. Run `/daily-end` command
   2. Review proposed memory updates
   3. Approve only if structural changes occurred
   
   ---
   
   ## Workflow Commands
   
   All workflows are triggered by typing commands in chat. See `.cursorrules` for complete details:
   
   - `/work` - Load context, show what to work on
   - `/scrum` or `/dsu` - Daily standup (yesterday/today/blockers)
   - `/interrupt` - Quick capture during work
   - `/save` - Save work state checkpoint
   - `/groom` - Process interrupts to backlog
   - `/refine-backlog` - Promote backlog items to TODO
   - `/daily-end` - End of day workflow
   - `/prioritize` - Reorder TODO items
   - `/weekly-review` - Weekly planning
   - `/monthly-review` - Monthly planning
   - `/system-scan` - System health check
   - `/ai-export` - Export system understanding
   - `/init-exocortex` - Initialize in new project
   
   ---
   
   **See `.exocortex/TEMPLATE_STRUCTURE.md` for complete file templates and structure reference.**
   
   ---
   ```

3. **Create Control Files:**
   
   **Create `docs/control/INTERRUPTS.md`:**
   ```
   # Interrupts
   
   Raw capture during work. Ideas, bugs, concerns — captured quickly without processing.
   
   **Weekly processing:** Run `/groom` to process items.
   
   ---
   
   ## How to Use
   
   - Capture ideas/bugs/concerns during work (use `/interrupt` command)
   - Don't act on them immediately
   - Review weekly with `/groom` command
   - Move to BACKLOG or TODO, or delete
   
   Most items should eventually be deleted.
   
   **Authority:** Human-only. This file has no governance power.
   
   ---
   ```
   
   **Create `docs/control/BACKLOG.md`:**
   ```
   # Backlog
   
   Items under investigation. Questions, spikes, bugs that need understanding.
   
   **Promotion to TODO:** Run `/refine-backlog` when ready to work on items.
   
   ---
   
   ## How to Use
   
   - Items come from INTERRUPTS.md (via `/groom` command)
   - Items are under investigation or need clarification
   - When ready, promote to TODO.md (via `/refine-backlog` command)
   - Items can be deferred or deleted if no longer relevant
   
   ---
   ```
   
   **Create `docs/control/README.md` (Control System Guide):**
   ```
   # Control Center – [Your Project Name]
   
   **Purpose:** Your command center for daily work and strategic planning.
   
   This folder contains the files you use to control project direction, capture ideas, and plan work. All files here are **human-controlled** - they represent your decisions and priorities, not automated suggestions.
   
   ---
   
   ## Files in This Folder
   
   ### `README.md` (this file)
   - Explains the control center structure and purpose
   - Entry point for understanding project control
   
   ### `INTERRUPTS.md`
   - Capture lane for ideas, issues, and observations discovered during execution
   - Prevents context switching and mid-task derailment
   - Reviewed during cleanup, not during execution
   
   ### `SNIPPETS.md`
   - Catalog of all Cursor workflow snippets
   - Reference for when to use each snippet (`/work`, `/interrupt`, `/groom`, etc.)
   - See this file to discover available workflow commands
   
   ---
   
   ## Related Control Files
   
   ### `.exocortex/OPEN_DECISIONS.md`
   - **Purpose:** Tracks unresolved decisions affecting architecture, logic, QA strategy, or product direction
   - **Use:** Review before making changes that touch these areas
   - **Authority:** Human-controlled decision log
   
   ### `docs/control/ROADMAP.md` (optional)
   - **Purpose:** Strategic planning artifact showing current phase, next steps, and future work
   - **Use:** Reference for understanding project evolution and priorities (strategic only, not task-level)
   - **Authority:** Human-controlled strategic planning
   - **Note:** Execution tasks belong in `.exocortex/TODO.md`, not in the roadmap
   
   ### `.exocortex/SESSION_CONTEXT.md`
   - **Purpose:** Current execution slice and immediate focus
   - **Use:** Daily work alignment
   - **Authority:** Human-controlled execution context
   - **Location:** Part of memory system (`.exocortex/`)
   
   ### `.exocortex/TODO.md`
   - **Purpose:** Concrete, testable tasks for current execution slice
   - **Use:** Daily task tracking
   - **Authority:** Human-controlled task list
   - **Location:** Part of memory system (`.exocortex/`)
   
   ---
   
   ## Authority
   
   **This control center is authoritative for:**
   - Daily execution priorities (via `.exocortex/TODO.md`)
   - Strategic planning direction (via `ROADMAP.md` if exists)
   - Decision tracking and resolution (via `.exocortex/OPEN_DECISIONS.md`)
   - Project phase definition (via `.exocortex/SESSION_CONTEXT.md`)
   
   **Human authority:**
   - All files in `docs/control/` are human-controlled
   - All files in `.exocortex/` are human-controlled
   - These override automated suggestions, AI-generated plans, and implied priorities
   
   **When in doubt:** Check control center files first.
   
   ---
   
   ## Workflow
   
   1. **Daily Start:** Run `/work` command or read `.exocortex/SESSION_CONTEXT.md` for current execution slice
   2. **Before Changes:** Check `.exocortex/OPEN_DECISIONS.md` for relevant decisions
   3. **During Work:** Use `/interrupt` command or capture interruptions in `INTERRUPTS.md` (parking lot, not backlog)
   4. **Strategic Planning:** Reference `docs/control/ROADMAP.md` for context (strategic only)
   5. **Task Management:** Use `.exocortex/TODO.md` for concrete work items
   6. **Workflow Commands:** See `docs/control/SNIPPETS.md` for all available snippets
   
   ---
   
   **Last Updated:** [Today's date]
   
   ```
   
   **Create `docs/control/SNIPPETS.md` (Workflow Command Catalog):**
   ```
   # Workflow Snippets Reference
   
   **Purpose:** Catalog of all workflow commands available for project management  
   **Last Updated:** [Today's date]
   
   ---
   
   ## Quick Reference
   
   | Command | Prefix | Purpose | When to Use |
   |---------|--------|---------|-------------|
   | Work | `/work` | Load context & identify tasks | Morning, after break, context switch |
   | Scrum | `/scrum` or `/dsu` | Daily standup (yesterday/today/blockers) | Morning daily scrum/standup |
   | Interrupt | `/interrupt` | Quick capture during work | When you have an idea/bug/concern mid-task |
   | Groom | `/groom` | Process interrupts to backlog | When INTERRUPTS.md has items to review |
   | Refine Backlog | `/refine-backlog` | Promote backlog items to TODO | When backlog items are ready |
   | Save | `/save` | Save current work state | Before breaks, mid-day checkpoints |
   | Daily End | `/daily-end` | End-of-day workflow review | End of work session |
   | Prioritize | `/prioritize` | Reorder TODO items | When TODO needs reorganization |
   | Weekly Review | `/weekly-review` | Weekly planning & review | End of week |
   | Monthly Review | `/monthly-review` | Monthly planning & review | End of month |
   | System Scan | `/system-scan` | System health check | Periodic maintenance |
   | AI Export | `/ai-export` | Export system understanding | For use with another AI |
   | Init Exocortex | `/init-exocortex` | Initialize exocortex structure | First-time setup |
   
   ---
   
   **See `.cursorrules` for complete workflow definitions and detailed steps.**
   
   ---
   ```
   
   **Create `docs/control/DAILY_WORKFLOW.md` (Detailed Workflow Guide):**
   ```
   # Daily Execution Workflow
   
   **Purpose:** Simple, repeatable daily workflow for operating [Your Project Name]
   
   This workflow minimizes context switching and centralizes when memory, TODO, and decisions are updated.
   
   ---
   
   ## Morning Start (5 minutes)
   
   1. **Run:** `/scrum` or `/dsu` for daily standup (or `/work` for quick start)
      - Review: What did I do yesterday?
      - Plan: What will I do today?
      - Check: Any blockers?
      - Update task status (Ready → In Progress)
   
   2. **Read:** `.exocortex/SESSION_CONTEXT.md`
      - Understand today's execution slice
      - Note any frozen areas
   
   3. **Read:** `.exocortex/TODO.md`
      - See what's actually in scope today
      - Maximum 5 items
   
   **Rule:** If it's not in TODO, it is not worked on today.
   
   **Workflow Commands:** See `docs/control/SNIPPETS.md` for all available commands (`/work`, `/interrupt`, `/save`, `/daily-end`, etc.)
   
   ---
   
   ## Execution Mode
   
   **Focus:**
   - Coding
   - Testing
   - Fixing bugs
   - Refactoring (if in TODO)
   
   **Do not do during execution:**
   - Update memory files
   - Edit roadmap
   - Make architectural decisions
   - Switch to different work
   
   **If you need to change direction:**
   - Capture in INTERRUPTS.md
   - Continue current task
   - Review at end of day
   
   ---
   
   ## Interrupts (During Work)
   
   **When an idea, bug, or concern appears:**
   
   1. **Use `/interrupt` command** (or write a short entry to `docs/control/INTERRUPTS.md`)
      - One line is enough
      - No detail required
      - No prioritization needed
      - Takes < 1 minute
   
   2. **Do not act on it immediately**
      - Continue current task
      - Don't context switch
      - Don't investigate now
   
   3. **Process later**
      - Run `/groom` weekly to review
      - Some may become TODO items later
      - No pressure to act on anything
   
   **Process interrupts later:** Run `/groom` command to review and move items to BACKLOG or TODO
   
   **Examples of interruptions:**
   - "Noticed potential bug in [file] line [number]"
   - "Should we add validation for X?"
   - "Idea: [feature concept]"
   
   ---
   
   ## End of Day (5–10 minutes)
   
   1. **Run:** `/daily-end` command (or `end session` or `end session confirm`)
   
   2. **Agent reviews work and proposes:**
      - SESSION_CONTEXT updates (if execution slice changed)
      - TODO updates (check off completed, add discovered tasks - max 5)
      - PROJECT_MEMORY updates (new constraints if any)
      - LESSONS updates (new lessons if any)
      - OPEN_DECISIONS updates (add new OR remove resolved)
   
   3. **You approve only if:**
      - Structural changes occurred (not routine progress)
      - New constraints discovered
      - Decisions resolved
      - Lessons learned
   
   **Remember:** Silence is a valid outcome. You don't need to update memory every day.
   
   ---
   
   ## Quick Reference
   
   **Start of day:**
   1. Run `/scrum` or `/dsu` for daily standup (or `/work` for quick start)
   2. Review: Yesterday's work, Today's plan, Blockers
   3. Update task status (Ready → In Progress)
   4. Work from TODO.md (focus on In Progress task)
   
   **During work:**
   - Code, test, fix
   - Use `/interrupt` command to capture ideas/bugs/concerns
   - Use `/save` command before breaks
   - Do not update memory
   
   **End of day:**
   1. Run `/daily-end` command (or `end session`)
   2. Review proposals
   3. Approve only structural changes
   
   **Weekly:**
   - Run `/groom` to process interrupts
   - Run `/refine-backlog` to promote backlog items
   - Run `/prioritize` to reorder TODO
   
   **Remember:**
   - TODO is your source of truth for daily work
   - ROADMAP is strategic, not tactical
   - INTERRUPTS is a parking lot, not a commitment
   - Memory updates happen at end of day, not during execution
   - **See `docs/control/SNIPPETS.md` for all available workflow commands**
   
   ---
   
   **Last Updated:** [Today's date]
   
   ```

4. **Create `.cursorrules` File:**
   
   **Create `.cursorrules` at project root:**
   - Read the current `.cursorrules` file (this file) to get all workflow definitions
   - Create a new `.cursorrules` file in the target project with the complete content
   - The file should include all workflow commands: `/work`, `/scrum` (or `/dsu`), `/interrupt`, `/save`, `/daily-end`, `/groom`, `/refine-backlog`, `/prioritize`, `/weekly-review`, `/monthly-review`, `/system-scan`, `/ai-export`, `/init-exocortex`
   - Update the header comment to reflect the new project name (replace "[PROJECT_NAME]" with the actual project name)
   - This enables all workflow commands to work immediately in the new project
   
   **Note:** The AI executing this workflow should read the current `.cursorrules` file and create a complete copy in the target project, adapting the project name in the header if needed.

5. **Optional: Copy Documentation (Adaptable):**
   **Note:** Documentation files are optional if using `.cursorrules` (workflows are self-contained).
   
   Optional: Copy these files from your EnkratFlow-Project/docs/ to your project (adapt paths as needed):
   - `AGILE_WORKFLOW.md` — Complete guide on how to work (optional reference)
   - `EXOCORTEX.md` — What is an exocortex and why it matters (optional reference)
   
   Skip `START_HERE.md` since workflows are in `.cursorrules`.

6. **Verify:**
   Checklist:
   - [ ] .exocortex/ folder created
   - [ ] .exocortex/MEMORY.md exists (entry point - REQUIRED)
   - [ ] .exocortex/PROJECT_MEMORY.md exists (system constraints - REQUIRED)
   - [ ] .exocortex/README.md exists (human guide)
   - [ ] .exocortex/SESSION_CONTEXT.md exists
   - [ ] .exocortex/TODO.md exists (with board structure)
   - [ ] .exocortex/LESSONS.md exists (can be empty)
   - [ ] .exocortex/ESSENTIAL_FILES.md exists (can be empty)
   - [ ] .exocortex/OPEN_DECISIONS.md exists (can be empty)
   - [ ] docs/control/ folder created
   - [ ] docs/control/README.md exists (control system guide)
   - [ ] docs/control/INTERRUPTS.md exists
   - [ ] docs/control/BACKLOG.md exists
   - [ ] docs/control/SNIPPETS.md exists (workflow catalog)
   - [ ] docs/control/DAILY_WORKFLOW.md exists (detailed guide)
   - [ ] .cursorrules file exists with all workflow definitions
   - [ ] Documentation files copied (if desired)

7. **Start Working:**
   1. Run `work` to load context
   2. Add your first TODO item
   3. Start working with `interrupt` for ideas, `save` for breaks, `daily-end` for session close
   
   All workflows are available in `.cursorrules` - no snippets needed.

---

## Workflow Reference

See `docs/control/DAILY_WORKFLOW.md` for complete workflow details.
