from datetime import datetime,timedelta,timezone
from pathlib import Path
import tempfile,unittest
from service_desk.jira_links import JiraLinks,LinkBlocked
from service_desk.jira import JiraConnection
from service_desk.contracts import Actor,Role,Ticket,AccessDenied
from service_desk.lifecycle import approve,LifecycleBlocked
from service_desk.jira_result import ResultWriteError

class LinksTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.actor=Actor('staff','alpha',Role.SPECIALIST);self.now=datetime.now(timezone.utc)
        self.linked=False;self.posts=0;self.lost=False;self.drift=False
        class Reader:
            def read(_,actor,key):return Ticket('alpha',key,'IT','[TEST] '+('changed' if self.drift else key),'Open',self.now)
        c=JiraConnection('alpha','86f72776-2ba9-422b-aaad-184f0ed671be','IT','x@y.test','fixture-token')
        self.adapter=JiraLinks(c,Path(self.tmp.name)/'links.sqlite',Reader(),self.transport)
        self.plan=self.adapter.prepare(self.actor)
        self.approval=approve(Actor('supervisor','alpha',Role.SUPERVISOR),self.plan.proposal(),self.now,self.now+timedelta(minutes=5))
    def transport(self,url,auth,method,body=None):
        if url.endswith('issueLinkType'):return 200,{'issueLinkTypes':[{'id':'10003','name':'Relates'}]}
        if method=='POST':
            self.posts+=1;self.linked=True
            self.assertNotIn('comment',body)
            if self.lost:raise ResultWriteError('response_lost')
            return 201,None
        return 200,{'key':'IT-2','fields':{'project':{'key':'IT'},'issuelinks':
            [{'id':'1','type':{'id':'10003'},'outwardIssue':{'key':'IT-1'}}] if self.linked else []}}
    def test_write_readback_replay_once(self):
        self.assertTrue(self.adapter.execute(self.actor,self.plan,self.approval)['matches'])
        self.assertFalse(self.adapter.execute(self.actor,self.plan,self.approval)['write_attempted'])
        self.assertEqual(self.posts,1)
    def test_lost_receipt_reconciles(self):
        self.lost=True;self.assertTrue(self.adapter.execute(self.actor,self.plan,self.approval)['matches'])
    def test_stale_source_blocks(self):
        self.drift=True
        with self.assertRaises(LinkBlocked):self.adapter.execute(self.actor,self.plan,self.approval)
        self.assertEqual(self.posts,0)
    def test_expired_approval_blocks(self):
        self.adapter.clock=lambda:self.now+timedelta(hours=1)
        with self.assertRaises(LifecycleBlocked):self.adapter.execute(self.actor,self.plan,self.approval)
        self.assertEqual(self.posts,0)
    def test_wrong_tenant_blocks(self):
        with self.assertRaises(AccessDenied):self.adapter.execute(Actor('other','beta',Role.SPECIALIST),self.plan,self.approval)
