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
account, IT-1 and one prior diagnostic read exist. William owns business decisions, approvals and credentials. Local sandbox
identities and action targets are configured; provider/model readiness is tracked in
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

- [x] Parameterized PostgreSQL repositories, migrations and tenant constraints.
- [x] Versioned business-state persistence contract, optimistic concurrency and
  transactional idempotency/audit; migration runner with pinned dependency.
- [x] Jira mapping/read-sync and guarded update/read-back contracts, bounded errors,
  callback ordering, unknown-outcome recovery and fake transport tests.
- [x] Adapter contract tests and schema checks without launching PostgreSQL.

Gate: code and offline contracts pass. PostgreSQL semantics, migrations on a real
server, durability and Jira write permissions remain Phase 5 requirements.

## Phase 4 â€” Client, MCP and AI preparation

- [x] TypeScript reference client and actual MCP stdio protocol server/client tests.
- [x] Read/prepare/approved-execute/verify/reopen tools use the same Python controls.
- [x] Strict tool schemas, identity binding, output bounds and sanitized errors.
- [x] Four reusable executable skills: triage, prepare, verify, summarize.
- [x] Provider adapters for OpenAI, Claude, Grok and Ollama, structured-output
  validation, prompt/schema versions, scoped retrieval and local-only behavior.
- [x] Mock-provider tests for invalid output, unsupported citations, failures and
  missing usage; reuse skills from interactive and automation callers.
- [x] Learning checkpoints and a concrete integration handoff checklist.

Gate: client/protocol and skill contracts pass offline. Real credentials, hosted
canaries, model artifacts/licenses and local inference remain unvalidated.

## Phase 5 â€” Local integration and architecture decision

Status: **complete for local V1 integration** on 2026-10-08. The intermediate
checkpoint `66693e6` was committed at William's request; this completion is recorded
in the final Phase 5 commit after the evidence gate passed.

Architecture: **code-led**, selected under William's explicit delegation.
[ADR 003](docs/architecture/ADR-003-selected-code-led.md) records the rationale,
responsibility boundaries, comparison evidence and tradeoffs. n8n remains optional;
existing workflows and baseline jobs are preserved. Jira uses outbound polling,
so V1 does not deploy an inbound webhook receiver.

- [x] Real PostgreSQL migrations, RLS, CAS, audit atomicity and connected MCP/API.
- [x] Both reference candidates: 14 base + 17 policy cases each; native wait,
  recovery, transport and persisted timer evidence recorded separately.
- [x] Keycloak/demo targets for alpha/beta, actual target read-back and replay.
- [x] William's browser approval, actual access grant and verified local closure.
- [x] Jira result property write/read-back and replay without another PUT.
- [x] API/worker supervision and crash restart with unchanged approved entitlement.
- [x] Logical restore, schema rollback, quiesced cross-database job cutover and
  rollback with one synthetic target effect.
- [x] Bounded Jira search/sync and approved-link adapters with negative tests.
- [x] Live IT-1/IT-2 link creation/read-back, two-page sync and negative authentication.
- [x] Enable and verify the authenticated periodic poller after live acceptance.
- [x] Pass scripts/check_phase5_gate.py and record the final Phase 5 status.

Final unit validation: **130 Python + 8 Node tests**.
[phase5-gate.json](docs/phase-5/phase5-gate.json) passes with no remaining gates.
The user-selected unscoped token uses the explicit Jira site origin. IT-2 was
created, related to IT-1, verified and rechecked without another link write.
The 60-second authenticated poller is active for these two keys only.

Gate scope: integrated local V1. Real-provider quality evaluation is Phase 6;
load/soak, host restart, network-partition fencing and release hardening are
Phase 7. Jira source checks are preflight checks, not cross-system transactions.
Billing/refund baseline jobs have not been cut over and are not deleted.

## Phase 6 â€” Quality and business evaluation

Status: **complete for the accepted OpenAI advisory lab scope**, 2026-10-09.
William accepted the flow, explicitly kept Ollama experimental after quality failures,
and deferred Claude/Grok live validation. [Current results](docs/phase-6/CURRENT.md)
and the [closure gate](docs/phase-6/phase6-gate.json) record the final boundaries.

- [x] Frozen OpenAI development/held-out evaluation: 4/4 and 16/16 all checks.
- [x] Actual local inference, pinned model/hardware/configuration and honest failure
  evidence; experimental status and further improvement accepted explicitly.
- [x] Eight-task human diagnostic pilot, preserved observations, no invented ROI.
- [x] Equal quote-selection UX and AI next-step recommendation with a reason.
- [x] Real-output domain replay: 38 valid outputs, eight checks each, zero target calls.
- [x] 172 Python tests, 8 MCP tests and 14 focused JavaScript assertions pass.
- [x] Reproducible closure gate and learning notes for one Phase 6 completion commit.

Gate scope: OpenAI advisory lab quality and diagnostic business evaluation.
The AI path does not replace domain approval/verification. Local quality, a fresh
ROI study and other-provider live readiness are not claimed. Source-grounded quotes
do not prove semantic correctness. Runtime hardening remains Phase 7.

## Phase 7 â€” Reliability, security and performance

Status: **complete for the bounded local lab release**, 2026-10-09.
[Results](docs/phase-7/CURRENT.md) and [gate](docs/phase-7/phase7-gate.json).

- [x] Authorization/tenant/approval boundaries and current regression suite.
- [x] Abrupt worker crash after effect, API cold start and durable replay.
- [x] Concurrent dispatch, lost claim session and isolated database outage.
- [x] 48 synthetic HTTP journeys: sequential, concurrency four and 61-second smoke soak.
- [x] Fix active queue counting; add local health alerts; verify ready runtime.
- [x] Reuse unchanged Phase 5 restore/cutover/rollback evidence; 179 Python + 8 MCP + 14 JS checks.

Gate scope: bounded local lab. Physical host reboot, long endurance, wire-level
partition fencing and production/cloud performance are not claimed. Manual startup
and operator review remain required. No shared containers or live targets changed.

## Phase 8 â€” Handover

Status: **complete for local lab handover**, 2026-10-09.
[Handover](docs/phase-8/README.md), [operator guide](docs/phase-8/HANDOVER.md)
and [gate](docs/phase-8/phase8-gate.json).

- [x] Source-only package excludes credentials/runtime data/dependencies/models.
- [x] Clean source export: new Python venv + locked npm install/build; 182 Python,
  8 MCP tests and 14 JavaScript assertions pass; offline demo passes.
- [x] English daily-use/setup/status/recovery/backup/upgrade/ownership guide.
- [x] Bounded local identity renewal tool, scope-preserving tests and expiry guidance.
- [x] Evidence/version manifest, acceptance map and synthetic failure/replay demo.
- [x] William remains owner/approver/credential custodian/support owner.

Code-led V1 requires no active n8n workflow export; existing optional workflows are
preserved under ADR 003. Clean installation was tested on this host, not a second
host or newly provisioned SaaS account. Physical reboot, full-volume disaster recovery
and unattended production deployment remain separate qualifications.
Azure preparation and provisioning are explicitly deferred at William's request.

## Phase 9 â€” Azure deployment last

Deploy only the selected tested architecture. Apply identity/secrets/network policy,
repeat connected acceptance, recovery/load/monitoring in cloud and validate rollback.
Document costs, retention, teardown and ongoing ownership. Local results do not
substitute for cloud validation. No cloud work is part of the current offline loop.
