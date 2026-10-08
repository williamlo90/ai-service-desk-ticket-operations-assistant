"""Run isolated recovery comparison. Never reads project .env."""
from datetime import datetime,timezone
from hashlib import sha256
import json,secrets,sys
from compare_orchestrators import ROOT,N8N,IMAGE,command,run_candidate


def main():
    run_id=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+secrets.token_hex(3)
    directory=ROOT/'local/recovery'/run_id;directory.mkdir(parents=True)
    report={'run_id':run_id,'mode':'synthetic','project_dotenv_read':False,'results':[],
        'python_image':command(['docker','image','inspect',IMAGE,'--format','{{.Id}}']).strip(),
        'n8n_image':N8N,'engine_winner':None,'raw_trace_location':str(directory.relative_to(ROOT)).replace('\\','/')}
    for name in ('code','n8n'):
        result=run_candidate(name,[],directory,recovery=True)
        result.pop('worker_restarted_at_checkpoint',None)
        report['results'].append(result)
        print(name+': '+result['status']+'; cleanup='+str(result['cleanup_passed'])+
              ('; '+result['error'] if 'error' in result else ''),flush=True)
    paths=[ROOT/'backend/service_desk/recovery.py',ROOT/'backend/service_desk/journeys.py',
           ROOT/'scripts/recovery_checks.py',ROOT/'scripts/compare_orchestrators.py',ROOT/'scripts/compare_recovery.py',
           *sorted((ROOT/'backend/comparison').glob('*.py'))]
    report['source_sha256']={str(p.relative_to(ROOT)).replace('\\','/'):sha256(p.read_bytes().replace(b'\r\n',b'\n')).hexdigest() for p in paths}
    report['limitations']=['Synthetic fixture approvals/target; no live credentials or model calls',
        'Shared single-worker recovery policy; native code/n8n timer scheduling, not independent policy implementations',
        'n8n waits under 65 seconds are in-process; timer crash/lease and transport retry coverage pending',
        'Retries are authoritative read-back only; uncertain mutations are never resubmitted',
        'Review queue is persisted case escalation, not an operator UI or external notification']
    (ROOT/'docs/phase-5/recovery-comparison.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    return 0 if all(r.get('recovery',{}).get('status')=='passed' and r['cleanup_passed'] for r in report['results']) else 1


if __name__=='__main__':sys.exit(main())
