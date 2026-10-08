"""Synthetic intake and an atomic repository contract; no external side effects."""
from dataclasses import dataclass, field
from datetime import datetime, timezone
import re
from threading import Lock
from typing import Protocol
from uuid import uuid4

from .contracts import AccessDenied, Actor, Role, require_staff


class CaseError(Exception):
    """Fixed public error codes, never request content."""


@dataclass(frozen=True)
class Intake:
    ticket_id: str
    requester_id: str
    summary: str = field(repr=False)
    requested_access: str
    resource: str
    synthetic: bool


@dataclass(frozen=True)
class Case:
    case_id: str
    tenant_id: str
    created_by: str
    intake: Intake
    created_at: str
    status: str = 'received'
    version: int = 1


class CaseRepository(Protocol):
    def create(self, actor: Actor, key: str, intake: Intake) -> tuple[Case, bool]:
        """Atomically deduplicate tenant+actor+key; conflict if payload changed.

        Return (case, created). Future SQL adapters must enforce uniqueness in a
        transaction; a preliminary SELECT without a constraint is insufficient.
        """
        ...

    def get(self, tenant_id: str, case_id: str) -> Case | None: ...


class MemoryCaseRepository:
    """Bounded, process-local test/development store. Lost on restart."""
    def __init__(self, capacity: int = 1000):
        if capacity < 1:
            raise ValueError('Invalid capacity.')
        self._capacity = capacity
        self._lock = Lock()
        self._cases: dict[tuple[str, str], Case] = {}
        self._keys: dict[tuple[str, str, str], Case] = {}

    def create(self, actor: Actor, key: str, intake: Intake) -> tuple[Case, bool]:
        scope = (actor.tenant_id, actor.actor_id, key)
        with self._lock:
            previous = self._keys.get(scope)
            if previous:
                if previous.intake != intake:
                    raise CaseError('idempotency_conflict')
                return previous, False
            if len(self._cases) >= self._capacity:
                raise CaseError('storage_capacity')
            case = Case(str(uuid4()), actor.tenant_id, actor.actor_id, intake,
                        datetime.now(timezone.utc).isoformat())
            self._cases[(actor.tenant_id, case.case_id)] = case
            self._keys[scope] = case
            return case, True

    def get(self, tenant_id: str, case_id: str) -> Case | None:
        with self._lock:
            return self._cases.get((tenant_id, case_id))


class CaseService:
    def __init__(self, repository: CaseRepository):
        self.repository = repository

    def create(self, actor: Actor, key: str, data: object) -> tuple[Case, bool]:
        require_staff(actor, actor.tenant_id)
        if actor.role not in (Role.SPECIALIST, Role.SUPERVISOR):
            raise AccessDenied()
        if not isinstance(key, str) or not re.fullmatch(r'[A-Za-z0-9._:-]{1,128}', key):
            raise CaseError('invalid_idempotency_key')
        fields = {'ticket_id','requester_id','summary','requested_access','resource','synthetic'}
        if type(data) is not dict or not fields <= data.keys() or data.keys() - fields - {'tenant_id'}:
            raise CaseError('invalid_request')
        # A supplied fixture tenant can only assert equality, never set identity.
        if 'tenant_id' in data and data['tenant_id'] != actor.tenant_id:
            raise AccessDenied()
        for name, limit in [('ticket_id',64),('requester_id',128),('summary',2000)]:
            value = data[name]
            if (not isinstance(value, str) or not value.strip() or len(value) > limit
                    or any(ord(c) < 32 or ord(c) == 127 for c in value)):
                raise CaseError('invalid_request')
        if (not re.fullmatch(r'SYN-[0-9]+', data['ticket_id'])
                or data['synthetic'] is not True
                or data['requested_access'] != 'read-only' or data['resource'] != 'reports'):
            raise CaseError('invalid_request')
        return self.repository.create(actor, key, Intake(**{k:data[k] for k in fields}))

    def get(self, actor: Actor, case_id: str) -> Case:
        require_staff(actor, actor.tenant_id)
        case = self.repository.get(actor.tenant_id, case_id)
        if case is None:
            raise CaseError('not_found')
        return case
