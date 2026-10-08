"""Logical lab snapshot/restore and additive schema rollback, isolated from live DB.

Copies the three application tables for both configured tenants. No target I/O.
This is not a volume/PITR backup, production cutover or n8n job migration.
"""
from datetime import datetime,timezone
from hashlib import sha256
import json,secrets,sys
from operator_lab import CONFIG,REPORT,ROOT,save
from check_database import sql as admin_sql

def run():
    import psycopg
    from psycopg.types.json import Jsonb
    from service_desk.migrations import migrate
    from service_desk.postgres import PostgresStateStore
    from service_desk.journeys import JourneyService
    from service_desk.contracts import Actor,Role
    config=json.loads(CONFIG.read_text());operator=json.loads(REPORT.read_text())
    name='sdrestore_'+secrets.token_hex(6);created=False
    owner={**config['migration_database'],'dbname':name}
    runtime={**config['database'],'dbname':name}
    report={'status':'failed','checked_at':datetime.now(timezone.utc).isoformat(),'checks':[],
        'source_database_modified':False,'live_target_calls':0,'secrets_printed':False}
    tables=('sd_case_intake','sd_journey','sd_audit');snapshot={t:[] for t in tables}
    try:
        with psycopg.connect(**config['database']) as source:
            source.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
            for tenant in ('alpha','beta'):
                source.execute("SELECT set_config('app.tenant_id',%s,true)",(tenant,))
                for table in tables:
                    snapshot[table]+=source.execute(f'SELECT * FROM {table} ORDER BY 1,2,3').fetchall()
        serialized=json.dumps(snapshot,default=str,sort_keys=True)
        folder=ROOT/'local/operator-migration'/name;folder.mkdir(parents=True)
        (folder/'snapshot.json').write_text(serialized,encoding='utf-8')
        report['snapshot_sha256']=sha256(serialized.encode()).hexdigest()
        report['row_counts']={t:len(rows) for t,rows in snapshot.items()}
        report['checks'].append('repeatable-read application snapshot for configured alpha/beta tenants')
        result=admin_sql(f"CREATE DATABASE {name} OWNER {owner['user']}",database='postgres')
        if result.returncode:raise RuntimeError('create_failed')
        created=True
        result=admin_sql(f"REVOKE ALL ON DATABASE {name} FROM PUBLIC; GRANT CONNECT ON DATABASE {name} TO {runtime['user']}",database='postgres')
        if result.returncode:raise RuntimeError('grant_failed')
        migrate(lambda:psycopg.connect(**owner));migrate(lambda:psycopg.connect(**owner))
        # Restore from disk, not from the in-memory snapshot used to produce it.
        restored=json.loads((folder/'snapshot.json').read_text())
        with psycopg.connect(**owner) as conn:
            user=runtime['user']
            conn.execute(f'REVOKE ALL ON SCHEMA public FROM PUBLIC; GRANT USAGE ON SCHEMA public TO {user}')
            conn.execute(f'GRANT SELECT,INSERT ON sd_case_intake,sd_audit TO {user}')
            conn.execute(f'GRANT SELECT,INSERT,UPDATE ON sd_journey TO {user}')
            for table in tables:
                for row in restored[table]:
                    conn.execute("SELECT set_config('app.tenant_id',%s,true)",(row[0],))
                    values=[Jsonb(v) if isinstance(v,dict) else v for v in row]
                    conn.execute(f"INSERT INTO {table} VALUES ({','.join(['%s']*len(values))})",values)
        recovered={t:[] for t in tables}
        with psycopg.connect(**runtime) as conn:
            for tenant in ('alpha','beta'):
                conn.execute("SELECT set_config('app.tenant_id',%s,true)",(tenant,))
                for table in tables:recovered[table]+=conn.execute(f'SELECT * FROM {table} ORDER BY 1,2,3').fetchall()
        if json.dumps(recovered,default=str,sort_keys=True)!=serialized:raise RuntimeError('restore_mismatch')
        report['checks'].append('fresh schema, migration replay and disk snapshot restore match every application row')
        store=PostgresStateStore(lambda:psycopg.connect(**runtime))
        before=store.get('alpha',operator['case_id'])
        from service_desk.durable_target import DurableSyntheticTarget
        from service_desk.recovery import RecoveryController
        class LostReceipt(DurableSyntheticTarget):
            def submit(self,*args):
                super().submit(*args)
                raise ConnectionError('fixture response loss')
        target_path=folder/'synthetic-target.sqlite'
        fixture=JourneyService(store,LostReceipt(target_path))
        staff=Actor('migration-fixture-staff','beta',Role.SPECIALIST)
        lead=Actor('migration-fixture-supervisor','beta',Role.SUPERVISOR)
        pending=fixture.create(staff,'Grant reports read access','requester-b')
        fixture.prepare(staff,pending['id'],1);fixture.approve(lead,pending['id'],1)
        pending=fixture.execute(staff,pending['id'],1)
        if pending['action']['status']!='unknown':raise RuntimeError('fixture_not_in_flight')
        with psycopg.connect(**owner) as conn:
            conn.execute('ALTER TABLE sd_journey ADD COLUMN migration_probe text')
        if store.get('alpha',operator['case_id'])!=before:raise RuntimeError('forward_read_mismatch')
        with psycopg.connect(**owner) as conn:conn.execute('ALTER TABLE sd_journey DROP COLUMN migration_probe')
        if store.get('alpha',operator['case_id'])!=before:raise RuntimeError('rollback_read_mismatch')
        if store.get('beta',pending['id'])!=pending:raise RuntimeError('pending_job_changed')
        report['checks'].append('additive column forward/rollback keeps existing repository reads and persisted case intact')
        resumed_target=DurableSyntheticTarget(target_path)
        resumed=JourneyService(PostgresStateStore(lambda:psycopg.connect(**runtime)),resumed_target)
        outcome=RecoveryController(resumed).tick(staff,pending['id'])
        if not outcome['done'] or outcome['reason']!='closed' or len(resumed_target.ledger())!=1:raise RuntimeError('inflight_reconciliation_failed')
        final=resumed.read(staff,pending['id'])
        if final['action']['id']!=pending['action']['id']:raise RuntimeError('operation_changed')
        report['checks'].append('synthetic in-flight effect with lost receipt survives schema forward/rollback and reconciles once through new connections')
        report['inflight_fixture']={'tenant':'beta','approval':'fixture supervisor, not William',
            'effects':1,'same_operation_id':True,'closed_after_reconciliation':True}
        try:
            with psycopg.connect(**owner) as conn:
                conn.execute('ALTER TABLE sd_journey ADD COLUMN failed_probe text')
                conn.execute('SELECT 1/0')
        except psycopg.errors.DivisionByZero:pass
        with psycopg.connect(**owner) as conn:
            if conn.execute("SELECT count(*) FROM information_schema.columns WHERE table_name='sd_journey' AND column_name='failed_probe'").fetchone()[0]:raise RuntimeError('ddl_not_rolled_back')
        report['checks'].append('failed DDL transaction rolls back its added column')
        class NoTarget:
            def submit(self,*args):raise AssertionError('target submit forbidden')
            def inspect(self,*args):raise AssertionError('target read forbidden')
        service=JourneyService(store,NoTarget());actor=Actor('restore-check','alpha',Role.SPECIALIST)
        # Restored completed job consumes its durable receipt, never repeats an effect.
        replay=service.execute(actor,before['id'],before['version'])
        if replay['action']['id']!=before['action']['id'] or replay['status']!='closed':raise RuntimeError('job_replay_failed')
        # Config cutover/rollback is exercised through new repository connections.
        original=PostgresStateStore(lambda:psycopg.connect(**config['database'])).get('alpha',before['id'])
        if original!=before:raise RuntimeError('source_changed_during_rehearsal')
        report['checks'].append('restored completed-job receipt replay performs no target calls; reconnect to source preserves original state')
        report.update(status='passed',operation_id=before['action']['id'],scope='configured two-tenant application tables; one completed access job')
    except Exception as exc:report['error']=type(exc).__name__
    finally:
        cleanup=not created or admin_sql(f'DROP DATABASE {name} WITH (FORCE)',database='postgres').returncode==0
        report['temporary_database_removed']=cleanup
        if not cleanup:report['status']='failed'
    report['limitations']=['No live schema/config change or job cutover performed',
        'In-flight case covers additive schema rollback only, not cross-database cutover or n8n state migration',
        'No database-volume recovery or external-target rollback',
        'Snapshot covers only the two configured tenants and three application tables']
    save(ROOT/'docs/phase-5/operator-migration-check.json',report);print(json.dumps(report,indent=2))
    return 0 if report['status']=='passed' else 1

if __name__=='__main__':sys.exit(run())
