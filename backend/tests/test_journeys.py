from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timedelta,timezone
from threading import Barrier
import unittest

from service_desk.contracts import Actor,Role,AccessDenied
from service_desk.journeys import JourneyService,JourneyBlocked
from service_desk.lifecycle import LifecycleBlocked
from service_desk.policy import triage
from service_desk.simulator import SimulatedTarget
from service_desk.store import MemoryStateStore,Conflict,Missing


class JourneyTests(unittest.TestCase):
    def setUp(self):
        self.now=datetime(2026,10,8,tzinfo=timezone.utc)
        self.staff=Actor('staff','alpha',Role.SPECIALIST)
        self.lead=Actor('lead','alpha',Role.SUPERVISOR)
        self.audit=Actor('audit','alpha',Role.AUDITOR)
        self.beta=Actor('staff','beta',Role.SPECIALIST)
        self.store=MemoryStateStore();self.target=SimulatedTarget()
        self.service=JourneyService(self.store,self.target,lambda:self.now)

    def ready(self,text='Grant requester-a read access to reports'):
        case=self.service.create(self.staff,text)
        self.service.prepare(self.staff,case['id'],1)
        self.service.approve(self.lead,case['id'],1)
        return case['id']

    def complete(self,key):
        state=self.service.execute(self.staff,key,1)
        self.target.complete('alpha',state['action']['id'])
        return state

    def test_access_success_reopen(self):
        key=self.ready();state=self.service.execute(self.staff,key,1)
        self.assertEqual(state['action']['status'],'accepted')
        with self.assertRaises(LifecycleBlocked): self.service.close(self.staff,key)
        self.target.complete('alpha',state['action']['id'])
        self.assertEqual(self.service.close(self.staff,key)['status'],'closed')
        self.now+=timedelta(seconds=1);self.target.revoke('alpha',state['action']['id'])
        reopened=self.service.reopen(self.staff,key)
        self.assertEqual((reopened['status'],reopened['version']),('reopened',2))
        self.assertEqual(len(self.target.ledger()),1)
        self.assertEqual(self.service.execute(self.staff,key,2)['action']['id'],state['action']['id'])
        self.assertEqual(self.target.request_count(),1)

    def test_wrong_tenant_and_auditor(self):
        key=self.ready()
        for command in (lambda:self.service.read(self.beta,key),
                        lambda:self.service.execute(self.beta,key,1)):
            with self.assertRaises(Missing):command()
        for command in (lambda:self.service.prepare(self.audit,key,1),
                        lambda:self.service.execute(self.audit,key,1)):
            with self.assertRaises(AccessDenied): command()
        self.assertEqual(self.target.ledger(),[])

    def test_stale_approval_and_exact_expiry(self):
        key=self.ready();self.service.revise(self.staff,key,'Grant reports read access please',1)
        with self.assertRaisesRegex(LifecycleBlocked,'stale_approval'):
            self.service.execute(self.staff,key,2)
        key=self.ready();self.now+=timedelta(minutes=15)
        with self.assertRaisesRegex(LifecycleBlocked,'expired_approval'):
            self.service.execute(self.staff,key,1)
        self.assertEqual(self.target.request_count(),0)

    def test_accepted_then_failed(self):
        key=self.ready();state=self.service.execute(self.staff,key,1)
        self.target.complete('alpha',state['action']['id'],False)
        result=self.service.verify(self.staff,key)
        self.assertEqual(result['action']['status'],'failed')
        self.assertIsNotNone(result['escalation'])
        with self.assertRaises(LifecycleBlocked): self.service.close(self.staff,key)
        self.assertEqual(self.target.ledger(),[])

    def test_timeout_after_effect_reconciles_without_retry(self):
        self.target.timeout_after_effect=True;key=self.ready()
        self.assertEqual(self.service.execute(self.staff,key,1)['action']['status'],'unknown')
        with self.assertRaisesRegex(JourneyBlocked,'reconciliation_required'):
            self.service.execute(self.staff,key,1)
        self.assertTrue(self.service.verify(self.staff,key)['verified']['matches'])
        self.assertEqual(self.service.close(self.staff,key)['status'],'closed')
        self.assertEqual((len(self.target.ledger()),self.target.request_count()),(1,1))

    def test_duplicate_observations_and_late_target_sequence(self):
        key=self.ready();state=self.complete(key);self.service.close(self.staff,key)
        before=self.service.read(self.staff,key)
        for _ in range(3):
            self.service.verify(self.staff,key);self.service.close(self.staff,key)
        after=self.service.read(self.staff,key)
        self.assertEqual(before,after)
        self.assertEqual(sum(x['event']=='closed' for x in after['audit']),1)
        self.assertEqual(len(self.target.ledger()),1)

    def test_concurrent_execute_has_one_external_operation(self):
        key=self.ready();barrier=Barrier(2)
        def execute(_):
            barrier.wait(timeout=5)
            try:return self.service.execute(self.staff,key,1)
            except Conflict:return None
        with ThreadPoolExecutor(max_workers=2) as pool: list(pool.map(execute,range(2)))
        state=self.service.read(self.staff,key)
        self.target.complete('alpha',state['action']['id'])
        self.assertEqual((self.target.request_count(),len(self.target.ledger())),(1,1))

    def test_service_reconstruction_same_store_is_not_process_restart(self):
        key=self.ready();state=self.service.execute(self.staff,key,1)
        resumed=JourneyService(self.store,self.target,lambda:self.now)
        self.target.complete('alpha',state['action']['id'])
        self.assertEqual(resumed.close(self.staff,key)['status'],'closed')
        self.assertEqual(self.target.request_count(),1)
        with self.assertRaises(Missing):
            JourneyService(MemoryStateStore(),self.target).read(self.staff,key)

    def test_ambiguity_and_missing_policy(self):
        self.assertEqual(triage('I need access')['missing'],['resource','entitlement'])
        for text,decision in [('I need access','clarification'),('Grant administrator access','escalate')]:
            case=self.service.create(self.staff,text)
            with self.assertRaisesRegex(JourneyBlocked,decision): self.service.prepare(self.staff,case['id'],1)
        self.assertEqual(self.target.ledger(),[])

    def test_incident_three_separated_healthy_checks(self):
        key=self.ready('demo-api is unavailable');self.complete(key)
        self.assertFalse(self.service.verify(self.staff,key)['verified']['matches'])
        self.assertFalse(self.service.verify(self.staff,key)['verified']['matches'])
        self.now+=timedelta(seconds=10)
        self.assertFalse(self.service.verify(self.staff,key)['verified']['matches'])
        self.now+=timedelta(seconds=10)
        closed=self.service.close(self.staff,key)
        self.assertEqual((closed['status'],len(closed['action']['healthy_checks'])),('closed',3))

    def test_related_ticket_is_not_incident_resolution(self):
        key=self.ready('SD-2 has the same outage as SD-1');self.complete(key)
        self.assertTrue(self.service.verify(self.staff,key)['verified']['matches'])
        with self.assertRaisesRegex(JourneyBlocked,'relation_does_not_resolve_incident'):
            self.service.close(self.staff,key)
        self.service.execute(self.staff,key,1)
        self.assertEqual(len(self.target.ledger()),1)

    def test_self_approval_and_unapproved_execute_denied(self):
        state=self.service.create(self.staff,'Grant reports read access',requester='lead')
        self.service.prepare(self.staff,state['id'],1)
        with self.assertRaises(AccessDenied):self.service.approve(self.lead,state['id'],1)
        with self.assertRaisesRegex(JourneyBlocked,'approval_required'):
            self.service.execute(self.staff,state['id'],1)

    def test_audit_snapshot_immutable_and_scoped_summary(self):
        key=self.ready();copy=self.service.read(self.staff,key);copy['audit'].clear()
        self.assertEqual(len(self.service.read(self.staff,key)['audit']),3)
        self.assertEqual(self.service.summary(self.audit)['total'],1)
        self.assertEqual(self.service.summary(self.beta)['total'],0)
        old=self.store.get('alpha',key);changed=self.store.get('alpha',key)
        changed['revision']+=1;changed['audit']=[]
        with self.assertRaises(ValueError):self.store.save('alpha',key,old['revision'],changed)

    def test_revocation_before_close_requires_fresh_readback(self):
        key=self.ready();state=self.complete(key);self.service.verify(self.staff,key)
        self.target.revoke('alpha',state['action']['id'])
        with self.assertRaises(LifecycleBlocked):self.service.close(self.staff,key)


if __name__=='__main__':unittest.main()
