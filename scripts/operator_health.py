"""Read-only operator health; private values never leave this process."""
from datetime import datetime,timezone,timedelta
import json,sys
from urllib.request import build_opener
from operator_lab import CONFIG,ROOT,save
from service_desk.health import assess
from service_desk.jira import NoRedirect


def collect():
    folder=ROOT/'local/operator-lab';now=datetime.now(timezone.utc)
    snapshot={}
    for component,file in (('service','service-status.json'),('worker','worker-status.json'),('poll','poll-status.json')):
        try:
            raw=(folder/file).read_text()
            snapshot[component]=json.loads(raw) if len(raw)<=262144 else {}
        except (OSError,ValueError):snapshot[component]={}
    snapshot['poll_enabled']=(folder/'enable-jira-poll').exists()
    snapshot['poll_blocked']=(folder/'poll-blocked.json').exists()
    try:
        with build_opener(NoRedirect()).open('http://127.0.0.1:5681/readyz',timeout=3) as response:
            snapshot['api_ready']=response.status==200
    except Exception:snapshot['api_ready']=False
    try:
        config=json.loads(CONFIG.read_text())
        expiry=[datetime.fromisoformat(v['expires_at']) for v in config['bindings'].values()]
        snapshot['expired_bindings']=sum(t<=now for t in expiry)
        snapshot['expiring_bindings']=sum(now<t<=now+timedelta(hours=1) for t in expiry)
    except Exception:snapshot['expired_bindings']=1
    return assess(snapshot,now)


if __name__=='__main__':
    report=collect()
    save(ROOT/'local/operator-lab/health.json',report)
    if '--report' in sys.argv:save(ROOT/'docs/phase-7/operator-health.json',report)
    print(json.dumps(report,indent=2))
    sys.exit(0 if report['status']=='ready' else 2)
