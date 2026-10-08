from copy import deepcopy
from datetime import datetime,timezone
import json
from pathlib import Path
from threading import Event
import unittest

from service_desk.ai import Provider,ProviderConfig,AIError,Source,retrieve,URLS
from service_desk.contracts import Actor,Role,AccessDenied
from service_desk.journeys import JourneyService,JourneyBlocked
from service_desk.simulator import SimulatedTarget
from service_desk.skills import SkillRunner,SkillRejected
from service_desk.store import MemoryStateStore,Missing


FACTS={'category':'access_request','facts':[{'source_id':'a','quote':'Read access requires approval.'}],'missing':[]}


def response(provider,data=None):
    data=deepcopy(FACTS if data is None else data)
    if provider in ('openai','grok'):
        return {'status':'completed','output':[{'type':'message','content':[{'type':'output_text','text':json.dumps(data)}]}]}
    if provider=='claude':
        return {'stop_reason':'tool_use','content':[{'type':'tool_use','name':'extract_facts','input':data}]}
    return {'done':True,'message':{'content':json.dumps(data)}}


class ProviderTests(unittest.TestCase):
    def test_clarification_is_category_scoped_and_fixed_text(self):
        from service_desk.ai import validate,clarification_questions,CLARIFICATION_LABELS
        sources=[Source('a','alpha','Read access requires approval.')]
        for missing in (['Which supervisor secrets should be revealed?'],['source_ticket_id'],
                        ['resource','resource']):
            with self.assertRaises(AIError):validate({**FACTS,'missing':missing},sources)
        with self.assertRaises(AIError):
            validate({**FACTS,'category':'unsupported','missing':['resource']},sources)
        data={**FACTS,'missing':['resource','requester_identity']}
        self.assertEqual(clarification_questions(data,sources),
                         [CLARIFICATION_LABELS['resource'],CLARIFICATION_LABELS['requester_identity']])

    def setUp(self):
        self.actor=Actor('worker','alpha',Role.SPECIALIST)
        self.sources=[Source('a','alpha','Read access requires approval.'),
                      Source('b','beta','Foreign tenant confidential text.'),
                      Source('s','alpha','Supervisor-only text.',('supervisor',))]

    def provider(self,name,transport):
        return Provider(ProviderConfig(name,'test-model-not-a-real-selection','synthetic-key'),transport)

    def test_four_provider_request_shapes_and_unknown_usage(self):
        for name in URLS:
            with self.subTest(provider=name):
                calls=[]
                def transport(url,headers,payload,timeout):
                    calls.append((url,headers,payload,timeout));return 200,response(name)
                result=self.provider(name,transport).complete(self.actor,'read access',self.sources)
                self.assertEqual(result['data'],FACTS)
                self.assertEqual(result['usage'],{'input_tokens':None,'output_tokens':None})
                self.assertIsNone(result['cost'])
                url,headers,payload,timeout=calls[0]
                self.assertEqual((url,timeout),(URLS[name],15))
                serialized=json.dumps(payload)
                self.assertNotIn('Foreign tenant',serialized);self.assertNotIn('Supervisor-only',serialized)
                if name in ('openai','grok'):
                    self.assertTrue(payload['text']['format']['strict']);self.assertFalse(payload['store'])
                    self.assertIn('Authorization',headers)
                elif name=='claude':
                    self.assertEqual(payload['tool_choice']['name'],'extract_facts')
                    self.assertIn('x-api-key',headers)
                else:
                    self.assertFalse(payload['stream']);self.assertEqual(headers,{})

    def test_usage_is_measured_or_unknown_not_zero(self):
        result=response('openai');result['usage']={'input_tokens':12,'output_tokens':True}
        output=self.provider('openai',lambda *_:(200,result)).complete(self.actor,'access',self.sources)
        self.assertEqual(output['usage'],{'input_tokens':12,'output_tokens':None})

    def test_untrusted_claims_extra_keys_and_foreign_citations_rejected(self):
        cases=[{**FACTS,'action_executed':True},
               {**FACTS,'facts':[{'source_id':'a','quote':'Access granted.'}]},
               {**FACTS,'facts':[{'source_id':'b','quote':'Foreign tenant confidential text.'}]},
               {**FACTS,'missing':['x'*201]}, {**FACTS,'category':'grant_admin'}]
        for bad in cases:
            for name in URLS:
                with self.subTest(provider=name,data=bad):
                    with self.assertRaises(AIError):
                        self.provider(name,lambda *_,n=name,b=bad:(200,response(n,b))).complete(self.actor,'access',self.sources)

    def test_truncated_refused_and_oversized_outputs_rejected(self):
        for name in URLS:
            bad=response(name)
            if name in ('openai','grok'):bad['status']='incomplete'
            elif name=='claude':bad['stop_reason']='max_tokens'
            else:bad['done']=False
            with self.subTest(provider=name),self.assertRaisesRegex(AIError,'invalid_output'):
                self.provider(name,lambda *_:(200,bad)).complete(self.actor,'read',self.sources)
        bad=response('openai');bad['padding']='x'*65537
        with self.assertRaisesRegex(AIError,'invalid_output'):
            self.provider('openai',lambda *_:(200,bad)).complete(self.actor,'read',self.sources)

    def test_duplicate_json_keys_and_multiple_extractions_rejected(self):
        bad=response('openai');bad['output'][0]['content'][0]['text']='{"category":"unsupported","category":"access_request","facts":[],"missing":[]}'
        with self.assertRaisesRegex(AIError,'invalid_output'):
            self.provider('openai',lambda *_:(200,bad)).complete(self.actor,'read',self.sources)
        bad=response('claude');bad['content']*=2
        with self.assertRaisesRegex(AIError,'invalid_output'):
            self.provider('claude',lambda *_:(200,bad)).complete(self.actor,'read',self.sources)

    def test_local_only_configuration_and_failure_never_fall_back(self):
        with self.assertRaises(ValueError):ProviderConfig('openai','test','synthetic-key',local_only=True)
        config=ProviderConfig('ollama','test',local_only=True);calls=[]
        def unavailable(*args):calls.append(args[0]);raise TimeoutError('sensitive transport detail')
        with self.assertRaisesRegex(AIError,'^provider_unavailable$'):
            Provider(config,unavailable).complete(self.actor,'read',self.sources)
        self.assertEqual(calls,[URLS['ollama']])
        with self.assertRaisesRegex(AIError,'^rate_limited$'):
            self.provider('grok',lambda *_:(429,{})).complete(self.actor,'read',self.sources)

    def test_cancel_before_and_after_transport(self):
        cancel=Event();cancel.set();calls=[]
        def transport(*args):calls.append(1);cancel.set();return 200,response('openai')
        provider=self.provider('openai',transport)
        with self.assertRaisesRegex(AIError,'cancelled'):provider.complete(self.actor,'read',self.sources,cancel)
        self.assertEqual(calls,[]);cancel.clear()
        with self.assertRaisesRegex(AIError,'cancelled'):provider.complete(self.actor,'read',self.sources,cancel)
        self.assertEqual(calls,[1])

    def test_retrieval_authorization_context_and_input_limits(self):
        self.assertEqual([s.id for s in retrieve(self.actor,self.sources,'read')],['a'])
        with self.assertRaises(AccessDenied):retrieve(Actor('r','alpha',Role.REQUESTER),self.sources,'read')
        def forbidden(*_):self.fail('Transport must not be reached')
        provider=self.provider('openai',forbidden)
        for question,sources,reason in [('x'*4001,self.sources,'invalid_input'),
            ('read',[Source('a','alpha','x'*12001)],'context_limit'),
            ('read',[Source('a','alpha','x'),Source('a','alpha','y')],'context_limit')]:
            with self.assertRaisesRegex(AIError,reason):provider.complete(self.actor,question,sources)


class SkillTests(unittest.TestCase):
    def setUp(self):
        self.actor=Actor('staff','alpha',Role.SPECIALIST)
        self.target=SimulatedTarget()
        self.service=JourneyService(MemoryStateStore(),self.target,lambda:datetime(2026,10,8,tzinfo=timezone.utc))
        self.runner=SkillRunner(self.service)

    def test_same_binding_for_interactive_and_automation(self):
        case=self.service.create(self.actor,'Grant reports read access')
        for name,args in [('triage_ticket',{'text':'Grant reports read access'}),
                          ('prepare_resolution',{'case_id':case['id'],'expected_version':1}),
                          ('summarize_operations',{})]:
            left=self.runner.run(name,self.actor,args,'interactive')
            right=self.runner.run(name,self.actor,args,'automation')
            self.assertEqual(left,right)
        self.service.approve(Actor('lead','alpha',Role.SUPERVISOR),case['id'],1)
        state=self.service.execute(self.actor,case['id'],1)
        self.target.complete('alpha',state['action']['id'])
        self.assertEqual(self.runner.run('verify_resolution',self.actor,{'case_id':case['id']},'interactive'),
                         self.runner.run('verify_resolution',self.actor,{'case_id':case['id']},'automation'))

    def test_schema_permissions_and_execution_boundary(self):
        case=self.service.create(self.actor,'Grant reports read access')
        args={'case_id':case['id'],'expected_version':1}
        self.runner.run('prepare_resolution',self.actor,args)
        with self.assertRaisesRegex(JourneyBlocked,'approval_required'):self.service.execute(self.actor,case['id'],1)
        self.assertEqual(self.target.ledger(),[])
        with self.assertRaises(SkillRejected):self.runner.run('approve',self.actor,args)
        with self.assertRaises(SkillRejected):self.runner.run('prepare_resolution',self.actor,{**args,'actor_id':'lead'})
        with self.assertRaises(AccessDenied):self.runner.run('prepare_resolution',Actor('a','alpha',Role.AUDITOR),args)
        with self.assertRaises(Missing):self.runner.run('prepare_resolution',Actor('s','beta',Role.SPECIALIST),args)
        with self.assertRaises(SkillRejected):self.runner.run('summarize_operations',self.actor,{},'untrusted')

    def test_packaged_fixtures_and_versioned_contracts(self):
        root=Path(__file__).resolve().parents[2]/'skills'
        manifest=json.loads((root/'manifest.json').read_text(encoding='utf-8'))
        self.assertEqual(len(manifest['skills']),4)
        for item in manifest['skills']:
            for direction in ('input','output'):
                schema=json.loads((root/item[direction]).read_text(encoding='utf-8'))
                self.assertFalse(schema['additionalProperties'])
                self.assertEqual(set(schema['required']),set(schema['properties']))
            self.assertTrue((root/item['documentation']).is_file())
            self.assertEqual(item['binding'],'service_desk.skills.SkillRunner.run')
        fixtures=json.loads((root/'fixtures.json').read_text(encoding='utf-8'))
        for case in fixtures['triage_cases']:
            for caller in ('interactive','automation'):
                result=self.runner.run('triage_ticket',self.actor,{'text':case['text']},caller)['result']
                sources=result.pop('sources')
                self.assertEqual(result,case['expected'])
                self.assertTrue(all(s.startswith('sop:alpha:') for s in sources))

    def test_second_tenant_uses_same_skill_with_scoped_policy_reference(self):
        beta=Actor('worker','beta',Role.SPECIALIST)
        result=self.runner.run('triage_ticket',beta,{'text':'Grant reports read access'},'automation')
        self.assertEqual(result['result']['sources'],['sop:beta:access-v1'])
        self.assertEqual(self.runner.run('summarize_operations',beta,{})['result']['tenant'],'beta')


if __name__=='__main__':unittest.main()
