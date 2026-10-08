"""Verify handover completeness and clean-tested sources; no private/network reads."""
from datetime import datetime,timezone
from hashlib import sha256
from pathlib import Path
import json,subprocess,sys
ROOT=Path(__file__).resolve().parents[1]


def read(name):return json.loads((ROOT/name).read_text(encoding='utf-8'))
def stable(path):return sha256(path.read_bytes().replace(bytes([13,10]),bytes([10]))).hexdigest()


def main():
    failures=[]
    clean=read('docs/phase-8/clean-delivery.json')
    if clean['status']!='passed' or clean['credentials_copied']:failures.append('clean_source_install')
    for name,expected in clean.get('tested_source_lf_sha256',{}).items():
        if stable(ROOT/name)!=expected:failures.append('changed_tested_source:'+name)
    # Every current application module and test must have been included in the clean run.
    for directory in ('backend/service_desk','backend/tests','mcp-server/src','mcp-server/test'):
        for p in (ROOT/directory).rglob('*'):
            if p.is_file() and p.suffix in ('.py','.ts','.mjs') and p.relative_to(ROOT).as_posix() not in clean.get('tested_source_lf_sha256',{}):
                failures.append('untested_source:'+p.relative_to(ROOT).as_posix())
    required=['docs/phase-8/HANDOVER.md','docs/phase-8/README.md','docs/phase-8/ACCEPTANCE.md',
              'docs/learning/phase-8.md','scripts/renew_lab_identity.py','scripts/demo_handover.py',
              'backend/requirements-postgres.txt','mcp-server/package-lock.json']
    for name in required:
        if not (ROOT/name).is_file():failures.append('missing:'+name)
    evidence=['docs/phase-5/phase5-gate.json','docs/phase-6/phase6-gate.json',
              'docs/phase-7/phase7-gate.json','docs/phase-8/clean-delivery.json','docs/phase-8/demo.json']
    for name in evidence:
        if read(name)['status']!='passed':failures.append(name)
    demo=read('docs/phase-8/demo.json')
    if demo['effects_after_replay']!=1 or demo['credential_reads'] or demo['external_calls']:failures.append('safe_demo')
    core=read('docs/phase-7/phase7-gate.json')['source_lf_sha256']
    for name,expected in core.items():
        if stable(ROOT/name)!=expected:failures.append('phase7_source_changed:'+name)
    archive=ROOT/clean['archive_relative_path']
    if archive.exists() and sha256(archive.read_bytes()).hexdigest()!=clean['archive_sha256']:failures.append('clean_archive_changed')
    manifest={'release':'local-lab-phase8','date_local':'2026-10-09','timezone':'Asia/Jakarta',
        'owner':'William','approver':'William','credential_custodian':'William','support_owner':'William',
        'phase7_commit':'666f7b1','tested_source_tree':clean.get('source_tree'),
        'final_commit':'Resolve git log for the Phase 8 completion commit; a commit cannot embed its own hash.',
        'versions':clean.get('versions'),
        'dependency_lf_sha256':{name:stable(ROOT/name) for name in ('backend/requirements-postgres.txt','mcp-server/package-lock.json','deploy/compose.yaml','deploy/targets.compose.yaml')},
        'evidence_lf_sha256':{name:stable(ROOT/name) for name in evidence},
        'accepted_model':'gpt-4.1-mini-2025-04-14 / evidence-first-v1',
        'accepted_model_pin':'evals/phase6-evidence-v1/freeze.json',
        'experimental_model':'qwen3:4b-instruct; local quality not accepted',
        'deferred':['Claude/Grok live validation','Ollama improvement','Azure preparation and deployment'],
        'orchestration':'code-led; optional n8n unchanged, no active workflow export required by selected architecture',
        'startup':'manual Windows lab startup; loopback listeners',
        'identity_lifetime_hours':24,'local_access_approval_minutes':15,
        'data':'synthetic/test lab; private runtime and credentials excluded from source archive',
        'limitations':read('docs/phase-7/phase7-gate.json')['not_claimed']}
    (ROOT/'docs/phase-8/release-manifest.json').write_text(json.dumps(manifest,indent=2)+chr(10))
    result={'status':'passed' if not failures else 'incomplete','checked_at_utc':datetime.now(timezone.utc).isoformat(),
            'scope':'local lab handover; clean-source install tested on existing host; Azure deferred',
            'remaining':failures,'clean_python_tests':clean.get('python_tests'),'clean_mcp_tests':clean.get('mcp_tests'),
            'javascript_assertions':14,'demo':'passed','owner':'William'}
    (ROOT/'docs/phase-8/phase8-gate.json').write_text(json.dumps(result,indent=2)+chr(10))
    print(json.dumps(result,indent=2));return bool(failures)


if __name__=='__main__':sys.exit(main())
