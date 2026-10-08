# Local AI and provider profiles

Phase 6 accepts OpenAI for the advisory lab flow. William explicitly kept Ollama
experimental and deferred Claude/Grok live validation; see
[accepted scope](docs/phase-6/accepted-scope.json) and
[current evidence](docs/phase-6/CURRENT.md).

| Profile | Implementation | Validation |
| --- | --- | --- |
| OpenAI | Evidence extraction, structured Responses output, pinned `gpt-4.1-mini-2025-04-14` | Accepted: real synthetic development/held-out reports |
| Ollama | Same evidence contract, fixed loopback endpoint, no key or hosted fallback | Experimental: pinned `qwen3:4b-instruct`; quality gate not passed |
| Claude | Original bounded provider adapter | Offline contract tests; live canary deferred |
| Grok | Original bounded provider adapter | Offline contract tests; live canary deferred |

Only OpenAI and Ollama implement the current evidence-first path. The original
four-provider adapter contract remains in `backend/service_desk/ai.py`; this does
not establish equivalent quality or capabilities across providers.

## How recommendations work

The model associates present fields with exact authorized-source quotes. Python
validates those quotes, computes missing fields, renders fixed questions and
recommends the next step. This reduces model responsibility but does not prove
that every field association is semantically correct. The operator chooses the
next step; approval, execution and verification remain in the domain service.
The evaluation/practice path is advisory, with no target credentials or action tools.
See [ADR 004](docs/architecture/ADR-004-evidence-first-ai.md) for the decision.

Retrieval is bounded lexical selection over explicit tenant-authorized sources;
there is no embedding model or vector database. API integrations use official
endpoints, not provider chat UI automation. Credentials load internally and never
belong in committed configuration or reports.

## Local deployment boundary

The Windows lab reuses an existing Ollama 0.40.1 loopback service. Model digest,
license hash, quantization, hardware, request options, observed GPU offload,
latencies and token counts are recorded in the local report/freeze. Initial model
provisioning requires a download; subsequent inference has no hosted fallback.
Jira still requires SaaS connectivity.

The [local runbook](docs/phase-6/LOCAL-RUNBOOK.md) covers provisioning, readiness,
warmup, limits, unload/reload, upgrade, rollback and retention. HTTP timeouts do not
guarantee immediate cancellation inside Ollama. Model unload/reload tests do not
establish daemon-crash, OOM or host-reboot recovery. Linux/Docker packaging,
sustained/concurrent load and those failure modes remain Phase 7 work.

## Evaluation interpretation

Both evaluated profiles use the same rubric and evidence schema. The local revision
adds omission examples, conservative value checks and source-bound quote choices.
It has its own fresh internally authored synthetic held-out pack;
these runs are not a paired provider benchmark. Each report retains selected cases
in its denominator,
including failures. Source and model versions are frozen before calls. A changed
prompt needs fresh held-out data; previous holdouts become regression data.

Hosted cost is a token/list-price estimate, not an invoice. Local electricity and
hardware cost are unmeasured, not zero. Shared-runtime latency is not an isolated
hardware benchmark. The completed human pilot is diagnostic; no correctness-matched
productivity or ROI claim is supported.
