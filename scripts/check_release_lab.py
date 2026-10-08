"""Bounded release rehearsal: isolated PostgreSQL DB + durable synthetic effects.
No Jira/model calls, .env reads, container stops, or live target mutations.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timedelta,timezone
import json,math,os,queue,re,secrets,subprocess,sys,sysconfig,threading,time
from pathlib import Path
from urllib.request import Request,build_opener
from urllib.error import HTTPError
from operator_lab import CONFIG,ROOT,save
from check_database import sql as admin_sql
from service_desk.jira import NoRedirect
from service_desk.contracts import Actor,Role
from service_desk.journeys import JourneyService
from service_desk.postgres import PostgresStateStore
from service_desk.durable_target import DurableSyntheticTarget
from service_desk.recovery import RecoveryController
from service_desk.migrations import migrate
from service_desk.store import Conflict

STAFF=Actor('release-fixture-staff','alpha',Role.SPECIALIST)
LEAD=Actor('release-fixture-approver','alpha',Role.SUPERVISOR)


def crash_child():
    import psycopg
    c=json.loads(sys.stdin.readline())
    class CrashAfterEffect(DurableSyntheticTarget):
        def submit(self,*args):
            super().submit(*args)
            os._exit(73)  # Abrupt process exit, before application receives receipt.
    JourneyService(PostgresStateStore(lambda:psycopg.connect(**c['database'])),
                   CrashAfterEffect(c['target_path'])).execute(STAFF,c['case_id'],1)
    return 1


def require(ok,label):
    if not ok:raise RuntimeError(label)


def main():
    import psycopg
    c=json.loads(CONFIG.read_text())
    name='sdrelease_'+secrets.token_hex(6)
    require(bool(re.fullmatch(r'sdrelease_[0-9a-f]{12}',name)),'isolated_name')
    owner={**c['migration_database'],'dbname':name}
    db={**c['database'],'dbname':name}
    folder=ROOT/'local/phase7'/name;folder.mkdir(parents=True)
    path=folder/'target.sqlite'
    report={'status':'failed','checked_at_utc':datetime.now(timezone.utc).isoformat(),
            'scope':'isolated real PostgreSQL + HTTP API + durable synthetic target; not live target throughput',
            'approval':'fixture supervisor, not a human approval','checks':[],
            'live_target_calls':0,'jira_calls':0,'host_reboot_tested':False}
    created=False;process=None
    env={**os.environ,'PYTHONPATH':os.pathsep.join([str(ROOT/'backend'),sysconfig.get_paths()['purelib']])}
    exe=sys._base_executable if os.name=='nt' else sys.executable
    flags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0
    tokens={r:secrets.token_hex(32) for r in ('specialist','supervisor','beta')}
    bindings={tokens[r]:{'actor_id':'release-'+r,'tenant_id':'beta' if r=='beta' else 'alpha',
                        'role':'specialist' if r=='beta' else r,
                        'expires_at':(datetime.now(timezone.utc)+timedelta(hours=1)).isoformat()} for r in tokens}
    runtime={'database':db,'target_path':str(path),'mode':'synthetic','port':0,'bindings':bindings}
    def start():
        p=subprocess.Popen([exe,'-B','-m','service_desk.runtime_api'],cwd=ROOT,env=env,
                stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True,creationflags=flags)
        p.stdin.write(json.dumps(runtime)+'\n');p.stdin.flush();p.stdin.close()
        result=queue.Queue()
        threading.Thread(target=lambda:result.put(p.stdout.readline()),daemon=True).start()
        try:
            line=json.loads(result.get(timeout=15));require(line['status']=='ready','runtime_ready')
            return p,line['origin']
        except Exception:
            p.kill();p.wait(timeout=5);raise RuntimeError('runtime_start_failed') from None
    def stop(p):
        if p is not None and p.poll() is None:p.kill();p.wait(timeout=5)
    def http(route,args=None,role='specialist',headers=None):
        req=Request(origin+route,data=json.dumps(args).encode() if args is not None else None,
            headers={'Content-Type':'application/json','Authorization':'Bearer '+tokens[role],**(headers or {})})
        try:
            with build_opener(NoRedirect()).open(req,timeout=15) as response:return response.status,json.load(response)
        except HTTPError as e:return e.code,json.loads(e.read())
    def tool(command,args):
        status,body=http('/v1/tools/'+command,args)
        require(status==200,'http_'+command)
        return body['result']
    def service():return JourneyService(PostgresStateStore(lambda:psycopg.connect(**db)),DurableSyntheticTarget(path))
    def prepared():
        s=service();state=s.create(STAFF,'Grant reports read access')
        s.prepare(STAFF,state['id'],1);s.approve(LEAD,state['id'],1)
        return state['id']
    def sql(text):require(admin_sql(text,database='postgres').returncode==0,'database_admin_operation')
    try:
        require(bool(re.fullmatch(r'[a-z_][a-z0-9_]*',owner['user'])) and
                bool(re.fullmatch(r'[a-z_][a-z0-9_]*',db['user'])),'role_names')
        sql(f"CREATE DATABASE {name} OWNER {owner['user']}");created=True
        sql(f"REVOKE ALL ON DATABASE {name} FROM PUBLIC; GRANT CONNECT ON DATABASE {name} TO {db['user']}")
        migrate(lambda:psycopg.connect(**owner))
        with psycopg.connect(**owner) as conn:
            conn.execute(f"GRANT USAGE ON SCHEMA public TO {db['user']}")
            conn.execute(f"GRANT SELECT,INSERT ON sd_case_intake,sd_audit TO {db['user']}")
            conn.execute(f"GRANT SELECT,INSERT,UPDATE ON sd_journey TO {db['user']}")
        target=DurableSyntheticTarget(path)
        process,origin=start()
        case=tool('create',{'text':'Grant reports read access'})['case_id']
        args={'case_id':case,'expected_version':1}
        proposal=tool('prepare',args)['proposal']
        require(http('/v1/tools/execute',args)[0]==409,'unapproved_execution_denied')
        approval={**args,'payload_hash':proposal['payload_hash']}
        require(http('/v1/approvals',approval)[0]==403,'staff_approval_denied')
        require(http('/v1/tools/context',{'case_id':case},role='beta')[0]==404,'cross_tenant_denied')
        require(http('/v1/tools/context',{'case_id':case},headers={'Origin':'https://untrusted.invalid'})[0]==403,'origin_denied')
        require(http('/v1/tools/create',{'text':'reports read access','approved':True})[0]!=200,'argument_authority_denied')
        require(not target.ledger(),'denied_calls_zero_effects')
        report['checks'].append('HTTP authorization, tenant, origin and argument injection denied with zero effects')
        # Expiry is evaluated against the domain clock; no need to sleep fifteen minutes.
        key=prepared();s=service();s.clock=lambda:datetime.now(timezone.utc)+timedelta(hours=1)
        try:s.execute(STAFF,key,1);raise RuntimeError('expired_approval_accepted')
        except Exception as e:
            from service_desk.lifecycle import LifecycleBlocked
            require(isinstance(e,LifecycleBlocked),'expired_approval_denied')
        require(not target.ledger(),'expired_zero_effects')
        report['checks'].append('expired approval blocked before dispatch')
        # An abrupt worker exit leaves a durable reservation and exactly one target effect.
        key=prepared()
        child=subprocess.run([exe,'-B',str(Path(__file__).resolve()),'--crash-child'],cwd=ROOT,env=env,
            input=json.dumps({**runtime,'case_id':key})+'\n',text=True,capture_output=True,timeout=20,creationflags=flags)
        require(child.returncode==73,'worker_crashed_after_effect')
        before=service().read(STAFF,key);require(before['action']['status']=='requested','durable_reservation')
        stop(process);process,origin=start()  # Fresh API process, same persistent stores.
        tool('verify',{'case_id':key});closed=tool('close',{'case_id':key})
        tool('execute',{'case_id':key,'expected_version':1})
        require(closed['status']=='closed' and len(target.ledger())==1,'crash_recovered_once')
        require(closed['action']['id']==before['action']['id'],'same_operation_after_restart')
        report['checks'].append('worker crash after effect + API cold start: same operation verified/closed, one effect')
        # Concurrent dispatchers share CAS reservation before any external submission.
        key=prepared()
        def dispatch(_):
            try:return service().execute(STAFF,key,1)['action']['id']
            except Conflict:return 'conflict'
        with ThreadPoolExecutor(max_workers=4) as pool:receipts=list(pool.map(dispatch,range(8)))
        op=service().read(STAFF,key)['action']['id']
        require(set(receipts)<={op,'conflict'} and len(target.ledger())==2,'concurrent_dispatch_once')
        service().close(STAFF,key)
        report['checks'].append('eight concurrent/replayed dispatch requests produce one operation/effect')
        # Lost database claim: stale dispatcher remains fenced by persisted action reservation.
        key=prepared();entered=threading.Event();release=threading.Event()
        claim=psycopg.connect(**db)
        identity=json.dumps(['service-desk-recovery','alpha',key],separators=(',',':'))
        claim.execute('SELECT pg_advisory_xact_lock(hashtextextended(%s,0))',(identity,))
        pid=claim.info.backend_pid
        class PausedTarget(DurableSyntheticTarget):
            def submit(self,*args):
                entered.set();require(release.wait(15),'dispatch_pause_timeout')
                return super().submit(*args)
        with ThreadPoolExecutor(max_workers=1) as pool:
            job=pool.submit(JourneyService(PostgresStateStore(lambda:psycopg.connect(**db)),PausedTarget(path)).execute,STAFF,key,1)
            try:
                require(entered.wait(10),'dispatch_reserved_before_claim_loss')
                sql(f"SELECT pg_terminate_backend({pid}) WHERE EXISTS (SELECT 1 FROM pg_stat_activity WHERE pid={pid} AND datname='{name}')")
                outcome=RecoveryController(service()).tick(STAFF,key)
                require(not outcome['done'] and len(target.ledger())==2,'new_worker_did_not_resubmit')
            finally:release.set()
            job.result(timeout=15)
        claim.close()
        future=lambda:datetime.now(timezone.utc)+timedelta(seconds=3)
        resumed=RecoveryController(service(),clock=future).tick(STAFF,key)
        require(resumed['reason']=='closed' and len(target.ledger())==3,'claim_loss_single_effect')
        report['checks'].append('database claim session terminated during paused dispatch: competing worker never resubmits')
        # Database outage applies only to the temporary DB. No Docker restart.
        sql(f"ALTER DATABASE {name} ALLOW_CONNECTIONS false")
        sql(f"SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='{name}'")
        code,body=http('/readyz');require(code==503 and body=={'error':'backend_unavailable'},'outage_readiness_sanitized')
        require(http('/v1/tools/create',{'text':'reports read access'})[0]==503,'outage_write_denied')
        sql(f"ALTER DATABASE {name} ALLOW_CONNECTIONS true")
        require(http('/readyz')[0]==200,'database_reconnected')
        require(len(target.ledger())==3,'outage_no_extra_effects')
        report['checks'].append('isolated database outage: readiness/write 503, sanitized error, restored connection')
        # Bounded local workload. Each case has explicit synthetic fixture approval.
        def journey(_):
            start_at=time.perf_counter()
            case=tool('create',{'text':'Grant reports read access'})['case_id']
            args={'case_id':case,'expected_version':1}
            p=tool('prepare',args)['proposal']
            require(http('/v1/approvals',{**args,'payload_hash':p['payload_hash']},role='supervisor')[0]==200,'fixture_approval')
            began=time.perf_counter();tool('execute',args);ack=(time.perf_counter()-began)*1000
            end=tool('close',{'case_id':case});require(end['status']=='closed','workload_closed')
            return {'case_id':case,'ack_ms':ack,'end_to_end_ms':(time.perf_counter()-start_at)*1000}
        def stats(rows):
            result={'completed':len(rows),'errors':0}
            for label in ('ack_ms','end_to_end_ms'):
                values=sorted(r[label] for r in rows)
                result[label]={'p50':round(values[math.ceil(len(values)*.5)-1],3),
                               'p95':round(values[math.ceil(len(values)*.95)-1],3)}
            return result
        normal=[journey(i) for i in range(8)]
        with ThreadPoolExecutor(max_workers=4) as pool:peak=list(pool.map(journey,range(16)))
        print('Normal and bounded peak workload complete; starting 60-second low-rate soak.',flush=True)
        soak=[];began=time.monotonic()
        while time.monotonic()-began<60:
            soak.append(journey(len(soak)));time.sleep(2)
        rows=normal+peak+soak
        require(len(target.ledger())==3+len(rows),'workload_exact_effect_count')
        with psycopg.connect(**db) as conn:
            conn.execute("SELECT set_config('app.tenant_id','alpha',true)")
            count=conn.execute("SELECT count(*) FROM sd_journey j WHERE j.revision != (SELECT count(*) FROM sd_audit a WHERE a.tenant_id=j.tenant_id AND a.case_id=j.case_id)").fetchone()[0]
            require(count==0,'audit_atomicity')
        report['workload']={'normal':stats(normal),'peak_concurrency_4':stats(peak),'soak':stats(soak),
                            'soak_wall_seconds':round(time.monotonic()-began,2),
                            'hardware_context':'shared host, existing 512MiB/0.5CPU PostgreSQL container',
                            'interpretation':'closed-loop synthetic HTTP journeys, not Jira/Keycloak or AI latency; 60s is a smoke soak, not endurance qualification'}
        require(all(group['end_to_end_ms']['p95']<10000 for group in (report['workload']['normal'],report['workload']['peak_concurrency_4'],report['workload']['soak'])),'local_10s_latency_budget')
        report['checks'].append('bounded normal/peak/60s smoke soak: all cases closed, exact effect count and atomic audit')
        report['synthetic_effects']=len(target.ledger());report['status']='passed'
    except Exception as exc:
        report['error_type']=type(exc).__name__
        report['failure']=str(exc) if type(exc) is RuntimeError and re.fullmatch('[a-z0-9_]+',str(exc)) else 'details_withheld'
    finally:
        stop(process)
        cleanup=not created or admin_sql(f'DROP DATABASE {name} WITH (FORCE)',database='postgres').returncode==0
        report['temporary_database_removed']=cleanup
        if not cleanup:report['status']='failed'
        save(ROOT/'docs/phase-7/release-lab.json',report)
    print(json.dumps(report,indent=2));return report['status']!='passed'


if __name__=='__main__':
    try:sys.exit(crash_child() if sys.argv[1:]==['--crash-child'] else main())
    except Exception as exc:print('Release check stopped: '+type(exc).__name__);sys.exit(1)
