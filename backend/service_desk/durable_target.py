"""Durable synthetic target, independent of the application's PostgreSQL state.

SQLite records synthetic effects only. No entitlement/service integration, and no
target mutation endpoint is exposed to the assistant. Operator/test fixture only.
"""
from contextlib import closing
import json
from pathlib import Path
import sqlite3


class DurableSyntheticTarget:
    def __init__(self,path):
        self.path=str(Path(path).resolve())
        with closing(self.connect()) as conn,conn:
            conn.execute('''CREATE TABLE IF NOT EXISTS operations (
                tenant text NOT NULL, operation text NOT NULL, payload text NOT NULL,
                status text NOT NULL, sequence integer NOT NULL, matches integer NOT NULL,
                PRIMARY KEY (tenant,operation))''')
            conn.execute('''CREATE TABLE IF NOT EXISTS effect_ledger (
                tenant text NOT NULL, operation text NOT NULL, payload text NOT NULL,
                PRIMARY KEY (tenant,operation))''')

    def connect(self):return sqlite3.connect(self.path,timeout=3)

    @staticmethod
    def encoded(tenant,payload):
        base={'action','tenant','requester'}
        expected={'grant_read_access':{'resource':'reports','access':'read-only'},
                  'restart_service':{'service':'demo-api'},
                  'link_tickets':{'source':'SD-2','related':'SD-1'}}.get(payload.get('action'))
        if (expected is None or set(payload)!=base|set(expected) or payload.get('tenant')!=tenant
                or not isinstance(payload.get('requester'),str)
                or any(payload.get(k)!=v for k,v in expected.items())):
            raise ValueError('Synthetic payload rejected.')
        return json.dumps(payload,sort_keys=True,separators=(',',':'))

    def submit(self,tenant,operation_id,payload):
        encoded=self.encoded(tenant,payload)
        with closing(self.connect()) as conn,conn:
            conn.execute('BEGIN IMMEDIATE')
            previous=conn.execute('SELECT payload FROM operations WHERE tenant=? AND operation=?',
                                  (tenant,operation_id)).fetchone()
            if previous:
                if previous[0]!=encoded:raise ValueError('Operation conflict.')
            else:
                conn.execute('INSERT INTO operations VALUES (?,?,?,\'succeeded\',2,1)',(tenant,operation_id,encoded))
                conn.execute('INSERT INTO effect_ledger VALUES (?,?,?)',(tenant,operation_id,encoded))
        # Receipt deliberately does not establish successful outcome to the caller.
        return {'status':'accepted','sequence':1}

    def inspect(self,tenant,operation_id,payload):
        encoded=self.encoded(tenant,payload)
        with closing(self.connect()) as conn:
            row=conn.execute('SELECT payload,status,sequence,matches FROM operations WHERE tenant=? AND operation=?',
                             (tenant,operation_id)).fetchone()
        if not row:return {'status':'unknown','sequence':0,'matches':False}
        return {'status':row[1],'sequence':row[2],'matches':row[0]==encoded and bool(row[3])}

    def revoke(self,tenant,operation_id):
        # Operator-side synthetic fault injection; never registered as an MCP tool.
        with closing(self.connect()) as conn,conn:
            conn.execute('UPDATE operations SET matches=0,sequence=sequence+1 WHERE tenant=? AND operation=?',(tenant,operation_id))

    def ledger(self):
        with closing(self.connect()) as conn:
            return [{'tenant':t,'operation_id':o,'payload':json.loads(p)} for t,o,p in
                    conn.execute('SELECT tenant,operation,payload FROM effect_ledger ORDER BY tenant,operation')]
