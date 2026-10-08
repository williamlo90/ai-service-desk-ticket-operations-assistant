"""Lab control API that restarts a real child health-service process per tenant.

Only fixed alpha/beta services are controlled. No host shell or Docker socket.
Operations are reserved in SQLite; unknown outcomes are never automatically replayed.
"""
from contextlib import closing
from http.server import BaseHTTPRequestHandler,HTTPServer,ThreadingHTTPServer
from hmac import compare_digest
from pathlib import Path
import json,multiprocessing,sqlite3,time,threading
from uuid import uuid4,UUID
from urllib.request import urlopen


def child(port,generation):
    class Health(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def do_GET(self):
            body=json.dumps({'healthy':True,'generation':generation}).encode()
            self.send_response(200);self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
    HTTPServer(('127.0.0.1',port),Health).serve_forever()


def main():
    tokens={t:Path('/run/secrets/control_'+t).read_text().strip() for t in ('alpha','beta')}
    processes={};generations={};ports={'alpha':8082,'beta':8083};lock=threading.Lock()
    def connect():return sqlite3.connect('/data/operations.sqlite',timeout=5)
    with closing(connect()) as conn,conn:
        conn.execute('CREATE TABLE IF NOT EXISTS operation (tenant text,id text,status text,generation text,PRIMARY KEY(tenant,id))')
    def launch(tenant):
        generation=str(uuid4());p=multiprocessing.Process(target=child,args=(ports[tenant],generation),daemon=True)
        p.start();processes[tenant]=p;generations[tenant]=generation;return generation
    for tenant in tokens:launch(tenant)
    def healthy(tenant):
        try:
            with urlopen('http://127.0.0.1:'+str(ports[tenant])+'/healthz',timeout=2) as r:return json.load(r)
        except Exception:return {'healthy':False,'generation':generations[tenant]}
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def reply(self,status,data):
            body=json.dumps(data).encode();self.send_response(status)
            self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(body)))
            self.end_headers();self.wfile.write(body)
        def auth(self):
            supplied=self.headers.get('Authorization','')
            return next((t for t,key in tokens.items() if compare_digest(supplied,'Bearer '+key)),None)
        def do_GET(self):
            if self.path=='/healthz':return self.reply(200,{'ready':True,'environment':'isolated-lab'})
            tenant=self.auth();parts=self.path.strip('/').split('/')
            if not tenant or len(parts)<3 or parts[:2]!=['v1',tenant]:return self.reply(403,{'error':'denied'})
            if parts[2:]==['service']:return self.reply(200,healthy(tenant))
            if len(parts)==4 and parts[2]=='operations':
                with closing(connect()) as conn:
                    row=conn.execute('SELECT status,generation FROM operation WHERE tenant=? AND id=?',(tenant,parts[3])).fetchone()
                if not row:return self.reply(404,{'error':'missing'})
                observed=healthy(tenant)
                return self.reply(200,{'status':row[0],'generation':row[1],
                    'matches':row[0]=='succeeded' and observed['healthy'] and observed['generation']==row[1]})
            self.reply(404,{'error':'missing'})
        def do_POST(self):
            tenant=self.auth()
            if not tenant or self.path!='/v1/'+tenant+'/restart':return self.reply(403,{'error':'denied'})
            try:
                size=int(self.headers.get('Content-Length','0'))
                if not 0<size<=1024:raise ValueError()
                data=json.loads(self.rfile.read(size));operation=data['operation_id']
                if set(data)!={'operation_id'} or str(UUID(operation))!=operation:raise ValueError()
            except Exception:return self.reply(400,{'error':'invalid_request'})
            with lock:
                with closing(connect()) as conn,conn:
                    old=conn.execute('SELECT status,generation FROM operation WHERE tenant=? AND id=?',(tenant,operation)).fetchone()
                    if old:return self.reply(200,{'status':old[0],'generation':old[1],'replayed':True})
                    conn.execute('INSERT INTO operation VALUES (?,?,?,?)',(tenant,operation,'unknown',''))
                processes[tenant].terminate();processes[tenant].join(timeout=3)
                if processes[tenant].is_alive():return self.reply(503,{'error':'manual_review'})
                generation=launch(tenant)
                for _ in range(30):
                    if healthy(tenant)['healthy']:break
                    time.sleep(0.1)
                if not healthy(tenant)['healthy']:return self.reply(503,{'error':'manual_review'})
                with closing(connect()) as conn,conn:
                    conn.execute('UPDATE operation SET status=?,generation=? WHERE tenant=? AND id=?',('succeeded',generation,tenant,operation))
                self.reply(202,{'status':'accepted','operation_id':operation})
    ThreadingHTTPServer(('0.0.0.0',8080),Handler).serve_forever()


if __name__=='__main__':main()
