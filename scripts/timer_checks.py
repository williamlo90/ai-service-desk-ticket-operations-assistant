"""One real 70-second timer checkpoint, abrupt kill, automatic due-time recovery."""
import json,subprocess
from datetime import datetime,timezone
from time import monotonic,sleep
from hashlib import sha256
from recovery_checks import workflow
from native_wait_checks import NativeWaitFailed


def check_timer(name,api,engine,capability,command,api_request,run_dir):
    children=[];fixture='timer-crash'
    def require(ok,label):
        if not ok:raise NativeWaitFailed('timer_'+label)
    def until(probe,label,seconds=100):
        end=monotonic()+seconds
        while monotonic()<end:
            result=probe()
            if result:return result
            sleep(0.4)
        raise NativeWaitFailed('timer_'+label)
    def state():return api_request('native',{'fixture':fixture})
    def step(action,**data):
        r=api_request('step',{'fixture':fixture,'command':action,**data})
        require(not r['denial'],action)
    def http(path,method='GET'):
        source="""import json,sys
from urllib.request import Request,urlopen
from urllib.error import HTTPError,URLError
c=json.load(sys.stdin)
try:
 with urlopen(Request(c['url'],data=b'{}' if c['method']=='POST' else None,method=c['method']),timeout=8) as r:print(r.status)
except HTTPError as e:print(e.code)
except (URLError,TimeoutError):print(0)
"""
        return int(command(['docker','exec','-i',api,'python','-c',source],json.dumps({'url':'http://'+engine+':5678'+path,'method':method})))
    def start():
        if name=='code':
            p=subprocess.Popen(['docker','exec','-i',engine,'python','-m','comparison.recovery_worker'],stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,text=True)
            p.stdin.write(json.dumps({'origin':'http://'+api+':8080','capability':capability,'fixture':fixture})+'\n');p.stdin.close()
        else:
            p=subprocess.Popen(['docker','exec',engine,'sh','-c','exec n8n start > /tmp/timer-start.log 2>&1'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        children.append(p)
        if name=='n8n':until(lambda:http('/healthz/readiness')==200,'readiness',60)
    def execution():
        js="const S=require(require.resolve('sqlite3',{paths:['/usr/local/lib/node_modules/n8n']}));const d=new S.Database('/home/node/.n8n/database.sqlite',S.OPEN_READONLY);d.all('SELECT id,status,waitTill FROM execution_entity WHERE workflowId=? ORDER BY id DESC',[process.argv[1]],(e,r)=>{if(e)process.exitCode=1;else console.log(JSON.stringify(r));d.close()})"
        return json.loads(command(['docker','exec',engine,'node','-e',js,wf['id']]))
    try:
        step('initialize',input='Grant reports read access');step('prepare');step('approve')
        if name=='n8n':
            wf=workflow(fixture,'http://'+api+':8080',capability)
            wf['nodes'][0].update(type='n8n-nodes-base.webhook',typeVersion=2,webhookId=wf['id'],
                parameters={'httpMethod':'POST','path':'timer-crash','responseMode':'onReceived','options':{}})
            command(['docker','exec','-i',engine,'node','-e',"let s='';process.stdin.on('data',x=>s+=x);process.stdin.on('end',()=>require('fs').writeFileSync('/tmp/timer.json',s,{mode:0o600}));"],json.dumps(wf))
            command(['docker','exec',engine,'n8n','import:workflow','--input=/tmp/timer.json'],timeout=120)
            command(['docker','exec',engine,'n8n','publish:workflow','--id='+wf['id']],timeout=60)
        start()
        if name=='n8n':
            status=http('/webhook/timer-crash','POST')
            for _ in range(15):
                if status!=404:break
                sleep(0.5);status=http('/webhook/timer-crash','POST')
            require(status==200,'trigger_http_'+str(status))
        first=until(lambda:(s:=state())['state'].get('recovery',{}).get('attempts')==1 and s,'first_attempt')
        if name=='n8n':
            original=until(lambda:(rows:=execution()) and rows[0]['status']=='waiting' and rows,'persisted_wait')
            require(len(original)==1 and original[0]['waitTill'],'persisted_timer')
        due=first['state']['recovery']['next_at'];operation=first['state']['action']['id']
        require(datetime.now(timezone.utc)<datetime.fromisoformat(due),'crash_before_due')
        command(['docker','kill',engine]);command(['docker','start',engine])
        # External result arrives during engine downtime; no resume webhook is sent.
        step('complete');start()
        early=state()
        require(early['state']['action']['id']==operation,'operation_preserved')
        require(early['submit_calls']==1,'dispatch_preserved')
        early_checked=datetime.now(timezone.utc)<datetime.fromisoformat(due)
        if early_checked:require(early['state']['recovery']['attempts']==1,'no_early_retry')
        finished=until(lambda:(s:=state())['state'].get('recovery',{}).get('done') and s,'automatic_resume',100)
        r=finished['state']['recovery']
        require(r['reason']=='closed' and r['attempts']==2,'budget_preserved')
        require(finished['effects']==1 and finished['submit_calls']==1,'single_effect_and_dispatch')
        if name=='n8n':
            final=until(lambda:(rows:=execution()) and rows[0]['status']=='success' and rows,'execution_success')
            require(len(final)==1 and final[0]['id']==original[0]['id'],'same_execution')
        step('checkpoint')
        path=run_dir/(name+'-timer-trace.json')
        path.write_text(json.dumps(api_request('observations',{}),indent=2)+'\n',encoding='utf-8')
        return {'status':'passed','delay_seconds':70,'abrupt_restarts':1,'attempts':2,
            'submit_calls':1,'effects':1,'no_early_retry_observed':early_checked,
            'same_execution_id':True if name=='n8n' else None,
            'resume_webhook_calls':0,'trace_sha256':sha256(path.read_bytes()).hexdigest()}
    finally:
        subprocess.run(['docker','kill',engine],capture_output=True,timeout=15)
        for p in children:
            try:p.wait(timeout=5)
            except subprocess.TimeoutExpired:p.kill();p.wait(timeout=5)
