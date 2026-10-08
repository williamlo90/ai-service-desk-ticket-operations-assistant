import unittest
from service_desk.jira_search import JiraSearch,SearchBlocked,sync
from service_desk.jira import JiraConnection
from service_desk.contracts import Actor,Role,AccessDenied
from service_desk.journeys import JourneyService
from service_desk.store import MemoryStateStore
from service_desk.simulator import SimulatedTarget

def issue(key='IT-1',summary='[TEST] reports read access'):
    return {'key':key,'fields':{'summary':summary,'status':{'name':'Open'},'project':{'key':'IT'}}}

class SearchTests(unittest.TestCase):
    def setUp(self):
        self.c=JiraConnection('alpha','86f72776-2ba9-422b-aaad-184f0ed671be','IT','x@y.test','fixture-token')
        self.actor=Actor('staff','alpha',Role.SPECIALIST)
    def search(self,pages):
        iterator=iter(pages)
        return JiraSearch(self.c,['IT-1','IT-2'],lambda *args:next(iterator))
    def test_cursor_paging(self):
        pages=list(self.search([(200,{'issues':[issue()],'isLast':False,'nextPageToken':'next'}),
            (200,{'issues':[issue('IT-2')],'isLast':True})]).pages(self.actor,1))
        self.assertEqual([t.key for p in pages for t in p],['IT-1','IT-2'])
    def test_repeated_cursor_rejected(self):
        data=(200,{'issues':[],'isLast':False,'nextPageToken':'same'})
        with self.assertRaises(SearchBlocked):list(self.search([data,data]).pages(self.actor))
    def test_wrong_tenant_never_calls_transport(self):
        with self.assertRaises(AccessDenied):list(self.search([]).pages(Actor('x','beta',Role.SPECIALIST)))
    def test_wrong_issue_fails_closed(self):
        with self.assertRaises(SearchBlocked):list(self.search([(200,{'issues':[issue('OTHER-1')],'isLast':True})]).pages(self.actor))
    def test_rate_limit_not_retried(self):
        with self.assertRaisesRegex(SearchBlocked,'http_429'):list(self.search([(429,None)]).pages(self.actor))
    def test_sync_replay_and_drift_preserve_original(self):
        service=JourneyService(MemoryStateStore(),SimulatedTarget())
        for _ in range(2):sync(service,self.actor,self.search([(200,{'issues':[issue()],'isLast':True})]),'requester-a')
        self.assertEqual(len(service.store.list('alpha')),1)
        result=sync(service,self.actor,self.search([(200,{'issues':[issue(summary='[TEST] changed')],'isLast':True})]),'requester-a')
        self.assertEqual(result[0]['status'],'source_changed_review_required')
        self.assertEqual(service.store.list('alpha')[0]['text'],'[TEST] reports read access')
