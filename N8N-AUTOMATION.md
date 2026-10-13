# Automation decision for service desk operations

Updated 2026-10-09. The current V1 is **code-led with outbound Jira polling**, as decided in [ADR 003](docs/architecture/ADR-003-selected-code-led.md). Python/PostgreSQL own case state, authorization, approval, dispatch and outcome verification. The delivered local scope does not require an active n8n workflow.

## Optional n8n integration

Existing workflow prototypes may be retained. A future n8n extension can coordinate authorized intake, reminders or reporting through the same domain API; it must not become a second authority over case lifecycle or repeat a side effect owned by the worker.

If that extension is selected:

- [ ] Define one owner of scheduling, retries and operation state before activation.
- [ ] Prepare exports, version mapping and endpoint contracts with native tests first.
- [ ] Reserve a bounded runtime session for actual engine import/execution/restart and connected acceptance.
- [ ] Verify caller scope, exact approval payload/version, replay, stale data and uncertain outcomes.
- [ ] Deliver sanitized exports, credentials setup, activation/deactivation, alert/recovery checks and operating instructions.

These are extension criteria, not missing gates in the completed code-led local release. Completed phase evidence and comparison results remain in their original reports. Future replacements need equivalent control/recovery evidence before cutover or deletion.

## Delivery

Local documentation and support accompany the delivered lab scope. Azure is an optional final extension with separate cloud acceptance. Follow the [local phase plan](PHASES.md); do not restart completed phases to adopt the new scheduling policy.
