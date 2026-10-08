# ADR 003 — code-led orchestration with outbound Jira polling

Date: 2026-10-08. Status: accepted architecture decision for V1 by delegated owner
authority. William explicitly authorized the implementer to choose the best
approach and record the reasons. Supersedes the open engine decision in ADR 001
and the provisional operating scope in ADR 002. Historical measurements remain
valid within their documented scope.

## Decision and reasons

Use Python domain services and PostgreSQL as the orchestration core, with the
TypeScript MCP client and browser approval UI as callers. Run API, approved-job
worker and bounded Jira poller under one local process supervisor. Keep n8n as
an optional integration client of the same API; it does not own action state,
approval, retry budgets or dispatch for V1.

This project requires strict approval binding, tenant separation, transactional
audit and reconciliation after uncertain outcomes. Those controls already live
in the shared Python service and PostgreSQL. Code-led operation uses those
controls directly and avoids introducing a second engine's execution lifecycle
as an additional source of operational state. The working human-approved
Keycloak journey is already on this path.

Both reference engines passed 14 base cases, 17 policy cases and the recovery
packs. n8n is technically capable. The decision is a fit and operational-complexity
judgment, not a claim that Python measured faster or cheaper. Machine policy-edit
timings do not establish human maintenance effort. Under the owner's new
delegation, those missing comparative UX measurements no longer prevent this
architecture choice; they remain unmeasured, not retroactively passed.

The tested code transport distinguishes permanent authentication failure from
retryable errors. The tested n8n node retried 401 four times. The n8n short-timer
crash limitation is also irrelevant to the selected runtime; its 70-second timer
proof remains a bounded comparison result. A future n8n-heavy design must revisit
these policies rather than inherit this decision by name.

## One owner for each responsibility

| Responsibility | V1 owner |
| --- | --- |
| Case, approval snapshot, operation ID and audit | PostgreSQL |
| Permission, freshness, verification and closure | Python domain service |
| Due times, attempts and escalation | Persisted RecoveryController state |
| Job scanning and dispatch | Python worker, only after a stored valid approval |
| API/worker/poller process restart | Local supervisor while it is running |
| Jira ingestion | Outbound authenticated polling of configured test keys |
| Jira result/link reconciliation | Dedicated adapters and durable attempt journals |
| Business/operational approval and credentials | William |

## Polling instead of inbound Jira webhooks

V1 polls only configured lab keys over authenticated HTTPS, once per minute,
with bounded cursor pagination. It reimports idempotently and exposes source
drift for review. The worker rechecks a Jira-backed source before processing
an approved job. A failed poll is latched for review; it is not automatically
retried on 401, 403 or 429. Restart the poll component explicitly after remediation.

No Jira webhook receiver is deployed, so there is no claim that the project's
custom HMAC envelope authenticates Jira events. The callback module is retained
as a separately tested contract. Polling trades immediate delivery for a bounded
delay and avoids an inbound public endpoint/tunnel in the local lab.

## Scope and tradeoffs

- Supervisor restart covers child-process failure, not host reboot or supervisor
  death. Host recovery, unattended startup and soak/load hardening remain Phase 7.
- Advisory locks coordinate cooperative workers; they are not distributed fencing
  across network partitions. Single-host operation is the supported V1 scope.
- Source preflight checks are not atomic cross-system transactions. Changed
  sources and uncertain outcomes stop for review.
- Billing/refund baseline jobs are retained and their 47 regression tests remain
  separate. V1 adds service-desk journeys without cutting those jobs over; no
  feature-parity or replacement claim is made for unrelated baseline workflows.
- n8n user workflows and other projects remain intact. No data or workflows are
  removed just because code-led orchestration was selected.

## Evidence

See the Phase 5 comparison, transport, timer, connected-target and
human-approved-access reports. `operator-supervisor-check.json` proves API and
worker crash recovery with unchanged case/operation and entitlement.
`job-cutover-check.json` proves quiesced cross-database synthetic-job cutover and
rollback with one independent target effect. Neither is a cloud release claim.

Revisit this ADR if connector volume, operator skill mix or measured maintenance
cost justifies n8n owning more orchestration. Keep domain controls authoritative
in either design.


## Final local acceptance

The Phase 5 gate now passes. Live Jira IT-2 creation, related-link read-back,
replay, two-page synchronization and negative-token denial were verified.
The authenticated one-minute poller is enabled for IT-1/IT-2. The user selected
an unscoped personal token for the lab, so live scripts use the explicit site
origin; connection code validates HTTPS Atlassian origins and disables redirects.
See jira-connected-check.json, jira-poll-check.json and phase5-gate.json.
