# Capability- and cost-aware model routing

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

## Advisory capability bands

These bands describe work, not vendors. Current adapters may map product
families to them using observed capability, tool access, privacy, reliability,
and cost.

| Band | Appropriate use |
|---|---|
| Bounded utility | Deterministic, low-risk inventory or formatting with complete inputs and exact checks; use only when allowed by owner policy. |
| General engineering | Normal implementation, diagnosis, reproduction, and verification with established patterns. |
| Frontier reasoning | Novel architecture, difficult debugging, security/privacy work, financial or numerical correctness, migrations, and high-cost failure modes. |
| Long-horizon | Work that must sustain a verified loop over an unusually long task and has evidence that the specialized runtime improves the outcome. |

Illustrative current adapter mappings may place Luna-class models in bounded
utility, Terra- or Sonnet-class models in general engineering, Sol- or
Opus-class models in frontier reasoning, and Fable-class runtimes in
long-horizon work. These are examples only. A named model may move bands as the
surface, tools, evaluations, price, or owner policy changes. Open-source and
future models map by demonstrated equivalent capability, never by brand or
parameter count alone.

## Optional empirical routing verifier

The parent-judgment policy above is the default and remains usable when no
formal catalog entry is eligible. The repository's deterministic routing
machinery is an optional empirical verifier for environments that maintain the
required evidence; it is not a prerequisite, authority source, or human
approval gate.

The evidence planes are:

1. `.exocortex/model-source-registry.json`, covering configured official
   sources only (`configured_official_sources_only`), not every model
   worldwide;
2. `.exocortex/model-routing-catalog.json`, containing reviewed normalized
   lifecycle, price, and evaluation records; and
3. protected `.exocortex/local/model-routing/**` observations, availability,
   and local evaluation evidence, which installation and update never copy or
   overwrite.

Public-source acquisition is a separately authorized
`explicit_external_read`. Credentials are forbidden. The registry tooling
validates already-acquired normalized evidence; it does not fetch sources,
read environment variables, use provider sessions, or write files.

The packaged catalog intentionally has zero eligible models and no verified
evaluation profiles. Therefore the formal `route` command cannot select a
model as shipped. That result means "formal verifier unavailable," not "the
parent may not exercise judgment." Discovery never activates a model.

### Discovery and admission

```bash
python3 .exocortex/scripts/model_registry.py validate-sources \
  --project-root "$PWD" \
  --sources .exocortex/model-source-registry.json

python3 .exocortex/scripts/model_registry.py validate-catalog \
  --project-root "$PWD" \
  --sources .exocortex/model-source-registry.json \
  --catalog .exocortex/model-routing-catalog.json

python3 .exocortex/scripts/model_registry.py plan-refresh \
  --project-root "$PWD" \
  --sources .exocortex/model-source-registry.json \
  --catalog .exocortex/model-routing-catalog.json \
  --as-of <explicit-UTC-timestamp>
```

`discover` compares normalized observations with the reviewed catalog and
returns quarantine proposals with `auto_activation=false`. A newly observed
model requires a reviewed catalog change and measured evaluation evidence.
Absence from a complete listing means `not_observed`. A partial observation
produces no missing-model finding. Neither result silently means deprecated.

```bash
python3 .exocortex/scripts/model_registry.py discover \
  --project-root "$PWD" \
  --sources .exocortex/model-source-registry.json \
  --catalog .exocortex/model-routing-catalog.json \
  --candidate-sources .exocortex/local/model-routing/candidate-sources.json \
  --observation .exocortex/local/model-routing/observations/<file>.json \
  --as-of <explicit-UTC-timestamp>
```

The discovery result binds the supplied normalized observation digests and the
baseline plus candidate registry snapshots. Conflicting facts, duplicate
source observations, and role-mismatched facts fail closed.

### Formal route command

Only `eligible` models can route through the optional verifier. It additionally
requires an exact current-surface observation, fresh source and lifecycle
evidence, matching capability and risk, an unexpired evaluation profile with a
success, and compliance with any cost-per-success ceiling.

Availability is scoped to `current_surface_session`, binds a non-sensitive
surface ID, version, and freshly generated session ID, and lasts at most 15
minutes. The caller supplies the exact current tuple independently of the
availability file. The explicit `as_of` timestamp must be within 60 seconds of
the runtime's UTC clock.

```bash
python3 .exocortex/scripts/orchestrate_work_item.py route \
  --project-root "$PWD" \
  --task .exocortex/local/model-routing/task.json \
  --sources .exocortex/model-source-registry.json \
  --catalog .exocortex/model-routing-catalog.json \
  --availability .exocortex/local/model-routing/availability.json \
  --as-of <current-UTC-timestamp-within-60-seconds> \
  --current-surface-id <surface-id> \
  --current-surface-version <surface-version> \
  --current-surface-session-id <non-sensitive-session-id>
```

The optional verifier ranks eligible candidates by exact availability, fresh
admission evidence, capability/risk fit, evaluation match, budget, and lowest
measured cost per successful completion. Cost per success is measured total
cost divided by successful attempts, rounded up in integer micro-units. The
result binds its evidence digests and reports `normative_model_pin=false`.
`model_registry.py validate-availability` remains a separate deterministic
historical validator and makes no selection.

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
