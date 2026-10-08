"""Reproducible accepted-scope Phase 6 gate. No credentials/network/model calls."""
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'backend'))
from service_desk.evaluation import summarize,digest


def read(name):return json.loads((ROOT/name).read_text(encoding='utf-8'))


def matches(raw,expected):
    # Git normalizes text on checkout; accept only LF/CRLF representation changes.
    lf=raw.replace(b'\r\n',b'\n')
    return expected in {hashlib.sha256(value).hexdigest() for value in (raw,lf,lf.replace(b'\n',b'\r\n'))}


def main():
    failures=[];passed=[]
    def check(name,callback):
        try:
            if not callback():raise ValueError()
            passed.append(name)
        except Exception:failures.append(name)
    cases=read('evals/phase6-evidence-v1/dataset.json')['cases']
    check('openai_dataset_pin',lambda:digest(read('evals/phase6-evidence-v1/dataset.json'))==read('evals/phase6-evidence-v1/freeze.json')['dataset_sha256'])
    def provider(split):
        report=read(f'docs/phase-6/evidence-v1/openai-{split}.json')
        selected=[c for c in cases if c['split']==split]
        summary=summarize(selected,report['rows'])
        return summary==report['summary'] and summary['quality_gate']
    for split in ('development','heldout'):check('openai_'+split,lambda s=split:provider(s))
    def local():
        report=read('docs/phase-6/local-evidence-v4.json')
        local_cases=read('evals/phase6-local-v4/dataset.json')['cases']
        if report['status'] not in ('passed','failed') or not report['final_unloaded']:return False
        if type(report.get('gpu_offload_observed')) is not bool:return False
        if report['freeze']['dataset_sha256']!=digest(local_cases):return False
        for split in ('development','heldout'):
            selected=[c for c in local_cases if c['split']==split];ids={c['id'] for c in selected}
            summary=summarize(selected,[r for r in report['rows'] if r['id'] in ids])
            if summary!=report['summaries'][split] or summary['unattempted']!=0:return False
        return report['status']=='failed' or (report['recovery']['unloaded_observed'] and report['recovery']['reloaded_valid_response'])
    check('experimental_local_evidence_and_cleanup',local)
    def sources():
        for path in ('evals/phase6-evidence-v1/freeze.json','evals/phase6-local-v4/local-freeze.json'):
            freeze=read(path)
            for name,expected in freeze['source_sha256'].items():
                raw=(ROOT/name).read_bytes()
                if not matches(raw,expected):return False
        return True
    check('frozen_sources',sources)
    def acceptance():
        scope=read('docs/phase-6/accepted-scope.json')
        return (scope['accepted_lab_flow'] and scope['required_profiles_for_this_phase']==['OpenAI']
                and scope['experimental_profiles']==['Ollama'] and not scope['experimental_profiles_claimed_quality_accepted']
                and set(scope['deferred_profiles'])=={'Claude','Grok'} and not scope['deferred_profiles_claimed_live_validated'])
    check('explicit_scope_acceptance',acceptance)
    def pilot():
        report=read('docs/phase-6/business-pilot-results.json')
        return report['status']=='pilot_completed' and report['analysis']['observations']==8 and report['analysis']['roi'] is None
    check('business_pilot_no_invented_roi',pilot)
    def controls():
        r=read('docs/phase-6/selected-output-controls.json')
        names={'evidence-v1/openai-development.json','evidence-v1/openai-heldout.json','local-evidence-v4.json'}
        expected=sum(bool(row['result']) for name in names for row in read('docs/phase-6/'+name)['rows'])
        valid=(set(r['source_reports_sha256'])==names and r['status']=='passed' and r['successful_outputs_tested']==expected
               and all(all(row['checks'].values()) for row in r['rows']))
        return valid and all(matches((ROOT/'docs/phase-6'/name).read_bytes(),sha)
                             for name,sha in r['source_reports_sha256'].items())
    check('real_output_domain_controls',controls)
    commands=[('python',[sys.executable,'-B','-m','unittest','discover','-s','tests'],ROOT/'backend'),
              ('mcp',['node','test/run.mjs'],ROOT/'mcp-server'),
              ('quote_ui',['node','scripts/check_quote_tools.cjs'],ROOT)]
    tests={}
    for name,command,cwd in commands:
        r=subprocess.run(command,cwd=cwd,capture_output=True,text=True,timeout=120)
        tests[name]={'passed':r.returncode==0,'output':(r.stdout+r.stderr)[-2000:]}
        (passed if r.returncode==0 else failures).append(name+'_tests')
    result={'checked_at_utc':datetime.now(timezone.utc).isoformat(),'status':'passed' if not failures else 'incomplete',
            'scope':'Accepted OpenAI advisory lab evaluation; Ollama experimental by explicit user decision; Claude/Grok deferred; not production or ROI',
            'passed':passed,'remaining':failures,'tests':tests}
    (ROOT/'docs/phase-6/phase6-gate.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='tests'},indent=2));return bool(failures)


if __name__=='__main__':sys.exit(main())
