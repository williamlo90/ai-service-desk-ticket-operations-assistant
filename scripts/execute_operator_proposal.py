"""Consume an existing William approval; never create/renew one or write Jira.

Re-read the allowlisted Jira snapshot before MCP -> API -> target dispatch.
No automatic retries after an ambiguous outcome. Secrets remain internal.
"""
from datetime import datetime,timezone
import json,subprocess,sys
from operator_lab import CONFIG,REPORT,ROOT,save

def run():
    import psycopg
    from check_jira_read import load_config,CLOUD_ID,SITE_URL
    from service_desk.jira import JiraConnection,JiraReader
    from service_desk.contracts import Actor,Role
    from service_desk.postgres import PostgresStateStore
    from service_desk.journeys import JourneyService
    from service_desk.lab_targets import LabTargets
    config=json.loads(CONFIG.read_text());report=json.loads(REPORT.read_text())
    store=PostgresStateStore(lambda:psycopg.connect(**config['database']))
    state=store.get('alpha',report['case_id']);approval=state['approval']
    if not approval or approval['approver_id']!='William':raise ValueError('human_approval_required')
    if not state['action'] and datetime.fromisoformat(approval['expires_at'])<=datetime.now(timezone.utc):
        raise ValueError('approval_expired')
    jira=load_config()
    if (jira.get('JIRA_CLOUD_ID')!=CLOUD_ID or jira.get('JIRA_PROJECT_KEY')!='IT'
            or jira.get('JIRA_TEST_ISSUE_KEY')!='IT-1'):raise ValueError()
    actor=Actor('lab-integration-alpha','alpha',Role.SPECIALIST)
    ticket=JiraReader(JiraConnection('alpha',CLOUD_ID,'IT',jira['JIRA_EMAIL'],jira['JIRA_API_TOKEN'],site_url=SITE_URL)).read(actor,'IT-1')
    target=LabTargets(config['target_path'],config['lab_tenants'])
    current=JourneyService(store,target).import_ticket(actor,ticket,CLOUD_ID,config['lab_tenants']['alpha']['requester'])
    if current['id']!=report['case_id'] or current['classification']['category']!='access_request':raise ValueError()
    tenant=config['lab_tenants']['alpha']
    def member():
        groups=target.http(target.keycloak+'/admin/realms/'+tenant['realm']+'/users/'+tenant['user_id']+'/groups',
            token=target.token(tenant))
        return any(g['id']==tenant['group_id'] for g in groups)
    before=member()
    result=subprocess.run(['node',str(ROOT/'mcp-server/test/connected.mjs')],
        input=json.dumps({'mode':'lab','stage':'approved','origin':'http://127.0.0.1:5681',
            'staff':config['tokens']['alpha']['staff'],'case_id':state['id']}),
        text=True,capture_output=True,timeout=45)
    if result.returncode:raise RuntimeError('execution_or_verification_requires_review')
    receipt=json.loads(result.stdout);after=member();final=store.get('alpha',state['id'])
    if not after or final['status']!='closed' or final['action']['id']!=receipt['operation_id']:raise RuntimeError()
    evidence={'status':'passed','checked_at':datetime.now(timezone.utc).isoformat(),
        'case_id':state['id'],'jira_issue':'IT-1','source_rechecked_at':ticket.observed_at.isoformat(),
        'source_snapshot_unchanged':True,'approver':approval['approver_id'],
        'approved_at':approval['approved_at'],'approval_expires_at':approval['expires_at'],
        'path':'Human browser approval -> MCP -> HTTP API -> PostgreSQL -> Keycloak read-back',
        'tenant':'alpha','realm':tenant['realm'],'requester':tenant['requester'],'group':'reports-reader',
        'membership_before':before,'membership_after':after,'operation_id':receipt['operation_id'],
        'case_status':final['status'],'verified':final['verified']['matches'],
        'dispatch_reservations':sum(e['event']=='dispatch_reserved' for e in final['audit']),
        'human_token_used_by_script':False,'jira_writes':0,'credentials_printed':False,
        'jira_credentials_loaded_internally':True,
        'limitations':['Jira summary/status snapshot checked before dispatch, not an atomic cross-system lock',
                       'Local case closed; Jira ticket status unchanged; Phase 5 gate remains open']}
    save(ROOT/'docs/phase-5/human-approved-access.json',evidence)
    report.update(status='local_case_closed',human_approval_recorded=True,target_dispatched=True,
                  verified=True,operation_id=receipt['operation_id'],jira_writes=0)
    save(REPORT,report)
    print(json.dumps(evidence))

if __name__=='__main__':
    try:run()
    except Exception as exc:
        print('Execution stopped: '+type(exc).__name__+'. No automatic retry; inspect stored state safely before continuing.')
        sys.exit(1)
