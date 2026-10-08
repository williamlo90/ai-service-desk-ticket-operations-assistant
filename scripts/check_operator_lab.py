"""Readiness/negative checks only; never use William's token to approve."""
import json,sys,subprocess
from urllib.request import Request,urlopen
from urllib.error import HTTPError
from operator_lab import CONFIG,REPORT,ROOT

def run():
    config=json.loads(CONFIG.read_text());report=json.loads(REPORT.read_text())
    origin=report['origin'];key=report['case_id']
    def call(tenant,path,args):
        req=Request(origin+path,data=json.dumps(args).encode(),headers={
            'Content-Type':'application/json','Authorization':'Bearer '+config['tokens'][tenant]['staff']})
        try:
            with urlopen(req,timeout=5) as r:return r.status,json.load(r)
        except HTTPError as exc:
            status=exc.code;exc.close();return status,None
    with urlopen(origin+'/readyz',timeout=5) as r:assert r.status==200
    status,data=call('alpha','/v1/tools/context',{'case_id':key});assert status==200
    case=data['result']['case'];assert case['source']['key']=='IT-1'
    assert case['action'] is None
    assert call('beta','/v1/tools/context',{'case_id':key})[0]==404
    assert call('alpha','/v1/approvals',{'case_id':key,'expected_version':case['version'],
        'payload_hash':case['proposal']['payload_hash']})[0]==403
    # Only before human review: this check must not dispatch an approved proposal.
    import psycopg
    from service_desk.postgres import PostgresStateStore
    stored=PostgresStateStore(lambda:psycopg.connect(**config['database'])).get('alpha',key)
    assert stored['approval'] is None
    mcp=subprocess.run(['node',str(ROOT/'mcp-server/test/connected.mjs')],
        input=json.dumps({'mode':'lab','origin':origin,'stage':'pending','case_id':key,
                          'staff':config['tokens']['alpha']['staff']}),text=True,capture_output=True,timeout=20)
    assert mcp.returncode==0
    # Approval could arrive concurrently, so never probe the execute endpoint here.
    evidence={'status':'passed','case_id':key,'ready':True,'source':'Jira IT-1',
        'cross_tenant_case_denied':True,'integration_approval_denied':True,
        'approval_absent_at_check':True,'target_action_absent_at_check':True,
        'mcp_imported_source_read_passed':True,'human_token_used':False,'project_dotenv_read':False}
    (ROOT/'docs/phase-5/operator-readiness.json').write_text(json.dumps(evidence,indent=2)+'\n')
    print(json.dumps(evidence))

if __name__=='__main__':
    try:run()
    except Exception as exc:
        print('Operator readiness stopped: '+type(exc).__name__+'. Details withheld.');sys.exit(1)
