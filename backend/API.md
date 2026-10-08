# Container-free case API

This increment is a dependency-free WSGI application, tested in-process. No
listener is started, Docker inspected, database contacted, or `.env` loaded.
The deployment plan still calls for a production HTTP adapter/identity integration
and PostgreSQL; this increment does not complete those gates.

## Composition

Construct `TokenAuthenticator` with explicit server-owned token-to-Actor bindings,
then `CaseAPI(authenticator, MemoryCaseRepository())`. There are no default users,
tokens or roles. The test suite uses artificial credentials only. Real local API
credentials have not been generated or configured, and Jira credentials are never
accepted implicitly as API credentials. Token digests are stored in the authenticator;
source configuration must still be protected. Changing bindings requires replacing
the authenticator. Token expiry, rotation, identity-provider integration, rate limits
and deployment TLS remain pending. Do not expose this prototype publicly.

The application is independent of the HTTP server, but WSGI request parsing relies
on the future server enforcing transport timeouts and valid request framing. No
live HTTP/socket testing is claimed by the in-process suite.

## Endpoints

| Endpoint | Behavior |
| --- | --- |
| `GET /healthz` | Public process liveness only; no database readiness claim |
| `POST /v1/cases` | Specialist/supervisor creates synthetic case; 201 new, 200 replay |
| `GET /v1/cases/{case_id}` | Same-tenant staff including auditor can read; other tenant gets 404 |

Protected endpoints require `Authorization: Bearer <local API credential>`.
POST additionally requires `Content-Type: application/json`, `Content-Length`, and
`Idempotency-Key` (1–128 ASCII letters, digits, dots, underscores, colons or hyphens).
Body limit is 16 KiB. Duplicate JSON keys, non-finite numbers, extra fields, malformed
UTF-8, non-synthetic tickets and unsupported access/resource values are rejected.

Example body (no secrets):

```json
{
  "ticket_id": "SYN-001",
  "requester_id": "requester-a",
  "summary": "Request read access to reports",
  "requested_access": "read-only",
  "resource": "reports",
  "synthetic": true
}
```

Tenant and creator come from authenticated configuration. Optional `tenant_id`
from the earlier n8n fixture must match; it never establishes identity. Supplied
role/actor fields are rejected; identity headers such as X-Tenant-ID are ignored.
`requester_id` is untrusted ticket metadata, not the authenticated actor.

Responses contain `case` with server-generated UUID, tenant, creator, timestamp,
version 1 and status `received`; POST also returns `created`. A received case is
not approved and grants no access. This API cannot dispatch, approve, close or
change Jira tickets. Authorization failures return 401/403, missing/cross-tenant
cases 404, conflicting idempotency replay 409, capacity exhaustion 503. Errors
never return raw request contents, credentials or exception text. Responses are
marked no-store. No request logging is configured in this adapter.

## Repository boundary

`CaseRepository` defines atomic create-or-replay and tenant-scoped lookup. The
memory implementation stores immutable values under a lock and bounds the store
to 1000 cases by default. Same tenant + actor + idempotency key + same payload
returns the original case; changed payload conflicts. Different keys may create
separate cases for the same ticket; business-level deduplication is not implemented.
Memory is lost on restart and is not shared between processes. No durable audit
or distributed race/recovery behavior is claimed. A PostgreSQL adapter must use
transactions and a uniqueness constraint for the idempotency scope.

## Verification

From `backend`: `python -B -m unittest discover -s tests -v`.

39 tests passed, including 17 new API tests. Coverage includes unauthenticated
requests, spoofed identity, auditor write rejection, tenant isolation, body limits,
malformed data, idempotency conflicts, 12 concurrent replay requests, storage bounds,
ephemeral restart behavior and sanitized failures. All tests run in one Python
process, with no sockets, external services or real credentials.

Next integration gate: provision real local identity configuration, implement the
SQL adapter/migrations, validate HTTP transport, then connect n8n. Docker-backed
integration tests are deferred at the user's request while another task uses Docker.
