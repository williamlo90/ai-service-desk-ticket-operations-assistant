from datetime import datetime,timezone
from hashlib import sha256
import json,secrets,sys
from compare_orchestrators import ROOT,IMAGE,N8N,command,run_candidate


def main():
    run_id=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+secrets.token_hex(3)
    directory=ROOT/'local/transport'/run_id;directory.mkdir(parents=True)
    report={'run_id':run_id,'mode':'synthetic','project_dotenv_read':False,'results':[],
        'python_image':command(['docker','image','inspect',IMAGE,'--format','{{.Id}}']).strip(),
        'n8n_image':N8N,'raw_trace_location':str(directory.relative_to(ROOT)).replace('\\','/')}
    for name in ('code','n8n'):
        result=run_candidate(name,[],directory,transport=True)
        result.pop('worker_restarted_at_checkpoint',None);report['results'].append(result)
        print(name+': '+result['status']+'; cleanup='+str(result['cleanup_passed'])+(' '+result['error'] if 'error' in result else ''),flush=True)
    paths=[ROOT/p for p in ['scripts/transport_checks.py','scripts/compare_orchestrators.py',
        'backend/service_desk/http_retry.py','backend/service_desk/recovery.py','backend/service_desk/postgres.py',
        'backend/comparison/server.py','backend/comparison/recovery_worker.py']]
    report['source_sha256']={str(p.relative_to(ROOT)).replace('\\','/'):sha256(p.read_bytes().replace(b'\r\n',b'\n')).hexdigest() for p in paths}
    report['limitations']=['PostgreSQL transaction advisory lock coordinates cooperative recovery ticks; aggregate CAS remains required',
        'Two worker processes share one fixture API; separate holder is killed to prove lock release',
        'n8n built-in retry permits four attempts with fixed 1s delays and retries 401 too; code fails terminal HTTP immediately',
        '429 test has Retry-After 1; arbitrary rate-limit delays not proven for n8n',
        'Transport exhaustion recorded in worker SQLite/n8n error execution; central case review synchronization pending',
        'No lease fencing across network partitions, no live targets and no final architecture winner']
    (ROOT/'docs/phase-5/transport-comparison.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    return 0 if all(r.get('transport',{}).get('status')=='passed' and r['cleanup_passed'] for r in report['results']) else 1


if __name__=='__main__':sys.exit(main())
