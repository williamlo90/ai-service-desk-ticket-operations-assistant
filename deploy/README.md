# Local runtime

Run commands from this project's root in PowerShell. Requires Docker Desktop in
Linux mode and Python 3.12+. This is a local prototype, not a production deployment.

```powershell
powershell -NoProfile -File scripts/runtime.ps1 prepare
powershell -NoProfile -File scripts/runtime.ps1 start-db
python -B scripts/check_database.py
powershell -NoProfile -File scripts/runtime.ps1 start-n8n
powershell -NoProfile -File scripts/runtime.ps1 status
```

Open http://localhost:5678 and create the instance owner account yourself. Keep
its password private. This is a local n8n account, separate from Atlassian. Owner
setup, service identity and workflow configuration are not implied by health checks.

Stop only this project's services, without deleting data:

```powershell
powershell -NoProfile -File scripts/runtime.ps1 stop-n8n
powershell -NoProfile -File scripts/runtime.ps1 stop-db
```

Both services use `restart: no` so restarting Docker does not automatically start
this lab. Start database first and n8n second. No other project's services are changed.

## Storage and credentials

- Project/network: `service-desk-lab`, `service-desk-lab_service_desk`.
- Data volumes: `service-desk-lab_postgres_data`, `service-desk-lab_n8n_data`.
- External private secret volumes: `service-desk-lab_secrets` and
  `service-desk-lab_n8n_secrets`. The latter contains only n8n's DB password and key.
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
Application tenant authorization is still a separate implementation task.

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
target files, SQL database and generated roles are cleaned up after the check.
