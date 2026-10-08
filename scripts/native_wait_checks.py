"""Engine-native wait tests; all resources provided by isolated comparison harness."""
import json
import subprocess
from time import monotonic,sleep
from urllib.parse import urlsplit,urlunsplit
from uuid import uuid4


class NativeWaitFailed(Exception):pass


def native_workflow(origin,capability):
    nodes=[];connections={};previous=None
    def add(name,kind,parameters,version=1):
        nonlocal previous
        node={'id':str(uuid4()),'name':name,'type':'n8n-nodes-base.'+kind,'typeVersion':version,
              'position':[len(nodes)*240,0],'parameters':parameters}
        if kind in ('wait','webhook'):node['webhookId']=str(uuid4())
        nodes.append(node)
        if previous:connections[previous]={'main':[[{'node':name,'type':'main','index':0}]]}
        previous=name
    def http(name,path,payload):
        add(name,'httpRequest',{'method':'POST','url':origin+path,'sendHeaders':True,
            'headerParameters':{'parameters':[{'name':'Authorization','value':'Bearer '+capability}]},
            'sendBody':True,'specifyBody':'json','jsonBody':payload,'options':{'timeout':10000}},4.2)
    add('Intake','webhook',{'httpMethod':'POST','path':'native-wait-check','responseMode':'onReceived','options':{}},2)
    for command in ('prepare','wait_approval','execute','wait_target','verify','close'):
        if command.startswith('wait_'):
            stage=command.removeprefix('wait_')
            # Insert suffix before any n8n-generated signature query string.
            payload="={{ {command:'register',stage:'"+stage+"',resume_url:$execution.resumeUrl.replace(/(\\?|$)/, '/"+stage+"$1')} }}"
            http('Register '+stage,'/native',payload)
            add('Wait '+stage,'wait',{'resume':'webhook','httpMethod':'POST','responseMode':'onReceived',
                                    'options':{'webhookSuffix':stage}},1.1)
        else:http(command.title(),'/step',json.dumps({'fixture':'native-wait','command':command}))
    return {'id':'sdNativeWait'+uuid4().hex[:10],'name':'Native wait restart comparison','nodes':nodes,
            'connections':connections,'active':False,'settings':{'executionOrder':'v1'}}


def check_native(name,api,engine,capability,command,api_request,run_dir):
    children=[];checks=[];last_http={}
    def require(ok,label):
        if not ok:raise NativeWaitFailed(label)
    def until(probe,label,seconds=35):
        deadline=monotonic()+seconds
        while monotonic()<deadline:
            result=probe()
            if result:return result
            sleep(0.5)
        raise NativeWaitFailed(label)
    def external_http(url,method='POST'):
        # All URLs must stay in this run's isolated engine. Never print resume URLs.
        require(urlsplit(url).hostname==engine,'callback_destination')
        code="""import json,sys
from urllib.request import Request,urlopen
from urllib.error import HTTPError,URLError
c=json.load(sys.stdin)
try:
 with urlopen(Request(c['url'],data=b'{}' if c['method']=='POST' else None,method=c['method'],headers={'Content-Type':'application/json'}),timeout=8) as r: print(json.dumps({'status':r.status}))
except HTTPError as e:
 text=e.read(6000).decode(errors='replace').lower()
 print(json.dumps({'status':e.code,'hints':[k for k in ['invalid token','matching path','running already','finished','does not exist'] if k in text]}))
except (URLError,TimeoutError):print(json.dumps({'status':0}))
"""
        result=json.loads(command(['docker','exec','-i',api,'python','-c',code],json.dumps({'url':url,'method':method})))
        last_http.clear();last_http.update(result)
        return result['status']
    def start_process(args,config=None):
        p=subprocess.Popen(args,stdin=subprocess.PIPE if config else subprocess.DEVNULL,
                           stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,text=True)
        if config:p.stdin.write(json.dumps(config)+'\n');p.stdin.close()
        children.append(p);return p
    def code_status():
        code="import sqlite3,json;print(json.dumps(sqlite3.connect('/tmp/native-worker.sqlite').execute('SELECT stage,ticks FROM job WHERE id=1').fetchone()))"
        try:return json.loads(command(['docker','exec',engine,'python','-c',code]))
        except Exception:return None
    def start_code():
        return start_process(['docker','exec','-i',engine,'python','-m','comparison.wait_worker'],
                             {'origin':'http://'+api+':8080','capability':capability})
    def n8n_status():
        js="""const sqlite=require(require.resolve('sqlite3',{paths:['/usr/local/lib/node_modules/n8n']}));
const db=new sqlite.Database('/home/node/.n8n/database.sqlite',sqlite.OPEN_READONLY);
db.all('SELECT id,status,waitTill FROM execution_entity WHERE workflowId=? ORDER BY id DESC LIMIT 1',[process.argv[1]],(e,rows)=>{if(e)process.exitCode=1;else console.log(JSON.stringify(rows));db.close();});"""
        try:
            rows=json.loads(command(['docker','exec',engine,'node','-e',js,wf['id']]))
            return rows[0] if rows else None
        except Exception:return None
    def start_n8n():
        start_process(['docker','exec',engine,'sh','-c','exec n8n start > /tmp/native-start.log 2>&1'])
        # A listening socket precedes route registration. Require full readiness.
        until(lambda:external_http('http://'+engine+':5678/healthz/readiness','GET')==200,'n8n_http_start',60)
    def wait_stage(stage):
        if name=='code':return until(lambda:(s:=code_status()) and s[0]=='waiting_'+stage and s,'code_wait_'+stage)
        return until(lambda:(s:=n8n_status()) and s['status']=='waiting' and stage in api_request('native',{})['resume'] and s,'n8n_wait_'+stage)
    def restart():
        command(['docker','kill',engine]);command(['docker','start',engine])
        if name=='code':start_code()
        else:start_n8n()
    api_request('step',{'fixture':'native-wait','command':'initialize','input':'Grant reports read access'})
    try:
        if name=='code':start_code()
        else:
            wf=native_workflow('http://'+api+':8080',capability)
            command(['docker','exec','-i',engine,'node','-e',"let s='';process.stdin.on('data',x=>s+=x);process.stdin.on('end',()=>require('fs').writeFileSync('/tmp/native.json',s,{mode:0o600}));"],json.dumps(wf))
            command(['docker','exec',engine,'n8n','import:workflow','--input=/tmp/native.json'],timeout=120)
            command(['docker','exec',engine,'n8n','publish:workflow','--id='+wf['id']],timeout=60)
            state_js="const S=require(require.resolve('sqlite3',{paths:['/usr/local/lib/node_modules/n8n']}));const db=new S.Database('/home/node/.n8n/database.sqlite');db.get('SELECT active,versionId,activeVersionId FROM workflow_entity WHERE id=?',[process.argv[1]],(e,r)=>{if(e)process.exitCode=1;else console.log(JSON.stringify({exists:!!r,active:r?.active,hasVersion:!!r?.versionId,hasPublishedVersion:!!r?.activeVersionId}));db.close()})"
            published=json.loads(command(['docker','exec',engine,'node','-e',state_js,wf['id']]))
            require(published.get('hasPublishedVersion'), 'n8n_publish_state_'+json.dumps(published))
            start_n8n()
            trigger_status=external_http('http://'+engine+':5678/webhook/native-wait-check')
            for _ in range(15):
                if trigger_status!=404:break
                sleep(0.5)
                trigger_status=external_http('http://'+engine+':5678/webhook/native-wait-check')
            if trigger_status!=200:
                diagnostics=command(['docker','exec',engine,'node','-e',"const s=require('fs').readFileSync('/tmp/native-start.log','utf8');console.log(JSON.stringify(Object.fromEntries(['Activated workflow','Starting active workflows','Error','Unrecognized node type','owner','credential'].map(k=>[k,s.includes(k)]))));"])
                raise NativeWaitFailed('n8n_trigger_http_'+str(trigger_status)+' '+diagnostics.strip()+' '+json.dumps(published))
            (run_dir/'native-n8n-sanitized.json').write_text(json.dumps(native_workflow('http://FIXTURE_API:8080','INJECT_AT_RUN'),indent=2)+'\n',encoding='utf-8')
        first=wait_stage('approval');before=api_request('native',{})
        require(before['state']['action'] is None and before['effects']==0,'no_action_before_approval')
        restart();after=wait_stage('approval')
        if name=='n8n':require(first['id']==after['id'],'same_execution_after_approval_restart')
        checks.append('persisted approval wait survives abrupt engine kill/start without dispatch')
        api_request('step',{'fixture':'native-wait','command':'approve'})
        if name=='n8n':
            approval_url=api_request('native',{})['resume']['approval']
            # A missing signature must not resume an execution on this pinned release.
            parsed=urlsplit(approval_url);unsigned=urlunsplit((parsed.scheme,parsed.netloc,parsed.path,'',''))
            denied=external_http(unsigned)
            require(denied in (401,403,404),'unsigned_resume_denied')
            response=external_http(approval_url)
            require(response==200,'approval_resume_'+json.dumps(last_http))
        target_wait=wait_stage('target');waiting=api_request('native',{})
        require(waiting['state']['action']['status']=='accepted' and waiting['effects']==0,'receipt_is_not_outcome')
        operation=waiting['state']['action']['id']
        restart();resumed=wait_stage('target')
        if name=='n8n':require(target_wait['id']==resumed['id'],'same_execution_after_target_restart')
        require(api_request('native',{})['state']['action']['id']==operation,'operation_preserved')
        checks.append('persisted target wait survives second abrupt engine kill/start with same operation ID')
        api_request('step',{'fixture':'native-wait','command':'complete'})
        if name=='n8n':
            target_url=api_request('native',{})['resume']['target']
            # Old-stage signed callbacks must not release the next-stage wait.
            require(external_http(approval_url) in (400,401,403,404,409),'old_stage_callback_denied')
            require(external_http(target_url)==200,'target_resume')
        finished=until(lambda:(s:=api_request('native',{}))['state']['status']=='closed' and s,'automatic_close')
        require(finished['effects']==1 and finished['state']['verified']['matches'],'one_verified_effect')
        if name=='n8n':
            status=until(lambda:(s:=n8n_status()) and s['status']=='success' and s,'n8n_success')
            require(status['id']==first['id'],'single_native_execution')
            require(external_http(target_url) in (400,401,403,404,409),'duplicate_resume_denied')
        else:until(lambda:(s:=code_status()) and s[0]=='closed','code_closed_checkpoint')
        api_request('step',{'fixture':'native-wait','command':'complete'})
        require(api_request('native',{})['effects']==1,'duplicate_event_no_effect')
        checks.append('external target event resumes verification/closure automatically; duplicate event does not repeat effect')
        return {'status':'passed','checks':checks,'abrupt_restarts':2,'target_effects':1,
                'native_execution_same_id':True if name=='n8n' else None,'unsigned_callback_denied':True if name=='n8n' else None}
    finally:
        # Stop only this run's engine; owning runner removes its container afterwards.
        subprocess.run(['docker','kill',engine],capture_output=True,timeout=15)
        for p in children:
            try:p.wait(timeout=5)
            except subprocess.TimeoutExpired:p.kill();p.wait(timeout=5)
