# Acceptance and evidence map

| Requirement | Actual result | Evidence |
| --- | --- | --- |
| Human approval and target verification | William-approved local access grant verified and closed | Phase 5 human-approved-access.json |
| Jira integration | IT-1/IT-2 result/link/read-back and bounded polling passed | Phase 5 jira-connected-check.json, jira-result-write.json, jira-poll-check.json |
| Restore and rollback | Logical application restore and quiesced synthetic job rollback passed | Phase 5 operator-migration-check.json, job-cutover-check.json |
| Advisory AI | OpenAI 4/4 development, 16/16 held-out all checks | Phase 6 evidence-v1 reports |
| Human business study | Eight tasks complete; no correctness-matched ROI claim | Phase 6 BUSINESS-RESULTS.md |
| Failure and duplicate safety | Crash after effect, claim-session loss, database outage and concurrent dispatch passed | Phase 7 release-lab.json |
| Bounded workload | 48 closed synthetic HTTP journeys; no errors or extra effects | Phase 7 release-lab.json |
| Operational alerts | Ready at check time; alert/expiry metadata unit-tested | Phase 7 operator-health.json, test_health.py |
| Clean delivery | Isolated Python + fresh locked npm install, build and tests | clean-delivery.json |
| Demonstration | Unapproved denied, unknown kept open, verified closure, one replay effect | demo.json |
| Scope and ownership | William; OpenAI accepted, Ollama experimental, Claude/Grok and Azure deferred | HANDOVER.md, release-manifest.json |

Run `python scripts/demo_handover.py` for the fastest self-check without credentials,
Docker or model calls. Run `scripts/operator_health.py` with the runtime environment
for the existing connected lab. Only rerun connected mutation/recovery checks as a
deliberate maintenance task; do not use them as everyday health probes.

Physical host reboot, long soak, full-volume disaster recovery and cloud acceptance
are not covered by the source-install or bounded lab evidence. The failed local-model
quality evidence remains experimental and is not promoted by this handover.
