# Phase 2 — business outcome before closure

Read policy.py -> store.py -> simulator.py -> journeys.py, then test_journeys.py.
The simulator keeps an independent effect ledger. The service reserves a stable
operation ID with compare-and-swap before submitting it. An acknowledgement is
not a verified outcome. Close performs a fresh authoritative read-back.

Approval binds case version, payload hash and policy version; it expires exactly
at the boundary and cannot be self-approved. Incident recovery needs three
checks ten simulated seconds apart. Linking tickets does not close an incident.
A later revoked entitlement can reopen a case without replaying the old action.

Run all tests from backend: `python -B -m unittest discover -s tests -v`.
53 tests pass. The 14 new journey tests use a fake clock, target ledger and memory
store; no sleep, Docker or network service is required. Test service reconstruction
reuses the same memory store: it is NOT durable restart evidence. Concurrency tests
prove process-local CAS behavior only. All persisted reference gates remain Phase 5.

Try reading test_timeout_after_effect_reconciles_without_retry and compare the
operation count against the state transitions. Read-based reporting is tenant
scoped. Aggregate audit records are append-only through the repository boundary;
this is not a tamper-proof external audit sink.
