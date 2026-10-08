# Phase Plan â€” build first, integrate in a reserved runtime session

2026-10-08. This plan replaces the earlier execution order. Feature requirements in
the topic documents remain applicable; phase references in the frozen comparison
contract describe its original schedule, not a requirement to run Docker now.

## Execution rules

- Phase 1â€“4: implement and test without Docker, live SaaS/model calls, .env access,
  or interference with other projects. Use deterministic fixtures and bounded tests.
- One commit per phase. Phase 1 is the initial snapshot, including pre-existing
  runtime setup/evidence; it does not claim these were recreated without Docker.
- Record implementation, offline validation and connected validation separately.
- Domain controls stay behind shared service interfaces. Do not build two complete
  orchestrators or pick an architecture before Phase 5 comparison evidence.
- Security and unit/contract tests accompany features. Runtime tests are deferred,
  not deleted. Missing ownership/access blocks only dependent connected actions.
- Commit only passing work with learning notes. Never include secrets, installed
  dependencies, caches or local credentials. No cloud deployment before Phase 9.

## Phase 0 â€” Scope and prerequisites (existing)

Inventory, source snapshot, contract v1 and 14 reference fixtures exist. Atlassian
account, IT-1 and one prior diagnostic read exist. Business owner, integration
identity, action-target sandbox and provider/model readiness remain open in
`docs/phase-0/setup-readiness.md`. Synthetic policy is not business authorization.

## Phase 1 â€” Backend foundation, no Docker

- [x] Typed identity/ticket contracts and GET-only Jira reader.
- [x] Pure approval, verification, retry and reopen predicates.
- [x] WSGI create/read API, explicit authentication, tenant/role checks.
- [x] Bounded repository interface/memory implementation and atomic idempotency.
- [x] 39 offline tests covering errors, input, access and concurrent replay.
- [x] Document API boundaries and deferred runtime integration.

Gate: foundation is reproducible with stdlib tests; no listener or real credentials
required. This is not a production identity system or durable storage.

## Phase 2 â€” Deterministic business journey

- [x] Tenant-scoped policy/context, triage and clarification/escalation.
- [x] Propose, supervisor approval, bound versions/expiry and dispatch.
- [x] Accepted/running/succeeded/failed/unknown outcomes and reconciliation.
- [x] Verify read-back before close, adverse evidence reopen, related-ticket rules.
- [x] Simulated access, incident recovery and related-ticket targets with an
  independent effect ledger; immutable domain snapshots and audit events.
- [x] Offline happy/negative/concurrent/replay tests; identify persisted checks
  deferred from the 14 reference scenarios without claiming the frozen gate passed.

Gate: the bounded three-journey simulator obeys controls. No external mutations.

## Phase 3 â€” Adapters and persistence preparation

- [ ] Parameterized PostgreSQL repositories, migrations and tenant constraints.
- [ ] Versioned business-state persistence contract, optimistic concurrency and
  transactional idempotency/audit; migration runner with pinned dependency.
- [ ] Jira mapping/read-sync and guarded update/read-back contracts, bounded errors,
  callback ordering, unknown-outcome recovery and fake transport tests.
- [ ] Adapter contract tests and schema checks without launching PostgreSQL.

Gate: code and offline contracts pass. PostgreSQL semantics, migrations on a real
server, durability and Jira write permissions remain Phase 5 requirements.

## Phase 4 â€” Client, MCP and AI preparation

- [ ] TypeScript reference client and actual MCP stdio protocol server/client tests.
- [ ] Read/prepare/approved-execute/verify/reopen tools use the same Python controls.
- [ ] Strict tool schemas, identity binding, output bounds and sanitized errors.
- [ ] Four reusable executable skills: triage, prepare, verify, summarize.
- [ ] Provider adapters for OpenAI, Claude, Grok and Ollama, structured-output
  validation, prompt/schema versions, scoped retrieval and local-only behavior.
- [ ] Mock-provider tests for invalid output, unsupported citations, failures and
  missing usage; reuse skills from interactive and automation callers.
- [ ] Learning checkpoints and a concrete integration handoff checklist.

Gate: client/protocol and skill contracts pass offline. Real credentials, hosted
canaries, model artifacts/licenses and local inference remain unvalidated.

## Phase 5 â€” Reserved integration session and architecture decision

Only start after resource availability is confirmed and the user resumes runtime
work. Use this project's bounded stack, one candidate at a time.

1. Install from pinned dependencies; configure real local service identity; run
   actual HTTP auth/readiness and PostgreSQL migrations/permissions/transactions.
2. Run equivalent complete code-led/n8n-led vertical prototypes against the same
   independent reference evaluator. Persisted restart/concurrency cases are mandatory.
3. Compare controls, recovery and equivalent process-change effort; document an ADR.
   Do not choose a winner from this project's memory simulator or trigger demo.
4. Connect Jira, approved sandbox targets, UI/client/MCP and selected orchestration.
   Test read/propose/approve/write/read-back, rate limits, callback/retry ordering,
   dead-letter/review paths and a second tenant configuration.
5. Rehearse schema/config/job migration and rollback without duplicate effects;
   correct integration defects and rerun affected tests before leaving the phase.

Gate: real connected outcomes, not merely node success. Revisit ADR if connected
results invalidate the synthetic comparison. No obsolete active code removed yet.

## Phase 6 â€” Quality and business evaluation

Freeze development/regression and independent held-out sets, rubric/denominators,
quality targets and versions. Run real-provider canaries and local inference with
approved synthetic data; record actual usage and unknown costs honestly. Compare
manual versus assisted tasks with equal correctness; distinguish active work,
waiting, corrections and elapsed time. Recheck critical controls with real models.
Gate: reproducible quality evidence and scoped limitations, no invented ROI.

## Phase 7 â€” Reliability, security and performance

Permission bypass/injection/leakage, duplicate triggers, expired approval, timeout
after effect, concurrency, interrupted worker, delayed callback, database recovery,
backup/restore, alerts and rollback. Bounded normal/peak/soak workload after sizing;
report outcome correctness and end-to-end percentiles separately from acknowledgement.
After quality gates pass, rehearse cutover and remove only proven obsolete code;
retain required baseline jobs until replacement passes. Rerun affected tests.
Gate: verified local release candidate, not a production/cloud claim.

## Phase 8 â€” Handover

Sanitized workflow exports, clean setup, daily use, approval/failure handling,
backup/upgrade/support guide, demo, evidence manifest, version locks and operational
owner. Prepare Azure IaC/cost/security/teardown plan without provisioning.
Gate: reproducible local delivery and documented remaining prerequisites.

## Phase 9 â€” Azure deployment last

Deploy only the selected tested architecture. Apply identity/secrets/network policy,
repeat connected acceptance, recovery/load/monitoring in cloud and validate rollback.
Document costs, retention, teardown and ongoing ownership. Local results do not
substitute for cloud validation. No cloud work is part of the current offline loop.
