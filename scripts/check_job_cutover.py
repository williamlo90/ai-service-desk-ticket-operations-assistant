"""Quiesced job migration between two disposable SQL databases, then rollback."""
import json,secrets,sys
from datetime import datetime,timezone
from operator_lab import CONFIG,ROOT,save
from check_database import sql as admin_sql

def run():
    import psycopg
    from psycopg.types.json import Jsonb
    from service_desk.migrations import migrate
    from service_desk.postgres import PostgresStateStore
    from service_desk.journeys import JourneyService
    from service_desk.recovery import RecoveryController
    from service_desk.durable_target import DurableSyntheticTarget
    from service_desk.contracts import Actor,Role
    config=json.loads(CONFIG.read_text());names=['sdmove_'+secrets.token_hex(6) for _ in range(2)]
    created=[];report={'status':'failed','checked_at':datetime.now(timezone.utc).isoformat()}
    folder=ROOT/'local/job-cutover'/names[0];folder.mkdir(parents=True)
    try:
        dbs=[]
        for name in names:
            owner={**config['migration_database'],'dbname':name};runtime={**config['database'],'dbname':name}
            result=admin_sql(f"CREATE DATABASE {name} OWNER {owner['user']}",database='postgres')
            if result.returncode:raise RuntimeError()
            created.append(name)
            if admin_sql(f"REVOKE ALL ON DATABASE {name} FROM PUBLIC; GRANT CONNECT ON DATABASE {name} TO {runtime['user']}",database='postgres').returncode:raise RuntimeError()
            migrate(lambda:psycopg.connect(**owner))
            with psycopg.connect(**owner) as conn:
                user=runtime['user'];conn.execute(f'REVOKE ALL ON SCHEMA public FROM PUBLIC; GRANT USAGE ON SCHEMA public TO {user}')
                conn.execute(f'GRANT SELECT,INSERT,UPDATE ON sd_journey TO {user}')
                conn.execute(f'GRANT SELECT,INSERT ON sd_audit TO {user}')
            dbs.append((owner,runtime))
        class LostReceipt(DurableSyntheticTarget):
            def submit(self,*args):super().submit(*args);raise ConnectionError('fixture lost reply')
        target_path=folder/'target.sqlite';actor=Actor('fixture-worker','beta',Role.SPECIALIST)
        source=JourneyService(PostgresStateStore(lambda:psycopg.connect(**dbs[0][1])),LostReceipt(target_path))
        state=source.create(actor,'reports read access','requester-b');key=state['id']
        source.prepare(actor,key,1);source.approve(Actor('fixture-supervisor','beta',Role.SUPERVISOR),key,1)
        state=source.execute(actor,key,1)
        if state['action']['status']!='unknown':raise RuntimeError()
        # No source worker runs after this point until rollback; source is quiesced.
        snapshot=folder/'pending.json';snapshot.write_text(json.dumps(state))
        state=json.loads(snapshot.read_text())
        with psycopg.connect(**dbs[1][0]) as conn:
            conn.execute("SELECT set_config('app.tenant_id','beta',true)")
            conn.execute('INSERT INTO sd_journey VALUES (%s,%s,%s,%s)',('beta',key,state['revision'],Jsonb(state)))
            for event in state['audit']:conn.execute('INSERT INTO sd_audit VALUES (%s,%s,%s,%s)',('beta',key,event['sequence'],Jsonb(event)))
        target=DurableSyntheticTarget(target_path)
        destination=JourneyService(PostgresStateStore(lambda:psycopg.connect(**dbs[1][1])),target)
        if destination.read(actor,key)!=state:raise RuntimeError()
        moved=RecoveryController(destination).tick(actor,key)
        if moved['reason']!='closed':raise RuntimeError()
        # Quiesce destination, roll config back to the original DB and reconcile
        # its stale unknown receipt against the SAME independent target ledger.
        rolled=RecoveryController(JourneyService(source.store,target)).tick(actor,key)
        if rolled['reason']!='closed' or len(target.ledger())!=1:raise RuntimeError()
        if destination.read(actor,key)['action']['id']!=source.read(actor,key)['action']['id']:raise RuntimeError()
        report.update(status='passed',cross_database_restore=True,cutover_closed=True,rollback_closed=True,
            target_effects=1,same_operation_id=True,source_worker_quiesced=True,destination_worker_quiesced_before_rollback=True,
            original_operator_database_touched=False,live_target_calls=0,approval='technical fixture',
            limitation='Quiesced synthetic job; not simultaneous writers or network-partition fencing')
    except Exception as exc:report['error']=type(exc).__name__
    finally:
        cleanup=True
        for name in reversed(created):cleanup=(admin_sql(f'DROP DATABASE {name} WITH (FORCE)',database='postgres').returncode==0) and cleanup
        report['temporary_databases_removed']=cleanup
        if not cleanup:report['status']='failed'
    save(ROOT/'docs/phase-5/job-cutover-check.json',report);print(json.dumps(report));return 0 if report['status']=='passed' else 1

if __name__=='__main__':sys.exit(run())
