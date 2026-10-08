"""Bounded local JSON-lines API for the offline TypeScript protocol harness.

Operator config binds identity; tool arguments cannot select an actor. Synthetic
mode only. No HTTP listener, credential file read, production target or Docker.
"""
import json,os,sys
from .api import strict_object,reject_constant
from .auth import TokenAuthenticator,AuthenticationFailed
from .contracts import Actor,Role,AccessDenied
from .journeys import JourneyService,JourneyBlocked
from .lifecycle import LifecycleBlocked
from .store import MemoryStateStore,Missing,Conflict
from .simulator import SimulatedTarget
from .skills import SkillRunner,SkillRejected


def public_state(state):
    return {'case_id':state['id'],'tenant':state['tenant'],'version':state['version'],
            'status':state['status'],'category':state['classification']['category'],
            'proposal':state['proposal'],'action':state['action'],'verified':state['verified'],
            'source':state.get('source')}


class Bridge:
    def __init__(self,auth,service,requesters=None):
        self.auth,self.service=auth,service
        self.requesters=dict(requesters or {})

    def call(self,token,command,args):
        actor=self.auth.authenticate('Bearer '+token)
        fields={'search':{'query','offset','limit'},'create':{'text'},'context':{'case_id'},
                'prepare':{'case_id','expected_version'},'execute':{'case_id','expected_version'},
                'verify':{'case_id'},'reopen':{'case_id'},'close':{'case_id'}}
        if command not in fields or type(args) is not dict or set(args)!=fields[command]:
            raise SkillRejected('invalid_arguments')
        if 'case_id' in args and (not isinstance(args['case_id'],str) or len(args['case_id'])!=36):
            raise SkillRejected('invalid_arguments')
        if 'expected_version' in args and (type(args['expected_version']) is not int or args['expected_version']<1):
            raise SkillRejected('invalid_arguments')
        if command=='search':
            if (not isinstance(args['query'],str) or len(args['query'])>200
                    or type(args['offset']) is not int or args['offset']<0
                    or type(args['limit']) is not int or not 1<=args['limit']<=20):
                raise SkillRejected('invalid_arguments')
            self.service.summary(actor) # Same permission boundary as all reads.
            rows=sorted(self.service.store.list(actor.tenant_id),key=lambda s:s['id'])
            rows=[s for s in rows if args['query'].lower() in s['text'].lower()]
            end=args['offset']+args['limit']
            return {'items':[public_state(s) for s in rows[args['offset']:end]],
                    'next_offset':end if end<len(rows) else None}
        if command=='create':return public_state(self.service.create(actor,args['text'],
            requester=self.requesters.get(actor.tenant_id,'requester-a')))
        if command=='context':
            result=self.service.get_context(actor,args['case_id'])
            return {'case':public_state(result['case']),'context':result['context']}
        if command=='prepare':
            return SkillRunner(self.service).run('prepare_resolution',actor,args)['result']
        if command=='verify':
            return SkillRunner(self.service).run('verify_resolution',actor,args)['result']
        return public_state(getattr(self.service,command)(actor,**args))


def main():
    try:
        if os.environ.get('SERVICE_DESK_MODE')!='synthetic':raise ValueError()
        bindings=json.loads(os.environ['SERVICE_DESK_BINDINGS'])
        auth=TokenAuthenticator({token:Actor(item['actor_id'],item['tenant_id'],Role(item['role']))
                                 for token,item in bindings.items()})
        token=os.environ['SERVICE_DESK_API_TOKEN'];auth.authenticate('Bearer '+token)
        target=SimulatedTarget()
        if os.environ.get('SERVICE_DESK_TEST_FIXTURES')=='1':
            class CompletingTarget(SimulatedTarget):
                def submit(self,tenant,operation,payload):
                    result=super().submit(tenant,operation,payload)
                    self.complete(tenant,operation)
                    return result
            target=CompletingTarget()
        service=JourneyService(MemoryStateStore(),target)
        if os.environ.get('SERVICE_DESK_TEST_FIXTURES')=='1':
            for tenant in ('alpha','beta'):
                staff=Actor('fixture-staff',tenant,Role.SPECIALIST)
                lead=Actor('fixture-human-supervisor',tenant,Role.SUPERVISOR)
                case=service.create(staff,'Grant requester-a read access to reports')
                service.prepare(staff,case['id'],1);service.approve(lead,case['id'],1)
        bridge=Bridge(auth,service)
    except Exception:
        print('Bridge configuration rejected.',file=sys.stderr);return 1
    while True:
        line=sys.stdin.buffer.readline(65537)
        if not line:break
        if len(line)>65536: return 1
        request_id=None
        try:
            message=json.loads(line,object_pairs_hook=strict_object,parse_constant=reject_constant)
            request_id=message['id']
            if type(request_id) is not int:raise ValueError()
            data=bridge.call(token,message['command'],message['args'])
            response={'id':request_id,'ok':True,'data':data}
        except AuthenticationFailed:response={'id':request_id,'ok':False,'error':'unauthorized'}
        except AccessDenied:response={'id':request_id,'ok':False,'error':'forbidden'}
        except Missing:response={'id':request_id,'ok':False,'error':'not_found'}
        except Conflict:response={'id':request_id,'ok':False,'error':'version_conflict'}
        except (JourneyBlocked,LifecycleBlocked,SkillRejected) as exc:
            safe={'approval_required','version_conflict','reconciliation_required','stale_approval',
                  'expired_approval','outcome_not_verified','adverse_evidence_required','case_not_closed',
                  'invalid_arguments','clarification','escalate','action_already_started',
                  'relation_does_not_resolve_incident','proposal_required','case_not_open','stale_policy'}
            response={'id':request_id,'ok':False,'error':str(exc) if str(exc) in safe else 'request_rejected'}
        except Exception:response={'id':request_id,'ok':False,'error':'invalid_request'}
        encoded=json.dumps(response,allow_nan=False)
        if len(encoded.encode())>60000:
            encoded=json.dumps({'id':request_id,'ok':False,'error':'output_limit'})
        print(encoded,flush=True)
    return 0


if __name__=='__main__':sys.exit(main())
