"""Code-led timer loop. Budget and due time survive in business PostgreSQL."""
import json,sys,time,sqlite3
from uuid import uuid4
from contextlib import closing
from service_desk.http_retry import recovery_post,TransportStopped


def run(config):
    worker_id=uuid4().hex
    for _ in range(20):
        try:result=recovery_post(config['origin']+'/recovery',config['capability'],{'fixture':config['fixture'],'worker_id':worker_id})
        except TransportStopped as exc:
            with closing(sqlite3.connect('/tmp/recovery-transport-review.sqlite')) as conn,conn:
                conn.execute('CREATE TABLE IF NOT EXISTS review (fixture text PRIMARY KEY,reason text)')
                conn.execute('INSERT OR REPLACE INTO review VALUES (?,?)',(config['fixture'],str(exc)))
            raise
        if result['done']:return
        time.sleep(result['retry_seconds'])
    raise RuntimeError('Recovery scheduler bound exceeded')


if __name__=='__main__':
    try:run(json.loads(sys.stdin.readline()))
    except Exception:print('Recovery worker stopped for review.',file=sys.stderr);sys.exit(1)
