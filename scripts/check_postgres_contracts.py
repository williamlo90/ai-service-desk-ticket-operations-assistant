"""Real adapter checks in a disposable database on the project-owned DB container.

Never reads .env, restarts a service, or logs connection strings/SQL errors.
Only generated sdcheck_* databases/roles created by this run are removed.
"""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import datetime,timezone
import json
from pathlib import Path
import secrets
import subprocess
import sys
from threading import Barrier

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
from check_database import sql as admin_sql
from connected_checks import check_connected,ConnectedCheckFailed
from service_desk.cases import Intake,CaseError
from service_desk.contracts import Actor,Role
from service_desk.journeys import JourneyService
from service_desk.migrations import migrate
from service_desk.postgres import PostgresCaseRepository,PostgresStateStore
from service_desk.simulator import SimulatedTarget
from service_desk.store import Conflict,Missing


class CheckFailed(Exception):pass


def require(condition,label):
    if not condition:raise CheckFailed(label)


def run():
    import psycopg
    suffix=secrets.token_hex(6)
    database='sdcheck_'+suffix
    owner=database+'_owner';runtime=database+'_runtime'
    owner_password=secrets.token_hex(32);runtime_password=secrets.token_hex(32)
    created_roles=[];created_database=False
    report={'checked_at_utc':datetime.now(timezone.utc).isoformat(),
            'scope':'disposable PostgreSQL database; actual Python adapters',
            'checks':[],'docker_used':True,'project_dotenv_read':False,
            'database_secret_read_inside_container':True,'secrets_printed':False,
            'container_restarted':False,'live_saas_calls':0,'frozen_evaluator_passed':False}
    def privileged(statement,label):
        result=admin_sql(statement,database='postgres')
        require(result.returncode==0,label)
    def config(user,password):
        return dict(host='127.0.0.1',port=5433,dbname=database,user=user,password=password,
                    connect_timeout=5,options='-c statement_timeout=5000 -c lock_timeout=3000')
    owner_config=config(owner,owner_password);runtime_config=config(runtime,runtime_password)
    connect_owner=lambda:psycopg.connect(**owner_config)
    connect=lambda:psycopg.connect(**runtime_config)
    try:
        for role,password in ((owner,owner_password),(runtime,runtime_password)):
            # Identifiers/passwords are locally generated lowercase hex, sent via stdin.
            privileged(f"CREATE ROLE {role} LOGIN PASSWORD '{password}' NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOBYPASSRLS;",'role_setup')
            created_roles.append(role)
        privileged(f'CREATE DATABASE {database} OWNER {owner};','database_setup');created_database=True
        privileged(f'REVOKE ALL ON DATABASE {database} FROM PUBLIC; GRANT CONNECT ON DATABASE {database} TO {runtime};','database_grants')
        migrate(connect_owner);migrate(connect_owner)
        with connect_owner() as conn:
            require(conn.execute('SELECT count(*) FROM sd_schema_version').fetchone()[0]==1,'migration_replay')
            checksum=conn.execute('SELECT checksum FROM sd_schema_version').fetchone()[0]
            conn.execute("UPDATE sd_schema_version SET checksum='tampered-test-checksum'")
        try:migrate(connect_owner)
        except ValueError:pass
        else:raise CheckFailed('migration_checksum_rejection')
        with connect_owner() as conn:
            conn.execute('UPDATE sd_schema_version SET checksum=%s',(checksum,))
            conn.execute(f'REVOKE ALL ON SCHEMA public FROM PUBLIC; GRANT USAGE ON SCHEMA public TO {runtime}')
            conn.execute(f'GRANT SELECT,INSERT ON sd_case_intake TO {runtime}')
            conn.execute(f'GRANT SELECT,INSERT,UPDATE ON sd_journey TO {runtime}')
            conn.execute(f'GRANT SELECT,INSERT ON sd_audit TO {runtime}')
        report['checks'].append('fresh migrations, replay and checksum rejection')
        with connect() as conn:
            report['postgres_version']=conn.execute('SHOW server_version').fetchone()[0]
            flags=conn.execute('SELECT rolsuper,rolcreatedb,rolcreaterole,rolbypassrls FROM pg_roles WHERE rolname=current_user').fetchone()
            require(flags==(False,False,False,False),'runtime_privileges')
        for statement in ('CREATE TABLE public.unauthorized_probe (id integer)',
                          'SELECT * FROM sd_schema_version',
                          'ALTER TABLE sd_journey DISABLE ROW LEVEL SECURITY',
                          'UPDATE sd_audit SET sequence=sequence'):
            try:
                with connect() as conn:conn.execute(statement)
            except psycopg.errors.InsufficientPrivilege:pass
            else:raise CheckFailed('runtime_privilege_denial')
        report['checks'].append('runtime role cannot own/alter schema or update audit')

        staff=Actor('staff','alpha',Role.SPECIALIST);beta=Actor('staff','beta',Role.SPECIALIST)
        intake=Intake('SYN-1','requester-a','Synthetic read request','read-only','reports',True)
        repo=PostgresCaseRepository(connect);barrier=Barrier(2)
        def create_intake(_):
            barrier.wait(timeout=5);return repo.create(staff,'same-key',intake)
        with ThreadPoolExecutor(max_workers=2) as pool:rows=list(pool.map(create_intake,range(2)))
        require(sum(created for _,created in rows)==1 and rows[0][0].case_id==rows[1][0].case_id,'concurrent_intake')
        try:repo.create(staff,'same-key',Intake('SYN-2','requester-a','Changed','read-only','reports',True))
        except CaseError:pass
        else:raise CheckFailed('intake_payload_conflict')
        require(repo.get('beta',rows[0][0].case_id) is None,'intake_scope')
        report['checks'].append('two-connection intake idempotency and conflicting payload rejection')

        store=PostgresStateStore(connect);target=SimulatedTarget();service=JourneyService(store,target)
        a=service.create(staff,'Grant reports read access');b=service.create(beta,'Grant reports read access')
        for tenant,key in [('beta',a['id']),('alpha',b['id'])]:
            try:store.get(tenant,key)
            except Missing:pass
            else:raise CheckFailed('repository_tenant_scope')
        with connect() as conn:
            require(conn.execute('SELECT count(*) FROM sd_journey').fetchone()[0]==0,'no_tenant_denied')
            conn.execute("SELECT set_config('app.tenant_id','alpha',true)")
            require([str(r[0]) for r in conn.execute('SELECT case_id FROM sd_journey')]==[a['id']],'rls_without_predicate')
        try:
            with connect() as conn:
                conn.execute("SELECT set_config('app.tenant_id','alpha',true)")
                conn.execute('INSERT INTO sd_journey VALUES (%s,%s,1,%s::jsonb)',('beta',b['id'],json.dumps(b)))
        except psycopg.errors.InsufficientPrivilege:pass
        else:raise CheckFailed('rls_write_denied')
        report['checks'].append('RLS denies absent/wrong tenant reads and writes; explicit repository scope')

        before=store.get('alpha',a['id']);barrier=Barrier(2)
        def cas(index):
            state=deepcopy(before);state['revision']+=1
            state['audit'].append({'sequence':2,'actor':'staff','event':'race_'+str(index),'at':datetime.now(timezone.utc).isoformat()})
            barrier.wait(timeout=5)
            try:store.save('alpha',a['id'],1,state);return True
            except Conflict:return False
        with ThreadPoolExecutor(max_workers=2) as pool:winners=list(pool.map(cas,range(2)))
        require(sum(winners)==1,'concurrent_cas')
        with connect() as conn:
            conn.execute("SELECT set_config('app.tenant_id','alpha',true)")
            require(conn.execute('SELECT count(*) FROM sd_audit WHERE case_id=%s',(a['id'],)).fetchone()[0]==2,'cas_audit_atomic')
        report['checks'].append('two-connection CAS permits one winner and one matching audit event')

        with connect_owner() as conn:
            conn.execute("ALTER TABLE sd_audit ADD CONSTRAINT sdcheck_failure CHECK (event->>'event' <> 'force_failure')")
        before=store.get('alpha',a['id']);changed=deepcopy(before);changed['revision']+=1
        changed['audit'].append({'sequence':changed['revision'],'actor':'staff','event':'force_failure'})
        try:store.save('alpha',a['id'],before['revision'],changed)
        except psycopg.errors.CheckViolation:pass
        else:raise CheckFailed('audit_failure_not_injected')
        require(store.get('alpha',a['id'])==before,'audit_rollback')
        report['checks'].append('audit insert failure rolls back aggregate update')
        with connect_owner() as conn:conn.execute('ALTER TABLE sd_audit DROP CONSTRAINT sdcheck_failure')

        service.prepare(staff,a['id'],1);service.approve(Actor('lead','alpha',Role.SUPERVISOR),a['id'],1)
        dispatched=service.execute(staff,a['id'],1);target.complete('alpha',dispatched['action']['id'])
        require(service.close(staff,a['id'])['status']=='closed','persisted_journey_close')
        require(service.execute(staff,a['id'],1)['action']['id']==dispatched['action']['id'] and target.request_count()==1,'dispatch_replay')
        # A new interpreter reads the committed state using a new TCP connection.
        # Target remains synthetic in the parent; this is not worker-crash recovery.
        child_code="""import json,sys,psycopg
from service_desk.postgres import PostgresStateStore
try:
 config,key=json.load(sys.stdin)
 state=PostgresStateStore(lambda:psycopg.connect(**config)).get('alpha',key)
 print(json.dumps({'status':state['status'],'action_id':state['action']['id']}))
except Exception:sys.exit(1)
"""
        child=subprocess.run([sys.executable,'-B','-c',child_code],cwd=ROOT/'backend',
                             input=json.dumps([runtime_config,a['id']]),text=True,capture_output=True,timeout=15)
        require(child.returncode==0,'fresh_process_read')
        require(json.loads(child.stdout)=={'status':'closed','action_id':dispatched['action']['id']},'fresh_process_persistence')
        report['checks'].append('SQL-backed approve/dispatch/verify/close/replay and fresh-process persistence')
        report['connected_checks']=check_connected(runtime_config)
        report['status']='passed'
    except Exception as exc:
        report['status']='failed'
        report['failure']=str(exc) if type(exc) in (CheckFailed,ConnectedCheckFailed) else type(exc).__name__
    finally:
        cleanup=True
        if created_database:
            cleanup=admin_sql(f'DROP DATABASE {database} WITH (FORCE);',database='postgres').returncode==0
        for role in reversed(created_roles):
            cleanup=(admin_sql(f'DROP ROLE {role};',database='postgres').returncode==0) and cleanup
        report['temporary_database_and_roles_removed']=cleanup
        if not cleanup:report['status']='failed';report['cleanup_failure']='generated sdcheck resources need review'
    report['limitations']=['No database/container restart or backup restore',
        'Abrupt worker recovery tested with durable synthetic target; independent frozen evaluator pending',
        'Tenant context comes from trusted service; runtime role is not safe for arbitrary user SQL',
        'Connected tests use a separate SQLite synthetic target; no live entitlement/service action',
        'n8n comparison, persistent operator deployment and live Jira/model integration remain pending']
    output=ROOT/'docs/phase-5/postgres-contract-check.json'
    output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2))
    return 0 if report['status']=='passed' else 1


if __name__=='__main__':
    try:sys.exit(run())
    except Exception:
        print('PostgreSQL check could not start; install pinned requirements and verify the project DB is running.')
        sys.exit(1)
