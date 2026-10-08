# ADR 004 — evidence-first advisory AI

Decision: use evidence extraction followed by deterministic clarification logic for
the accepted lab recommendation flow. Phase 6 evidence records provider readiness;
this ADR does not independently assert a provider passed.

## Problem and resulting behavior

The initial model output generated a missing-information list directly. It sometimes
asked for already-present symptoms and once asked for details about an injected
permission-bypass instruction. Schema validity and correct category were insufficient.
The human pilot also showed confusion between asking for missing ticket IDs and
preparing a relationship action.

The new contract asks for the legitimate category and present fields, each supported
by an exact quote from a permitted source. Python derives the missing-field set from
the category's required fields. Fixed application text renders clarification questions
and the next-step recommendation with a reason. Complete triage means prepare for
human approval, not execute. The user makes the final next-step choice.

The UI offers source-selection/copy controls equally in manual and assisted modes,
so assisted-only quote prefill is not mistaken for better human reasoning. The
completed pilot is preserved as diagnostic evidence; the updated UI is not assigned
unmeasured productivity gains.

## Responsibility and tradeoffs

- Model: category and field-to-source associations. These can still be semantically
  wrong even if the quote exists. Human review remains necessary.
- Application: trusted actor/tenant filtering, schema/quote validation, missing-field
  computation, fixed questions, recommendation policy and explicit operator choice.
- Existing domain service: approval, dispatch, target verification, closure and audit.
  The AI evaluation/practice path has no action authority and is not silently wired
  into the existing operator worker.

OpenAI uses the pinned GPT-4.1 mini snapshot already evaluated. This is a bounded
quality/cost choice for extraction, not a claim that it is the newest or universally
best model. Ollama uses a separately pinned local model with the same evidence
contract and no hosted fallback. Its local revision also requires non-empty supporting
quotes and conservatively drops explicit absence statements or ticket-ID fields
without an ID. Discarded evidence is retained in the result for inspection. This
lexical guard is bounded and does not establish general semantic correctness.
Local fact quotes are constrained before inference to authorized full texts/sentence
spans. They provide source context and may retain untrusted instructions as quoted
text; their grounding is structural, not a model-authored factual summary. Category,
field mapping and missing-field correctness still need independent checks. This
local profile differs from OpenAI, so no paired provider comparison is claimed.
Same schema does not imply equal model quality;
each profile requires its own recorded evaluation.

William explicitly accepted OpenAI for the lab flow and deferred Claude/Grok live
canaries. Following local quality failures, he accepted closure with Ollama remaining
experimental and its improvement deferred. OpenAI is the accepted reference profile;
no automatic fallback selects an unaccepted local model. Their original contract adapters/tests remain. The new evidence-first
path is implemented for OpenAI and Ollama only; cross-provider parity is not claimed.

The local model cache/runtime is shared on this machine. The evaluation is sequential,
bounded, and unloads only its selected model afterward. No shared daemon/container
is stopped. GPU metadata is observed after loading rather than assumed from hardware.
This is suitable for lab acceptance, not an isolated performance or production test.

See [current evidence](../phase-6/CURRENT.md), [accepted scope](../phase-6/accepted-scope.json)
and [local runbook](../phase-6/LOCAL-RUNBOOK.md). Phase 7 owns broader reliability,
load, host recovery and deployment hardening.
