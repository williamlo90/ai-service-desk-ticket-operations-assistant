"""Bounded native wait/restart check for each actual orchestration engine."""
from datetime import datetime,timezone
from hashlib import sha256
import json,secrets,sys
from compare_orchestrators import ROOT,N8N,IMAGE,command,run_candidate


def main():
    run_id=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+secrets.token_hex(3)
    directory=ROOT/'local/native-wait'/run_id;directory.mkdir(parents=True)
    report={'run_id':run_id,'mode':'synthetic','project_dotenv_read':False,'model_calls':0,
        'python_image':command(['docker','image','inspect',IMAGE,'--format','{{.Id}}']).strip(),
        'n8n_image':N8N,'results':[],'engine_winner':None}
    for name in ('code','n8n'):
        print('Testing '+name+' durable approval and target waits.',flush=True)
        result=run_candidate(name,[],directory,native=True)
        # The linear runner's segment marker does not describe native restarts.
        result.pop('worker_restarted_at_checkpoint',None)
        report['results'].append(result)
        print(name+': '+result['status']+'; cleanup='+str(result['cleanup_passed'])+
              ('; '+result['error'] if 'error' in result else ''),flush=True)
    report['source_sha256']={str(p.relative_to(ROOT)).replace('\\','/'):sha256(p.read_bytes().replace(b'\r\n',b'\n')).hexdigest()
        for p in [ROOT/'backend/comparison/wait_worker.py',ROOT/'backend/comparison/server.py',
                  ROOT/'scripts/native_wait_checks.py',ROOT/'scripts/compare_orchestrators.py']}
    report['raw_trace_location']=str(directory.relative_to(ROOT)).replace('\\','/')
    report['limitations']=['One synthetic access journey, two wait checkpoints per engine',
        'Code worker is single-instance polling with durable SQLite checkpoint; distributed leases/backoff pending',
        'External approval and target events are authenticated fixture-controller actions, not live platforms',
        'Business PostgreSQL and fixture target remain running during engine restarts',
        'Maintenance effort, broader native negative-case pack and production deployment remain pending']
    (ROOT/'docs/phase-5/native-wait-comparison.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    return 0 if all(r.get('native_wait',{}).get('status')=='passed' and r['cleanup_passed'] for r in report['results']) else 1


if __name__=='__main__':sys.exit(main())
