import copy
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
from analyze_business_pilot import analyze


class PilotAnalysisTests(unittest.TestCase):
    def fixture(self):
        reference=[];rows=[]
        for order,condition in enumerate(('manual','assisted'),1):
            reference.append({'id':condition,'condition':condition,'pair':'p','text':'Which service is down?',
                              'expected_category':'service_incident','expected_missing':['service_name'],'advice':None})
            rows.append({'case_id':condition,'condition':condition,'pair_id':'p','order':order,
                         'active_seconds':10,'elapsed_seconds':12,'interruption_seconds':2,'waiting_seconds':0,
                         'answer':{'category':'service_incident','missing':['service_name'],
                                   'evidence':'Which service is down?','next_step':'clarify'},
                         'correct_automatic_rubric':True,'changed_category_or_missing_fields':None})
        return rows,reference

    def test_only_equally_correct_pairs_enter_timing_comparison(self):
        rows,reference=self.fixture()
        self.assertEqual(len(analyze(rows,reference)['eligible_correct_pairs']),1)
        rows[0]['answer']['evidence']='A paraphrase';rows[0]['correct_automatic_rubric']=False
        result=analyze(rows,reference)
        self.assertEqual(result['eligible_correct_pairs'],[])
        self.assertEqual(result['efficiency_comparison'],'not_estimable')
        self.assertEqual(result['conditions']['manual']['dimensions']['category'],1)

    def test_stored_grade_is_not_silently_rewritten(self):
        rows,reference=self.fixture();rows[0]['correct_automatic_rubric']=False
        with self.assertRaisesRegex(ValueError,'stored_grade_mismatch'):analyze(rows,reference)

    def test_incomplete_duplicate_or_inconsistent_observations_rejected(self):
        rows,reference=self.fixture()
        for invalid in (rows[:1],[rows[0],rows[0]]):
            with self.assertRaises(ValueError):analyze(invalid,reference)
        broken=copy.deepcopy(rows);broken[0]['active_seconds']=50
        with self.assertRaisesRegex(ValueError,'inconsistent_time'):analyze(broken,reference)
