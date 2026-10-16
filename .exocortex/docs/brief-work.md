# Task briefs and continuity

A task brief keeps the requested outcome, its source, boundaries and acceptance
criteria available as work moves between sessions and assistants. It can
represent software, a website update, a press release or another deliverable.
A program master brief can contain several tasks; selecting a task does not
replace the larger program or its approvals.

The sole command-flow authority is
[brief-work.json](../commands/brief-work.json), beneath `AI_START_HERE.md`.
This guide describes records and helper interfaces, not additional authority.

## A small workflow

1. Supply the request in conversation or paste a source such as a ticket.
   `/brief-work` drafts objective, audience, owner, approver, deliverables,
   constraints, exclusions, criteria, questions, assumptions and decisions.
   It preserves source text, reference and revision. Missing facts stay open.
2. Approve the bounded local operation and requirements. The helper creates an
   immutable revision and can record the actual requirements approval evidence.
   Creating a brief does not itself record approval.
3. Explicitly select the task. `/work` and `/onboard` reload its exact revision
   and applicable history. `/where` also reports the task and checkout.
4. Do the authorized work. At milestones compare the artifacts against the
   criteria. `/save` links reviewed progress, evidence, decisions and proposed
   lessons to the exact brief revision. It still begins with a chat draft and
   needs applicable local-save authorization.
5. Review each criterion against the deliverables and recorded evidence. Ask
   the owner to accept or reject the result, and accurately record that decision
   in an authorized save. Publication and deployment remain separate actions.

For example, a page update may require the supplied headline, a verified date
and an accessible link. A press release may require source-backed claims and
editor approval. A code change may require a reproduced defect and a passing
regression test. The same process handles all three without hard-coded roles,
accounts, paths or integrations.

## Commands and records

| Surface | Role |
|---|---|
| `/brief-work` | Draft, revise, select, clear selection or prepare evidence review |
| `/brief` | Existing quick read-only status |
| `/work` | Resume the selected task within the overall program |
| `/save` | Link a local narrative to the exact task revision |
| `/onboard`, `/where`, `/handoff` | Reconcile and report task and checkout context |

The stdlib-only helper is `.exocortex/scripts/brief_work.py`. Run from the
project root, or put `--project-root <root>` before the subcommand:

```text
python3 .exocortex/scripts/brief_work.py list
python3 .exocortex/scripts/brief_work.py context
python3 .exocortex/scripts/brief_work.py show page-update
python3 .exocortex/scripts/brief_work.py create page-update --input request.json
python3 .exocortex/scripts/brief_work.py revise page-update --input revised.json --expected <current-sha256>
python3 .exocortex/scripts/brief_work.py approve page-update --expected <sha256> --actor <approver> --evidence <actual-decision-reference>
python3 .exocortex/scripts/brief_work.py select page-update --expected <sha256>
python3 .exocortex/scripts/brief_work.py review page-update
python3 .exocortex/scripts/brief_work.py clear
```

`list`, `context`, `show` and `review` only read. Other operations require
applicable owner authorization. Use the JSON shape in
[task-brief.json](../templates/task-brief.json), validated against
[task-brief.schema.json](../schemas/task-brief.schema.json) and runtime limits.
Replace placeholders with reviewed requirements. The helper rejects unknown
fields, duplicate criterion IDs and credential-shaped or linked input paths.
It never obtains a ticket from an external service.

Portable revisions and approval evidence live under
`.exocortex/planning/briefs/<id>/`. Local selection and the transient write lock
live under `.exocortex/local/briefs/`. Requirements revisions are immutable,
chain their previous digest, and must be edited through a new revision.
Concurrent writers, conflicting histories or unexpected approval files require
reconciliation; no unique record is discarded. A crashed writer may leave a
lock: verify that no writer is active before an explicitly authorized repair.

The active pointer binds the task ID, revision and SHA to the current checkout,
branch and HEAD. A switch or new commit requires explicit reselection. A new
requirements revision makes the old selection stale. `clear` explicitly chooses
no task, leaving all history intact. No command silently chooses the only task.

## Saves and recovery

An authorized task save uses the reviewed body and a UUID allocated once for
that logical save:

```text
bash .exocortex/scripts/create_event.sh --body-file summary.md --brief page-update --brief-sha <sha256> --save-id <stable-uuid>
```

Reusing that ID and identical content returns the original event, including
when the selected task has since changed. Changed content, task references or
an edited original event cause a conflict. A new milestone needs its own ID.
Saves include path-free task and Git scope; unfinished or unpushed work may be
saved. An event does not imply that its changes are present in another checkout.

Exit 3 means the event exists but generated context could not refresh. Preserve
it, resolve the reported issue and run `refresh_rollups.py --apply`; do not
create another save. An explicitly requested `--unscoped` project-wide save
can preserve a narrative while task selection is unresolved, but it deliberately
returns this deferred-refresh result until the owner selects a task or clears
selection. Never clear selection automatically to bypass a continuity gap.

A generated context includes the selected task and labels other-task or older
revision events. Source text is quoted as evidence. It never becomes authority.
The review packet initially marks criteria `not_assessed`: event presence and
test success cannot establish human acceptance, publication or deployment.

## Sharing and limits

In a consuming project, deliberately commit and push portable briefs and events
with the relevant work, then synchronize the other clone. Review its ignore
rules and visibility before sharing. Branch-specific notes remain branch-specific;
Git does not automatically share new saves between working folders or machines.
Non-Git content folders support briefs and saves, but have no Git transport.

The template's public package excludes actual briefs, events and local state.
Template updates preserve consumer planning records. Only the helper, schema,
blank template, generic guide and fictional tests ship. Generated context is
rebuilt for its checkout; copying or symlinking memory directories is not a
substitute for reconciliation.

Approval evidence is unsigned cooperative bookkeeping, not cryptographic proof
of identity, a guarded capability or permission to act. A requirements change
needs another reviewed revision. Criteria assessments and human decisions are
narrative evidence in this first version, not an automated acceptance engine.
Proposed lessons require review before becoming durable memory. There is no
Jira connector, background monitor, automatic cleanup, release or deployment.
Native provider-menu discovery and platform validation remain separate checks.
