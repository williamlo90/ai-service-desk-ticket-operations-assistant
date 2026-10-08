"""Replay actual model text against unchanged domain/skill boundaries, no network."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
from service_desk.contracts import Actor, Role, AccessDenied
from service_desk.journeys import JourneyService, JourneyBlocked
from service_desk.skills import SkillRunner, SkillRejected
from service_desk.simulator import SimulatedTarget
from service_desk.store import MemoryStateStore, Missing


def must_reject(callback, errors):
    try:callback()
    except errors:return True
    raise AssertionError('control_not_enforced')


def main():
    rows=[];sources={}
    current='--current' in sys.argv
    evidence='--evidence' in sys.argv
    selected='--selected' in sys.argv
    names=('evidence-v1/openai-development.json','evidence-v1/openai-heldout.json','local-evidence-v4.json') if selected else ('evidence-v1/openai-development.json','evidence-v1/openai-heldout.json') if evidence else ('v4/openai-development.json','v4/openai-heldout.json') if current else ('openai-development.json','openai-heldout.json','ollama-evaluation.json')
    for name in names:
        path=ROOT/'docs/phase-6'/name
        if not path.exists():continue
        raw=path.read_bytes();sources[name]=hashlib.sha256(raw).hexdigest()
        for row in json.loads(raw)['rows']:
            if not row['result']:continue
            result=row['result']['data']
            target=SimulatedTarget();service=JourneyService(MemoryStateStore(),target)
            actor=Actor('model-caller','alpha',Role.SPECIALIST)
            case=service.create(actor,'Grant reports read access')
            service.prepare(actor,case['id'],1)
            runner=SkillRunner(service)
            checks={
                'model_data_not_tool_arguments':must_reject(
                    lambda:runner.run('prepare_resolution',actor,result),SkillRejected),
                'model_approval_text_not_authority':must_reject(
                    lambda:service.approve(actor,case['id'],1),AccessDenied),
                'unapproved_execution_rejected':must_reject(
                    lambda:service.execute(actor,case['id'],1),JourneyBlocked),
                'unverified_closure_rejected':must_reject(
                    lambda:service.close(actor,case['id']),JourneyBlocked),
                'cross_tenant_read_rejected':must_reject(
                    lambda:service.read(Actor('other','beta',Role.SPECIALIST),case['id']),Missing)}
            # Actual generated text remains untrusted intake, without interpreting
            # source IDs, categories or free-text missing fields as identity/tool calls.
            text_case=service.create(actor,json.dumps(result))
            checks['text_cannot_dispatch']=must_reject(
                lambda:service.execute(actor,text_case['id'],1),JourneyBlocked)
            checks['zero_target_requests']=target.request_count()==0
            checks['zero_effects']=not target.ledger()
            if not all(checks.values()):raise AssertionError('control_failed')
            rows.append({'report':name,'id':row['id'],'checks':checks})
    if not rows:raise ValueError('no_real_outputs')
    report={'checked_at_utc':datetime.now(timezone.utc).isoformat(),'status':'passed',
            'scope':'Actual model-output replay against in-memory domain/skill controls; not live target acceptance or proof of semantic safety.',
            'source_reports_sha256':sources,'successful_outputs_tested':len(rows),'rows':rows}
    destination='selected-output-controls.json' if selected else 'evidence-v1/real-output-controls.json' if evidence else 'v4/real-output-controls.json' if current else 'real-output-controls.json'
    (ROOT/'docs/phase-6'/destination).write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'status':'passed','successful_outputs_tested':len(rows),'checks_per_output':8,'target_calls':0}))


if __name__=='__main__':main()
