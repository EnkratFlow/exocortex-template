# Exocortex Documentation

## Overview

The **Exocortex** is a neuroscience-inspired external memory system for software developers. It provides persistent context, intelligent memory retrieval, and workflow automation designed to eliminate the cognitive overhead of project re-entry and context switching.

## Table of Contents

### Core Documentation
- [**Vision & Philosophy**](vision.md) - Why the exocortex exists and its guiding principles
- [**Architecture**](architecture.md) - System design, components, and data flows  
- [**Getting Started**](getting-started.md) - Installation and initial setup
- [**User Guide**](user-guide.md) - Day-to-day usage patterns

### Technical Documentation
- [**Memory System**](memory-system.md) - Four-tier memory architecture and AI curation
- [**Command System**](command-system.md) - JSON-based command specifications and execution
- [**Event System**](event-system.md) - Append-only event storage and context generation
- [**API Reference**](api-reference.md) - Script interfaces and command specifications

### Development
- [**Implementation Guide**](implementation.md) - Adding exocortex to new projects
- [**Roadmap**](roadmap.md) - Planned features and development timeline  
- [**Research Foundation**](research.md) - Neuroscience research that informed the design
- [**Contributing**](contributing.md) - Development guidelines and architecture decisions

---

## Quick Start

```bash
# 1. Initialize exocortex in your project
mkdir .exocortex
cp templates/* .exocortex/

# 2. Set up API keys for AI memory curation
echo "OPENAI_API_KEY=sk-..." > .exocortex/.env

# 3. Start working 
/work
```

## Key Features

- **Zero Context Loss** — Never lose track of what you were working on
- **Intelligent Memory** — AI-curated recall across multiple time scales  
- **Workflow Automation** — Command system for consistent development patterns
- **Multi-Machine Sync** — Work seamlessly across different environments
- **Neuroscience-Based** — Memory architecture based on human cognition research

---

*The exocortex transforms your development experience from "what was I doing?" to "here's exactly where we left off."*