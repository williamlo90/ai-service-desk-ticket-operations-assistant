"""Shared application controls. Simulator is injected, never selected by input."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
from uuid import uuid4

from .contracts import AccessDenied, Role, require_staff
from .lifecycle import (Proposal, Approval, ActionState, VerifiedOutcome, approve,
                        require_current_approval, require_closable, should_reopen)
from .policy import POLICIES, context, triage, writer


class JourneyBlocked(Exception): pass


def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)


def stamp(now):
    if now.tzinfo is None or now.utcoffset() is None: raise ValueError('Aware clock required.')
    return now.isoformat()


class JourneyService:
    def __init__(self,store,target,clock=None):
        self.store,self.target=store,target
        self.clock=clock or (lambda:datetime.now(timezone.utc))

    def read(self,actor,case_id):
        require_staff(actor,actor.tenant_id)
        return self.store.get(actor.tenant_id,case_id)

    def _save(self,actor,state,event):
        revision=state['revision']
        state['revision']+=1
        state['audit'].append({'sequence':state['revision'],'actor':actor.actor_id,
                               'event':event,'at':stamp(self.clock())})
        self.store.save(actor.tenant_id,state['id'],revision,state)
        return deepcopy(state)

    def create(self,actor,text,requester='requester-a'):
        writer(actor,actor.tenant_id)
        if not isinstance(requester,str) or not requester or len(requester)>128:
            raise JourneyBlocked('invalid_requester')
        classification=triage(text)
        key=str(uuid4())
        state={'id':key,'tenant':actor.tenant_id,'revision':1,'version':1,
               'requester':requester,'text':text,'classification':classification,
               'status':'open','proposal':None,'approval':None,'action':None,
               'verified':None,'closed_at':None,'escalation':None,
               'audit':[{'sequence':1,'actor':actor.actor_id,'event':'received','at':stamp(self.clock())}]}
        self.store.create(actor.tenant_id,key,state)
        return deepcopy(state)

    def get_context(self,actor,case_id):
        state=self.read(actor,case_id)
        return {'case':state,'context':context(actor,state['tenant'],state['classification']['category'])}

    def prepare(self,actor,case_id,expected_version):
        writer(actor,actor.tenant_id)
        state=self.read(actor,case_id)
        if state['version'] != expected_version: raise JourneyBlocked('version_conflict')
        if state['status'] != 'open' or state['action']: raise JourneyBlocked('action_already_started')
        if state['classification']['decision'] != 'prepare':
            raise JourneyBlocked(state['classification']['decision'])
        category=state['classification']['category'];policy=POLICIES[category]
        payload={'action':policy.action,'tenant':state['tenant'],'requester':state['requester']}
        payload.update({'resource':'reports','access':'read-only'} if category=='access_request'
                       else {'service':'demo-api'} if category=='service_incident'
                       else {'source':'SD-2','related':'SD-1'})
        state['proposal']={'tenant_id':state['tenant'],'case_id':case_id,
            'case_version':state['version'],'payload_hash':sha256(canonical(payload).encode()).hexdigest(),
            'policy_version':policy.version,'requester_id':state['requester'],'payload':payload}
        state['approval']=None
        return self._save(actor,state,'proposal_prepared')

    @staticmethod
    def _proposal(state):
        if not state['proposal']: raise JourneyBlocked('proposal_required')
        return Proposal(**{k:v for k,v in state['proposal'].items() if k!='payload'})

    def approve(self,actor,case_id,expected_version):
        state=self.read(actor,case_id)
        if state['version'] != expected_version: raise JourneyBlocked('version_conflict')
        if state['action'] or state['status']!='open': raise JourneyBlocked('action_already_started')
        proposal=self._proposal(state);policy=POLICIES[state['classification']['category']]
        if proposal.policy_version != policy.version: raise JourneyBlocked('stale_policy')
        approval=approve(actor,proposal,self.clock(),self.clock()+timedelta(seconds=policy.ttl_seconds))
        state['approval']={'approver_id':approval.approver_id,
            'approved_at':stamp(approval.approved_at),'expires_at':stamp(approval.expires_at),
            'snapshot':{k:v for k,v in state['proposal'].items() if k!='payload'}}
        return self._save(actor,state,'approved')

    def revise(self,actor,case_id,text,expected_version):
        writer(actor,actor.tenant_id);state=self.read(actor,case_id)
        if state['version']!=expected_version: raise JourneyBlocked('version_conflict')
        if state['action']: raise JourneyBlocked('action_already_started')
        state['text']=text;state['classification']=triage(text);state['version']+=1
        return self._save(actor,state,'case_revised')

    def execute(self,actor,case_id,expected_version):
        writer(actor,actor.tenant_id);state=self.read(actor,case_id)
        if state['version']!=expected_version: raise JourneyBlocked('version_conflict')
        if state['action']:
            if state['action']['status']=='unknown': raise JourneyBlocked('reconciliation_required')
            return state  # Idempotent receipt; never submit a second external operation.
        if state['status']!='open': raise JourneyBlocked('case_not_open')
        proposal=self._proposal(state);raw=state['approval']
        if not raw: raise JourneyBlocked('approval_required')
        current=Proposal(proposal.tenant_id,case_id,state['version'],
            sha256(canonical(state['proposal']['payload']).encode()).hexdigest(),
            POLICIES[state['classification']['category']].version, state['requester'])
        approval=Approval(Proposal(**raw['snapshot']),raw['approver_id'],
                          datetime.fromisoformat(raw['approved_at']),datetime.fromisoformat(raw['expires_at']))
        require_current_approval(approval,current,self.clock())
        operation=str(uuid4())
        state['action']={'id':operation,'status':'requested','dispatched_at':stamp(self.clock()),
                         'sequence':0,'healthy_checks':[]}
        state=self._save(actor,state,'dispatch_reserved') # CAS before side effect.
        try:
            receipt=self.target.submit(state['tenant'],operation,state['proposal']['payload'])
            status=receipt['status']
        except Exception:
            status='unknown'
        state=self.read(actor,case_id)
        # Reconciliation may have raced dispatch completion; never regress terminal state.
        if state['action']['status']=='requested':
            state['action']['status']=status
            return self._save(actor,state,'dispatch_'+status)
        return state

    def verify(self,actor,case_id):
        writer(actor,actor.tenant_id);state=self.read(actor,case_id)
        if not state['action']: raise JourneyBlocked('action_required')
        if state['status']=='closed': return state
        observation=self.target.inspect(state['tenant'],state['action']['id'],state['proposal']['payload'])
        if observation['sequence'] < state['action']['sequence']: return state
        state['action']['sequence']=observation['sequence']
        if state['action']['status'] not in ('succeeded','failed'):
            state['action']['status']=observation['status']
        now=self.clock();category=state['classification']['category']
        valid=observation['status']=='succeeded' and observation['matches']
        if category=='service_incident':
            checks=state['action']['healthy_checks']
            if not valid: checks.clear()
            elif not checks or (now-datetime.fromisoformat(checks[-1])).total_seconds()>=10:
                checks.append(stamp(now))
            valid=valid and len(checks)>=3
        state['verified']={'matches':valid,'at':stamp(now),'reference':'target:'+state['action']['id']}
        if observation['status']=='failed':
            state['escalation']={'owner':actor.actor_id,'reason':'target_failed'}
        return self._save(actor,state,'outcome_verified' if valid else 'outcome_pending')

    def close(self,actor,case_id):
        writer(actor,actor.tenant_id);state=self.read(actor,case_id)
        if state['status']=='closed': return state
        if state['classification']['category']=='repeated_ticket':
            raise JourneyBlocked('relation_does_not_resolve_incident')
        state=self.verify(actor,case_id) # Fresh authoritative read-back, not cached Boolean.
        action=state['action'];verified=state['verified']
        outcome=VerifiedOutcome(state['tenant'],case_id,action['id'],state['version'],
            verified['reference'],datetime.fromisoformat(verified['at']),verified['matches'])
        require_closable(tenant_id=state['tenant'],case_id=case_id,action_id=action['id'],
            case_version=state['version'],state=ActionState(action['status']),
            dispatched_at=datetime.fromisoformat(action['dispatched_at']),now=self.clock(),outcome=outcome)
        state['status']='closed';state['closed_at']=stamp(self.clock())
        return self._save(actor,state,'closed')

    def reopen(self,actor,case_id):
        writer(actor,actor.tenant_id);state=self.read(actor,case_id)
        if state['status']!='closed': raise JourneyBlocked('case_not_closed')
        observation=self.target.inspect(state['tenant'],state['action']['id'],state['proposal']['payload'])
        now=self.clock()
        if not should_reopen(closed=True,evidence_authenticated=True,evidence_tenant=state['tenant'],
            case_tenant=state['tenant'],closed_at=datetime.fromisoformat(state['closed_at']),
            observed_at=now,now=now,invalidates_outcome=not observation['matches']):
            raise JourneyBlocked('adverse_evidence_required')
        state['status']='reopened';state['version']+=1;state['verified']=None
        return self._save(actor,state,'reopened')

    def summary(self,actor):
        require_staff(actor,actor.tenant_id)
        states=self.store.list(actor.tenant_id)
        return {'tenant':actor.tenant_id,'total':len(states),
                'closed':sum(s['status']=='closed' for s in states),
                'reopened':sum(s['status']=='reopened' for s in states),
                'escalated':sum(s['escalation'] is not None for s in states)}
