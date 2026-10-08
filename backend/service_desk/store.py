"""Versioned aggregate boundary; SQL implements the same CAS contract later."""
from copy import deepcopy
from threading import Lock
from typing import Protocol


class Conflict(Exception): pass
class Missing(Exception): pass


class StateStore(Protocol):
    def create(self, tenant: str, key: str, state: dict) -> None: ...
    def get(self, tenant: str, key: str) -> dict: ...
    def save(self, tenant: str, key: str, expected_revision: int, state: dict) -> None: ...
    def list(self, tenant: str) -> list[dict]: ...


class MemoryStateStore:
    def __init__(self, capacity=1000):
        self._states = {}
        self._lock = Lock()
        self.capacity = capacity

    def create(self, tenant, key, state):
        with self._lock:
            if (tenant,key) in self._states or len(self._states) >= self.capacity:
                raise Conflict()
            if state['tenant'] != tenant or state['id'] != key or state['revision'] != 1:
                raise ValueError('Invalid initial state.')
            self._states[tenant,key] = deepcopy(state)

    def get(self, tenant, key):
        with self._lock:
            if (tenant,key) not in self._states: raise Missing()
            return deepcopy(self._states[tenant,key])

    def save(self, tenant, key, expected_revision, state):
        with self._lock:
            old = self._states.get((tenant,key))
            if old is None: raise Missing()
            if old['revision'] != expected_revision: raise Conflict()
            if (state['tenant'] != tenant or state['id'] != key
                    or state['revision'] != expected_revision + 1
                    or state['audit'][:-1] != old['audit']):
                raise ValueError('Invalid aggregate update.')
            self._states[tenant,key] = deepcopy(state)

    def list(self, tenant):
        with self._lock:
            return deepcopy([s for (t,_),s in self._states.items() if t==tenant])
