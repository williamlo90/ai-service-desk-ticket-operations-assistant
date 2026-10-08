# Phase 1 — trusted context and API boundaries

Read `backend/service_desk/contracts.py`, `auth.py`, `cases.py`, then `api.py`.
Trace POST /v1/cases from bearer binding through validation into the locked memory
repository. The server sets identity; the body cannot assign a role or tenant.
Replay with the same key returns the same case; changed payload returns conflict.

Run from backend: `python -B -m unittest discover -s tests -v` (39 tests).
Try the existing negative tests for cross-tenant reads and auditor writes. A 201
means received, never approved or executed. Memory storage loses data on restart.

Existing local runtime scripts and old evidence are retained in this initial
snapshot. They were not executed in this offline checkpoint. WSGI transport,
production identity, persistent SQL and connected workflows are still pending.
