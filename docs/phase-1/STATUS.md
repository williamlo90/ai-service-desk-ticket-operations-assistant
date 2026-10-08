# Phase 1 — Split execution status

2026-10-08. User authorized separating low-resource implementation from runtime
work while other Codex chats use the shared laptop.

## Phase 1A — Container-free backend foundation

Completed this turn:

- Typed actor and ticket contracts; ticket text cannot set the trusted tenant.
- GET-only Jira adapter with tenant/project checks before network access, scoped
  gateway URL, response identity checks, size bound, no redirects or retries,
  credential-safe errors and repr.
- Pure predicates for supervisor approval, exact snapshot/version matching,
  expiry, verified closure, terminal-absence retry, and authenticated adverse-evidence reopen.
- 22 serial standard-library unit tests passed in 0.006 seconds on the available
  Python runtime. Command: `python -B -m unittest discover -s tests -v`, cwd `backend`.
  Transport is fake; no .env read, external API, model, database or container used.

The original 14 reference fixtures remain unchanged. These focused tests are not
the independent end-to-end evaluator, and do not claim that all 14 scenarios pass.
The earlier IT-1 HTTP 200 diagnostic applies to the earlier script, not this new
adapter. No active baseline code was removed or imported.

## Phase 1B — Runtime and persisted prototype (in progress)

Former queue dependencies on host `local`:

1. `03 - ConnectWise Service Operations MCP Server`, ID `01a11acf-f2d3-7401-afe1-8075a2a6cacc`.
2. `02 - Odoo Business Operations MCP Server`, ID `01a11acf-453c-71c0-b8f2-a74935ff9683`.

The user explicitly authorized staged runtime startup on 2026-10-08 after the
other project containers were stopped. The 4 GiB full-stack guard is no longer a
blocker to the authorized bounded single-service rollout. Heartbeat
`antrean-runtime-service-desk` is now PAUSED because the queue has been taken.
Other project services remain untouched, including independently restarting ERPNext.

Database infrastructure is verified: PostgreSQL 16.14 with pgvector 0.8.4, pinned
image, isolated volumes/network, 512 MiB / 0.5 CPU, loopback-only port, independent
application/n8n roles and databases. Authenticated TCP checks, cross-database
denials, wrong-password rejection and synthetic persistence after restart passed.
Evidence: `database-check.json`. Instructions: `../../deploy/README.md`.
This is infrastructure persistence, not yet persisted business cases/actions.

n8n 2.42.5 is also running, pinned by digest, with its own data and secret volumes,
1 GiB / 1 CPU cap and loopback-only editor at http://localhost:5678. Health,
readiness and editor GET returned 200; unauthenticated workflow access returned
401. Both containers report healthy with OOMKilled=false. The n8n database contains
148 public tables after initial migrations. Evidence: `n8n-check.json` and
`runtime-versions.json`. User confirmed owner signup completed on 2026-10-08; the authenticated n8n Assistant onboarding page was observed in the browser. No workflow credentials, service identity or business workflow has been configured.

Post-start sample: n8n 569.2 MiB, database 47.62 MiB; host free RAM 0.60 GiB.
These are point-in-time idle/startup observations, not benchmark capacity. Stop
expansion here: no API server, model or further runtime is started this turn.
Next: skip optional Assistant setup, then build a synthetic manual workflow before connected Jira integration. Resource headroom
must be reassessed before the next service; close unused apps if the host is slow.

Remaining Phase 1B work:

- Sample resources with `scripts/check_docker_readiness.ps1` in the appropriate
  staged mode immediately before adding a service. Idle chat alone is not proof
  that containers released memory; running services naturally occupy their ports.
- Review remaining Phase 0A items: owner/business policy confirmation, exact image
  pins, isolated local secret configuration and scoped integration identity. Block
  only dependent work; do not claim a fully closed Phase 0A.
- Resolve compatible FastAPI/database dependencies and exact image digests.
- Use only the `service-desk-lab` Compose project, dedicated volumes/network and
  resource limits from `../phase-0/local-runtime-plan.md`. Never stop other stacks.
- Build FastAPI identity integration and auth checks, PostgreSQL migrations,
  persisted case/actions/audit, n8n runtime and a usable reference client.
- Bind approval and verifier evidence to trusted server data inside transactions;
  add idempotency, version conflicts, callback ordering and restart recovery tests.
- Complete equal code-led/n8n-led vertical prototypes and independent fixture
  evaluation. Candidate winner remains a Phase 2 decision.

The heartbeat has been paused. No cloud deployment, local load tests or full-stack
startup is implied by a single staged service passing its smoke checks.

## Remaining boundaries

Phase 1A is a tested library, not a running API service. Authentication middleware,
business-state persistence, transaction races, real target verification, UI, MCP
and n8n workflows are not implemented. Phase 1 overall stays incomplete until the
original runtime gates pass. No business-authority role is assigned by inference.

## First n8n learning workflow

Manual Trigger -> Edit Fields -> If created and executed in the local editor.
The read-only fixture reached True; an admin-access variant reached False; the
read-only fixture was restored and the complete workflow rerun successfully.
Evidence: `synthetic-workflow-check.json` and `synthetic-workflow.png`. This is
fixture routing only, not application authorization or an architecture benchmark.
Jira credentials were not accessed and no real ticket or access was changed.
The connected business workflow and independent reference evaluator remain pending.

## Container-free API increment

User requested no Docker use while another task uses it. Implemented a stdlib
WSGI adapter, explicit bearer-token authentication bindings, trusted tenant/role
checks, synthetic case intake and a bounded memory repository. POST /v1/cases
creates received cases with atomic tenant/actor-scoped idempotency; GET scopes
lookup by the authenticated tenant. No approval or real action endpoints exist.
39 tests passed (17 new API tests), including concurrent replay, denied access,
malformed input and sanitized failures. See `../../backend/API.md` and
`api-check.json`. No Docker commands, network services, .env reads or dependencies
were used for this increment. Persistent SQL, production identity, HTTP transport
and n8n integration remain deferred. Data in this adapter is intentionally ephemeral.
