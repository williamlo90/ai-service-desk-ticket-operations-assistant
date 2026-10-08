"""Local operational alerts from bounded metadata, never payloads or credentials."""
from datetime import datetime,timezone


def assess(snapshot,now=None):
    now=now or datetime.now(timezone.utc)
    alerts=[]
    for component,max_age in (('service',15),('worker',30),('poll',150)):
        state=snapshot.get(component,{})
        if component=='poll' and not snapshot.get('poll_enabled'):continue
        try:
            at=datetime.fromisoformat(state['checked_at'])
            age=(now-at).total_seconds()
            if not -5<=age<=max_age:alerts.append(component+'_heartbeat_stale')
        except (KeyError,ValueError,TypeError):alerts.append(component+'_heartbeat_missing')
        if state.get('status')=='review_required':alerts.append(component+'_review_required')
        if component=='worker' and any(r.get('done') and r.get('reason') not in (None,'closed')
                                       for r in state.get('results',[])):
            alerts.append('job_review_required')
    if snapshot.get('poll_blocked'):alerts.append('poll_manual_resume_required')
    if not snapshot.get('api_ready'):alerts.append('api_not_ready')
    if snapshot.get('expired_bindings',0):alerts.append('identity_expired')
    elif snapshot.get('expiring_bindings',0):alerts.append('identity_expires_within_hour')
    return {'status':'ready' if not alerts else 'review_required','alerts':sorted(set(alerts)),
            'checked_at':now.isoformat()}
