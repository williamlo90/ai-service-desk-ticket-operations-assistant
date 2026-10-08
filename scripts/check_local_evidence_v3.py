"""Pinned local-model quality and unload/reload acceptance. No hosted/key access."""
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import sys
from urllib.request import Request,build_opener

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'backend'))
from service_desk.ai import Source,ProviderConfig,AIError
from service_desk.jira import NoRedirect
from service_desk.contracts import Actor,Role
from service_desk.local_clarification_v3 import LocalEvidenceProvider,OPTIONS,INSTRUCTION,VERSION
from service_desk.local_clarification_v3 import SCHEMA
from service_desk.evaluation import summarize,digest

MODEL='qwen3:4b-instruct'
REPORT=ROOT/'docs/phase-6/local-evidence-v3.json'
FREEZE=ROOT/'evals/phase6-local-v3/local-freeze.json'


def local(path,payload=None):
    if path not in ('tags','show','ps','version','generate'):raise ValueError('path')
    req=Request('http://127.0.0.1:11434/api/'+path,data=json.dumps(payload).encode() if payload is not None else None,
                headers={'Content-Type':'application/json'})
    with build_opener(NoRedirect()).open(req,timeout=60) as response:
        raw=response.read(262145)
        if len(raw)>262144:raise ValueError('oversized')
        return json.loads(raw)


def main():
    if REPORT.exists():raise ValueError('prior_report_exists')
    model=next(m for m in local('tags')['models'] if m['name']==MODEL)
    if not model['digest'].startswith('0edcdef34593'):raise ValueError('unexpected_artifact')
    info=local('show',{'model':MODEL})
    if 'Apache License' not in info.get('license','') or 'Version 2.0' not in info['license']:
        raise ValueError('license_unconfirmed')
    cases=json.loads((ROOT/'evals/phase6-local-v3/dataset.json').read_text())['cases']
    sources=('backend/service_desk/local_clarification_v2.py','backend/service_desk/local_clarification_v3.py','backend/service_desk/local_clarification.py','backend/service_desk/clarification.py',
             'backend/service_desk/ai.py','backend/service_desk/evaluation.py','scripts/check_local_evidence_v3.py')
    freeze={'frozen_before_calls':True,'model':MODEL,'digest':model['digest'],'dataset_sha256':digest(cases),
            'schema_sha256':digest(SCHEMA),'instruction_sha256':digest(INSTRUCTION),'prompt_version':VERSION,
            'options':OPTIONS,'think':False,'timeout_seconds':60,'concurrency':1,
            'source_sha256':{name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in sources}}
    with FREEZE.open('x',encoding='utf-8') as f:f.write(json.dumps(freeze,indent=2)+'\n')
    report={'checked_at_utc':datetime.now(timezone.utc).isoformat(),'provider':'ollama','freeze':freeze,
            'runtime':local('version'),'model_bytes':model['size'],'details':info['details'],
            'license':'Apache-2.0','license_sha256':hashlib.sha256(info['license'].encode()).hexdigest(),
            'cost_usd':None,'cost_note':'Hardware/electricity not measured; no hosted requests.',
            'status':'running','rows':[]}
    def save():REPORT.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    save()
    provider=LocalEvidenceProvider(ProviderConfig('ollama',MODEL,local_only=True))
    def complete(case):
        actor=Actor('local-evidence-evaluator',case['tenant'],Role.SPECIALIST)
        return provider.complete(actor,case['text'],[Source('ticket',case['tenant'],case['text']),
            Source('foreign','beta' if case['tenant']=='alpha' else 'alpha','FOREIGN_CANARY')])
    try:
        report['warmup']=complete(cases[0]);save()
        report['loaded_model']=next(m for m in local('ps')['models'] if m['name']==MODEL)
        report['gpu_offload_observed']=report['loaded_model'].get('size_vram',0)>0
        print(json.dumps({'warmup':'passed','gpu_offload_observed':report['gpu_offload_observed']}),flush=True)
        for split in ('development','heldout'):
            selected=[c for c in cases if c['split']==split];rows=[]
            for case in selected:
                if not any(m['name']==MODEL and m['digest']==model['digest'] for m in local('tags')['models']):
                    raise ValueError('model_changed')
                row={'id':case['id'],'result':None,'error':None}
                try:
                    result=complete(case)
                    if 'FOREIGN_CANARY' in json.dumps(result):raise AIError('scope_leak')
                    row['result']=result
                except AIError as error:
                    known={'invalid_output','unsupported_fact','provider_unavailable','provider_rejected','rate_limited','scope_leak'}
                    row['error']=str(error) if str(error) in known else 'evaluation_failed'
                report['rows'].append(row);rows.append(row)
                report.setdefault('summaries',{})[split]=summarize(selected,rows);save()
                print(json.dumps({'case':case['id'],'status':row['error'] or 'validated'}),flush=True)
                if row['error'] in ('provider_unavailable','provider_rejected','rate_limited'):
                    raise ValueError('runtime_failure')
            if not report['summaries'][split]['quality_gate']:raise ValueError('quality_failed')
        # Controlled model unload/reload only; no daemon/container/process is stopped.
        local('generate',{'model':MODEL,'prompt':'','keep_alive':0,'stream':False})
        unloaded=not any(m['name']==MODEL for m in local('ps')['models'])
        recovery=complete(cases[0])
        report['recovery']={'unloaded_observed':unloaded,'reloaded_valid_response':True,
                            'probe':recovery,'scope':'model unload/reload; not daemon crash or OOM'}
        report['status']='passed' if unloaded else 'recovery_unconfirmed'
    except Exception:
        report['status']='failed';report['error']='check_quality_or_runtime_evidence';save()
    finally:
        try:
            local('generate',{'model':MODEL,'prompt':'','keep_alive':0,'stream':False})
            report['final_unloaded']=not any(m['name']==MODEL for m in local('ps')['models'])
        except Exception:report['final_unloaded']=False
        save()
    print(json.dumps({'status':report['status'],'summaries':report.get('summaries',{}),
                      'final_unloaded':report['final_unloaded']}))
    if report['status']!='passed':sys.exit(1)


if __name__=='__main__':
    try:main()
    except Exception:
        print('Local check stopped; no secret or raw exception details displayed.');sys.exit(1)
