"""Reconciliation budget persisted with the journey.

Retries authoritative reads, never resubmits an uncertain target operation.
An orchestrator owns timer scheduling; this controller owns the persisted budget.
PostgreSQL stores coordinate cooperative ticks with a transaction advisory lock;
memory stores remain single-worker fixtures. This is not a network-partition lease.
"""
from datetime import datetime,timedelta,timezone
from contextlib import nullcontext
from .journeys import JourneyBlocked,stamp
from .lifecycle import LifecycleBlocked
from .policy import writer


class RecoveryController:
    def __init__(self,service,clock=None,delay_scale=1):
        if type(delay_scale) is not int or not 1<=delay_scale<=300:raise ValueError('Invalid backoff scale')
        self.service=service
        self.delay_scale=delay_scale
        self.clock=clock or (lambda:datetime.now(timezone.utc))

    def tick(self,actor,case_id):
        writer(actor,actor.tenant_id)
        claim=getattr(self.service.store,'claim',None)
        with claim(actor.tenant_id,case_id) if claim else nullcontext(True) as acquired:
            if not acquired:
                state=self.service.read(actor,case_id)
                return {'done':False,'retry_seconds':0.25,'attempts':state.get('recovery',{}).get('attempts',0),
                        'reason':'worker_busy'}
            return self._tick(actor,case_id)

    def _tick(self,actor,case_id):
        s=self.service;state=s.read(actor,case_id);now=self.clock()
        recovery=state.get('recovery',{'attempts':0,'done':False,'next_at':None})
        if recovery['done']:return self.result(state)
        if recovery['next_at'] and now<datetime.fromisoformat(recovery['next_at']):
            return self.result(state)
        if recovery['attempts']>=4:
            return self.finish(actor,state,recovery,'retry_exhausted')
        if not state['action']:
            try:state=s.execute(actor,case_id,state['version'])
            except (JourneyBlocked,LifecycleBlocked):
                return self.finish(actor,s.read(actor,case_id),recovery,'approval_rejected')
        # Reserve a read attempt durably before contacting the target.
        recovery['attempts']+=1
        recovery['next_at']=stamp(now+timedelta(seconds=self.delay_scale*2**(recovery['attempts']-1)))
        state['recovery']=recovery
        s._save(actor,state,'reconciliation_attempt')
        try:
            state=s.verify(actor,case_id)
            if state['verified']['matches']:
                state=s.close(actor,case_id)
                return self.finish(actor,state,recovery,'closed')
            if state['action']['status']=='failed':
                return self.finish(actor,state,recovery,'target_failed')
        except (TimeoutError,ConnectionError):
            state=s.read(actor,case_id)
        if recovery['attempts']>=4:
            return self.finish(actor,state,recovery,'retry_exhausted')
        return self.result(state)

    def finish(self,actor,state,recovery,reason):
        recovery.update(done=True,next_at=None,reason=reason)
        state['recovery']=recovery
        if reason!='closed':
            state['escalation']={'owner':actor.actor_id,'reason':reason}
        state=self.service._save(actor,state,'recovery_'+reason)
        return self.result(state)

    def result(self,state):
        r=state['recovery']
        delay=max(0,(datetime.fromisoformat(r['next_at'])-self.clock()).total_seconds()) if r['next_at'] else 0
        return {'done':r['done'],'retry_seconds':max(0.1,delay),
                'attempts':r['attempts'],'reason':r.get('reason')}
