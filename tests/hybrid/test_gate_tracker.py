"""Hybrid Test Suite for QualityGateTracker (AI-Generated Base + Human Review).

Strengthened with multi-step hysteresis debounce verification,
state invariant assertions, and audit log history checks.
"""

import pytest
from quality_assessment.gate_tracker import (
    GateState,
    InvalidStateTransitionError,
    QualityGateTracker,
)


class TestQualityGateTrackerHybrid:
    """Hybrid test suite for QualityGateTracker."""

    def test_init_state(self):
        """Test initial state of gate."""
        tracker = QualityGateTracker()
        assert tracker.current_state == GateState.INITIALIZED
        assert tracker.consecutive_passes == 0

    def test_evaluate_risk_pass(self):
        """Test transitioning to PASSED."""
        tracker = QualityGateTracker()
        state = tracker.evaluate_risk(10.0)
        assert state == GateState.PASSED
        assert tracker.consecutive_passes == 1

    def test_evaluate_risk_fail(self):
        """Test transitioning to FAILED on high risk."""
        tracker = QualityGateTracker()
        state = tracker.evaluate_risk(90.0)
        assert state == GateState.FAILED
        assert tracker.consecutive_passes == 0

    def test_evaluate_risk_warning(self):
        """Test transitioning to WARNING."""
        tracker = QualityGateTracker()
        state = tracker.evaluate_risk(50.0)
        assert state == GateState.WARNING

    # Human Added: Hysteresis Debounce Multi-Step Temporal Verification
    def test_hysteresis_debounce_recovery(self):
        """Human Added: Test that recovery from WARNING/FAILED requires 2 consecutive passes."""
        tracker = QualityGateTracker(pass_threshold=30.0, fail_threshold=70.0, recovery_debounce=2)
        tracker.evaluate_risk(50.0)
        assert tracker.current_state == GateState.WARNING

        # 1st pass: stays in WARNING
        tracker.evaluate_risk(20.0)
        assert tracker.current_state == GateState.WARNING
        assert tracker.consecutive_passes == 1

        # 2nd pass: satisfies debounce -> recovers to PASSED
        tracker.evaluate_risk(20.0)
        assert tracker.current_state == GateState.PASSED
        assert tracker.consecutive_passes == 2

    def test_block_and_reset_lifecycle(self):
        """Test manual gate blocking and reset from blocked."""
        tracker = QualityGateTracker()
        tracker.block_gate("Security lockdown")
        assert tracker.current_state == GateState.BLOCKED

        # Reset back to INITIALIZED
        tracker.reset_to_initial("Review completed")
        assert tracker.current_state == GateState.INITIALIZED
        assert len(tracker.history) == 2

    def test_illegal_transition_raises_error(self):
        """Human Added: Verify illegal transition raises InvalidStateTransitionError."""
        tracker = QualityGateTracker()
        tracker.block_gate("Lock")
        with pytest.raises(InvalidStateTransitionError):
            tracker._apply_transition(GateState.PASSED, 0.0, "Forced bypass")
