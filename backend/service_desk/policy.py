"""Deterministic synthetic policies shared by all orchestration candidates."""
from dataclasses import dataclass
from .contracts import AccessDenied, Role, require_staff


@dataclass(frozen=True)
class Policy:
    version: str
    action: str
    ttl_seconds: int = 900


POLICIES = {
    'access_request': Policy('access-v1','grant_read_access'),
    'service_incident': Policy('incident-v1','restart_service'),
    'repeated_ticket': Policy('duplicate-v1','link_tickets'),
}


def triage(text: str) -> dict:
    if not isinstance(text,str) or not 1 <= len(text) <= 4000:
        raise ValueError('Invalid message.')
    lower=text.lower()
    if 'admin' in lower or 'privileged' in lower:
        return {'category':'unsupported','decision':'escalate','missing':[]}
    if 'sd-1' in lower and 'sd-2' in lower:
        return {'category':'repeated_ticket','decision':'prepare','missing':[]}
    if 'demo-api' in lower and any(x in lower for x in ('unavailable','down','outage')):
        return {'category':'service_incident','decision':'prepare','missing':[]}
    missing=[]
    if 'reports' not in lower: missing.append('resource')
    if 'read' not in lower: missing.append('entitlement')
    return {'category':'access_request','decision':'clarification' if missing else 'prepare','missing':missing}


def context(actor, tenant, category):
    require_staff(actor,tenant)
    policy=POLICIES.get(category)
    if not policy: return {'decision':'escalate','sources':[]}
    return {'policy':policy.version,'action':policy.action,
            'sources':[f'sop:{tenant}:{policy.version}'],'synthetic':True}


def writer(actor, tenant):
    require_staff(actor,tenant)
    if actor.role not in (Role.SPECIALIST,Role.SUPERVISOR): raise AccessDenied()
