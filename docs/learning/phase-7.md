# Phase 7 — critical-path release checks

Study `scripts/check_release_lab.py`: it reserves operations in real PostgreSQL,
then crashes a child after a synthetic effect. Recovery must preserve the operation
ID and effect count, not merely return HTTP 200. It also tests simultaneous dispatch,
loss of a claim connection, isolated DB outage and bounded HTTP workloads.

The workload records acknowledgement and verified end-to-end latency separately.
Backup/rollback evidence from Phase 5 is reused because those components did not
change. Long endurance, physical host reboot and cloud readiness are not inferred.

The worker fix in `backend/service_desk/worker.py` counts eligible work rather than
closed history toward its active limit. `test_worker.py` guards both sides of that
boundary. `health.py` and `operator_health.py` turn runtime metadata into actionable
local alert codes while excluding tokens and payloads.

[Results](../phase-7/CURRENT.md): 179 Python tests, 8 MCP tests and 14 UI assertions.
One Phase 7 completion commit contains the fix, checks and evidence. Phase 8 is a
separate handover commit. Azure is deferred by William.
