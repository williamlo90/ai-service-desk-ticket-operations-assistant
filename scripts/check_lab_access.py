"""Technical Keycloak adapter smoke checks on dedicated lab users only.

Each test restores initial group membership. No ticket/business approval asserted.
"""
from datetime import datetime,timezone
from hashlib import sha256
from pathlib import Path
from uuid import uuid4
import json,sys
from setup_target_sandbox import ROOT,PRIVATE
sys.path.insert(0,str(ROOT/'backend'))
from service_desk.lab_targets import LabTargets,LabTargetUnavailable


def main():
    config=json.loads((PRIVATE/'bootstrap.json').read_text())
    run_id=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    folder=ROOT/'local/lab-access'/run_id;folder.mkdir(parents=True)
    target=LabTargets(folder/'operations.sqlite',config['tenants']);original_http=target.http
    rows=[];cleanup=True
    try:
        for tenant,c in config['tenants'].items():
            membership=target.keycloak+'/admin/realms/'+c['realm']+'/users/'+c['user_id']+'/groups'
            before=original_http(membership,token=target.token(c));was_member=any(g['id']==c['group_id'] for g in before)
            if was_member:raise RuntimeError('Lab user must start without reports-reader access')
            payload={'action':'grant_read_access','tenant':tenant,'requester':c['requester'],'resource':'reports','access':'read-only'}
            try:
                for lost_reply in (False,True):
                    calls=[0]
                    def observed_http(url,method='GET',data=None,token=None,form=False):
                        value=original_http(url,method,data,token,form)
                        if method=='PUT':
                            calls[0]+=1
                            if lost_reply:raise LabTargetUnavailable('Injected reply loss after actual target commit')
                        return value
                    target.http=observed_http;operation=str(uuid4())
                    try:target.submit(tenant,operation,payload)
                    except LabTargetUnavailable:
                        if not lost_reply:raise
                    observed=target.inspect(tenant,operation,payload)
                    assert observed['matches'] and observed['status']=='succeeded'
                    target.submit(tenant,operation,payload);assert calls[0]==1
                    original_http(membership+'/'+c['group_id'],'DELETE',token=target.token(c))
                    assert not target.inspect(tenant,operation,payload)['matches']
                    rows.append({'tenant':tenant,'lost_reply_injected':lost_reply,'membership_readback':True,
                        'put_calls':calls[0],'replay_without_second_put':True,'revocation_detected':True})
            finally:
                target.http=original_http
                try:
                    current=original_http(membership,token=target.token(c))
                    if any(g['id']==c['group_id'] for g in current):original_http(membership+'/'+c['group_id'],'DELETE',token=target.token(c))
                    cleanup=cleanup and not any(g['id']==c['group_id'] for g in original_http(membership,token=target.token(c)))
                except Exception:cleanup=False
        assert cleanup
        status='passed'
    except Exception as exc:
        status='failed';error=type(exc).__name__
    report={'run_id':run_id,'status':status,'results':rows,'initial_membership_restored':cleanup,
        'project_dotenv_read':False,'credentials_printed':False,
        'source_sha256':sha256((ROOT/'backend/service_desk/lab_targets.py').read_bytes().replace(b'\r\n',b'\n')).hexdigest(),
        'scope':'Technical adapter test using isolated Keycloak users; not human-approved Jira-to-target acceptance'}
    if status!='passed':report['error']=error
    (ROOT/'docs/phase-5/lab-access-check.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Keycloak adapter: '+status+'; '+str(len(rows))+' checks; original membership restored='+str(cleanup))
    return 0 if status=='passed' else 1


if __name__=='__main__':
    try:sys.exit(main())
    except Exception as exc:print('Keycloak adapter check could not start: '+type(exc).__name__);sys.exit(1)
