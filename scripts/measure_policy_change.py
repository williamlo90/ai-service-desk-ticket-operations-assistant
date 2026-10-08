"""Prospective automated edit/revert rehearsal, not a human effort benchmark."""
from datetime import datetime,timezone
from hashlib import sha256
from pathlib import Path
from time import perf_counter
import json,subprocess,sys

ROOT=Path(__file__).resolve().parents[1]
CHECK="""
from datetime import datetime,timedelta,timezone
from service_desk.contracts import Actor,Role
from service_desk.journeys import JourneyService
from service_desk.lifecycle import LifecycleBlocked
from service_desk.store import MemoryStateStore
from service_desk.simulator import SimulatedTarget
from service_desk.policy import POLICIES,Policy
assert POLICIES['access_request'].version=='access-v2'
assert POLICIES['access_request'].ttl_seconds==300
staff=Actor('staff','alpha',Role.SPECIALIST);lead=Actor('lead','alpha',Role.SUPERVISOR)
def setup():
 now=[datetime(2026,10,8,tzinfo=timezone.utc)]
 service=JourneyService(MemoryStateStore(),SimulatedTarget(),lambda:now[0])
 key=service.create(staff,'Grant reports read access')['id']
 service.prepare(staff,key,1);service.approve(lead,key,1)
 return service,key,now
s,k,t=setup();t[0]+=timedelta(seconds=299);assert s.execute(staff,k,1)['action']
s,k,t=setup();t[0]+=timedelta(seconds=300)
try:s.execute(staff,k,1)
except LifecycleBlocked:pass
else:raise AssertionError('Expired approval accepted')
POLICIES['access_request']=Policy('access-v1','grant_read_access',900)
s,k,t=setup();POLICIES['access_request']=Policy('access-v2','grant_read_access',300)
try:s.execute(staff,k,1)
except LifecycleBlocked:pass
else:raise AssertionError('Old policy approval accepted')
print('3 boundary checks passed')
"""


def main():
    run_id=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    folder=ROOT/'local/maintenance'/run_id;folder.mkdir(parents=True)
    rows=[]
    for candidate in ('code','n8n'):
        target=folder/candidate;package=target/'service_desk';package.mkdir(parents=True)
        for source in (ROOT/'backend/service_desk').glob('*.py'):
            (package/source.name).write_bytes(source.read_bytes())
        path=package/'policy.py';before=path.read_text()
        old="'access_request': Policy('access-v1','grant_read_access'),"
        new="'access_request': Policy('access-v2','grant_read_access',300),"
        assert before.count(old)==1
        started=perf_counter();path.write_text(before.replace(old,new),encoding='utf-8')
        patch_ms=(perf_counter()-started)*1000
        digest=sha256(path.read_bytes()).hexdigest()
        started=perf_counter()
        test=subprocess.run([sys.executable,'-B','-c',CHECK],cwd=target,text=True,capture_output=True,timeout=30)
        test_ms=(perf_counter()-started)*1000
        assert test.returncode==0,'Boundary regression failed'
        started=perf_counter();path.write_text(before,encoding='utf-8')
        assert path.read_text()==before
        rollback_ms=(perf_counter()-started)*1000
        rows.append({'candidate':candidate,'shared_files_changed':1,'policy_entries_changed':1,
            'orchestrator_files_changed':0,'workflow_nodes_changed':0,'boundary_checks_passed':3,
            'failed_regressions':0,'rollback_verified':True,'edited_policy_sha256':digest,
            'automated_patch_ms':round(patch_ms,3),'boundary_test_process_ms':round(test_ms,3),
            'automated_rollback_ms':round(rollback_ms,3),'active_human_editing_seconds':None})
    report={'run_id':run_id,'method':'Prospective automated shared-policy patch/test/rollback on two isolated source copies',
        'change':'access-v1 900s to access-v2 300s; deny old-policy approvals','results':rows,
        'source_policy_sha256':sha256((ROOT/'backend/service_desk/policy.py').read_bytes()).hexdigest(),
        'raw_copies':str(folder.relative_to(ROOT)).replace('\\','/'),
        'limitations':['Identical shared domain implementation; does not differentiate engine editing UX',
            'Machine patch timings include filesystem overhead; not operator effort or performance ranking',
            'Three domain boundary checks, not a rerun of full connected candidate acceptance',
            'No workflow deployment edit, new connector change or operator usability session measured'],
        'engine_winner':None}
    (ROOT/'docs/phase-5/maintenance-rehearsal.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print('Both source copies: 1 shared policy entry changed, 0 engine edits, 3/3 boundary checks; rollback verified.')


if __name__=='__main__':main()
