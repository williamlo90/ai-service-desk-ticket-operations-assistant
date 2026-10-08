"""Loopback-only evidence extraction. No hosted fallback or credential loading."""
import json
import re
from copy import deepcopy
from time import monotonic
from .ai import AIError,retrieve,http_json,URLS
from .api import strict_object,reject_constant
from .contracts import require_staff
from .clarification import SCHEMA as BASE_SCHEMA,from_evidence
from .local_clarification_v2 import INSTRUCTION as BASE_INSTRUCTION

VERSION='evidence-first-local-v3'
SCHEMA=deepcopy(BASE_SCHEMA)
SCHEMA['properties']['facts']['minItems']=1
SCHEMA['properties']['facts']['items']['properties']['quote']['minLength']=12
INSTRUCTION=BASE_INSTRUCTION+"\nFacts MUST contain at least one exact full sentence from the legitimate ticket, including unsupported tasks. A short ID or error code alone is not a sufficient fact. Copy text exactly; do not translate."
ABSENCE=re.compile(r"\b(?:unknown|unspecified|unidentified|unnamed|not (?:supplied|provided|given|identified|named|known|described)|belum (?:disebutkan|diketahui|diberikan)|tidak diketahui)\b",re.I)
TICKET_ID=re.compile(r"\b[A-Z][A-Z0-9_]*-[1-9][0-9]*\b")


def present_fields(raw):
    """Conservatively omit explicit absence statements and non-ID ticket values."""
    if type(raw) is not dict or type(raw.get('fields')) is not list:
        return raw,[]
    kept=[];discarded=[]
    for item in raw['fields']:
        if type(item) is not dict or set(item)!={'field','source_id','quote'} or not isinstance(item['quote'],str):
            kept.append(item);continue  # Standard validation must reject malformed data.
        reason=None
        if ABSENCE.search(item['quote']):reason='explicit_absence'
        elif item['field'] in ('source_ticket_id','related_ticket_id') and not TICKET_ID.search(item['quote']):
            reason='ticket_id_missing'
        if reason:discarded.append({'evidence':item,'reason':reason})
        else:kept.append(item)
    return {**raw,'fields':kept},discarded

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
            # Validate original shape/grounding before conservatively discarding absent values.
            from_evidence(raw,selected)
            if not raw['facts'] or any(len(f['quote'])<12 for f in raw['facts']):raise AIError('invalid_output')
            raw,discarded=present_fields(raw)
            data=from_evidence(raw,selected)
            usage={key:response.get(source) if type(response.get(source)) is int and response[source]>=0 else None
                   for key,source in [('input_tokens','prompt_eval_count'),('output_tokens','eval_count')]}
            return {'data':data,'field_evidence':raw['fields'],'discarded_field_evidence':discarded,'provider':'ollama','model':self.config.model,
                    'prompt_version':VERSION,'usage':usage,'cost':None,
                    'elapsed_ms':round((monotonic()-started)*1000,3)}
        except AIError:raise
        except Exception:raise AIError('invalid_output') from None
