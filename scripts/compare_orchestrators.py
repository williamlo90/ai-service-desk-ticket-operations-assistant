"""Sequential, disposable code/n8n experiment; no .env or existing workflow edits."""
from datetime import datetime,timezone
from hashlib import sha256
import json
from pathlib import Path
from queue import Queue,Empty
import secrets
import subprocess
import sys
from threading import Thread
from time import monotonic
from uuid import uuid4

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
from check_database import sql as admin_sql
from service_desk.migrations import migrate
from comparison.plans import segments
from comparison.evaluate import evaluate

N8N='docker.n8n.io/n8nio/n8n@sha256:f6dc0d15bc9620baf5ba1df834ef81ae4e969f778c09300e567217be88f04a96'
IMAGE='service-desk-comparison:local'


class ComparisonFailed(Exception):pass


def command(args,data=None,timeout=60):
    result=subprocess.run(args,input=data,text=True,capture_output=True,timeout=timeout)
    if result.returncode:raise ComparisonFailed('command_failed:'+args[0]+':'+next((x for x in args if x in ('import:workflow','execute','build','run','exec','cp')), 'operation'))
    return result.stdout


def workflow(steps,origin,capability):
    nodes=[{'id':'start','name':'Start','type':'n8n-nodes-base.manualTrigger','typeVersion':1,'position':[0,0],'parameters':{}}]
    connections={};previous='Start'
    for index,step in enumerate(steps):
        name=f'{index+1:03d} {step["fixture"]} {step["command"]}'
        nodes.append({'id':str(uuid4()),'name':name,'type':'n8n-nodes-base.httpRequest','typeVersion':4.2,'position':[(index+1)*240,0],
            'parameters':{'method':'POST','url':origin+'/step','sendHeaders':True,
                'headerParameters':{'parameters':[{'name':'Authorization','value':'Bearer '+capability}]},
                'sendBody':True,'specifyBody':'json','jsonBody':json.dumps(step),
                'options':{'timeout':15000}},'retryOnFail':False})
        connections[previous]={'main':[[{'node':name,'type':'main','index':0}]]};previous=name
    return {'id':'sdReference'+secrets.token_hex(5),'name':'Service Desk isolated reference sequence',
            'nodes':nodes,'connections':connections,'settings':{'executionOrder':'v1'},'active':False}


def run_candidate(name,inputs,run_dir,profile='v1',native=False,recovery=False,timer=False,transport=False):
    import psycopg
    suffix=secrets.token_hex(5);db='sdcompare_'+suffix;owner=db+'_owner';runtime=db+'_app'
    owner_pw=secrets.token_hex(32);app_pw=secrets.token_hex(32);capability=secrets.token_hex(32)
    api='sdcompare-'+suffix+'-api';engine='sdcompare-'+suffix+'-n8n'
    roles=[];containers=[];database_created=False;api_process=None
    report={'candidate':name,'profile':profile,'status':'failed','worker_restarted_at_checkpoint':False}
    def sql(statement):
        result=admin_sql(statement,database='postgres')
        if result.returncode:raise ComparisonFailed('database_setup')
    def api_request(path,payload):
        code="import json,sys;from urllib.request import Request,urlopen;c=json.load(sys.stdin);r=urlopen(Request('http://127.0.0.1:8080/'+c['path'],data=json.dumps(c['data']).encode(),headers={'Authorization':'Bearer '+c['capability'],'Content-Type':'application/json'}),timeout=15);print(r.read().decode())"
        return json.loads(command(['docker','exec','-i',api,'python','-c',code],json.dumps({'path':path,'data':payload,'capability':capability})))
    try:
        for role,password in ((owner,owner_pw),(runtime,app_pw)):
            sql(f"CREATE ROLE {role} LOGIN PASSWORD '{password}' NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS;");roles.append(role)
        sql(f'CREATE DATABASE {db} OWNER {owner};');database_created=True
        sql(f'REVOKE ALL ON DATABASE {db} FROM PUBLIC; GRANT CONNECT ON DATABASE {db} TO {runtime};')
        connect=lambda:psycopg.connect(host='127.0.0.1',port=5433,dbname=db,user=owner,password=owner_pw)
        migrate(connect)
        with connect() as conn:
            conn.execute(f'REVOKE ALL ON SCHEMA public FROM PUBLIC; GRANT USAGE ON SCHEMA public TO {runtime}')
            conn.execute(f'GRANT SELECT,INSERT,UPDATE ON sd_journey TO {runtime}')
            conn.execute(f'GRANT SELECT,INSERT ON sd_audit TO {runtime}')
        command(['docker','run','-d','--name',api,'--network','service-desk-lab_service_desk','--memory','256m','--cpus','0.5','--pids-limit','64','--entrypoint','sleep',IMAGE,'infinity']);containers.append(api)
        config={'database':{'host':'service-desk-lab-db-1','port':5432,'dbname':db,'user':runtime,'password':app_pw,'connect_timeout':5,
                           'options':'-c statement_timeout=5000 -c lock_timeout=3000'},'capability':capability,'profile':profile}
        api_process=subprocess.Popen(['docker','exec','-i',api,'python','-m','comparison.server'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        api_process.stdin.write(json.dumps(config)+'\n');api_process.stdin.flush()
        queue=Queue();Thread(target=lambda:queue.put(api_process.stdout.readline()),daemon=True).start()
        try:ready=queue.get(timeout=20)
        except Empty:raise ComparisonFailed('fixture_api_start_timeout') from None
        if ready.strip()!='comparison-ready':raise ComparisonFailed('fixture_api_not_ready')
        if name=='n8n':
            command(['docker','run','-d','--name',engine,'--network','service-desk-lab_service_desk','--memory','1280m' if transport else '768m','--cpus','1','--pids-limit','192' if transport else '128',
                '-e','N8N_DIAGNOSTICS_ENABLED=false','-e','N8N_VERSION_NOTIFICATIONS_ENABLED=false','-e','N8N_ENFORCE_SETTINGS_FILE_PERMISSIONS=true',
                '-e','NODE_OPTIONS=--max-old-space-size=512','-e','WEBHOOK_URL=http://'+engine+':5678/',
                '-e','N8N_HOST='+engine,'--entrypoint','sleep',N8N,'infinity']);containers.append(engine)
        elif native or timer:
            command(['docker','run','-d','--name',engine,'--network','service-desk-lab_service_desk','--memory','128m','--cpus','0.5',
                     '--pids-limit','64','--entrypoint','sleep',IMAGE,'infinity']);containers.append(engine)
        if transport:
            from transport_checks import check_transport
            report['transport']=check_transport(name,api,engine,capability,command,api_request,run_dir,config['database'])
            report['status']='executed'
            return report
        if timer:
            from timer_checks import check_timer
            report['timer']=check_timer(name,api,engine,capability,command,api_request,run_dir)
            report['status']='executed'
            return report
        if recovery:
            from recovery_checks import check_recovery
            report['recovery']=check_recovery(name,api,engine,capability,command,api_request,run_dir)
            report['status']='executed'
            return report
        if native:
            from native_wait_checks import check_native
            report['native_wait']=check_native(name,api,engine,capability,command,api_request,run_dir)
            trace=api_request('observations',{})
            tracefile=run_dir/(name+'-native-trace.json');tracefile.write_text(json.dumps(trace,indent=2)+'\n',encoding='utf-8')
            report.update(status='executed',trace_sha256=sha256(tracefile.read_bytes()).hexdigest())
            return report
        timings=[]
        for index,steps in enumerate(segments(inputs,profile)):
            started=monotonic()
            if name=='code':
                command(['docker','exec','-i',api,'python','-m','comparison.code_worker'],json.dumps({'origin':'http://127.0.0.1:8080','steps':steps,'capability':capability}),timeout=120)
            else:
                wf=workflow(steps,'http://'+api+':8080',capability)
                # Ephemeral capability travels by stdin into isolated container only.
                command(['docker','exec','-i',engine,'node','-e',"let s='';process.stdin.on('data',x=>s+=x);process.stdin.on('end',()=>require('fs').writeFileSync('/tmp/reference.json',s,{mode:0o600}));"],json.dumps(wf))
                command(['docker','exec',engine,'n8n','import:workflow','--input=/tmp/reference.json'],timeout=120)
                command(['docker','exec',engine,'n8n','execute','--id='+wf['id'],'--rawOutput'],timeout=180)
                clean=workflow(steps,'http://FIXTURE_API:8080','SYNTHETIC_CAPABILITY_INJECTED_AT_RUN')
                (run_dir/f'n8n-{profile}-segment-{index+1}.json').write_text(json.dumps(clean,indent=2)+'\n',encoding='utf-8')
            timings.append(round((monotonic()-started)*1000,3))
            if index==0:
                if name=='n8n':command(['docker','restart',engine])
                # Code worker already exited; next segment is a new interpreter.
                report['worker_restarted_at_checkpoint']=True
        trace=api_request('observations',{})
        tracefile=run_dir/(name+'-'+profile+'-trace.json');tracefile.write_text(json.dumps(trace,indent=2)+'\n',encoding='utf-8')
        report.update(status='executed',segment_wall_ms=timings,trace_sha256=sha256(tracefile.read_bytes()).hexdigest(),observations=trace)
    except Exception as exc:
        report['error']=str(exc) if type(exc).__name__ in ('ComparisonFailed','NativeWaitFailed') else type(exc).__name__
    finally:
        cleanup=True
        for container in reversed(containers):
            cleanup=(subprocess.run(['docker','rm','-f',container],capture_output=True,timeout=30).returncode==0) and cleanup
        if api_process:
            try:api_process.communicate(timeout=10)
            except subprocess.TimeoutExpired:api_process.kill();api_process.communicate(timeout=5)
        if database_created:cleanup=(admin_sql(f'DROP DATABASE {db} WITH (FORCE);',database='postgres').returncode==0) and cleanup
        for role in reversed(roles):cleanup=(admin_sql(f'DROP ROLE {role};',database='postgres').returncode==0) and cleanup
        report['cleanup_passed']=cleanup
    return report


def main():
    fixture_path=ROOT/'docs/phase-0/reference-fixtures.json';contract=ROOT/'docs/architecture/comparison-contract.md'
    source=json.loads(fixture_path.read_text(encoding='utf-8'))
    change_path=ROOT/'docs/phase-5/policy-v2-fixtures.json'
    change=json.loads(change_path.read_text(encoding='utf-8'))
    # Explicitly strip all expected outcomes before constructing candidate inputs.
    inputs=[{k:v for k,v in item.items() if k!='expected'} for item in source['cases']]
    run_id=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+secrets.token_hex(3)
    run_dir=ROOT/'local/comparison'/run_id;run_dir.mkdir(parents=True)
    result={'run_id':run_id,'contract_sha256':sha256(contract.read_bytes()).hexdigest(),
            'fixture_sha256':sha256(fixture_path.read_bytes()).hexdigest(),'candidate_results':[],
            'policy_change_fixture_sha256':sha256(change_path.read_bytes()).hexdigest(),
            'n8n_image':N8N,'model_calls':0,'project_dotenv_read':False,'winner':None,
            'gate':'bounded functional reference experiment, not full architecture acceptance'}
    result['source_base_commit']=command(['git','rev-parse','HEAD']).strip()
    result['source_hash_basis']='UTF-8 text normalized LF; includes uncommitted Phase 5 source'
    paths=sorted([*Path(ROOT/'backend/comparison').glob('*.py'),*Path(ROOT/'backend/service_desk').glob('*.py'),Path(__file__)])
    result['source_sha256']={str(p.relative_to(ROOT)).replace('\\','/'):sha256(p.read_bytes().replace(b'\r\n',b'\n')).hexdigest() for p in paths}
    result['python_image']=command(['docker','image','inspect',IMAGE,'--format','{{.Id}}']).strip()
    for profile,candidate in [('v1','code'),('v1','n8n'),('v2','code'),('v2','n8n')]:
        print('Running isolated '+candidate+' '+profile+' candidate.',flush=True)
        candidate_inputs=inputs if profile=='v1' else inputs+[{k:v for k,v in item.items() if k!='expected'} for item in change['additional_cases']]
        report=run_candidate(candidate,candidate_inputs,run_dir,profile)
        trace=report.pop('observations',{})
        # Expected outcomes enter only this evaluator after the candidate has exited.
        expected=json.loads(fixture_path.read_text(encoding='utf-8'))['cases']
        if profile=='v2':expected+=json.loads(change_path.read_text(encoding='utf-8'))['additional_cases']
        report['cases']=[evaluate(f,trace.get(f['id'],[]),report['worker_restarted_at_checkpoint'],profile) for f in expected]
        report['passed']=sum(row['passed'] for row in report['cases']);report['total']=len(expected)
        result['candidate_results'].append(report)
        print(candidate+' '+profile+': '+str(report['passed'])+'/'+str(len(expected))+' functional cases; cleanup='+str(report['cleanup_passed']),flush=True)
    result['limitations']=['Linear reference sequences; not autonomous wait/retry schedulers',
        'Worker restart at explicit persisted boundary, not native n8n Wait-node resume',
        'Shared domain runtime is newly implemented; full baseline billing/refund regression comparison pending',
        'Policy-change correctness tested; active editing effort is unmeasured. Native scheduling/recovery and isolated performance measurements pending',
        'Existing n8n instance/workflows and other projects unchanged; no architecture winner selected']
    result['raw_trace_location']=str(run_dir.relative_to(ROOT)).replace('\\','/')
    out=ROOT/'docs/phase-5/orchestrator-comparison.json';out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    return 0 if all(x['passed']==x['total'] and x['cleanup_passed'] for x in result['candidate_results']) else 1


if __name__=='__main__':sys.exit(main())
