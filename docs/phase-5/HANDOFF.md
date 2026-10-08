# Phase 5 integration handoff — not started

The offline loop stops here. Do not run the stack until William resumes runtime
work and the shared Docker resource slot is available. No current Docker status
was inspected as part of the offline loop.

## Ready to integrate

- Python intake API, guarded three-journey service and independent fake target.
- PostgreSQL schema/repositories/migration runner and callback hint verification.
- Scoped Jira reader and approved summary-update contract with injected transport.
- Local TypeScript MCP server/reference client and four Python skill packages.
- Four structured-data provider adapters with no default model or fallback.
- 74 Python tests and 6 MCP tests; evidence in docs/phase-4/offline-check.json.

## Prerequisites before connected actions

Confirm business/policy owner and designated supervisor, integration identity,
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
PostgreSQL behavior and provider compatibility are all pending. Offline unit tests
do not close those gates. Phase 5 should also have one commit after its gate passes.
