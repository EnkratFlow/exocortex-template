# Exocortex Documentation

## Overview

Exocortex is a project-local memory, delivery, and multi-AI entry protocol for
software repositories. The repository owns its history and approval gates;
models and providers are interchangeable workers.

## Table of Contents

### Core Documentation
- [**Vision & Philosophy**](docs/vision.md) — Why Exocortex exists
- [**Architecture**](docs/architecture.md) — System design and data planes
- [**Getting Started**](docs/getting-started.md) — Installation and orientation
- [**Install with a coding AI**](docs/AI_INSTALLATION.md) — Copy-paste
  clean-install and existing-update prompts
- [**User Guide**](docs/user-guide.md) — Day-to-day usage

### Technical Documentation
- [**Memory System**](docs/memory-system.md) — Project-local memory tiers
- [**Command System**](COMMAND_SYSTEM.md) — Canonical JSON commands
- [**Event System**](docs/event-system.md) — Append-only narrative events
- [**IDE Integration**](docs/IDE_INTEGRATION_GUIDE.md) — Provider adapters
- [**Upgrade Manifest**](docs/UPGRADE_MANIFEST.md) — Code/data boundaries
- [**Model Routing**](control/MODEL_ROUTING.md) — Source freshness,
  quarantine, availability, and measured cost-per-success

### Development
- [**Implementation Guide**](docs/implementation.md) — Installing and evolving
  the protocol
- [**Current Status**](docs/status.md) — What is ready, in progress, blocked,
  and next
- [**Roadmap**](docs/roadmap.md) — Planned work and evidence status
- [**Repository contributing guide**](../CONTRIBUTING.md) — Deterministic
  development and review expectations

---

## Quick Start

For a new or existing repository, use the pinned local installer/update path in
the root [`README.md`](../README.md). A coding AI with local terminal access can
operate it using the copy-paste prompts in
[`docs/AI_INSTALLATION.md`](docs/AI_INSTALLATION.md).

Never manually copy a partial template, create a credential file as part of
installation, request an unpinned `latest`, or pipe a remote installer into a
shell. Rehearse in a sanitized disposable fixture, then use one named-target
local-delivery decision to create a clean isolated Git worktree, install,
verify, record the permitted local handoff, and release the writer; direct
installation in a shared or primary checkout is unsupported. Internal
reservations and technical capabilities are not separate human approvals.
After a verified installation, open a new AI session and ask it to read
`AI_START_HERE.md`, then use `/work` for read-only orientation.

## Key Features

- **Project-owned memory** — Durable local context across AI providers
- **Provider-neutral entry** — One canonical orientation and authority contract
- **Guarded delivery** — Four human-facing business gate classes, one writer,
  exact internal capabilities, and deterministic evidence
- **Safe upgrades** — Protected project data, dry runs, rollback, and idempotency
- **Freshness-gated routing** — Official-source catalog proposals remain
  advisory until separately reviewed evaluation and local availability admit them
- **Deny-by-default egress** — Nothing synchronizes externally without a
  separate destination-specific approval

---

*Root coordinates. Projects remember. Providers remain interchangeable.*
