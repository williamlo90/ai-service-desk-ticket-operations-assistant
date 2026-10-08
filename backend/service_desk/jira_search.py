"""Bounded, allowlisted enhanced Jira search. No arbitrary JQL or tenant from input."""
import base64,re
from datetime import datetime,timezone
from urllib.parse import urlencode
from .contracts import Ticket,require_staff
from .jira_result import request,ResultWriteError

class SearchBlocked(Exception):pass

class JiraSearch:
    def __init__(self,connection,keys,transport=request):
        if not 1<=len(keys)<=20 or len(set(keys))!=len(keys):raise ValueError('scope_limit')
        if any(not re.fullmatch(re.escape(connection.project_key)+r'-[1-9][0-9]{0,11}',k) for k in keys):raise ValueError('scope_rejected')
        self.connection,self.keys,self.transport=connection,tuple(sorted(keys)),transport

    def pages(self,actor,page_size=10,max_pages=10):
        c=self.connection;require_staff(actor,c.tenant_id)
        if type(page_size) is not int or not 1<=page_size<=20 or type(max_pages) is not int or not 1<=max_pages<=20:raise ValueError()
        auth='Basic '+base64.b64encode(f'{c.email}:{c.api_token}'.encode()).decode()
        cursor=None;seen_cursors=set();seen_keys=set()
        for _ in range(max_pages):
            params={'jql':f'project = {c.project_key} AND key IN ({",".join(self.keys)}) ORDER BY key',
                'maxResults':page_size,'fields':'summary,status,project'}
            if cursor:params['nextPageToken']=cursor
            url=c.api_base+'search/jql?'+urlencode(params)
            status,body=self.transport(url,auth,'GET')
            if status!=200:raise SearchBlocked('http_'+str(status))
            if not isinstance(body,dict) or not isinstance(body.get('issues'),list) or len(body['issues'])>page_size:raise SearchBlocked('invalid_page')
            tickets=[]
            for item in body['issues']:
                try:
                    key=item['key'];fields=item['fields'];summary=fields['summary'];state=fields['status']['name']
                    if key not in self.keys or fields['project']['key']!=c.project_key:raise ValueError()
                    if not isinstance(summary,str) or not 1<=len(summary)<=1000 or not isinstance(state,str) or not 1<=len(state)<=100:raise ValueError()
                    for secret in (c.email,c.api_token,auth.removeprefix('Basic ')):
                        if secret in summary+state:raise ValueError()
                    if key in seen_keys:raise SearchBlocked('duplicate_key_review')
                    seen_keys.add(key)
                    tickets.append(Ticket(c.tenant_id,key,c.project_key,summary,state,datetime.now(timezone.utc)))
                except SearchBlocked:raise
                except Exception:raise SearchBlocked('out_of_scope_or_invalid_issue') from None
            yield tickets
            if body.get('isLast') is True:return
            cursor=body.get('nextPageToken')
            if not isinstance(cursor,str) or not 1<=len(cursor)<=4096 or cursor in seen_cursors:raise SearchBlocked('invalid_cursor')
            seen_cursors.add(cursor)
        raise SearchBlocked('page_budget_exhausted')

def sync(service,actor,search,requester,page_size=10):
    results=[]
    for tickets in search.pages(actor,page_size):
        for ticket in tickets:
            if not ticket.summary.startswith('[TEST]'):raise SearchBlocked('non_test_issue')
            from .journeys import JourneyBlocked
            try:
                state=service.import_ticket(actor,ticket,search.connection.cloud_id,requester)
                results.append({'key':ticket.key,'case_id':state['id'],'status':'synchronized'})
            except JourneyBlocked as exc:
                if str(exc)!='source_changed_review_required':raise
                # Keep the approved snapshot intact; source drift needs explicit review.
                results.append({'key':ticket.key,'status':'source_changed_review_required'})
    return results
