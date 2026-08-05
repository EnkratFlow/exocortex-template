# Capability- and cost-aware model routing

## Normative policy

Choose the least-expensive available model that can reliably own the complete
bounded task as the accountable parent. Do not automatically choose either the
largest model, the newest model, or the cheapest advertised model.

The parent must be able to interpret authority, decompose scope, make risk
decisions, integrate delegated results, and validate final evidence. If no
verified available model can do that, stop and request a stronger model, new
evidence, or a narrower task.

Model identifiers and provider mappings are advisory data. They are never
normative protocol pins.

## Evidence planes

Routing uses three separately validated evidence planes:

1. `.exocortex/model-source-registry.json` identifies configured public,
   official sources and their freshness limits. Its coverage claim is
   `configured_official_sources_only`; it does not claim every provider or
   model worldwide.
2. `.exocortex/model-routing-catalog.json` stores reviewed normalized public
   lifecycle and price facts plus measured evaluation profiles. A catalog
   entry alone does not make a model eligible.
3. `.exocortex/local/model-routing/**` stores project-local observations,
   availability, and evaluation evidence. Installation and update never
   create, copy, checksum, or overwrite this protected data plane.

Availability is scoped to `current_surface_session` and binds a non-sensitive
surface ID, version, and freshly generated session ID. Its observation window
is at most 15 minutes. Every route request supplies the exact current tuple
from the active surface independently of the availability file; a different
surface, client version, session, or overlong window fails closed. A session ID
must never be a provider cookie, token, credential, or account identifier.
Production routing also requires the explicit `as_of` timestamp to be within
60 seconds of the runtime's current UTC clock. The tolerance absorbs only
bounded clock and process-launch skew; stale or future timestamps cannot replay
a route. `model_registry.py validate-availability` remains the separate,
deterministic historical evidence validator and does not select a model.

Public-source acquisition is a separately authorized
`explicit_external_read`. Credentials are forbidden. The registry tooling
does not fetch sources, read environment variables, access provider sessions,
or write files. Normalized observations must not retain raw source text,
headers, cookies, authentication material, account identifiers, or free-form
notes.

## Discovery and admission

Use `.exocortex/scripts/model_registry.py` to validate already-acquired,
normalized evidence:

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

`discover` compares normalized observations and returns findings plus
quarantine candidates. The catalog stays bound to the reviewed baseline source
registry; `--candidate-sources` supplies a refreshed acquisition snapshot with
the exact same source IDs, providers, URLs, roles, and refresh policies.
Only retrieval metadata and registry snapshot metadata may advance. This
breaks the refresh/rebind cycle without allowing discovery to redefine an
official source. It performs no network access or mutation and always reports
`auto_activation=false`. A newly observed model is quarantined until a
human-reviewed catalog change and measured evaluation evidence admit it.
Absence from a complete listing means `not_observed`. A partial observation
produces no missing-model finding. Neither case silently means deprecated or
retired.

```bash
python3 .exocortex/scripts/model_registry.py discover \
  --project-root "$PWD" \
  --sources .exocortex/model-source-registry.json \
  --catalog .exocortex/model-routing-catalog.json \
  --candidate-sources .exocortex/local/model-routing/candidate-sources.json \
  --observation .exocortex/local/model-routing/observations/<file>.json \
  --as-of <explicit-UTC-timestamp>
```

The discovery result binds the supplied normalized observation digests. It
also binds the baseline registry and refreshed candidate registry.
Observation fields are role-scoped: model listings and names come only from
`models` sources, lifecycle facts from `lifecycle` sources, and prices from
`pricing` sources. Conflicting facts or duplicate source observations across
input files fail closed. The result is still a proposal and never changes
catalog admission.

Only `eligible` models can route. A route also requires:

- an exact current-surface availability observation;
- fresh official-source evidence and an active lifecycle;
- capability and risk support for the task;
- a matching, unexpired evaluation profile with at least one success; and
- compliance with any cost-per-success ceiling.

Future-dated, stale, expired, unavailable, incomplete, or digest-mismatched
evidence fails closed.

## Routing command and selection

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

Selection is deterministic:

1. exact availability;
2. eligible admission state;
3. fresh source and lifecycle evidence;
4. required capability and risk level;
5. fresh matching evaluation profile;
6. task budget ceiling;
7. lowest measured cost per successful completion; and
8. stable identifier as the tie-break.

Cost per success uses integer micro-units and is calculated from measured total
cost divided by successful attempts, rounded up. Advertised token or request
price is catalog evidence, not a substitute for successful task evidence.

The route result binds the accepted live `as_of` value and the exact
source-registry, catalog, availability, and selected evaluation evidence digests.
It also binds the availability surface ID, version, session ID, and scope, and
reports `normative_model_pin=false`. Re-running with the same bytes and
timestamp while that timestamp remains inside the live clock-skew boundary
converges on the same result; later replay fails closed. Use the separate
deterministic validator for historical evidence inspection.

The packaged catalog is intentionally advisory: version 3.2.0 contains zero eligible models
and no verified evaluation profiles. It therefore cannot route a model as
shipped. Admission requires a separately reviewed,
guarded catalog update with a verified evaluation summary and evidence digest,
plus fresh project-local availability for the exact current surface.

## Routing sequence

1. Classify task complexity, novelty, ambiguity, context size, tool needs, and
   outward effects.
2. Classify privacy, security, data, financial, migration, destructive,
   deployment, and external-action risk.
3. Use deterministic tooling first for Git truth, schemas, searches,
   checksums, tests, and repeatable transformations.
4. Select the least-cost verified capable parent.
5. Keep one accountable parent and no delegate by default. Split only a
   concrete, independently useful bounded task when doing so is expected to
   improve time, cost, or review quality.
6. Delegate each task to the least-cost verified role that can meet its
   acceptance criteria.
7. Keep support lanes read-only unless exact approval grants a writer role.
8. Escalate ambiguity, repeated failure, sensitive data, scope drift, material
   design decisions, or outward action.
9. Return evidence and proposed changes to the parent for integration and
   deterministic verification.
10. Stop duplicate reviews when evidence converges.

## Capability roles

| Role | Use |
|---|---|
| Deterministic tooling | Git truth, validation, hashes, schemas, tests, idempotency |
| Bounded evidence lane | Read-only inventory, comparison, and test mapping |
| Accountable parent | Authority interpretation, planning, integration, risk and gate decisions |
| Guarded writer | One exact approved implementation lane |
| Independent reviewer | Security, privacy, data, migration, architecture, or gate-required review |
| Record formatter | Low-risk narrative formatting from a complete evidence packet |

Provider adapters may map current models to these roles using versioned
availability, capability, reliability, and cost evidence. Latency may be
reported as advisory provider metadata, but it is not a deterministic routing
criterion unless a future reviewed schema binds a measured rule. A provider
name, product, model slug, or permanent highest-model-first rule must not appear
as a protocol requirement.

## Cost controls

- Report parent/delegate routing and ETA before substantial phases.
- Send compact evidence packets instead of full chat history when sufficient.
- Use one accountable parent and no delegate by default; add only the minimum
  useful parallel lanes.
- Use at most one independent reviewer unless a separately identified risk
  requires more than one discipline.
- Do not delegate `/save`, weekly/monthly review, retrospective synthesis, or
  pattern interpretation. The accountable parent owns those narratives.
- Report before starting a newly discovered tool or model phase expected to
  take more than five minutes.
- Do not duplicate converged audits.
- Do not repeat deterministic work already bound to the unchanged exact
  candidate merely because it reached main, a tag, or another status label.
- Use a record formatter only from parent-supplied facts.
- Report material changes in routing, scope, capability, risk, or estimate.

Cost never overrides authority, correctness, security, privacy, or required
independent review.
