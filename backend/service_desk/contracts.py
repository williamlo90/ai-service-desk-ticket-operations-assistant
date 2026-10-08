"""Trusted application context is separate from untrusted ticket content."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum


class Role(StrEnum):
    SPECIALIST = "specialist"
    SUPERVISOR = "supervisor"
    AUDITOR = "auditor"
    REQUESTER = "requester"


@dataclass(frozen=True)
class Actor:
    """Construct only after authentication; never from ticket text or LLM output."""

    actor_id: str
    tenant_id: str
    role: Role


@dataclass(frozen=True)
class Ticket:
    tenant_id: str
    key: str
    project_key: str
    summary: str = field(repr=False)
    source_status: str
    observed_at: datetime


class AccessDenied(Exception):
    def __init__(self):
        super().__init__("Access denied.")


def require_staff(actor: Actor, tenant_id: str) -> None:
    if (not actor.actor_id or not tenant_id or actor.tenant_id != tenant_id
            or actor.role not in (Role.SPECIALIST, Role.SUPERVISOR, Role.AUDITOR)):
        raise AccessDenied()
