"""Same-project lab ticket links with bound approvals and authoritative read-back."""
import base64,json,sqlite3
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime,timezone
from hashlib import sha256
from uuid import uuid5,NAMESPACE_URL
from .jira import JiraReader
from .jira_result import request,ResultWriteError
from .policy import writer
from .lifecycle import Proposal,require_current_approval

class LinkBlocked(Exception):pass

@dataclass(frozen=True)
class LinkPlan:
    tenant:str
    cloud_id:str
    source:str
    related:str
    type_id:str
    source_summary:str
    related_summary:str
    source_status:str
    related_status:str
    def proposal(self):
        digest=sha256(json.dumps(self.__dict__,sort_keys=True).encode()).hexdigest()
        key=str(uuid5(NAMESPACE_URL,self.cloud_id+':'+digest))
        return Proposal(self.tenant,key,1,digest,'jira-relates-v1','phase5-lab-requester')

class JiraLinks:
    def __init__(self,connection,journal,reader=None,transport=request,clock=None):
        self.c=connection;self.journal=str(journal);self.reader=reader or JiraReader(connection)
        self.transport=transport;self.clock=clock or (lambda:datetime.now(timezone.utc))
        with closing(sqlite3.connect(self.journal)) as conn,conn:
            conn.execute('CREATE TABLE IF NOT EXISTS link_attempt (operation TEXT PRIMARY KEY,payload TEXT NOT NULL)')
    def call(self,path,method='GET',body=None):
        auth='Basic '+base64.b64encode(f'{self.c.email}:{self.c.api_token}'.encode()).decode()
        return self.transport(self.c.api_base+path,auth,method,body)
    def scope(self,actor,source,related):
        writer(actor,self.c.tenant_id)
        if self.c.project_key!='IT' or {source,related}!={'IT-1','IT-2'}:raise LinkBlocked('lab_pair_required')
    def prepare(self,actor,source='IT-2',related='IT-1'):
        self.scope(actor,source,related)
        a=self.reader.read(actor,source);b=self.reader.read(actor,related)
        if not all(t.summary.startswith('[TEST]') for t in (a,b)):raise LinkBlocked('test_tickets_required')
        status,data=self.call('issueLinkType')
        if status!=200:raise LinkBlocked('types_http_'+str(status))
        types=[t for t in data.get('issueLinkTypes',[]) if t.get('name','').casefold() in ('relates','relates to')]
        if len(types)!=1 or not str(types[0]['id']).isdigit():raise LinkBlocked('relates_type_required')
        return LinkPlan(actor.tenant_id,self.c.cloud_id,source,related,str(types[0]['id']),a.summary,b.summary,a.source_status,b.source_status)
    def inspect(self,actor,plan):
        self.scope(actor,plan.source,plan.related)
        if plan.cloud_id!=self.c.cloud_id or plan.tenant!=self.c.tenant_id:raise LinkBlocked('scope_mismatch')
        status,data=self.call('issue/'+plan.source+'?fields=issuelinks,project')
        if status!=200:raise LinkBlocked('read_http_'+str(status))
        if data.get('key')!=plan.source or data['fields']['project']['key']!='IT':raise LinkBlocked('invalid_readback')
        links=[link for link in data['fields'].get('issuelinks',[]) if str(link.get('type',{}).get('id'))==plan.type_id
            and any(link.get(direction,{}).get('key')==plan.related for direction in ('inwardIssue','outwardIssue'))]
        if len(links)>1:raise LinkBlocked('duplicate_links_review')
        return {'matches':len(links)==1,'link_id':str(links[0]['id']) if links else None}
    def execute(self,actor,plan,approval):
        self.scope(actor,plan.source,plan.related)
        if plan.cloud_id!=self.c.cloud_id or plan.tenant!=self.c.tenant_id:raise LinkBlocked('scope_mismatch')
        require_current_approval(approval,plan.proposal(),self.clock())
        a=self.reader.read(actor,plan.source);b=self.reader.read(actor,plan.related)
        if (a.summary,b.summary,a.source_status,b.source_status)!=(plan.source_summary,plan.related_summary,plan.source_status,plan.related_status):raise LinkBlocked('source_changed')
        current=self.inspect(actor,plan)
        if current['matches']:return {**current,'write_attempted':False}
        operation=plan.proposal().case_id;encoded=json.dumps(plan.__dict__,sort_keys=True)
        with closing(sqlite3.connect(self.journal)) as conn,conn:
            conn.execute('BEGIN IMMEDIATE')
            if conn.execute('SELECT 1 FROM link_attempt WHERE operation=?',(operation,)).fetchone():raise LinkBlocked('unknown_requires_review')
            conn.execute('INSERT INTO link_attempt VALUES (?,?)',(operation,encoded))
        try:
            status,_=self.call('issueLink','POST',{'type':{'id':plan.type_id},
                'inwardIssue':{'key':plan.source},'outwardIssue':{'key':plan.related}})
        except ResultWriteError:status=0
        if status in (401,403):
            with closing(sqlite3.connect(self.journal)) as conn,conn:conn.execute('DELETE FROM link_attempt WHERE operation=?',(operation,))
        if status not in (0,201):raise LinkBlocked('write_http_'+str(status))
        observed=self.inspect(actor,plan)
        if not observed['matches']:raise LinkBlocked('outcome_unknown')
        return {**observed,'write_attempted':True}
