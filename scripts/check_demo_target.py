"""Technical acceptance of user-selected demo targets; not business approval."""
from datetime import datetime,timezone
from pathlib import Path
from uuid import uuid4
from urllib.error import HTTPError
import json,sys
from setup_target_sandbox import ROOT,PRIVATE,request


def main():
    config=json.loads((PRIVATE/'bootstrap.json').read_text());rows=[]
    base='http://127.0.0.1:8086'
    for tenant,c in config['tenants'].items():
        token=c['control_token'];prefix='/v1/'+tenant
        before=request(prefix+'/service',token=token,base=base)
        operation=str(uuid4())
        receipt=request(prefix+'/restart','POST',{'operation_id':operation},token,base=base)
        assert receipt['status']=='accepted'
        observed=request(prefix+'/operations/'+operation,token=token,base=base)
        after=request(prefix+'/service',token=token,base=base)
        assert observed['matches'] and observed['status']=='succeeded' and before['generation']!=after['generation']
        replay=request(prefix+'/restart','POST',{'operation_id':operation},token,base=base)
        assert replay['replayed'] and request(prefix+'/service',token=token,base=base)['generation']==after['generation']
        other='beta' if tenant=='alpha' else 'alpha'
        for path,method,data in [('/v1/'+other+'/service','GET',None),('/v1/'+other+'/restart','POST',{'operation_id':str(uuid4())})]:
            try:request(path,method,data,token,base=base)
            except HTTPError as exc:assert exc.code==403
            else:raise AssertionError('Cross tenant access')
        rows.append({'tenant':tenant,'real_child_generation_changed':True,'readback_matches':True,
            'replay_did_not_restart_child':True,'cross_tenant_read_and_write_denied':True})
    report={'checked_at':datetime.now(timezone.utc).isoformat(),'status':'passed','results':rows,
        'project_dotenv_read':False,'credentials_printed':False,
        'scope':'Technical lab target checks; business approval and full ticket-to-target journey not exercised'}
    (ROOT/'docs/phase-5/demo-target-check.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Demo lab: both tenants passed real child restart/read-back, idempotent replay and cross-tenant denial.')


if __name__=='__main__':
    try:main()
    except Exception as exc:print('Demo acceptance stopped: '+type(exc).__name__);sys.exit(1)
