import json
import unittest
from service_desk.ai import ProviderConfig,AIError,Source
from service_desk.contracts import Actor,Role
from service_desk.local_clarification import LocalEvidenceProvider


class LocalClarificationTests(unittest.TestCase):
    def test_local_contract_grounding_usage_and_context_filter(self):
        calls=[]
        raw={'category':'service_incident','facts':[{'source_id':'ticket','quote':'connection refused'}],
             'fields':[{'field':'symptoms','source_id':'ticket','quote':'connection refused'}]}
        def transport(url,headers,payload,timeout):
            calls.append((url,headers,payload,timeout))
            return 200,{'done':True,'message':{'content':json.dumps(raw)},'prompt_eval_count':100,'eval_count':50}
        p=LocalEvidenceProvider(ProviderConfig('ollama','fixture',local_only=True),transport)
        result=p.complete(Actor('a','alpha',Role.SPECIALIST),'connection refused',
                          [Source('ticket','alpha','connection refused'),Source('foreign','beta','HIDDEN')])
        self.assertEqual(result['data']['missing'],['service_name'])
        self.assertEqual(result['usage']['output_tokens'],50)
        self.assertEqual(calls[0][0],'http://127.0.0.1:11434/api/chat')
        self.assertEqual(calls[0][1],{});self.assertEqual(calls[0][3],60)
        self.assertNotIn('HIDDEN',json.dumps(calls));self.assertFalse(calls[0][2]['think'])

    def test_failure_never_falls_back_and_errors_are_sanitized(self):
        calls=[]
        def unavailable(*args):calls.append(args[0]);raise TimeoutError('secret')
        p=LocalEvidenceProvider(ProviderConfig('ollama','fixture',local_only=True),unavailable)
        with self.assertRaisesRegex(AIError,'^provider_unavailable$'):
            p.complete(Actor('a','alpha',Role.SPECIALIST),'test',[])
        self.assertEqual(calls,['http://127.0.0.1:11434/api/chat'])
        with self.assertRaises(ValueError):LocalEvidenceProvider(ProviderConfig('openai','fixture','synthetic'))

    def test_malformed_output_and_foreign_evidence_rejected(self):
        for response in ({'done':False,'message':{'content':'{}'}},
                         {'done':True,'message':{'content':'not json'}},
                         {'done':True,'message':{'content':json.dumps({'category':'service_incident','facts':[],
                          'fields':[{'field':'symptoms','source_id':'foreign','quote':'hidden'}]})}}):
            p=LocalEvidenceProvider(ProviderConfig('ollama','fixture',local_only=True),lambda *_:(200,response))
            with self.assertRaises(AIError):p.complete(Actor('a','alpha',Role.SPECIALIST),'test',[])
