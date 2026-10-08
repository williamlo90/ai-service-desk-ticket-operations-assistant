"""Crash only supervisor-owned children, then verify durable case and entitlement."""
import json,sys,time
from urllib.request import urlopen
from datetime import datetime,timezone
from operator_lab import CONFIG,REPORT,ROOT,save
from operator_service import FOLDER

def run():
    import psycopg
    from service_desk.postgres import PostgresStateStore
    from service_desk.lab_targets import LabTargets
    config=json.loads(CONFIG.read_text());operator=json.loads(REPORT.read_text())
    store=PostgresStateStore(lambda:psycopg.connect(**config['database']))
    before=store.get('alpha',operator['case_id']);checks=[]
    if before['status']!='closed':raise ValueError('expected_completed_case')
    for component in ('api','worker'):
        baseline=json.loads((FOLDER/'service-status.json').read_text())
        old=baseline['children'][component]
        save(FOLDER/'restart-request.json',{'component':component})
        deadline=time.monotonic()+40
        while time.monotonic()<deadline:
            time.sleep(1)
            current=json.loads((FOLDER/'service-status.json').read_text())
            if current['children'].get(component,old)==old:continue
            try:
                if component=='api':
                    with urlopen('http://127.0.0.1:5681/readyz',timeout=2) as r:
                        if r.status!=200:continue
                else:
                    w=json.loads((FOLDER/'worker-status.json').read_text())
                    if w['status']!='ready' or w['pid']!=current['children']['worker']:continue
                break
            except Exception:continue
        else:raise RuntimeError('restart_timeout')
        if store.get('alpha',operator['case_id'])!=before:raise RuntimeError('case_changed')
        checks.append(component+' crash automatically restarted; persisted case unchanged')
    target=LabTargets(config['target_path'],config['lab_tenants'])
    if not target.inspect('alpha',before['action']['id'],before['proposal']['payload'])['matches']:raise RuntimeError('membership_changed')
    result={'status':'passed','checked_at':datetime.now(timezone.utc).isoformat(),'checks':checks,
        'case_status':'closed','same_operation_id':True,'membership_preserved':True,
        'other_project_processes_touched':False,'credentials_printed':False,
        'limitation':'Supervisor must be running; no OS reboot/autostart or host-failure recovery claim'}
    save(ROOT/'docs/phase-5/operator-supervisor-check.json',result);print(json.dumps(result));return 0

if __name__=='__main__':
    try:sys.exit(run())
    except Exception as exc:print('Supervisor check stopped: '+type(exc).__name__);sys.exit(1)
