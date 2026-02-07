# Event System

## Overview

The event system is the foundation of the exocortex — it captures your work sessions as append-only markdown files that serve as the raw material for all memory processing.

### Core Principles

**Append-only** — Events are never modified after creation, ensuring historical integrity  
**Machine-aware** — Each event captures which development environment was used  
**Editor-agnostic** — Works with any text editor or IDE  
**Human-readable** — Events are markdown files you can read and search manually  
**Version-controllable** — Events sync across machines via git

### Event Anatomy

**File naming convention:**
```
YYYY-MM-DD_HH-MM-SS_machine-editor.md
2024-01-15_14-30-00_macbook-cursor.md
2024-01-15_16-45-30_desktop-vscode.md
```

**File structure:**
```markdown
---
timestamp: 2024-01-15T14:30:00Z
machine: macbook
editor: cursor  
git_branch: feature-auth
git_status: modified
work_duration: 120
---

# Authentication System Implementation

## What I Did
- Implemented JWT token validation middleware
- Added refresh token rotation logic  
- Created login/logout API endpoints
- Wrote unit tests for auth functions

## Key Decisions
- Chose JWT over session cookies for stateless auth
- Set token expiration to 4 hours (balance security vs UX)
- Used bcrypt with cost factor 12 for password hashing
- Decided to store refresh tokens in database for revocation

## Problems Encountered  
- Token expiration too short initially (1 hour caused UX issues)
- Bcrypt cost factor 10 was too fast on production hardware
- Refresh token rotation created race condition with concurrent requests

## Context
- Working toward MVP launch in 2 weeks
- Authentication is blocking other features
- Need to balance security with development speed
- Previous session-based auth was causing scaling issues

## Next Steps
- Test token rotation under load
- Add rate limiting for login attempts  
- Implement password reset flow
- Document authentication architecture decisions
```

## Event Creation Methods

### 1. Manual Creation
Direct event creation for significant work sessions:

```bash
# Create event with description
.exocortex/scripts/create_event.sh "Implemented user authentication system"

# Create event with auto-detected work state
.exocortex/scripts/create_event.sh
```

**When to use:**
- End of significant work sessions
- After completing features or fixing major bugs
- When you want to capture specific decision context
- Before switching to different projects

### 2. Automatic Detection  
System-triggered event creation based on work patterns:

```bash
# Detect and create event if significant work has occurred
.exocortex/scripts/detect_work_state.sh
```

**Triggers automatic event creation:**
- Modified files in git (more than 3 files or 100 lines)
- Time elapsed since last event (more than 2 hours of active work)
- Branch switching with uncommitted changes
- First work session of the day

### 3. Editor Integration
IDE/editor plugins for seamless event capture:

**Cursor integration (via .cursorrules):**
```
When user says "/save <description>", create event with:
- Description from user
- Current file context  
- Git status
- Recent changes summary
```

**VS Code integration (future):**
- Workspace extension for event creation
- Automatic triggers on file save patterns
- Integration with git workflow

### 4. Git Hooks (Optional)
Automatic event creation on git operations:

```bash
# .git/hooks/post-commit
#!/bin/bash
if [ -f .exocortex/scripts/create_event.sh ]; then
    .exocortex/scripts/create_event.sh "Committed: $(git log -1 --pretty=%s)"
fi
```

## Event Metadata System

### YAML Frontmatter
Every event includes structured metadata:

```yaml
---
timestamp: 2024-01-15T14:30:00Z    # ISO 8601 timestamp
machine: macbook                    # Development machine identifier  
editor: cursor                      # Editor/IDE used
git_branch: feature-auth           # Current git branch
git_status: modified               # Git working directory status
work_duration: 120                 # Minutes of active work
files_modified: 5                  # Number of files changed
lines_added: 234                   # Lines of code added
lines_removed: 67                  # Lines of code removed
tags: [auth, security, backend]    # Custom tags for categorization
---
```

### Metadata Collection Logic

**Machine identification:**
```bash
# Detect development environment
if command -v scutil >/dev/null 2>&1; then
    MACHINE=$(scutil --get ComputerName | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9]//g')
else  
    MACHINE=$(hostname | cut -d. -f1 | tr '[:upper:]' '[:lower:]')
fi
```

**Editor detection:**
```bash
# Detect current editor context
if [ -n "$CURSOR_SESSION" ]; then
    EDITOR="cursor"
elif [ -n "$VSCODE_PID" ]; then
    EDITOR="vscode"  
elif [ -n "$VIM" ]; then
    EDITOR="vim"
else
    EDITOR="terminal"
fi
```

**Git context extraction:**
```bash
# Capture git state
GIT_BRANCH=$(git branch --show-current 2>/dev/null || echo "none")
GIT_STATUS=$(git status --porcelain 2>/dev/null | wc -l | tr -d ' ')
MODIFIED_FILES=$(git diff --name-only 2>/dev/null | wc -l | tr -d ' ')
```

## Event Quality Framework

### High-Quality Event Characteristics

**Specific actions:**
```markdown
❌ "Worked on the database layer"
✅ "Optimized user query performance by adding composite index on (user_id, created_at)"
```

**Decision context:**
```markdown  
❌ "Fixed the bug"
✅ "Fixed race condition in token refresh by adding database-level locking. 
   Chose database locks over application-level locks because we need 
   consistency across multiple server instances."
```

**Problem documentation:**
```markdown
❌ "Had some issues but got it working"  
✅ "Initial approach using in-memory cache caused problems with multiple 
   server instances. Cache invalidation wasn't synchronized. Switched 
   to Redis for shared cache state."
```

**Context preservation:**
```markdown
❌ "Added new feature"
✅ "Added bulk import feature for trading data. Customer requested this 
   for onboarding existing traders with historical data. Chose CSV format 
   over API integration due to data sensitivity concerns."
```

### Event Writing Guidelines

**Structure template:**
```markdown
# [Descriptive Title - What was accomplished]

## What I Did
- [Specific action 1]
- [Specific action 2]  
- [Specific action 3]

## Key Decisions
- [Decision 1]: [Reasoning]
- [Decision 2]: [Reasoning]

## Problems Encountered
- [Problem 1]: [How it was resolved or current status]
- [Problem 2]: [How it was resolved or current status]

## Context  
- [Why this work matters]
- [How it connects to larger goals]
- [Constraints or pressures influencing decisions]

## Next Steps
- [What to do next]
- [Open questions or investigations needed]
```

**Content guidelines:**

**Be specific about technologies:**
```markdown
❌ "Updated the frontend"
✅ "Migrated login form from class components to React hooks, 
   replaced Redux with Zustand for simpler state management"
```

**Include reasoning:**
```markdown
❌ "Chose PostgreSQL"
✅ "Chose PostgreSQL over MongoDB because trading data has strong 
   relationships (users→accounts→positions→trades) and we need 
   ACID transactions for financial accuracy"
```

**Document failed approaches:**
```markdown
❌ "Got authentication working"
✅ "Got authentication working after trying 3 approaches:
   1. Session cookies (failed: doesn't scale across servers)
   2. JWT with 24hr expiration (failed: security team rejected) 
   3. JWT with 4hr + refresh tokens (working: balances security/UX)"
```

## Event Processing Pipeline

### 1. Event Collection
Scripts that aggregate events for memory processing:

```bash  
# Collect events by time range
collect_events_by_date_range() {
    local start_date=$1
    local end_date=$2
    find .exocortex/events/ -name "*.md" -newermt "$start_date" ! -newermt "$end_date"
}

# Collect events by machine
collect_events_by_machine() {
    local machine=$1
    grep -l "machine: $machine" .exocortex/events/*.md
}
```

### 2. Event Parsing
Extract and structure event content:

```python
import yaml
import re

def parse_event(event_file):
    """Parse event file into metadata and content."""
    with open(event_file, 'r') as f:
        content = f.read()
    
    # Split frontmatter and content
    parts = content.split('---', 2)
    if len(parts) >= 3:
        metadata = yaml.safe_load(parts[1])
        body = parts[2].strip()
    else:
        metadata = {}
        body = content
    
    return {
        'metadata': metadata,
        'content': body,
        'filepath': event_file
    }
```

### 3. Event Filtering
Filter events based on criteria:

```python
def filter_events(events, criteria):
    """Filter events based on various criteria."""
    filtered = []
    
    for event in events:
        # Time range filtering
        if criteria.get('start_date') and event['metadata'].get('timestamp'):
            event_date = parse_datetime(event['metadata']['timestamp'])
            if event_date < criteria['start_date']:
                continue
                
        # Machine filtering  
        if criteria.get('machine') and event['metadata'].get('machine'):
            if event['metadata']['machine'] != criteria['machine']:
                continue
                
        # Tag filtering
        if criteria.get('tags') and event['metadata'].get('tags'):
            if not any(tag in event['metadata']['tags'] for tag in criteria['tags']):
                continue
                
        filtered.append(event)
    
    return filtered
```

### 4. Event Analysis
Pre-processing for memory systems:

```python
def analyze_events(events):
    """Extract patterns and insights from event collection."""
    analysis = {
        'total_events': len(events),
        'date_range': get_date_range(events),
        'machines': get_unique_machines(events), 
        'editors': get_unique_editors(events),
        'branches': get_unique_branches(events),
        'themes': extract_themes(events),
        'work_patterns': analyze_work_patterns(events)
    }
    return analysis
```

## Storage and Archival

### File System Organization
```
.exocortex/events/
├── 2024/
│   ├── 01/
│   │   ├── 2024-01-15_14-30-00_macbook-cursor.md
│   │   ├── 2024-01-15_16-45-30_desktop-vscode.md
│   │   └── ...
│   ├── 02/
│   └── ...
├── 2023/
│   └── ...
└── archived/
    ├── 2022_compressed.jsonl
    └── 2021_compressed.jsonl
```

### Archival Strategy
**Active events:** Last 12 months in full markdown format  
**Archived events:** Older than 12 months, compressed to JSONL format  
**Backup strategy:** Events sync via git, with separate backup of archived data

**Compression logic:**
```python
def compress_old_events(cutoff_date):
    """Compress events older than cutoff_date to JSONL format."""
    old_events = find_events_before(cutoff_date)
    compressed_data = []
    
    for event_file in old_events:
        event = parse_event(event_file)
        # Extract key information for compressed storage
        compressed = {
            'timestamp': event['metadata']['timestamp'],
            'machine': event['metadata']['machine'],
            'title': extract_title(event['content']),
            'summary': extract_summary(event['content']),
            'decisions': extract_decisions(event['content']),
            'tags': event['metadata'].get('tags', [])
        }
        compressed_data.append(compressed)
        
    # Save compressed data
    year = cutoff_date.year
    with open(f'.exocortex/events/archived/{year}_compressed.jsonl', 'w') as f:
        for item in compressed_data:
            f.write(json.dumps(item) + '\n')
            
    # Remove original files after successful compression
    for event_file in old_events:
        os.remove(event_file)
```

### Multi-Machine Synchronization

**Git-based sync (recommended):**
```bash
# .gitignore configuration
.exocortex/.env          # Keep API keys private
.exocortex/SESSION_CONTEXT.md  # Regenerated automatically

# Include everything else
!.exocortex/
!.exocortex/events/
!.exocortex/commands/
!.exocortex/scripts/
```

**Conflict resolution:**
Events are append-only by design, so conflicts are rare. When they occur:
1. Both events are preserved (rename one with conflict suffix)
2. Manual review determines if events should be merged
3. Duplicate detection can identify and remove true duplicates

**Sync workflow:**
```bash
# Push events from current machine
git add .exocortex/events/
git commit -m "Add events from $(hostname) $(date +%Y-%m-%d)"
git push

# Pull events from other machines  
git pull
# Events are automatically available for memory processing
```

## Advanced Event Features

### Custom Event Types
Extend events with custom metadata and structure:

**Meeting events:**
```yaml
---
event_type: meeting
participants: [john, sarah, mike]
meeting_type: planning
duration_minutes: 60
decisions_made: 3
action_items: 5
---
```

**Learning events:**
```yaml  
---
event_type: learning
technology: React
learning_method: documentation
time_invested: 120
proficiency_before: beginner
proficiency_after: intermediate
resources: [react-docs, tutorial-video]
---
```

### Event Relationships
Link related events for better context:

```yaml
---
related_events:
  - 2024-01-14_16-30-00_macbook-cursor.md  # Previous work on same feature
  - 2024-01-10_09-15-00_desktop-vscode.md  # Initial planning session
parent_event: 2024-01-13_14-00-00_macbook-cursor.md  # Continuing work from
---
```

### Event Templates
Standardized templates for common event types:

**Bug fix template:**
```markdown
# Bug Fix: [Brief description]

## Problem
- [What was broken]
- [How it manifested]  
- [Impact on users/system]

## Root Cause
- [Why the bug occurred]
- [Contributing factors]

## Solution
- [How it was fixed]
- [Code changes made]
- [Tests added]

## Prevention
- [How to avoid similar bugs]
- [Process improvements]
```

**Feature implementation template:**
```markdown  
# Feature: [Feature name]

## Requirements
- [What the feature should do]
- [Acceptance criteria]

## Design Decisions
- [Architecture choices]
- [Technology decisions]
- [Trade-offs considered]

## Implementation
- [How it was built]
- [Key components created]
- [Integration points]

## Testing
- [Test strategy]  
- [Test cases covered]
- [Edge cases considered]
```

---

*Next: Read [Command System Details](command-system.md) for understanding how workflows are automated.*