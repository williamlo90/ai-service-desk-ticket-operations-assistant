"""Explicit migration entry point. Caller supplies the connection, never .env."""
from hashlib import sha256
from pathlib import Path


def migrate(connect):
    with connect() as conn:
        conn.execute('SELECT pg_advisory_xact_lock(819274001)')
        conn.execute('CREATE TABLE IF NOT EXISTS sd_schema_version (name text PRIMARY KEY, checksum text NOT NULL)')
        for path in sorted((Path(__file__).resolve().parents[1]/'migrations').glob('*.sql')):
            sql=path.read_text(encoding='utf-8');checksum=sha256(sql.encode()).hexdigest()
            row=conn.execute('SELECT checksum FROM sd_schema_version WHERE name=%s',(path.name,)).fetchone()
            if row:
                if row[0]!=checksum:raise ValueError('Applied migration checksum mismatch.')
                continue
            conn.execute(sql)
            conn.execute('INSERT INTO sd_schema_version VALUES (%s,%s)',(path.name,checksum))
