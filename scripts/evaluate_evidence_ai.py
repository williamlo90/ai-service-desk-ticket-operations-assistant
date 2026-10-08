"""Bounded evidence-first evaluation; prior measured usage settles reservations.

Unknown or interrupted calls retain their full reservation. The cumulative $1
cap is unchanged. All reports are immutable per split; no automatic retry.
"""
import argparse
from datetime import datetime,timezone
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import sys
from evaluate_ai import ROOT,MODEL,load_key,guarded_transport
from service_desk.ai import ProviderConfig,Source,AIError
from service_desk.contracts import Actor,Role
from service_desk.clarification import EvidenceProvider,SCHEMA,INSTRUCTION,VERSION
from service_desk.evaluation import digest,summarize

DIRECTORY=ROOT/'docs/phase-6/evidence-v1'
DATA=ROOT/'evals/phase6-evidence-v1/dataset.json'
FREEZE=ROOT/'evals/phase6-evidence-v1/freeze.json'
CAP=Decimal('1.00');RESERVE=Decimal('0.02')
SOURCES=('backend/service_desk/clarification.py','backend/service_desk/ai.py',
         'backend/service_desk/evaluation.py','scripts/evaluate_evidence_ai.py','scripts/evaluate_ai.py')


def measured_cost(row):
    result=row.get('result')
    if not result or result.get('model')!=MODEL:return None
    usage=result.get('usage',{})
    values=[usage.get(k) for k in ('input_tokens','output_tokens')]
    if any(type(v) is not int or v<0 for v in values):return None
    return (Decimal(values[0])*Decimal('.4')+Decimal(values[1])*Decimal('1.6'))/Decimal(1000000)


def spend(reservations,reports):
    if len({r['identity'] for r in reservations})!=len(reservations):raise ValueError('duplicate_reservation')
    total=Decimal(0);settled=0
    for row in reservations:
        cost=measured_cost(reports.get(row['identity'],{}))
        if cost is None:cost=Decimal(row['reserved_usd'])
        else:settled+=1
        if not cost.is_finite() or cost<0:raise ValueError('invalid_cost')
        total+=cost
    return total,settled


def report_index():
    rows={}
    for prefix,folder in (('',ROOT/'docs/phase-6'),('v2:',ROOT/'docs/phase-6/v2'),
                          ('v3:',ROOT/'docs/phase-6/v3'),('v4:',ROOT/'docs/phase-6/v4'),
                          ('evidence-v1:',DIRECTORY)):
        for split in ('canary','development','heldout'):
            path=folder/f'openai-{split}.json'
            if path.exists():
                for row in json.loads(path.read_text())['rows']:rows[prefix+split+':'+row['id']]=row
    return rows


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--live',action='store_true')
    parser.add_argument('--split',choices=['development','heldout'],default='development');args=parser.parse_args()
    data=json.loads(DATA.read_text());freeze=json.loads(FREEZE.read_text())
    actual={'dataset_sha256':digest(data),'schema_sha256':digest(SCHEMA),'instruction_sha256':digest(INSTRUCTION),
            'prompt_version':VERSION,'model':MODEL,
            'source_sha256':{name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in SOURCES}}
    if any(freeze.get(k)!=v for k,v in actual.items()):raise ValueError('freeze_mismatch')
    cases=[c for c in data['cases'] if c['split']==args.split]
    if len(cases)!=(4 if args.split=='development' else 16):raise ValueError('dataset_count')
    if not args.live:
        print(json.dumps({'status':'offline_ready','cases':len(cases),'calls':0}));return
    key=load_key();local=ROOT/'local/phase6'
    lock=(local/'runner.lock').open('a+b');lock.seek(0)
    import msvcrt
    msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
    journal=local/'reservations.jsonl'
    reservations=[json.loads(line) for line in journal.read_text().splitlines()]
    DIRECTORY.mkdir(parents=True,exist_ok=True)
    path=DIRECTORY/f'openai-{args.split}.json'
    if path.exists():raise ValueError('already_run')
    if args.split=='heldout':
        development=json.loads((DIRECTORY/'openai-development.json').read_text())
        if not development['summary']['quality_gate'] or development['freeze']!=freeze:raise ValueError('development_required')
    total,settled=spend(reservations,report_index())
    report={'checked_at_utc':datetime.now(timezone.utc).isoformat(),'kind':'real_provider',
            'model':MODEL,'freeze':freeze,'split':args.split,'rows':[],
            'budget':{'cap_usd':str(CAP),'reservation_usd':str(RESERVE),
                      'previous_calls_settled_from_usage':settled,'previous_accounted_usd':str(total),
                      'basis':'uncached published token rates; unknown calls retain reservation; invoice unknown'}}
    provider=EvidenceProvider(ProviderConfig('openai',MODEL,key),guarded_transport)
    for case in cases:
        identity='evidence-v1:'+args.split+':'+case['id']
        if any(r['identity']==identity for r in reservations):raise ValueError('prior_attempt')
        total,_=spend(reservations,report_index())
        if total+RESERVE>CAP:report['stop_reason']='budget_exhausted';break
        entry={'identity':identity,'reserved_usd':str(RESERVE)}
        with journal.open('a') as f:f.write(json.dumps(entry)+'\n');f.flush();os.fsync(f.fileno())
        reservations.append(entry)
        row={'id':case['id'],'result':None,'error':None}
        try:
            result=provider.complete(Actor('evidence-evaluator',case['tenant'],Role.SPECIALIST),case['text'],
                                    [Source('ticket',case['tenant'],case['text']),Source('foreign','beta' if case['tenant']=='alpha' else 'alpha','FOREIGN_CANARY')])
            if key in json.dumps(result) or 'FOREIGN_CANARY' in json.dumps(result):raise AIError('unsafe_output')
            row['result']=result;cost=measured_cost(row);row['estimated_cost_usd']=float(cost) if cost is not None else None
        except AIError as error:
            allowed={'invalid_output','unsupported_fact','provider_unavailable','provider_rejected','rate_limited','unsafe_output'}
            row['error']=str(error) if str(error) in allowed else 'evaluation_failed'
        report['rows'].append(row);report['summary']=summarize(cases,report['rows'])
        path.write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps({'case':case['id'],'status':row['error'] or 'validated'}),flush=True)
        if row['error'] in ('provider_unavailable','provider_rejected','rate_limited'):
            report['stop_reason']=row['error'];break
    report['summary']=summarize(cases,report['rows'])
    total,settled=spend(reservations,report_index())
    report['budget'].update(accounted_total_usd=str(total),settled_calls=settled)
    path.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report['summary']))


if __name__=='__main__':
    try:main()
    except Exception:
        print('Evaluation stopped: check freeze, budget or prior attempt. No sensitive details displayed.');sys.exit(1)
