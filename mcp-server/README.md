# Local MCP reference implementation

Eight strict tools call the shared Python service through a bounded JSON-lines
subprocess. The MCP boundary itself is the SDK stdio transport; the private
Python bridge is not a second MCP implementation. No Docker or network listener.

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

Covered: initialization/discovery, schema rejection, tenant filtering, auditor
write denial, proposal approval boundary, verified close, replay, adverse-evidence
reopen denial, CLI client and cancellation before/after dispatch. Runtime identity
rotation/expiry, persisted restart, backend timeout recovery, remote transport,
Jira connection and end-to-end correlation remain Phase 5/7 work. Stdio identity
is an explicit process binding, not a production credential lifecycle.
