"""Read-only local n8n readiness and access-boundary smoke check."""
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def main():
    report = {'checked_at_utc': datetime.now(timezone.utc).isoformat(), 'checks': []}
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    try:
        for path, expected in [('/healthz',200),('/healthz/readiness',200),('/',200),('/rest/workflows',401)]:
            try:
                with opener.open('http://127.0.0.1:5678'+path, timeout=10) as response:
                    code = response.status
            except urllib.error.HTTPError as exc:
                code = exc.code
                exc.close()
            if code != expected:
                raise RuntimeError(f'{path}: unexpected HTTP {code}')
            report['checks'].append(f'{path}: HTTP {code}')
        result = subprocess.run(['docker','inspect','service-desk-lab-n8n-1','--format',
            '{{json .HostConfig}}'],capture_output=True,text=True,timeout=10)
        config = json.loads(result.stdout)
        if config['Memory'] != 1073741824 or config['NanoCpus'] != 1000000000:
            raise RuntimeError('resource limits mismatch')
        if config['PortBindings']['5678/tcp'] != [{'HostIp':'127.0.0.1','HostPort':'5678'}]:
            raise RuntimeError('port binding mismatch')
        report['checks'].append('1 GiB / 1 CPU and loopback-only port enforced')
        report['status'] = 'passed'
        report['limitations'] = 'Owner account, workflow execution and business acceptance not tested.'
    except Exception as exc:
        report['status'] = 'failed'
        report['failure'] = str(exc) if type(exc) is RuntimeError else type(exc).__name__
    (ROOT/'docs/phase-1/n8n-check.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2))
    return 0 if report['status'] == 'passed' else 1


if __name__ == '__main__':
    sys.exit(main())
