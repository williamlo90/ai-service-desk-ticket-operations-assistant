# Owner and environment recommendation

2026-10-08. Status: recommendation for user selection; no account, subscription or role assignment has been made.

## Ownership

Recommend William as portfolio product owner, business decision owner and credential custodian. These roles decide scope, approve synthetic business policies, own accounts and control spending. Codex assists implementation and documentation but is not the accountable owner or a human approval authority.

Specialist, supervisor, requester and auditor are separate application identities/roles in synthetic tests. William may operate test sessions, but requester self-approval remains prohibited by the contract. One operator testing separate identities is not independent multi-person validation. Application roles do not each require a paid Jira agent account.

## Environment

Start with a dedicated Jira Service Management Cloud Free test site/project containing synthetic data, separate from any work/customer site. Suggested site name: `william-service-desk-lab` (availability unchecked). Suggested service project: `Service Desk Lab`, key `SDL` (creation-time availability unchecked).

The current Free offering supports up to three agents. This is a dedicated test environment, not Atlassian's native Sandbox feature, which requires Premium/Enterprise. Free has restrictions on permission customization and issue security; do not treat two projects in one Free site as proof of strong platform-level tenant isolation. Enforce and test application tenant boundaries independently; reassess the plan or isolated sites if connected acceptance requires finer Jira controls.

Use local FastAPI/PostgreSQL/n8n in Phase 1; connecting to a Jira SaaS test site is permitted before cloud deployment. Initially use synthetic authoritative entitlement and health-check targets. Select actual connected action targets before Phase 5; simulated grants/restarts are never described as real identity-provider or service changes.

Prefer Free initially over a time-limited paid trial. Review Standard only when a required permission/workflow capability is demonstrably unavailable. Premium native Sandbox is not required for the first prototype. Exact features and plan selection must be checked during signup.

## Setup handoff

1. User confirms the ownership recommendation and signs in/creates the Atlassian account they will own.
2. Select the Free offering including Jira Service Management; record actual plan and edition. Do not activate a paid trial/subscription implicitly.
3. Create the dedicated synthetic service project and record its URL/key.
4. Configure identity, scoped credentials and secret storage using the setup plan; do not paste credentials into chat.
5. Verify API access and available project permissions, then update setup-readiness.md from pending to verified using actual evidence.

Sources checked: [pricing](https://www.atlassian.com/collections/service/pricing?bundle=jira-service-management), [native Sandbox eligibility](https://support.atlassian.com/organization-administration/docs/jira-family-and-sandboxes/), [Free permission limits](https://confluence.atlassian.com/servicedeskcloud/project-permissions-roles-and-issue-level-security-in-free-plans-1097175961.html).
