"""Independent target ledger. Domain code cannot declare external success."""
from copy import deepcopy
from threading import Lock


class SimulatedTarget:
    def __init__(self):
        self._lock=Lock()
        self._ops={}
        self._effects={}
        self._ledger=[]
        self.timeout_after_effect=False

    def submit(self, tenant, operation_id, payload):
        with self._lock:
            key=(tenant,operation_id)
            if key in self._ops:
                if self._ops[key]['payload'] != payload: raise ValueError('Operation conflict.')
                return deepcopy(self._ops[key])
            self._ops[key]={'payload':deepcopy(payload),'status':'accepted','sequence':1}
            if self.timeout_after_effect:
                self._complete(key,True)
                raise TimeoutError('Simulated lost response.')
            return deepcopy(self._ops[key])

    def _complete(self,key,success):
        op=self._ops[key]
        if op['status'] in ('succeeded','failed'): return
        op['status']='succeeded' if success else 'failed'
        op['sequence']+=1
        if success:
            self._effects[key]=True
            self._ledger.append({'tenant':key[0],'operation_id':key[1],
                                 'payload':deepcopy(op['payload'])})

    def complete(self,tenant,operation_id,success=True):
        with self._lock: self._complete((tenant,operation_id),success)

    def revoke(self,tenant,operation_id):
        with self._lock: self._effects[(tenant,operation_id)]=False

    def inspect(self,tenant,operation_id,payload):
        with self._lock:
            op=self._ops.get((tenant,operation_id))
            if not op: return {'status':'unknown','matches':False,'sequence':0}
            return {'status':op['status'], 'sequence':op['sequence'],
                    'matches':op['payload']==payload and self._effects.get((tenant,operation_id),False)}

    def ledger(self):
        with self._lock: return deepcopy(self._ledger)

    def request_count(self):
        with self._lock: return len(self._ops)
