# Security

This is a loopback-only service desk lab. Do not expose the WSGI server or preview
to a public network. The disposable preview uses a public fixture token and must
never be connected to business targets.

## Enforced boundaries

- Server-bound identity, role and tenant; model/tool arguments cannot select identity.
- Human approval bound to proposal version, payload hash and expiry.
- Separate execution and target read-back; uncertain outcomes require reconciliation.
- Bounded inputs and outputs, origin/host checks and an explicit static-asset allowlist.
- Browser tokens held only in page memory and cleared on exit. No local storage.

## Credentials and publication checks

Keep `.env`, private runtime configuration, tokens, database snapshots and model
outputs containing private input outside Git. `.env.example` contains blank secret
values. Never paste credentials into issues, screenshots or logs.

Publication checks use Gitleaks 8.30.1 across all Git refs plus an all-commit path and
known-pattern audit. `.gitleaksignore` contains 25 exact historical fingerprints,
all reviewed JSON source/evidence SHA-256 digests. It does not suppress entire files,
rules or commits. The audit validates that each exception still refers to that kind
of digest. A clean scan means no unexcluded findings under these checks, not a
proof that arbitrary sensitive information can never exist.

Run `python scripts/check_public_history.py` and
`gitleaks git . --log-opts=--all --redact=100` before publishing history.
Run `python scripts/check_staged.py` before committing staged changes. CI repeats
history scanning and regression tests without business credentials.

## Report a vulnerability

Use this repository's **Security → Report a vulnerability** for private reporting.
Include affected revision, reproduction using synthetic data, and expected impact.
Do not open a public issue containing credentials or private customer information.
If private reporting is unavailable, contact the maintainer through the contact
channel listed on their GitHub profile, without including the sensitive payload.
