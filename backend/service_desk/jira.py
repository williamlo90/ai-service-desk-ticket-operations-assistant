"""GET-only scoped-token adapter with bounded responses and safe errors.

Server-side tenant/project binding is mandatory. No credential loader or live
network call runs on import. This module does not read the repository .env.
"""

import base64
import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable
from urllib.error import HTTPError
from urllib.request import HTTPRedirectHandler, Request, build_opener
from uuid import UUID

from .contracts import Actor, Ticket, require_staff

MAX_BYTES = 262144


class JiraReadError(Exception):
    def __init__(self, code: str, http_status: int | None = None):
        self.code = code
        self.http_status = http_status
        super().__init__(f"Jira read failed: {code}")


@dataclass(frozen=True, repr=False)
class JiraConnection:
    tenant_id: str
    cloud_id: str
    project_key: str
    email: str = field(repr=False)
    api_token: str = field(repr=False)
    site_url: str | None = None

    @property
    def api_base(self):
        return ((self.site_url if self.site_url else f'https://api.atlassian.com/ex/jira/{self.cloud_id}')
                + '/rest/api/3/')

    def __repr__(self):
        return "JiraConnection(credentials=REDACTED)"

    def __post_init__(self):
        try:
            valid = (bool(self.tenant_id) and str(UUID(self.cloud_id)) == self.cloud_id
                     and re.fullmatch(r"[A-Z][A-Z0-9_]{1,19}", self.project_key)
                     and self.email and self.api_token
                     and ":" not in self.email
                     and not any(c.isspace() for c in self.email + self.api_token))
            if self.site_url is not None:
                valid=valid and bool(re.fullmatch(r'https://[a-z0-9][a-z0-9-]{0,62}\.atlassian\.net',self.site_url))
        except (ValueError, TypeError, AttributeError):
            valid = False
        if not valid:
            raise JiraReadError("invalid_configuration") from None


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def http_get(url: str, authorization: str) -> tuple[int, bytes]:
    request = Request(url, method="GET", headers={
        "Authorization": authorization, "Accept": "application/json"})
    try:
        with build_opener(NoRedirect()).open(request, timeout=20) as response:
            return response.status, response.read(MAX_BYTES + 1)
    except HTTPError as error:
        status = error.code
        error.close()
        return status, b""  # Never inspect upstream error body or headers.
    except Exception:
        raise JiraReadError("transport_error") from None


class JiraReader:
    def __init__(self, connection: JiraConnection,
                 transport: Callable[[str, str], tuple[int, bytes]] = http_get):
        self._connection = connection
        self._transport = transport

    def read(self, actor: Actor, issue_key: str) -> Ticket:
        connection = self._connection
        require_staff(actor, connection.tenant_id)
        if not isinstance(issue_key, str) or not re.fullmatch(
                re.escape(connection.project_key) + r"-[1-9][0-9]{0,11}", issue_key):
            raise JiraReadError("issue_out_of_scope")
        encoded = base64.b64encode(
            f"{connection.email}:{connection.api_token}".encode()).decode("ascii")
        url = (connection.api_base + "issue/"
               f"{issue_key}?fields=summary,status,project")
        try:
            status, body = self._transport(url, f"Basic {encoded}")
        except Exception:
            raise JiraReadError("transport_error") from None
        if status != 200:
            code = {401: "authentication_rejected", 403: "forbidden",
                    404: "not_found", 429: "rate_limited"}.get(status, "http_error")
            raise JiraReadError(code, status)
        try:
            if len(body) > MAX_BYTES:
                raise ValueError()
            payload = json.loads(body)
            fields = payload["fields"]
            summary, source_status = fields["summary"], fields["status"]["name"]
            if (payload["key"] != issue_key
                    or fields["project"]["key"] != connection.project_key
                    or not isinstance(summary, str) or not 0 < len(summary) <= 1000
                    or not isinstance(source_status, str) or not 0 < len(source_status) <= 100):
                raise ValueError()
            for secret in (connection.api_token, connection.email, encoded):
                summary = summary.replace(secret, "[REDACTED]")
                source_status = source_status.replace(secret, "[REDACTED]")
            summary = re.sub(r"[\x00-\x1f\x7f-\x9f]", " ", summary)
            source_status = re.sub(r"[\x00-\x1f\x7f-\x9f]", " ", source_status)
        except Exception:
            raise JiraReadError("invalid_response") from None
        return Ticket(connection.tenant_id, issue_key, connection.project_key,
                      summary, source_status, datetime.now(timezone.utc))
