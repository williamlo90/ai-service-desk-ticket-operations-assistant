# Phase 8 — reproducible handover

The handover separates the source package from private runtime state. Read
`docs/phase-8/HANDOVER.md` for operating steps and `ACCEPTANCE.md` for the evidence map.
The package does not include credentials, databases, dependency directories or models.

`check_clean_delivery.py` exports a staged Git tree, installs pinned Python packages
in a fresh venv and locked npm dependencies in a fresh directory, then runs Python,
MCP/build, UI assertions and the offline demo. It records exactly which source bytes
were tested. This is a same-host clean installation, not a new-host SaaS migration.

`demo_handover.py` shows unapproved rejection, an unknown result after a lost receipt,
verified reconciliation and one effect after replay. It uses fixture approval and
never reads credentials. `renew_lab_identity.py` rotates local tokens only after
the service is stopped; tests verify scope preservation and rejection of mismatches.
Actual current tokens were not rotated merely to produce handover evidence.

`check_phase8_gate.py` verifies clean-tested source hashes, Phase 7 source continuity,
required docs and accepted evidence, then creates the release manifest. The final
source archive is generated from the Phase 8 commit. Its SHA-256 sidecar stays beside
it, avoiding the impossible requirement that a package embed its own checksum.

One completion commit contains Phase 8. Azure is explicitly deferred. Longer
endurance, physical reboot and full-volume recovery remain deployment qualifications;
they are not inferred from successful source installation or the short lab workload.
