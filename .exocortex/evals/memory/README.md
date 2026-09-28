# Memory curator GEPA pilot

Status: infrastructure ready; one small local-model trial completed without a
usable improvement. See [the trial findings](local-pilot-2026-09-28.md).
There is no paid optimization or real-model improvement claim.
The baseline is `../../prompts/memory-curator.md`. GEPA 0.1.4 is optional;
ordinary event saves, refreshes, proposal previews and recorded-output scoring
use only Python's standard library.

## Purpose

Optimize how a model interprets events into sourced lessons, decisions, tasks
and patterns. The model must distinguish completed, cancelled, blocked,
rolled-back and uncertain work. The evaluator, output schema, source history,
reference answers and allowed target files are fixed.

The reader receives only the candidate prompt and event text. The scorer keeps
the answer key. Reflection can see training mistakes and reference answers;
validation controls candidate selection. Final held-out histories load only
after a candidate is frozen. No candidate is automatically installed or applied.

## Data and scoring

- `train.json`: eight fictional development histories.
- `validation.json`: six separate histories for candidate selection.
- `holdout.json`: eight separate histories for a final comparison.

Items use stable subject keys, allowed target/status combinations and verbatim
source quotations. The score is F1 over target, status and required decisive
source events. Additional verbatim supporting context is allowed. Matching is
one-to-one, so duplicate proposals lose precision. Model-chosen identifiers are
checked for valid syntax; exact reference-label agreement is reported separately
and does not determine the score. Invalid schemas or fabricated quotations are
hard failures. This rubric checks dispositions and attribution, not meaningful
label wording, prose quality or every possible semantic error. Real-history
evaluation requires reviewed answers and adjudication of ambiguous cases.

Structured example answers are refused as candidate instruction prompts. Reaching
the reflection-call limit stops at an iteration boundary, retaining completed
work. Identical baseline/selected prompts share one held-out evaluation and
cannot appear to improve because of sampling variation.

The final candidate must beat the baseline using the same reader model and
configuration, have no hard failures and no per-case regression. The report
contains aggregate results and hashes, not new reflection feedback. Repeated
testing consumes the holdout; use new unseen histories for another cycle.
The tiny public fixture set is an engineering test, not a generalization study.

## Zero-cost checks

```bash
python3 .exocortex/scripts/memory_gepa.py plan
python3 -m unittest discover -s tests -p 'test_memory_*.py'
```

To check the real GEPA API with fake model callables in a disposable environment:

```bash
python3 -m venv /tmp/exocortex-memory-gepa-pilot
/tmp/exocortex-memory-gepa-pilot/bin/pip install --no-deps \
  -r .exocortex/evals/memory/requirements.txt
/tmp/exocortex-memory-gepa-pilot/bin/python -m unittest discover \
  -s tests -p 'test_memory_gepa.py'
```

Those tests deliberately use reference-derived fake outputs to exercise the
optimizer. Their scores are not evidence of LLM improvement.

`memory_gepa.py score --responses outputs.json` can score already recorded
development outputs, mapped by case id. It never calls a model or loads holdout.

## An actual optimization run

Before a paid run, name the reader and reflection models, fixed configurations,
data destination, call caps and total approved budget. Quote current provider
prices and estimate token usage separately. No default provider or credentials
are configured by this pilot.

For example, these are illustrative spending caps, not a model price estimate:

```bash
python3 .exocortex/scripts/memory_gepa.py plan \
  --max-reader-calls 40 --max-reflection-calls 8 \
  --reader-cap-usd 0.02 --reflection-cap-usd 0.10
```

That reserves at most $1.60 for optimization; a final 16-call baseline/candidate
holdout comparison would need a separate $0.32 cap at the same reader limit.
The model bridge must enforce token/cost limits at its own provider boundary.
The pilot reserves each full call cap before invoking the bridge, including
failed attempts; it does not claim to meter the provider's bill.

The Python API in `../../scripts/memory_gepa.py` exposes:

- `Budget(approved, reader_cap, reflection_cap, max_reader_calls, max_reflection_calls)`
  with Decimal dollar values.
- `optimize(reader, reflector, budget)`, where
  `reader(prompt, events, cap)` returns JSON and `reflector(prompt, cap)` returns
  a complete prompt in a fenced code block. Supply authorized callables only.
- `evaluate_holdout(reader, budget, baseline, candidate)` after freezing and
  reviewing the selected candidate. Freeze the reader configuration as well.

GEPA has no trackers, callbacks, run directory, subprocess adapter or built-in
provider in this integration. Save run reports only to ignored local storage
when authorized, with exact prompt, dataset and model/configuration hashes.
Review any winning prompt for memorized examples and source fidelity before
adoption. Building a provider bridge and conducting that measured paid pilot
remain separate work.

References: [GEPA source](https://github.com/gepa-ai/gepa),
[GEPA guidance](https://gepa-ai.github.io/gepa/guides/faq/).
