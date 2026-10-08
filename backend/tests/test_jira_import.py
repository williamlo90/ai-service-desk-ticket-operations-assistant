from dataclasses import replace
from datetime import datetime,timezone
import unittest
from service_desk.contracts import Actor,Role,Ticket,AccessDenied
from service_desk.journeys import JourneyService,JourneyBlocked
from service_desk.store import MemoryStateStore
from service_desk.simulator import SimulatedTarget

class JiraImportTests(unittest.TestCase):
    def setUp(self):
        self.service=JourneyService(MemoryStateStore(),SimulatedTarget())
        self.actor=Actor('integration','alpha',Role.SPECIALIST)
        self.ticket=Ticket('alpha','IT-1','IT','Request reports read access','Open',datetime.now(timezone.utc))
    def load(self,ticket=None,actor=None):
        return self.service.import_ticket(actor or self.actor,ticket or self.ticket,'lab-cloud','requester-a')
    def test_reimport_preserves_prepared_state_without_approval(self):
        first=self.load();self.service.prepare(self.actor,first['id'],1)
        second=self.load()
        self.assertEqual(first['id'],second['id']);self.assertIsNotNone(second['proposal'])
        self.assertIsNone(second['approval']);self.assertIsNone(second['action'])
        self.assertEqual(len(self.service.store.list('alpha')),1)
    def test_source_change_requires_review(self):
        self.load()
        with self.assertRaisesRegex(JourneyBlocked,'source_changed'):
            self.load(replace(self.ticket,source_status='Closed'))
    def test_tenant_and_role_denied(self):
        for actor in (Actor('other','beta',Role.SPECIALIST),Actor('audit','alpha',Role.AUDITOR)):
            with self.assertRaises(AccessDenied):self.load(actor=actor)
    def test_different_source_has_different_identity(self):
        self.assertNotEqual(self.load()['id'],self.load(replace(self.ticket,key='IT-2'))['id'])
