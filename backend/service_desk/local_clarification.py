"""Loopback-only evidence extraction. No hosted fallback or credential loading."""
import json
from time import monotonic
from .ai import AIError,retrieve,http_json,URLS
from .api import strict_object,reject_constant
from .contracts import require_staff
from .clarification import SCHEMA,INSTRUCTION,VERSION,from_evidence

OPTIONS={'num_ctx':4096,'num_predict':1000,'num_thread':2,'num_gpu':99,'temperature':0,'seed':42}


class LocalEvidenceProvider:
    def __init__(self,config,transport=http_json):
        if config.provider!='ollama' or not config.local_only or config.api_key:
            raise ValueError('local_configuration_required')
        self.config=config;self.transport=transport

    def complete(self,actor,question,sources):
        require_staff(actor,actor.tenant_id)
        if not isinstance(question,str) or not 1<=len(question)<=4000:raise AIError('invalid_input')
        selected=retrieve(actor,sources,question)
        if len({s.id for s in selected})!=len(selected) or sum(len(s.text) for s in selected)>12000:
            raise AIError('context_limit')
        content=json.dumps({'ticket':question,'sources':[{'id':s.id,'text':s.text} for s in selected]})
        payload={'model':self.config.model,'messages':[{'role':'system','content':INSTRUCTION},
                 {'role':'user','content':content}],'format':SCHEMA,'stream':False,'think':False,
                 'options':dict(OPTIONS),'keep_alive':'2m'}
        started=monotonic()
        try:status,response=self.transport(URLS['ollama'],{},payload,60)
        except Exception:raise AIError('provider_unavailable') from None
        if status!=200:raise AIError('rate_limited' if status==429 else 'provider_rejected')
        try:
            if response.get('done') is not True or len(json.dumps(response))>65536:raise ValueError()
            raw=json.loads(response['message']['content'],object_pairs_hook=strict_object,parse_constant=reject_constant)
            data=from_evidence(raw,selected)
            usage={key:response.get(source) if type(response.get(source)) is int and response[source]>=0 else None
                   for key,source in [('input_tokens','prompt_eval_count'),('output_tokens','eval_count')]}
            return {'data':data,'field_evidence':raw['fields'],'provider':'ollama','model':self.config.model,
                    'prompt_version':VERSION,'usage':usage,'cost':None,
                    'elapsed_ms':round((monotonic()-started)*1000,3)}
        except AIError:raise
        except Exception:raise AIError('invalid_output') from None
