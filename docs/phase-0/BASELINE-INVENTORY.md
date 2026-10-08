# Phase 0 — Baseline inventory

Inspected: 2026-10-08. Status: initial source review and bounded unit verification complete; Phase 0 remains in progress.

Source: `C:/Users/William/OneDrive/Dokumen/Agentic Project/case-resolution-copilot-rebuild`.
Revision: `1a88dbb0e55889303ec83c7abb789fade81f16bf` plus local changes recorded in [source-inventory.json](source-inventory.json).
All source paths below are relative to that repository. This review does not certify the full baseline or any deployed environment.

## Findings and reuse candidates

| Capability | Evidence inspected | Assessment for the new project |
| --- | --- | --- |
| Tenant and action permissions | `backend/app/services/action_service.py`: permission checks and organization-scoped repository calls | Existing, reuse candidate; cross-tenant API/database verification still required. |
| Immutable approvals and stale-action blocking | `backend/app/persistence/actions/_base.py`: snapshot fingerprint, expiration, case/proposal version checks; `backend/app/services/review_service.py` | Existing, reuse candidate. Fingerprint unit tests passed; full approval workflow not rerun. |
| Controlled action and recovery | `backend/app/services/action_service.py`, `backend/app/domain/actions.py`, `backend/app/persistence/actions/execution.py` | Existing leases, idempotency binding and unknown-outcome reconciliation; adapt to asynchronous target outcomes. |
| Policy retrieval | `backend/app/persistence/policies/retrieval_v2_filters.py` | Existing organization, category, effective-time and context filters. MSP SOP corpus and role visibility require verification/adaptation. |
| Signed intake | `backend/app/api/routes/case_intake.py`, `backend/app/integrations/case_webhook.py` | Existing bounded signed webhook and duplicate handling. `category` is required from the caller; raw-message triage is new work. |
| Case lifecycle | `backend/app/domain/cases.py` and inspected case service/commands | Existing investigation/review/completion states. No explicit reopen command found in inspected command definitions; implement and verify close/reopen predicates. |
| Action outcome | `backend/app/persistence/actions/execution.py:151` | `finish_execution_success` records a receipt and marks the action completed. A delayed accepted/running/final result lifecycle needs an explicit contract before using asynchronous MSP targets. |
| Orchestration | `backend/app/orchestrators/langgraph_orchestrator.py`; baseline README | Existing LangGraph candidate; retain for comparison until evidence supports replacement. |
| Background jobs | `backend/app/async_jobs/celery_app.py` | Registered inbox and policy drain/status/reprocess tasks plus validation task. Do not remove Celery without mapping their replacements. Runtime jobs/in-flight work not queried. |
| UI | `frontend/package.json`, baseline README | Next.js/React/TypeScript with Clerk. Reuse workspace/review UI concepts; do not assume this is already the new Jira service desk UI. |
| Jira, n8n, custom MCP, additional model providers | Target project plans; bounded keyword search of baseline application/client code returned no matches for Jira/n8n/Ollama/Anthropic/Grok/MCP | Treat as new or unverified integrations, not existing executable capabilities. |
| Billing/refund evaluation | `docs/evidence/case-resolution-evaluation-v1/README.md` and persisted-workflow aggregate | Preserve as regression material. Add MSP cases; old results are not new-project acceptance. |

## Local changes

Git status reported 13 modified tracked paths and one untracked file. The textual diff contained changes in 10 tracked paths (122 additions, 45 deletions); three status entries had no textual diff in this inspection. Preserve all status entries until their differences are resolved, including possible line-ending/index metadata differences.

- Backend config/hooks reject fault commands without an active validation run; an accompanying unit test was added.
- k6 image/runner changes concern package updates, summary generation/upload, percentiles, and expected conflict responses.
- AWS validation scripts change deployment/load invocation and use an isolated SQS transport/DLQ probe.
- `infra/aws/test/load-runner.test.ts` is untracked and tests runner measurement behavior.
- Backup runbook and frontend package/workspace files are also flagged by Git status.

The new backend fault test passed in the bounded run below. AWS scripts, k6 execution and the untracked TypeScript test were not run. No local changes were committed, reverted, imported or deleted. The inventory contains fingerprints, not a restorable source snapshot; take a proper snapshot before import or migration.

## Evidence and verification

Historical evidence inspected: the 2026-09-30 evaluation pack reports 20/20 deterministic observations across 10 synthetic cases, a separate 3/3 provider canary, and 4/4 guarded PostgreSQL scenarios. The aggregate describes a validation database, not production. These are historical, bounded observations and do not establish correctness of today's dirty tree.

Fresh verification used the existing backend Python 3.12.13 environment:

```powershell
.\.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider tests/unit/test_action_recovery_policy.py tests/unit/test_review_snapshot.py tests/unit/test_production_validation_faults.py tests/unit/test_case_webhook.py
```

Working directory: baseline `backend/`. Result: **13 passed in 0.34s**, exit code 0. No database, browser, application server, external provider or load runner was started. No full integration, frontend, performance or connected-platform acceptance is claimed.

## Import strategy

Use a separate implementation repository/checkout for the new project. Before copying code, preserve the exact source revision and relevant dirty changes with a restorable snapshot and checksums. Import only justified modules plus behavioral tests; do not copy credentials, runtime data or historical cloud configuration by default.

Retain approval, authorization, retrieval and action-recovery behavior as comparison requirements. Adapt triage, final-outcome verification and case lifecycle. Evaluate orchestration, scheduling and integration glue in Phase 1; decide retain/replace/delete in Phase 2. No active code is approved for deletion by this inventory.

## Remaining Phase 0 work

1. Establish the business owner and finalize the three V1 journeys, allowed actions and completion rules; see [scope-and-dependencies.md](scope-and-dependencies.md).
2. Create `docs/architecture/comparison-contract.md` and engine-independent reference fixtures, including all mandated failure cases.
3. Record equal candidate configuration, reference outcomes, evaluation method and workload/hardware before prototype comparison.
4. Resolve or explicitly register environment, version, access and licensing dependencies.
5. Snapshot source/configuration needed for reuse and identify active jobs before migration. Do not mark the snapshot or Phase 0 checklist complete from this inventory alone.

## Follow-up 2026-10-08

The remaining-work list above records the initial pass. Contract v1 and 14 synthetic reference fixtures now exist; the source archive/patch/overlay is recorded in artifact-manifest.json. User requested a setup phase because ownership/access are not ready: Phase 0A now precedes Phase 1. Current blockers and snapshot limits are in setup-readiness.md. Candidate execution and full restore rehearsal remain pending.
