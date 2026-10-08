"""Copy only generated local DB passwords over stdin to a project-owned volume."""
import io
import os
from pathlib import Path
import subprocess
import tarfile
import sys

IMAGE = 'pgvector/pgvector@sha256:ad2e18408bf447f62092a8a5259e7df10505c5a0360bd1a1853ac8b8b0763da2'


def main():
    try:
        root = Path(os.environ['LOCALAPPDATA'])/'ServiceDeskLab'/'secrets'
        for volume, names, owner in [
            ('service-desk-lab_secrets', ('db_admin','db_app','db_n8n'), 'postgres:postgres'),
            ('service-desk-lab_n8n_secrets', ('db_n8n','n8n_key'), '1000:1000'),
        ]:
            archive = io.BytesIO()
            with tarfile.open(fileobj=archive, mode='w') as tar:
                for name in names:
                    data = (root/name).read_bytes()
                    if len(data) != 44:
                        raise ValueError('invalid length')
                    item = tarfile.TarInfo(name)
                    item.size = len(data)
                    item.mode = 0o600
                    tar.addfile(item, io.BytesIO(data))
            # Host bind mounts to AppData were not readable in this Desktop setup.
            # Private volumes avoid changing global file-sharing configuration.
            result = subprocess.run(['docker','run','--rm','-i','--network','none',
                '--memory','64m','--cpus','0.25','--entrypoint','sh',
                '--mount',f'type=volume,source={volume},target=/run/secrets',
                IMAGE,'-c',f'set -eu; umask 077; tar -xf - -C /run/secrets; chown -R {owner} /run/secrets; chmod 700 /run/secrets'],
                input=archive.getvalue(),capture_output=True,timeout=45)
            if result.returncode != 0:
                raise RuntimeError('copy failed')
        print('Isolated runtime secret volumes prepared; values not displayed.')
        return 0
    except Exception:
        print('Database secret volume preparation failed; details suppressed.')
        return 1


if __name__ == '__main__':
    sys.exit(main())
