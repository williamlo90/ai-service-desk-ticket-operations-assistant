"""Candidate command plans use fixture input/events, never expected outcomes."""
PLANS={
 'access-success-reopen':['prepare','approve','execute','complete','verify','close','revoke','reopen'],
 'wrong-tenant':['foreign_read','foreign_prepare','foreign_execute'],
 'stale-approval':['prepare','approve','revise','execute'],
 'accepted-then-failed':['prepare','approve','execute','fail','verify','close'],
 'timeout-after-effect':['prepare','approve','lost_response','execute','verify','close'],
 'duplicate-late-callback':['prepare','approve','execute','complete','callback2','close','callback2','callback1'],
 'concurrent-execute':['prepare','approve','concurrent','complete','verify','close'],
 'restart-after-acceptance':['prepare','approve','execute','checkpoint','complete','verify','close'],
 'ambiguous-request':['prepare'],
 'incident-recovery':['prepare','approve','execute','complete','verify','advance10','verify','advance10','close'],
 'related-ticket':['prepare','approve','execute','complete','verify','execute','close'],
 'approval-expired':['prepare','approve','advance900','execute'],
 'auditor-write':['prepare','approve','auditor_execute'],
 'missing-policy':['prepare'],
 'approval-at-459':['prepare','approve','advance299','execute','complete','verify','close'],
 'approval-at-500':['prepare','approve','advance300','execute'],
 'policy-version-invalidation':['policy_v1','prepare','approve','policy_v2','execute'],
}


def segments(fixtures,profile='v1'):
    before=[];after=[];current=before
    for item in fixtures:
        key=item['id']
        current.append({'fixture':key,'command':'initialize','input':item['input']})
        for command in PLANS[key]:
            if profile=='v2' and key=='approval-expired' and command=='advance900':command='advance300'
            current.append({'fixture':key,'command':command})
            if command=='checkpoint':current=after
    return before,after
