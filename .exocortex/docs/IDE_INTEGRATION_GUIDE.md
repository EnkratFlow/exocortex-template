# AI and IDE Integration Guide

Every AI surface begins at `AI_START_HERE.md`. The 24 JSON files beneath
`.exocortex/commands/` remain the single command-behavior source. Provider files
are generated thin adapters; they do not copy behavior or expand authority.

## Installation capability is separate

Native command or skill visibility does not mean a provider can install
Exocortex. Installation and updates require a coding agent with local
filesystem and terminal access to the exact target. Chat-only provider
surfaces remain advisory. Use the provider-neutral prompts and platform
boundaries in `.exocortex/docs/AI_INSTALLATION.md`; do not create a
provider-specific installer.

## Provider-native contract

| Surface | Repository adapter | Native invocation | Recorded evidence |
|---|---|---|---|
| Codex | `.agents/skills/{command}/SKILL.md` | `$command` or the skills selector | `compatible`; selector observation pending |
| Claude Desktop 1.24012.1 (0adcae) | `.claude/skills/{command}/SKILL.md` | `/command` | `verified`; all 24 Exocortex commands appeared exactly once |
| Cursor Stable 3.12.30 | `.cursor/skills/{command}/SKILL.md` | `/command` | `verified`; all 24 Exocortex commands appeared exactly once among 72 unique skills |
| GitHub Copilot | `.agents/skills/{command}/SKILL.md` | `/command` where repository skills are supported | `compatible`; exact client version was not captured |
| Kimi Code CLI 1.14.0 | `.agents/skills/{command}/SKILL.md` | `/skill:{name}` | `verified`; all 24 Exocortex entries appeared exactly once among 26 unique skills |
| Kimi Desktop Work 3.1.3 | No Desktop-specific adapter claim | Not advertised | `failed`; 0/24 appeared and exact `/skill:ai-export` produced no match |
| Zed 1.12.0 stable.328 built-in Agent | `.agents/skills/{command}/SKILL.md` | built-in Agent skills selector | `verified`; all 24 Exocortex skills appeared exactly once among 25 unique skills; ACP agents excluded |
| Windsurf | None in the active/default install | Not advertised | `unavailable`; no installed version was tested |
| Generic or unidentified host | `AI_START_HERE.md` and `.exocortex/commands/{command}.json` | Host-dependent; no native-menu claim | Not applicable |

The generated repository set is exactly 72 files: 24 portable Agent Skills, 24
Claude skills, and 24 Cursor skills. Every generated adapter is
manual-only, points to exactly one matching command JSON, and tells the model to
fail closed before unapproved mutation or egress.

## Evidence statuses

- `verified`: the recorded installed version passed complete provider-native
  discovery Human UAT.
- `compatible`: the documented contract and static structure match, but Human
  UAT is partial or pending.
- `failed`: the recorded installed version produced a concrete reproducible
  failure.
- `blocked`: a prerequisite such as authentication prevented Human UAT.
- `unavailable`: no installed local surface exists for Human UAT.

Statuses never transfer across provider, client, adapter, discovery, or
configuration changes. Static generation cannot promote a provider to
`verified`.

## Verification boundary

Run:

```bash
python3 .exocortex/scripts/generate_command_adapters.py --check
```

That deterministically proves names, bytes, and repository paths. It does not
prove a particular installed provider version displayed every entry. Native
menu visibility and collision behavior require bounded Human UAT before that
provider/version is advertised as verified.

## Current limitations and revalidation

The completed Cursor, Claude Desktop, Kimi Code CLI, and Zed checks establish
native visibility only for the exact recorded versions and surfaces. No command
was selected or executed, and no UAT action granted repository authority.

Kimi Desktop Work 3.1.3 is a separate surface from Kimi Code CLI 1.14.0.
Desktop displayed 0/24 project skills, while the isolated CLI displayed every
expected `/skill:{name}` entry exactly once. Neither result transfers to the
other surface.

Codex remains `compatible` until its native desktop selector is observed.
GitHub Copilot remains `compatible` until the exact passing client version is
captured. Cursor 3.6.21's portable-family failure remains historical evidence;
Cursor Stable 3.12.30 is verified only for the dedicated native family. Zed
evidence covers only its built-in Agent; ACP agents remain separate. Windsurf
remains `unavailable`.

## Legacy migration

The old `.cursor/commands/*.md` wrappers and the duplicate Cursor/GitHub
`onboard` persona entries are superseded; the canonical commands themselves are
not removed. An installer may retire one of those paths only when:

1. its generated replacement installed and byte-matches the candidate;
2. the old path is owned by the prior install manifest; and
3. its current bytes still match the prior manifest hash.

Customized or unknown paths are preserved and reported with
`EXOCORTEX_ADAPTER_COLLISION_PRESERVED`. Resolve that warning in a separate,
reviewed target-specific change before claiming collision-free native parity.

The cumulative migration inventory is 51 paths: 26 prior Cursor/GitHub
retirements—24 old Cursor command wrappers plus the duplicate Cursor and GitHub
`onboard` entries—plus 24 Windsurf workflows and `.windsurfrules`. Windsurf paths are
no longer installed. They are removed only when the prior manifest proves
ownership and their bytes still match; customized and unknown paths remain.
The former Cursor `onboard` path is the sole reactivated path: a managed legacy
copy is retired before the current generated Cursor adapter is installed,
while customized or unknown content is preserved.

The Cursor phase hook remains reminder-only. It never creates a save or
checkpoint, selects a model, writes a repository, or contacts an external
system. Global editor-home installation is outside repository installation and
requires a separate system-operation work item.
