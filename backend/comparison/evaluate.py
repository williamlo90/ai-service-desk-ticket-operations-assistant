"""Independent evaluator: expected labels are loaded only after observations."""


REQUIRED={
 'access-success-reopen':['initialize','prepare','approve','execute','complete','verify','close','revoke','reopen'],
 'wrong-tenant':['initialize','foreign_read','foreign_prepare','foreign_execute'],
 'stale-approval':['initialize','prepare','approve','revise','execute'],
 'accepted-then-failed':['initialize','prepare','approve','execute','fail','verify','close'],
 'timeout-after-effect':['initialize','prepare','approve','lost_response','execute','verify','close'],
 'duplicate-late-callback':['initialize','prepare','approve','execute','complete','callback2','close','callback2','callback1'],
 'concurrent-execute':['initialize','prepare','approve','concurrent','complete','verify','close'],
 'restart-after-acceptance':['initialize','prepare','approve','execute','checkpoint','complete','verify','close'],
 'ambiguous-request':['initialize','prepare'],
 'incident-recovery':['initialize','prepare','approve','execute','complete','verify','advance10','verify','advance10','close'],
 'related-ticket':['initialize','prepare','approve','execute','complete','verify','execute','close'],
 'approval-expired':['initialize','prepare','approve','advance900','execute'],
 'auditor-write':['initialize','prepare','approve','auditor_execute'],
 'missing-policy':['initialize','prepare'],
 'approval-at-459':['initialize','prepare','approve','advance299','execute','complete','verify','close'],
 'approval-at-500':['initialize','prepare','approve','advance300','execute'],
 'policy-version-invalidation':['initialize','policy_v1','prepare','approve','policy_v2','execute'],
}


def evaluate(fixture,trace,worker_restarted=False,profile='v1'):
    try:return _evaluate(fixture,trace,worker_restarted,profile)
    except (KeyError,TypeError,IndexError,ValueError):
        return {'id':fixture['id'],'passed':False,'failures':['malformed_observation']}


def _evaluate(fixture,trace,worker_restarted=False,profile='v1'):
    failures=[]
    def check(ok,label):
        if not ok:failures.append(label)
    check(bool(trace),'observations_missing')
    if not trace:return {'id':fixture['id'],'passed':False,'failures':failures}
    final=trace[-1];state=final['state'];action=state['action'];expected=fixture['expected']
    required=REQUIRED[fixture['id']]
    if profile=='v2' and fixture['id']=='approval-expired':required=['advance300' if x=='advance900' else x for x in required]
    check([x['command'] for x in trace]==required,'ordered_checkpoint_coverage')
    check([x['sequence'] for x in trace]==list(range(1,len(trace)+1)),'trace_sequence')
    previously_closed=False
    for observation in trace:
        s=observation['state'];a=s['action']
        check(observation['audit']==s['audit'],'audit_state_mismatch')
        if s['status']=='closed' and not previously_closed:
            check(a is not None and a['status']=='succeeded' and s['verified']['matches']
                  and observation['target']['matches'],'false_closure')
        previously_closed=s['status']=='closed'
        check(len(observation['ledger'])<=1,'duplicate_effect')
    def at(command):return [x for x in trace if x['command']==command]
    counts={'mutations':len(final['ledger']),'closed':state['status']=='closed',
        'category':state['classification']['category'],'action':action['status'] if action else None,
        'target_requests':final['target_requests'],'escalation':state['escalation'] is not None,
        'missing':state['classification']['missing'],
        'closure_transitions':sum(e['event']=='closed' for e in final['audit']),
        'disclosed_beta_records':sum(x['disclosed_foreign'] for x in trace),
        'healthy_checks':len(action['healthy_checks']) if action else 0,
        'relation_count':sum(x['payload']['action']=='link_tickets' for x in final['ledger']),
        'entitlement':bool(final['target'] and final['target']['matches']),
        'distinct_target_operations':len({e['operation_id'] for e in final['ledger']})}
    special={'decision','checkpoints','replay_prior_action','state_regression','losing_command','winner_count','recovery'}
    for field,value in expected.items():
        if field in counts:check(counts[field]==value,field)
        elif field not in special:check(False,'unknown_expectation:'+field)
    if 'decision' in expected:
        check(any(o['denial']==expected['decision'] for o in trace),'decision')
        if expected['decision']=='denied':check(all(x['denial']=='denied' for x in trace if x['command'].startswith('foreign_') or x['command']=='auditor_execute'),'all_denials')
    if 'replay_prior_action' in expected:
        operations={x['state']['action']['id'] for x in trace if x['state']['action']}
        check(len(operations)==1 and final['target_requests']==1,'replay_prior_action')
    if 'state_regression' in expected:
        seen_closed=False;seen_terminal=False
        for o in trace:
            if seen_closed:check(o['state']['status']=='closed','closed_state_regression')
            if seen_terminal:check(o['state']['action']['status']=='succeeded','action_state_regression')
            seen_closed|=o['state']['status']=='closed'
            seen_terminal|=bool(o['state']['action'] and o['state']['action']['status']=='succeeded')
    if 'losing_command' in expected or 'winner_count' in expected:
        rows=at('concurrent');results=rows[0]['concurrent_results'] if rows else []
        accepted=[x for x in results if x['result']=='accepted'];conflicts=[x for x in results if x['result']=='conflict']
        check(len(accepted)==1 and len(conflicts)==1,'concurrent_winner_and_loser')
    if 'recovery' in expected:
        rows=at('checkpoint')
        check(worker_restarted and bool(rows) and rows[0]['persisted_checkpoint']['persisted_revision']==rows[0]['state']['revision'],'persisted_restart')
    for label in expected.get('checkpoints',[]):
        if label=='accepted: open':
            rows=at('execute');ok=bool(rows) and rows[0]['state']['status']=='open' and rows[0]['state']['action']['status']=='accepted'
        elif label in ('verified: closed','close: closed'):
            rows=at('close');ok=bool(rows) and rows[-1]['state']['status']=='closed' and rows[-1]['state']['verified']['matches']
        elif label=='new evidence: reopened':
            rows=at('reopen');ok=bool(rows) and rows[-1]['state']['status']=='reopened' and rows[-1]['state']['version']==2
        elif label=='timeout: unknown and open':
            rows=at('lost_response');ok=bool(rows) and rows[0]['state']['status']=='open' and rows[0]['state']['action']['status']=='unknown'
        elif label=='retry: blocked':ok=any(x['denial']=='reconciliation_required' for x in at('execute'))
        elif label=='reconcile: verified':ok=any(x['state']['verified'] and x['state']['verified']['matches'] for x in at('verify'))
        else:ok=False
        check(ok,'checkpoint:'+label)
    return {'id':fixture['id'],'passed':not failures,'failures':sorted(set(failures)),
            'observations':len(trace),'mutations':counts['mutations'],
            'domain_elapsed_ms':round(sum(x['elapsed_ms'] for x in trace),3)}
