# Jira IT-1: from access request to verified grant

A synthetic Jira service request for read-only report access became a **human-approved, verified Keycloak group grant** in the local lab. The ticket, approval, target read-back, and Jira result metadata are separate records; each answers a different question.

![Actual Jira IT-1 request showing the lab ticket description and related IT-2 work item](assets/jira-it1-request.jpg)

*Actual Jira Service Management view of the IT-1 lab ticket, captured for this walkthrough. The request explicitly identifies `requester-a`, tenant `alpha`, resource `reports`, and read-only access. It says no production account should be changed. The screenshot does not show a resolved Jira status.* [Open the lab ticket](https://william-service-desk-lab.atlassian.net/browse/IT-1).

## One request, five boundaries

| Step | What happened | Evidence |
| --- | --- | --- |
| **1. Jira source** | The bounded IT-1 ticket was read and its summary/status rechecked before dispatch. | [Jira read check](phase-0/jira-read-check.json), [human journey](phase-5/human-approved-access.json) |
| **2. MCP tools** | The connected local path used the custom TypeScript MCP server to call the service through the loopback HTTP API. Tools expose case context, proposal, execution and verification; they do **not** expose an approval tool. | [MCP contract](../mcp-server/README.md), [tool definitions](../mcp-server/src/server.ts), [human journey](phase-5/human-approved-access.json) |
| **3. Policy and human approval** | Python/PostgreSQL held a versioned proposal. William reviewed and approved it in the browser. The backend checked identity and the stored approval before action. | [Approval record and path](phase-5/human-approved-access.json), [operator guide](phase-8/HANDOVER.md) |
| **4. Keycloak read-back** | The lab adapter added `requester-a` to `reports-reader` in realm `sd-lab-alpha`. Target membership changed from absent to present; the local case closed only after verification. | [Connected result](phase-5/human-approved-access.json) |
| **5. Jira result** | A later, separate operation wrote a bounded result as an **issue property** and read it back. Replaying the operation caused no extra PUT. | [Result write/read-back](phase-5/jira-result-write.json) |

The source check and Keycloak change are **not an atomic transaction across Jira and Keycloak**. Jira remained **Waiting for support** in the captured issue view. The property is machine-readable metadata; this project did not add a Jira comment, set a Jira resolution, or transition the ticket workflow.

## What MCP contributes

MCP is the tool protocol between an AI client and this service. The [eight ticket tools](../mcp-server/README.md) have strict input/output schemas and bounded calls. In connected mode, they use the local HTTP API; the server-side identity, tenant and policy still decide whether a call is allowed. The client cannot choose its own actor or approve a proposal through MCP.

For IT-1, the [human journey report](phase-5/human-approved-access.json) records `Human browser approval -> MCP -> HTTP API -> PostgreSQL -> Keycloak read-back`. That is the demonstrated connected path. The screenshot below is a **synthetic UI preview**, included to show the shape of the review screen; it is **not** a capture of William's historical approval session.

![Synthetic approval screen illustrating the proposal a supervisor reviews](assets/case-review.png)

## The outcome, without a target UI screenshot

The Keycloak lab container is not running for this documentation pass. Instead of presenting a recreated console screen, this excerpt reproduces selected fields from the [connected acceptance record](phase-5/human-approved-access.json):

```json
{
  "jira_issue": "IT-1",
  "approver": "William",
  "tenant": "alpha",
  "realm": "sd-lab-alpha",
  "requester": "requester-a",
  "group": "reports-reader",
  "membership_before": false,
  "membership_after": true,
  "case_status": "closed",
  "verified": true
}
```

The subsequent [Jira result property](phase-5/jira-result-write.json) contains `action: grant_read_access`, `resource: reports`, `result: verified`, and `local_case_status: closed`. Its checks report `write_attempted: true`, `verified: true`, and `replay_without_write: true`. The Jira workflow status and comments were untouched.

## If the receipt disappears

A lost response is an uncertain outcome, not permission to run the action again. The worker persists an operation identity and reads the target before deciding whether the original action succeeded. The [offline recovery demo](../scripts/demo_handover.py) exercises a lost receipt and replay with **one synthetic target effect**. The [Phase 7 release exercise](phase-7/release-lab.json) adds a real PostgreSQL process crash and concurrent dispatch checks, also on synthetic targets. These recovery tests support the mechanism; they are not a second live Keycloak grant.

## Scope of this evidence

IT-1 is a **synthetic local lab request**, not a customer ticket. William's browser approval is distinct from fixture-supervisor acceptance tests. The linked IT-2 ticket was exercised separately with a technical fixture approval. The screenshot shows the later Jira state with that related work item; it is not a frame captured at the exact instant of the IT-1 grant. No claim of production throughput, ROI, hosted deployment, or atomic cross-system consistency follows from this walkthrough. Azure is optional and deferred.
