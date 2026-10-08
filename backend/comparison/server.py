"""Isolated fixture controller/shared domain API. Receives no expected labels.

Fixture authority (clock/target/approval) is explicitly separate from actor calls.
Never run this API on a public network or attach real platform credentials.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timedelta,timezone
from hashlib import sha256
from hmac import compare_digest,new as hmac_new
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import json
import sys
from threading import Barrier,local
from time import monotonic,sleep
import psycopg
from service_desk.contracts import Actor,Role,AccessDenied
from service_desk.events import CallbackVerifier,CallbackHandler
from service_desk.journeys import JourneyService,JourneyBlocked
from service_desk.lifecycle import LifecycleBlocked
from service_desk.postgres import PostgresStateStore
from service_desk.store import Missing,Conflict
from service_desk.policy import POLICIES,Policy
from .target import ReferenceTarget
from service_desk.recovery import RecoveryController


class Harness:
    def __init__(self,config):
        self.config=config;self.contexts={};self.observations={};self.http_faults={};self.http_calls={}
        self.connect=lambda:psycopg.connect(**config['database'])
        self.store=PostgresStateStore(self.connect)
        self.target=ReferenceTarget('/tmp/reference-target.sqlite')
        self.staff=Actor('specialist','alpha',Role.SPECIALIST)
        self.lead=Actor('supervisor','alpha',Role.SUPERVISOR)
        self.beta=Actor('specialist','beta',Role.SPECIALIST)
        self.auditor=Actor('auditor','alpha',Role.AUDITOR)
        self.callback_secret=b'synthetic-callback-fixture-key-0001'
        if config.get('profile')=='v2':POLICIES['access_request']=Policy('access-v2','grant_read_access',300)

    def service(self,ctx):return JourneyService(self.store,self.target,lambda:ctx['clock'])

    def native(self,data):
        ctx=self.contexts[data.get('fixture','native-wait')]
        if data.get('command')=='register':
            if data['stage'] not in ('approval','target'):raise ValueError()
            ctx.setdefault('resume',{})[data['stage']]=data['resume_url']
            return {'registered':data['stage']}
        state=self.store.get(ctx['tenant'],ctx['id']);action=state['action']
        return {'state':state,'resume':ctx.get('resume',{}),
            'http_calls':self.http_calls.get(data.get('fixture','native-wait'),0),
            'busy_returns':ctx.get('busy_returns',0),
            'worker_ids':sorted(ctx.get('worker_ids',set())),
            'submit_calls':self.target.submit_calls(ctx['tenant'],action['id']) if action else 0,
            'target':self.target.inspect(ctx['tenant'],action['id'],state['proposal']['payload']) if action else None,
            'effects':len([x for x in self.target.ledger() if action and x['operation_id']==action['id']])}

    def recovery(self,data):
        ctx=self.contexts[data['fixture']];target=self.target
        if data.get('worker_id'):ctx.setdefault('worker_ids',set()).add(str(data['worker_id']))
        class FaultTarget:
            def submit(inner,*args):
                result=target.submit(*args)
                if ctx.get('complete_on_submit'):target.complete(args[0],args[1],True)
                return result
            def inspect(inner,*args):
                if ctx.get('hold_read'):sleep(0.6)
                if ctx.get('read_timeouts',0)>0:
                    ctx['read_timeouts']-=1
                    raise TimeoutError('Synthetic target read timeout')
                return target.inspect(*args)
        service=JourneyService(self.store,FaultTarget(),lambda:ctx['clock'])
        result=RecoveryController(service,delay_scale=70 if self.config.get('profile')=='timer' else 1).tick(self.staff,ctx['id'])
        if result.get('reason')=='worker_busy':ctx['busy_returns']=ctx.get('busy_returns',0)+1
        return result

    def faults(self,data):
        key=data['fixture'];plan=data.get('plan',[])
        if not isinstance(plan,list) or len(plan)>10 or any(x not in ('503','429','401','drop_after') for x in plan):raise ValueError()
        self.http_faults[key]=list(plan)
        self.contexts[key]['complete_on_submit']=bool(data.get('complete_on_submit',True))
        self.contexts[key]['hold_read']=bool(data.get('hold_read',False))
        return {'configured':True}

    def step(self,data):
        key,command=data['fixture'],data['command'];started=monotonic();error=None;results=None
        if command=='initialize':
            ctx={'clock':datetime(2026,10,8,tzinfo=timezone.utc),'tenant':'beta' if key=='wrong-tenant' else 'alpha'}
            self.contexts[key]=ctx;service=self.service(ctx)
            state=service.create(self.beta if ctx['tenant']=='beta' else self.staff,data['input'])
            ctx['id']=state['id'];self.observations[key]=[]
        else:
            ctx=self.contexts[key];service=self.service(ctx);case_id=ctx['id']
            before=self.store.get(ctx['tenant'],case_id)
            try:
                if command in ('policy_v1','policy_v2'):
                    POLICIES['access_request']=Policy('access-'+command[-2:],'grant_read_access',900 if command=='policy_v1' else 300)
                elif command=='prepare':results=service.prepare(self.staff,case_id,before['version'])
                elif command=='approve':results=service.approve(self.lead,case_id,before['version'])
                elif command=='revoke_approval':results=service.revoke_approval(self.lead,case_id,before['version'])
                elif command=='read_timeouts':ctx['read_timeouts']=int(data['count'])
                elif command in ('execute','lost_response','auditor_execute'):
                    self.target.timeout_after_effect=command=='lost_response'
                    results=service.execute(self.auditor if command=='auditor_execute' else self.staff,case_id,before['version'])
                    self.target.timeout_after_effect=False
                elif command in ('verify','close','reopen'):results=getattr(service,command)(self.staff,case_id)
                elif command=='revise':results=service.revise(self.staff,case_id,'Grant reports read access with revised context',before['version'])
                elif command in ('complete','fail'):self.target.complete(ctx['tenant'],before['action']['id'],command=='complete')
                elif command=='revoke':
                    self.target.revoke(ctx['tenant'],before['action']['id']);ctx['clock']+=timedelta(seconds=1)
                elif command.startswith('advance'):ctx['clock']+=timedelta(seconds=int(command.removeprefix('advance')))
                elif command=='foreign_read':results=service.read(self.staff,case_id)
                elif command=='foreign_prepare':results=service.prepare(self.staff,case_id,1)
                elif command=='foreign_execute':results=service.execute(self.staff,case_id,1)
                elif command.startswith('callback'):
                    timestamp=str(int(ctx['clock'].timestamp()))
                    body=json.dumps({'tenant':ctx['tenant'],'case_id':case_id,'operation_id':before['action']['id'],
                        'sequence':int(command[-1]),'event_id':'fixture-'+command}).encode()
                    signature=hmac_new(self.callback_secret,timestamp.encode()+b'.'+body,sha256).hexdigest()
                    results=CallbackHandler(CallbackVerifier(ctx['tenant'],self.callback_secret),service,self.staff).handle(body,timestamp,signature,int(timestamp))
                elif command=='concurrent':
                    barrier=Barrier(2);thread_state=local();store=self.store
                    class BarrierStore:
                        def get(inner,tenant,key):
                            state=store.get(tenant,key)
                            if not getattr(thread_state,'seen',False):
                                thread_state.seen=True;barrier.wait(timeout=5)
                            return state
                        def save(inner,*args):return store.save(*args)
                    def execute(_):
                        try:
                            result=JourneyService(BarrierStore(),self.target,lambda:ctx['clock']).execute(self.staff,case_id,1)
                            return {'result':'accepted','operation':result['action']['id']}
                        except Conflict:return {'result':'conflict'}
                    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(execute,range(2)))
                elif command=='checkpoint':
                    # Durable checkpoint verified by independent connection; worker exits here.
                    results={'persisted_revision':self.store.get(ctx['tenant'],case_id)['revision']}
                else:raise ValueError('Unknown fixture command.')
            except (JourneyBlocked,LifecycleBlocked) as exc:error=str(exc)
            except (AccessDenied,Missing):error='denied'
            except Conflict:error='conflict'
        state=self.store.get(ctx['tenant'],ctx['id']);action=state['action']
        operation=action['id'] if action else None
        effects=[x for x in self.target.ledger() if x['operation_id']==operation]
        target=self.target.inspect(ctx['tenant'],operation,state['proposal']['payload']) if action else None
        with self.connect() as conn:
            conn.execute("SELECT set_config('app.tenant_id',%s,true)",(ctx['tenant'],))
            audit=[row[0] for row in conn.execute('SELECT event FROM sd_audit WHERE tenant_id=%s AND case_id=%s ORDER BY sequence',(ctx['tenant'],ctx['id']))]
        observation={'sequence':len(self.observations[key])+1,'command':command,'state':state,'audit':audit,
                     'target':target,'ledger':effects,'target_requests':self.target.requests(ctx['tenant'],operation) if action else 0,
                     'denial':error,'elapsed_ms':round((monotonic()-started)*1000,3),
                     'concurrent_results':results if command=='concurrent' else None,
                     'disclosed_foreign':int(command.startswith('foreign_') and results is not None),
                     'persisted_checkpoint':results if command=='checkpoint' else None}
        self.observations[key].append(observation)
        return {'fixture':key,'command':command,'recorded':True,'denial':error}


def main():
    config=json.loads(sys.stdin.buffer.readline(65537));harness=Harness(config)
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def do_POST(self):
            if not compare_digest(self.headers.get('Authorization',''),'Bearer '+config['capability']):
                self.send_error(403);return
            try:
                length=int(self.headers.get('Content-Length','0'))
                if not 0<length<=16384:raise ValueError()
                data=json.loads(self.rfile.read(length))
                fault=None
                if self.path=='/recovery':
                    key=data['fixture'];harness.http_calls[key]=harness.http_calls.get(key,0)+1
                    plan=harness.http_faults.get(key,[])
                    fault=plan.pop(0) if plan else None
                    if fault in ('503','429','401'):
                        self.send_response(int(fault));self.send_header('Retry-After','1')
                        self.send_header('Content-Length','0');self.end_headers();return
                if self.path=='/faults':
                    result=harness.faults(data)
                else:
                    result=harness.observations if self.path=='/observations' else harness.step(data) if self.path=='/step' else harness.native(data) if self.path=='/native' else harness.recovery(data) if self.path=='/recovery' else {'ready':True}
                if fault=='drop_after':
                    self.close_connection=True;self.connection.shutdown(2);self.connection.close();return
                body=json.dumps(result).encode();self.send_response(200)
            except Exception:
                body=b'{"error":"comparison_request_failed"}';self.send_response(500)
            self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
    server=ThreadingHTTPServer(('0.0.0.0',8080),Handler)
    print('comparison-ready',flush=True);server.serve_forever()


if __name__=='__main__':main()
