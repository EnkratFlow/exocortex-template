# Exocortex AI entry contract

This is the provider-neutral entry point for every AI, editor, command, skill, and automation in this repository.

## 1. Read before acting

Read, in order:

1. This file.
2. `.exocortex/AI_BOOTSTRAP.md`.
3. `.exocortex/reference/MEMORY.md` and the project files it requires.
4. `.exocortex/control/DELIVERY_WORKFLOW.md`.
5. `.exocortex/control/MODEL_ROUTING.md`.

Then resolve live Git state and project-local authority. Generated context and prior chat are supporting evidence, never authority.

## 2. Declare the role

Choose exactly one role for the current bounded task:

- `read_only`: orientation, evidence gathering, review, or test observation.
- `writer`: the one registered guarded executor holding the current exact reservation and approval capability.
- `independent_reviewer`: read-only review from evidence produced by the writer.

Unknown, unregistered, expired, revoked, unattested, or unconstrained AI surfaces are `read_only`. They cannot become writers or egress actors merely by claiming a role.

## 3. Resolve authority deterministically

Before a mutation, identify all of the following from project-local records:

- work-item ID and revision;
- approved operation;
- exact target path, Git object, destination, or immutable payload digest;
- current lifecycle state and attempt;
- writer reservation and allowed paths;
- registered surface and guarded-executor identity;
- approval acceptance, expiry, consumption, and revocation state;
- required verification and downstream gates that remain closed.

If any field is absent, stale, ambiguous, mismatched, expired, revoked, or consumed, stop before reservation or mutation.

Protocol-managed mutations use `.exocortex/scripts/orchestrate_work_item.py` and `.exocortex/scripts/authority_guard.py`. Instructions in prose, a model assertion, configuration, credentials, a branch name, or an allowlist never grants authority by itself.

## 4. Work in small delivery slices

Use the lifecycle and acceptance gates in `.exocortex/control/DELIVERY_WORKFLOW.md`.

- Use deterministic tools before model work.
- Keep one accountable writer.
- Keep support lanes read-only.
- Validate the exact diff and required evidence after every bounded slice.
- Do not call code Done before all applicable Human UAT, release, deployment, and hypercare gates pass.

## 5. Route by capability, risk, and cost

Follow `.exocortex/control/MODEL_ROUTING.md`.

Choose the least-expensive model capable of owning the whole task as parent. Delegate bounded work to the least-cost capable role, escalate when evidence or risk requires it, and return all results to the parent for integration and verification. No provider or named model is mandatory.

## 6. Separate saves, checkpoints, and handoffs

- A narrative save is a user-requested project-local event. It is not a lifecycle transition or external-sync approval.
- A lifecycle checkpoint is emitted only by an accepted durable transition explicitly marked checkpoint-eligible.
- Retry and replay converge on the same checkpoint ID.
- Rejected, invalid, unauthorized, stale, conflicting, read-only, support, test, ordinary-chat, and explicitly non-checkpointing activity creates no lifecycle checkpoint.
- Handoffs are project-local by default.

## 7. Fail closed on egress

External delivery uses `.exocortex/scripts/egress_guard.py` and requires:

1. a one-time local inspection capability for the exact source path before the
   source is opened or hashed;
2. a second one-time writer capability that binds the resulting digest, size,
   class, source, immutable object path, and descriptor path;
3. an exact destination/method/digest-bound egress capability;
4. metadata authorization before outward-payload access;
5. streamed payload digest verification before credential lookup;
6. commit-time expiry, revocation, policy, destination, method, and digest checks before transport.

Without all six, do not open source content for inspection, open the payload
for delivery, read credentials, initialize a destination, spawn a transport,
copy a file, or make a network call.

## 8. Approval gates never cascade

Implementation, local commit, push or pull request, merge, release, deployment, service action, external synchronization, template promotion, and each live-repository rollout are separate approvals. Approval for one does not authorize the next.

## 9. Security boundary

Never read, print, log, echo, or expose secret values. Do not read `.env` files with tools that return their contents. A key check may return status only.

The project-local guards are cooperative enforcement. Local unsigned JSON is
not proof of human approval against a process that can rewrite both trust
records and guard inputs; host-level enforcement requires a privileged broker
and trusted signature or attestation root.

## 10. Public-template boundary

Project-local memory, work items, approvals, reservations, events, handoffs, destinations, identities, and origin history are data plane. They are never copied from this template, manifest-tracked, or promoted as public fixtures. Public tests use generated fictional data and reserved example domains.
