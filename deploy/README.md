# Local code-led runtime

Run commands from this project's root in PowerShell. The selected runtime uses
Python/PostgreSQL, the TypeScript MCP server, and the separate Keycloak/demo
target sandbox. It requires Docker Desktop in Linux mode, Python 3.12/3.13 and
Node.js 22. This is a bounded local lab, not a production deployment.

## First-time setup

On a new checkout, prepare the isolated database and install the runtime
dependencies. The `prepare` command creates private local database secrets
without printing them:

```powershell
python -m venv .venv
& ./.venv/Scripts/python.exe -m pip install -r backend/requirements-postgres.txt
npm ci --prefix mcp-server --ignore-scripts --no-audit --no-fund
npm run build --prefix mcp-server
./scripts/runtime.ps1 prepare
./scripts/runtime.ps1 start-db
python -B scripts/cache_keycloak_image.py
python -B scripts/setup_target_sandbox.py
& ./.venv/Scripts/python.exe -B scripts/operator_lab.py setup
```

On an already-provisioned lab, reuse the existing `.venv`, private secret
files and data volumes; do not create a replacement identity or database.
The target setup above is scoped to this project's Keycloak and demo service.
To import Jira IT-1, configure your own authorized sandbox credentials in
the ignored local `.env` using [the example](../.env.example), then follow
the bounded [operator lab procedure](../docs/phase-5/OPERATOR-LAB.md).
That import is a Jira read, not an approval or target action.

## Start an already-provisioned lab

Start only this project's database and target sandbox, then the supervised API,
worker and bounded poller. Port 5681 must be free:

```powershell
./scripts/runtime.ps1 start-db
docker compose --env-file deploy/compose.empty.env -f deploy/targets.compose.yaml -p service-desk-targets up -d
./scripts/operator-service.ps1 Start
& ./.venv/Scripts/python.exe -B scripts/operator_health.py
```

Read [the operator guide](../docs/phase-8/HANDOVER.md) for daily use, status
meanings, identity renewal, backup/recovery and safe shutdown. `ready` is a
point-in-time diagnostic, not proof that every open case is resolved.

Stop only this project's services, without deleting data:

```powershell
./scripts/operator-service.ps1 Stop
docker compose --env-file deploy/compose.empty.env -f deploy/targets.compose.yaml -p service-desk-targets stop
./scripts/runtime.ps1 stop-db
```

No other project's containers are changed. A host reboot does not automatically
start the supervisor; restart the owned services as described in the operator
guide.

## Optional n8n comparison

n8n is **not required** for the delivered code-led runtime. If you explicitly
want to inspect the retained workflow prototypes, start this project's n8n
only after the database is healthy:

```powershell
./scripts/runtime.ps1 start-n8n
```

Open `http://localhost:5678` and create its local instance owner account
yourself. The n8n account is separate from Atlassian. Stop it with
`./scripts/runtime.ps1 stop-n8n`; this does not stop the code-led operator.

## Storage and credentials

- Project/network: `service-desk-lab`, `service-desk-lab_service_desk`.
- Data volumes: `service-desk-lab_postgres_data`; optional n8n uses
  `service-desk-lab_n8n_data`.
- External private secret volumes: `service-desk-lab_secrets` and, when n8n is
  enabled, `service-desk-lab_n8n_secrets`. The latter contains only n8n's DB
  password and key.
- Generated source secrets: `%LOCALAPPDATA%\ServiceDeskLab\secrets`, outside OneDrive
  and Git, with restricted Windows directory permissions. Never print their contents.
- Compose always receives the explicit empty `deploy/compose.empty.env`; it never
  loads the project's Jira `.env`. No Jira token is sent to these containers.
- `prepare` reuses existing secret files. Do not delete/regenerate them against
  existing databases: changing a file does not rotate a PostgreSQL password.
  Losing n8n's encryption key makes stored workflow credentials unrecoverable.
- These are local file/volume secrets, not an encrypted secret manager. A user with
  Docker administrator access can access them. Volume backups and restore rehearsal
  remain pending; restart persistence is not a backup/restore test.

Separate DB owners `service_desk_app` and `service_desk_n8n` have no superuser,
create-role or create-database privileges. Cross-database connections are denied.
DB ownership supports future migrations; it is not a final least-privilege API role.
The local API binds trusted identities to tenants and enforces tenant checks;
the PostgreSQL runtime has RLS and cross-tenant denial tests. Those controls
do not constitute a production identity provider or enterprise access review.

## Resource policy

Staged startup was explicitly authorized on 2026-10-08. The old 4 GiB check is a
conservative full-stack guard, not a Docker requirement. Database startup requires
1 GiB host headroom with a 512 MiB / 0.5 CPU cap; n8n requires 1 GiB host headroom
AND 2 GiB Linux MemAvailable, with a 1 GiB / 1 CPU cap and 640 MiB Node heap.
Host and Linux memory figures overlap and must not be added. This considers Linux
reclaimable cache rather than relying solely on Windows free RAM. These are working lab guards, not capacity
guarantees. Stop the newest lab service if it OOMs or the host becomes unresponsive.
No load tests or model inference are included. n8n idle readiness does not establish
capacity for real workflows.

Database port: `127.0.0.1:5433`; editor: `127.0.0.1:5678`. No public tunnel, privileged
container, Docker socket mount, or external task-runner sandbox is configured.

## Verification boundaries

`check_database.py` uses only project-owned containers and synthetic data. It checks
TCP authentication, wrong-password rejection, database separation, role privileges,
restart persistence, resource caps and loopback binding. It removes its synthetic
table afterwards; the script restarts only `service-desk-lab-db-1`. Run it before
starting workflows, not while n8n has active executions.

Database init scripts run only against an empty data volume. Editing `init.sh`
does not migrate an existing database. Do not use `down -v` as an update mechanism.

Upstream references: [pgvector](https://github.com/pgvector/pgvector),
[Postgres image](https://hub.docker.com/_/postgres),
[n8n configuration](https://docs.n8n.io/deploy/host-n8n/configure-n8n/basic-configuration.md).

## PostgreSQL adapter integration checks (Phase 5)

With this project's database already running, create the ignored project .venv
if needed (`python -m venv .venv`). Install dependencies and build MCP first:

```powershell
& ./.venv/Scripts/python.exe -m pip install -r backend/requirements-postgres.txt
npm --prefix mcp-server ci --ignore-scripts --no-audit --no-fund
npm --prefix mcp-server run build
& ./.venv/Scripts/python.exe -B scripts/check_postgres_contracts.py
```

This script exercises the actual Python repositories and migration runner through
TCP. It creates a random sdcheck_* database and separate migration/runtime roles,
then removes only those resources in cleanup. Existing application/n8n databases
are untouched. It does not restart containers or read the project's .env. The
existing database administrator secret is consumed inside the DB container only;
generated disposable role passwords pass through stdin, never command arguments
or logs. Results contain fixed check labels, never raw database exceptions.

It verifies migration replay/checksums, least-privilege runtime grants, tenant RLS,
independent-connection idempotency/CAS, audit rollback and fresh-process reads of
persisted journey state. It also starts a temporary loopback API and MCP clients,
checks approval/closure/reopen through real HTTP, terminates/restarts the API and
crashes workers before/after a durable synthetic target effect. Only those owned
processes are terminated. It does not prove database restart/backup recovery, live
target actions or the frozen architecture comparison. All temporary API processes,
SQL database and generated roles are cleaned up after the check. Local target
ledgers remain in ignored `local/` directories for diagnosis.

## Keycloak and demo targets

William selected this independent local sandbox. Keycloak listens on
`http://localhost:8085`; the demo health endpoint is
`http://localhost:8086/healthz`. Compose project `service-desk-targets` has its own
network and volumes. It does not mount the Docker socket or change existing n8n
workflows. Keycloak uses development mode and H2, for this lab only.

```powershell
python -B scripts/cache_keycloak_image.py
python -B scripts/setup_target_sandbox.py
& ./.venv/Scripts/python.exe -B scripts/check_demo_target.py
& ./.venv/Scripts/python.exe -B scripts/check_lab_access.py
& ./.venv/Scripts/python.exe -B scripts/check_postgres_contracts.py --lab-targets
```

The image cache script verifies official registry layer/config digests before
loading the image. Setup checks the pinned image ID before starting Keycloak.
Compose receives an explicit empty env file. The project `.env` is not read.
Generated credentials are kept under the current user's
`.codex/private/service-desk-targets/bootstrap.json`, with restricted Windows
directory permissions, and consumed internally by scripts. Do not paste this
file into chat, logs or Git. The technical bootstrap username is
`service-desk-bootstrap`; it is not an operational role assignment.

Each realm (`sd-lab-alpha`, `sd-lab-beta`) has a separate integration client,
requester and `reports-reader` group. Clients are denied access to the other
realm. Their own-realm `manage-users` permission is broader than group membership;
the adapter additionally limits actions to the configured requester/group.
Demo tokens are tenant-specific and control only a dedicated child process.
Repeated operation IDs cannot trigger another restart.

Connected acceptance uses temporary API/SQL resources and fixture supervisor
identities. Access tests restore original membership. Service tests deliberately
restart only the dedicated demo children. The sandbox containers and persistent
volumes remain available afterward. William is the confirmed lab operational approver and credential custodian;
these scripts do not represent human acceptance. See
[operator lab](../docs/phase-5/OPERATOR-LAB.md) for the persistent API and IT-1 review.

Reference: [official Keycloak Docker guide](https://www.keycloak.org/getting-started/getting-started-docker)
and [Admin REST API](https://www.keycloak.org/docs-api/latest/rest-api/index.html).
