"""One bounded scan of approved durable jobs; no synthetic supervisor approvals."""
from .recovery import RecoveryController

def scan(service,actor,source_check=lambda state:True,limit=100):
    states=[state for state in service.store.list(actor.tenant_id)
            if state['status']!='closed' and not state.get('escalation')
            and not state.get('recovery',{}).get('done')
            and (state['approval'] or state['action'])]
    if len(states)>limit:raise ValueError('queue_scan_limit')
    results=[]
    for state in states:
        source_problem=None
        if state.get('source'):
            try:
                if not source_check(state):source_problem='source_changed_review_required'
            except Exception:source_problem='source_unavailable_review_required'
        if source_problem:
            state=service.read(actor,state['id'])
            state['escalation']={'owner':actor.actor_id,'reason':source_problem}
            service._save(actor,state,source_problem)
            results.append({'case_id':state['id'],'reason':source_problem});continue
        controller=RecoveryController(service,delay_scale=10 if state['classification']['category']=='service_incident' else 1)
        results.append({'case_id':state['id'],**controller.tick(actor,state['id'])})
    return results
