"""Disposable, in-memory UI preview. No credentials, Docker, Jira or model calls."""
from pathlib import Path
import sys,json
from wsgiref.simple_server import make_server
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'backend'))
from service_desk.auth import TokenAuthenticator
from service_desk.cases import MemoryCaseRepository
from service_desk.contracts import Actor,Role
from service_desk.journeys import JourneyService
from service_desk.store import MemoryStateStore
from service_desk.simulator import SimulatedTarget
from service_desk.runtime_api import RuntimeAPI,QuietHandler

def build(port=5683):
    staff=Actor('preview-specialist','demo',Role.SPECIALIST)
    lead=Actor('preview-supervisor','demo',Role.SUPERVISOR)
    service=JourneyService(MemoryStateStore(),SimulatedTarget())
    case=service.create(staff,'Grant requester-a read access to reports')
    service.prepare(staff,case['id'],1)
    # Public fixture value; accepted only by this disposable in-memory server.
    auth=TokenAuthenticator({'preview-only-'+'x'*32:lead})
    app=RuntimeAPI(auth,service,MemoryCaseRepository(),f'http://127.0.0.1:{port}')
    return app,case['id']
if __name__=='__main__':
    app,key=build()
    print(json.dumps({'url':f'http://127.0.0.1:5683/?case={key}','mode':'synthetic preview; no worker or external targets'}),flush=True)
    make_server('127.0.0.1',5683,app,handler_class=QuietHandler).serve_forever()
