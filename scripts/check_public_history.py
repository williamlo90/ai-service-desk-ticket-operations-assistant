"""Inspect committed Git objects only. Never reads .env or private working files."""
import json,re,subprocess,sys
from pathlib import PurePosixPath,Path

def git(*args):return subprocess.check_output(['git',*args])
def main():
    revisions=git('rev-list','--all').decode().splitlines()
    blobs={};bad=[]
    for revision in revisions:
        for entry in git('ls-tree','-rz',revision).split(b'\0'):
            if not entry:continue
            meta,rawpath=entry.split(b'\t',1);path=rawpath.decode();oid=meta.split()[-1].decode()
            p=PurePosixPath(path)
            if ((p.name.startswith('.env') and p.name!='.env.example') or
                    set(p.parts)&{'local','.venv','node_modules','__pycache__'} or
                    p.suffix in {'.pem','.key','.sqlite','.db','.pfx'}):
                bad.append({'commit':revision[:12],'path':path,'reason':'private_path'})
            blobs.setdefault((oid,path),revision)
    pattern=re.compile(rb'ATATT3[A-Za-z0-9_=-]{30,}|sk-(?:proj-|ant-)?[A-Za-z0-9_-]{30,}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----')
    for (oid,path),revision in blobs.items():
        if PurePosixPath(path).suffix in {'.jpg','.jpeg','.png'}:continue
        raw=git('cat-file','blob',oid)
        if pattern.search(raw):bad.append({'commit':revision[:12],'path':path,'reason':'known_secret_pattern'})
        if PurePosixPath(path).name=='.env.example':
            for line in raw.decode().splitlines():
                if '=' in line and not line.lstrip().startswith('#'):
                    key,value=line.split('=',1)
                    if any(word in key.upper() for word in ('TOKEN','PASSWORD','SECRET','API_KEY')) and value.strip():
                        bad.append({'commit':revision[:12],'path':path,'reason':'nonempty_example_secret'})
    exceptions=0
    for line in Path('.gitleaksignore').read_text(encoding='utf-8').splitlines():
        if not line or line.startswith('#'):continue
        revision,path,rule,number=line.split(':')
        content=git('show',revision+':'+path).decode().splitlines()[int(number)-1]
        if rule!='generic-api-key' or not re.fullmatch(r'\s*"[^"\n]+\.(?:py|js|ts|json|sql|html|cjs)": "[0-9a-f]{64}",?\s*',content):
            bad.append({'path':path,'reason':'invalid_scanner_exception'})
        exceptions+=1
    print(json.dumps({'status':'failed' if bad else 'passed','commits':len(revisions),
        'unique_path_blobs':len(blobs),'reviewed_digest_exceptions':exceptions,'findings':bad},indent=2))
    return bool(bad)
if __name__=='__main__':sys.exit(main())
