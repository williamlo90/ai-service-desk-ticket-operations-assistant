"""Sandbox summary-update contract with injected transport, no live default.

Never wire this to production until Jira permission and concurrent-edit behavior
are validated in Phase 5. A preflight read is not an atomic Jira version check.
"""
from dataclasses import dataclass,field
from datetime import datetime,timezone
import base64
from hashlib import sha256
import json
from uuid import uuid5,NAMESPACE_URL
from .lifecycle import Proposal,require_current_approval
from .policy import writer
from .store import Missing


class UpdateBlocked(Exception):pass


@dataclass(frozen=True)
class SummaryPlan:
    tenant: str
    key: str
    version: int
    requester: str
    before: str=field(repr=False)
    after: str=field(repr=False)

    def proposal(self):
        payload=json.dumps([self.tenant,self.key,self.version,self.before,self.after],separators=(',',':'))
        return Proposal(self.tenant,self.key,self.version,sha256(payload.encode()).hexdigest(),
                        'jira-summary-v1',self.requester)

    @property
    def operation_id(self):
        return str(uuid5(NAMESPACE_URL,self.tenant+':'+self.proposal().payload_hash))


class JiraSummaryAdapter:
    def __init__(self,connection,reader,transport,journal,clock=None):
        self.connection,self.reader,self.transport,self.journal=connection,reader,transport,journal
        self.clock=clock or (lambda:datetime.now(timezone.utc))

    def prepare(self,actor,key,summary,version,requester):
        writer(actor,self.connection.tenant_id)
        if (not isinstance(summary,str) or not summary.strip() or len(summary)>255
                or any(ord(c)<32 for c in summary) or type(version) is not int or version<1
                or not isinstance(requester,str) or not requester):raise UpdateBlocked('invalid_update')
        ticket=self.reader.read(actor,key)
        if '[REDACTED]' in ticket.summary:raise UpdateBlocked('redacted_source')
        return SummaryPlan(actor.tenant_id,key,version,requester,ticket.summary,summary)

    def _check(self,actor,plan):
        writer(actor,self.connection.tenant_id)
        if plan.tenant!=actor.tenant_id:raise UpdateBlocked('out_of_scope')

    def _record(self,actor,plan,state,status):
        previous=state['revision'];state['revision']+=1;state['status']=status
        state['audit'].append({'sequence':state['revision'],'actor':actor.actor_id,'event':status,
                               'at':self.clock().isoformat()})
        self.journal.save(plan.tenant,plan.operation_id,previous,state)
        return state

    def execute(self,actor,plan,approval):
        self._check(actor,plan)
        require_current_approval(approval,plan.proposal(),self.clock())
        try:
            previous=self.journal.get(plan.tenant,plan.operation_id)
        except Missing:previous=None
        if previous:return previous # Unknown/pending never causes automatic resubmission.
        current=self.reader.read(actor,plan.key)
        if current.summary!=plan.before:raise UpdateBlocked('source_changed')
        state={'tenant':plan.tenant,'id':plan.operation_id,'revision':1,'status':'reserved',
               'audit':[{'sequence':1,'actor':actor.actor_id,'event':'reserved','at':self.clock().isoformat()}]}
        self.journal.create(plan.tenant,plan.operation_id,state)
        auth=base64.b64encode((self.connection.email+':'+self.connection.api_token).encode()).decode()
        url=f'https://api.atlassian.com/ex/jira/{self.connection.cloud_id}/rest/api/3/issue/{plan.key}'
        try:
            status=self.transport(url,{'Authorization':'Basic '+auth,'Content-Type':'application/json'},
                                  json.dumps({'fields':{'summary':plan.after}}).encode())
        except Exception:
            return self._record(actor,plan,state,'unknown')
        if status in (200,204):return self._record(actor,plan,state,'accepted')
        return self._record(actor,plan,state,'rejected' if status in (400,401,403,404,429) else 'unknown')

    def reconcile(self,actor,plan):
        self._check(actor,plan)
        state=self.journal.get(plan.tenant,plan.operation_id)
        if state['status']=='verified':return state
        ticket=self.reader.read(actor,plan.key)
        return self._record(actor,plan,state,'verified' if ticket.summary==plan.after else 'unknown')


def map_ticket(ticket):
    return {'external_reference':f'{ticket.tenant_id}/{ticket.project_key}/{ticket.key}',
            'tenant':ticket.tenant_id,'key':ticket.key,'summary':ticket.summary,
            'source_status':ticket.source_status,'observed_at':ticket.observed_at.isoformat(),
            'source_of_truth':'jira','read_only_snapshot':True}
