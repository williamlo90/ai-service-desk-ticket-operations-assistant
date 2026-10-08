# Phase 5 integration handoff — local connected path verified

William authorized Docker use after the offline loop. Existing project PostgreSQL
and n8n containers were healthy on 2026-10-08. Initial PostgreSQL adapter checks
passed in a disposable database inside service-desk-lab-db-1; no service restarted
and no other project was modified. See postgres-contract-check.json.

Seven connected check groups passed: migration/replay/checksum rejection, runtime
privilege boundaries, concurrent intake deduplication, RLS, concurrent CAS/audit,
transaction rollback after audit insert failure, and persisted journey state read
from a fresh Python process. Temporary DB/roles were removed. The generated test
roles are not a deployment of final API identities into the application database.

William requested committing the validated Phase 5 checkpoint before the full
gate is complete, overriding the earlier wait-for-phase-end commit plan. The
phase remains open. Database restart,
architecture comparison and persistent operator deployment remain pending.
Historical offline evidence remains unchanged.

## Current connected checkpoint

- RuntimeAPI serves journey commands and a separate supervisor approval endpoint.
  A small browser proposal-review page is included. Tokens have server-bound expiry;
  Origin/Host checks, body bounds and correlation headers are enforced.
- MCP supports a fixed loopback HTTP backend; it carries only the staff token,
  never the supervisor credential or SQL connection configuration.
- PostgreSQL stores journey/approval/audit state. A separate SQLite synthetic
  target persists its own operation/effect ledger and read-back observations.
- Real subprocess tests cover MCP -> HTTP -> PostgreSQL -> target -> verify/close,
  API restart, fresh MCP connection, adverse-evidence reopen and abrupt worker
  exits before target submission and after the target effect commits. Missing
  target operations remain unknown/manual review; they are not blindly retried.
- 81 Python tests and 8 Node tests pass. The connected harness records 7 database
  groups plus 5 HTTP/MCP/recovery groups in postgres-contract-check.json.

The API/target processes and test database are disposed after checks. No long-lived
operator application was left running, and no existing container was restarted.
The review page was checked through HTTP and handler tests; visual browser QA and
operator authentication UX are pending. This is a single-worker stdlib WSGI lab
adapter, not the final FastAPI/React deployment. /v1/cases remains the legacy intake
record API; /v1/tools/* operates the journey aggregate. A unified intake-to-journey
mapping is still needed for the final application. No architecture winner is claimed.

William is the confirmed business owner. The live target is not ready, and the
operational approver and credentials custodian remain to be designated. Continue
local synthetic work; do not interpret fixture approvals as real authorization.

## Orchestration reference experiment

Actual isolated Python and n8n workers each passed 14/14 base cases and 17/17
policy-v2 cases (62 scenario executions total). The evaluator checks ordered
observations, SQL audit and independent target ledger; expected labels are withheld
from candidates. n8n imports/executes saved HTTP-node workflows in a separate
container, which is restarted at the persisted acceptance boundary. The user's
existing n8n workflows are unchanged. All temporary comparison resources were removed.

See orchestrator-comparison.json and
[ADR 001](../architecture/ADR-001-orchestration-checkpoint.md). This is a bounded
linear-sequence functional comparison. Broader native retry scheduling, baseline
regression parity and measured editing/recovery effort remain open, so no engine
winner is selected. Shared Python domain controls are retained. Unit suite is now
86 Python tests, including evaluator tests for false closure, missing steps,
audit tampering and duplicate effects; the latest Node suite remains 8 tests.

## Native wait/restart checkpoint

Both candidates pass one synthetic access journey with two abrupt engine
kill/start checkpoints: approval wait and target wait. Code uses a durable SQLite
polling checkpoint; n8n resumes the same execution through native webhook Wait
nodes. External fixture events lead to automatic verification and closure, with
one effect per journey. n8n rejects unsigned, old-stage and duplicate callbacks.
See native-wait-comparison.json and the learning guide for reproduction.

All generated resources were cleaned up. Existing application containers and
workflows were unchanged. The shared business database and target were not
restarted. Next: timer interruption, transport retry, baseline
parity, and measured maintenance effort. Live integration still requires its
target and operational identities. This checkpoint does not close Phase 5.

## Bounded recovery checkpoint

Code-led and n8n-led each pass 7/7 cases in recovery-comparison.json: expired and
revoked approval, delayed outcome, terminal failure, response lost after effect,
transient read timeouts and exhausted retry budget. The shared recovery controller
persists attempts and next due time in PostgreSQL; native timer loops schedule
four reads with 1/2/4-second backoff. Target submit-call counts remain zero for
denied approval and one for dispatched cases. Duplicate/late callback hints do
not redispatch or close cases held for review. Late completion after exhaustion
updates evidence while retaining the review escalation.

94 Python unit tests pass, including revocation authorization, attempt budget,
due-time enforcement, last-attempt reservation recovery and read-timeout handling.
The existing Node checkpoint remains 8 tests. All temporary resources were removed.
Escalation is stored on cases, not a deployed queue UI. Short n8n timer waits are
in-process; timer crash and transport retry are not covered by this pack. The
earlier webhook-wait restart proof is separate. Phase 5 stays open; this checkpoint is committed at William's explicit request.

## Ready to integrate

Latest additional checks: both engines pass a 70-second persisted timer crash
test, with two read attempts, one submit/effect, no early retry and no resume
webhook; n8n retains its execution ID (timer-comparison.json). The short 1/2/4-second
profile's crash recovery and host supervisor deployment remain unproven.

The restored Phase 0 baseline passes 47 unit regressions across 11 test files
(baseline-regressions.json). This does not port its billing/refund behavior into
the new runtime. ADR 001 maps the remaining financial, lease, UI and job gaps.
The policy maintenance rehearsal changes one shared entry and zero engine files
or nodes per candidate, with 3/3 boundaries and rollback passing for each copy
(maintenance-rehearsal.json). Machine timings are not human maintenance effort.
No architecture winner, baseline removal or full Phase 5 completion is claimed.

- Python intake API, guarded three-journey service and independent fake target.
- PostgreSQL schema/repositories/migration runner and callback hint verification.
- Scoped Jira reader and approved summary-update contract with injected transport.
- Local TypeScript MCP server/reference client and four Python skill packages.
- Four structured-data provider adapters with no default model or fallback.
- 74 Python tests and 6 MCP tests; evidence in docs/phase-4/offline-check.json.

## Prerequisites before connected actions

William is business owner. Confirm designated supervisor, integration identity,
approved Jira scope and sandbox action targets in phase-0/setup-readiness.md.
Configure credentials privately; do not print .env, headers, or secret bindings.
Choose actual provider/model revisions and permitted synthetic data; record
hardware/license/artifact versions before local inference. Existing accounts do
not by themselves authorize all mutations or establish production readiness.

## Integration order and exit evidence

1. Inspect available resources only when runtime work resumes. Start this project's
   bounded stack with explicit Compose project identity; keep other projects intact.
2. Install pinned dependencies. Apply migrations with a separate owner, configure
   non-superuser/non-BYPASSRLS runtime role, and verify RLS, tenant predicates,
   uniqueness, independent-connection concurrency and rollback on audit failure.
   Test fresh install, migration replay and checksum mismatch.
3. Compose real API deployment, identity validation/rotation, journey endpoints,
   durable repository/worker and target adapter. Connect the reference MCP client;
   implement the user-facing approval flow and planned UI. The current WSGI intake
   and synthetic bridge are separate entry points, not a complete deployed product.
4. Build equivalent code-led and n8n-led vertical prototypes using the shared
   domain controls. Run the frozen independent comparison contract and all 14
   reference scenarios. Kill/restart worker after dispatch reservation and after
   effect-before-response; prove no duplicate effects with target ledger/read-back.
   Include multi-connection races and late callbacks; memory reconstruction is not
   restart evidence. Compare process-change effort and record architecture ADR.
5. Connect Jira and authorized sandbox targets. Add bounded Jira search pagination
   and synchronization for the selected scope. Verify live write/read-back,
   source concurrency handling, permissions, rate limits, unknown outcome review,
   real callback authentication, job retry/DLQ, and second-tenant configuration.
   The custom HMAC callback contract must not be treated as Jira webhook signing.
6. Connect the selected UI/client/MCP/worker path, record correlation IDs without
   sensitive payloads, and test expired identity/approval, injection and output
   bounds. Choose real models and run bounded canaries before Phase 6 evaluation.
7. Rehearse schema/config/job migration and rollback; retain needed baseline jobs
   until replacement is validated. Produce sanitized run IDs/artifacts and rerun
   tests affected by integration fixes. Backup/restore and broader reliability
   acceptance continue in Phase 7; Azure remains Phase 9.

The architecture winner, frozen evaluator, live quality, ROI, persistent restart,
remaining PostgreSQL recovery checks and provider compatibility are pending. Offline unit tests
do not close those gates. The intermediate Phase 5 commit records validated local progress, not a passed final gate.
