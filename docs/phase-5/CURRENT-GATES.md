# Phase 5 — completed local V1 integration

Completed 2026-10-08. [phase5-gate.json](phase5-gate.json) passes with no remaining
Phase 5 gates: **130 Python tests + 8 Node tests**. Architecture is **code-led**;
[ADR 003](../architecture/ADR-003-selected-code-led.md) records the owner's
explicit delegation and the decision rationale.

| Gate | Verified result |
| --- | --- |
| Roles and targets | William owns business decisions, approvals and credentials; alpha/beta Keycloak and demo configured |
| Connected targets | Actual local access/service checks and William-approved access journey pass |
| Jira result | Operation property written/read back; replay makes no extra PUT |
| Jira link/search | IT-2 created, related to IT-1, exact link read-back and replay verified; two search pages imported idempotently |
| Negative authentication | Invalid token returned 404 without issue data; no unauthorized read succeeded |
| Polling | Active every 60 seconds, scoped to IT-1/IT-2; durable failure latch and explicit resume |
| Supervision | API and worker child crashes recover with case, operation ID and entitlement unchanged |
| Migration/rollback | Logical restore, schema rollback and quiesced cross-database job cutover/rollback pass with one target effect |
| Final regression | 130 Python + 8 Node tests pass; source hashes recorded in the gate report |

## Acceptance boundaries

William's access approval was entered in the browser. The related-ticket link
uses an explicitly labeled technical supervisor fixture in the authorized lab;
it is not a second William browser approval. The Jira tickets' workflow statuses
remain unchanged, and no comments were sent. Linking tickets is not treated as
incident resolution.

Rate-limit and uncertain-response handling use controlled fault tests; no attempt
was made to force Jira SaaS throttling. Polling replaces inbound Jira webhooks in
the selected architecture, so no Jira webhook-signing claim is made. Source checks
are preflight comparisons, not atomic transactions spanning Jira and Keycloak.

The user chose an API token without scopes. Live scripts use the explicitly
configured Jira site origin and consume .env internally without displaying it.
Library adapters retain support for scoped tokens through the Atlassian gateway.

Phase 6 covers real-model quality and business evaluation. Phase 7 covers load,
soak, host reboot/supervisor failure, network-partition fencing and release
hardening. Billing/refund baseline jobs remain intact; none were cut over or
claimed feature-equivalent to the new service-desk journeys.

## Reproducible checks

`check_phase5_gate.py` runs the final unit suites and validates the evidence
reports without reading .env or contacting Jira. `check_jira_connected.py` is the
explicit live acceptance script and may create the designated test ticket if it
is absent. `check_jira_poll.py` enables/verifies the bounded poller after connected
acceptance. Do not revoke active operator membership when rerunning fixture tests.
