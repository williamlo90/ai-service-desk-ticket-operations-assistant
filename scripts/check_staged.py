"""Bounded pre-commit secret-path check; never reads the working .env file."""
import re
import subprocess
import sys

paths = subprocess.check_output(['git','diff','--cached','--name-only','-z']).decode().split('\0')
bad = []
for path in filter(None, paths):
    leaf = path.rsplit('/',1)[-1]
    if ((leaf.startswith('.env') and leaf != '.env.example')
            or set(path.split('/')) & {'local','node_modules','dist','__pycache__','.venv'}):
        bad.append(path)
        continue
    if path.endswith('.png'):
        continue
    text = subprocess.check_output(['git','show',':'+path]).decode('utf-8', errors='replace')
    if re.search(r'ATATT3[A-Za-z0-9_=-]{30,}|sk-(?:proj-|ant-)?[A-Za-z0-9_-]{30,}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----', text):
        bad.append(path)
    if leaf == '.env.example':
        for line in text.splitlines():
            if '=' in line and not line.lstrip().startswith('#'):
                key,value=line.split('=',1)
                if any(x in key.upper() for x in ('TOKEN','PASSWORD','SECRET','API_KEY')) and value.strip():
                    bad.append(path)
print('Staged path/known-secret checks:', 'FAILED' if bad else 'passed')
# Report filenames only; never secret values. This is not a comprehensive secret scanner.
if bad:
    print('\n'.join(sorted(set(bad))))
sys.exit(bool(bad))
