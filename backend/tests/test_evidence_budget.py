from decimal import Decimal
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
from evaluate_evidence_ai import spend,measured_cost,MODEL


class EvidenceBudgetTests(unittest.TestCase):
    def test_unknown_attempt_keeps_full_reservation(self):
        self.assertEqual(spend([{'identity':'a','reserved_usd':'.02'}],{}),(Decimal('.02'),0))
        self.assertIsNone(measured_cost({'result':{'model':MODEL,'usage':{'input_tokens':1,'output_tokens':None}}}))

    def test_reported_usage_settles_only_its_own_attempt(self):
        entries=[{'identity':k,'reserved_usd':'.02'} for k in ('a','b')]
        report={'result':{'model':MODEL,'usage':{'input_tokens':1000,'output_tokens':100}}}
        self.assertEqual(spend(entries,{'a':report}),(Decimal('.02056'),1))
        self.assertEqual(spend(entries,{'unrelated':report}),(Decimal('.04'),0))

    def test_duplicates_and_nonfinite_reservations_rejected(self):
        with self.assertRaises(ValueError):spend([{'identity':'a','reserved_usd':'.02'}]*2,{})
        with self.assertRaises(ValueError):spend([{'identity':'a','reserved_usd':'NaN'}],{})
