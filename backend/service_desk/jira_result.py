"""Operation-scoped Jira result property; bounded writes with read-back reconciliation."""
import base64,json,sqlite3
from contextlib import closing
from urllib.request import Request,build_opener
from urllib.error import HTTPError
from uuid import UUID
from .jira import NoRedirect,MAX_BYTES
from .contracts import Role,require_staff,AccessDenied

class ResultWriteError(Exception):pass

def request(url,authorization,method,value=None):
    body=None if value is None else json.dumps(value,sort_keys=True).encode()
    req=Request(url,data=body,method=method,headers={'Authorization':authorization,
        'Content-Type':'application/json','Accept':'application/json'})
    try:
        with build_opener(NoRedirect()).open(req,timeout=20) as response:
            raw=response.read(MAX_BYTES+1)
            if len(raw)>MAX_BYTES:raise ResultWriteError('response_limit')
            return response.status,json.loads(raw) if raw else None
    except HTTPError as exc:
        code=exc.code;exc.close();return code,None
    except Exception:raise ResultWriteError('transport_or_response_unknown') from None

class JiraResultWriter:
    def __init__(self,connection,journal,transport=request):
        self.connection,self.journal,self.transport=connection,str(journal),transport
        with closing(sqlite3.connect(self.journal)) as conn,conn:
            conn.execute('CREATE TABLE IF NOT EXISTS result_write (identity TEXT PRIMARY KEY,payload TEXT NOT NULL)')

    def publish(self,actor,issue,operation,value):
        c=self.connection;require_staff(actor,c.tenant_id)
        if actor.role not in (Role.SPECIALIST,Role.SUPERVISOR):raise AccessDenied()
        # The first live write is deliberately restricted to the approved lab ticket.
        if c.project_key!='IT' or issue!='IT-1':raise ResultWriteError('issue_out_of_scope')
        if str(UUID(operation))!=operation:raise ResultWriteError('invalid_operation')
        encoded=json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)
        if len(encoded.encode())>4096:raise ResultWriteError('payload_limit')
        key='service-desk.lab.result.'+operation
        identity=json.dumps([c.tenant_id,c.cloud_id,issue,key])
        url=c.api_base+f'issue/{issue}/properties/{key}'
        auth='Basic '+base64.b64encode(f'{c.email}:{c.api_token}'.encode()).decode()
        def read():
            status,body=self.transport(url,auth,'GET')
            if status==404:return None
            if status!=200:raise ResultWriteError('read_http_'+str(status))
            if not isinstance(body,dict) or body.get('key')!=key:raise ResultWriteError('invalid_readback')
            return body.get('value')
        observed=read()
        if observed is not None:
            if observed!=value:raise ResultWriteError('property_conflict')
            return {'property_key':key,'verified':True,'write_attempted':False}
        with closing(sqlite3.connect(self.journal)) as conn,conn:
            conn.execute('BEGIN IMMEDIATE')
            old=conn.execute('SELECT payload FROM result_write WHERE identity=?',(identity,)).fetchone()
            if old:raise ResultWriteError('reserved_outcome_requires_review')
            conn.execute('INSERT INTO result_write VALUES (?,?)',(identity,encoded))
        try:status,_=self.transport(url,auth,'PUT',value)
        except ResultWriteError:status=0
        if status in (401,403):
            # A definite authorization rejection did not apply this write. Permit
            # a later explicit run after credentials are fixed, never retry here.
            with closing(sqlite3.connect(self.journal)) as conn,conn:
                conn.execute('DELETE FROM result_write WHERE identity=? AND payload=?',(identity,encoded))
        if status not in (0,200,201):raise ResultWriteError('write_http_'+str(status))
        if read()!=value:raise ResultWriteError('write_not_verified')
        return {'property_key':key,'verified':True,'write_attempted':True}
