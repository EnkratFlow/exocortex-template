# AI Roles and Commands

Exocortex does not require a single persona, provider, or named model. The
active AI is an interchangeable actor with one declared role:

- parent: accountable for planning, integration, risk, and gates;
- writer: the single registered executor holding an exact mutation capability;
- reviewer: independent read-only correctness or risk review;
- evidence lane: bounded read-only or deterministic gathering;
- egress executor: separately registered for one exact external operation.

Choose the least-expensive available model capable of the bounded role and
risk. Escalate on evidence, never on brand. No support lane inherits writer or
egress authority.

“Available” means current-surface availability plus fresh, digest-bound source
and measured evaluation evidence. A new or cheaper catalog entry is
quarantined until reviewed; discovery never activates it. The complete
evidence and denial rules are in `.exocortex/control/MODEL_ROUTING.md`.

Commands are defined in the 24 JSON files under `.exocortex/commands/` and are
grouped as daily, memory, planning/review, and system operations. See
`.exocortex/COMMAND_SYSTEM.md` for the index.

Natural-language requests work too, but they cannot bypass the same entry,
work-item, reservation, capability, lifecycle, and egress gates. Modes such as
rapid build, deep analysis, architecture, security, UX, or trading precision
change reasoning emphasis only; they never broaden authority.

Every AI should communicate:

1. exact project, branch/base, work item, revision, and role;
2. what is read-only versus authorized to change;
3. the model-routing reason and material estimate changes;
4. deterministic evidence and unresolved risk;
5. the next separately gated decision.

Recursive improvement is prospective: retrospectives propose new bounded work
items, and humans approve them through the normal lifecycle.
