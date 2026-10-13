# Service desk backend

The selected local runtime is Python/PostgreSQL. The backend owns tenant
authorization, proposal versions, human-approval checks, dispatch ownership,
target read-back, case state and audit. The TypeScript MCP server calls this
service through a bounded loopback HTTP adapter; MCP cannot approve a proposal.

## Verify without credentials

Python 3.12 or 3.13 is sufficient for the offline unit suite. From this folder:

```powershell
python -B -m unittest discover -s tests
```

At the current portfolio revision, **183 Python tests** and **8 MCP tests**
pass in [CI](../.github/workflows/ci.yml). CI also checks the approval
controller, grounded next-step guidance, the offline recovery demo and Git
history. The offline suite uses synthetic targets and does not read `.env`,
contact Jira or Keycloak, or prove production operations.

## Main components

| Component | Responsibility |
| --- | --- |
| `contracts.py`, `auth.py`, `policy.py`, `lifecycle.py` | Trusted actor and tenant boundaries, deterministic proposals, approval expiry and verified closure |
| `journeys.py`, `store.py`, `postgres.py`, `migrations.py` | Case lifecycle, compare-and-swap persistence, tenant RLS and audit |
| `runtime_api.py`, `skills.py` | Loopback HTTP API, separate supervisor approval route and bounded tool handlers |
| `jira.py`, `jira_update.py`, `jira_links.py` | Scoped Jira reads, guarded result writes and related-ticket links |
| `simulator.py`, `durable_target.py` | Synthetic target effects and independent read-back for offline/recovery checks |
| `bridge.py` | Disposable JSON-lines subprocess for the MCP protocol harness |

The subprocess bridge owns a **separate in-memory synthetic store** in its
offline mode. Connected MCP mode calls the HTTP API and shares its PostgreSQL
case state instead. See the [MCP contract](../mcp-server/README.md) and
[API contract](API.md).

The API binds to `127.0.0.1`, consumes explicit server-side configuration and
keeps caller identity outside tool arguments. The browser page records a
version- and payload-bound human approval; a separate worker executes and
verifies. Ticket text cannot assign a tenant, role or approval. Do not log
headers, tokens, traceback locals or raw credential-bearing configuration.

## Connected local evidence

The [Phase 5 gate](../docs/phase-5/CURRENT-GATES.md) covers PostgreSQL
migrations/RLS, real HTTP/MCP calls, scoped Jira operations, a William-approved
IT-1 access grant and Keycloak membership read-back. The Jira result is an
issue property; it did not transition the ticket or add a comment.

The [Phase 7 exercise](../docs/phase-7/CURRENT.md) covers a lost receipt,
worker/API restart, concurrent replay, database outage and a bounded synthetic
HTTP workload. The [Phase 8 handover](../docs/phase-8/README.md) records the
accepted local source delivery and operator procedures. These reports describe
their own recorded revisions; they are not new live runs performed by CI.

For setup and day-to-day use, start with [local deployment](../deploy/README.md)
and the [operator guide](../docs/phase-8/HANDOVER.md). Azure hosting, production
identity, high availability and long-duration capacity have not been accepted.
