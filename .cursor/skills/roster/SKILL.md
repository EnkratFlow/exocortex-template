---
name: roster
description: Skill roster that helps select the right specialist skill for the current task. This skill is always relevant and should be consulted when the task would benefit from specialist expertise. Use proactively at the start of complex tasks.
---

<!-- EXOCORTEX_ENTRY: public-v2 -->
Read `AI_START_HERE.md` before substantive action. It is the canonical, provider-neutral entry contract. Then apply this adapter only within the authority and scope resolved there.
<!-- /EXOCORTEX_ENTRY -->


## Available Specialist Skills

When the task would benefit from specialist expertise, load the appropriate skill:

### Build

| Skill | Specialist | Use for |
|---|---|---|
| **architect** | MARCUS | System design, API contracts, service boundaries, scaling decisions |
| **engineer** | ARIA | Code quality, patterns, refactoring, tech debt, implementation review |
| **devops** | DEVLIN | Docker, CI/CD, VPS, nginx, deployment, infrastructure |
| **sre** | SABLE | Observability, health checks, failure modes, alerting, logging |
| **security** | - | Auth, secrets, threat models, data handling, prompt injection |
| **ai-architect** | DR. NOVA | RAG pipelines, embeddings, prompts, model routing, agent design |

### Product

| Skill | Specialist | Use for |
|---|---|---|
| **product-manager** | - | Requirements, MVP, prioritization, user stories, trade-offs |
| **project-planner** | - | Estimation, sequencing, risk, dependencies, roadmaps |
| **ux-designer** | QUINN | UI review, cognitive load, user flows, information architecture |
| **cx-strategist** | SIERRA | Customer journey, onboarding, retention, trust, product experience |
| **behavioral** | DR. REED | Habit loops, nudge design, decision fatigue, engagement patterns |

### Quality

| Skill | Specialist | Use for |
|---|---|---|
| **qa-strategist** | - | Test strategy, coverage analysis, regression planning, test design |
| **technical-writer** | - | User docs, API docs, guides, READMEs, architecture docs |
| **data-engineer** | CADEN | Data pipelines, ETL, schemas, signal extraction, data quality |

### Strategy

| Skill | Specialist | Use for |
|---|---|---|
| **chief-of-staff** | - | Strategic planning, cross-project coordination, priority alignment |
| **deep-agent** | - | Plan-first analysis: restate, assumptions, scope, plan before acting |

### Orientation

| Skill | Specialist | Use for |
|---|---|---|
| **onboard** | - | Read and understand a codebase before starting work |

## Selection Rules

- Match the skill to the primary concern of the task
- For tasks spanning multiple domains, load the most relevant skill first
- For security-sensitive work, always include the security skill
- When uncertain about approach, load deep-agent to plan first
