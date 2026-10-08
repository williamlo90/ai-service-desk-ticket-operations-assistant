"""Allowlisted adapters for the dedicated Keycloak/demo lab, never production.

Opaque credentials are supplied by trusted process configuration. Local SQLite
reserves operation IDs before HTTP writes; independent target read-back determines
the observed outcome after a lost reply. No blind mutation replay.
"""
from contextlib import closing
from pathlib import Path
import json,sqlite3
from urllib.parse import urlencode
from urllib.request import Request,build_opener
from urllib.error import HTTPError,URLError
from .durable_target import DurableSyntheticTarget
from .http_retry import NoRedirect


class LabTargetError(Exception):pass
class LabTargetUnavailable(ConnectionError):pass


class LabTargets:
    def __init__(self,path,tenants,keycloak='http://127.0.0.1:8085',demo='http://127.0.0.1:8086'):
        if keycloak not in ('http://127.0.0.1:8085','http://keycloak:8080'):raise ValueError('Unapproved lab origin')
        if demo not in ('http://127.0.0.1:8086','http://demo:8080'):raise ValueError('Unapproved lab origin')
        if set(tenants)!={'alpha','beta'}:raise ValueError('Lab tenants required')
        self.path=str(Path(path));self.tenants=tenants;self.keycloak=keycloak;self.demo=demo
        for tenant,c in tenants.items():
            if c['realm']!='sd-lab-'+tenant:raise ValueError('Realm mismatch')
        with closing(self.connect()) as conn,conn:
            conn.execute('CREATE TABLE IF NOT EXISTS operation (tenant text,id text,payload text,applied integer,PRIMARY KEY(tenant,id))')
    def connect(self):return sqlite3.connect(self.path,timeout=5)
    def http(self,url,method='GET',data=None,token=None,form=False):
        headers={};raw=None
        if token:headers['Authorization']='Bearer '+token
        if data is not None:
            raw=urlencode(data).encode() if form else json.dumps(data).encode()
            headers['Content-Type']='application/x-www-form-urlencoded' if form else 'application/json'
        try:
            with build_opener(NoRedirect()).open(Request(url,data=raw,method=method,headers=headers),timeout=10) as response:
                body=response.read(1048577)
                if len(body)>1048576:raise LabTargetError('response_limit')
                return json.loads(body) if body else None
        except HTTPError as exc:
            if exc.code in (408,429,502,503,504):raise LabTargetUnavailable('lab_target_temporarily_unavailable') from None
            raise LabTargetError('lab_target_request_rejected') from None
        except (URLError,TimeoutError,ConnectionError):raise LabTargetUnavailable('lab_target_unreachable') from None
        except Exception:raise LabTargetError('lab_target_request_failed') from None
    def token(self,c):
        return self.http(self.keycloak+'/realms/'+c['realm']+'/protocol/openid-connect/token','POST',{
            'grant_type':'client_credentials','client_id':c['client_id'],'client_secret':c['client_secret']},form=True)['access_token']
    def validate(self,tenant,payload):
        encoded=DurableSyntheticTarget.encoded(tenant,payload)
        c=self.tenants.get(tenant)
        if not c or payload['requester']!=c['requester'] or payload['action'] not in ('grant_read_access','restart_service'):
            raise LabTargetError('lab_action_not_allowlisted')
        return c,encoded
    def submit(self,tenant,operation_id,payload):
        c,encoded=self.validate(tenant,payload)
        with closing(self.connect()) as conn,conn:
            conn.execute('BEGIN IMMEDIATE')
            row=conn.execute('SELECT payload FROM operation WHERE tenant=? AND id=?',(tenant,operation_id)).fetchone()
            if row:
                if row[0]!=encoded:raise LabTargetError('operation_conflict')
                return {'status':'unknown','sequence':1}
            conn.execute('INSERT INTO operation VALUES (?,?,?,0)',(tenant,operation_id,encoded))
        if payload['action']=='grant_read_access':
            self.http(self.keycloak+'/admin/realms/'+c['realm']+'/users/'+c['user_id']+'/groups/'+c['group_id'],
                      'PUT',token=self.token(c))
        else:
            self.http(self.demo+'/v1/'+tenant+'/restart','POST',{'operation_id':operation_id},c['control_token'])
        with closing(self.connect()) as conn,conn:
            conn.execute('UPDATE operation SET applied=1 WHERE tenant=? AND id=?',(tenant,operation_id))
        return {'status':'accepted','sequence':1}
    def inspect(self,tenant,operation_id,payload):
        c,encoded=self.validate(tenant,payload)
        with closing(self.connect()) as conn:
            row=conn.execute('SELECT payload,applied FROM operation WHERE tenant=? AND id=?',(tenant,operation_id)).fetchone()
        if not row:return {'status':'unknown','sequence':0,'matches':False}
        if row[0]!=encoded:raise LabTargetError('operation_conflict')
        if payload['action']=='grant_read_access':
            groups=self.http(self.keycloak+'/admin/realms/'+c['realm']+'/users/'+c['user_id']+'/groups',token=self.token(c))
            matches=any(g['id']==c['group_id'] for g in groups)
            return {'status':'succeeded' if matches or row[1] else 'unknown','sequence':2 if matches or row[1] else 1,'matches':matches}
        observed=self.http(self.demo+'/v1/'+tenant+'/operations/'+operation_id,token=c['control_token'])
        return {'status':observed['status'],'sequence':2 if observed['status']=='succeeded' else 1,'matches':observed['matches']}
