"""Release gate using current tests and bounded connected lab evidence."""
from datetime import datetime,timezone
from hashlib import sha256
import json,re,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]


def main():
    failures=[];evidence={}
    names=['docs/phase-7/release-lab.json','docs/phase-6/phase6-gate.json',
           'docs/phase-5/operator-migration-check.json','docs/phase-5/job-cutover-check.json',
           'docs/phase-5/operator-supervisor-check.json']
    for name in names:
        raw=(ROOT/name).read_bytes();r=json.loads(raw)
        if r['status']!='passed':failures.append(name)
        evidence[name]=sha256(raw).hexdigest()
    lab=json.loads((ROOT/names[0]).read_text())
    if not lab['temporary_database_removed'] or lab['live_target_calls']!=0:failures.append('isolated_cleanup')
    w=lab['workload']
    if w['soak_wall_seconds']<60 or any(w[k]['errors'] or w[k]['completed']<1 for k in ('normal','peak_concurrency_4','soak')):failures.append('workload')
    health=json.loads((ROOT/'docs/phase-7/operator-health.json').read_text())
    if health['status']!='ready':failures.append('operator_readiness')
    tests={}
    for name,args,cwd in [('python',[sys.executable,'-B','-m','unittest','discover','-s','tests'],ROOT/'backend'),
                          ('mcp',['node','test/run.mjs'],ROOT/'mcp-server'),
                          ('javascript',['node','scripts/check_quote_tools.cjs'],ROOT)]:
        r=subprocess.run(args,cwd=cwd,capture_output=True,text=True,timeout=120)
        output=r.stdout+r.stderr
        match=re.search(r'Ran (\d+) tests' if name=='python' else r'# pass (\d+)' if name=='mcp' else r'(\d+) quote/',output)
        tests[name]={'passed':r.returncode==0,'count':int(match[1]) if match else None}
        if r.returncode or not match:failures.append(name+'_tests')
    sources={}
    for directory in ('backend/service_desk','scripts'):
        for path in sorted((ROOT/directory).glob('*.py')):
            sources[path.relative_to(ROOT).as_posix()]=sha256(path.read_bytes().replace(b'\r\n',b'\n')).hexdigest()
    result={'status':'passed' if not failures else 'incomplete','checked_at_utc':datetime.now(timezone.utc).isoformat(),
            'scope':'bounded local lab release; manual host startup; Azure deferred',
            'remaining':failures,'tests':tests,'evidence_sha256':evidence,'source_lf_sha256':sources,
            'not_claimed':['physical host reboot','long-duration endurance','wire-level network partition fencing',
                           'live SaaS/model throughput','production or cloud readiness']}
    (ROOT/'docs/phase-7/phase7-gate.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('source_lf_sha256','evidence_sha256')},indent=2))
    return bool(failures)


if __name__=='__main__':sys.exit(main())
