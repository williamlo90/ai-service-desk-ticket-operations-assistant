"""Check local Markdown link targets against files in this repository."""
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
LINK = re.compile(r'!?\[[^\]]*\]\(([^)]+)\)')
SCHEME = re.compile(r'^[A-Za-z][A-Za-z0-9+.-]*:')
tracked = subprocess.check_output(
    ['git', 'ls-files', '-z', '--', '*.md'], cwd=ROOT,
).decode('utf-8').split('\0')
missing = []
count = 0

for relative in filter(None, tracked):
    source = ROOT / relative
    if not source.is_file():
        continue
    for match in LINK.finditer(source.read_text(encoding='utf-8')):
        destination = match.group(1).strip().split(' ', 1)[0].strip('<>')
        if not destination or destination.startswith('#') or SCHEME.match(destination):
            continue
        count += 1
        path = unquote(destination.split('#', 1)[0])
        resolved = (source.parent / path).resolve()
        if not resolved.is_relative_to(ROOT) or not resolved.exists():
            line = source.read_text(encoding='utf-8').count('\n', 0, match.start()) + 1
            missing.append(f'{relative}:{line}: {destination}')

print(f'Checked {count} relative Markdown links: ' +
      ('FAILED' if missing else 'passed'))
for item in missing:
    print(item)
sys.exit(bool(missing))
