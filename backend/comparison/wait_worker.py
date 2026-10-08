"""Single-worker durable polling prototype; never issues approvals or target effects.

Checkpoint storage survives process/container restart. This is not a distributed
queue: lease ownership, overlapping workers and retry backoff are separate gates.
"""
from contextlib import closing
import json,sqlite3,sys,time
from urllib.request import Request,urlopen


def run(config):
    path='/tmp/native-worker.sqlite'
    with closing(sqlite3.connect(path)) as conn,conn:
        conn.execute('CREATE TABLE IF NOT EXISTS job (id integer PRIMARY KEY CHECK(id=1), stage text NOT NULL, ticks integer NOT NULL)')
        conn.execute("INSERT OR IGNORE INTO job VALUES (1,'new',0)")
        saved=conn.execute('SELECT stage FROM job WHERE id=1').fetchone()[0]
    if saved=='closed':return
    def request(path,data):
        with urlopen(Request(config['origin']+path,data=json.dumps(data).encode(),
            headers={'Authorization':'Bearer '+config['capability'],'Content-Type':'application/json'}),timeout=10) as response:
            return json.load(response)
    def checkpoint(stage):
        with closing(sqlite3.connect(path)) as conn,conn:
            conn.execute('UPDATE job SET stage=?,ticks=ticks+1 WHERE id=1',(stage,))
    def command(name):
        result=request('/step',{'fixture':'native-wait','command':name})
        if result.get('denial'):raise RuntimeError('Domain command rejected.')
    for _ in range(180):
        status=request('/native',{});state=status['state']
        if state['status']=='closed':checkpoint('closed');return
        if not state['proposal']:command('prepare')
        elif not state['approval']:checkpoint('waiting_approval')
        elif not state['action']:command('execute');checkpoint('waiting_target')
        elif status['target'] and status['target']['matches']:
            command('verify');command('close');checkpoint('closed');return
        else:checkpoint('waiting_target')
        time.sleep(0.5)
    raise RuntimeError('Bounded wait elapsed.')


if __name__=='__main__':
    try:run(json.loads(sys.stdin.buffer.readline(65537)))
    except Exception:print('Durable wait worker stopped for review.',file=sys.stderr);sys.exit(1)
