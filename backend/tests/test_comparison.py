from copy import deepcopy
from datetime import datetime,timedelta,timezone
import json
from pathlib import Path
import tempfile
import unittest

from comparison.evaluate import evaluate
from comparison.plans import segments
from comparison.target import ReferenceTarget
from service_desk.contracts import Actor,Role
from service_desk.journeys import JourneyService
from service_desk.store import MemoryStateStore


class EvaluatorTests(unittest.TestCase):
    def setUp(self):
        fixtures=json.loads((Path(__file__).resolve().parents[2]/'docs/phase-0/reference-fixtures.json').read_text(encoding='utf-8'))
        self.fixture=next(x for x in fixtures['cases'] if x['id']=='access-success-reopen')
        with tempfile.TemporaryDirectory(prefix='sd-evaluator-') as directory:
            target=ReferenceTarget(Path(directory)/'target.sqlite')
            now=datetime(2026,10,8,tzinfo=timezone.utc)
            service=JourneyService(MemoryStateStore(),target,lambda:now)
            staff=Actor('staff','alpha',Role.SPECIALIST);lead=Actor('lead','alpha',Role.SUPERVISOR)
            case=service.create(staff,self.fixture['input']);key=case['id'];self.trace=[]
            def observe(command):
                state=service.read(staff,key);action=state['action'];operation=action['id'] if action else None
                self.trace.append({'sequence':len(self.trace)+1,'command':command,'state':state,'audit':deepcopy(state['audit']),
                    'target':target.inspect('alpha',operation,state['proposal']['payload']) if action else None,
                    'ledger':target.ledger(),'target_requests':target.requests('alpha',operation) if action else 0,
                    'denial':None,'elapsed_ms':0,'concurrent_results':None,'disclosed_foreign':0,'persisted_checkpoint':None})
            observe('initialize')
            service.prepare(staff,key,1);observe('prepare')
            service.approve(lead,key,1);observe('approve')
            state=service.execute(staff,key,1);observe('execute')
            target.complete('alpha',state['action']['id'],True);observe('complete')
            service.verify(staff,key);observe('verify')
            service.close(staff,key);observe('close')
            target.revoke('alpha',state['action']['id']);now+=timedelta(seconds=1);observe('revoke')
            service.reopen(staff,key);observe('reopen')

    def test_positive_readback_closure_then_new_evidence_reopen(self):
        self.assertTrue(evaluate(self.fixture,self.trace)['passed'])

    def test_accepted_receipt_cannot_be_used_as_closure(self):
        trace=deepcopy(self.trace);trace[3]['state']['status']='closed'
        result=evaluate(self.fixture,trace)
        self.assertFalse(result['passed']);self.assertIn('false_closure',result['failures'])

    def test_missing_checkpoint_and_audit_tampering_fail(self):
        trace=deepcopy(self.trace);trace.pop(2)
        self.assertFalse(evaluate(self.fixture,trace)['passed'])
        trace=deepcopy(self.trace);trace[-1]['audit']=[]
        self.assertIn('audit_state_mismatch',evaluate(self.fixture,trace)['failures'])

    def test_duplicate_effect_and_malformed_observation_fail(self):
        trace=deepcopy(self.trace);trace[-1]['ledger']*=2
        self.assertIn('duplicate_effect',evaluate(self.fixture,trace)['failures'])
        self.assertFalse(evaluate(self.fixture,[{}])['passed'])

    def test_expected_labels_never_enter_candidate_plans(self):
        fixture=deepcopy(self.fixture);fixture['expected']={'secret_label':'must-not-enter-workflow'}
        self.assertNotIn('must-not-enter-workflow',json.dumps(segments([fixture])))


if __name__=='__main__':unittest.main()
