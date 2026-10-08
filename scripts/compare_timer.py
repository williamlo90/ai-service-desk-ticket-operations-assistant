from datetime import datetime,timezone
from hashlib import sha256
import json,secrets,sys
from compare_orchestrators import ROOT,IMAGE,N8N,command,run_candidate


def main():
    run_id=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+secrets.token_hex(3)
    directory=ROOT/'local/timer'/run_id;directory.mkdir(parents=True)
    report={'run_id':run_id,'mode':'synthetic','project_dotenv_read':False,'results':[],
        'python_image':command(['docker','image','inspect',IMAGE,'--format','{{.Id}}']).strip(),
        'n8n_image':N8N,'raw_trace_location':str(directory.relative_to(ROOT)).replace('\\','/')}
    for name in ('code','n8n'):
        print('Testing '+name+' persisted 70-second backoff restart.',flush=True)
        result=run_candidate(name,[],directory,profile='timer',timer=True)
        result.pop('worker_restarted_at_checkpoint',None);report['results'].append(result)
        print(name+': '+result['status']+'; cleanup='+str(result['cleanup_passed'])+(' '+result['error'] if 'error' in result else ''),flush=True)
    paths=[ROOT/p for p in ['scripts/timer_checks.py','scripts/recovery_checks.py','scripts/compare_orchestrators.py',
        'backend/service_desk/recovery.py','backend/comparison/server.py','backend/comparison/recovery_worker.py']]
    report['source_sha256']={str(p.relative_to(ROOT)).replace('\\','/'):sha256(p.read_bytes().replace(b'\r\n',b'\n')).hexdigest() for p in paths}
    report['limitations']=['70-second first backoff only; short in-process n8n waits are not covered',
        'Engine kill/start and service launch are harness actions; no host supervisor deployment tested',
        'Business DB and target remain alive; no distributed leases or transport-failure coverage']
    (ROOT/'docs/phase-5/timer-comparison.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    return 0 if all(r.get('timer',{}).get('status')=='passed' and r['cleanup_passed'] for r in report['results']) else 1


if __name__=='__main__':sys.exit(main())
