# Phase 5 handoff

The selected local architecture is code-led. Start with
[CURRENT-GATES.md](CURRENT-GATES.md) for the current completion state and
[ADR 003](../architecture/ADR-003-selected-code-led.md) for the decision.

William is business owner, operational approver and credential custodian. The
human-approved IT-1 access journey is closed locally with independently verified
Keycloak membership. Jira has the operation result property; its workflow status
is unchanged. Keep that approved membership in place. Existing fixture tests that
revoke membership must use isolated users before being run again.

The loopback API, approved-job worker and Jira poller have a bounded supervisor.
The poller is active for IT-1/IT-2 after successful live link/search acceptance.
Use scripts/operator-service.ps1 Start, Stop or Status. These commands operate
only this project's service. Never stop other projects' Docker containers.

Evidence includes the actual two-tenant target checks, human-approved journey,
PostgreSQL/MCP integration, reference engine comparisons, API/worker crash restart,
logical restore and quiesced cross-database job cutover/rollback. Synthetic fixture
approvals are labeled and must not be described as William's approvals.

Phase 5 is complete for the selected local V1 integration. The final gate passes
130 Python and 8 Node tests and validates all required evidence. The earlier
commit 66693e6 is a user-requested checkpoint; the final Phase 5 commit records
closure. Next work is Phase 6 model quality and business evaluation.

Never display .env or private credential files. Scripts may consume credentials
internally and emit only sanitized status. Raw snapshots, target ledgers, process
status and private runtime files remain outside tracked artifacts.

After Phase 5, proceed to real-model quality evaluation in Phase 6. Phase 7 covers
host/supervisor failure, workload and release hardening; Phase 9 remains Azure last.
