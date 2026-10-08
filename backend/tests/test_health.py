from datetime import datetime,timedelta,timezone
import unittest
from service_desk.health import assess


class HealthTests(unittest.TestCase):
    def setUp(self):
        self.now=datetime(2026,10,9,tzinfo=timezone.utc)
        self.snapshot={c:{'checked_at':self.now.isoformat(),'status':'ready'} for c in ('service','worker','poll')}
        self.snapshot.update(api_ready=True,poll_enabled=True,expired_bindings=0)
    def test_healthy_metadata_and_no_secret_leak(self):
        self.snapshot['worker']['secret']='DO_NOT_PRINT'
        self.assertEqual(assess(self.snapshot,self.now)['status'],'ready')
        self.assertNotIn('DO_NOT_PRINT',str(assess(self.snapshot,self.now)))
    def test_stale_and_future_heartbeats_alert(self):
        for delta in (-31,10):
            self.snapshot['worker']['checked_at']=(self.now+timedelta(seconds=delta)).isoformat()
            self.assertIn('worker_heartbeat_stale',assess(self.snapshot,self.now)['alerts'])
    def test_blocked_expired_and_unavailable_are_actionable(self):
        self.snapshot.update(poll_blocked=True,expired_bindings=1,api_ready=False)
        alerts=assess(self.snapshot,self.now)['alerts']
        self.assertTrue({'poll_manual_resume_required','identity_expired','api_not_ready'}<=set(alerts))
    def test_worker_job_review_and_missing_monitor(self):
        self.snapshot['worker']['results']=[{'done':True,'reason':'retry_exhausted','case_id':'private'}]
        self.snapshot.pop('service')
        alerts=assess(self.snapshot,self.now)['alerts']
        self.assertIn('job_review_required',alerts);self.assertIn('service_heartbeat_missing',alerts)
    def test_disabled_poll_and_expiry_warning(self):
        self.snapshot.update(poll_enabled=False,expiring_bindings=1);self.snapshot.pop('poll')
        self.assertEqual(assess(self.snapshot,self.now)['alerts'],['identity_expires_within_hour'])
