# Implementation Guide

## Repository Structure

```
exocortex/
├── README.md                      # Project overview and quick start
├── docs/                          # Comprehensive documentation
│   ├── architecture.md           # System architecture and design
│   ├── getting-started.md         # Setup and basic usage
│   ├── user-guide.md             # Detailed usage patterns  
│   ├── memory-system.md          # Memory tier deep dive
│   ├── event-system.md           # Event creation and management
│   ├── command-system.md         # Workflow automation
│   ├── api-reference.md          # Script APIs and interfaces
│   ├── implementation.md         # This file - how to implement
│   ├── roadmap.md                # Future development plans
│   └── research.md               # Neuroscience foundation
├── .exocortex/                   # Core system files
│   ├── commands/                 # JSON workflow specifications
│   │   ├── work.json            # Main context loading command
│   │   ├── drill.json           # Deep-dive memory search
│   │   ├── shortterm.json       # 7-31 day memory analysis
│   │   ├── longterm.json        # 31+ day historical analysis  
│   │   └── subconscious.json    # Cross-cutting pattern detection
│   ├── scripts/                 # Processing and utility scripts
│   │   ├── generate_context.sh  # Event aggregation
│   │   ├── get_rightnow_memory.py     # 0-7 day memory processing
│   │   ├── get_shortterm_memory.py    # 7-31 day memory processing  
│   │   ├── get_longterm_memory.py     # 31+ day memory processing
│   │   ├── get_subconscious_memory.py # Pattern detection processing
│   │   ├── drill_memory.py            # Topic-specific deep search
│   │   ├── create_event.sh            # Event creation utility
│   │   ├── detect_work_state.sh       # Auto work detection
│   │   └── archive_events.sh          # Event archival management
│   ├── events/                  # Event storage (created at runtime)
│   ├── .env.example             # Environment template  
│   ├── commands/                # JSON command specifications (20 commands)
│   ├── COMMAND_SYSTEM.md        # Command system documentation
│   └── MEMORY_TIERS.md          # Memory system documentation  
├── examples/                    # Example configurations and usage
│   ├── vscode-settings.json     # VS Code integration
│   ├── sample-events/           # Example event files
│   └── custom-commands/         # Example custom commands
├── tests/                       # Test suite
│   ├── test_memory_processing.py
│   ├── test_event_creation.py  
│   ├── test_command_execution.py
│   └── fixtures/               # Test data
└── install.sh                  # Installation script
```

## Installation Methods

### Method 1: Direct Installation
For integrating into existing projects:

```bash  
#!/bin/bash
# install.sh - Direct installation script

set -e

INSTALL_DIR="${1:-.exocortex}"
PROJECT_ROOT=$(pwd)

echo "Installing exocortex to $PROJECT_ROOT/$INSTALL_DIR"

# Create directory structure
mkdir -p "$INSTALL_DIR"/{commands,scripts,events}

# Download and install core files
curl -sL https://github.com/user/exocortex/releases/latest/download/exocortex-core.tar.gz | tar -xz -C "$INSTALL_DIR"

# Make scripts executable  
chmod +x "$INSTALL_DIR"/scripts/*.sh
chmod +x "$INSTALL_DIR"/scripts/*.py

# Create environment template
if [ ! -f "$INSTALL_DIR/.env" ]; then
    cp "$INSTALL_DIR/.env.example" "$INSTALL_DIR/.env"
    echo "Created .env file - please add your API keys"
fi

# Add to .gitignore
if [ -f .gitignore ]; then
    echo ".exocortex/.env" >> .gitignore
    echo ".exocortex/SESSION_CONTEXT.md" >> .gitignore
else
    echo -e ".exocortex/.env\n.exocortex/SESSION_CONTEXT.md" > .gitignore
fi

echo "✓ Exocortex installed successfully"
echo "Next steps:"
echo "  1. Add API keys to $INSTALL_DIR/.env"
echo "  2. Add exocortex user rule in Cursor Settings > General > Rules for AI (see README.md)"
echo "  3. Run: $INSTALL_DIR/scripts/create_event.sh 'Initial setup'"
```

### Method 2: Git Submodule
For version-controlled installations:

```bash
# Add exocortex as submodule
git submodule add https://github.com/user/exocortex.git .exocortex
git submodule update --init --recursive

# Link or copy configuration files
# User rules are set in Cursor Settings > General > Rules for AI (not per-project files)
cp .exocortex/examples/.env.example .exocortex/.env

# Make scripts executable
chmod +x .exocortex/scripts/*.sh
chmod +x .exocortex/scripts/*.py
```

### Method 3: Package Manager (Future)
```bash
# NPM package (planned)
npm install -g @exocortex/cli
exocortex init

# Homebrew formula (planned)  
brew install exocortex
exocortex setup
```

## Core Script Implementation

### Memory Processing Scripts (Python)

**get_rightnow_memory.py:**
```python
#!/usr/bin/env python3
"""
RIGHT NOW memory processing (0-7 days)
Provides episodic memory with scannable format
"""

import os
import sys
import json
import openai
from datetime import datetime, timedelta
from pathlib import Path

# Configuration
DAYS_BACK = 7
EVENT_DIR = Path(".exocortex/events")
ENV_FILE = Path(".exocortex/.env")

def load_environment():
    """Load API keys from .env file."""
    env_vars = {}
    if ENV_FILE.exists():
        with open(ENV_FILE) as f:
            for line in f:
                if '=' in line and not line.startswith('#'):
                    key, value = line.strip().split('=', 1)
                    env_vars[key] = value
    return env_vars

def collect_recent_events():
    """Collect events from the last 7 days."""
    cutoff_date = datetime.now() - timedelta(days=DAYS_BACK)
    events = []
    
    for event_file in EVENT_DIR.glob("**/*.md"):
        # Parse date from filename: YYYY-MM-DD_HH-MM-SS_machine-editor.md
        try:
            date_part = event_file.stem.split('_')[0]
            event_date = datetime.strptime(date_part, "%Y-%m-%d")
            
            if event_date >= cutoff_date:
                with open(event_file) as f:
                    content = f.read()
                events.append({
                    'date': date_part,
                    'file': str(event_file),
                    'content': content
                })
        except (ValueError, IndexError):
            continue
    
    # Sort by date
    events.sort(key=lambda x: x['date'])
    return events

def call_openai(prompt, events_text):
    """Call OpenAI API for memory processing."""
    client = openai.OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": events_text}
        ]
    )
    return response.choices[0].message.content

def call_anthropic(prompt, events_text):
    """Fallback to Anthropic API."""
    import anthropic
    client = anthropic.Anthropic(api_key=os.environ.get('ANTHROPIC_API_KEY'))
    
    response = client.messages.create(
        model="claude-3-haiku-20240307",
        max_tokens=2000,
        messages=[
            {"role": "user", "content": f"{prompt}\n\nEvents:\n{events_text}"}
        ]
    )
    return response.content[0].text

def process_memory_pass1(events):
    """First pass: Generate memory from events."""
    events_text = "\n\n".join([f"File: {e['file']}\n{e['content']}" for e in events])
    
    prompt = """
You are a memory system analyzing recent work events (0-7 days).
Provide scannable episodic memory with specific details.

Format each event as:
**Date - Machine**: Brief action. Key details. Context.

Focus on:
- Specific actions taken
- Important decisions made  
- Problems encountered
- Context about why work was done

Use direct, technical language. Avoid: "implemented", "leveraged", "enhanced", "optimized".
Replace with: "built", "used", "improved", "made faster".

Create 2-3 short paragraphs maximum. Use bold date anchors for scannability.
"""
    
    try:
        return call_openai(prompt, events_text)
    except Exception:
        return call_anthropic(prompt, events_text)

def process_memory_pass2(initial_output):
    """Second pass: Self-critique and refinement."""
    critique_prompt = """
Review your output and improve it by:

1. Replacing corporate language with direct technical terms:
   - "implemented" → "built"
   - "leveraged" → "used"  
   - "enhanced" → "improved"
   - "optimized" → "made faster"
   - "comprehensive" → "complete"

2. Ensuring bold anchors are present and scannable  
3. Making paragraphs short (2-3 sentences max)
4. Being specific rather than vague
5. Focusing on actions and decisions rather than abstract concepts

Find specific instances of banned words and replace them with direct alternatives.
Output only the improved version.
"""
    
    try:
        client = openai.OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": critique_prompt},
                {"role": "user", "content": f"Initial output:\n{initial_output}"}
            ]
        )
        return response.choices[0].message.content
    except Exception:
        return initial_output  # Return original if critique fails

def main():
    """Main processing function."""
    # Load environment
    env_vars = load_environment()
    for key, value in env_vars.items():
        os.environ[key] = value
    
    # Check for API keys
    if not os.environ.get('OPENAI_API_KEY') and not os.environ.get('ANTHROPIC_API_KEY'):
        print("Error: No API keys found in .exocortex/.env", file=sys.stderr)
        sys.exit(1)
    
    # Collect and process events
    events = collect_recent_events()
    
    if not events:
        print("No recent events found (last 7 days)")
        return
    
    # Two-pass processing
    pass1_output = process_memory_pass1(events)
    final_output = process_memory_pass2(pass1_output)
    
    print(final_output)

if __name__ == "__main__":
    main()
```

### Context Generation Script (Bash)

**generate_context.sh:**
```bash
#!/bin/bash
"""
Context generation script - aggregates events and memory for AI consumption
"""

set -e

EXOCORTEX_DIR=".exocortex"
CONTEXT_FILE="$EXOCORTEX_DIR/SESSION_CONTEXT.md"
EVENTS_DIR="$EXOCORTEX_DIR/events"

# Ensure exocortex directory exists
if [ ! -d "$EXOCORTEX_DIR" ]; then
    echo "Error: .exocortex directory not found"
    exit 1
fi

# Count recent events (last 7 days)
recent_count=0
if [ -d "$EVENTS_DIR" ]; then
    cutoff_date=$(date -d '7 days ago' '+%Y-%m-%d' 2>/dev/null || date -v-7d '+%Y-%m-%d')
    recent_count=$(find "$EVENTS_DIR" -name "*.md" -newer <(date -d "$cutoff_date" 2>/dev/null || date -v-"$cutoff_date") | wc -l)
fi

# Generate context file
cat > "$CONTEXT_FILE" << EOF
# Session Context

Generated: $(date)
Recent events: $recent_count (last 7 days)

## Recent Activity (Right Now Memory)

EOF

# Add RIGHT NOW memory if available
if command -v python3 >/dev/null 2>&1 && [ -f "$EXOCORTEX_DIR/scripts/get_rightnow_memory.py" ]; then
    echo "Generating recent memory..." >&2
    if python3 "$EXOCORTEX_DIR/scripts/get_rightnow_memory.py" >> "$CONTEXT_FILE" 2>/dev/null; then
        echo >> "$CONTEXT_FILE"
    else
        echo "No recent activity or memory generation failed" >> "$CONTEXT_FILE"
        echo >> "$CONTEXT_FILE"
    fi
else
    echo "Memory processing not available (Python or scripts missing)" >> "$CONTEXT_FILE"
    echo >> "$CONTEXT_FILE"
fi

# Add SHORT-TERM memory if available  
cat >> "$CONTEXT_FILE" << EOF
## Themes and Patterns (Short Term Memory)

EOF

if command -v python3 >/dev/null 2>&1 && [ -f "$EXOCORTEX_DIR/scripts/get_shortterm_memory.py" ]; then
    echo "Generating short term memory..." >&2
    if python3 "$EXOCORTEX_DIR/scripts/get_shortterm_memory.py" >> "$CONTEXT_FILE" 2>/dev/null; then
        echo >> "$CONTEXT_FILE"
    else
        echo "No short term patterns available" >> "$CONTEXT_FILE"
        echo >> "$CONTEXT_FILE"
    fi
else
    echo "Short term memory processing not available" >> "$CONTEXT_FILE"
    echo >> "$CONTEXT_FILE"
fi

# Add work state information
cat >> "$CONTEXT_FILE" << EOF
## Current Work State

EOF

if [ -f "$EXOCORTEX_DIR/scripts/detect_work_state.sh" ]; then
    echo "Detecting work state..." >&2
    bash "$EXOCORTEX_DIR/scripts/detect_work_state.sh" >> "$CONTEXT_FILE" 2>/dev/null || echo "Work state detection failed" >> "$CONTEXT_FILE"
else
    echo "Work state detection not available" >> "$CONTEXT_FILE"
fi

echo >> "$CONTEXT_FILE"

echo "Context generated: $CONTEXT_FILE" >&2
```

### Event Creation Script (Bash)

**create_event.sh:**
```bash
#!/bin/bash
"""
Event creation script - captures work sessions as structured markdown files
"""

set -e

EXOCORTEX_DIR=".exocortex"
EVENTS_DIR="$EXOCORTEX_DIR/events"
DESCRIPTION="$1"

# Create events directory if it doesn't exist
mkdir -p "$EVENTS_DIR"

# Generate filename components
TIMESTAMP=$(date '+%Y-%m-%d_%H-%M-%S')
MACHINE=$(hostname | cut -d. -f1 | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9]//g')

# Detect editor context
EDITOR_CONTEXT="terminal"
if [ -n "$CURSOR_SESSION" ]; then
    EDITOR_CONTEXT="cursor"
elif [ -n "$VSCODE_PID" ]; then
    EDITOR_CONTEXT="vscode"
elif [ -n "$VIM" ]; then
    EDITOR_CONTEXT="vim"
fi

# Generate event filename
EVENT_FILE="$EVENTS_DIR/${TIMESTAMP}_${MACHINE}-${EDITOR_CONTEXT}.md"

# Collect git context
GIT_BRANCH="none"
GIT_STATUS="clean"
MODIFIED_FILES=0
if git rev-parse --git-dir >/dev/null 2>&1; then
    GIT_BRANCH=$(git branch --show-current 2>/dev/null || echo "detached")
    GIT_STATUS_OUTPUT=$(git status --porcelain 2>/dev/null || echo "")
    MODIFIED_FILES=$(echo "$GIT_STATUS_OUTPUT" | wc -l | tr -d ' ')
    if [ "$MODIFIED_FILES" -gt 0 ]; then
        GIT_STATUS="modified"
    fi
fi

# Interactive event creation if no description provided
if [ -z "$DESCRIPTION" ]; then
    echo "Creating new event for $MACHINE ($EDITOR_CONTEXT)"
    echo "Git: $GIT_BRANCH ($MODIFIED_FILES modified files)"
    echo
    read -p "Event description: " DESCRIPTION
fi

if [ -z "$DESCRIPTION" ]; then
    echo "Error: Event description required"
    exit 1
fi

# Create event file with template
cat > "$EVENT_FILE" << EOF
---
timestamp: $(date -Iseconds)
machine: $MACHINE
editor: $EDITOR_CONTEXT
git_branch: $GIT_BRANCH
git_status: $GIT_STATUS
files_modified: $MODIFIED_FILES
---

# $DESCRIPTION

## What I Did
- [Describe specific actions taken]
- [Include technical details and decisions]
- [Document what was accomplished]

## Key Decisions
- [Important choices made and why]
- [Alternatives considered]
- [Reasoning behind decisions]

## Problems Encountered
- [Issues, blockers, or challenges]
- [How they were resolved or current status]
- [Lessons learned from difficulties]

## Context
- [Why this work matters]
- [How it connects to larger goals]
- [Business/technical context]

## Next Steps
- [What to do next]
- [Open questions or investigations needed]
- [Dependencies or blockers for future work]
EOF

echo "Created event: $(basename "$EVENT_FILE")"
echo "Edit with: \$EDITOR $EVENT_FILE"

# Optionally open in editor
if [ "$2" = "--edit" ] || [ "$2" = "-e" ]; then
    ${EDITOR:-nano} "$EVENT_FILE"
fi
```

## Command System Implementation

### Command Specification Format
Commands are defined as JSON files in `.exocortex/commands/`:

**work.json:**
```json
{
  "name": "/work",
  "description": "Load recent context and memory for work session",
  "steps": [
    {
      "type": "shell",
      "command": ".exocortex/scripts/generate_context.sh",
      "description": "Generating recent context",
      "success_format": "✓ Context loaded ({} events from last 7 days)"
    },
    {
      "type": "shell", 
      "command": ".exocortex/scripts/get_rightnow_memory.py",
      "description": "Processing right now memory",
      "success_format": "✓ Right now memory processed"
    },
    {
      "type": "shell",
      "command": ".exocortex/scripts/get_shortterm_memory.py", 
      "description": "Processing short term memory",
      "success_format": "✓ Short term memory processed"
    },
    {
      "type": "shell",
      "command": ".exocortex/scripts/detect_work_state.sh",
      "description": "Detecting current work state", 
      "success_format": "✓ Work state detected"
    },
    {
      "type": "ai",
      "command": "Based on the generated context, provide a brief 2-3 sentence summary of what I should focus on in this work session. Include any important context from recent memory.",
      "description": "Generating work session brief",
      "success_format": "✓ Brief: {summary}"
    }
  ]
}
```

### AI Assistant Integration

**User rules + AI_BOOTSTRAP.md:**
- **Cursor:** Add exocortex user rule in Settings > General > Rules for AI (see README.md for rule text). The rule instructs the AI to read `.exocortex/AI_BOOTSTRAP.md` when commands are invoked.
- **Other editors:** Tell the AI "read .exocortex/AI_BOOTSTRAP.md" at session start.
- `AI_BOOTSTRAP.md` defines command recognition, step execution, and memory system integration. See that file for the full protocol.

## Testing Implementation

### Unit Tests for Memory Processing

**test_memory_processing.py:**
```python
import unittest
import tempfile
import os
from pathlib import Path
import sys

# Add scripts to path
sys.path.append('.exocortex/scripts')

from get_rightnow_memory import collect_recent_events, process_memory_pass1
from get_shortterm_memory import collect_shortterm_events, process_themes

class TestMemoryProcessing(unittest.TestCase):
    
    def setUp(self):
        """Set up test environment with sample events."""
        self.test_dir = tempfile.mkdtemp()
        self.events_dir = Path(self.test_dir) / "events"
        self.events_dir.mkdir()
        
        # Create sample events
        self.create_sample_event("2024-01-15_14-30-00_test-cursor.md", 
                                "Implemented authentication system")
        self.create_sample_event("2024-01-14_09-15-00_test-vscode.md",
                                "Fixed database connection issues")
    
    def create_sample_event(self, filename, description):
        """Create a sample event file for testing."""
        event_content = f"""---
timestamp: 2024-01-15T14:30:00Z
machine: test
editor: cursor
---

# {description}

## What I Did
- Built JWT authentication middleware
- Added token validation logic
- Created login/logout endpoints

## Key Decisions  
- Chose JWT over sessions for scalability
- Set 4 hour token expiration for security/UX balance

## Problems Encountered
- Initial token expiration too short
- Race conditions with refresh token rotation

## Context
- Working toward MVP launch
- Authentication blocking other features
"""
        
        event_file = self.events_dir / filename
        with open(event_file, 'w') as f:
            f.write(event_content)
    
    def test_event_collection(self):
        """Test that events are collected correctly."""
        # Mock EVENT_DIR for testing
        import get_rightnow_memory
        original_event_dir = get_rightnow_memory.EVENT_DIR
        get_rightnow_memory.EVENT_DIR = self.events_dir
        
        try:
            events = collect_recent_events()
            self.assertEqual(len(events), 2)
            self.assertIn("authentication", events[0]['content'].lower())
        finally:
            get_rightnow_memory.EVENT_DIR = original_event_dir
    
    def test_memory_processing(self):
        """Test memory processing produces valid output."""
        events = [
            {
                'date': '2024-01-15',
                'file': 'test_event.md',
                'content': 'Test event content with specific technical details'
            }
        ]
        
        # Mock AI call for testing
        def mock_ai_call(prompt, events_text):
            return "**Jan 15, 2024 - test**: Built authentication system. Added JWT middleware and token validation. Chose 4-hour expiration for security balance."
        
        import get_rightnow_memory
        original_call = get_rightnow_memory.call_openai
        get_rightnow_memory.call_openai = mock_ai_call
        
        try:
            result = process_memory_pass1(events)
            self.assertIn("**", result)  # Check for bold anchors
            self.assertIn("Built", result)  # Check for direct language
            self.assertNotIn("implemented", result)  # Check banned words removed
        finally:
            get_rightnow_memory.call_openai = original_call

if __name__ == '__main__':
    unittest.main()
```

### Integration Tests

**test_command_execution.py:**
```python
import unittest
import json
import subprocess
from pathlib import Path

class TestCommandExecution(unittest.TestCase):
    
    def test_work_command_structure(self):
        """Test that work.json command is properly structured."""
        work_command_file = Path(".exocortex/commands/work.json")
        self.assertTrue(work_command_file.exists())
        
        with open(work_command_file) as f:
            command_spec = json.load(f)
        
        required_fields = ['name', 'description', 'steps']
        for field in required_fields:
            self.assertIn(field, command_spec)
        
        self.assertEqual(command_spec['name'], '/work')
        self.assertTrue(len(command_spec['steps']) > 0)
        
        # Validate step structure
        for step in command_spec['steps']:
            required_step_fields = ['type', 'command', 'description']
            for field in required_step_fields:
                self.assertIn(field, step)
            self.assertIn(step['type'], ['shell', 'ai'])
    
    def test_script_execution(self):
        """Test that core scripts are executable and functional."""
        scripts = [
            'generate_context.sh',
            'create_event.sh',
            'detect_work_state.sh'
        ]
        
        for script in scripts:
            script_path = Path(f".exocortex/scripts/{script}")
            self.assertTrue(script_path.exists(), f"Script {script} not found")
            self.assertTrue(os.access(script_path, os.X_OK), f"Script {script} not executable")
    
    def test_memory_script_execution(self):
        """Test that Python memory scripts can be executed."""
        python_scripts = [
            'get_rightnow_memory.py',
            'get_shortterm_memory.py', 
            'get_longterm_memory.py',
            'get_subconscious_memory.py'
        ]
        
        for script in python_scripts:
            script_path = Path(f".exocortex/scripts/{script}")
            self.assertTrue(script_path.exists(), f"Script {script} not found")
            
            # Test that script can be imported (basic syntax check)
            try:
                result = subprocess.run(['python3', '-m', 'py_compile', str(script_path)], 
                                      capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, f"Script {script} has syntax errors: {result.stderr}")
            except Exception as e:
                self.fail(f"Failed to check script {script}: {e}")

if __name__ == '__main__':
    unittest.main()
```

## Deployment and Distribution

### Package Creation
```bash
#!/bin/bash
# build-package.sh - Create distribution package

VERSION=${1:-"latest"}
PACKAGE_NAME="exocortex-${VERSION}"
BUILD_DIR="build/${PACKAGE_NAME}"

echo "Building exocortex package version $VERSION"

# Create build directory structure
mkdir -p "$BUILD_DIR"/.exocortex/{commands,scripts}
mkdir -p "$BUILD_DIR"/docs
mkdir -p "$BUILD_DIR"/examples

# Copy core files
cp -r .exocortex/commands/* "$BUILD_DIR"/.exocortex/commands/
cp -r .exocortex/scripts/* "$BUILD_DIR"/.exocortex/scripts/
cp .exocortex/.env.example "$BUILD_DIR"/.exocortex/
cp .exocortex/*.md "$BUILD_DIR"/.exocortex/

# Copy documentation
cp docs/* "$BUILD_DIR"/docs/

# Copy examples
cp examples/* "$BUILD_DIR"/examples/

# Copy root files
cp README.md install.sh "$BUILD_DIR"/

# Create archive
cd build
tar -czf "${PACKAGE_NAME}.tar.gz" "$PACKAGE_NAME"
cd ..

echo "Package created: build/${PACKAGE_NAME}.tar.gz"
```

### Version Management
```bash
#!/bin/bash
# version.sh - Version management script

CURRENT_VERSION=$(git describe --tags --abbrev=0 2>/dev/null || echo "v0.1.0")
echo "Current version: $CURRENT_VERSION"

case "$1" in
    "major")
        # Increment major version
        NEW_VERSION=$(echo $CURRENT_VERSION | awk -F. '{$1=$1+1; $2=0; $3=0; print $1"."$2"."$3}' | sed 's/v//')
        ;;
    "minor") 
        # Increment minor version
        NEW_VERSION=$(echo $CURRENT_VERSION | awk -F. '{$2=$2+1; $3=0; print $1"."$2"."$3}' | sed 's/v//')
        ;;
    "patch"|"")
        # Increment patch version (default)
        NEW_VERSION=$(echo $CURRENT_VERSION | awk -F. '{$3=$3+1; print $1"."$2"."$3}' | sed 's/v//')
        ;;
    *)
        echo "Usage: $0 [major|minor|patch]"
        exit 1
        ;;
esac

NEW_TAG="v$NEW_VERSION"

echo "Creating new version: $NEW_TAG"
git tag -a "$NEW_TAG" -m "Release $NEW_TAG"
echo "Tagged: $NEW_TAG"
echo "Push with: git push origin $NEW_TAG"
```

---

*Next: Read [Roadmap](roadmap.md) for planned features and development priorities.*