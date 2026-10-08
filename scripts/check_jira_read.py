"""One bounded, read-only Jira check. Never print credentials or raw errors.

Uses only Python's standard library. Reads the project's .env internally.
No redirects, retries, writes to Jira, or automatic scope expansion.
"""

import base64
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import HTTPRedirectHandler, Request, build_opener

ROOT = Path(__file__).resolve().parents[1]
CLOUD_ID = "86f72776-2ba9-422b-aaad-184f0ed671be"
ISSUE = "IT-1"


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def load_config():
    values = {}
    for line in (ROOT / ".env").read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:]
        key, separator, value = line.partition("=")
        if not separator or not key.strip().startswith("JIRA_"):
            continue
        key, value = key.strip(), value.strip()
        if len(value) >= 2 and value[0] in "\"'" and value[-1] == value[0]:
            value = value[1:-1]
        if key in values:
            raise ValueError("Invalid configuration")
        values[key] = value
    return values


def check():
    result = {"checked_at_utc": datetime.now(timezone.utc).isoformat(),
              "operation": "GET issue IT-1", "result": "failed"}
    try:
        config = load_config()
        email, token = config.get("JIRA_EMAIL", ""), config.get("JIRA_API_TOKEN", "")
        if not email or not token or any(c.isspace() for c in email + token):
            raise ValueError("Invalid configuration")
        if (config.get("JIRA_CLOUD_ID") != CLOUD_ID
                or config.get("JIRA_PROJECT_KEY") != "IT"
                or config.get("JIRA_TEST_ISSUE_KEY") != ISSUE):
            raise ValueError("Unexpected test target")
        auth = base64.b64encode(f"{email}:{token}".encode()).decode("ascii")

        def safe_text(value):
            if not isinstance(value, str):
                raise ValueError("Invalid response")
            for secret in (token, email, auth):
                value = value.replace(secret, "[REDACTED]")
            return re.sub(r"[\x00-\x1f\x7f-\x9f]", " ", value)[:200]

        url = (f"https://api.atlassian.com/ex/jira/{CLOUD_ID}/rest/api/3/issue/"
               f"{ISSUE}?fields=summary,status")
        request = Request(url, method="GET", headers={
            "Authorization": f"Basic {auth}", "Accept": "application/json"})
        with build_opener(NoRedirect()).open(request, timeout=20) as response:
            result["http_status"] = response.status
            raw = response.read(262145)
            if len(raw) > 262144:
                raise ValueError("Response too large")
            data = json.loads(raw)
        if data.get("key") != ISSUE:
            raise ValueError("Unexpected issue")
        fields = data["fields"]
        result.update(result="passed", issue_key=ISSUE,
                      summary=safe_text(fields["summary"]),
                      status=safe_text(fields["status"]["name"]))
    except HTTPError as error:
        # Do not read/print error body, headers, URL or exception text.
        result["http_status"] = error.code
        result["error"] = {
            401: "Authentication rejected; check account email, token and expiry locally.",
            403: "Access denied; check token scope and Jira permissions.",
            404: "Issue not visible or target not found.",
            429: "Rate limited; retry later manually.",
        }.get(error.code, "HTTP request failed; no response details displayed.")
        error.close()
    except (FileNotFoundError, ValueError, KeyError, TypeError, AttributeError):
        result["error"] = "Configuration or response validation failed; values withheld."
    except Exception:
        result["error"] = "Connection or local check failed; details withheld."
    return result


def main():
    result = check()
    evidence = ROOT / "docs" / "phase-0" / "jira-read-check.json"
    try:
        evidence.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    except OSError:
        result["evidence_saved"] = False
    print(json.dumps(result, indent=2))
    return 0 if result["result"] == "passed" else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("Check cancelled; no credentials displayed.")
        sys.exit(130)
    except Exception:
        print("Check failed; diagnostic details withheld.")
        sys.exit(1)
