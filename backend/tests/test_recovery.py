from datetime import datetime,timedelta,timezone
import tempfile,unittest
from pathlib import Path
from service_desk.contracts import Actor,Role,AccessDenied
from service_desk.journeys import JourneyService,JourneyBlocked
from service_desk.recovery import RecoveryController
from service_desk.store import MemoryStateStore
from comparison.target import ReferenceTarget


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.now=datetime(2026,10,8,tzinfo=timezone.utc)
        self.target=ReferenceTarget(Path(self.temp.name)/'target.sqlite')
        self.store=MemoryStateStore()
        self.service=JourneyService(self.store,self.target,lambda:self.now)
        self.staff=Actor('staff','alpha',Role.SPECIALIST)
        self.lead=Actor('lead','alpha',Role.SUPERVISOR)
        self.key=self.service.create(self.staff,'Grant reports read access')['id']
        self.service.prepare(self.staff,self.key,1);self.service.approve(self.lead,self.key,1)
        self.controller=RecoveryController(self.service,lambda:self.now)
    def tick(self):return self.controller.tick(self.staff,self.key)
    def state(self):return self.service.read(self.staff,self.key)

    def test_expired_and_revoked_approval_never_dispatch(self):
        self.now+=timedelta(seconds=900)
        self.assertEqual(self.tick()['reason'],'approval_rejected')
        self.assertIsNone(self.state()['action'])

    def test_only_supervisor_can_revoke_before_dispatch(self):
        with self.assertRaises(AccessDenied):self.service.revoke_approval(self.staff,self.key,1)
        self.service.revoke_approval(self.lead,self.key,1)
        self.assertEqual(self.tick()['reason'],'approval_rejected')
        self.assertIsNone(self.state()['action'])

    def test_no_revocation_after_dispatch(self):
        self.tick()
        with self.assertRaises(JourneyBlocked):self.service.revoke_approval(self.lead,self.key,1)

    def test_budget_backoff_and_fresh_controller(self):
        self.assertEqual(self.tick()['attempts'],1)
        self.assertEqual(self.tick()['attempts'],1)
        for delay,count in [(1,2),(2,3),(4,4)]:
            self.now+=timedelta(seconds=delay)
            self.controller=RecoveryController(self.service,lambda:self.now)
            self.assertEqual(self.tick()['attempts'],count)
        self.assertEqual(self.tick()['reason'],'retry_exhausted')
        self.assertEqual(self.state()['status'],'open')
        self.assertEqual(self.target.submit_calls('alpha',self.state()['action']['id']),1)

    def test_timeout_after_effect_reconciles_without_resubmit(self):
        self.target.timeout_after_effect=True
        self.assertEqual(self.tick()['reason'],'closed')
        self.assertEqual(self.target.submit_calls('alpha',self.state()['action']['id']),1)
        self.assertEqual(len(self.target.ledger()),1)

    def test_terminal_failure_routes_to_review(self):
        self.tick();self.target.complete('alpha',self.state()['action']['id'],False)
        self.now+=timedelta(seconds=1)
        self.assertEqual(self.tick()['reason'],'target_failed')
        self.assertEqual(self.state()['escalation']['reason'],'target_failed')

    def test_crash_reserved_last_attempt_does_not_reset_budget(self):
        self.tick();state=self.state()
        state['recovery'].update(attempts=4,next_at=self.now.isoformat())
        self.service._save(self.staff,state,'test_crash_checkpoint')
        self.assertEqual(self.tick()['reason'],'retry_exhausted')
        self.assertEqual(self.tick()['attempts'],4)

    def test_read_timeouts_exhaust_budget_without_mutation_retry(self):
        self.tick()
        def timeout(*args):raise TimeoutError()
        self.target.inspect=timeout
        for delay in (1,2,4):
            self.now+=timedelta(seconds=delay);result=self.tick()
        self.assertEqual(result['reason'],'retry_exhausted')
        self.assertEqual(self.target.submit_calls('alpha',self.state()['action']['id']),1)
