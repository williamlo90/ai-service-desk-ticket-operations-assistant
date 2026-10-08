"""Export staged sources, install pinned deps in isolation, run offline acceptance.
No project .env/private runtime copied or read. Dependency downloads need internet.
"""
from datetime import datetime,timezone
from hashlib import sha256
from pathlib import Path
import json,os,re,secrets,subprocess,sys,zipfile
ROOT=Path(__file__).resolve().parents[1]


def main():
    run=ROOT/'local/phase8'/('clean-'+secrets.token_hex(6));run.mkdir(parents=True)
    source=run/'source';source.mkdir()
    report={'status':'failed','checked_at_utc':datetime.now(timezone.utc).isoformat(),
            'scope':'fresh source export, isolated Python environment, fresh npm install, offline synthetic verification; not new-host SaaS provisioning',
            'steps':[],'credentials_copied':False}
    def command(label,args,cwd,timeout=180,env=None):
        result=subprocess.run(args,cwd=cwd,capture_output=True,text=True,timeout=timeout,env=env)
        if result.returncode:raise RuntimeError(label)
        report['steps'].append(label);return result.stdout+result.stderr
    try:
        tree=command('staged_tree',['git','write-tree'],ROOT).strip()
        report['source_tree']=tree
        archive=run/'service-desk-source.zip'
        command('source_archive',['git','archive','--format=zip','--output='+str(archive),tree],ROOT)
        with zipfile.ZipFile(archive) as z:
            for item in z.infolist():
                p=Path(item.filename)
                if not (source/p).resolve().is_relative_to(source.resolve()):raise RuntimeError('archive_path')
                if p.name.startswith('.env') and p.name!='.env.example':raise RuntimeError('credential_path')
                if set(p.parts)&{'local','.venv','node_modules','.git','__pycache__'}:raise RuntimeError('private_or_generated_path')
            z.extractall(source)
        report['archive_sha256']=sha256(archive.read_bytes()).hexdigest()
        report['archive_relative_path']=archive.relative_to(ROOT).as_posix()
        command('create_isolated_python',[sys.executable,'-m','venv',str(run/'venv')],ROOT)
        python=run/'venv'/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
        command('install_pinned_python',[str(python),'-m','pip','install','--disable-pip-version-check','-r',str(source/'backend/requirements-postgres.txt')],source)
        command('python_dependency_check',[str(python),'-m','pip','check'],source)
        npm='npm.cmd' if os.name=='nt' else 'npm'
        command('install_locked_npm',[npm,'ci','--ignore-scripts','--no-audit','--no-fund'],source/'mcp-server')
        text=command('python_tests',[str(python),'-B','-m','unittest','discover','-s','tests'],source/'backend')
        report['python_tests']=int(re.search(r'Ran ([0-9]+) tests',text)[1])
        # MCP harness invokes python by name: resolve it to the clean venv too.
        env={**os.environ,'PATH':str(python.parent)+os.pathsep+os.environ.get('PATH','')}
        text=command('mcp_build_and_tests',['node','test/run.mjs'],source/'mcp-server',env=env)
        report['mcp_tests']=int(re.search(r'# pass ([0-9]+)',text)[1])
        command('quote_ui_checks',['node','scripts/check_quote_tools.cjs'],source)
        command('offline_demo',[str(python),'-B','scripts/demo_handover.py'],source)
        versions=command('versions',[str(python),'-c','import sys,psycopg,json;print(json.dumps({"python":sys.version.split()[0],"psycopg":psycopg.__version__}))'],source)
        report['versions']=json.loads(versions)
        report['versions']['node']=command('node_version',['node','--version'],source).strip()
        # Record exact source bytes tested, normalized for Git LF/CRLF checkout differences.
        report['tested_source_lf_sha256']={p.relative_to(source).as_posix():sha256(p.read_bytes().replace(bytes([13,10]),bytes([10]))).hexdigest()
            for directory in ('backend/service_desk','backend/tests','scripts','mcp-server/src','mcp-server/test')
            for p in (source/directory).rglob('*') if p.is_file() and p.suffix in ('.py','.ts','.mjs','.cjs','.ps1')}
        report['status']='passed'
    except Exception as exc:
        report['failure']=str(exc) if type(exc) is RuntimeError else type(exc).__name__
    (ROOT/'docs/phase-8/clean-delivery.json').write_text(json.dumps(report,indent=2)+chr(10))
    print(json.dumps({k:v for k,v in report.items() if k!='tested_source_lf_sha256'},indent=2))
    return report['status']!='passed'


if __name__=='__main__':sys.exit(main())
