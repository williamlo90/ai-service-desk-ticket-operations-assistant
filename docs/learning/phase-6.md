# Phase 6 — quality evaluation and advisory recommendations

This phase separates a working AI demo from reproducible evidence. Read
[the current result](../phase-6/CURRENT.md) and
[the gate](../phase-6/phase6-gate.json) for the accepted scope and validation.
William accepted the OpenAI lab flow, kept Ollama experimental after its quality
failures, and deferred Claude/Grok live canaries.

## What to study in this commit

1. `backend/service_desk/clarification.py`: extract present fields with exact source
   quotes, validate them, then compute missing fields in Python. Fixed application
   questions and next-step guidance replace model-authored clarification text.
2. `backend/service_desk/local_clarification_v4.py`: apply the same contract through a
   fixed loopback Ollama endpoint, without credentials or hosted fallback.
3. `backend/service_desk/evaluation.py`: keep every selected case in denominators,
   including unavailable/invalid responses. A valid schema alone is insufficient.
4. `scripts/evaluate_evidence_ai.py`: freeze versions before calls; reserve budget
   before transmission and settle only matched, recorded usage. A timeout is not
   proof that a provider did no work or charged nothing.
5. `scripts/check_local_evidence_v4.py`: verify model/license, warm up, gate development
   before held-out inference, observe actual offload, and unload/reload only the
   selected model. Do not stop a shared daemon to test recovery.
6. `scripts/business_pilot.py` and `evals/phase6-v2/`: show evidence and next-step
   reasons, offer equal quote-selection tools, and leave the final choice to the
   operator. Untimed practice saves no answers and executes no business action.
7. `scripts/check_ai_controls.py` and `scripts/check_phase6_gate.py`: replay actual
   model outputs against domain boundaries, verify frozen evidence and run tests.

## Why the design changed

Early evaluation exposed unnecessary clarification and unsafe interpretation of
injected instructions. Asking the model only for grounded present information makes
its responsibility smaller. Python decides which category fields remain missing;
complete triage recommends preparing for approval, never execution. Exact quotes
prove source membership, not that semantic field labels are always correct.
[ADR 004](../architecture/ADR-004-evidence-first-ai.md) records the choice and limits.

Each evaluated profile uses four development and sixteen disjoint held-out cases, internally
authored and frozen before inference. The local revision uses its own untouched
held-out pack, so these are not paired provider comparisons. It is synthetic lab evidence, not independent
customer validation. A future changed prompt requires fresh held-out data; old packs
remain regression material. Reports record actual model/runtime versions and usage.

## What the human pilot teaches

William completed eight tasks. None of the manual/assisted pairs both satisfied the
full correctness rubric, so the study cannot establish a productivity or ROI gain.
Quote retyping versus prefill also confounded the original interface. Both modes now
have equal quote-selection tools, and AI mode explains the suggested next step.
Original observations remain unchanged; an updated interface needs a fresh study if
we want an efficiency claim. Model latency is not a substitute for human effort.

## Reproduce and continue

Run `python scripts/check_phase6_gate.py` from the project root after installing the
locked MCP dependencies. It checks saved evidence and local tests without reading
credentials or making model calls. Evaluation runners deliberately refuse to overwrite
existing runs; use a new versioned run instead of deleting evidence to retry.

Phase 7 covers broader reliability, load, host/runtime failures and release hardening.
Phase 8 packages handover. Azure remains Phase 9. Study this phase through its one
completion commit; local runtime files, raw human observations and secrets stay ignored.
