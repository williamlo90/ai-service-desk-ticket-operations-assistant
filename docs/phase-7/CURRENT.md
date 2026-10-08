# Phase 7 — bounded local release complete

2026-10-09, Asia/Jakarta. [Gate](phase7-gate.json): passed.
The urgent delivery scope prioritizes approval safety, duplicate prevention,
recovery and a small measured workload. Azure remains deferred.

## Evidence

[Release rehearsal](release-lab.json) used a disposable PostgreSQL database, the
real HTTP/domain code and a separate durable SQLite synthetic target. Fixture
approvals are not William's approvals. No Jira, model, Keycloak or demo-service
mutation occurred; no shared container was stopped. The temporary database was removed.

- Unauthorized execution, staff self-approval, cross-tenant read, external Origin
  and injected tool arguments were denied with zero effects; expired approval was denied.
- A worker exited abruptly after the target effect but before its receipt. A fresh
  API process read the same durable operation, verified and closed it; replay added no effect.
- Eight concurrent/replayed dispatch calls created one operation and one effect.
- A database advisory-lock session was terminated while dispatch was paused. A
  competing worker reconciled the reserved operation without resubmitting it.
- An isolated database outage returned sanitized 503 responses, prevented new
  writes/effects and recovered after connectivity was restored.
- 48 HTTP journeys completed: 8 sequential, 16 at concurrency four, 24 during a
  61-second low-rate soak. No errors, extra effects or audit-count mismatches.

| Workload | End-to-end p95 | Dispatch acknowledgement p95 |
| --- | --- | --- |
| Sequential | 812ms | 231ms |
| Concurrency four | 1,876ms | 539ms |
| Smoke soak | 658ms | 175ms |

End-to-end includes create, prepare, fixture approval, dispatch and verified closure.
These are closed-loop synthetic measurements on a shared host, not live-target/AI
latency or a capacity forecast. All pass the predeclared 10-second local p95 budget.

[Phase 5 restore](../phase-5/operator-migration-check.json),
[cutover/rollback](../phase-5/job-cutover-check.json) and
[child restart](../phase-5/operator-supervisor-check.json) remain the applicable
storage/integration evidence; their experiments were not unnecessarily repeated.
Current tests cover delayed observations, permission/expiry, retry budgets and
adverse verification. **179 Python, 8 MCP and 14 JavaScript checks pass.**

## Fix and operations

The worker now applies its 100-job limit to eligible active jobs. Closed history,
unapproved intake and escalated jobs no longer block an otherwise small active
queue. It still reads tenant history before filtering; large-dataset pagination is
future work. Regression tests cover eligible-limit enforcement and excluded history.
The project-owned idle worker was reloaded; runtime health remained ready.

`python scripts/operator_health.py` reports bounded alert codes for stale/missing
heartbeats, unavailable API, blocked polling, review-required jobs and expired or
soon-expiring identities. It never prints credentials/payloads or sends external
notifications. [Observed runtime health](operator-health.json) was ready with no alerts.

## Operational limits

Manual startup after a host reboot remains required. The rehearsal restarted
application processes, not Windows or Docker. The claim-session test is not a
wire-level partition/fencing proof. A 60-second soak does not establish endurance.
Only OpenAI is quality-accepted; Ollama remains experimental and Claude/Grok are
deferred. Local V1 is a lab release, not an unattended production service.

Next: Phase 8 clean-source verification, operator runbook, demo and handover manifest.
