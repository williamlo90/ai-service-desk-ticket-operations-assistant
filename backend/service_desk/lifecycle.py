"""Pure predicates for the prototype; persistence and endpoint auth remain Phase 1B.

These checks must run inside the eventual repository transaction. They are not
an execution gateway and do not dispatch actions or trust external callback text.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from .contracts import Actor, Role, AccessDenied


class ActionState(StrEnum):
    REQUESTED = "requested"
    ACCEPTED = "accepted"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class Proposal:
    tenant_id: str
    case_id: str
    case_version: int
    payload_hash: str
    policy_version: str
    requester_id: str


@dataclass(frozen=True)
class Approval:
    proposal: Proposal
    approver_id: str
    approved_at: datetime
    expires_at: datetime


class LifecycleBlocked(Exception):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def aware(value: datetime) -> bool:
    return value.tzinfo is not None and value.utcoffset() is not None


def approve(actor: Actor, proposal: Proposal, now: datetime,
            expires_at: datetime) -> Approval:
    if (actor.role != Role.SUPERVISOR or actor.tenant_id != proposal.tenant_id
            or not actor.actor_id or actor.actor_id == proposal.requester_id):
        raise AccessDenied()
    if (not aware(now) or not aware(expires_at) or expires_at <= now
            or proposal.case_version < 1 or not proposal.payload_hash
            or not proposal.policy_version or not proposal.case_id):
        raise LifecycleBlocked("invalid_approval")
    return Approval(proposal, actor.actor_id, now, expires_at)


def require_current_approval(approval: Approval, current: Proposal, now: datetime) -> None:
    if approval.proposal != current:
        raise LifecycleBlocked("stale_approval")
    if (not aware(now) or not aware(approval.approved_at) or not aware(approval.expires_at)
            or now < approval.approved_at or now >= approval.expires_at):
        raise LifecycleBlocked("expired_approval")


@dataclass(frozen=True)
class VerifiedOutcome:
    """Issued by a trusted verifier after authoritative target read-back."""

    tenant_id: str
    case_id: str
    action_id: str
    case_version: int
    evidence_reference: str
    observed_at: datetime
    matches_expected: bool


def require_closable(*, tenant_id: str, case_id: str, action_id: str,
                     case_version: int, state: ActionState,
                     dispatched_at: datetime, now: datetime,
                     outcome: VerifiedOutcome | None) -> None:
    if (state != ActionState.SUCCEEDED or outcome is None
            or not outcome.matches_expected or not outcome.evidence_reference
            or (outcome.tenant_id, outcome.case_id, outcome.action_id, outcome.case_version)
            != (tenant_id, case_id, action_id, case_version)
            or not all(aware(t) for t in (dispatched_at, now, outcome.observed_at))
            or not dispatched_at <= outcome.observed_at <= now):
        raise LifecycleBlocked("outcome_not_verified")


def require_safe_retry(state: ActionState, *, terminal_absence_confirmed: bool) -> None:
    # Absence must come from an authoritative, terminal lookup, not a transient miss.
    if state not in (ActionState.FAILED, ActionState.UNKNOWN) or not terminal_absence_confirmed:
        raise LifecycleBlocked("reconciliation_required")


def should_reopen(*, closed: bool, evidence_authenticated: bool,
                  evidence_tenant: str, case_tenant: str,
                  closed_at: datetime, observed_at: datetime,
                  now: datetime, invalidates_outcome: bool) -> bool:
    return (closed and evidence_authenticated and evidence_tenant == case_tenant
            and invalidates_outcome
            and all(aware(t) for t in (closed_at, observed_at, now))
            and closed_at < observed_at <= now)
