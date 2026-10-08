from datetime import datetime,timedelta,timezone
from io import BytesIO
import json
from pathlib import Path
import tempfile
import unittest

from service_desk.runtime_api import RuntimeAPI,RuntimeAuthenticator
from service_desk.auth import AuthenticationFailed
from service_desk.cases import MemoryCaseRepository
from service_desk.contracts import Actor,Role
from service_desk.durable_target import DurableSyntheticTarget
from service_desk.journeys import JourneyService
from service_desk.simulator import SimulatedTarget
from service_desk.store import MemoryStateStore


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.now=datetime(2026,10,8,tzinfo=timezone.utc)
        self.tokens={r:r[0]*40 for r in ('specialist','supervisor','auditor')}
        # Specialist and supervisor need different tokens despite their shared initial.
        self.tokens['supervisor']='h'*40
        bindings={self.tokens[role]:{'actor_id':role,'tenant_id':'alpha','role':role,
            'expires_at':(self.now+timedelta(hours=1)).isoformat()} for role in self.tokens}
        self.auth=RuntimeAuthenticator(bindings,lambda:self.now)
        self.service=JourneyService(MemoryStateStore(),SimulatedTarget(),lambda:self.now)
        self.api=RuntimeAPI(self.auth,self.service,MemoryCaseRepository(),'http://127.0.0.1:5679')

    def call(self,path,args=None,role='specialist',**overrides):
        raw=json.dumps(args or {}).encode()
        env={'REQUEST_METHOD':'POST','PATH_INFO':path,'HTTP_HOST':'127.0.0.1:5679',
             'HTTP_AUTHORIZATION':'Bearer '+self.tokens[role],'CONTENT_TYPE':'application/json',
             'CONTENT_LENGTH':str(len(raw)),'wsgi.input':BytesIO(raw),**overrides}
        seen={}
        def start(status,headers,exc_info=None):seen.update(status=int(status.split()[0]),headers=dict(headers))
        body=b''.join(self.api(env,start))
        seen['body']=json.loads(body) if seen['headers']['Content-Type'].startswith('application/json') else body.decode()
        return seen

    def test_expiry_is_server_bound(self):
        self.auth.authenticate('Bearer '+self.tokens['specialist'])
        self.now+=timedelta(hours=1)
        with self.assertRaises(AuthenticationFailed):self.auth.authenticate('Bearer '+self.tokens['specialist'])
        self.assertEqual(self.call('/v1/tools/search',{'query':'','offset':0,'limit':5})['status'],401)

    def test_human_approval_boundary_and_reviewed_payload(self):
        c=self.call('/v1/tools/create',{'text':'reports read access'})['body']['result']
        args={'case_id':c['case_id'],'expected_version':1}
        p=self.call('/v1/tools/prepare',args)['body']['result']['proposal']
        approval={**args,'payload_hash':p['payload_hash']}
        self.assertEqual(self.call('/v1/approvals',approval)['status'],403)
        self.assertEqual(self.call('/v1/approvals',{**approval,'payload_hash':'0'*64},'supervisor')['status'],409)
        self.assertEqual(self.call('/v1/approvals',approval,'supervisor')['status'],200)
        result=self.call('/v1/tools/execute',args)
        self.assertEqual(result['status'],200)
        self.assertIn('X-Correlation-ID',result['headers'])
        self.assertEqual(self.call('/v1/tools/approve',args,'supervisor')['body']['error'],'invalid_arguments')

    def test_cross_origin_host_and_overrides_denied(self):
        args={'query':'','offset':0,'limit':5}
        self.assertEqual(self.call('/v1/tools/search',args,HTTP_ORIGIN='https://external.invalid')['status'],403)
        self.assertEqual(self.call('/v1/tools/search',args,HTTP_HOST='external.invalid')['status'],403)
        self.assertEqual(self.call('/v1/tools/search',{**args,'tenant':'beta'})['status'],409)

    def test_size_json_and_secret_safe_errors(self):
        self.assertEqual(self.call('/v1/tools/create',{'text':'x'*17000})['status'],413)
        result=self.call('/v1/tools/create',{},CONTENT_LENGTH='2',**{'wsgi.input':BytesIO(b'{{')})
        self.assertEqual(result['status'],400)
        self.assertNotIn(self.tokens['specialist'],json.dumps(result))

    def test_intake_uses_same_authentication_boundary(self):
        payload={'ticket_id':'SYN-3','requester_id':'r','summary':'read','requested_access':'read-only','resource':'reports','synthetic':True}
        result=self.call('/v1/cases',payload,HTTP_IDEMPOTENCY_KEY='one')
        self.assertEqual(result['status'],201)
        self.assertEqual(self.call('/v1/cases',payload,'auditor',HTTP_IDEMPOTENCY_KEY='two')['status'],403)

    def test_review_page_csp_and_readiness_failure(self):
        result=self.call('/',REQUEST_METHOD='GET')
        self.assertEqual(result['status'],200)
        self.assertIn('Approve this proposal',result['body'])
        self.assertIn("frame-ancestors 'none'",result['headers']['Content-Security-Policy'])
        self.api.ready=lambda:False
        self.assertEqual(self.call('/readyz',REQUEST_METHOD='GET')['status'],503)


class DurableTargetTests(unittest.TestCase):
    def test_reconstruction_replay_scope_and_revocation(self):
        with tempfile.TemporaryDirectory(prefix='sd-target-test-') as directory:
            path=Path(directory)/'target.sqlite'
            target=DurableSyntheticTarget(path)
            payload={'tenant':'alpha','requester':'r','action':'grant_read_access','resource':'reports','access':'read-only'}
            self.assertEqual(target.submit('alpha','op1',payload)['status'],'accepted')
            target=DurableSyntheticTarget(path)
            target.submit('alpha','op1',payload)
            self.assertEqual(len(target.ledger()),1)
            self.assertTrue(target.inspect('alpha','op1',payload)['matches'])
            self.assertFalse(target.inspect('beta','op1',{**payload,'tenant':'beta'})['matches'])
            with self.assertRaises(ValueError):target.submit('alpha','op1',{**payload,'requester':'other'})
            with self.assertRaises(ValueError):target.submit('alpha','op2',{**payload,'access':'admin'})
            target.revoke('alpha','op1')
            self.assertFalse(target.inspect('alpha','op1',payload)['matches'])
            self.assertEqual(len(target.ledger()),1)
