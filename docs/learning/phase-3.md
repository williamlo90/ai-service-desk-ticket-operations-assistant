# Phase 3 — adapters are contracts before connected evidence

Read migrations/001_service_desk.sql, postgres.py and migrations.py. Transactions
set a tenant context and use explicit tenant predicates. Composite keys and row
policies are defense in depth. The runtime role must not be superuser/BYPASSRLS;
separate migration-owner and runtime privileges during Phase 5. An owner can alter
DDL, so current lab ownership is not a final least-privilege configuration.

The intake adapter uses a unique idempotency scope. The journey adapter locks the
current row, validates revision and audit prefix, then updates state and inserts
the audit event in the same transaction. Migration checksums reject silent edits.
The schema is PostgreSQL-specific; a spy test cannot prove its semantics.

Read jira_update.py and events.py. Summary updates require a bound approval and
fresh preflight read. A reserved operation is never automatically resubmitted,
even after timeout. GET read-back verifies the intended summary. This does not
prove which actor made the change; Jira concurrent-edit/version handling remains
an explicit runtime gate. No live write transport is installed by default.

Callback HMAC binds timestamp and exact body; callbacks are only wake-up hints.
The target read-back drives success. This custom HMAC is for our target contract,
not a claim that Jira webhooks use this signing scheme.

62 tests pass using scripted DB-API spies and fake Jira transport. These verify
parameter binding, transaction intent, checksum behavior, authorization/expiry,
source conflict, callback signature checks and unknown-outcome reconciliation.
No PostgreSQL connection, migration, Jira request or Docker command ran.

Phase 5 must run fresh install + migration replay/checksum rejection, constrained
runtime role/RLS tests, independent-connection CAS/idempotency races, rollback on
audit failure, restart persistence and backup/restore. Single-issue mapping/update
is implemented; Jira search pagination/bulk synchronization requires a separately
bounded integration implementation before it can be claimed complete.

Sources: https://www.psycopg.org/psycopg3/docs/basic/transactions.html and
https://developer.atlassian.com/cloud/jira/platform/rest/v3/api-group-issues/.
psycopg and psycopg-binary are pinned to 3.3.6 for the later runtime environment.
