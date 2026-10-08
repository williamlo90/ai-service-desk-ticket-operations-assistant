"""Parameterized SQL adapters with transaction-scoped tenant context.

Connection factory must return a fresh psycopg3 connection with autocommit=False,
default tuple rows and READ COMMITTED isolation. No connection opens on import.
"""
from dataclasses import asdict
from datetime import datetime,timezone
from uuid import uuid4
import json
from .cases import Case,CaseError,Intake
from .store import Conflict,Missing


def _scope(conn,tenant):
    conn.execute("SELECT set_config('app.tenant_id', %s, true)",(tenant,))


def _decode(value):
    return json.loads(value) if isinstance(value,str) else value


class PostgresCaseRepository:
    def __init__(self,connect):self.connect=connect

    @staticmethod
    def _case(tenant,row):
        key,actor,intake,created=row
        return Case(str(key),tenant,actor,Intake(**_decode(intake)),
                    created.isoformat() if isinstance(created,datetime) else created)

    def create(self,actor,key,intake):
        case_id=str(uuid4());now=datetime.now(timezone.utc)
        with self.connect() as conn:
            _scope(conn,actor.tenant_id)
            row=conn.execute('''INSERT INTO sd_case_intake
                (tenant_id,case_id,actor_id,idempotency_key,intake,created_at)
                VALUES (%s,%s,%s,%s,%s::jsonb,%s)
                ON CONFLICT (tenant_id,actor_id,idempotency_key) DO NOTHING
                RETURNING case_id,actor_id,intake,created_at''',
                (actor.tenant_id,case_id,actor.actor_id,key,json.dumps(asdict(intake)),now)).fetchone()
            created=row is not None
            if not created:
                row=conn.execute('''SELECT case_id,actor_id,intake,created_at FROM sd_case_intake
                    WHERE tenant_id=%s AND actor_id=%s AND idempotency_key=%s''',
                    (actor.tenant_id,actor.actor_id,key)).fetchone()
                if row is None:raise Conflict()
            case=self._case(actor.tenant_id,row)
            if case.intake!=intake:raise CaseError('idempotency_conflict')
            return case,created

    def get(self,tenant_id,case_id):
        with self.connect() as conn:
            _scope(conn,tenant_id)
            row=conn.execute('''SELECT case_id,actor_id,intake,created_at FROM sd_case_intake
                WHERE tenant_id=%s AND case_id=%s''',(tenant_id,case_id)).fetchone()
            return self._case(tenant_id,row) if row else None


class PostgresStateStore:
    def __init__(self,connect):self.connect=connect

    @staticmethod
    def _audit(conn,tenant,key,event):
        conn.execute('INSERT INTO sd_audit (tenant_id,case_id,sequence,event) VALUES (%s,%s,%s,%s::jsonb)',
                     (tenant,key,event['sequence'],json.dumps(event,allow_nan=False)))

    def create(self,tenant,key,state):
        if (state['tenant'],state['id'],state['revision'])!=(tenant,key,1) or len(state['audit'])!=1:
            raise ValueError('Invalid initial state.')
        with self.connect() as conn:
            _scope(conn,tenant)
            row=conn.execute('''INSERT INTO sd_journey (tenant_id,case_id,revision,state)
                VALUES (%s,%s,1,%s::jsonb) ON CONFLICT DO NOTHING RETURNING case_id''',
                (tenant,key,json.dumps(state,allow_nan=False))).fetchone()
            if row is None:raise Conflict()
            self._audit(conn,tenant,key,state['audit'][0])

    def get(self,tenant,key):
        with self.connect() as conn:
            _scope(conn,tenant)
            row=conn.execute('SELECT state FROM sd_journey WHERE tenant_id=%s AND case_id=%s',
                             (tenant,key)).fetchone()
            if row is None:raise Missing()
            return _decode(row[0])

    def save(self,tenant,key,expected_revision,state):
        with self.connect() as conn:
            _scope(conn,tenant)
            row=conn.execute('SELECT state FROM sd_journey WHERE tenant_id=%s AND case_id=%s FOR UPDATE',
                             (tenant,key)).fetchone()
            if row is None:raise Missing()
            old=_decode(row[0])
            if old['revision']!=expected_revision:raise Conflict()
            if ((state['tenant'],state['id'],state['revision'])!=(tenant,key,expected_revision+1)
                    or state['audit'][:-1]!=old['audit']
                    or state['audit'][-1]['sequence']!=state['revision']):
                raise ValueError('Invalid aggregate update.')
            result=conn.execute('''UPDATE sd_journey SET revision=%s,state=%s::jsonb
                WHERE tenant_id=%s AND case_id=%s AND revision=%s RETURNING case_id''',
                (state['revision'],json.dumps(state,allow_nan=False),tenant,key,expected_revision)).fetchone()
            if result is None:raise Conflict()
            self._audit(conn,tenant,key,state['audit'][-1])

    def list(self,tenant):
        with self.connect() as conn:
            _scope(conn,tenant)
            return [_decode(row[0]) for row in conn.execute(
                'SELECT state FROM sd_journey WHERE tenant_id=%s ORDER BY case_id',(tenant,)).fetchall()]
