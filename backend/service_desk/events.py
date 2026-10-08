"""Authenticated callback envelope; body claims never establish tenant identity."""
from dataclasses import dataclass,field
from hashlib import sha256
import hmac
import json


class EventRejected(Exception):pass


@dataclass(frozen=True,repr=False)
class CallbackVerifier:
    tenant: str
    secret: bytes=field(repr=False)
    def __post_init__(self):
        if not self.tenant or len(self.secret)<32:raise ValueError('Invalid callback configuration.')

    def verify(self,body:bytes,timestamp:str,signature:str,now_seconds:int):
        if len(body)>16384 or not timestamp.isdigit() or len(timestamp)>12:raise EventRejected()
        if abs(now_seconds-int(timestamp))>300:raise EventRejected()
        expected=hmac.new(self.secret,timestamp.encode()+b'.'+body,sha256).hexdigest()
        if not hmac.compare_digest(expected,signature):raise EventRejected()
        try:
            from .api import strict_object,reject_constant
            data=json.loads(body,object_pairs_hook=strict_object,parse_constant=reject_constant)
            if (set(data)!={'tenant','case_id','operation_id','sequence','event_id'}
                    or data['tenant']!=self.tenant or type(data['sequence']) is not int or data['sequence']<1
                    or any(not isinstance(data[k],str) or not 1<=len(data[k])<=128
                           for k in ('case_id','operation_id','event_id'))):raise ValueError()
            return data
        except Exception:raise EventRejected() from None


class CallbackHandler:
    def __init__(self,verifier,service,actor):
        if verifier.tenant!=actor.tenant_id:raise ValueError('Callback identity mismatch.')
        self.verifier,self.service,self.actor=verifier,service,actor

    def handle(self,body,timestamp,signature,now_seconds):
        data=self.verifier.verify(body,timestamp,signature,now_seconds)
        state=self.service.read(self.actor,data['case_id'])
        if not state['action'] or state['action']['id']!=data['operation_id']:raise EventRejected()
        # Callback is only a wake-up hint. Trusted read-back drives domain state;
        # duplicate/late callbacks cannot inject success or regress a final result.
        if data['sequence']<=state['action']['sequence']:return state
        return self.service.verify(self.actor,data['case_id'])
