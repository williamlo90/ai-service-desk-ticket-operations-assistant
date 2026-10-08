from copy import deepcopy
from datetime import datetime,timedelta,timezone
import hashlib,hmac,json
from pathlib import Path
import unittest
from service_desk.contracts import Actor,Role
from service_desk.cases import Intake,CaseError
from service_desk.postgres import PostgresCaseRepository,PostgresStateStore
from service_desk.migrations import migrate
from service_desk.store import Conflict,MemoryStateStore
from service_desk.events import CallbackVerifier,CallbackHandler,EventRejected
from service_desk.jira import JiraConnection,JiraReader
from service_desk.jira_update import JiraSummaryAdapter,UpdateBlocked,map_ticket
from service_desk.lifecycle import approve,LifecycleBlocked
from service_desk.journeys import JourneyService
from service_desk.simulator import SimulatedTarget


class Cursor:
    def __init__(self,value):self.value=value
    def fetchone(self):return self.value
    def fetchall(self):return self.value


class Connection:
    """Scripted DB-API spy, deliberately not an SQL/database emulator."""
    def __init__(self,rows):self.rows=iter(rows);self.calls=[];self.rolled_back=False
    def __enter__(self):return self
    def __exit__(self,kind,*args):self.rolled_back=kind is not None
    def execute(self,sql,params=None):
        self.calls.append((sql,params))
        if 'set_config' in sql:return Cursor(None)
        return Cursor(next(self.rows))


class PostgresContractTests(unittest.TestCase):
    def test_intake_replay_conflict_rolls_back_and_uses_parameters(self):
        actor=Actor("staff';DROP TABLE x;--",'alpha',Role.SPECIALIST)
        intake=Intake('SYN-1','requester','summary','read-only','reports',True)
        row=('d8c04183-cda0-4bfb-9e98-37d428c7d9c2',actor.actor_id,deepcopy(intake.__dict__),'2026-10-08T00:00:00+00:00')
        conn=Connection([None,row]);repo=PostgresCaseRepository(lambda:conn)
        case,created=repo.create(actor,'key',intake)
        self.assertFalse(created);self.assertEqual(case.intake,intake)
        self.assertNotIn(actor.actor_id,conn.calls[1][0])
        self.assertIn(actor.actor_id,conn.calls[1][1])
        altered=Intake('SYN-1','requester','changed','read-only','reports',True)
        conn=Connection([None,row]);repo=PostgresCaseRepository(lambda:conn)
        with self.assertRaises(CaseError):repo.create(actor,'key',altered)
        self.assertTrue(conn.rolled_back)

    def test_state_update_audit_same_transaction_and_cas(self):
        old={'tenant':'alpha','id':'key','revision':1,'audit':[{'sequence':1}]}
        new={**old,'revision':2,'audit':old['audit']+[{'sequence':2}]}
        conn=Connection([(old,),('key',),None]);repo=PostgresStateStore(lambda:conn)
        repo.save('alpha','key',1,new)
        self.assertIn('FOR UPDATE',conn.calls[1][0])
        self.assertIn('AND revision=%s',conn.calls[2][0])
        self.assertIn('INSERT INTO sd_audit',conn.calls[3][0])
        self.assertFalse(conn.rolled_back)
        conn=Connection([(old,)]);repo=PostgresStateStore(lambda:conn)
        with self.assertRaises(Conflict):repo.save('alpha','key',0,new)
        self.assertTrue(conn.rolled_back)

    def test_migration_checksum_skip_and_changed_migration_rejected(self):
        sql=(Path(__file__).resolve().parents[1]/'migrations/001_service_desk.sql').read_text()
        checksum=hashlib.sha256(sql.encode()).hexdigest()
        conn=Connection([None,None,(checksum,)])
        migrate(lambda:conn)
        self.assertEqual(len(conn.calls),3)
        conn=Connection([None,None,('wrong',)])
        with self.assertRaises(ValueError):migrate(lambda:conn)
        self.assertTrue(conn.rolled_back)

    def test_schema_contains_tenant_foreign_key_and_uniqueness(self):
        sql=(Path(__file__).resolve().parents[1]/'migrations/001_service_desk.sql').read_text()
        for fragment in ['UNIQUE (tenant_id, actor_id, idempotency_key)',
                         'FOREIGN KEY (tenant_id, case_id)','FORCE ROW LEVEL SECURITY',
                         'BEFORE UPDATE OR DELETE','state->>\'tenant\' = tenant_id']:
            self.assertIn(fragment,sql)


class CallbackTests(unittest.TestCase):
    def test_signed_callback_validation(self):
        verifier=CallbackVerifier('alpha',b'x'*32)
        body=json.dumps({'tenant':'alpha','case_id':'case','operation_id':'op','sequence':2,'event_id':'e'}).encode()
        signature=hmac.new(b'x'*32,b'1000.'+body,hashlib.sha256).hexdigest()
        self.assertEqual(verifier.verify(body,'1000',signature,1000)['tenant'],'alpha')
        for payload,stamp,sig,now in [(body,'1000','wrong',1000),(body,'1000',signature,1301),
                                      (body+b' ','1000',signature,1000)]:
            with self.assertRaises(EventRejected):verifier.verify(payload,stamp,sig,now)

    def test_callback_reads_target_and_ignores_old_sequence(self):
        actor=Actor('staff','alpha',Role.SPECIALIST);lead=Actor('lead','alpha',Role.SUPERVISOR)
        target=SimulatedTarget();service=JourneyService(MemoryStateStore(),target)
        case=service.create(actor,'Grant reports read access');key=case['id']
        service.prepare(actor,key,1);service.approve(lead,key,1);state=service.execute(actor,key,1)
        handler=CallbackHandler(CallbackVerifier('alpha',b'x'*32),service,actor)
        data={'tenant':'alpha','case_id':key,'operation_id':state['action']['id'],'sequence':2,'event_id':'e'}
        body=json.dumps(data).encode();sig=hmac.new(b'x'*32,b'1000.'+body,hashlib.sha256).hexdigest()
        # Claimed sequence 2 while target only accepted cannot establish success.
        self.assertFalse(handler.handle(body,'1000',sig,1000)['verified']['matches'])
        target.complete('alpha',state['action']['id'])
        result=handler.handle(body,'1000',sig,1000)
        self.assertTrue(result['verified']['matches'])
        self.assertEqual(handler.handle(body,'1000',sig,1000),result)


class JiraWriteContractTests(unittest.TestCase):
    def setUp(self):
        self.now=datetime(2026,10,8,tzinfo=timezone.utc)
        self.actor=Actor('staff','alpha',Role.SPECIALIST);self.lead=Actor('lead','alpha',Role.SUPERVISOR)
        self.connection=JiraConnection('alpha','86f72776-2ba9-422b-aaad-184f0ed671be','IT','fake@example.invalid','fake-token')
        self.summary='before';self.calls=[];self.timeout=False
        def get(url,authorization):
            return 200,json.dumps({'key':'IT-1','fields':{'summary':self.summary,'project':{'key':'IT'},'status':{'name':'Open'}}}).encode()
        def put(url,headers,body):
            self.calls.append((url,json.loads(body)));self.summary=json.loads(body)['fields']['summary']
            if self.timeout:raise TimeoutError('private upstream failure')
            return 204
        self.reader=JiraReader(self.connection,get)
        self.adapter=JiraSummaryAdapter(self.connection,self.reader,put,MemoryStateStore(),lambda:self.now)

    def plan(self):
        plan=self.adapter.prepare(self.actor,'IT-1','after',1,'requester-a')
        approval=approve(self.lead,plan.proposal(),self.now,self.now+timedelta(minutes=15))
        return plan,approval

    def test_write_readback_and_replay(self):
        plan,approval=self.plan()
        self.assertEqual(self.adapter.execute(self.actor,plan,approval)['status'],'accepted')
        self.assertEqual(self.adapter.reconcile(self.actor,plan)['status'],'verified')
        self.adapter.execute(self.actor,plan,approval)
        self.assertEqual(len(self.calls),1)
        self.assertTrue(map_ticket(self.reader.read(self.actor,'IT-1'))['read_only_snapshot'])

    def test_lost_response_readback_never_resubmits(self):
        self.timeout=True;plan,approval=self.plan()
        self.assertEqual(self.adapter.execute(self.actor,plan,approval)['status'],'unknown')
        self.adapter.execute(self.actor,plan,approval)
        self.assertEqual(self.adapter.reconcile(self.actor,plan)['status'],'verified')
        self.assertEqual(len(self.calls),1)

    def test_source_change_and_expired_approval(self):
        plan,approval=self.plan();self.summary='concurrent change'
        with self.assertRaises(UpdateBlocked):self.adapter.execute(self.actor,plan,approval)
        self.now+=timedelta(minutes=15)
        with self.assertRaises(LifecycleBlocked):self.adapter.execute(self.actor,plan,approval)
        self.assertEqual(self.calls,[])


if __name__=='__main__':unittest.main()
