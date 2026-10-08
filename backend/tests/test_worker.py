import unittest
from service_desk.worker import scan
from service_desk.store import MemoryStateStore
from service_desk.journeys import JourneyService
from service_desk.simulator import SimulatedTarget
from service_desk.contracts import Actor,Role

class WorkerTests(unittest.TestCase):
    def setUp(self):
        self.target=SimulatedTarget();self.service=JourneyService(MemoryStateStore(),self.target)
        self.actor=Actor('staff','alpha',Role.SPECIALIST)
        self.case=self.service.create(self.actor,'reports read access')
        self.service.prepare(self.actor,self.case['id'],1)
    def test_unapproved_case_is_not_dispatched(self):
        self.assertEqual(scan(self.service,self.actor),[])
        self.assertIsNone(self.service.read(self.actor,self.case['id'])['action'])
    def test_source_change_escalates_before_dispatch(self):
        state=self.service.approve(Actor('lead','alpha',Role.SUPERVISOR),self.case['id'],1)
        state['source']={'key':'IT-1'};self.service._save(self.actor,state,'source_attached')
        scan(self.service,self.actor,lambda state:False)
        state=self.service.read(self.actor,self.case['id'])
        self.assertIsNone(state['action']);self.assertEqual(state['escalation']['reason'],'source_changed_review_required')
    def test_approved_job_reserves_once(self):
        self.service.approve(Actor('lead','alpha',Role.SUPERVISOR),self.case['id'],1)
        scan(self.service,self.actor);scan(self.service,self.actor)
        state=self.service.read(self.actor,self.case['id'])
        self.assertEqual(sum(e['event']=='dispatch_reserved' for e in state['audit']),1)
    def test_source_transport_failure_latches_review_without_retry(self):
        state=self.service.approve(Actor('lead','alpha',Role.SUPERVISOR),self.case['id'],1)
        state['source']={'key':'IT-1'};self.service._save(self.actor,state,'source_attached')
        calls=[]
        def fail(state):calls.append(1);raise ConnectionError()
        scan(self.service,self.actor,fail);scan(self.service,self.actor,fail)
        self.assertEqual(len(calls),1)
        self.assertIsNone(self.service.read(self.actor,self.case['id'])['action'])

    def test_closed_history_and_unapproved_intake_do_not_exhaust_active_limit(self):
        for _ in range(5):self.service.create(self.actor,'reports read access')
        self.service.approve(Actor('lead','alpha',Role.SUPERVISOR),self.case['id'],1)
        old=self.service.create(self.actor,'reports read access')
        old['status']='closed';self.service._save(self.actor,old,'fixture_closed_history')
        results=scan(self.service,self.actor,limit=1)
        self.assertEqual(len(results),1)
        self.assertEqual(results[0]['case_id'],self.case['id'])

    def test_active_limit_blocks_before_any_effect(self):
        lead=Actor('lead','alpha',Role.SUPERVISOR)
        self.service.approve(lead,self.case['id'],1)
        other=self.service.create(self.actor,'reports read access')
        self.service.prepare(self.actor,other['id'],1);self.service.approve(lead,other['id'],1)
        with self.assertRaisesRegex(ValueError,'queue_scan_limit'):scan(self.service,self.actor,limit=1)
        self.assertIsNone(self.service.read(self.actor,self.case['id'])['action'])
        self.assertIsNone(self.service.read(self.actor,other['id'])['action'])
