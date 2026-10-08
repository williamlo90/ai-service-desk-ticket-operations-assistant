import json
import unittest
from service_desk.ai import Source,ProviderConfig,AIError
from service_desk.clarification import from_evidence,next_step,EvidenceProvider
from service_desk.contracts import Actor,Role


class ClarificationTests(unittest.TestCase):
    def test_present_symptom_is_not_asked_again(self):
        sources=[Source('ticket','alpha','A service returns connection refused; its name is unknown.')]
        raw={'category':'service_incident','facts':[{'source_id':'ticket','quote':'connection refused'}],
             'fields':[{'field':'symptoms','source_id':'ticket','quote':'connection refused'}]}
        self.assertEqual(from_evidence(raw,sources)['missing'],['service_name'])
        self.assertEqual(next_step('service_incident',['service_name']),'clarify')

    def test_complete_incident_and_missing_related_id(self):
        sources=[Source('ticket','alpha','The payroll endpoint returns HTTP 502. IT-55 is the source ticket.')]
        fields=[{'field':f,'source_id':'ticket','quote':q} for f,q in
                [('service_name','payroll endpoint'),('symptoms','HTTP 502')]]
        raw={'category':'service_incident','facts':[],'fields':fields}
        self.assertEqual(from_evidence(raw,sources)['missing'],[])
        raw={'category':'repeated_ticket','facts':[],
             'fields':[{'field':'source_ticket_id','source_id':'ticket','quote':'IT-55'}]}
        result=from_evidence(raw,sources)
        self.assertEqual(result['missing'],['related_ticket_id'])
        self.assertEqual(next_step(result['category'],result['missing']),'clarify')

    def test_unknown_ungrounded_foreign_duplicate_fields_rejected(self):
        sources=[Source('ticket','alpha','HTTP 502')]
        base={'field':'symptoms','source_id':'ticket','quote':'HTTP 502'}
        for fields in ([{**base,'field':'password'}],[{**base,'quote':'healthy'}],
                       [{**base,'source_id':'foreign'}],[base,base],
                       [{**base,'field':'related_ticket_id'}]):
            with self.assertRaises(AIError):from_evidence({'category':'service_incident','facts':[],'fields':fields},sources)

    def test_provider_filters_context_and_retains_actual_usage(self):
        calls=[]
        raw={'category':'service_incident','facts':[{'source_id':'ticket','quote':'HTTP 502'}],
             'fields':[{'field':'symptoms','source_id':'ticket','quote':'HTTP 502'}]}
        def transport(url,headers,payload,timeout):
            calls.append(payload)
            return 200,{'status':'completed','usage':{'input_tokens':50,'output_tokens':25},
                        'output':[{'type':'message','content':[{'type':'output_text','text':json.dumps(raw)}]}]}
        provider=EvidenceProvider(ProviderConfig('openai','test','synthetic'),transport)
        result=provider.complete(Actor('a','alpha',Role.SPECIALIST),'HTTP 502',
                                [Source('ticket','alpha','HTTP 502'),Source('foreign','beta','SECRET')])
        self.assertNotIn('SECRET',json.dumps(calls));self.assertFalse(calls[0]['store'])
        self.assertEqual(result['usage']['input_tokens'],50)
        self.assertEqual(result['data']['missing'],['service_name'])

    def test_transport_detail_suppressed_and_unsupported_has_no_questions(self):
        def transport(*_):raise RuntimeError('sensitive')
        provider=EvidenceProvider(ProviderConfig('openai','test','synthetic'),transport)
        with self.assertRaisesRegex(AIError,'^provider_unavailable$'):
            provider.complete(Actor('a','alpha',Role.SPECIALIST),'test',[])
        self.assertEqual(from_evidence({'category':'unsupported','facts':[],'fields':[]},[])['missing'],[])
        self.assertEqual(next_step('unsupported',[]),'route_out_of_scope')
