from contextlib import closing
from service_desk.durable_target import DurableSyntheticTarget


class ReferenceTarget(DurableSyntheticTarget):
    """Test environment controls delay/failure; application only submit/inspect."""
    timeout_after_effect=False
    def __init__(self,path):
        super().__init__(path)
        with closing(self.connect()) as conn,conn:
            conn.execute('CREATE TABLE IF NOT EXISTS submit_attempts (tenant text, operation text)')
    def submit(self,tenant,operation_id,payload):
        encoded=self.encoded(tenant,payload)
        with closing(self.connect()) as conn,conn:
            conn.execute('BEGIN IMMEDIATE')
            conn.execute('INSERT INTO submit_attempts VALUES (?,?)',(tenant,operation_id))
            old=conn.execute('SELECT payload FROM operations WHERE tenant=? AND operation=?',(tenant,operation_id)).fetchone()
            if old and old[0]!=encoded:raise ValueError('Operation conflict.')
            if not old:conn.execute("INSERT INTO operations VALUES (?,?,?,'accepted',1,0)",(tenant,operation_id,encoded))
        if self.timeout_after_effect:
            self.complete(tenant,operation_id,True)
            raise TimeoutError('Fixture response lost.')
        return {'status':'accepted','sequence':1}

    def complete(self,tenant,operation_id,success):
        with closing(self.connect()) as conn,conn:
            conn.execute('BEGIN IMMEDIATE')
            old=conn.execute('SELECT payload,status FROM operations WHERE tenant=? AND operation=?',(tenant,operation_id)).fetchone()
            if old[1] in ('succeeded','failed'):return
            conn.execute('UPDATE operations SET status=?,sequence=2,matches=? WHERE tenant=? AND operation=?',
                         ('succeeded' if success else 'failed',int(success),tenant,operation_id))
            if success:conn.execute('INSERT INTO effect_ledger VALUES (?,?,?)',(tenant,operation_id,old[0]))

    def requests(self,tenant,operation_id):
        with closing(self.connect()) as conn:
            return conn.execute('SELECT count(*) FROM operations WHERE tenant=? AND operation=?',(tenant,operation_id)).fetchone()[0]

    def submit_calls(self,tenant,operation_id):
        with closing(self.connect()) as conn:
            return conn.execute('SELECT count(*) FROM submit_attempts WHERE tenant=? AND operation=?',(tenant,operation_id)).fetchone()[0]
