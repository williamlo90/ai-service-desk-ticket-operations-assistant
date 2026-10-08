"""Code-led linear reference worker; resumes only at explicit fixture boundary."""
import json,sys
from urllib.request import Request,urlopen


def main():
    config=json.load(sys.stdin)
    for step in config['steps']:
        request=Request(config['origin']+'/step',data=json.dumps(step).encode(),
                        headers={'Content-Type':'application/json','Authorization':'Bearer '+config['capability']})
        with urlopen(request,timeout=15) as response:
            result=json.load(response)
            if result.get('recorded') is not True:raise ValueError('Missing observation.')
    print(json.dumps({'completed_steps':len(config['steps'])}))


if __name__=='__main__':
    try:main()
    except Exception:print('Reference worker failed.',file=sys.stderr);sys.exit(1)
