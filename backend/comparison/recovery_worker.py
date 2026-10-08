"""Code-led timer loop. Budget and due time survive in business PostgreSQL."""
import json,sys,time
from urllib.request import Request,urlopen


def run(config):
    for _ in range(20):
        request=Request(config['origin']+'/recovery',
            data=json.dumps({'fixture':config['fixture']}).encode(),
            headers={'Authorization':'Bearer '+config['capability'],'Content-Type':'application/json'})
        with urlopen(request,timeout=10) as response:result=json.load(response)
        if result['done']:return
        time.sleep(result['retry_seconds'])
    raise RuntimeError('Recovery scheduler bound exceeded')


if __name__=='__main__':
    try:run(json.loads(sys.stdin.readline()))
    except Exception:print('Recovery worker stopped for review.',file=sys.stderr);sys.exit(1)
