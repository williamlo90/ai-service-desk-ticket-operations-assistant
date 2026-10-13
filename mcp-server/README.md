# Local MCP reference implementation

Eight strict tools expose bounded service-desk operations through the SDK's
MCP stdio transport. The offline test mode calls a disposable Python JSON-lines
bridge; connected local mode calls the loopback HTTP API backed by PostgreSQL.
The private bridge is not a second MCP implementation. Neither mode gives the
tool caller approval authority.

Prerequisites: Python 3.12/3.13 on PATH, Node 22 (tested 22.19.0), npm. From here:

```powershell
npm ci --ignore-scripts --no-audit --no-fund
npm test
```

Installation downloads pinned npm dependencies. Tests use fresh random synthetic
identity bindings, fake targets and disposable memory. No credential file is read.
Tests spawn and close their own child processes. Build scripts invoke JavaScript
directly so Windows paths containing spaces and `&` work.

SDK 1.32.1, Zod 4.6.5 and TypeScript 5.9.3 are pinned in package-lock.json. This
compatibility baseline exercises protocol 2025-11-25 using the SDK client and
server. It is not a claim to implement newer protocol revisions or remote OAuth.

For an operator-configured local client, `npm run build` then `npm run demo`.
Explicit process configuration is required: SERVICE_DESK_MODE=synthetic,
SERVICE_DESK_API_TOKEN (at least 32 characters), and SERVICE_DESK_BINDINGS JSON
mapping that token to actor_id, tenant_id and role. This local service identity is
separate from Jira credentials. There are no default accounts. An optional
SERVICE_DESK_PYTHON selects the Python executable. Never print these variables.
The demo refuses to start without configuration; the tests configure themselves.

The reference client lists tools and searches the empty store. Each process owns
its store and loses it on exit. SERVICE_DESK_TEST_FIXTURES=1 is a synthetic harness
switch used only in tests: it creates two isolated tenant cases with separately
seeded supervisor approval and a completing fake target. It is not an approval UI,
real supervisor identity or a way to enable real platform writes.

Tools: search (bounded pagination), create_synthetic, get_context, propose_update,
apply_approved_update, verify_outcome, close, reopen, under the ticket namespace.
No approve tool or caller-selected identity is exposed. Verification writes audit
evidence, so it is not annotated read-only. Target/SOP references are returned;
the original ticket body and audit history are not dumped into tool output.

Inputs are strict Zod schemas; outputs are explicitly validated per command before
the SDK validates the result envelope. Errors use a small safe code vocabulary.
The child has an environment allowlist, no inherited provider/Jira credentials.
Requests are capped at 16 KiB, outputs at 60 KiB, pending calls at 16 and bridge
waits at 5 seconds. There is no retry. A cancelled/timed-out dispatched call is
reported as outcome unknown; cancellation does not promise rollback.

The eight offline Node tests cover initialization/discovery, schema rejection,
tenant filtering, auditor write denial, proposal approval boundary, verified
close, replay, adverse-evidence reopen denial, CLI client and cancellation
before/after dispatch. They do not themselves contact Jira or Keycloak.

## Connected local mode (Phase 5)

Set SERVICE_DESK_API_URL to the exact `http://127.0.0.1:<port>` origin and provide
SERVICE_DESK_MODE=synthetic plus SERVICE_DESK_API_TOKEN for the staff identity.
Bindings and PostgreSQL settings remain on the API server; MCP receives neither.
The reference client forwards this URL explicitly. In this mode, MCP calls HTTP
instead of creating a private Python memory store. Supervisor approval remains
outside the exposed tool set and uses /v1/approvals plus the reviewed payload hash.

The HTTP backend forbids remote origins, URL credentials, redirect following and
unknown commands, bounds streamed responses, and never retries. Cancellation or
transport ambiguity requires read-back. Eight local Node tests cover both modes;
the real PostgreSQL + HTTP + MCP scenario is run separately by
scripts/check_postgres_contracts.py (which invokes test/connected.mjs).

The [Phase 5 local gate](../docs/phase-5/CURRENT-GATES.md) records connected
Jira/Keycloak acceptance, including William's browser-approved IT-1 grant and
target read-back. The [Phase 7 exercise](../docs/phase-7/CURRENT.md) covers
persisted restart, lost receipts and concurrent replay on isolated synthetic
targets; the [Phase 8 handover](../docs/phase-8/README.md) covers bounded local
identity renewal and operating procedures. These are linked lab evidence,
not claims that the eight offline MCP tests repeat the live integrations.

Remote MCP transport/OAuth, production identity lifecycle, hosted deployment
and long-running capacity are outside the accepted local scope. Stdio identity
remains an explicit process binding.
