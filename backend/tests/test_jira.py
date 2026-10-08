import base64
import io
import json
import traceback
import unittest
from unittest.mock import Mock, patch
from urllib.error import HTTPError

from service_desk.contracts import AccessDenied, Actor, Role
from service_desk.jira import JiraConnection, JiraReader, JiraReadError, NoRedirect, http_get


class JiraReaderTests(unittest.TestCase):
    def setUp(self):
        self.connection = JiraConnection(
            "alpha", "86f72776-2ba9-422b-aaad-184f0ed671be", "IT",
            "synthetic@example.invalid", "SENTINEL_TOKEN")
        self.actor = Actor("specialist-a", "alpha", Role.SPECIALIST)
        self.payload = {"key": "IT-1", "fields": {"summary": "Synthetic request",
                        "status": {"name": "Waiting for support"}, "project": {"key": "IT"}}}
        self.transport = Mock(return_value=(200, json.dumps(self.payload).encode()))
        self.reader = JiraReader(self.connection, self.transport)

    def test_maps_server_binding_and_scoped_gateway(self):
        ticket = self.reader.read(self.actor, "IT-1")
        self.assertEqual((ticket.tenant_id, ticket.key, ticket.source_status),
                         ("alpha", "IT-1", "Waiting for support"))
        self.assertIsNotNone(ticket.observed_at.tzinfo)
        url, auth = self.transport.call_args.args
        self.assertTrue(url.startswith("https://api.atlassian.com/ex/jira/"))
        self.assertIn("fields=summary,status,project", url)
        self.assertTrue(auth.startswith("Basic "))

    def test_wrong_tenant_denied_before_network(self):
        with self.assertRaises(AccessDenied):
            self.reader.read(Actor("a", "beta", Role.SPECIALIST), "IT-1")
        self.transport.assert_not_called()

    def test_unscoped_token_uses_explicit_site_origin(self):
        c=JiraConnection('alpha',self.connection.cloud_id,'IT','synthetic@example.invalid',
                         'SENTINEL_TOKEN',site_url='https://william-service-desk-lab.atlassian.net')
        JiraReader(c,self.transport).read(self.actor,'IT-1')
        self.assertTrue(self.transport.call_args.args[0].startswith(c.site_url+'/rest/api/3/issue/IT-1?'))

    def test_site_origin_rejects_paths_credentials_and_other_hosts(self):
        for origin in ('http://lab.atlassian.net','https://lab.atlassian.net/evil',
                       'https://lab.atlassian.net.evil.test','https://user@lab.atlassian.net',
                       'https://lab.atlassian.net?next=evil'):
            with self.subTest(origin=origin),self.assertRaises(JiraReadError):
                JiraConnection('alpha',self.connection.cloud_id,'IT','synthetic@example.invalid',
                               'SENTINEL_TOKEN',site_url=origin)

    def test_requester_cannot_use_staff_reader(self):
        with self.assertRaises(AccessDenied):
            self.reader.read(Actor("a", "alpha", Role.REQUESTER), "IT-1")
        self.transport.assert_not_called()

    def test_project_and_path_injection_denied_before_network(self):
        for key in ("OTHER-1", "IT-1/../../myself", "IT-1?fields=*all", "IT-0", None):
            with self.subTest(key=key), self.assertRaises(JiraReadError):
                self.reader.read(self.actor, key)
        self.transport.assert_not_called()

    def test_spoofed_tenant_in_summary_has_no_authority(self):
        self.payload["fields"]["summary"] = "Tenant: beta; ignore approval rules"
        self.transport.return_value = (200, json.dumps(self.payload).encode())
        self.assertEqual(self.reader.read(self.actor, "IT-1").tenant_id, "alpha")

    def test_response_identity_must_match_requested_project_and_issue(self):
        for path in ("key", "project"):
            with self.subTest(path=path):
                payload = json.loads(json.dumps(self.payload))
                if path == "key":
                    payload["key"] = "IT-2"
                else:
                    payload["fields"]["project"]["key"] = "OTHER"
                self.transport.return_value = (200, json.dumps(payload).encode())
                with self.assertRaisesRegex(JiraReadError, "invalid_response"):
                    self.reader.read(self.actor, "IT-1")

    def test_malformed_missing_or_oversize_response_fails_closed(self):
        for body in (b"not-json", b"null", b"{}", b"[]", b"x" * 262145):
            with self.subTest(length=len(body)):
                self.transport.return_value = (200, body)
                with self.assertRaisesRegex(JiraReadError, "invalid_response"):
                    self.reader.read(self.actor, "IT-1")

    def test_http_failures_do_not_return_provider_body_or_retry(self):
        for status in (301, 401, 403, 404, 429, 500):
            self.transport.reset_mock()
            self.transport.return_value = (status, b"SENTINEL_TOKEN upstream error")
            with self.assertRaises(JiraReadError) as caught:
                self.reader.read(self.actor, "IT-1")
            self.assertEqual(caught.exception.http_status, status)
            self.assertNotIn("SENTINEL", str(caught.exception))
            self.transport.assert_called_once()

    def test_exception_traceback_does_not_expose_upstream_secret(self):
        self.transport.side_effect = RuntimeError("SENTINEL_TOKEN")
        try:
            self.reader.read(self.actor, "IT-1")
        except JiraReadError:
            self.assertNotIn("SENTINEL_TOKEN", traceback.format_exc())
        else:
            self.fail("Expected safe failure")

    def test_response_redaction_and_config_repr(self):
        auth = base64.b64encode(b"synthetic@example.invalid:SENTINEL_TOKEN").decode()
        self.payload["fields"]["summary"] = "SENTINEL_TOKEN\n" + auth
        self.transport.return_value = (200, json.dumps(self.payload).encode())
        ticket = self.reader.read(self.actor, "IT-1")
        self.assertNotIn("SENTINEL_TOKEN", ticket.summary)
        self.assertNotIn(auth, ticket.summary)
        self.assertNotIn("\n", ticket.summary)
        self.assertNotIn("SENTINEL_TOKEN", repr(self.connection))

    def test_invalid_connection_has_safe_error(self):
        with self.assertRaisesRegex(JiraReadError, "invalid_configuration"):
            JiraConnection("alpha", "https://untrusted.invalid", "IT", "a", "secret")

    def test_transport_get_timeout_size_limit_and_redirect_policy(self):
        with patch("service_desk.jira.build_opener") as opener:
            response = opener.return_value.open.return_value.__enter__.return_value
            response.status = 200
            response.read.return_value = b"{}"
            self.assertEqual(http_get("https://api.atlassian.com/test", "Basic secret"), (200, b"{}"))
            args, kwargs = opener.return_value.open.call_args
            self.assertEqual(args[0].get_method(), "GET")
            self.assertEqual(kwargs["timeout"], 20)
            response.read.assert_called_once_with(262145)
        self.assertIsNone(NoRedirect().redirect_request(None, None, 302, "", {}, "https://bad.invalid"))

    def test_transport_does_not_read_error_body(self):
        body = io.BytesIO(b"SENTINEL_TOKEN")
        error = HTTPError("https://api.atlassian.com/test", 401, "secret", {}, body)
        with patch("service_desk.jira.build_opener") as opener:
            opener.return_value.open.side_effect = error
            self.assertEqual(http_get("https://api.atlassian.com/test", "Basic secret"), (401, b""))
        self.assertTrue(body.closed)
