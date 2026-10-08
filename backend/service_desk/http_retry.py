"""Bounded redelivery for idempotent recovery ticks, not arbitrary mutations."""
import json,time
from urllib.request import Request,build_opener,HTTPRedirectHandler
from urllib.error import HTTPError,URLError


class TransportStopped(Exception):pass


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):return None


def recovery_post(url,capability,payload,*,opener=None,sleep=time.sleep):
    opener=opener or build_opener(NoRedirect())
    encoded=json.dumps(payload).encode()
    for attempt in range(4):
        delay=2**attempt
        try:
            request=Request(url,data=encoded,headers={'Authorization':'Bearer '+capability,
                'Content-Type':'application/json'})
            with opener.open(request,timeout=10) as response:
                raw=response.read(65537)
                if len(raw)>65536:raise TransportStopped('response_limit')
                result=json.loads(raw)
                if type(result) is not dict or type(result.get('done')) is not bool:
                    raise TransportStopped('invalid_response')
                return result
        except HTTPError as exc:
            if exc.code not in (408,409,429,502,503,504):
                raise TransportStopped('terminal_http_'+str(exc.code)) from None
            retry_after=exc.headers.get('Retry-After','')
            if retry_after:
                if not retry_after.isdigit() or int(retry_after)>30:
                    raise TransportStopped('retry_after_requires_review') from None
                delay=max(delay,int(retry_after))
        except (URLError,TimeoutError,ConnectionError):pass
        if attempt==3:raise TransportStopped('transport_exhausted')
        sleep(delay)
