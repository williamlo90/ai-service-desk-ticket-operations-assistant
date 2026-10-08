import tempfile,unittest
from pathlib import Path
from service_desk.jira import JiraConnection
from service_desk.jira_result import JiraResultWriter,ResultWriteError
from service_desk.contracts import Actor,Role,AccessDenied

class ResultTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.c=JiraConnection('alpha','86f72776-2ba9-422b-aaad-184f0ed671be','IT','a@b.test','fake-token')
        self.actor=Actor('staff','alpha',Role.SPECIALIST);self.value={'verified':True};self.remote=None;self.puts=0
        self.operation='f98d23f4-2d55-4eb4-8139-5ae6cdfa1878';self.drop=False
    def transport(self,url,auth,method,value=None):
        if method=='GET':return (404,None) if self.remote is None else (200,{'key':url.rsplit('/',1)[1],'value':self.remote})
        self.puts+=1;self.remote=value
        if self.drop:raise ResultWriteError('lost_response')
        return 201,None
    def writer(self,transport=None):return JiraResultWriter(self.c,Path(self.temp.name)/'journal.sqlite',transport or self.transport)
    def test_verified_replay_writes_once(self):
        w=self.writer();w.publish(self.actor,'IT-1',self.operation,self.value)
        self.assertFalse(w.publish(self.actor,'IT-1',self.operation,self.value)['write_attempted']);self.assertEqual(self.puts,1)
    def test_lost_response_reconciles(self):
        self.drop=True;self.assertTrue(self.writer().publish(self.actor,'IT-1',self.operation,self.value)['verified'])
    def test_conflict_never_overwritten(self):
        self.remote={'other':True}
        with self.assertRaisesRegex(ResultWriteError,'conflict'):self.writer().publish(self.actor,'IT-1',self.operation,self.value)
        self.assertEqual(self.puts,0)
    def test_denials_before_transport(self):
        w=self.writer(lambda *args: self.fail('network called'))
        with self.assertRaises(AccessDenied):w.publish(Actor('x','beta',Role.SPECIALIST),'IT-1',self.operation,self.value)
        with self.assertRaises(AccessDenied):w.publish(Actor('x','alpha',Role.AUDITOR),'IT-1',self.operation,self.value)
        with self.assertRaises(ResultWriteError):w.publish(self.actor,'IT-2',self.operation,self.value)
    def test_unknown_without_effect_never_retries_put(self):
        calls=[]
        def transport(url,auth,method,value=None):
            calls.append(method)
            if method=='PUT':raise ResultWriteError('timeout')
            return 404,None
        w=self.writer(transport)
        for _ in range(2):
            with self.assertRaises(ResultWriteError):w.publish(self.actor,'IT-1',self.operation,self.value)
        self.assertEqual(calls.count('PUT'),1)
    def test_definite_auth_rejection_allows_later_manual_run(self):
        def rejected(url,auth,method,value=None):return (404,None) if method=='GET' else (401,None)
        with self.assertRaisesRegex(ResultWriteError,'write_http_401'):
            self.writer(rejected).publish(self.actor,'IT-1',self.operation,self.value)
        self.assertTrue(self.writer().publish(self.actor,'IT-1',self.operation,self.value)['verified'])
