# Essential Files Reference

**Last Updated:** [DATE]
**Purpose:** Map of the most important files and their relationships

---

## Project Structure Overview

```
[PROJECT_NAME]/
├── .exocortex/              # Project memory (workflow, decisions, lessons)
│   ├── commands/            # JSON command specs (20 commands)
│   ├── control/             # Interrupts, backlog, roadmap, QA
│   ├── docs/                # System documentation
│   ├── events/              # Append-only work events
│   ├── reference/           # Quick reference files
│   └── scripts/             # Shell and Python automation
├── src/                     # Source code (customize for your project)
├── tests/                   # Test files
└── README.md                # Project readme
```

---

## Source of Truth Files

_Map your project's key files here. Example:_

| File | Purpose | Authority |
|------|---------|-----------|
| _src/index.ts_ | _Entry point_ | _Source of truth for app bootstrap_ |
| _src/config.ts_ | _Configuration_ | _Source of truth for settings_ |

---

## Testing Infrastructure

_Document your test files and what they cover._

| Test File | Purpose | Tests |
|-----------|---------|-------|
| _example.test.ts_ | _Description_ | _Count_ |

---

**Last Updated:** [DATE]
