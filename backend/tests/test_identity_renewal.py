from datetime import datetime,timezone
from pathlib import Path
import sys,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
from renew_lab_identity import rotated


class IdentityRenewalTests(unittest.TestCase):
    def config(self):
        c={'database':{'fixture':'unchanged'},'tokens':{},'bindings':{}}
        for tenant in ('alpha','beta'):
            c['tokens'][tenant]={}
            for role in ('staff','supervisor'):
                token=tenant+'-'+role;c['tokens'][tenant][role]=token
                c['bindings'][token]={'actor_id':token,'tenant_id':tenant,'role':'specialist' if role=='staff' else role,'expires_at':'2026-01-01T00:00:00+00:00'}
        return c
    def test_rotation_preserves_scope_and_config_but_invalidates_old_tokens(self):
        before=self.config();after=rotated(before,datetime(2026,10,9,tzinfo=timezone.utc))
        self.assertEqual(before,self.config());self.assertEqual(after['database'],before['database'])
        self.assertFalse(set(before['bindings'])&set(after['bindings']))
        self.assertEqual(len(after['bindings']),4)
        for item in after['bindings'].values():self.assertEqual(item['expires_at'],'2026-10-10T00:00:00+00:00')
    def test_mismatched_tenant_is_rejected(self):
        c=self.config();c['bindings']['alpha-staff']['tenant_id']='beta'
        with self.assertRaises(ValueError):rotated(c,datetime.now(timezone.utc))
    def test_extra_bindings_are_not_silently_dropped(self):
        c=self.config();c['bindings']['extra']={}
        with self.assertRaises(ValueError):rotated(c,datetime.now(timezone.utc))
