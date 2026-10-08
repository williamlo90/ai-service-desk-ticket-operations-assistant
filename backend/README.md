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

Current suite: 39 tests (22 original core tests plus 17 API tests). Docker-backed
integration is deferred; no API listener or real local API credentials are configured.

Construct `JiraConnection` from trusted server configuration and an `Actor` only
after authentication. Ticket text is untrusted data and cannot assign tenant or role.
The reader has no .env loader and does not call the network until `read` is invoked.
Credentials are omitted from repr, but remain secrets in memory: do not dump objects,
request headers, traceback locals or dataclass dictionaries.

The pure lifecycle predicates do not implement a persisted state machine. In Phase
1B the application must bind authenticated identity, verify target evidence, and
run predicates and state/version updates in a database transaction. Durable audit,
idempotency, concurrency, callback ordering and restarts are not proven by unit tests.
Do not expose a network endpoint that accepts an Actor/Approval/VerifiedOutcome
directly from a client. FastAPI deployment, identity-provider integration, migrations
and the connected n8n prototype remain pending. The in-process WSGI adapter uses
explicit development token bindings. No read-only test proves a token lacks write access.

The existing `../scripts/check_jira_read.py` remains the separately authorized
live diagnostic. It is not run by this unit suite, and its previous live result is
not a live validation of the new adapter. No .env was inspected during Phase 1A.
