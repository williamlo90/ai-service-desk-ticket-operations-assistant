# ADR 002 — local operator execution ownership

Date: 2026-10-08. Status: accepted for the current bounded local operator lab.
Final code-led versus n8n-led selection remains governed by ADR 001 and the
comparison contract; this decision does not declare an engine winner.

## Operating decision

Continue the working code-led operator path: browser approval, staff MCP client,
loopback Python API, PostgreSQL state and exact-target adapters. The actual
William-approved access journey has passed this path. Keep existing n8n workflows
and baseline jobs intact; they are not part of this operator dispatch path.

| Responsibility | Single authority in the operator lab |
| --- | --- |
| Human approval | William through the separate supervisor endpoint |
| Authorization, proposal binding and closure | Python domain service |
| Case, approval, operation ID and audit | PostgreSQL |
| Authoritative membership and health | Keycloak and demo service respectively |
| Recovery budget and next due time | Persisted Python RecoveryController state |
| Recovery tick concurrency | PostgreSQL advisory transaction lock plus aggregate CAS |
| Operator execution | Explicit staff MCP invocation; no unattended scheduler installed |
| Jira outcome publication | Dedicated property writer with durable attempt journal and read-back |
| Credential custody | William; private local files consumed internally |

The operator workflow is manually started and explicitly invoked. Reference
recovery workers prove bounded recovery behavior but are not an installed Windows
service or a production queue. Do not claim unattended restart recovery for this
operator deployment. An ambiguous Jira PUT is reconciled by GET; a missing result
after an uncertain attempt requires review, not another PUT. A definite 401/403
rejection allows a later manual run after credentials are fixed.

## Why the final comparison is still open

Both reference engines pass the measured base, policy, recovery and transport
packs. The code retry implementation stops on 401; the tested n8n node repeats it.
This is a real behavioral difference, but not the entire agreed selection rubric.
Active human maintenance effort and baseline feature parity remain unmeasured.
The contract explicitly says to continue the bounded prototype when evidence is
insufficient. Current machine patch timings cannot substitute for human effort.

Therefore preserve both candidates and use the already validated operator path
for ongoing integration. Do not remove baseline billing/refund jobs, report an
engine performance winner, or close the final architecture gate on this evidence.

## Migration evidence

[Operator migration rehearsal](../phase-5/operator-migration-check.json) passes
logical application-table restore, migration replay, additive schema rollback,
failed-DDL transaction rollback, a completed-operation replay without target I/O,
and synthetic in-flight reconciliation across schema changes. One real closed
case and eight audit rows were copied; beta had no source rows, and its in-flight
job was added only to the disposable clone with a fixture approval.

This is not a live cutover, database-volume restore, n8n execution-state migration
or rollback of external effects. The original database and approved entitlement
were preserved; the temporary database was removed.
