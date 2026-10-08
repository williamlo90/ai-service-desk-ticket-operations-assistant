from pathlib import Path
import tempfile,unittest
from service_desk.lab_targets import LabTargets,LabTargetError,LabTargetUnavailable


class Target(LabTargets):
    def http(self,url,method='GET',data=None,token=None,form=False):
        if url.endswith('/token'):return {'access_token':'fixture-token'}
        if method=='PUT':
            self.puts+=1;self.member=True
            if self.lose_reply:raise LabTargetUnavailable('fixture reply lost')
            return None
        if url.endswith('/groups'):return [{'id':'group-alpha'}] if self.member else []
        raise AssertionError('Unexpected lab request')


class LabTargetTests(unittest.TestCase):
    def setUp(self):
        self.folder=tempfile.TemporaryDirectory();self.addCleanup(self.folder.cleanup)
        tenants={t:{'realm':'sd-lab-'+t,'requester':'requester-'+t,'user_id':'user-'+t,
            'group_id':'group-'+t,'client_id':'fixture','client_secret':'fixture','control_token':'fixture'} for t in ('alpha','beta')}
        self.target=Target(Path(self.folder.name)/'operation.sqlite',tenants)
        self.target.member=False;self.target.puts=0;self.target.lose_reply=False
        self.payload={'action':'grant_read_access','tenant':'alpha','requester':'requester-alpha','resource':'reports','access':'read-only'}
    def test_reserved_operation_does_not_repeat_put(self):
        self.assertEqual(self.target.submit('alpha','op-1',self.payload)['status'],'accepted')
        self.target.submit('alpha','op-1',self.payload)
        self.assertEqual(self.target.puts,1)
        self.assertTrue(self.target.inspect('alpha','op-1',self.payload)['matches'])
    def test_lost_reply_is_read_back_without_resubmit(self):
        self.target.lose_reply=True
        with self.assertRaises(LabTargetUnavailable):self.target.submit('alpha','op-1',self.payload)
        self.assertTrue(self.target.inspect('alpha','op-1',self.payload)['matches'])
        self.target.submit('alpha','op-1',self.payload)
        self.assertEqual(self.target.puts,1)
    def test_entitlement_revocation_invalidates_read_back(self):
        self.target.submit('alpha','op-1',self.payload);self.target.member=False
        observed=self.target.inspect('alpha','op-1',self.payload)
        self.assertEqual(observed['status'],'succeeded');self.assertFalse(observed['matches'])
    def test_unapproved_requester_or_tenant_is_rejected(self):
        with self.assertRaises(LabTargetError):self.target.submit('alpha','op-1',{**self.payload,'requester':'other'})
        with self.assertRaises(ValueError):self.target.submit('beta','op-1',self.payload)
        self.assertEqual(self.target.puts,0)
