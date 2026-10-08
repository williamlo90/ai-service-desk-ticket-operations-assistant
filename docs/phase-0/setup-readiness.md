# Setup readiness — 2026-10-08

Status: Phase 0A pending. No accounts or services created by the planning work.

| Item | Status | Responsible role | Evidence / next action | Affected phase |
| --- | --- | --- | --- | --- |
| Atlassian account | Created per user; authenticated Jira session observed | User | Login verified through Jira UI on 2026-10-08; email verification not separately inspected | 0A.1 |
| Business owner and credential custodian | William confirmed as business owner, operational approver and credential custodian for the lab | William | User confirmed all three lab roles during Phase 5; Keycloak/demo sandbox ready | 0A / 5 |
| Jira test environment | Site and project verified in browser; Free plan confirmed by user; integration identity pending | Future custodian | william-service-desk-lab.atlassian.net; IT Service Project, key IT; Free (not trial) confirmed by user on 2026-10-08; verify API identity/access next | 0A / 5 |
| Jira credentials and scopes | Read authentication verified for IT-1; scope inventory and negative permission checks pending | William | jira-read-check.json: GET returned HTTP 200 on 2026-10-08; personal-account token loaded locally without displaying credentials | 0A / 5 |
| Access/service sandbox | Ready: local Keycloak and demo targets for alpha/beta | Business owner | Actual membership and child restart/read-back checks pass; see phase-5 evidence | 0A / 5 |
| Docker Linux runtime | Engine/Compose ready; startup blocked by current RAM headroom | Implementer | docker-readiness.json: Linux engine 29.8.0, Compose 5.5.1, 1.81 GiB host free at sample; local-runtime-plan.md defines initial resource budgets | 0A / 1 |
| Exact new-project version lock | Pending setup compatibility check | Implementer | Pin n8n image digest and compatible PostgreSQL/dependencies before installation | 0A / 1 |
| Model credentials | Unknown, not requested/read | Future custodian | Configure provider references when needed | 3 |
| Ollama/model license | Pending model selection | Implementer | Hardware recorded; choose compatible model and review license | 3 |
| Existing remote jobs | Unknown; no migration underway | Existing runtime owner | Inspect in-flight work before any cutover; isolate prototypes meanwhile | 5 |
| Isolated performance environment | Not selected | User / implementer | Select non-cloud local/sandbox capacity compatible with resource policy before measurements | 1 comparison / 7 |
| Other portfolio projects | No hard dependency chosen for prototype | Implementer | Use self-contained fake target; record any later dependency explicitly | 1 / 5 |

## Snapshot and artifact verification

Snapshot location: `C:/Users/William/.codex/project-backups/service-desk-phase0-20261008` (outside the public project).

`baseline-head.zip` contains the committed tree; `working-tree.patch` preserves tracked differences; `overlay/` preserves changed and untracked files. `manifest.json` records SHA-256 values. Ignored credentials, database contents, environment files and live queues are excluded. Tracked migration/config templates and committed evidence are included in the archive. This is a source snapshot, not a backup of a running deployment or Git history.

Recovery procedure: extract archive into a new empty isolated directory; apply overlay files to matching relative paths. The patch is an alternative for tracked textual/binary changes, not an additional step after overlay. Recreate ignored runtime configuration separately. Verify hashes against snapshot manifest before import. Do not restore over the old working tree.

Fresh checks: archive opens with 1,164 entries; JSON parses and contains 14 unique case IDs. Contract and fixture hashes are in artifact-manifest.json. These checks validate artifact structure, not candidate execution or a full restore rehearsal. The earlier 13 passing unit tests remain bounded baseline evidence.

Phase 0 planning artifacts are ready for setup review. Overall Phase 0/0A readiness is not complete while owner and required setup items remain pending. No candidate winner or deletion decision has been made.


## First synthetic ticket — UI verification 2026-10-08

[IT-1](https://william-service-desk-lab.atlassian.net/browse/IT-1): [TEST] Request read access to reports. Request type: Get IT help. Status observed: Waiting for support; assignee Unassigned; priority Medium. Description contains synthetic requester-a, tenant alpha, reports resource and read-only access, with no real access change requested. This proves manual portal intake and agent-view read-back only; API integration, approval and external outcome verification remain pending. Tenant alpha in description is test content, not an authenticated tenant boundary.


Subscription update 2026-10-08: user inspected Billing and confirmed Free, not a trial. This is user-reported subscription evidence; API authentication and permissions have not been validated.


## API read verification — 2026-10-08

Ran scripts/check_jira_read.py with explicit user authorization to load .env internally. One GET through the scoped-token Atlassian gateway returned HTTP 200 for IT-1, summary [TEST] Request read access to reports, status Waiting for support. Evidence: [jira-read-check.json](jira-read-check.json). No Jira write attempted. Credentials, authorization headers, raw responses and exception details were not printed or saved. Offline synthetic checks verified HTTP/network error suppression and redirect blocking. This confirms this ticket's read access only, not absence of write access, cross-tenant isolation, API token scope inventory or connected workflow acceptance.

## Phase 5 update — 2026-10-08

William explicitly confirmed himself as business owner and selected local
Keycloak plus dedicated demo service targets. Setup now passes realm isolation
and health checks; see ../phase-5/target-sandbox-setup.json. This does not designate
production authority. William subsequently confirmed both operational approver and credential custodian roles for this lab. Synthetic
supervisor identities in tests are fixtures, not a record of William approving a
real action. Project PostgreSQL/n8n were observed healthy; updated connected check
results are in ../phase-5/postgres-contract-check.json. Earlier runtime blockers
above are historical snapshots, not the current container status.

Local target credentials were generated privately without reading the project
.env. The two realms and demo children are technical lab resources. Adapter checks
exercise actual membership changes (restored afterward) and actual child restarts.
Jira write acceptance and a named human approval session remain separate gates.

William has now confirmed both operational roles. The persistent operator API
and IT-1 read-only import are ready; see [operator guide](../phase-5/OPERATOR-LAB.md).
The first proposal awaits an explicit human click, with no target action or Jira
write performed by setup/import.
