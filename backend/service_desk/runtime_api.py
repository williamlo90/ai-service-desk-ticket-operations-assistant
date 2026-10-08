"""Loopback-only local integration API. Explicit config over stdin; no .env loader."""
from datetime import datetime,timezone
from http import HTTPStatus
import json
from pathlib import Path
import re
import sys
from uuid import uuid4
from wsgiref.simple_server import make_server,WSGIRequestHandler

from .api import strict_object,reject_constant,CaseAPI
from .auth import TokenAuthenticator,AuthenticationFailed
from .bridge import Bridge,public_state
from .contracts import Actor,Role,AccessDenied
from .journeys import JourneyService,JourneyBlocked
from .lifecycle import LifecycleBlocked
from .skills import SkillRejected
from .store import Missing,Conflict

SAFE={'approval_required','version_conflict','reconciliation_required','stale_approval',
      'expired_approval','outcome_not_verified','adverse_evidence_required','case_not_closed',
      'clarification','escalate','action_already_started','relation_does_not_resolve_incident',
      'proposal_required','case_not_open','stale_policy','action_required','invalid_arguments'}


class RuntimeAuthenticator:
    """Server-side per-identity expiry; tokens never determine their own scope."""
    def __init__(self,bindings,clock=None):
        self.clock=clock or (lambda:datetime.now(timezone.utc))
        actors={};self.expiry={}
        for token,item in bindings.items():
            actor=Actor(item['actor_id'],item['tenant_id'],Role(item['role']))
            expires=datetime.fromisoformat(item['expires_at'])
            if expires.tzinfo is None or expires.utcoffset() is None:raise ValueError('Aware expiry required.')
            # Each identity must have a single binding, so expiry cannot be ambiguous.
            key=(actor.actor_id,actor.tenant_id)
            if key in self.expiry:raise ValueError('Duplicate identity.')
            self.expiry[key]=expires;actors[token]=actor
        self.auth=TokenAuthenticator(actors)

    def authenticate(self,authorization):
        actor=self.auth.authenticate(authorization)
        if self.clock()>=self.expiry[(actor.actor_id,actor.tenant_id)]:raise AuthenticationFailed()
        return actor


class RuntimeAPI:
    def __init__(self,auth,service,intake_repository,origin,ready=lambda:True,mode='synthetic',requesters=None):
        self.auth,self.service,self.origin,self.ready=auth,service,origin,ready
        if mode not in ('synthetic','lab'):raise ValueError('Unsupported runtime mode')
        self.mode=mode
        self.bridge=Bridge(auth,service,requesters)
        self.intake=CaseAPI(auth,intake_repository)

    def __call__(self,env,start_response):
        correlation=str(uuid4())
        if env.get('HTTP_HOST')!=self.origin.removeprefix('http://'):
            return self.reply(start_response,403,{'error':'origin_denied'},correlation)
        if env.get('HTTP_ORIGIN') not in (None,'',self.origin):
            return self.reply(start_response,403,{'error':'origin_denied'},correlation)
        if env.get('PATH_INFO','').startswith('/v1/cases'):
            def correlated(status,headers,exc_info=None):
                return start_response(status,[*headers,('X-Correlation-ID',correlation)],exc_info)
            return self.intake(env,correlated)
        try:
            method,path=env.get('REQUEST_METHOD'),env.get('PATH_INFO')
            assets={'/':('approval.html','text/html'),'/approval.js':('approval.js','text/javascript'),
                    '/workspace.css':('workspace.css','text/css'),'/primer.css':('vendor/primer.css','text/css')}
            if method=='GET' and path in assets:
                filename,media=assets[path]
                content=(Path(__file__).parent/'web'/filename).read_bytes()
                return self.reply(start_response,200,content,correlation,
                                  media+'; charset=utf-8')
            if method=='GET' and path=='/healthz':
                return self.reply(start_response,200,{'status':'ok','mode':self.mode},correlation)
            if method=='GET' and path=='/readyz':
                if not self.ready():raise RuntimeError()
                return self.reply(start_response,200,{'status':'ready'},correlation)
            actor=self.auth.authenticate(env.get('HTTP_AUTHORIZATION',''))
            if method!='POST':return self.reply(start_response,404,{'error':'not_found'},correlation)
            if env.get('CONTENT_TYPE','').split(';')[0]!='application/json':
                return self.reply(start_response,415,{'error':'unsupported_media_type'},correlation)
            length=env.get('CONTENT_LENGTH','')
            if not re.fullmatch(r'[0-9]{1,6}',length):
                return self.reply(start_response,411,{'error':'length_required'},correlation)
            if int(length)>16384:return self.reply(start_response,413,{'error':'input_limit'},correlation)
            raw=env['wsgi.input'].read(int(length))
            if len(raw)!=int(length):raise ValueError()
            args=json.loads(raw.decode('utf-8'),object_pairs_hook=strict_object,parse_constant=reject_constant)
            if path=='/v1/approvals':
                if actor.role!=Role.SUPERVISOR:raise AccessDenied()
                if (type(args) is not dict or set(args)!={'case_id','expected_version','payload_hash'}
                        or type(args['expected_version']) is not int or args['expected_version']<1
                        or not isinstance(args['case_id'],str) or not re.fullmatch(r'[a-f0-9-]{36}',args['case_id'])
                        or not isinstance(args['payload_hash'],str) or not re.fullmatch(r'[a-f0-9]{64}',args['payload_hash'])):
                    raise ValueError()
                state=self.service.read(actor,args['case_id'])
                if not state['proposal'] or state['proposal']['payload_hash']!=args['payload_hash']:
                    raise JourneyBlocked('stale_approval')
                result=public_state(self.service.approve(actor,args['case_id'],args['expected_version'],args['payload_hash']))
            elif path.startswith('/v1/tools/'):
                token=env['HTTP_AUTHORIZATION'].partition(' ')[2]
                result=self.bridge.call(token,path.removeprefix('/v1/tools/'),args)
            else:return self.reply(start_response,404,{'error':'not_found'},correlation)
            return self.reply(start_response,200,{'result':result},correlation)
        except AuthenticationFailed:status,code=401,'unauthorized'
        except AccessDenied:status,code=403,'forbidden'
        except Missing:status,code=404,'not_found'
        except Conflict:status,code=409,'version_conflict'
        except (JourneyBlocked,LifecycleBlocked,SkillRejected) as exc:
            status,code=409,str(exc) if str(exc) in SAFE else 'request_rejected'
        except (ValueError,TypeError,KeyError,UnicodeError,RecursionError):status,code=400,'invalid_arguments'
        except Exception:status,code=503,'backend_unavailable'
        return self.reply(start_response,status,{'error':code},correlation)

    @staticmethod
    def reply(start_response,status,body,correlation,media='application/json; charset=utf-8'):
        encoded=body if isinstance(body,bytes) else json.dumps(body,allow_nan=False).encode()
        if len(encoded)>(200000 if media=='text/css; charset=utf-8' else 60000):status,encoded=500,b'{"error":"output_limit"}'
        start_response(f'{status} {HTTPStatus(status).phrase}',[
            ('Content-Type',media),('Content-Length',str(len(encoded))),('Cache-Control','no-store'),
            ('X-Content-Type-Options','nosniff'),('X-Correlation-ID',correlation),
            ('Content-Security-Policy',"default-src 'none'; script-src 'self'; connect-src 'self'; style-src 'self' 'unsafe-inline'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'")])
        return [encoded]


class QuietHandler(WSGIRequestHandler):
    def setup(self):
        super().setup();self.connection.settimeout(10)
    def log_message(self,*args):pass


def main():
    try:
        raw=sys.stdin.buffer.readline(65537)
        if len(raw)>65536:raise ValueError()
        config=json.loads(raw,object_pairs_hook=strict_object,parse_constant=reject_constant)
        if config['mode'] not in ('synthetic','lab'):raise ValueError()
        import psycopg
        from .postgres import PostgresStateStore,PostgresCaseRepository
        from .durable_target import DurableSyntheticTarget
        db=config['database']
        if db['host']!='127.0.0.1' or db['port']!=5433:raise ValueError()
        connect=lambda:psycopg.connect(**db)
        auth=RuntimeAuthenticator(config['bindings'])
        requesters=None
        if config['mode']=='lab':
            from .lab_targets import LabTargets
            target=LabTargets(config['target_path'],config['lab_tenants'])
            requesters={t:c['requester'] for t,c in config['lab_tenants'].items()}
        else:target=DurableSyntheticTarget(config['target_path'])
        service=JourneyService(PostgresStateStore(connect),target)
        def ready():
            with connect() as conn:conn.execute('SELECT 1 FROM sd_journey LIMIT 0')
            return True
        ready()
        server=make_server('127.0.0.1',config.get('port',5679),lambda *_:[],handler_class=QuietHandler)
        origin=f'http://127.0.0.1:{server.server_port}'
        server.set_app(RuntimeAPI(auth,service,PostgresCaseRepository(connect),origin,ready,config['mode'],requesters))
        print(json.dumps({'status':'ready','origin':origin}),flush=True)
        server.serve_forever()
    except KeyboardInterrupt:return 0
    except Exception:
        print('Runtime configuration or startup rejected.',file=sys.stderr);return 1


if __name__=='__main__':sys.exit(main())
