"""Publish the verified IT-1 lab outcome as operation-specific Jira metadata."""
import json,sys
from datetime import datetime,timezone
from operator_lab import CONFIG,REPORT,ROOT,save

def run():
    import psycopg
    from check_jira_read import load_config,CLOUD_ID,SITE_URL
    from service_desk.jira import JiraConnection,JiraReader
    from service_desk.jira_result import JiraResultWriter,ResultWriteError
    from service_desk.contracts import Actor,Role
    from service_desk.postgres import PostgresStateStore
    from service_desk.journeys import JourneyService
    from service_desk.lab_targets import LabTargets
    evidence={'checked_at':datetime.now(timezone.utc).isoformat(),'issue':'IT-1',
        'status':'failed','credentials_printed':False,'jira_credentials_loaded_internally':True,
        'ticket_status_changed':False,'comments_sent':0}
    try:
        config=json.loads(CONFIG.read_text());report=json.loads(REPORT.read_text());jira=load_config()
        if (jira.get('JIRA_CLOUD_ID')!=CLOUD_ID or jira.get('JIRA_PROJECT_KEY')!='IT'
                or jira.get('JIRA_TEST_ISSUE_KEY')!='IT-1'):raise ValueError()
        connection=JiraConnection('alpha',CLOUD_ID,'IT',jira['JIRA_EMAIL'],jira['JIRA_API_TOKEN'],site_url=SITE_URL)
        actor=Actor('lab-integration-alpha','alpha',Role.SPECIALIST)
        target=LabTargets(config['target_path'],config['lab_tenants'])
        store=PostgresStateStore(lambda:psycopg.connect(**config['database']))
        ticket=JiraReader(connection).read(actor,'IT-1')
        state=JourneyService(store,target).import_ticket(actor,ticket,CLOUD_ID,config['lab_tenants']['alpha']['requester'])
        if (state['id']!=report['case_id'] or state['status']!='closed' or not state['verified']['matches']
                or state['approval']['approver_id']!='William'):raise ValueError()
        observed=target.inspect('alpha',state['action']['id'],state['proposal']['payload'])
        if not observed['matches'] or observed['status']!='succeeded':raise ValueError()
        value={'schema':1,'environment':'local-lab','tenant':'alpha','case_id':state['id'],
            'operation_id':state['action']['id'],'action':'grant_read_access','resource':'reports',
            'result':'verified','local_case_status':'closed','closed_at':state['closed_at'],
            'jira_resolution_changed':False}
        writer=JiraResultWriter(connection,ROOT/'local/operator-lab/jira-result.sqlite')
        evidence.update(operation_id=state['action']['id'],payload=value)
        result=writer.publish(actor,'IT-1',state['action']['id'],value)
        # A fresh writer instance must read the same property without issuing another PUT.
        replay=JiraResultWriter(connection,ROOT/'local/operator-lab/jira-result.sqlite').publish(actor,'IT-1',state['action']['id'],value)
        if replay['write_attempted']:raise RuntimeError()
        evidence.update(status='passed',**result,replay_without_write=True,payload=value,
            limitation='Operation property is not a Jira resolution transition or cross-system transaction')
        report.update(jira_result_property=result['property_key'],jira_result_verified=True,jira_writes=1)
        save(REPORT,report)
    except ResultWriteError as exc:evidence['error']=str(exc)
    except Exception as exc:evidence['error']=type(exc).__name__
    save(ROOT/'docs/phase-5/jira-result-write.json',evidence)
    print(json.dumps(evidence));return 0 if evidence['status']=='passed' else 1

if __name__=='__main__':sys.exit(run())
