# Phase 6 â€” quality and business evaluation

Status: **complete for the accepted OpenAI advisory lab scope**. See
[current results](CURRENT.md), [explicit scope](accepted-scope.json) and
[closure gate](phase6-gate.json). Ollama remains experimental; Claude/Grok are deferred.
The original rubric below is a planning checkpoint, not the current release claim.

## Frozen evaluation contract

`evals/phase6/dataset.json` contains 8 development and 16 held-out synthetic cases,
balanced across four categories. Alpha/beta tenants, Indonesian/English requests,
missing details and injection attempts are covered. Canary uses two development
cases; its results are not additional independent samples. No customer data is sent.

The sets are disjoint and frozen before any model calls. They share an author with
the implementation: this is a small synthetic holdout, not externally annotated
independent business evidence. Do not tune on held-out results; a changed prompt
requires a new labelled holdout and version. Freeze hashes cover data, schema and
instructions. Store code revision/hash with live results before making a claim.

First candidate: `gpt-4.1-mini-2025-04-14`, a pinned non-reasoning snapshot for
bounded extraction, not a claim that it is the best/current model. Responses API,
structured output, no tools, no writes, `store=false`, 1,000 maximum output tokens.
[Official model documentation](https://developers.openai.com/api/docs/models/gpt-4.1-mini)
supports this endpoint/schema capability and lists $0.40 input / $1.60 output per
million tokens (checked 2026-10-08). This is a list-price estimate, not an invoice.
[Structured output reference](https://developers.openai.com/api/docs/guides/structured-outputs)
does not make semantic correctness automatic.

## Rubric v1, fixed before live inference

Each selected case is in the denominator, including failures and unattempted cases.

| Measure | Acceptance |
| --- | --- |
| Valid schema and grounded quotes | 100% of cases |
| Exact category | >=90% of cases |
| At least one relevant labelled ticket quote, >=12 characters | >=90% of cases |
| Clarification present when labelled necessary | 100% of cases |

Report numerator/denominator by split; do not combine development with held-out.
The clarification check tests presence only. A human must review relevance,
completeness, harmful instructions quoted as facts, and claimed outcomes before
business acceptance. Exact quote grounding cannot establish that a source is true.
Successful-response p50/p95 use nearest-rank and disclose the sample count; failures
remain in quality denominators and are not silently counted as fast responses.

The model receives only an advisory extraction contract, with no execution tool.
Foreign-tenant and supervisor-only canary sources are filtered before transmission.
Existing tests enforce approval, verification and source permissions; a real-model
run still needs a recorded critical-control review. No model can authorize itself.

## Running

1. Put `OPENAI_API_KEY` in the project `.env` locally. Never paste it into chat.
2. `python scripts/evaluate_ai.py` validates the freeze offline without secrets.
3. `python scripts/evaluate_ai.py --live --split canary` performs two requests
   only for an unused frozen run. Current run reports already exist and the
   reservation cap is reached; it will not silently rerun them.
4. After a passing canary, development reuses those two outputs; other development
   cases and held-out cases use separate calls. Current scripts target the new
   20-case pack and `docs/phase-6/v4`, not the original 24-case pack.
5. Review the outputs and record remaining gaps; failing output stays in the report.

The Windows runner takes an OS lock, reserves $0.02 per attempt in an ignored
durable journal before transmission and limits cumulative reservations to $1.
Input serialization is capped at 12KB; output is capped at 1,000 tokens. This has
ample margin against 40,000 input tokens plus output at the recorded prices.
No retries or automatic provider fallback. A timeout may still incur cost and its
reservation is retained. Existing report/reservation blocks accidental reruns.
Authentication, timeout or rate-limit failure stops the run. Actual token counts
are kept where available; missing usage/cost is null. Headers, key and error bodies
are never persisted. These budgets cover this runner only, not other account jobs.

## Remaining gates

- OpenAI canary, development and holdout outputs are recorded with frozen source hashes.
- Real-output boundary checks pass; unsafe clarification needs remediation and
  human semantic review, distinct from automated category/schema scoring.
- Ollama inference/model/license are recorded; current model fails quality and
  a viable configuration remains pending. Claude/Grok canaries await credentials.
- Manual-versus-assisted matched correctness and timing, using BUSINESS-STUDY.md.
- Final scoped quality report, learning notes and one Phase 6 completion commit.

No live operator API, worker, Docker, Jira or Keycloak changes are required for
this extraction evaluation. Phase 5 remains the integrated deterministic baseline.
