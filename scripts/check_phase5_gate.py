"""Fail-closed Phase 5 evidence gate; never calls Jira or reads private credentials."""
from datetime import datetime,timezone
from hashlib import sha256
import json,re,subprocess,sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
def main():
    folder=ROOT/'docs/phase-5';checks=[];failures=[]
    reports=['postgres-contract-check.json','lab-connected-check.json','human-approved-access.json',
        'jira-result-write.json','jira-connected-check.json','operator-migration-check.json',
        'job-cutover-check.json','operator-supervisor-check.json','jira-poll-check.json']
    for name in reports:
        try:
            data=json.loads((folder/name).read_text())
            if data['status']!='passed':raise ValueError()
            checks.append(name)
        except Exception:failures.append(name)
    comparison=json.loads((folder/'orchestrator-comparison.json').read_text())
    if not all(r['cleanup_passed'] and all(c['passed'] for c in r['cases']) for r in comparison['candidate_results']):failures.append('reference_comparison')
    if not (ROOT/'docs/architecture/ADR-003-selected-code-led.md').exists():failures.append('architecture_decision')
    py=subprocess.run([sys.executable,'-B','-m','unittest','discover','-s','tests'],cwd=ROOT/'backend',capture_output=True,text=True,timeout=90)
    node=subprocess.run(['node','test/run.mjs'],cwd=ROOT/'mcp-server',capture_output=True,text=True,timeout=90)
    py_count=re.search(r'Ran (\d+) tests',py.stderr);node_count=re.search(r'# pass (\d+)',node.stdout)
    if py.returncode or not py_count:failures.append('python_tests')
    if node.returncode or not node_count:failures.append('node_tests')
    source={}
    for directory,suffixes in [('backend/service_desk',('.py','.html','.js')),('mcp-server/src',('.ts',)),('scripts',('.py','.ps1'))]:
        for path in sorted((ROOT/directory).rglob('*')):
            if path.is_file() and path.suffix in suffixes:source[str(path.relative_to(ROOT)).replace('\\','/')]=sha256(path.read_bytes()).hexdigest()
    report={'status':'passed' if not failures else 'incomplete','checked_at':datetime.now(timezone.utc).isoformat(),
        'selected_architecture':'code-led','passed_evidence':checks,'remaining':failures,
        'python_tests':int(py_count[1]) if py_count else None,'node_tests':int(node_count[1]) if node_count else None,
        'source_sha256':source,'scope':'local V1 integration gate; not Phase 6 model evaluation or Phase 7 release hardening'}
    (folder/'phase5-gate.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='source_sha256'},indent=2))
    return 0 if not failures else 1

if __name__=='__main__':sys.exit(main())
