"""Real HTTP faults and independent worker coordination; fixture-only execution."""
from hashlib import sha256
import json,subprocess
from time import sleep,monotonic
from recovery_checks import workflow
from native_wait_checks import NativeWaitFailed


def check_transport(name,api,engine,capability,command,api_request,run_dir,database):
    cases={'unavailable':['503','503'],'rate_limit':['429'],'lost_reply':['drop_after'],
           'exhausted':['503']*4,'unauthorized':['401']*4,'two_workers':[],'lock_owner_crash':[]}
    workflows={case:workflow(case,'http://'+api+':8080',capability) for case in cases}
    for case,wf in workflows.items():
        wf['nodes'][1].update(retryOnFail=True,maxTries=4,waitBetweenTries=1000)
        wf['nodes'][1]['parameters']['jsonBody']="={{ {fixture:'"+case+"',worker_id:$execution.id} }}"
    if name=='n8n':
        command(['docker','exec','-i',engine,'node','-e',"let s='';process.stdin.on('data',x=>s+=x);process.stdin.on('end',()=>require('fs').writeFileSync('/tmp/transport.json',s,{mode:0o600}));"],json.dumps(list(workflows.values())))
        command(['docker','exec',engine,'n8n','import:workflow','--input=/tmp/transport.json'],timeout=120)
    def require(ok,label):
        if not ok:raise NativeWaitFailed('transport_'+label)
    def step(case,action,**data):
        r=api_request('step',{'fixture':case,'command':action,**data})
        require(not r['denial'],case+'_'+action)
    launch_count=0
    def launch(case):
        nonlocal launch_count
        launch_count+=1
        if name=='code':
            p=subprocess.Popen(['docker','exec','-i',api,'python','-m','comparison.recovery_worker'],
                stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,text=True)
            p.stdin.write(json.dumps({'origin':'http://127.0.0.1:8080','capability':capability,'fixture':case})+'\n');p.stdin.close()
        else:
            p=subprocess.Popen(['docker','exec','-e','N8N_RUNNERS_BROKER_PORT='+str(6000+launch_count),engine,'n8n','execute','--id='+workflows[case]['id'],'--rawOutput'],
                stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        return p
    rows=[]
    for case,plan in cases.items():
        step(case,'initialize',input='Grant reports read access');step(case,'prepare');step(case,'approve')
        api_request('faults',{'fixture':case,'plan':plan,'hold_read':case=='two_workers'})
        children=[];holder=None
        try:
            if case in ('two_workers','lock_owner_crash'):
                # Separate process/DB session holds the exact coordination lock.
                state=api_request('native',{'fixture':case})['state']
                holder_code="""import json,sys,time,os
import psycopg
from service_desk.postgres import PostgresStateStore
c=json.load(sys.stdin)
with PostgresStateStore(lambda:psycopg.connect(**c['database'])).claim('alpha',c['case_id']) as held:
 print(json.dumps({'held':held,'pid':os.getpid()}),flush=True)
 time.sleep(90)
"""
                holder=subprocess.Popen(['docker','exec','-i',api,'python','-c',holder_code],stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True)
                holder.stdin.write(json.dumps({'database':database,'case_id':state['id']})+'\n');holder.stdin.close()
                info=json.loads(holder.stdout.readline());require(info['held'],'holder_acquired')
            children=[launch(case)]
            if case=='two_workers':children.append(launch(case))
            if holder:
                end=monotonic()+50
                while monotonic()<end:
                    s=api_request('native',{'fixture':case})
                    if s['busy_returns']>=len(children) and len(s['worker_ids'])>=len(children):break
                    sleep(0.3)
                require(s['busy_returns']>=len(children),case+'_busy_observed')
                require(len(s['worker_ids'])>=len(children),case+'_distinct_workers')
                require(s['submit_calls']==0 and s['state']['action'] is None,case+'_no_dispatch_while_locked')
                command(['docker','exec',api,'python','-c','import os,signal,sys;os.kill(int(sys.argv[1]),signal.SIGKILL)',str(info['pid'])]);holder.wait(timeout=10)
            codes=[p.wait(timeout=90) for p in children]
            snapshot=api_request('native',{'fixture':case});state=snapshot['state']
            denied=case in ('exhausted','unauthorized')
            if denied:
                require(all(c!=0 for c in codes),case+'_worker_must_fail')
                require(state['status']=='open' and state['action'] is None and snapshot['submit_calls']==0,case+'_no_mutation')
                expected=1 if name=='code' and case=='unauthorized' else 4
                require(snapshot['http_calls']==expected,case+'_retry_bound')
                if name=='code':
                    src="import sqlite3,json,sys;print(json.dumps(sqlite3.connect('/tmp/recovery-transport-review.sqlite').execute('SELECT reason FROM review WHERE fixture=?',(sys.argv[1],)).fetchone()))"
                    require(json.loads(command(['docker','exec',api,'python','-c',src,case])) is not None,case+'_durable_review')
                else:
                    js="const S=require(require.resolve('sqlite3',{paths:['/usr/local/lib/node_modules/n8n']}));const d=new S.Database('/home/node/.n8n/database.sqlite');d.all('SELECT status FROM execution_entity WHERE workflowId=?',[process.argv[1]],(e,r)=>{console.log(JSON.stringify(r));d.close()})"
                    statuses=json.loads(command(['docker','exec',engine,'node','-e',js,workflows[case]['id']]))
                    require(any(x['status']=='error' for x in statuses),case+'_durable_error_execution')
            else:
                require(all(c==0 for c in codes),case+'_exit')
                require(state['status']=='closed' and state['recovery']['attempts']==1,case+'_closed_once')
                require(snapshot['submit_calls']==snapshot['effects']==1,case+'_one_effect')
                if case in ('unavailable','rate_limit','lost_reply'):
                    require(snapshot['http_calls']==len(plan)+1,case+'_redelivery_count')
            step(case,'checkpoint')
            rows.append({'case':case,'passed':True,'http_calls':snapshot['http_calls'],
                'submit_calls':snapshot['submit_calls'],'effects':snapshot['effects'],
                'busy_returns':snapshot['busy_returns'],'workers':len(snapshot['worker_ids']),'status':state['status']})
            print(name+' transport '+case+': passed',flush=True)
        finally:
            if holder and holder.poll() is None:
                command(['docker','exec',api,'python','-c','import os,signal,sys;os.kill(int(sys.argv[1]),signal.SIGKILL)',str(info['pid'])]);holder.wait(timeout=10)
            for p in children:
                if p.poll() is None:p.kill();p.wait(timeout=5)
    path=run_dir/(name+'-transport-trace.json')
    path.write_text(json.dumps(api_request('observations',{}),indent=2)+'\n',encoding='utf-8')
    return {'status':'passed','cases':rows,'trace_sha256':sha256(path.read_bytes()).hexdigest()}
