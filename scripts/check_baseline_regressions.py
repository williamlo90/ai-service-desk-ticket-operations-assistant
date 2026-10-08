"""Restore the frozen credential-free source backup and run bounded old tests."""
from pathlib import Path,PurePosixPath
from datetime import datetime,timezone
from hashlib import sha256
import json,os,subprocess,sys,zipfile
from xml.etree import ElementTree

ROOT=Path(__file__).resolve().parents[1]
BACKUP=Path('C:/Users/William/.codex/project-backups/service-desk-phase0-20261008')
PYTHON=Path('C:/Users/William/OneDrive/Dokumen/Agentic Project/case-resolution-copilot-rebuild/backend/.venv/Scripts/python.exe')
TESTS=['test_action_recovery_policy','test_review_snapshot','test_production_validation_faults',
       'test_case_webhook','test_action_service','test_action_gateway','test_review_authority',
       'test_review_service','test_review_action_materialization','test_case_domain','test_workflow_evaluation']


def main():
    run_id=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    directory=ROOT/'local/baseline'/run_id;directory.mkdir(parents=True)
    manifest=json.loads((BACKUP/'manifest.json').read_text())
    for entry in manifest:
        assert sha256((BACKUP/entry['path']).read_bytes()).hexdigest().upper()==entry['sha256'].upper()
    with zipfile.ZipFile(BACKUP/'baseline-head.zip') as archive:
        for entry in archive.infolist():
            name=PurePosixPath(entry.filename)
            assert not name.is_absolute() and '..' not in name.parts
            if any(part.startswith('.env') for part in name.parts) or entry.is_dir():continue
            target=directory.joinpath(*name.parts);target.parent.mkdir(parents=True,exist_ok=True)
            target.write_bytes(archive.read(entry))
    for entry in manifest:
        relative=Path(entry['path'])
        if relative.parts[0]!='overlay':continue
        assert not any(part.startswith('.env') for part in relative.parts)
        target=directory.joinpath(*relative.parts[1:]);target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes((BACKUP/relative).read_bytes())
    env=os.environ.copy();env['PYTEST_DISABLE_PLUGIN_AUTOLOAD']='1';env['PYTHONDONTWRITEBYTECODE']='1'
    for key in list(env):
        if key.startswith('SUPPORT_COPILOT_'):del env[key]
    xml=directory/'pytest.xml'
    result=subprocess.run([str(PYTHON),'-B','-m','pytest','-q','-p','no:cacheprovider',
        '--junitxml='+str(xml),*['tests/unit/'+name+'.py' for name in TESTS]],
        cwd=directory/'backend',env=env,text=True,capture_output=True,timeout=120)
    (directory/'pytest-output.txt').write_text(result.stdout+result.stderr,encoding='utf-8')
    tree=ElementTree.parse(xml);suites=list(tree.getroot().iter('testsuite'))
    totals={key:sum(int(s.attrib.get(key,0)) for s in suites) for key in ('tests','failures','errors','skipped')}
    report={'run_id':run_id,'baseline_revision':'1a88dbb0e55889303ec83c7abb789fade81f16bf',
        'overlay_applied':True,'snapshot_hashes_verified':True,'dotenv_copied_or_read':False,
        'suite_files':TESTS,'totals':totals,'exit_code':result.returncode,
        'raw_evidence':str(directory.relative_to(ROOT)).replace('\\','/'),
        'baseline_archive_sha256':sha256((BACKUP/'baseline-head.zip').read_bytes()).hexdigest(),
        'scope':'Baseline unit regressions only; no new-candidate billing/refund parity or connected baseline replay',
        'candidate_billing_refund_parity':False}
    (ROOT/'docs/phase-5/baseline-regressions.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'totals':totals,'exit_code':result.returncode}))
    return result.returncode


if __name__=='__main__':sys.exit(main())
