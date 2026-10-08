# Orchestration: the right model at the right cost

This guide replaces the retired model-routing catalog and registry. It holds
the judgment rules /orchestrate and every agent use to pick models. There is
no catalog to refresh and nothing here expires.

## Normative policy

Use the correct model for the job while keeping the expected cost of a correct
outcome in mind. The accountable parent makes that judgment for itself and for
every subagent. Routine model selection is not a human approval gate.

Choose a parent that can reliably understand authority, frame the complete
bounded outcome, make risk decisions, integrate delegated results, and verify
the final evidence. The cheapest advertised model is not cost-effective if it
needs repeated steering or produces weak verification; the strongest model is
not cost-effective when a lower-cost model can close the same evidence loop.

Before a substantial phase, announce the parent, any delegated lanes, the
reason for the route, and an ETA. This is a visibility report, not a request
for permission to use the selected model. Re-route autonomously when risk,
ambiguity, tool access, evidence, or repeated failure changes the judgment,
then report the material change.

Provider names and model identifiers are illustrative adapter data, never
permanent protocol pins. Explicit owner exclusions and privacy constraints are
hard routing inputs; price alone is not.

## Parent judgment

Evaluate the whole task before selecting a route:

1. complexity, novelty, ambiguity, context size, and expected duration;
2. tool access and whether the model can observe the result it must verify;
3. security, privacy, financial, data, migration, destructive, deployment,
   and external-action risk;
4. the quality and independence of the required verification loop;
5. current availability, demonstrated reliability, latency when it matters,
   and expected total cost through a correct result; and
6. explicit owner or project constraints, including excluded models or data
   boundaries.

Use deterministic tools first for Git truth, schemas, searches, checksums,
tests, and repeatable transformations. Give the selected model a clear goal,
boundaries, observable exit criteria, and the evidence it needs. Do not turn
the routing guide into a step-by-step script that prevents useful model
judgment.

Escalate capability when any of these is true:

- the work is novel, ambiguous, long-horizon, or architecture-heavy;
- it touches secrets, privacy, security, financial calculations, migrations,
  destructive behavior, or outward effects;
- the current model cannot use the necessary tools or close the verification
  loop;
- two materially similar attempts fail or require substantial parent repair;
  or
- the expected cost of correction now exceeds the cost of a stronger model.

De-escalate when the remaining slice is bounded, independently checkable, and
lower risk. Never lower the verification standard merely to use a cheaper
model.

## Delegation and review

Keep one accountable parent and no delegate by default. Spawn a subagent only
for a concrete bounded outcome that can improve elapsed time, expected cost,
context quality, or independent review. Apply the same full routing judgment
to each subagent; a worker is not automatically assigned the cheapest tier.

- The parent owns decomposition, authority interpretation, integration,
  verification, and the final answer.
- Keep one registered guarded writer. Support and review lanes remain read-only
  unless exact project authority grants otherwise.
- Send compact evidence packets and explicit acceptance criteria rather than
  an entire conversation when sufficient.
- Use one independent reviewer by default when risk requires review. Add a
  second only for a genuinely separate named discipline, such as security plus
  numerical-model validation.
- Stop duplicate lanes when evidence converges.
- Do not delegate `/save`, weekly or monthly review, retrospective synthesis,
  or pattern interpretation; the accountable parent owns those narratives.

## Cost and communication controls

- Report route and ETA before substantial phases; do not ask for routine model
  approval.
- Report a material change in route, scope, risk, tools, or estimate.
- Use the minimum useful number of parallel lanes, not a fixed agent count.
- Do not repeat deterministic work already bound to the unchanged exact
  candidate.
- Treat advertised price as input evidence, never as proof of task-level
  economy.
- Cost never overrides authority, correctness, security, privacy, owner model
  exclusions, or required independent review.
