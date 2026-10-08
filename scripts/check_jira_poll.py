"""Enable the selected bounded poller only after connected Jira acceptance passes."""
import json,sys,time
from operator_lab import ROOT,save
from operator_service import FOLDER

def main():
    acceptance=json.loads((ROOT/'docs/phase-5/jira-connected-check.json').read_text())
    if acceptance['status']!='passed':raise ValueError('connected_gate_required')
    (FOLDER/'enable-jira-poll').write_text('IT-1 and IT-2 only\n')
    (FOLDER/'resume-jira-poll').write_text('explicit acceptance resume\n')
    deadline=time.monotonic()+70
    while time.monotonic()<deadline:
        path=FOLDER/'poll-status.json'
        if path.exists():
            status=json.loads(path.read_text())
            if status['status']=='review_required':raise RuntimeError('poll_requires_review')
            if status['status']=='ready' and {x['key'] for x in status['results']}=={'IT-1','IT-2'}:
                if any(x['status']!='synchronized' for x in status['results']):raise RuntimeError('source_drift')
                report={'status':'passed','checked_at':status['checked_at'],'keys':['IT-1','IT-2'],
                    'interval_seconds':60,'public_webhook_receiver':False,'error_policy':'durable review latch; explicit manual resume',
                    'credentials_printed':False}
                save(ROOT/'docs/phase-5/jira-poll-check.json',report);print(json.dumps(report));return 0
        time.sleep(1)
    raise RuntimeError('poll_timeout')

if __name__=='__main__':
    try:sys.exit(main())
    except Exception as exc:print('Poll check stopped: '+type(exc).__name__);sys.exit(1)
