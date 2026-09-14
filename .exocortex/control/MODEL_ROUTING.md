# Capability- and cost-aware model routing

## Normative policy

Choose the least-expensive available model that can reliably own the whole bounded task as the accountable parent. Do not automatically choose either the largest model or the cheapest model.

The parent must be able to interpret authority, decompose the scope, make risk decisions, integrate delegated results, and validate the final evidence. If no available model can do that, stop and request a stronger model or narrower task.

## Routing sequence

1. Classify task complexity, novelty, ambiguity, context size, tool needs, and outward effects.
2. Classify privacy, security, data, financial, migration, destructive, deployment, and external-action risk.
3. Use deterministic tooling first for Git truth, schemas, searches, checksums, tests, and repeatable transformations.
4. Select the least-cost capable parent.
5. Split only independently useful bounded tasks.
6. Delegate each task to the least-cost role that can meet its acceptance criteria.
7. Keep support lanes read-only unless the exact approval grants a writer role.
8. Escalate ambiguity, repeated failure, sensitive data, scope drift, material design decisions, or outward action.
9. Return evidence and proposed changes to the parent for integration and deterministic verification.
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

## Provider adapters

Adapters may map currently available models to roles using versioned capability, reliability, latency, and cost metadata. Mappings are advisory and non-normative. A provider name, product, model slug, or permanent highest-model-first rule must not appear as a protocol requirement.

## Cost controls

- Report parent/delegate routing and ETA before substantial phases.
- Send compact evidence packets instead of full chat history when sufficient.
- Use the minimum useful parallel lanes.
- Do not duplicate converged audits.
- Use a record formatter only from parent-supplied facts.
- Report material changes in routing, scope, capability, risk, or estimate.

Cost never overrides authority, correctness, security, privacy, or required independent review.
