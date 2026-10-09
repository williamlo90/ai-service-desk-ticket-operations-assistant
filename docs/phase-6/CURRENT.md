# Phase 6 — completed for the accepted lab scope

Closed 2026-10-09, Asia/Jakarta. **OpenAI is the accepted advisory profile.**
William accepted the lab flow, kept Ollama experimental after its quality failures,
and deferred Claude/Grok live validation. The [closure gate](phase6-gate.json)
passes with no remaining gates within that scope; [the explicit decision](accepted-scope.json)
records the boundaries. This is not production, cloud or ROI acceptance.

## Current behavior

AI mode shows a next-step recommendation and its reason. Missing information leads
to clarification; complete triage suggests preparing a plan for human approval;
unsupported tasks route out of scope. The operator chooses the final next step.

The accepted OpenAI pipeline extracts present fields with exact authorized-source
quotes. Python validates them, computes missing fields, and renders fixed questions.
Exact quotes establish source membership, not infallible semantic field matching.
[ADR 004](../architecture/ADR-004-evidence-first-ai.md) records responsibilities and
tradeoffs. The evaluation/practice path is advisory; the existing operator worker's
approval, execution, verification and audit controls remain authoritative.

## Validated evidence

- OpenAI `gpt-4.1-mini-2025-04-14`, `evidence-first-v1`: **4/4 development and
  16/16 held-out** pass every rubric dimension: schema/grounding, category,
  relevant source quote, clarification presence and exact missing-field set.
- Data and implementation were frozen before inference. The pack is internally
  authored synthetic data, not independent customer annotation or broad production
  accuracy. No tuning occurred after the accepted held-out run.
- **172 Python tests, 8 MCP tests and 14 focused JavaScript assertions pass.**
- **38 valid real-model outputs** (20 OpenAI, 18 experimental local) pass eight
  domain/skill boundary checks each, with zero target requests/effects. Failed model
  responses remain in their quality denominator. This replay uses an in-memory
  target and is not another live Jira/Keycloak acceptance or proof of semantic safety.

OpenAI reports: [development](evidence-v1/openai-development.json),
[held-out](evidence-v1/openai-heldout.json). Source/data pins:
[freeze](../../evals/phase6-evidence-v1/freeze.json). Domain replay:
[selected-output-controls.json](selected-output-controls.json).

## Experimental local profile

Qwen3 4B Instruct, pinned digest, Q4_K_M, Ollama 0.40.1, context 4,096, concurrency
one, two CPU threads and 60-second request timeout. Actual offload observation was
**CPU, no VRAM allocation**. The shared daemon and other projects were not stopped.

The latest local revision passes 4/4 development but fails held-out quality:
14/16 structurally valid responses and **11/16 all-checks correctness**. Two
responses had unsupported quotations; missing-field errors also remain. All sixteen
held-out cases were attempted. It is not an accepted fallback for OpenAI.

Local code uses omission examples, conservative absence/ID checks and source-bound
context quotes. Context quoting is structurally grounded, not a generated factual
summary; quoted instructions remain untrusted data. This profile has a separate
fresh held-out pack and different constraints, so these runs are not a paired
provider benchmark. Held-out successful-response latency: p50 14.18s, p95 19.22s
on this shared CPU runtime. Hardware/electricity cost was not measured.

The selected model was unloaded after the run. The reload probe was skipped because
quality failed; no successful recovery, OOM or host-reboot claim is made. Model
artifacts remain cached. See [local report](local-evidence-v4.json),
[freeze](../../evals/phase6-local-v4/local-freeze.json) and [runbook](LOCAL-RUNBOOK.md).
Local improvement is deferred by William's explicit decision.

## Human pilot and practice

William completed eight diagnostic tasks. No manual/assisted pair both met the full
correctness rubric, so no efficiency gain or ROI is claimed. Original observations
remain unchanged; [business results](BUSINESS-RESULTS.md) explain the denominator.

The later pilot UI offered equal source-selection/copy tools in both modes. AI
mode explained the suggested next step without selecting or executing it. These
UX improvements were not part of the completed pilot and have no assigned
productivity claim. A fresh correctness-matched study is needed for such a claim.

The earlier untimed practice page used four cached OpenAI examples. It made no
model calls or business changes. That page has been removed from the current
operator interface; the pilot data and evaluation scripts remain in the repository.

## Costs and reproducibility

Across 70 hosted requests, cumulative uncached list-price estimate is
**US$0.0164488**, not an invoice. The US$1 cap remains. Pre-call reservations settle
only against matched recorded usage; unknown/interrupted requests retain their full
reservation. Credentials were not displayed or committed.

Run `python scripts/check_phase6_gate.py` from the project root to check saved
evidence, source pins and tests without credentials or model calls. Historical
checkpoint reports retain their original status; this document and the closure gate
are the current status. The phase is saved as one completion commit.

## Next work

Phase 7: broader reliability/security tests, bounded load and soak, host/runtime
recovery, monitoring and rollback for a local release candidate. Ollama improvements
require a new versioned evaluation before acceptance. Claude/Grok need live canaries
before any readiness claim. Phase 8 packages handover; Azure remains Phase 9.
