from concurrent.futures import ThreadPoolExecutor
import io
import json
import unittest

from service_desk.api import CaseAPI, MAX_BODY
from service_desk.auth import TokenAuthenticator
from service_desk.cases import MemoryCaseRepository
from service_desk.contracts import Actor, Role

# Deliberately fake credentials, valid only in this in-process fixture.
TOKENS = {name: 'synthetic-test-token-' + name + '-xxxxxxxxxxxxxxxx'
          for name in ('alpha','beta','auditor','requester','supervisor')}
DATA = dict(ticket_id='SYN-001', tenant_id='alpha', requester_id='requester-a',
            summary='Request read access to reports', requested_access='read-only',
            resource='reports', synthetic=True)


class APITests(unittest.TestCase):
    def setUp(self):
        self.auth = TokenAuthenticator({
            TOKENS['alpha']:Actor('staff-a','alpha',Role.SPECIALIST),
            TOKENS['beta']:Actor('staff-b','beta',Role.SPECIALIST),
            TOKENS['auditor']:Actor('audit-a','alpha',Role.AUDITOR),
            TOKENS['requester']:Actor('requester-a','alpha',Role.REQUESTER),
            TOKENS['supervisor']:Actor('lead-a','alpha',Role.SUPERVISOR),
        })
        self.repo = MemoryCaseRepository()
        self.app = CaseAPI(self.auth,self.repo)

    def request(self, method='POST', path='/v1/cases', data=None,
                identity='alpha', key='request-1', raw=None, extra=None):
        raw = json.dumps(DATA if data is None else data).encode() if raw is None else raw
        env = {'REQUEST_METHOD':method,'PATH_INFO':path,
               'CONTENT_TYPE':'application/json','CONTENT_LENGTH':str(len(raw)),
               'wsgi.input':io.BytesIO(raw),'HTTP_IDEMPOTENCY_KEY':key}
        if identity:
            env['HTTP_AUTHORIZATION'] = 'Bearer '+TOKENS.get(identity,identity)
        env.update(extra or {})
        response = {}
        def start(status,headers):
            response['status'] = int(status.split()[0])
            response['headers'] = dict(headers)
        encoded = b''.join(self.app(env,start))
        self.assertEqual(int(response['headers']['Content-Length']),len(encoded))
        self.assertEqual(response['headers']['Cache-Control'],'no-store')
        return response['status'], json.loads(encoded)

    def test_create_read_and_status_is_received_not_approved(self):
        status, result = self.request()
        self.assertEqual(status,201)
        case = result['case']
        self.assertEqual((case['tenant_id'],case['created_by'],case['status']),
                         ('alpha','staff-a','received'))
        status, read = self.request('GET','/v1/cases/'+case['case_id'])
        self.assertEqual((status,read['case']),(200,case))

    def test_auth_required_and_errors_do_not_echo_credentials(self):
        for identity in (None,'unknown-sensitive-token-xxxxxxxxxxxxxxxxxx'):
            with self.subTest(identity=identity):
                self.assertEqual(self.request(identity=identity),(401,{'error':'unauthorized'}))
        for header in ('Basic xyz','Bearer short','Bearer '+TOKENS['alpha']+' extra'):
            self.assertEqual(self.request(extra={'HTTP_AUTHORIZATION':header})[0],401)

    def test_spoofed_headers_cannot_assign_tenant_or_role(self):
        status,result=self.request(extra={'HTTP_X_TENANT_ID':'beta','HTTP_X_ROLE':'supervisor'})
        self.assertEqual(status,201)
        self.assertEqual(result['case']['tenant_id'],'alpha')
        self.assertEqual(self.request(identity='requester',extra={'HTTP_X_ROLE':'supervisor'})[0],403)
        self.assertEqual(self.request(data={**DATA,'role':'supervisor'})[0],400)

    def test_cross_tenant_create_denied_and_read_is_not_found(self):
        self.assertEqual(self.request(identity='beta')[0],403)
        _,result=self.request()
        path='/v1/cases/'+result['case']['case_id']
        self.assertEqual(self.request('GET',path,identity='beta'),(404,{'error':'not_found'}))

    def test_roles(self):
        _,result=self.request()
        path='/v1/cases/'+result['case']['case_id']
        self.assertEqual(self.request(identity='auditor')[0],403)
        self.assertEqual(self.request('GET',path,identity='auditor')[0],200)
        self.assertEqual(self.request('GET',path,identity='requester')[0],403)
        self.assertEqual(self.request(identity='supervisor')[0],201)

    def test_missing_tenant_uses_trusted_binding(self):
        data={k:v for k,v in DATA.items() if k!='tenant_id'}
        self.assertEqual(self.request(data=data,identity='beta')[1]['case']['tenant_id'],'beta')

    def test_validation_rejects_unsafe_or_non_synthetic_intake(self):
        bad = [[], {}, {**DATA,'synthetic':1}, {**DATA,'synthetic':False},
               {**DATA,'ticket_id':'IT-1'}, {**DATA,'requested_access':'admin'},
               {**DATA,'resource':'payroll'}, {**DATA,'summary':' '},
               {**DATA,'summary':'x'*2001}, {**DATA,'summary':'x\ny'},
               {**DATA,'requester_id':None}, {**DATA,'actor_id':'other'}]
        for data in bad:
            with self.subTest(data=data):
                self.assertEqual(self.request(data=data)[0],400)

    def test_json_parser_rejects_duplicate_keys_constants_and_invalid_utf8(self):
        for raw in (b'{', b'{"synthetic":true,"synthetic":false}',b'{"x":NaN}',b'\xff'):
            self.assertEqual(self.request(raw=raw)[0],400)

    def test_body_limits_and_media_type(self):
        class Unreadable:
            def read(self,*args):
                raise AssertionError('Must reject before reading.')
        self.assertEqual(self.request(extra={'CONTENT_LENGTH':str(MAX_BODY+1),'wsgi.input':Unreadable()})[0],413)
        self.assertEqual(self.request(extra={'CONTENT_LENGTH':''})[0],411)
        self.assertEqual(self.request(extra={'CONTENT_LENGTH':'-1'})[0],400)
        self.assertEqual(self.request(extra={'CONTENT_LENGTH':'999'})[0],400)
        self.assertEqual(self.request(extra={'CONTENT_TYPE':'text/plain'})[0],415)

    def test_idempotent_replay_and_conflicting_payload(self):
        _,first=self.request()
        status,again=self.request()
        self.assertEqual((status,again['created'],again['case']),(200,False,first['case']))
        self.assertEqual(self.request(data={**DATA,'summary':'changed'})[0],409)
        self.assertEqual(self.request(key='')[0],400)

    def test_idempotency_is_scoped_to_tenant_and_actor(self):
        _,alpha=self.request()
        _,beta=self.request(data={**DATA,'tenant_id':'beta'},identity='beta')
        _,lead=self.request(identity='supervisor')
        self.assertEqual(len({x['case']['case_id'] for x in (alpha,beta,lead)}),3)

    def test_parallel_replays_create_one_case(self):
        with ThreadPoolExecutor(max_workers=4) as pool:
            responses=list(pool.map(lambda _:self.request(),range(12)))
        self.assertEqual(sum(status==201 for status,_ in responses),1)
        self.assertEqual(len({body['case']['case_id'] for _,body in responses}),1)

    def test_storage_bound_preserves_existing_replay(self):
        self.app=CaseAPI(self.auth,MemoryCaseRepository(capacity=1))
        self.assertEqual(self.request()[0],201)
        self.assertEqual(self.request(key='second')[0],503)
        self.assertEqual(self.request()[0],200)

    def test_storage_is_explicitly_ephemeral(self):
        _,created=self.request()
        self.app=CaseAPI(self.auth,MemoryCaseRepository())
        self.assertEqual(self.request('GET','/v1/cases/'+created['case']['case_id'])[0],404)

    def test_exception_is_sanitized(self):
        class Broken(MemoryCaseRepository):
            def create(self,*args):
                raise RuntimeError('private-password-and-ticket-data')
        self.app=CaseAPI(self.auth,Broken())
        self.assertEqual(self.request(),(500,{'error':'internal_error'}))

    def test_health_and_unknown_routes(self):
        self.assertEqual(self.request('GET','/healthz',identity=None),(200,{'status':'ok'}))
        self.assertEqual(self.request('GET','/not-a-route')[0],404)

    def test_auth_configuration_has_no_default_and_no_secret_repr(self):
        with self.assertRaises(ValueError):
            TokenAuthenticator({})
        with self.assertRaises(ValueError):
            TokenAuthenticator({'short':Actor('a','alpha',Role.SPECIALIST)})
        self.assertNotIn(TOKENS['alpha'],repr(self.auth))


if __name__ == '__main__':
    unittest.main()
