---
name: onboard
description: Codebase onboarding that reads a project structure, entry points, and context to build working understanding before making changes. Use when starting work on an unfamiliar codebase, switching projects, or when a new agent needs to understand the code.
---

You are onboarding to a codebase. Your goal is to build a working mental model of the project before making any changes. Follow these steps in order.

## Step 1: Project Detection

Read the project root directory tree (filenames only, 2-3 levels deep). Then read whichever of these exist:
- `package.json` or `package-lock.json` (Node/JS/TS)
- `requirements.txt` or `pyproject.toml` or `setup.py` (Python)
- `Cargo.toml` (Rust), `go.mod` (Go), `Gemfile` (Ruby), `pom.xml` (Java)
- `README.md`

From this, identify: language, framework, package manager, approximate project size.

## Step 2: Structure and Config

Read whichever of these exist:
- `Dockerfile`, `docker-compose*.yml`
- `tsconfig.json`, `next.config.*`, `vite.config.*`, `webpack.config.*`
- `.env.example` or `.env.local` (for variable names only, not values)
- `Makefile`, `justfile`, or CI/CD configs (`.github/workflows/`)

Identify: how the project builds, runs, and deploys.

## Step 3: Entry Points and Architecture

Based on what you learned in steps 1-2, read the main entry point files:
- For FastAPI/Flask: the server/app file and router definitions
- For Next.js/React: `app/layout.tsx`, `app/page.tsx`, key route files
- For Node/Express: `index.js`/`server.js` and route definitions
- For any project: the `src/` or `lib/` top-level files

Then scan for:
- API route definitions or endpoint files
- Core service/business logic modules (read the top 2-3 by importance)
- Data models, schemas, or type definitions
- Test directory structure (don't read tests, just note what's covered)

Read no more than 15 source files total. Focus on signatures, exports, and structure over implementation details.

## Step 4: Project Context (if available)

Check for and read any of these that exist:
- `.exocortex/PROJECT_MEMORY.md` (system purpose and constraints)
- `.exocortex/SESSION_CONTEXT.md` (recent work state)
- `.exocortex/LESSONS.md` (known pitfalls)
- `.exocortex/TODO.md` (current task board)
- `.exocortex/reference/ESSENTIAL_FILES.md` (file map)
- `.cursor/rules/*.mdc` (project-specific rules)

If none of these exist, skip this step.

## Step 5: Summary

Display a structured summary:

```
Project: [name]
Stack: [language / framework / key dependencies]
Structure: [how source is organized]
Entry points: [main files]
Key modules: [core business logic areas]
Data: [database, storage, or state management approach]
Deployment: [how it runs in production, if detectable]
Context: [current work state from exocortex, or "no project memory found"]

Ready to work. What do you need?
```

## Constraints

- Read-only. Do not create, modify, or delete any files.
- Do not read .env files with actual secrets. Only read .env.example.
- Cap at ~20 file reads total across all steps.
- Skip node_modules, .git, __pycache__, dist, build, .next directories.
- If the project is a monorepo, identify the sub-projects and ask which one to focus on.
