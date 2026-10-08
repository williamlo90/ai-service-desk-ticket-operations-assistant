"""Bounded local smoke: no Jira .env reads and no secret-bearing output."""
import json
from pathlib import Path
import subprocess
import sys
import time
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
CONTAINER = 'service-desk-lab-db-1'


def run(args, *, data=None, timeout=30):
    return subprocess.run(args, input=data, text=True, capture_output=True, timeout=timeout)


def sql(query, role='postgres', database='service_desk', secret='db_admin', bad=False):
    # Password is read only inside the container, never into Python or arguments.
    password = 'invalid-smoke-password' if bad else f'"$(cat /run/secrets/{secret})"'
    shell = f'export PGPASSWORD={password}; exec psql -X -h 127.0.0.1 -U {role} -d {database} -Atq -v ON_ERROR_STOP=1'
    return run(['docker', 'exec', '-i', CONTAINER, 'sh', '-c', shell], data=query)


def require(ok, label):
    if not ok:
        raise RuntimeError(label)


def main():
    report = {'checked_at_utc': datetime.now(timezone.utc).isoformat(), 'checks': []}
    try:
        versions = sql("SELECT current_setting('server_version'); SELECT extversion FROM pg_extension WHERE extname='vector';")
        require(versions.returncode == 0, 'version_query')
        lines = versions.stdout.strip().splitlines()
        require(len(lines) == 2 and all(len(s) < 120 for s in lines), 'version_shape')
        report['postgres_version'], report['pgvector_version'] = lines
        for role, db, secret, other in [('service_desk_app','service_desk','db_app','n8n'), ('service_desk_n8n','n8n','db_n8n','service_desk')]:
            result = sql('SELECT current_user;', role, db, secret)
            require(result.returncode == 0 and result.stdout.strip() == role, 'role_login')
            report['checks'].append(f'{role}: authenticated TCP login')
            denied = sql('SELECT 1;', role, other, secret)
            require(denied.returncode != 0 and 'permission denied for database' in denied.stderr, 'database_isolation')
            report['checks'].append(f'{role}: cross-database connection denied')
        bad = sql('SELECT 1;', 'service_desk_app','service_desk','db_app',bad=True)
        require(bad.returncode != 0 and 'password authentication failed' in bad.stderr, 'wrong_password_denied')
        report['checks'].append('wrong password denied')
        flags = sql("SELECT count(*) FROM pg_roles WHERE rolname IN ('service_desk_app','service_desk_n8n') AND (rolsuper OR rolcreatedb OR rolcreaterole OR rolbypassrls);")
        require(flags.returncode == 0 and flags.stdout.strip() == '0', 'unprivileged_roles')
        report['checks'].append('application roles have no cluster administration privileges')
        written = sql("CREATE TABLE IF NOT EXISTS public.runtime_smoke_probe (id integer PRIMARY KEY, note text NOT NULL); INSERT INTO public.runtime_smoke_probe VALUES (1,'synthetic-persistence-probe') ON CONFLICT (id) DO UPDATE SET note=EXCLUDED.note;", 'service_desk_app','service_desk','db_app')
        require(written.returncode == 0, 'probe_write')
        require(run(['docker','restart',CONTAINER], timeout=45).returncode == 0, 'restart')
        for _ in range(20):
            ready = run(['docker','exec',CONTAINER,'pg_isready','-U','postgres'], timeout=5)
            if ready.returncode == 0:
                break
            time.sleep(1)
        persisted = sql('SELECT note FROM public.runtime_smoke_probe WHERE id=1;', 'service_desk_app','service_desk','db_app')
        require(persisted.returncode == 0 and persisted.stdout.strip() == 'synthetic-persistence-probe', 'persistence_after_restart')
        report['checks'].append('synthetic record survives database container restart')
        require(sql('DROP TABLE public.runtime_smoke_probe;', 'service_desk_app','service_desk','db_app').returncode == 0, 'probe_cleanup')
        report['checks'].append('synthetic probe removed')
        inspection = run(['docker','inspect','--format','{{json .HostConfig}}',CONTAINER])
        require(inspection.returncode == 0, 'limits_inspection')
        config = json.loads(inspection.stdout)
        require(config['Memory'] == 536870912 and config['NanoCpus'] == 500000000, 'resource_limits')
        require(config['PortBindings']['5432/tcp'] == [{'HostIp':'127.0.0.1','HostPort':'5433'}], 'loopback_binding')
        report['checks'].append('512 MiB / 0.5 CPU and loopback-only port enforced')
        state = run(['docker','inspect','--format','{{json .State}}',CONTAINER])
        require(state.returncode == 0 and not json.loads(state.stdout)['OOMKilled'], 'oom_check')
        report['status'] = 'passed'
    except Exception as exc:
        report['status'] = 'failed'
        # Only known test labels, never raw Docker/SQL stderr or exception text.
        report['failure'] = str(exc) if type(exc) is RuntimeError else type(exc).__name__
    (ROOT/'docs/phase-1/database-check.json').write_text(json.dumps(report,indent=2)+'\n', encoding='utf-8')
    print(json.dumps(report,indent=2))
    return 0 if report['status'] == 'passed' else 1


if __name__ == '__main__':
    sys.exit(main())
