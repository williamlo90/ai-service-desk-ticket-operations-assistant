# ADR 001 — shared controls retained; orchestration selection remains open

Date: 2026-10-08. Status: **provisional component decision**, not final engine selection.

## Evidence

The isolated reference experiment executed actual Python and n8n workers against
the same domain API, PostgreSQL repositories, fake clock and independently stored
target effects. Candidate inputs exclude expected outcomes; a separate evaluator
checks ordered observations, database audit events and target ledger/read-back.

| Candidate | Original 14 scenarios | Policy v2: same 14 + 3 boundary cases |
| --- | --- | --- |
| Code-led reference worker | 14/14 pass | 17/17 pass |
| n8n-led reference workflow | 14/14 pass | 17/17 pass |

These are **62 scenario executions**, not 62 independent held-out cases. The
policy change shortens approval validity from 15 to 5 fake-clock minutes; the
extra cases check 4:59, 5:00 and invalidation of approval issued under access-v1.
Checks cover tenant denial, stale/expired approval, delayed failure, timeout after
effect, duplicate/late callbacks, concurrent dispatch, checkpoint restart,
clarification, incident recovery and related-ticket behavior.

Run ID, source hashes, summary and per-case results:
[orchestrator-comparison.json](../phase-5/orchestrator-comparison.json).
Raw synthetic traces and sanitized n8n exports are retained locally at the path
recorded in that report. Each candidate/profile uses its own temporary SQL database
and target ledger. All generated containers, databases and roles were removed.

## Decision supported now

Retain Python as the authority for permission, tenant scope, proposal/approval,
idempotency, transactional audit, reconciliation, closure and reopen. Both runners
successfully reuse those controls. Keep these rules out of n8n nodes and model
prompts. PostgreSQL owns business state; the synthetic target owns its outcome
ledger. No existing baseline job or n8n user workflow is removed or replaced.

Do **not** select an orchestration winner from this run. Both satisfy the measured
functional expectations; the differentiating operational evidence is incomplete.
The larger elapsed duration of the n8n runner includes CLI startup/import, SQLite
migrations and explicit restart overhead, so it is not a production latency or
operator-effort comparison. No ROI, p95, peak resource or cost claim is made.

## What the experiment does not establish

Both candidates are explicit linear reference sequences. Environment events
(supervisor fixture approval, fake clock advancement, target completion/failure)
are driven as test steps, not live integrations. The fixture API is internal to
the isolated test network and is not the production authorization surface.

Worker restart is performed at an explicit persisted acceptance boundary: the
Python worker exits and a new interpreter resumes the second segment; the isolated
n8n container is restarted and executes the second saved workflow. This proves
reuse of persisted domain state, not native n8n Wait-node resume or autonomous
scheduling/retry recovery. Separate connected tests cover abrupt action-worker
exits, but they do not substitute for engine-native scheduling acceptance.

The new shared runtime is not a complete execution of the earlier billing/refund
baseline candidate. Requester messages are routed through the staff gateway in
this harness; requester portal authentication is not under comparison. Active
editing time, manual intervention effort and baseline regression parity were not
measured. Thus the full frozen architecture gate remains open even though every
measured fixture expectation passes.

## Evidence required for final selection

1. Short-timer interruption, transport failures and distributed lease coverage.
   Bounded approval/target wait recovery and the recovery pack below now pass.
2. Baseline billing/refund regression parity or an explicitly versioned scope
   decision; no silent change to the frozen comparison contract.
3. Measured process-change editing/recovery effort on equivalent implementations,
   then workload-isolated latency/resources if they affect selection.
4. Connected sandbox acceptance after the live target and operational approver
   are ready. William is the business owner; fixture identities are not live approval.

Final selection follows the frozen contract: exclude correctness failures, then
compare recovery interventions and measured change effort. Until then, maintain
both small reference runners and one shared implementation of domain controls.

## Native wait/restart checkpoint

A separate [native wait run](../phase-5/native-wait-comparison.json) passes for both
engines on one synthetic access journey each. The code worker polls shared state
and persists its stage in SQLite; n8n uses two webhook Wait nodes in one published
workflow. The harness abruptly kills and starts each engine container during
approval wait and again during target wait: four restarts across two journeys.
Approval and target completion come from the external fixture controller.

Both workers continue automatically to verification and closure after those
events, with one target effect per journey. The n8n execution ID survives both
restarts; unsigned, previous-stage and duplicate resume callbacks are rejected.
The runner waits for `/healthz/readiness` after n8n startup, since a listening
HTTP port alone does not establish that resume routes are registered.

Only engine containers restart. Business PostgreSQL, the fixture API and target
ledger remain running. This does not prove database recovery, distributed worker
leases, retry/backoff, real callback integration or broader native failure handling.
All temporary resources are removed. The bounded result advances the operational
comparison without selecting a winner or closing the full architecture gate.

## Bounded recovery checkpoint

The [recovery pack](../phase-5/recovery-comparison.json) tests seven conditions per
engine: expired/revoked approval, delayed outcome, terminal failure, lost response
after effect, transient read timeout and exhausted budget. The same persisted
controller is scheduled by a code timer loop or n8n HTTP/IF/Wait loop. Four read
attempts are allowed with 1/2/4-second backoff. Uncertain writes are not retried.
The evaluator checks closure, review reason, attempt count, independent effect
ledger and actual submit-call count. Repeated/late callback hints do not redispatch
or automatically close a case held for review.

This isolates scheduling against shared controls; it is not a comparison of two
independent recovery policy implementations. Unknown/failure/read-timeout fixtures
seed target state before scheduler execution. Short n8n timer waits remain in
process; crash during backoff, HTTP transport retry and distributed ownership are
not established. Review is persisted escalation, not a deployed operator queue UI.
The architecture decision remains provisional.

## Baseline compatibility and maintenance

The frozen Phase 0 source archive and overlay were restored into an isolated,
credential-free local directory after verifying their manifest hashes. Eleven
baseline unit files pass **47 tests**, covering action recovery, approval snapshots,
review authority/materialization, case state, gateway behavior, signed intake and
workflow evaluation. See [baseline-regressions.json](../phase-5/baseline-regressions.json).
The old repository was not modified. These results preserve baseline regression
evidence; they do not establish billing/refund parity in the new runtime.

| Capability | Baseline | Current service desk candidates | Migration status |
| --- | --- | --- | --- |
| Approval and authorization | Financial review rules, amount/currency and role thresholds | Tenant/role, payload/version, expiry and pre-dispatch revocation | Shared invariants tested; financial rules not ported |
| Action recovery | Lease/idempotency/reconciliation contracts | Reserved operation, authoritative read-back, bounded retry budget | Distributed lease parity pending |
| Outcome and lifecycle | Existing action receipt/completion model | Delayed outcome verification, close and adverse-evidence reopen | New MSP semantics tested separately |
| Billing/refund | Existing domain and fixture pack | Access/incident/related-ticket scope | No billing/refund execution path; retain baseline |
| UI and background jobs | Review UI, inbox and policy jobs | Lab API/MCP, synthetic orchestrators | No job cutover or UI replacement justified |

The prospective [maintenance rehearsal](../phase-5/maintenance-rehearsal.json)
applied the frozen 15-to-5-minute policy/version change to isolated copies for
both candidates. Each required one shared policy entry, zero orchestrator edits
and zero workflow-node edits. All three boundary checks (4:59, 5:00, old-policy
approval) passed for each copy, and rollback restored its source.

Recorded patch/test/rollback durations are machine timings, not active human
editing effort. The identical change surface is a consequence of shared domain
controls, not evidence that either engine is easier to operate. Full connected
policy acceptance is in the earlier 17-case runs; this rehearsal checks only
the three domain boundaries. New-connector edits and operator usability remain
unmeasured. Retain the baseline and both bounded prototypes; no engine winner
or removal of active jobs is justified by these checks.

## Persisted timer interruption

Both engines pass the [70-second timer test](../phase-5/timer-comparison.json).
After attempt one, the engine container is killed before its persisted due time.
The fixture target completes while the engine is down. After container/service
restart, the scheduler waits until due, performs attempt two and closes after
read-back. Each journey has one submit call and one effect. No resume webhook is
sent. n8n retains one execution ID across the interruption.

This uses a dedicated 70-second backoff profile so n8n persists the timer. It does
not validate crash recovery for the 1/2/4-second in-process timer profile. The
code worker reads due time from PostgreSQL when relaunched; the harness supplies
the same job configuration. Host/service auto-start deployment, lost HTTP replies,
database restart and distributed ownership remain outside this test. Keep the
short-timer profile a bounded lab fixture rather than treating it as durable.

## HTTP retries and concurrent recovery

[Transport comparison](../phase-5/transport-comparison.json) passes seven cases
per engine: 503 recovery, 429, lost reply after commit, retry exhaustion, 401,
two workers and lock-owner crash. PostgreSQL transaction advisory locks coordinate
recovery ticks while aggregate CAS protects persisted state. A killed lock holder
releases ownership; this is not a fencing lease for network partitions.

Code retries selected transient failures with bounded backoff and stops on 401.
The tested n8n node retries 401 four times as well as transient errors, with fixed
one-second waits. Both persist a review outcome on exhaustion. These behavioral
differences remain relevant to selection; equal scenario pass counts do not imply
identical retry policies. Human maintenance effort, short-timer crash behavior and
baseline feature parity remain open. No final engine selection is made here.
