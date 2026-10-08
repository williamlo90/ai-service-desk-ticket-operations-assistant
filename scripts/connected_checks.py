"""Connected checks called inside the disposable PostgreSQL harness."""
from datetime import datetime,timedelta,timezone
import json
import os
from pathlib import Path
from queue import Queue,Empty
import secrets
import subprocess
import sys
import tempfile
from threading import Thread
from urllib.request import Request,urlopen
from urllib.error import HTTPError

ROOT=Path(__file__).resolve().parents[1]


class ConnectedCheckFailed(Exception):pass


def check_connected(database):
    import psycopg
    from service_desk.contracts import Actor,Role
    from service_desk.durable_target import DurableSyntheticTarget
    from service_desk.journeys import JourneyService,JourneyBlocked
    from service_desk.postgres import PostgresStateStore
    def require(ok,label):
        if not ok:raise ConnectedCheckFailed(label)
    tokens={role:secrets.token_hex(32) for role in ('staff','supervisor','auditor','beta','expired')}
    expiry=(datetime.now(timezone.utc)+timedelta(hours=1)).isoformat()
    bindings={tokens[name]:{'actor_id':name,'tenant_id':'beta' if name=='beta' else 'alpha',
        'role':'supervisor' if name=='supervisor' else 'auditor' if name=='auditor' else 'specialist',
        'expires_at':'2020-01-01T00:00:00+00:00' if name=='expired' else expiry} for name in tokens}
    fd,filename=tempfile.mkstemp(prefix='sd-target-connected-',suffix='.sqlite');os.close(fd)
    config={'mode':'synthetic','port':0,'database':database,'bindings':bindings,'target_path':filename}
    process=None;checks=[]
    def stop():
        nonlocal process
        if process is not None:
            if process.poll() is None:process.terminate()
            try:process.wait(timeout=5)
            except subprocess.TimeoutExpired:process.kill();process.wait(timeout=5)
            process.stdout.close();process=None
    def start():
        nonlocal process
        process=subprocess.Popen([sys.executable,'-B','-m','service_desk.runtime_api'],cwd=ROOT/'backend',
                                 stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True)
        process.stdin.write(json.dumps(config)+'\n');process.stdin.close()
        queue=Queue();Thread(target=lambda:queue.put(process.stdout.readline()),daemon=True).start()
        try:line=queue.get(timeout=15)
        except Empty:raise ConnectedCheckFailed('api_start_timeout') from None
        ready=json.loads(line);require(ready['status']=='ready','api_start')
        return ready['origin']
    def request(origin,path,args=None,identity='staff',headers=None):
        request=Request(origin+path,data=None if args is None else json.dumps(args).encode(),
                        headers={'Authorization':'Bearer '+tokens[identity],'Content-Type':'application/json',**(headers or {})})
        try:
            with urlopen(request,timeout=6) as response:
                return response.status,response.read(60001),dict(response.headers)
        except HTTPError as error:
            with error:return error.code,error.read(60001),dict(error.headers)
    def mcp(origin,stage,case=None):
        result=subprocess.run(['node',str(ROOT/'mcp-server/test/connected.mjs')],
            input=json.dumps({'origin':origin,'staff':tokens['staff'],'supervisor':tokens['supervisor'],
                              'stage':stage,**(case or {})}),text=True,capture_output=True,timeout=30)
        require(result.returncode==0,'connected_mcp_'+stage)
        require(all(token not in result.stdout+result.stderr for token in tokens.values()),'mcp_secret_safety')
        return json.loads(result.stdout)
    try:
        origin=start()
        require(request(origin,'/readyz')[0]==200,'api_ready')
        status,page,headers=request(origin,'/')
        require(status==200 and b'Approve this proposal' in page and 'Content-Security-Policy' in headers,'approval_page')
        search={'query':'','offset':0,'limit':20}
        require(request(origin,'/v1/tools/search',search,'expired')[0]==401,'identity_expiry')
        require(request(origin,'/v1/tools/create',{'text':'reports read access'},'auditor')[0]==403,'auditor_write')
        require(request(origin,'/v1/tools/search',search,headers={'Origin':'https://untrusted.invalid'})[0]==403,'origin_denied')
        status,body,headers=request(origin,'/v1/tools/search',search)
        require(status==200 and 'X-Correlation-ID' in headers,'correlation_header')
        checks.append('real HTTP readiness, identity expiry, auditor denial, Origin guard and correlation ID')
        case=mcp(origin,'create')
        require(request(origin,'/v1/tools/context',{'case_id':case['case_id']},'beta')[0]==404,'tenant_denied')
        target=DurableSyntheticTarget(filename)
        require(len(target.ledger())==1,'one_mcp_effect')
        checks.append('MCP to HTTP to PostgreSQL with separate supervisor approval and target read-back closure')
        stop();origin=start();mcp(origin,'resume',case)
        require(len(target.ledger())==1,'restart_no_duplicate')
        checks.append('API process termination/restart and fresh MCP process preserve state and replay operation ID')
        target.revoke('alpha',case['operation_id']);mcp(origin,'reopen',case)
        require(len(target.ledger())==1,'reopen_no_duplicate')
        checks.append('persisted adverse target evidence reopens through MCP without repeating effect')
        stop()
        service=JourneyService(PostgresStateStore(lambda:psycopg.connect(**database)),target)
        staff=Actor('staff','alpha',Role.SPECIALIST);lead=Actor('supervisor','alpha',Role.SUPERVISOR)
        crash_code="""import json,os,sys,psycopg
from service_desk.contracts import Actor,Role
from service_desk.durable_target import DurableSyntheticTarget
from service_desk.journeys import JourneyService
from service_desk.postgres import PostgresStateStore
try:
 c=json.load(sys.stdin)
 class CrashTarget(DurableSyntheticTarget):
  def submit(self,*args):
   if c['after_effect']:super().submit(*args)
   os._exit(23)
 s=JourneyService(PostgresStateStore(lambda:psycopg.connect(**c['db'])),CrashTarget(c['path']))
 s.execute(Actor('staff','alpha',Role.SPECIALIST),c['case_id'],1)
except Exception:sys.exit(1)
"""
        for after_effect in (True,False):
            created=service.create(staff,'Grant reports read access');key=created['id']
            service.prepare(staff,key,1);service.approve(lead,key,1)
            before=len(target.ledger())
            child=subprocess.run([sys.executable,'-B','-c',crash_code],cwd=ROOT/'backend',
                input=json.dumps({'db':database,'path':filename,'case_id':key,'after_effect':after_effect}),
                text=True,capture_output=True,timeout=15)
            require(child.returncode==23,'worker_crash_checkpoint')
            require(service.read(staff,key)['action']['status']=='requested','reserved_before_crash')
            recovered=service.verify(staff,key)
            if after_effect:
                require(recovered['verified']['matches'],'crash_effect_readback')
                require(service.close(staff,key)['status']=='closed','crash_effect_close')
                service.execute(staff,key,1)
                require(len(target.ledger())==before+1,'crash_effect_once')
            else:
                require(recovered['action']['status']=='unknown','crash_before_effect_unknown')
                try:service.execute(staff,key,1)
                except JourneyBlocked as exc:require(str(exc)=='reconciliation_required','crash_review_required')
                else:raise ConnectedCheckFailed('unexpected_redispatch')
                require(len(target.ledger())==before,'crash_before_effect_zero')
        checks.append('abrupt worker exits after reservation and after committed target effect reconcile without duplicate effects')
        return checks
    finally:
        stop()
        # Remove only this run's individual temporary target files, never directories.
        for suffix in ('','-journal','-wal','-shm'):
            Path(filename+suffix).unlink(missing_ok=True)
