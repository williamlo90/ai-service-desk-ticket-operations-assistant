# Architecture comparison contract — v1

Date: 2026-10-08. Status: frozen synthetic reference contract for prototype implementation; no candidate has been executed or selected. Business owner, connected targets and credentials remain Phase 0A prerequisites. Changes to this contract require a new version, reason and fixture hash; both candidates must be rerun against the same version.

## Scope and candidates

A: code-led orchestration adapted from baseline revision `1a88dbb0e55889303ec83c7abb789fade81f16bf`, with local changes preserved separately.
B: n8n-led orchestration calling the same domain services. A broader n8n implementation is optional only after equivalent controls can be demonstrated.

Compare one complete access-request journey: raw ticket → tenant-scoped context and SOP → proposal → authorized approval → target accepts → delayed target result → read-back verification → close → fresh adverse evidence → reopen. Incident diagnosis and repeated-ticket linking are additional reference cases. Existing billing/refund tests remain regression coverage, not MSP benchmark results.

Both candidates use the same domain rules, fake target contract, fixtures, seed state, deterministic triage outputs, fake clock and no external model calls. Add missing baseline lifecycle behavior to both; do not compare a complete candidate with an incomplete baseline. Each candidate uses a separate database namespace and target ledger. Run sequentially; never let two engines write the same external operation.

## Authority and state ownership

| Concern | Candidate A | Candidate B |
| --- | --- | --- |
| Case state and optimistic version | Python/PostgreSQL | Same Python/PostgreSQL |
| Permission, tenant, policy checks | Domain service | Same domain service |
| Approval snapshot and expiry | Domain service | Same domain service |
| Idempotency and action reconciliation | Domain service | Same domain service |
| Closure/reopen predicates | Domain service | Same domain service |
| Workflow progression and wait scheduling | Code orchestrator | n8n |
| Transport retry scheduling | Code orchestrator | n8n |

Transport retries may redeliver a command with the same operation ID. Only the domain service authorizes an external mutation. A timeout after possible mutation requires reconciliation; retry scheduling cannot override it. Keep Celery inbox/policy jobs isolated until their dependencies and replacement are mapped.

## Synthetic business rules

Tenant `alpha` owns resource `reports`, user `requester-a`, service `demo-api`, tickets `SD-1` and `SD-2`. Tenant `beta` owns separate resources with the same display names. Identifiers always include tenant scope.

SOP `access-v1`: a specialist can propose `grant_read_access` to reports; a supervisor of the same tenant must approve. Privileged access is out of scope. Approval binds actor, tenant, action payload, case version, policy version and proposal hash; expires after 15 fake-clock minutes. A version change requires new approval. An auditor is read-only. The requester cannot self-approve.

SOP `incident-v1`: read-only health diagnosis is allowed; a supervisor must approve a single restart of `demo-api`. Completion requires three consecutive healthy checks, 10 fake-clock seconds apart, after action success. Failure escalates with an owner and reason.

SOP `duplicate-v1`: a specialist proposes a same-tenant related-ticket link; a supervisor approves the write. Read-back must confirm the exact link once. The underlying ticket remains open unless separate resolution evidence exists.

`accepted` and `running` never satisfy success. Access completion requires authoritative read-back of the exact entitlement after target success. Unknown outcomes remain open. New authenticated evidence that invalidates a closed result reopens the case and increments its version, without replaying the prior action. A structured no-action resolution must cite its reason and evidence; it cannot stand in for failed verification.

## Fixtures and independent evaluation

Reference inputs and expected outcomes: `../phase-0/reference-fixtures.json`. These are development/control fixtures, not a held-out set. Candidate adapters receive input, preconditions and events only. The evaluator separately loads expected outcomes after collecting observations. No expected labels enter prompts or workflows.

The Phase 1 evaluator must read the fake target's independent operation ledger and read-back state, the domain state and append-only audit trace. A workflow node reporting success is not evidence of a successful business outcome. Missing observations, skipped cases or exceptions fail the case. Assess each ordered checkpoint, not only final state.

Required observation fields: run ID, candidate revision, contract/fixture hashes, case ID, tenant, event sequence, case/action versions, approval snapshot hash, external operation ID, target mutation count, observed target state, closure/reopen transitions, denial reason, manual touches, recovery steps and timing. Redact credentials and unnecessary content.

## Hard gates and comparison protocol

Every reference case must pass, with zero cross-tenant disclosure/write, unauthorized mutation, duplicate mutation, stale-approval execution or false closure. Count mutations against the independent target ledger. Retry and concurrency scenarios must test persisted behavior, not just mocked return values.

Phase 1 runs each case once per candidate, sequentially, with deterministic barriers for concurrent-update cases. This is a bounded functional pass, not load testing. Restart cases restart only the candidate worker after a persisted checkpoint. If safety/resource limits prevent a case, record it unexecuted and do not select a winner.

After correctness passes, apply the same process change to each: `access-v2` shortens approval expiry from 15 to 5 minutes and introduces a new policy version, invalidating older approvals. Record active editing time, files/nodes touched, failed regressions, debugging and recovery steps; rerun the same acceptance pack plus expiry boundaries at 4:59 and 5:00.

Measure elapsed time from intake to verified outcome separately from approval wait, queue time, target delay and recovery. p95 uses nearest-rank and reports sample count; a small functional sample is descriptive only. Record peak memory/CPU and elapsed operator effort. With no provider calls, provider usage is not applicable; do not label unknown infrastructure cost as zero. Performance/load comparisons require an isolated approved environment and a separately frozen workload before execution.

Selection in Phase 2: exclude candidates failing any hard gate; prefer fewer recovery interventions, then lower measured change effort; assess latency/resources/cost as explicit tradeoffs. If neither passes or evidence is too limited, continue the bounded prototype. No winner from lines of code or an incomplete measurement alone. Record component-level retain/replace/delete and one owner per state/retry responsibility in the ADR. Connected acceptance remains Phase 5 and cloud deployment Phase 9.
