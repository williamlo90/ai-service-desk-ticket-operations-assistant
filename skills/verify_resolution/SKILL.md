# verify_resolution v1

Verify an action against authoritative target read-back.

Use after dispatch or unknown outcome; never trust a receipt or model claim as evidence.

Owner: project maintainer for this executable package. Business/policy owner is
still pending in the Phase 0 readiness register; synthetic policy is not approval.

Preconditions: authenticated trusted Actor, bound tenant, specialist or supervisor.
No actor/tenant override in input. Binding: `service_desk.skills.SkillRunner.run`
with name `verify_resolution`. Use input.schema.json / output.schema.json (v1).

Steps: Read action and target; ignore older sequence; record evidence; require three spaced healthy checks for incidents.

Declared dependency: shared JourneyService/policy only; no arbitrary SQL, shell,
Jira write or model tools. Side effect: `evidence_write`. This skill cannot approve an
action. Domain service enforces permissions, versions and approval invariants.

No target mutation. Repeated observations may add audit; no automatic retry. Failed/unknown outcomes require review; this skill does not close cases.

Timeout/cancellation: synchronous bounded local service; caller controls deadline.
MCP bridge deadline is 5 seconds, with no automatic retries. Cancellation after
dispatch means outcome unknown; inspect persisted/target state before resuming.
The local Python call itself is not interruptible midway. Runtime workers need
transaction deadlines and durable recovery in Phase 5; memory does not survive exit.

Postcondition: output contract plus stored audit for writes. No model-authored
facts can satisfy target verification. Permission/missing/version/clarification
failures propagate as typed service errors; no raw transport errors are shown.
Manual recovery: correct missing facts, load current case, and obtain fresh human
approval if a proposal changed; no automatic compensation for external effects.

Examples and independently authored expected cases: ../fixtures.json.
Tests: backend/tests/test_ai_skills.py, test_journeys.py and MCP protocol tests.
Metrics: offline contract pass/fail only; real correctness/latency/cost pending
Phase 6. No zero-cost or time-saving claim from a fixture run.

Compatibility/changelog: 0.1.0 adds this v1 binding for interactive and automation
callers. Breaking fields require a new schema version. No caller-specific logic.
