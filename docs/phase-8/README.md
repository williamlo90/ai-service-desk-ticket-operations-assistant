# Local handover

The service desk lab turns a bounded Jira request into a reviewed proposal, approved
action, independent target verification and durable audit. William owns business
scope, operational approval, credentials and support. The selected implementation is
Python/PostgreSQL with TypeScript MCP; n8n remains optional.

- [Operator guide](HANDOVER.md): startup, daily use, demo, statuses, renewal,
  troubleshooting, setup, backup/rollback and ownership.
- [Acceptance map](ACCEPTANCE.md): what was validated and where to find evidence.
- `release-manifest.json`: versions, source/evidence hashes and scope.
- `clean-delivery.json`: clean-source installation, build and test result.
- `demo.json`: reproducible offline failure/replay demonstration.
- `phase8-gate.json`: final handover gate.

OpenAI passed all 16 synthetic held-out cases. Phase 7 completed 48 synthetic HTTP
journeys with no errors/extra effects; concurrency-four p95 was 1.88 seconds on the
shared lab host. These measurements do not establish customer accuracy, production
capacity or human ROI. William's completed pilot is diagnostic.

The source package excludes `.env`, private identities, runtime databases and model
weights. Azure remains deferred. Ollama is experimental and Claude/Grok are unvalidated
live profiles. No service is represented as production-ready.
