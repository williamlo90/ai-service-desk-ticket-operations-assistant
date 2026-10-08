"""Persistent local operator lab. Secrets are consumed internally, never printed.

Only import-jira reads Jira credentials internally using the authorized loader.
No command approves a proposal, executes a target, or writes to Jira.
"""
from datetime import datetime,timedelta,timezone
from pathlib import Path
import io,json,secrets,sys,time
from setup_target_sandbox import ROOT,PRIVATE,command
from check_database import sql as admin_sql

sys.path.insert(0,str(ROOT/'backend'))
CONFIG=PRIVATE/'operator.json'
REPORT=ROOT/'docs/phase-5/operator-lab.json'

def save(path,value):
    temporary=path.with_name(path.name+'.'+secrets.token_hex(6)+'.tmp')
    temporary.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
    try:
        for attempt in range(10):
            try:temporary.replace(path);break
            except PermissionError:
                if attempt==9:raise
                time.sleep(0.05)
    finally:
        temporary.unlink(missing_ok=True)

def setup():
    import psycopg
    from service_desk.migrations import migrate
    if not PRIVATE.is_dir():raise RuntimeError('sandbox_setup_required')
    if CONFIG.exists():
        config=json.loads(CONFIG.read_text())
    else:
        lab=json.loads((PRIVATE/'bootstrap.json').read_text())
        name='sdoperator_'+secrets.token_hex(6)
        expiry=(datetime.now(timezone.utc)+timedelta(hours=24)).isoformat()
        db=dict(host='127.0.0.1',port=5433,dbname=name,connect_timeout=5,
                options='-c statement_timeout=5000 -c lock_timeout=3000')
        tokens={t:{r:secrets.token_hex(32) for r in ('staff','supervisor')} for t in ('alpha','beta')}
        bindings={token:{'actor_id':'William' if role=='supervisor' else 'lab-integration-'+tenant,
            'tenant_id':tenant,'role':role if role=='supervisor' else 'specialist','expires_at':expiry}
            for tenant,roles in tokens.items() for role,token in roles.items()}
        target=ROOT/'local/operator-lab';target.mkdir(parents=True,exist_ok=True)
        config={'mode':'lab','port':5681,'bindings':bindings,'tokens':tokens,
            'database':{**db,'user':name+'_runtime','password':secrets.token_hex(32)},
            'migration_database':{**db,'user':name+'_owner','password':secrets.token_hex(32)},
            'target_path':str(target/'targets.sqlite'),'lab_tenants':lab['tenants']}
        save(CONFIG,config)
    owner=config['migration_database'];runtime=config['database'];name=runtime['dbname']
    def admin(statement):
        result=admin_sql(statement,database='postgres')
        if result.returncode:raise RuntimeError('operator_database_setup_failed')
        return result.stdout.strip()
    # All names and passwords originate here; never accept arbitrary SQL values.
    import re
    if not re.fullmatch('sdoperator_[a-f0-9]{12}',name):raise ValueError()
    for c,suffix in ((owner,'_owner'),(runtime,'_runtime')):
        if c['user']!=name+suffix or not re.fullmatch('[a-f0-9]{64}',c['password']):raise ValueError()
        if admin("SELECT count(*) FROM pg_roles WHERE rolname='"+c['user']+"'")=='0':
            admin(f"CREATE ROLE {c['user']} LOGIN PASSWORD '{c['password']}' NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOBYPASSRLS")
    if admin(f"SELECT count(*) FROM pg_database WHERE datname='{name}'")=='0':
        admin(f"CREATE DATABASE {name} OWNER {owner['user']}")
    admin(f"REVOKE ALL ON DATABASE {name} FROM PUBLIC; GRANT CONNECT ON DATABASE {name} TO {runtime['user']}")
    migrate(lambda:psycopg.connect(**owner))
    with psycopg.connect(**owner) as conn:
        user=runtime['user']
        conn.execute(f'REVOKE ALL ON SCHEMA public FROM PUBLIC; GRANT USAGE ON SCHEMA public TO {user}')
        conn.execute(f'GRANT SELECT,INSERT ON sd_case_intake,sd_audit TO {user}')
        conn.execute(f'GRANT SELECT,INSERT,UPDATE ON sd_journey TO {user}')
    with psycopg.connect(**runtime) as conn:
        flags=conn.execute('SELECT rolsuper,rolcreatedb,rolcreaterole,rolbypassrls FROM pg_roles WHERE rolname=current_user').fetchone()
        if flags!=(False,False,False,False):raise RuntimeError('unexpected_runtime_privilege')
    for tenant in ('alpha','beta'):
        (PRIVATE/('william-'+tenant+'-approval-token.txt')).write_text(config['tokens'][tenant]['supervisor'],encoding='utf-8')
    report=json.loads(REPORT.read_text()) if REPORT.exists() else {}
    report.setdefault('status','configured')
    report.update(origin='http://127.0.0.1:5681',business_owner='William',
        operational_approver='William',credential_custodian='William',
        token_expires_at=next(iter(config['bindings'].values()))['expires_at'],
        database_persistent=True,runtime_privileges_checked=True,project_dotenv_read_by_setup=False)
    report.setdefault('human_approval_recorded',False)
    save(REPORT,report)
    print('Persistent operator lab configured. William approval tokens saved privately; no approval performed.')

def serve():
    from service_desk.runtime_api import main
    config=json.loads(CONFIG.read_text())
    config={k:v for k,v in config.items() if k not in ('migration_database','tokens')}
    sys.stdin=io.TextIOWrapper(io.BytesIO((json.dumps(config)+'\n').encode()))
    return main()

def import_jira():
    import psycopg
    from check_jira_read import load_config,CLOUD_ID,SITE_URL
    from service_desk.jira import JiraConnection,JiraReader
    from service_desk.contracts import Actor,Role
    from service_desk.journeys import JourneyService
    from service_desk.postgres import PostgresStateStore
    from service_desk.lab_targets import LabTargets
    config=json.loads(CONFIG.read_text());jira=load_config()
    if (jira.get('JIRA_CLOUD_ID')!=CLOUD_ID or jira.get('JIRA_PROJECT_KEY')!='IT'
            or jira.get('JIRA_TEST_ISSUE_KEY')!='IT-1'):raise ValueError()
    actor=Actor('lab-integration-alpha','alpha',Role.SPECIALIST)
    ticket=JiraReader(JiraConnection('alpha',CLOUD_ID,'IT',jira['JIRA_EMAIL'],jira['JIRA_API_TOKEN'],site_url=SITE_URL)).read(actor,'IT-1')
    if not ticket.summary.startswith('[TEST]'):raise ValueError()
    service=JourneyService(PostgresStateStore(lambda:psycopg.connect(**config['database'])),
        LabTargets(config['target_path'],config['lab_tenants']))
    state=service.import_ticket(actor,ticket,CLOUD_ID,config['lab_tenants']['alpha']['requester'])
    if state['classification']['category']!='access_request':raise ValueError()
    if not state['proposal']:state=service.prepare(actor,state['id'],state['version'])
    report=json.loads(REPORT.read_text())
    report.setdefault('jira_writes',0)
    report.update(status='local_case_closed' if state['status']=='closed' else 'awaiting_human_review',issue='IT-1',case_id=state['id'],
        review_url='http://127.0.0.1:5681/?case='+state['id'],jira_gets_this_run=1,
        credentials_loaded_internally=True,credentials_printed=False,
        human_approval_recorded=state['approval'] is not None,target_dispatched=state['action'] is not None,
        source_observed_at=state['source_observed_at'])
    save(REPORT,report)
    print(json.dumps({k:report[k] for k in ('status','issue','case_id','review_url','jira_writes','target_dispatched')}))

if __name__=='__main__':
    try:
        action=sys.argv[1]
        if action=='setup':setup()
        elif action=='serve':sys.exit(serve())
        elif action=='import-jira':import_jira()
        else:raise ValueError()
    except Exception as exc:
        print('Operator lab stopped: '+type(exc).__name__+'. Details withheld; no credentials displayed.')
        sys.exit(1)
