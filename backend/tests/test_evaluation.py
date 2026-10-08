import copy
import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import patch
from service_desk.evaluation import score, summarize, digest

ROOT = Path(__file__).resolve().parents[2]


class EvaluationTests(unittest.TestCase):
    def setUp(self):
        self.case = json.loads((ROOT/'evals/phase6/dataset.json').read_text())['cases'][0]
        self.result = {'data': {'category':self.case['expected_category'],
                               'facts':[{'source_id':'ticket','quote':self.case['text']}],
                               'missing':[]}, 'elapsed_ms':10}

    def test_empty_and_failed_responses_cannot_pass(self):
        result = summarize([self.case], [])
        self.assertEqual(result['metrics']['schema'], {'passed':0,'total':1,'rate':0})
        self.assertFalse(result['quality_gate'])
        self.assertEqual(result['unattempted'],1)
        result = summarize([self.case],[{'id':self.case['id'],'result':None}])
        self.assertEqual(result['attempted'],1)
        self.assertFalse(result['quality_gate'])

    def test_real_denominator_and_latency(self):
        other={**self.case,'id':'other'}
        result=summarize([self.case,other],[{'id':self.case['id'],'result':self.result}])
        self.assertEqual(result['metrics']['category']['rate'],.5)
        self.assertEqual(result['successful_response_latency_ms']['samples'],1)
        self.assertFalse(result['quality_gate'])

    def test_hallucinated_foreign_and_vacuous_evidence(self):
        for facts in ([],[{'source_id':'foreign','quote':self.case['text']}],
                      [{'source_id':'ticket','quote':'Operation succeeded.'}]):
            result=copy.deepcopy(self.result);result['data']['facts']=facts
            self.assertFalse(score(self.case,result)['ticket_evidence'])

    def test_clarification_and_wrong_class_are_separate(self):
        case={**self.case,'needs_clarification':True}
        checks=score(case,self.result)
        self.assertTrue(checks['schema']);self.assertFalse(checks['required_clarification'])
        result=copy.deepcopy(self.result);result['data']['category']='unsupported'
        self.assertFalse(score(self.case,result)['category'])

    def test_duplicate_and_unknown_rows_rejected(self):
        row={'id':self.case['id'],'result':self.result}
        for rows in ([row,row],[{**row,'id':'unknown'}]):
            with self.assertRaises(ValueError):summarize([self.case],rows)

    def test_frozen_dataset_labels_and_splits(self):
        data=json.loads((ROOT/'evals/phase6/dataset.json').read_text())
        freeze=json.loads((ROOT/'evals/phase6/freeze.json').read_text())
        self.assertEqual(digest(data),freeze['dataset_sha256'])
        self.assertEqual(len(data['cases']),24)
        self.assertEqual(len({c['text'] for c in data['cases']}),24)
        for case in data['cases']:
            self.assertTrue(all(s in case['text'] for s in case['evidence_spans']))

    def test_runner_refuses_unpriced_model_and_oversized_input_without_network(self):
        spec=importlib.util.spec_from_file_location('evaluate_ai',ROOT/'scripts/evaluate_ai.py')
        runner=importlib.util.module_from_spec(spec);spec.loader.exec_module(runner)
        from service_desk.ai import AIError
        with patch.object(runner,'http_json') as transport:
            for payload in ({'model':'unpriced','max_output_tokens':1000},
                            {'model':runner.MODEL,'max_output_tokens':1001},
                            {'model':runner.MODEL,'max_output_tokens':1000,'input':'x'*12001}):
                with self.assertRaises(AIError):runner.guarded_transport('unused',{},payload,15)
            transport.assert_not_called()

    def test_runner_verifies_source_freeze_without_credentials(self):
        spec=importlib.util.spec_from_file_location('evaluate_ai',ROOT/'scripts/evaluate_ai.py')
        runner=importlib.util.module_from_spec(spec);spec.loader.exec_module(runner)
        with patch.object(runner,'load_key',side_effect=AssertionError('No credentials')):
            data,freeze=runner.load_frozen()
        self.assertEqual(len(data['cases']),20)
        self.assertEqual(freeze['model'],runner.MODEL)

    def test_exact_clarification_slots_not_merely_nonempty(self):
        case={**self.case,'expected_missing':['requester_identity'],'needs_clarification':True}
        result=copy.deepcopy(self.result);result['data']['missing']=['resource']
        self.assertTrue(score(case,result)['required_clarification'])
        self.assertFalse(score(case,result)['clarification_slots'])
        result['data']['missing']=['requester_identity']
        self.assertTrue(score(case,result)['clarification_slots'])


if __name__=='__main__':unittest.main()
