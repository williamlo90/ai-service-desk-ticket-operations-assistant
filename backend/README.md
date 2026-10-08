# Backend core and container-free API

Python 3.12 or 3.13, standard library only. No installation, credentials, Docker,
database, model call or persistent server is needed for unit verification.

From this directory:

```powershell
python -B -m unittest discover -s tests -v
```

Implemented modules:

- `contracts.py`: typed ticket, trusted actor context and staff/tenant boundary.
- `jira.py`: GET-only reader with configured tenant/project binding, fixed Atlassian
  gateway, no redirects/retries, response bound and sanitized errors.
- `lifecycle.py`: pure approval/expiry, verified-closure, safe-retry and reopen predicates.
- `auth.py`: explicit local bearer-token bindings to trusted server identity.
- `cases.py`: synthetic intake, repository protocol and bounded memory implementation.
- `api.py`: WSGI create/read API tested without running a server. See [API.md](API.md).

- `journeys.py`, `policy.py`, `store.py`, `simulator.py`: shared deterministic journeys,
  bounded memory state and an independent synthetic target/effect ledger.
- `postgres.py`, `migrations.py`, `migrations/`: transactional repositories and schema.
- `jira_update.py`, `events.py`: guarded update/reconciliation and signed callback hints.
- `skills.py`, `ai.py`: reusable handlers and four structured-data provider adapters.
- `bridge.py`: synthetic JSON-lines subprocess API for the TypeScript MCP harness.

Current suite: 74 Python tests; 6 MCP tests run separately in ../mcp-server.
PostgreSQL adapter uses pinned optional requirements-postgres.txt only during
runtime integration; unit tests use stdlib spies. No API listener or real local
API credentials are configured. See ../docs/phase-5/HANDOFF.md for connected gates.

Construct `JiraConnection` from trusted server configuration and an `Actor` only
after authentication. Ticket text is untrusted data and cannot assign tenant or role.
The reader has no .env loader and does not call the network until `read` is invoked.
Credentials are omitted from repr, but remain secrets in memory: do not dump objects,
request headers, traceback locals or dataclass dictionaries.

JourneyService binds the pure predicates to state/version updates and target
read-back. SQL adapters express transactions, but real PostgreSQL concurrency,
audit rollback, restarts and RLS are not proven by spies or memory-store tests.
Do not expose a network endpoint that accepts an Actor/Approval/VerifiedOutcome
directly from client data. FastAPI deployment, production identity integration,
actual migrations and connected n8n/code-led comparison remain pending. The WSGI
adapter uses explicit development identity bindings. The MCP bridge has a separate
in-memory journey store; connecting entry points to one durable store is Phase 5.

The existing `../scripts/check_jira_read.py` remains the separately authorized
live diagnostic. It is not run by this unit suite, and its previous live result is
not a live validation of the new adapter. No .env was inspected during Phase 1A.
