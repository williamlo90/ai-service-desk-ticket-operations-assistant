# Case study: Jira ticket to verified Keycloak access

The [IT-1 integration walkthrough](JIRA-TO-KEYCLOAK-WALKTHROUGH.md) is the concrete service desk example: a Jira request led to a William-approved report-access grant, Keycloak membership read-back and a separate Jira result-property write. It keeps the actual connected evidence distinct from the synthetic UI illustration and offline recovery tests.

## Problem

A service desk assistant needs to help an operator move from an incomplete request
to a reliable outcome. Language models can suggest a category or extract evidence,
but they cannot establish permission to modify an account. Network timeouts create
a second problem: a target may accept an action even when its receipt is lost.
Blindly retrying can duplicate a business effect.

## Implementation

The assistant separates model suggestions, deterministic policy, human approval,
execution and verification. The browser presents the action payload and policy;
approval is bound to a case version and payload hash. The backend authenticates
identity independently of tool arguments and enforces tenant and role boundaries.

PostgreSQL stores the lifecycle, audit and job state. A durable operation ID survives
retries. When the outcome is unknown, recovery reads the target rather than assuming
failure and creating another action. A case closes only after the requested outcome
has been verified. Related-ticket linking is not treated as proof that an incident
has been resolved.

## Architectural choice

A code-led service owns transactional state and recovery. This keeps approval,
compare-and-swap, idempotency and reconciliation in one explicit domain model.
n8n remains useful for supporting integrations, but is not a second authority over
the case lifecycle. [ADR 003](architecture/ADR-003-selected-code-led.md) records the
comparison and tradeoffs.

The small browser page provides independent human approval. Jira remains the request surface; the custom MCP server is the tool interface for AI clients. Cached AI practice is a supporting exercise and does not add provider calls.

## Evidence

The [offline demo](../scripts/demo_handover.py) blocks execution before approval,
simulates a lost receipt, reconciles the outcome, closes the verified case, and
replays with one target effect. [Release exercises](phase-7/release-lab.json) add
real PostgreSQL, process interruption, concurrent dispatch and bounded HTTP load.
[Connected tests](phase-5/lab-connected-check.json) exercise Keycloak and service
sandbox targets. Human approval evidence is recorded separately from fixture tests.

OpenAI passed an internally designed 16-case synthetic held-out set. This supports
the accepted lab triage profile, not a general accuracy claim. An eight-task human
pilot was diagnostic and does not establish productivity improvement.

## Scope

The delivered system is a local lab with explicit startup and operator ownership.
Its health check is a point-in-time diagnostic. Long endurance, physical host reboot,
production qualification remain separate. Azure hosting is an optional final
extension. These boundaries keep the demonstrated behavior reproducible and the
operational claims concrete.

## Delivery choice

The local lab handover includes an English operator guide, recovery demonstration
and named ownership. New work starts with native tests, then uses a reserved
runtime session for affected integrations. Connected evidence remains tied to
its original environment. Azure is optional; a hosted claim requires fresh
cloud acceptance.
