"""Foreground supervisor for this lab's API and approved-job worker only.

Launch hidden on Windows. Stop by creating local/operator-lab/stop-service.
No OS startup registration; process crashes are restarted while supervisor lives.
"""
import json,os,subprocess,sys,time,sysconfig
from datetime import datetime,timezone
from operator_lab import CONFIG,ROOT,save

FOLDER=ROOT/'local/operator-lab'
def poll_jira():
    import psycopg
    from check_jira_read import load_config,CLOUD_ID,SITE_URL
    from service_desk.jira import JiraConnection
    from service_desk.jira_search import JiraSearch,sync
    from service_desk.runtime_api import RuntimeAuthenticator
    from service_desk.journeys import JourneyService
    from service_desk.postgres import PostgresStateStore
    from service_desk.lab_targets import LabTargets
    config=json.loads(CONFIG.read_text());blocked=(FOLDER/'poll-blocked.json').exists()
    service=JourneyService(PostgresStateStore(lambda:psycopg.connect(**config['database'])),
        LabTargets(config['target_path'],config['lab_tenants']))
    auth=RuntimeAuthenticator(config['bindings']);next_poll=0
    while not (FOLDER/'stop-service').exists():
        resume=FOLDER/'resume-jira-poll'
        if resume.exists():
            resume.unlink();(FOLDER/'poll-blocked.json').unlink(missing_ok=True);blocked=False
        if time.monotonic()<next_poll or blocked or not (FOLDER/'enable-jira-poll').exists():
            time.sleep(1);continue
        try:
            c=load_config()
            if c['JIRA_CLOUD_ID']!=CLOUD_ID or c['JIRA_PROJECT_KEY']!='IT':raise ValueError('scope_changed')
            actor=auth.authenticate('Bearer '+config['tokens']['alpha']['staff'])
            search=JiraSearch(JiraConnection('alpha',CLOUD_ID,'IT',c['JIRA_EMAIL'],c['JIRA_API_TOKEN'],site_url=SITE_URL),['IT-1','IT-2'])
            results=sync(service,actor,search,config['lab_tenants']['alpha']['requester'])
            save(FOLDER/'poll-status.json',{'status':'ready','checked_at':datetime.now(timezone.utc).isoformat(),
                'pid':os.getpid(),'results':results})
            next_poll=time.monotonic()+60
        except Exception as exc:
            # Latch on any failure: notably 429 never produces an automatic retry
            # that might violate Retry-After. Resume requires explicit poll restart.
            blocked=True
            save(FOLDER/'poll-blocked.json',{'error':type(exc).__name__,'manual_resume_required':True})
            save(FOLDER/'poll-status.json',{'status':'review_required','error':type(exc).__name__,
                'pid':os.getpid(),'automatic_retries':0})

def worker():
    import psycopg
    from service_desk.runtime_api import RuntimeAuthenticator
    from service_desk.postgres import PostgresStateStore
    from service_desk.journeys import JourneyService,canonical
    from service_desk.lab_targets import LabTargets
    from service_desk.worker import scan
    from service_desk.jira import JiraReader,JiraConnection
    from check_jira_read import load_config,SITE_URL
    config=json.loads(CONFIG.read_text())
    auth=RuntimeAuthenticator(config['bindings'])
    service=JourneyService(PostgresStateStore(lambda:psycopg.connect(**config['database'])),
        LabTargets(config['target_path'],config['lab_tenants']))
    # Actor bindings are revalidated on each scan, including identity expiry.
    while not (FOLDER/'stop-service').exists():
        try:
            results=[]
            for tenant in ('alpha','beta'):
                actor=auth.authenticate('Bearer '+config['tokens'][tenant]['staff'])
                def unchanged(state):
                    c=load_config();source=state['source']
                    if c['JIRA_CLOUD_ID']!=source['cloud_id'] or c['JIRA_PROJECT_KEY']!=source['project']:return False
                    ticket=JiraReader(JiraConnection(tenant,c['JIRA_CLOUD_ID'],c['JIRA_PROJECT_KEY'],c['JIRA_EMAIL'],c['JIRA_API_TOKEN'],site_url=SITE_URL)).read(actor,source['key'])
                    return source['summary']==ticket.summary and source['status']==ticket.source_status
                results.extend(scan(service,actor,unchanged))
            save(FOLDER/'worker-status.json',{'status':'ready','checked_at':datetime.now(timezone.utc).isoformat(),
                'results':results,'pid':os.getpid()})
            time.sleep(1)
        except Exception as exc:
            save(FOLDER/'worker-status.json',{'status':'review_required','error':type(exc).__name__,'pid':os.getpid()})
            time.sleep(10)

def supervise():
    FOLDER.mkdir(parents=True,exist_ok=True)
    # Exclusive lifetime lock prevents accidentally launching competing supervisors.
    lock=open(FOLDER/'supervisor.lock','a+b')
    if os.name=='nt':
        import msvcrt
        lock.seek(0);lock.write(b'1');lock.flush();lock.seek(0)
        msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
    children={};starts={'api':0,'worker':0,'poll':0};due={'api':0,'worker':0,'poll':0}
    # Windows venv python.exe is a launcher. Direct base Python avoids orphaning
    # its real child when the launcher is killed; preserve venv dependencies.
    executable=sys._base_executable if os.name=='nt' else sys.executable
    child_env={**os.environ,'PYTHONPATH':os.pathsep.join([sysconfig.get_paths()['purelib'],str(ROOT/'backend')])}
    commands={'api':[executable,'-B',str(ROOT/'scripts/operator_lab.py'),'serve'],
              'worker':[executable,'-B',str(Path(__file__).resolve()),'worker'],
              'poll':[executable,'-B',str(Path(__file__).resolve()),'poll']}
    try:
        while not (FOLDER/'stop-service').exists():
            restart=FOLDER/'restart-request.json'
            if restart.exists():
                raw=restart.read_text();restart.unlink()
                if len(raw)>256:raise ValueError('restart_request_limit')
                name=json.loads(raw)['component']
                if name not in commands:raise ValueError('unknown_component')
                process=children.get(name)
                if process is not None and process.poll() is None:process.kill();process.wait(timeout=5)
            for name,args in commands.items():
                process=children.get(name)
                if process is not None and process.poll() is not None:
                    children.pop(name);due[name]=time.monotonic()+min(30,2**min(starts[name],5))
                if name not in children and time.monotonic()>=due[name]:
                    children[name]=subprocess.Popen(args,cwd=ROOT,env=child_env,stdin=subprocess.DEVNULL,
                        stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,
                        creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
                    starts[name]+=1
            save(FOLDER/'service-status.json',{'supervisor_pid':os.getpid(),
                'children':{name:p.pid for name,p in children.items()},'starts':starts,
                'checked_at':datetime.now(timezone.utc).isoformat()})
            time.sleep(1)
    finally:
        for p in children.values():
            if p.poll() is None:
                p.terminate()
                try:p.wait(timeout=5)
                except subprocess.TimeoutExpired:p.kill();p.wait(timeout=5)
        lock.close()

from pathlib import Path
if __name__=='__main__':
    try:
        if sys.argv[1:]==['worker']:worker()
        elif sys.argv[1:]==['poll']:poll_jira()
        else:supervise()
    except Exception as exc:
        print('Operator service stopped: '+type(exc).__name__);sys.exit(1)
