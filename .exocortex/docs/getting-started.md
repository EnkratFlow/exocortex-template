# Getting Started

## Quick Setup (5 minutes)

### 1. Initialize the exocortex
```bash
# Create the directory structure
mkdir -p .exocortex/{events,commands,scripts}

# Copy the core scripts (adjust paths to your exocortex installation)
cp -r /path/to/exocortex/scripts/* .exocortex/scripts/
cp -r /path/to/exocortex/commands/* .exocortex/commands/

# Make scripts executable
chmod +x .exocortex/scripts/*.sh
```

### 2. Configure AI providers
```bash
# Create environment file
echo "OPENAI_API_KEY=your_openai_key_here" > .exocortex/.env
echo "ANTHROPIC_API_KEY=your_anthropic_key_here" >> .exocortex/.env
```

### 3. Set up AI assistant integration
Copy this to your `.cursorrules` file (or equivalent for your AI assistant):

```
# Exocortex Integration
Load .exocortex/COMMAND_SYSTEM.md to understand available commands

When I type a command starting with "/", check if it exists in .exocortex/commands/
If found, execute the steps from the JSON spec in order
Auto-verify success messages and provide brief command completion status

Available commands: /work, /drill, /shortterm, /longterm, /subconscious
Use /work at the start of sessions to load recent context
```

### 4. Create your first event
```bash
# Start a work session
.exocortex/scripts/create_event.sh "Setting up exocortex"

# Or let it auto-detect your work
.exocortex/scripts/detect_work_state.sh
```

### 5. Test the system
In your AI assistant, type:
```
/work
```

You should see:
- ✓ Context loaded
- ✓ Memory tiers processed  
- ✓ Work state detected
- Brief summary of recent activity

## Detailed Setup

### Prerequisites
- **AI Assistant** with `.cursorrules` support (Cursor, VS Code with Copilot, Claude Desktop)
- **API Keys** for OpenAI and/or Anthropic  
- **Python 3.7+** for memory processing scripts
- **Git repository** (optional but recommended for multi-machine sync)

### File Structure After Setup
```
your-project/
├── .cursorrules              # AI assistant configuration
├── .exocortex/
│   ├── .env                  # API keys (keep private!)
│   ├── commands/             # Command specifications
│   │   ├── work.json
│   │   ├── drill.json
│   │   └── ...
│   ├── scripts/             # Processing scripts
│   │   ├── generate_context.sh
│   │   ├── get_rightnow_memory.py
│   │   ├── get_shortterm_memory.py
│   │   ├── get_longterm_memory.py
│   │   ├── get_subconscious_memory.py
│   │   ├── drill_memory.py
│   │   ├── create_event.sh
│   │   └── ...
│   ├── events/              # Event storage (will be created)
│   └── *.md                 # Context and documentation files
```

### API Key Setup

**Option 1: OpenAI (recommended for cost)**
1. Get API key from https://platform.openai.com/api-keys
2. Add to `.exocortex/.env`: `OPENAI_API_KEY=sk-...`
3. Approximate cost: ~$0.0001 per memory operation

**Option 2: Anthropic (fallback)**  
1. Get API key from https://console.anthropic.com/  
2. Add to `.exocortex/.env`: `ANTHROPIC_API_KEY=sk-ant-...`
3. Approximate cost: ~$0.001 per memory operation

**Option 3: Both (recommended)**
Scripts will use OpenAI by default, fallback to Anthropic if needed.

### Multi-Machine Setup

The exocortex works across multiple development environments:

**Method 1: Git sync (recommended)**
```bash
# Add to .gitignore
echo ".exocortex/.env" >> .gitignore  # Keep API keys private
echo ".exocortex/SESSION_CONTEXT.md" >> .gitignore  # Regenerated automatically

# Commit everything else
git add .exocortex/
git commit -m "Add exocortex setup"
```

**Method 2: Manual sync**
Copy the `.exocortex/` directory (excluding `.env`) to other machines, then configure API keys locally.

## First Commands

### /work - Load Context
Your main command for starting work sessions:

```
/work
```

**What it does:**
- Generates recent context (last 7 days)  
- Processes memory tiers automatically
- Detects current work state (git status, recent files)
- Provides brief of what you were working on

**Example output:**
```
✓ Context generated (15 events from last 7 days)
✓ Right now memory processed  
✓ Work state detected (3 modified files, main branch)
✓ Brief: Continuing work on exocortex documentation system
```

### /drill \<topic> - Deep Dive
Search all events for a specific topic:

```
/drill authentication system
```

**What it does:**
- Searches ALL events (no time limit) for the topic
- Reconstructs chronological development history  
- Shows key decisions and implementation details
- Provides cross-references to related work

### /shortterm - 7-31 Day Memory  
See what you worked on in the past month:

```
/shortterm
```

**What it does:**
- Analyzes events from 7-31 days ago
- Groups work into themed blocks  
- Shows how projects evolved
- Identifies patterns and recurring topics

## Common Workflows

### Daily Startup Routine
```
1. Type "/work" to load recent context
2. Review what was happening last time you worked
3. Start coding/writing/designing
4. System automatically creates events as you work
```

### Weekly Review
```
1. Type "/shortterm" to see the past 7-31 days
2. Use "/drill <project>" for specific deep-dives
3. Review patterns and themes that emerged
4. Plan next week's priorities
```

### Project Archeology
```
1. Use "/drill <project name>" to reconstruct history
2. Use "/longterm" to see monthly arcs
3. Use "/subconscious" to detect recurring patterns
4. Export findings to project documentation
```

### Debugging Memory Issues
```bash
# Check event creation
ls -la .exocortex/events/ | tail -10

# Test memory script manually  
python3 .exocortex/scripts/get_rightnow_memory.py

# Regenerate context
.exocortex/scripts/generate_context.sh

# Check AI integration
cat .exocortex/.env  # Ensure API keys are set
```

## Tips for Success

### 1. Event Quality
**Good events** describe:
- What you accomplished  
- Key decisions made
- Problems encountered
- Context about why you made certain choices

**Example:**
```markdown
# Trading Journal UI Refactor

## What I Did
- Simplified the position entry form by removing redundant fields
- Added client-side validation for price/quantity inputs  
- Fixed the date picker to default to current date

## Key Decisions
- Chose to use Zod for validation instead of manual checks
- Decided against real-time price validation due to API costs

## Problems
- Vite dev server keeps crashing with TypeScript errors
- Need to investigate the build process

## Context  
- Working toward MVP launch next week
- Focus on core functionality over nice-to-haves
```

### 2. Command Usage Patterns
- Use `/work` at the beginning of every session
- Use `/drill` when you can't remember how something works
- Use `/shortterm` for weekly reviews  
- Use `/longterm` for quarterly planning
- Use `/subconscious` when you feel stuck or need fresh perspective

### 3. Multi-Project Setup
You can have multiple exocortex installations:

```
~/projects/
├── trading-journal/.exocortex/     # Project-specific
├── personal-site/.exocortex/       # Project-specific  
└── .exocortex/                     # Global (for general development)
```

Commands will use the closest `.exocortex/` directory in the directory tree.

### 4. Performance Optimization
- Archive events older than 6 months if you have thousands
- Use `/drill` for specific searches instead of reading all events manually
- The system is designed to be fast with hundreds of events

---

## Troubleshooting

### Command not recognized
- Check that `.cursorrules` includes the exocortex integration
- Verify the command exists in `.exocortex/commands/command.json`
- Ensure your AI assistant supports custom commands

### Scripts not running
- Check file permissions: `chmod +x .exocortex/scripts/*.sh`  
- Verify Python is available: `python3 --version`
- Check API keys: `cat .exocortex/.env`

### Memory scripts failing
- Test API connectivity manually
- Check for rate limiting (wait a few minutes)  
- Verify event files exist: `ls .exocortex/events/`
- Try running scripts individually to isolate issues

### Events not being created
- Check if `create_event.sh` is executable
- Verify the events directory exists
- Check git status (some integrations depend on git)

**Still having issues?** Check the [troubleshooting guide](troubleshooting.md) or [open an issue](contributing.md).

---

*Next: Read the [User Guide](user-guide.md) for detailed usage patterns and advanced features.*