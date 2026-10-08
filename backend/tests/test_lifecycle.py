import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone

from service_desk.contracts import AccessDenied, Actor, Role
from service_desk.lifecycle import (
    ActionState, LifecycleBlocked, Proposal, VerifiedOutcome, approve,
    require_closable, require_current_approval, require_safe_retry, should_reopen,
)


class LifecycleTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 10, 8, tzinfo=timezone.utc)
        self.proposal = Proposal("alpha", "case-1", 1, "payload-v1", "policy-v1", "requester")
        self.supervisor = Actor("supervisor", "alpha", Role.SUPERVISOR)
        self.approval = approve(self.supervisor, self.proposal, self.now, self.now + timedelta(minutes=15))

    def test_approval_requires_same_tenant_supervisor_and_no_self_approval(self):
        for actor in (Actor("a", "alpha", Role.AUDITOR),
                      Actor("a", "beta", Role.SUPERVISOR),
                      Actor("requester", "alpha", Role.SUPERVISOR)):
            with self.subTest(actor=actor), self.assertRaises(AccessDenied):
                approve(actor, self.proposal, self.now, self.now + timedelta(minutes=15))

    def test_all_snapshot_changes_invalidate_approval(self):
        for field, value in (("tenant_id", "beta"), ("case_id", "case-2"),
                             ("case_version", 2), ("payload_hash", "changed"),
                             ("policy_version", "policy-v2"), ("requester_id", "other")):
            with self.subTest(field=field), self.assertRaisesRegex(LifecycleBlocked, "stale_approval"):
                require_current_approval(self.approval, replace(self.proposal, **{field: value}), self.now)

    def test_approval_expiry_boundary(self):
        require_current_approval(self.approval, self.proposal, self.now + timedelta(minutes=14, seconds=59))
        with self.assertRaisesRegex(LifecycleBlocked, "expired_approval"):
            require_current_approval(self.approval, self.proposal, self.now + timedelta(minutes=15))

    def test_approval_rejects_naive_clock(self):
        with self.assertRaises(LifecycleBlocked):
            approve(self.supervisor, self.proposal, self.now.replace(tzinfo=None), self.now)

    def outcome(self):
        return VerifiedOutcome("alpha", "case-1", "action-1", 1, "target/receipt-1", self.now, True)

    def close(self, state, outcome):
        require_closable(tenant_id="alpha", case_id="case-1", action_id="action-1",
                         case_version=1, state=state, dispatched_at=self.now,
                         now=self.now + timedelta(seconds=30), outcome=outcome)

    def test_accepted_running_failed_unknown_cannot_close(self):
        for state in ActionState:
            if state != ActionState.SUCCEEDED:
                with self.subTest(state=state), self.assertRaises(LifecycleBlocked):
                    self.close(state, self.outcome())

    def test_success_requires_readback_not_receipt_alone(self):
        with self.assertRaises(LifecycleBlocked):
            self.close(ActionState.SUCCEEDED, None)
        self.close(ActionState.SUCCEEDED, self.outcome())

    def test_wrong_stale_future_or_negative_evidence_cannot_close(self):
        for field, value in (("tenant_id", "beta"), ("case_id", "case-2"),
                             ("action_id", "other"), ("case_version", 2),
                             ("matches_expected", False), ("evidence_reference", ""),
                             ("observed_at", self.now - timedelta(seconds=1)),
                             ("observed_at", self.now + timedelta(days=1))):
            with self.subTest(field=field), self.assertRaises(LifecycleBlocked):
                self.close(ActionState.SUCCEEDED, replace(self.outcome(), **{field: value}))

    def test_unknown_requires_terminal_reconciliation_before_retry(self):
        with self.assertRaises(LifecycleBlocked):
            require_safe_retry(ActionState.UNKNOWN, terminal_absence_confirmed=False)
        require_safe_retry(ActionState.UNKNOWN, terminal_absence_confirmed=True)
        with self.assertRaises(LifecycleBlocked):
            require_safe_retry(ActionState.SUCCEEDED, terminal_absence_confirmed=True)

    def test_reopen_requires_authenticated_fresh_same_tenant_adverse_evidence(self):
        args = dict(closed=True, evidence_authenticated=True, evidence_tenant="alpha",
                    case_tenant="alpha", closed_at=self.now,
                    observed_at=self.now + timedelta(seconds=1),
                    now=self.now + timedelta(seconds=2), invalidates_outcome=True)
        self.assertTrue(should_reopen(**args))
        for field, value in (("evidence_authenticated", False), ("evidence_tenant", "beta"),
                             ("observed_at", self.now), ("invalidates_outcome", False),
                             ("closed", False)):
            with self.subTest(field=field):
                self.assertFalse(should_reopen(**{**args, field: value}))
