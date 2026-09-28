# Small local GEPA trial, 2026-09-28

## Decision

Keep the existing prompt. This trial did not produce a usable optimized prompt
or demonstrate better memory quality. Automatic durable-memory updates remain
disabled. The deterministic context refresh is evaluated separately.

## Frozen setup

- Actual GEPA 0.1.4, one reflection attempt.
- Installed local Qwen 2.5 7B, Q4_K_M, used for both reading and reflection.
- Local Ollama chat endpoint, no model tools, no cloud inference.
- Temperature 0, seed 42, 8,192-token context; reader output limited to 1,024
  tokens and reflection to 2,048. One request at a time, four CPU threads.
- Eight training histories, six validation histories and eight held-out
  histories. All are fictional, with reviewed reference dispositions.
- Baseline prompt SHA-256:
  `f77ffe1f983d106d68c3f506a665e3c5af523490dc9adeff63b1dc7e51d6fa6c`.
- Held-out cases were loaded only after the selected prompt was frozen.
- The configured cloud connection failed before using tokens. The local trial
  made 25 model calls: 24 reader calls and one reflection. API cost was $0.

## What happened

The reflection model returned example answer JSON instead of a revised
instruction prompt. The proposal did not improve the development score, so
GEPA kept the original prompt. The selected prompt and baseline hashes match;
the held-out stage therefore evaluated that unchanged prompt once.

The original exact-identifier score was also misleading. It treated labels
such as `index_rebuild` and `index-rebuild` as different answers even when the
destination, disposition and decisive evidence were correct. Both original
aggregate scores were zero; they must not be interpreted as zero semantic
accuracy or as a valid comparison of model quality.

Review of the development outputs also found real errors: the model placed a
rolled-back task under project facts, turned a single pattern observation into
a lesson, and proposed storing quoted prompt-injection text as uncertain
project memory. These are reasons to retain human review.

## Corrections made after the run

- Score disposition and decisive source attribution independently of arbitrary
  subject-label wording. Keep identifier agreement as a separate diagnostic.
- Permit extra verbatim supporting history, and match proposals one-to-one so
  duplicates cannot inflate the score.
- Reject structured answer JSON as an instruction prompt before evaluating it.
- Stop at the reflection limit after a completed iteration. Reuse one held-out
  result when the selected prompt is identical to the baseline.

Using only the already-recorded development outputs, the corrected diagnostic
gave mean F1 of 0.708 on training and 0.833 on validation. This was an analysis
after the run, not a new optimization result, and used no additional model
calls. Held-out outputs were not rescored against the revised evaluator.
No prompt was adopted under either metric.

## Next experiment

The next trial needs a newly frozen evaluator and fresh held-out histories.
The current small public fixture set has served its debugging purpose. Use a
reflection model that reliably returns instruction text, and test realistic
multi-event histories, ambiguous labels and optional historical facts. Review
the reference answers before running it. Results from this local 7B model do
not establish quality for Claude, Codex or a real project's memory.

This report records a bounded diagnostic experiment, not a production-quality
benchmark or evidence that GEPA improves the shipped baseline.
