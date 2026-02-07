# User Guide

## Understanding the Memory System

The exocortex provides four tiers of memory, each designed for different types of recall and analysis.

### Tier 0: RIGHT NOW Memory (0-7 days)
**When to use:** Start of every session, daily standup prep, "what was I working on?"

**What it provides:**
- **Episodic memory** — Specific events, decisions, and actions
- **Scannable format** — Bold date/machine anchors + short paragraphs  
- **Full detail** — Recent events with context preserved
- **Auto-loaded** — Included in `/work` command

**Example output:**
```
**Jan 15, 2024 - macbook-cursor**: Implemented user authentication flow. Added JWT 
token validation middleware and tested login/logout functionality. Discovered that 
the token expires too quickly for development.

**Jan 14, 2024 - desktop-vscode**: Fixed database connection pooling issues. 
Changed from single connection to pool of 10. Performance improved significantly 
for concurrent requests.

**Jan 14, 2024 - macbook-cursor**: Started work on password reset feature. 
Created email templates and SMTP configuration. Still need to implement the 
actual password update logic.
```

**Command usage:**
```
/work  # Automatically includes RIGHT NOW memory
```

### Tier 1: SHORT-TERM Memory (7-31 days)  
**When to use:** Weekly reviews, project planning, "what themes emerged last month?"

**What it provides:**
- **Semantic memory** — Themes and patterns across work sessions
- **Themed blocks** — Related work grouped together
- **Evolution tracking** — How projects developed over time
- **Auto-loaded** — Included in `/work` command

**Example output:**
```
**Authentication System Development**
Over the past few weeks, you built a complete authentication system from scratch. 
Started with basic JWT implementation, then added refresh tokens, password reset 
flow, and email verification. Key challenge was getting the token expiration 
timing right for both security and user experience.

**Database Performance Optimization**  
Significant focus on database performance issues. Moved from single connections 
to connection pooling, added query optimization, and implemented caching for 
frequently accessed data. Results were dramatic - response times improved by 60%.

**UI/UX Refinements**
Continuous iteration on the user interface. Major changes included simplifying 
the navigation, improving form validation feedback, and making the mobile 
experience more responsive. User testing revealed the original design was too 
complex.
```

**Command usage:**
```
/work  # Automatically includes SHORT-TERM memory  
/shortterm  # Focus specifically on this tier
```

### Tier 2: LONG-TERM Memory (31+ days)
**When to use:** Quarterly reviews, project archeology, "how did this project evolve?"

**What it provides:**
- **Historical arcs** — Major developments over months/quarters
- **Pattern recognition** — Recurring challenges and solutions
- **Compression** — Less detail, more synthesis
- **On-demand** — Not auto-loaded, use specific command

**Example output:**
```
**Q4 2023: Foundation Building (31-120 days ago)**
Established core architecture decisions for the trading journal. Chose React + 
TypeScript frontend with Node.js backend. Major debates around database choice 
(PostgreSQL vs MongoDB) and authentication approach. Set up Docker development 
environment and CI/CD pipeline.

**Q1 2024: User Experience Focus (120-180 days ago)**  
Shifted focus to user experience after feedback that the application was too 
complex. Complete redesign of the entry workflow, simplified navigation, and 
improved mobile responsiveness. This period involved significant UI rework but 
established the foundation for user adoption.
```

**Command usage:**
```
/longterm  # View historical arcs and major developments
```

### Tier 3: SUBCONSCIOUS Memory (all events)
**When to use:** Feeling stuck, need fresh perspective, "what patterns am I not seeing?"

**What it provides:**
- **Cross-cutting patterns** — Patterns that span all time periods  
- **Blind spot detection** — Things you might be missing
- **Behavioral analysis** — How you work and make decisions
- **Meta-insights** — Patterns about patterns

**Example output:**
```
**Recurring Technical Debt Pattern**
You consistently underestimate refactoring time by about 50%. This appears in 
authentication rework (estimated 2 days, took 4), database optimization 
(estimated 1 week, took 2), and UI redesign (estimated 3 days, took 6). Consider 
building 2x buffers into technical estimates.

**Decision-Making Under Pressure**  
When facing deadlines, you tend to choose simpler solutions that create technical 
debt rather than investing in better architecture. This happened with the auth 
system (chose JWT over OAuth), database (delayed normalization), and deployment 
(manual vs automated). The debt always gets addressed later, but at higher cost.

**Learning Style Preferences**
You prefer to implement features completely before moving to the next one, rather 
than building horizontal slices. This provides psychological satisfaction but 
sometimes misses integration issues. Consider more frequent integration points.
```

**Command usage:**
```
/subconscious  # Pattern detection across all events
```

## Advanced Command Usage

### /drill - Deep Dive Investigation
The most powerful command for project archeology and knowledge recovery.

**Basic usage:**
```
/drill authentication
/drill database performance  
/drill user interface decisions
```

**Advanced patterns:**

**Technical deep-dive:**
```
/drill JWT token expiration  
# Returns: Complete chronology of JWT implementation decisions, 
# why you chose specific expiration times, problems encountered, solutions tried
```

**Decision archaeology:**
```  
/drill why did we choose PostgreSQL
# Returns: Original database decision process, alternatives considered, 
# criteria used, how it worked out in practice
```

**Problem pattern analysis:**
```
/drill performance issues
# Returns: All performance-related work across all events, 
# patterns in how you identify and solve performance problems
```

**What makes a good drill query:**
- **Specific enough** to focus the search
- **General enough** to catch related work  
- **Problem-focused** rather than solution-focused
- **Decision-oriented** to understand reasoning

### /work - Session Initialization
Your primary command for starting work sessions. Understanding what it does helps you use it effectively.

**Full process:**
1. **Context generation** — Aggregates recent events into unified view
2. **Memory tier processing** — Runs RIGHT NOW and SHORT-TERM analysis
3. **Work state detection** — Analyzes git status, recent files, current context  
4. **Brief synthesis** — Provides actionable summary

**When to use:**
- Start of every work session (daily/hourly)
- After switching projects or contexts
- When you feel lost or unfocused
- After breaks longer than 2 hours

**Reading the output:**
```
✓ Context generated (23 events from last 7 days)
✓ Right now memory processed  
✓ Short term memory processed
✓ Work state detected (5 modified files, feature-auth branch)
✓ Brief: Continue implementing JWT refresh token rotation, 
         focusing on security edge cases and token cleanup
```

**Key indicators:**
- **Event count** — How much recent activity there is
- **Modified files** — What you were working on
- **Branch** — Current context/feature
- **Brief** — AI's understanding of your current priority

## Memory Quality and Optimization

### Creating High-Quality Events
The memory system is only as good as the events you create. Here's how to create events that lead to useful memory:

**Good event structure:**
```markdown  
# [Brief descriptive title]

## What I Did
[Specific actions taken]

## Key Decisions  
[Important choices made and why]

## Problems Encountered
[Issues, blockers, frustrations]

## Context
[Why this work matters, connections to other work]

## Next Steps
[What to do next time]
```

**Event writing tips:**

**Be specific about decisions:**
```
❌ "Fixed the authentication bug"
✅ "Fixed JWT token expiration issue by increasing timeout from 1 hour to 4 hours. 
   Chose 4 hours as balance between security and user experience after testing 
   with 3 different values."
```

**Include your reasoning:**
```
❌ "Chose PostgreSQL for the database"  
✅ "Chose PostgreSQL over MongoDB because we need strong consistency for financial 
   data, and the relationships between users/trades/positions are well-defined. 
   MongoDB would be better for analytics but not core trading data."
```

**Capture problems and context:**
```  
❌ "Worked on UI improvements"
✅ "Simplified the trade entry form after user feedback that it was confusing. 
   Removed the 'advanced options' section and moved those fields to a separate 
   modal. Users were getting overwhelmed by 12 fields on one screen."
```

### Optimizing Memory Retrieval

**Use specific drill queries:**
```
❌ /drill database
✅ /drill PostgreSQL connection pooling performance
```

**Combine commands strategically:**
```
# Weekly review pattern
/work           # What's happening now  
/shortterm      # What themes emerged
/subconscious   # What patterns am I missing
```

**Time your command usage:**
```
# Session start: /work
# Mid-project confusion: /drill <topic>  
# Weekly planning: /shortterm
# Quarterly review: /longterm
# Feeling stuck: /subconscious
```

### Memory System Health

**Signs of healthy memory:**
- RIGHT NOW memory provides specific, actionable context
- SHORT-TERM memory shows clear themes and evolution
- DRILL commands return relevant, comprehensive information
- SUBCONSCIOUS detects meaningful patterns

**Signs of memory issues:**
- Vague, generic responses from memory commands
- DRILL commands return "no relevant information"
- Memory feels disconnected from your actual work
- Patterns detected by SUBCONSCIOUS feel random or irrelevant

**Improving memory quality:**
1. **Write better events** — More detail, better context, clear reasoning
2. **Use consistent terminology** — Same words for same concepts
3. **Create events regularly** — Don't let work sessions go unrecorded  
4. **Include failures** — Failed approaches are valuable learning
5. **Connect to bigger picture** — How does this work relate to project goals

## Multi-Project and Team Usage

### Managing Multiple Projects
Each project can have its own exocortex instance:

**Project-specific setup:**
```
~/projects/trading-journal/.exocortex/  
~/projects/mobile-app/.exocortex/  
~/projects/analytics-dashboard/.exocortex/
```

**Global developer memory:**
```
~/.exocortex/  # Cross-project patterns and learnings
```

**Command priority:**
Commands use the closest `.exocortex/` directory in the directory tree, so you get project-specific context automatically.

**Cross-project insights:**
```
# In global directory
/subconscious  # Patterns across all projects
/drill React performance  # React knowledge from all projects
```

### Team and Collaboration Patterns

**Individual exocortex + shared documentation:**
- Each team member maintains their own exocortex
- Important insights get promoted to shared documentation
- Decisions and architecture get documented in team wikis

**Shared event streams (future feature):**
- Team events could be aggregated for cross-team pattern detection
- Shared memory tiers for team knowledge
- Privacy controls for personal vs team events

**Current team workflow:**
```
1. Individual: Use /work for personal context
2. Individual: Use /drill to research before team discussions  
3. Team: Share insights from /subconscious during retrospectives
4. Team: Document decisions in shared systems, reference personal context
```

## Advanced Customization

### Custom Commands
Create your own workflow commands by adding JSON specs to `.exocortex/commands/`:

**Example: Project status command**
```json
{
  "name": "/status",
  "description": "Generate project status report",
  "steps": [
    {
      "type": "shell",
      "command": ".exocortex/scripts/generate_context.sh",
      "description": "Loading recent context",
      "success_format": "✓ Context loaded"
    },
    {
      "type": "ai",  
      "command": "Based on the context, provide a brief project status: current focus, recent accomplishments, next priorities, and any blockers.",
      "description": "Generating status report",
      "success_format": "✓ Status report generated"
    }
  ]
}
```

### Memory Script Customization  
Modify the memory processing scripts in `.exocortex/scripts/` to change:
- **Output format** — Change bold anchors, paragraph length, structure
- **AI prompts** — Adjust tone, focus areas, analysis depth  
- **Time windows** — Modify day ranges for memory tiers
- **Processing logic** — Add filters, categorization, custom analysis

**Example prompt customization:**
```python
# In get_rightnow_memory.py
SYSTEM_PROMPT = """
You are a software developer's memory system. Analyze recent work events and 
provide scannable context.

Focus on:
- Code changes and technical decisions  
- Architecture choices and why they were made
- Problems encountered and solutions attempted
- Dependencies between different work items

Format with bold date anchors and short, specific paragraphs.
Avoid corporate language - be direct and technical.
"""
```

### Integration Customization

**Different AI assistants:**
- Cursor: Uses `.cursorrules`
- VS Code: Uses workspace settings
- Claude Desktop: Uses system instructions  
- Custom: Implement command recognition in your preferred tool

**Event creation hooks:**
- Git hooks for automatic event creation on commits
- Editor plugins for session-based event creation
- Time-based triggers for periodic event capture

---

*Next: Read [Memory System Details](memory-system.md) for deeper understanding of how the memory tiers work internally.*