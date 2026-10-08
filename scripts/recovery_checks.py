"""Independent environment/evaluator for bounded native timer-loop scenarios."""
import json,subprocess
from time import monotonic,sleep
from uuid import uuid4
from hashlib import sha256
from native_wait_checks import NativeWaitFailed


CASES=('expired','revoked','delayed','failed','lost_response','read_timeout','exhausted')


def workflow(fixture,origin,capability):
    nodes=[
        {'name':'Start','type':'manualTrigger','typeVersion':1,'parameters':{}},
        {'name':'Reconcile','type':'httpRequest','typeVersion':4.2,'parameters':{
            'method':'POST','url':origin+'/recovery','sendHeaders':True,
            'headerParameters':{'parameters':[{'name':'Authorization','value':'Bearer '+capability}]},
            'sendBody':True,'specifyBody':'json','jsonBody':json.dumps({'fixture':fixture}),
            'options':{'timeout':10000}}},
        {'name':'Done','type':'if','typeVersion':2.2,'parameters':{'conditions':{
            'options':{'caseSensitive':True,'leftValue':'','typeValidation':'strict','version':2},
            'conditions':[{'id':str(uuid4()),'leftValue':'={{ $json.done }}','rightValue':'',
                           'operator':{'type':'boolean','operation':'true','singleValue':True}}],
            'combinator':'and'},'options':{}}},
        {'name':'Backoff','type':'wait','typeVersion':1.1,'parameters':{
            'resume':'timeInterval','amount':'={{ $json.retry_seconds }}','unit':'seconds'}}]
    for i,node in enumerate(nodes):
        node.update(id=str(uuid4()),position=[240*i,0],type='n8n-nodes-base.'+node['type'])
    edge=lambda n:[{'node':n,'type':'main','index':0}]
    return {'id':'sdRecovery'+uuid4().hex[:12],'name':'Recovery '+fixture,'nodes':nodes,
        'connections':{'Start':{'main':[edge('Reconcile')]},'Reconcile':{'main':[edge('Done')]},
                       'Done':{'main':[[],edge('Backoff')]},'Backoff':{'main':[edge('Reconcile')]}},
        'settings':{'executionOrder':'v1'},'active':False}


def check_recovery(name,api,engine,capability,command,api_request,run_dir):
    def require(ok,label):
        if not ok:raise NativeWaitFailed('recovery_'+label)
    def step(fixture,action,**data):
        result=api_request('step',{'fixture':fixture,'command':action,**data})
        require(not result.get('denial'),fixture+'_'+action)
    workflows={case:workflow(case,'http://'+api+':8080',capability) for case in CASES}
    if name=='n8n':
        command(['docker','exec','-i',engine,'node','-e',
            "let s='';process.stdin.on('data',x=>s+=x);process.stdin.on('end',()=>require('fs').writeFileSync('/tmp/recovery.json',s,{mode:0o600}));"],json.dumps(list(workflows.values())))
        command(['docker','exec',engine,'n8n','import:workflow','--input=/tmp/recovery.json'],timeout=120)
        (run_dir/'recovery-n8n-sanitized.json').write_text(json.dumps(
            [workflow(c,'http://FIXTURE_API:8080','INJECT_AT_RUN') for c in CASES],indent=2)+'\n')
    rows=[]
    for case in CASES:
        step(case,'initialize',input='Grant reports read access')
        step(case,'prepare');step(case,'approve')
        if case=='expired':step(case,'advance900')
        elif case=='revoked':step(case,'revoke_approval')
        elif case=='lost_response':step(case,'lost_response')
        elif case in ('failed','read_timeout'):
            step(case,'execute');step(case,'fail' if case=='failed' else 'complete')
            if case=='read_timeout':step(case,'read_timeouts',count=2)
        if name=='code':
            args=['docker','exec','-i',api,'python','-m','comparison.recovery_worker']
        else:args=['docker','exec',engine,'n8n','execute','--id='+workflows[case]['id'],'--rawOutput']
        p=subprocess.Popen(args,stdin=subprocess.PIPE if name=='code' else subprocess.DEVNULL,
                           stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,text=True)
        try:
            if name=='code':
                p.stdin.write(json.dumps({'origin':'http://127.0.0.1:8080','capability':capability,'fixture':case})+'\n');p.stdin.close()
            deadline=monotonic()+90;completed=False
            while monotonic()<deadline:
                snapshot=api_request('native',{'fixture':case});r=snapshot['state'].get('recovery',{})
                if case=='delayed' and r.get('attempts',0)>=2 and not completed:
                    step(case,'complete');completed=True
                if r.get('done'):break
                if p.poll() is not None:raise NativeWaitFailed('recovery_worker_early_exit_'+case)
                sleep(0.15)
            require(r.get('done'),case+'_deadline')
            require(p.wait(timeout=40)==0,case+'_worker_exit')
        finally:
            if p.poll() is None:
                # Stop this candidate container's exec process via owning cleanup on failure.
                p.kill();p.wait(timeout=5)
        state=snapshot['state']
        expected_reason={'expired':'approval_rejected','revoked':'approval_rejected',
            'failed':'target_failed','exhausted':'retry_exhausted'}.get(case,'closed')
        require(r['reason']==expected_reason,case+'_reason')
        success=expected_reason=='closed'
        require((state['status']=='closed')==success,case+'_closure')
        require(snapshot['effects']==int(success),case+'_effects')
        require(snapshot['submit_calls']==(0 if case in ('expired','revoked') else 1),case+'_dispatch_count')
        if not success:require(state['escalation']['reason']==expected_reason,case+'_review_queue')
        if case in ('expired','revoked'):require(r['attempts']==0,case+'_no_read_attempt')
        if case=='exhausted':require(r['attempts']==4,case+'_bounded')
        if case=='read_timeout':require(r['attempts']==3,case+'_retries')
        # Repeated/late callback hints cannot close an unresolved case or redispatch.
        if state['action']:
            if case=='exhausted':step(case,'complete')
            for hint in ('callback2','callback2','callback1'):step(case,hint)
            after=api_request('native',{'fixture':case})
            require(after['submit_calls']==1,case+'_callback_dispatch')
            require(after['state']['status']==state['status'],case+'_callback_closure')
            require(after['state']['recovery']==r,case+'_callback_budget')
            require(after['effects']==int(success or case=='exhausted'),case+'_callback_effects')
            if case=='exhausted':require(after['state']['escalation']['reason']=='retry_exhausted',case+'_late_review_retained')
        # Calling a completed controller again cannot reset the attempt budget.
        require(api_request('recovery',{'fixture':case})['attempts']==r['attempts'],case+'_terminal_budget')
        step(case,'checkpoint')
        rows.append({'case':case,'passed':True,'reason':r['reason'],'attempts':r['attempts'],
                     'effects_at_decision':snapshot['effects'],'submit_calls':snapshot['submit_calls']})
        print(name+' recovery '+case+': passed',flush=True)
    path=run_dir/(name+'-recovery-trace.json')
    path.write_text(json.dumps(api_request('observations',{}),indent=2)+'\n',encoding='utf-8')
    return {'status':'passed','cases':rows,'trace_sha256':sha256(path.read_bytes()).hexdigest()}
