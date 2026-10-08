# William's local approval lab

William is the business owner, operational approver and credential custodian for
this lab, as explicitly confirmed on 2026-10-08. These assignments do not count as
approval of an individual proposal.

The local API runs at http://127.0.0.1:5681 and uses a dedicated persistent
PostgreSQL database with separate migration-owner and application roles. It is a
manually started supervisor with separate API, approved-job worker and poller.
API/worker child crashes are automatically restarted; reboot does not auto-start
the supervisor. Existing n8n and other project containers are untouched.

## Review the first proposal

1. Open the `review_url` in [operator-lab.json](operator-lab.json). The case ID is
   prefilled. The source is a read-only snapshot of Jira IT-1, mapped by trusted
   configuration to tenant alpha and sandbox requester-a.
2. Locally copy the token from
   `C:/Users/William/.codex/private/service-desk-targets/william-alpha-approval-token.txt`
   into **Supervisor access token**. Never send the token to chat or commit it.
3. Click **Load proposal**. Review the source, tenant, requester, policy and action.
   The proposed target action adds requester-a to `reports-reader` in the local
   Keycloak realm `sd-lab-alpha`.
4. Click **Approve this proposal** only if the displayed action is intended.
   This records William's approval; it does not dispatch the action or change Jira.
   The existing access policy allows execution for 15 minutes after approval.

The token expires at the timestamp in operator-lab.json (24 hours after issue).
The browser keeps it only in the current page, without local storage. Reloading or
leaving the page requires entering it again. Execution remains a separate staff
step with authoritative target read-back. Before execution of an imported source,
re-read Jira and review any changed source; this initial import is not continuous
synchronization or a Jira write implementation.

## Setup and checks

```powershell
& ./.venv/Scripts/python.exe -B scripts/operator_lab.py setup
& ./.venv/Scripts/python.exe -B scripts/operator_lab.py import-jira
& ./.venv/Scripts/python.exe -B scripts/check_operator_lab.py
```

Setup consumes only private lab credentials. `import-jira` uses the existing
authorized loader to consume `.env` internally, without displaying it. The cloud,
project, ticket and `[TEST]` prefix are checked. One Jira GET is performed, with no
write. A deterministic local identity makes repeated imports idempotent; changed
source snapshots stop for review and do not overwrite approval or action state.

The readiness check verifies an imported source through HTTP and MCP, denies
cross-tenant case reads and staff approval, and checks that human approval and
target dispatch are absent. Run it before human review; it intentionally stops
after an approval exists. It never uses William's token to approve or invokes the
execute endpoint.

Start only when port 5681 is free:

```powershell
Start-Process -FilePath '.\.venv\Scripts\python.exe' `
  -ArgumentList '-B','scripts/operator_lab.py','serve' `
  -WorkingDirectory (Get-Location).Path -WindowStyle Hidden `
  -RedirectStandardOutput 'local/operator-lab/api.out.log' `
  -RedirectStandardError 'local/operator-lab/api.err.log'
```

Never dump private config files, environment variables or raw subprocess output.
Do not delete the persistent database to refresh tokens. The current launcher
does not implement token renewal, OS startup registration or production
deployment. The selected supervisor and bounded Jira poller are described below.

## Current evidence

[Operator readiness](operator-readiness.json) verifies actual HTTP/MCP access to
the imported Jira snapshot, tenant denial and staff-approval denial. William approved the proposal in the browser. The staff MCP/API path executed
the grant and independently verified membership before closing the local case.
See [human-approved access](human-approved-access.json). Jira remains unchanged. Separate [connected target tests](lab-connected-check.json)
validate real local membership changes and demo process restarts using fixture
approvals. Those tests do not constitute William approving this proposal.

Phase 5 is complete for local V1: Jira link/search/poll acceptance, code-led
selection and bounded migration/rollback checks pass. See CURRENT-GATES.md.

## Approved execution

`python scripts/execute_operator_proposal.py` consumes an existing, current
William approval. It re-reads IT-1 summary/status and checks the stored source
snapshot before calling MCP execute/verify/close. It never creates an approval
or writes Jira. Ambiguous failures stop without automatic retry. The source
check is not an atomic transaction with Jira.

The first approved grant remains in place in the lab. Do not run tests that
revoke requester-a membership against this active operator case; use fresh
fixtures for subsequent regression work. Existing target-test evidence predates
this grant. The local case is closed; Jira IT-1 is not closed by this action.

## Selected supervised runtime

Use `./scripts/operator-service.ps1 Start`, `Stop`, or `Status` from the project
folder. The standalone launch above is a diagnostic alternative; do not run it
alongside the supervisor on the same port. The worker scans only approved or
already-dispatched jobs; it never creates supervisor approvals. Jira source drift
or unavailable source checks are escalated before dispatch. Incident recovery
uses ten-second minimum scheduling intervals for its health-observation policy.

The poller is activated only after `check_jira_connected.py` passes. It reads only
IT-1/IT-2 every 60 seconds. A failed poll persists a review latch across process
restarts. After fixing its cause, write the local `resume-jira-poll` marker to
resume explicitly. This avoids uncontrolled authentication/rate-limit retries.

`check_operator_supervisor.py` kills only the supervisor's owned API/worker child
handles, checks automatic restart and confirms the completed case and entitlement
remain unchanged. `check_job_cutover.py` uses two disposable databases to exercise
quiesced in-flight job migration and rollback with one synthetic effect. These
checks do not restart any other project or mutate the original operator database.
