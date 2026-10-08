"""Bounded live IT-1/IT-2 link + search/sync acceptance; secrets never printed.

Creates one explicit [TEST] issue if IT-2 is absent. Never sends comments or
transitions a Jira status. Link approval uses a labeled technical fixture.
"""
import base64,json,sys
from datetime import datetime,timedelta,timezone
from operator_lab import CONFIG,ROOT,save

def run():
    import psycopg
    from check_jira_read import load_config,CLOUD_ID,SITE_URL
    from service_desk.jira import JiraConnection,JiraReader,JiraReadError
    from service_desk.jira_result import request
    from service_desk.jira_search import JiraSearch,sync
    from service_desk.jira_links import JiraLinks
    from service_desk.contracts import Actor,Role
    from service_desk.lifecycle import approve
    from service_desk.journeys import JourneyService
    from service_desk.postgres import PostgresStateStore
    from service_desk.lab_targets import LabTargets
    report={'status':'failed','checked_at':datetime.now(timezone.utc).isoformat(),
        'credentials_printed':False,'comments_sent':0,'jira_status_transitions':0}
    stage='configuration'
    try:
        config=json.loads(CONFIG.read_text());c=load_config()
        if c.get('JIRA_CLOUD_ID')!=CLOUD_ID or c.get('JIRA_PROJECT_KEY')!='IT' or c.get('JIRA_TEST_ISSUE_KEY')!='IT-1':raise ValueError()
        connection=JiraConnection('alpha',CLOUD_ID,'IT',c['JIRA_EMAIL'],c['JIRA_API_TOKEN'],site_url=SITE_URL)
        actor=Actor('phase5-link-fixture-staff','alpha',Role.SPECIALIST)
        base=connection.api_base
        auth='Basic '+base64.b64encode((c['JIRA_EMAIL']+':'+c['JIRA_API_TOKEN']).encode()).decode()
        def call(path,method='GET',body=None):return request(base+path,auth,method,body)
        stage='read_preflight'
        reader=JiraReader(connection);reader.read(actor,'IT-1')
        status,_=call('issueLinkType');report['link_types_http']=status
        if status!=200:raise ValueError()
        search=JiraSearch(connection,['IT-1','IT-2'])
        list(search.pages(actor,1))
        title='[TEST] Related reports access verification'
        stage='second_test_ticket'
        try:
            ticket=reader.read(actor,'IT-2')
            if ticket.summary!=title:raise ValueError('unexpected_second_ticket')
        except JiraReadError as exc:
            if exc.http_status!=404:raise
            reserve=ROOT/'local/operator-lab/jira-create-fixture.json'
            if reserve.exists():raise ValueError('prior_create_requires_review')
            status,data=call('issue/createmeta/IT/issuetypes?maxResults=50')
            if status!=200:report['create_metadata_http']=status;raise ValueError()
            types=data.get('issueTypes',[])
            candidates=[t for t in types if not t.get('subtask') and t.get('name','').casefold() in ('task','service request','[system] service request')]
            if not candidates:raise ValueError('supported_type_missing')
            chosen=sorted(candidates,key=lambda t:(t['name'].casefold()!='task',t['name']))[0]
            save(reserve,{'attempted':True,'expected_summary':title})
            status,data=call('issue','POST',{'fields':{'project':{'key':'IT'},'issuetype':{'id':chosen['id']},
                'summary':title,'labels':['service-desk-phase5-fixture']}})
            report['create_http']=status
            if status in (401,403):reserve.unlink()
            if status!=201:raise ValueError('create_not_confirmed')
            created=data.get('key');report['created_issue']=created
            save(reserve,{'attempted':True,'created_issue':created})
            if created!='IT-2':raise ValueError('unexpected_created_key_review')
            ticket=reader.read(actor,'IT-2')
            if ticket.summary!=title:raise ValueError()
        stage='link_prepare'
        adapter=JiraLinks(connection,ROOT/'local/operator-lab/jira-links.sqlite')
        plan=adapter.prepare(actor)
        now=datetime.now(timezone.utc)
        approval=approve(Actor('phase5-link-fixture-supervisor','alpha',Role.SUPERVISOR),plan.proposal(),now,now+timedelta(minutes=5))
        stage='link_execute_readback'
        result=adapter.execute(actor,plan,approval)
        replay=adapter.execute(actor,plan,approval)
        if replay['write_attempted']:raise ValueError()
        report.update(link=result,link_replay_without_write=True,link_approval='technical fixture; not a William browser approval')
        previous_path=ROOT/'docs/phase-5/jira-connected-check.json'
        if previous_path.exists():
            previous=json.loads(previous_path.read_text())
            if previous.get('link',{}).get('link_id')==result['link_id']:
                report['prior_link_write_verified']=previous.get('prior_link_write_verified',False) or previous.get('link',{}).get('write_attempted',False)
        reserve=ROOT/'local/operator-lab/jira-create-fixture.json'
        if reserve.exists():report['created_issue']=json.loads(reserve.read_text()).get('created_issue')
        stage='pagination_sync'
        pages=list(search.pages(actor,1));keys=[t.key for page in pages for t in page]
        if set(keys)!={'IT-1','IT-2'} or len(pages)!=2:raise ValueError('two_pages_not_visible_yet')
        service=JourneyService(PostgresStateStore(lambda:psycopg.connect(**config['database'])),
            LabTargets(config['target_path'],config['lab_tenants']))
        results=sync(service,actor,search,config['lab_tenants']['alpha']['requester'],1)
        again=sync(service,actor,search,config['lab_tenants']['alpha']['requester'],1)
        if results!=again or any(r['status']!='synchronized' for r in results):raise ValueError('sync_review_required')
        report.update(search_pages=len(pages),synchronized_keys=keys,import_replay_same_cases=True)
        stage='negative_authentication'
        invalid='Basic '+base64.b64encode((c['JIRA_EMAIL']+':invalid-phase5-negative-token').encode()).decode()
        status,body=request(base+'issue/IT-1?fields=summary',invalid,'GET')
        if status not in (401,403,404) or (isinstance(body,dict) and body.get('key')=='IT-1'):raise ValueError('invalid_token_not_denied')
        report.update(invalid_token_http=status,status='passed',stage='complete',
            invalid_token_issue_data_returned=False,
            rate_limit_evidence='controlled adapter tests only; no deliberate live SaaS throttling',
            polling_transport='outbound authenticated HTTPS; no Jira webhook receiver deployed')
    except Exception as exc:report.update(stage=stage,error=type(exc).__name__)
    save(ROOT/'docs/phase-5/jira-connected-check.json',report);print(json.dumps(report,indent=2))
    return 0 if report['status']=='passed' else 1

if __name__=='__main__':sys.exit(run())
