# Phase 0 — Proposed scope and dependency register

Date: 2026-10-08. Status: synthetic prototype rules frozen in comparison-contract v1; named business ownership and connected setup pending Phase 0A at user request. See SETUP-PHASE-0A.md for current environment observations and setup sequence.

## Proposed V1 journeys

Business owner role: service desk lead. Named owner is not yet established. Support specialists investigate and prepare proposals; authorized reviewers approve the exact action and evidence version.

| Journey | Proposed allowed work | Completion evidence |
| --- | --- | --- |
| Access request | Collect requester/resource/entitlement context, retrieve applicable SOP, prepare a bounded access proposal, request approval | Authorized target confirms the exact intended access. A Jira comment or accepted request alone does not prove access was granted. Target system remains to be selected. |
| Service incident | Collect symptoms and affected service, propose SOP diagnosis, execute only a specifically allowed operation | Post-action service check meets the incident-specific recovery condition, or escalation remains open with owner and reason. Service/check remain to be selected. |
| Repeated ticket | Find same-tenant related incidents, explain match, prepare a link/update | Jira read-back confirms the intended relationship; linking alone does not establish resolution of the underlying incident. Closure requires its own evidence or structured no-action disposition. |

Initial default: consequential external changes require approval. Low-risk automatic actions require an explicit allowlist and policy before activation. Missing facts trigger clarification; unsupported operations escalate. Synthetic data and two tenant configurations are the initial scope. Billing/refund cases remain a regression pack.

The comparison journey must cover intake → context/SOP → proposal → approval → accepted action → delayed result → verification → closure → new evidence → reopen. Both candidates must implement equivalent behavior before comparison. Wrong tenant, stale approval, accepted-then-failed action, timeout after side effect, duplicate/late callback, concurrent update and reopen are mandatory gates.

## Dependency register

Unknown means not verified, not absent. No secrets were read or copied during this inventory.

| Dependency | Observed status | Next step / affected gate |
| --- | --- | --- |
| Baseline source | Available at recorded revision, with local changes | Source archive, patch and overlay captured; see artifact-manifest.json. Restore validation/import remains pending. |
| Python | Baseline venv reports 3.12.13; default PATH Python points to Python313 | Use explicit compatible runtime; create isolated new-project environment in Phase 1. |
| Node / pnpm | Reports v22.19.0 / 10.21.0 | Pin new-project versions after compatibility review. |
| uv | Not found by PATH lookup | Locate or install for clean setup if selected. Existing venv allowed bounded tests. |
| Docker / Linux runtime | Docker executable found; Linux daemon unavailable; WSL distributions listed; see setup plan for hardware | Verify local runtime readiness before starting services. |
| PostgreSQL / pgvector / Redis | Baseline compose specifies pgvector PostgreSQL 16 and Redis 7; prior evidence describes PostgreSQL 18.6 | Choose and test one explicit new-project version; do not assume historical DB evidence matches compose. |
| n8n | New-project runtime/version not established | Verify official compatibility/licensing and pin a version for Phase 1. |
| Jira | Product edition, API, sandbox, permissions and credential owner unknown | Establish test tenant and scopes; connected acceptance remains pending until verified. |
| Action target | Access-management and service-health targets not selected | Define fake contracts for Phase 1; actual sandbox required for Phase 5 connected outcomes. |
| Model APIs | New-project OpenAI/Claude/Grok credential availability not verified | Record provider/version/access; canaries only after suitable credentials and permitted data are configured. |
| Ollama and model hardware/license | Ollama not found in PATH; hardware inventoried in setup plan; model and license remain unselected | Inventory capacity and choose a compatible model/license before local inference. |
| Runtime jobs | Celery task registrations found; running jobs and remote queues unknown | Query only the intended environment before migration; no cutover or scheduler change during inventory. |
| Business ownership | Role defined; named owner and exact policies outstanding | Finalize scope and reference outcomes before freezing comparison contract. |
| Resource constraints | Baseline resource policy prohibits local load/stress/browser suites; this pass used small unit tests only | Resolve a suitable isolated performance environment before benchmark/load phases. No cloud deployment before Phase 9. |

Baseline dependency manifests and lockfiles are inventory inputs, not chosen new-project versions. Official documentation/version verification is still required when selecting the implementation stack. No paid service, model request, cloud provisioning or deployment was initiated.
