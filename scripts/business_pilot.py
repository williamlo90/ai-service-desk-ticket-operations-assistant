"""Loopback-only human correction pilot. Cached model advice; no provider calls.

Only participant button presses begin timing. Stores observations under local/.
This is a diagnostic usability pilot, not production acceptance or model approval.
"""
import json
from pathlib import Path
from datetime import datetime, timezone
from time import monotonic
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Lock
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
from service_desk.ai import CLARIFICATION_LABELS, CATEGORIES

PORT=5682
ORIGIN=f'http://127.0.0.1:{PORT}'
OUTPUT=ROOT/'local/phase6/human-pilot.json'
PAGE=ROOT/'evals/phase6-v2/pilot.html'


def tasks():
    data=json.loads((ROOT/'evals/phase6-v2/dataset.json').read_text())['cases']
    cases={c['id']:c for c in data}
    rows={r['id']:r['result']['data'] for r in json.loads(
        (ROOT/'docs/phase-6/v4/openai-heldout.json').read_text())['rows']}
    # Two matched cases per category, alternating the first condition. New manual
    # cases are not copies of the AI answers. One operator, non-randomized pilot.
    manual=[
      ('access','Read-only access to the expense archive is requested; the user identity was not supplied.','access_request',['requester_identity']),
      ('incident','A service returns connection refused, but its name is absent from the report.','service_incident',['service_name']),
      ('link','Link current ticket IT-101 to an older duplicate; the older ticket number is unknown.','repeated_ticket',['related_ticket_id']),
      ('other','Tolong pilihkan warna cat untuk ruang tamu saya.','unsupported',[])]
    ids=['v2-q07','v2-q11','v2-q15','v2-q18'];out=[]
    for i,(pair,text,category,missing) in enumerate(manual):
        left={'id':'manual-'+pair,'pair':pair,'condition':'manual','text':text,
              'expected_category':category,'expected_missing':missing,'advice':None}
        c=cases[ids[i]]
        right={'id':'assisted-'+pair,'pair':pair,'condition':'assisted','text':c['text'],
               'expected_category':c['expected_category'],'expected_missing':c['expected_missing'],
               'advice':rows[ids[i]]}
        out.extend([left,right] if i%2==0 else [right,left])
    return out


class Study:
    def __init__(self,path=OUTPUT):
        self.path=path;self.items=tasks();self.started=None;self.paused_at=None
        self.pause_seconds=0;self.started_utc=None
        self.rows=json.loads(path.read_text())['observations'] if path.exists() else []
        self.index=len(self.rows)

    def state(self):
        task=self.items[self.index] if self.index<len(self.items) else None
        public={k:task[k] for k in ('id','pair','condition','text','advice')} if task else None
        return {'index':self.index,'total':len(self.items),'task':public,
                'running':self.started is not None,'paused':self.paused_at is not None,
                'categories':CATEGORIES,'fields':CLARIFICATION_LABELS}

    def act(self,action,data):
        if self.index>=len(self.items):raise ValueError('finished')
        now=monotonic()
        if action=='start' and self.started is None:
            self.started=now;self.started_utc=datetime.now(timezone.utc).isoformat()
            self.pause_seconds=0
        elif action=='pause' and self.started is not None and self.paused_at is None:
            self.paused_at=now
        elif action=='resume' and self.paused_at is not None:
            self.pause_seconds+=now-self.paused_at;self.paused_at=None
        elif action=='submit' and self.started is not None and self.paused_at is None:
            if set(data)!={'category','missing','evidence','next_step'}:raise ValueError('fields')
            if (data['category'] not in CATEGORIES or type(data['missing']) is not list
                    or any(x not in CLARIFICATION_LABELS for x in data['missing'])
                    or len(set(data['missing']))!=len(data['missing'])
                    or not isinstance(data['evidence'],str) or not 12<=len(data['evidence'])<=1000
                    or data['next_step'] not in ('clarify','prepare_for_approval','route_out_of_scope')):
                raise ValueError('answer')
            task=self.items[self.index];elapsed=now-self.started
            expected_step=('route_out_of_scope' if task['expected_category']=='unsupported' else
                           'clarify' if task['expected_missing'] else 'prepare_for_approval')
            correct=(data['category']==task['expected_category'] and
                     set(data['missing'])==set(task['expected_missing']) and
                     data['evidence'] in task['text'] and data['next_step']==expected_step)
            advice=task['advice']
            changed=(int(data['category']!=advice['category'])+
                     int(set(data['missing'])!=set(advice['missing']))) if advice else None
            row={'participant':'William','order':self.index+1,'case_id':task['id'],
                 'pair_id':task['pair'],'condition':task['condition'],'started_utc':self.started_utc,
                 'ended_utc':datetime.now(timezone.utc).isoformat(),'active_seconds':round(elapsed-self.pause_seconds,3),
                 'interruption_seconds':round(self.pause_seconds,3),'elapsed_seconds':round(elapsed,3),
                 'waiting_seconds':0,'answer':data,'correct_automatic_rubric':correct,
                 'changed_category_or_missing_fields':changed,'human_reviewer':None}
            document={'study':'diagnostic-cached-advice-v1','model':'gpt-4.1-mini-2025-04-14',
                      'prompt_version':'service-desk-facts-v5','observations':self.rows+[row],
                      'limitations':['single participant','non-randomized matched pairs','cached advice; excludes generation wait','active time depends on participant pausing','semantic human review pending']}
            self.path.parent.mkdir(parents=True,exist_ok=True)
            temporary=self.path.with_suffix('.tmp');temporary.write_text(json.dumps(document,indent=2)+'\n',encoding='utf-8')
            temporary.replace(self.path)
            self.rows.append(row);self.index+=1;self.started=None;self.paused_at=None
        else:raise ValueError('state')
        return self.state()


class Handler(BaseHTTPRequestHandler):
    def setup(self):
        super().setup()
        self.connection.settimeout(5)
    def log_message(self,*_):pass
    def send(self,status,data,content_type='application/json'):
        body=data if isinstance(data,bytes) else json.dumps(data).encode()
        self.send_response(status);self.send_header('Content-Type',content_type)
        self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
    def do_GET(self):
        if self.headers.get('Host')!=f'127.0.0.1:{PORT}':return self.send(403,{'error':'host'})
        if self.path=='/':return self.send(200,PAGE.read_bytes(),'text/html; charset=utf-8')
        if self.path=='/quote-tools.js':return self.send(200,(PAGE.parent/'quote-tools.js').read_bytes(),'text/javascript; charset=utf-8')
        if self.path=='/practice':return self.send(200,(PAGE.parent/'practice.html').read_bytes(),'text/html; charset=utf-8')
        if self.path=='/practice-data':
            cases={c['id']:c for c in json.loads((ROOT/'evals/phase6-evidence-v1/dataset.json').read_text())['cases']}
            report=json.loads((ROOT/'docs/phase-6/evidence-v1/openai-development.json').read_text())
            items=[{'text':cases[row['id']]['text'],'result':row['result']} for row in report['rows'] if row['result']]
            return self.send(200,{'items':items,'fields':CLARIFICATION_LABELS})
        if self.path=='/state':
            with self.server.study_lock:state=self.server.study.state()
            return self.send(200,state)
        self.send(404,{'error':'not_found'})
    def do_POST(self):
        if (self.headers.get('Host')!=f'127.0.0.1:{PORT}' or self.headers.get('Origin')!=ORIGIN
                or self.headers.get('X-Pilot-Client')!='browser'):
            return self.send(403,{'error':'origin'})
        try:
            size=int(self.headers.get('Content-Length','0'))
            if not 0<size<=8192:raise ValueError('size')
            data=json.loads(self.rfile.read(size))
            if self.path not in ('/start','/pause','/resume','/submit'):raise ValueError('route')
            with self.server.study_lock:state=self.server.study.act(self.path[1:],data)
            self.send(200,state)
        except (ValueError,KeyError,TypeError):self.send(400,{'error':'invalid_answer_or_state'})


if __name__=='__main__':
    server=ThreadingHTTPServer(('127.0.0.1',PORT),Handler)
    server.study=Study();server.study_lock=Lock()
    server.serve_forever()
