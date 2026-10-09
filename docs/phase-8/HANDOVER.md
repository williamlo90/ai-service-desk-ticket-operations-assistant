# Operator handover — local lab

Owner, operational approver, credential custodian and support owner: **William**.
Accepted AI profile: OpenAI. Ollama is experimental; Claude/Grok and Azure are deferred.
This guide describes the tested Windows lab. It does not authorize a new business action.

## Start here on the existing machine

From the project directory, check health:

```powershell
./.venv/Scripts/python.exe -B scripts/operator_health.py
```

`ready` means the API, supervisor/worker heartbeats, enabled poller and identity
expiry checks passed. This is a point-in-time runtime diagnostic, not an exhaustive durable review-queue
check or an external alert service. Review persisted open/escalated cases separately.
If runtime is stopped, start the project's dependencies and operator supervisor:

```powershell
./scripts/runtime.ps1 start-db
docker compose --env-file deploy/compose.empty.env -f deploy/targets.compose.yaml -p service-desk-targets up -d
./scripts/operator-service.ps1 Start
./.venv/Scripts/python.exe -B scripts/operator_health.py
```

Allow startup to finish before evaluating health. Do not start another API on port
5681. Optional n8n is not required by the selected code-led runtime. After a host
reboot, start Docker Desktop and repeat these steps; no OS autostart is installed.
Stop the operator with `./scripts/operator-service.ps1 Stop`. Do not stop other
projects' containers. Stopping services preserves their volumes and approvals.

## Daily use and status meanings

1. Open `http://127.0.0.1:5681/?case=7c72fff3-881e-571e-9be7-aed9870482bc`
   to inspect the existing IT-1 lab case. It is already closed; it is not a new approval task.
2. For an open proposal, use William's private approval-token file, review the
   tenant, requester, action and proposal version, then approve only the intended action.
   The token stays in the browser page, not local storage. Never paste it into chat.
3. The worker executes only approved jobs. Approval expires after its policy window
   (15 minutes for access). Changed proposal/source or expired approval needs review.
4. `accepted`/`requested` is a receipt, not success. `unknown` means the outcome
   requires read-back; do not create another action to retry it. Only verified
   completion permits local closure. A ticket relationship alone does not resolve an incident.
5. A failed or ambiguous job stays open/escalated for the operator. Inspect its
   correlation ID and bounded health alert; avoid sharing raw logs or configuration.

Polling is explicitly limited to Jira IT-1 and IT-2 every 60 seconds. The original
access grant remains in place. Local closure does not imply a Jira workflow-status
transition. Expanding ticket/user/group scope needs a deliberate configuration and
acceptance change; arbitrary tickets are not automatically enrolled.

## Short offline demo

The Phase 6 human pilot is retained as an evaluation artifact; it is not part of
daily operator use. The operator-facing browser page at port 5681 only handles
independent human approval.

For a reproducible terminal demo without credentials or Docker:

```powershell
python -B scripts/demo_handover.py
```

It demonstrates rejected unapproved execution, a lost receipt remaining open,
verified reconciliation and replay with one synthetic effect. Its supervisor is an
explicit test fixture, not William. It does not repeat live Jira/Keycloak acceptance.

## Troubleshooting and renewal

| Alert/state | Operator action |
| --- | --- |
| `api_not_ready` | Check this project's database and supervisor. Avoid starting a duplicate API. |
| `worker_heartbeat_stale` / missing | Check supervisor status; restart the owned service after confirming pending work. |
| `poll_manual_resume_required` | Resolve credential/network/rate-limit issue first; respect Jira Retry-After, then create `local/operator-lab/resume-jira-poll`. |
| `identity_expired` / expires within hour | Stop the owned service and rotate local identities using the procedure below. |
| `job_review_required` | Inspect source/approval/target result. Do not erase the operation ID or retry budget. |
| `unknown` outcome | Read back the same operation. If unresolved, keep open and escalate to William. |
| `queue_scan_limit` | Review the active queue; closed history no longer consumes this limit. Do not raise limits without sizing. |

Local bearer identities expire after 24 hours. To renew them:

```powershell
./scripts/operator-service.ps1 Stop
Start-Sleep -Seconds 16
./.venv/Scripts/python.exe -B scripts/renew_lab_identity.py --rotate
./scripts/operator-service.ps1 Start
./.venv/Scripts/python.exe -B scripts/operator_health.py
```

Renewal preserves role/tenant bindings and database credentials, invalidates old
bearer tokens and saves new approval tokens privately. It does not approve any job
or renew an expired business approval. Update an open browser with the new token.
The private token path is `%USERPROFILE%/.codex/private/service-desk-targets/william-alpha-approval-token.txt`.
Current expiry is checked by the health script; older evidence timestamps are historical.

## Clean install / restore on another workstation

Prerequisites: Python 3.12/3.13, Node 22–26, npm, Git, Docker Desktop and PowerShell.
Use the delivered source archive or Git checkout. Install pinned dependencies:

```powershell
python -m venv .venv
./.venv/Scripts/python.exe -m pip install -r backend/requirements-postgres.txt
Push-Location mcp-server
npm ci --ignore-scripts --no-audit --no-fund
npm test
Pop-Location
Push-Location backend
../.venv/Scripts/python.exe -B -m unittest discover -s tests
Pop-Location
python scripts/demo_handover.py
```

Clean-source installation/tests were rehearsed on this host in an isolated venv and
fresh npm tree. This does not claim a second Windows host or new SaaS account was provisioned.
For a **new empty sandbox**, follow [deployment setup](../../deploy/README.md):
prepare/start the database, cache the verified Keycloak image, run target-sandbox
setup and `operator_lab.py setup`, then start the supervisor. Required commands:

```powershell
./scripts/runtime.ps1 prepare
./scripts/runtime.ps1 start-db
./.venv/Scripts/python.exe -B scripts/cache_keycloak_image.py
./.venv/Scripts/python.exe -B scripts/setup_target_sandbox.py
./.venv/Scripts/python.exe -B scripts/operator_lab.py setup
```

Jira/OpenAI credentials are separately provisioned into the ignored `.env`, using
blank `.env.example` as the variable template. Never overwrite an existing `.env`.
The source package contains no keys, bearer identities, databases or model weights.
IT-1/IT-2 and tenant allowlists belong to William's current lab, not a universal setup.
Do not replay setup against restored persistent volumes with newly generated secrets.

## Backup, recovery and upgrades

Before an upgrade, stop the operator so it cannot dispatch while state is copied.
Keep the current Git commit, source package and an encrypted/private backup of the
PostgreSQL application data, operator config/bindings, target SQLite state and target
volumes. Keep original database passwords and the optional n8n encryption key with
the recovery set. Runtime secrets live outside Git under `.codex/private/service-desk-targets`
and `%LOCALAPPDATA%/ServiceDeskLab/secrets`; Docker secret volumes are also needed.
Do not expose these backups in the source archive or chat.

[Phase 5 restore rehearsal](../phase-5/operator-migration-check.json) verifies logical
application-table restore, not an all-volume disaster-recovery backup. Its ignored
snapshots are engineering fixtures, not a scheduled production backup. Use
`check_operator_migration.py` only for a deliberate bounded restore rehearsal;
it creates/drops a temporary database, reads the current source and writes local
snapshot evidence. It does not replace the live database.

Apply migrations with the migration-owner connection, not the runtime role. First
validate a new version in an isolated database. Roll back code/config and affected
schema together only after verifying compatibility. Reconcile unknown operations
before resuming jobs; a database rollback does not undo an external effect.
[Cutover rehearsal](../phase-5/job-cutover-check.json) demonstrates quiesced synthetic
job movement/rollback. No automatic rollback or backup scheduler is installed.

Keep baseline jobs/workflows until their replacement is separately proven. n8n does
not own V1 orchestration; no production workflow export is required for this release.
Existing optional n8n workflows remain unchanged. Do not activate comparison fixtures
as production automation. Follow [ADR 003](../architecture/ADR-003-selected-code-led.md).

## Ownership, retention and support cadence

William checks health before a demo/work session, reviews open/escalated outcomes
at the end, and renews identities before expiry. Review dependency/prompt/policy
changes with relevant tests and a fresh model holdout when needed. Record incidents
without tokens or raw sensitive payloads. Costs: hosted AI usage is metered; recorded
Phase 6 estimate is $0.0164488 across 70 calls, not an invoice or future budget.
Local hardware/electricity and SaaS subscription costs are not measured here.

Current data is lab/synthetic. Audit/operation receipts must remain available while
jobs can replay. No automatic retention deletion is installed. William decides when
completed lab records and backups can be retired; never delete an unknown outcome.
Stop owned services before retiring the installation. Retain/export required data
and credentials first; no `down -v` cleanup is part of normal shutdown.

## Remaining deployment work

Azure, unattended production identity, physical reboot acceptance, long endurance,
wire-level partition fencing and full-volume disaster recovery remain outside this
lab delivery. Ollama improvements and Claude/Grok canaries are future work. The
current assistant's AI path is advisory/practice; domain approval and verified
execution remain controlled by the code-led operator runtime.
