"""Constrain local fact quotes to actual source sentences before inference."""
from copy import deepcopy
import json
import re
from .ai import http_json,AIError
from .local_clarification_v3 import LocalEvidenceProvider as BaseProvider,SCHEMA,INSTRUCTION,OPTIONS

VERSION='evidence-first-local-v4'


def source_schema(payload):
    sources=json.loads(payload['messages'][-1]['content'])['sources']
    candidates=[]
    for source in sources:
        text=source['text']
        candidates.extend([text,*re.split(r'(?<=[.!?])\s+',text)])
    candidates=list(dict.fromkeys(s for s in candidates if len(s)>=12))
    if not candidates:raise AIError('insufficient_source_context')
    schema=deepcopy(SCHEMA)
    quote=schema['properties']['facts']['items']['properties']
    quote['quote']={'type':'string','enum':candidates}
    quote['source_id']={'type':'string','enum':[s['id'] for s in sources]}
    return schema


class LocalEvidenceProvider(BaseProvider):
    def __init__(self,config,transport=http_json):
        def with_source_quotes(url,headers,payload,timeout):
            payload={**payload,'format':source_schema(payload)}
            return transport(url,headers,payload,timeout)
        super().__init__(config,with_source_quotes)

    def complete(self,actor,question,sources):
        result=super().complete(actor,question,sources)
        result['prompt_version']=VERSION
        return result
