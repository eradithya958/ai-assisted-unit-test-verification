"""Manual Unit Test Suite for QualityGateTracker.

Tests state machine transitions, hysteresis recovery debounce, manual override
locks (BLOCKED), audit history trail, and invalid transition safeguards.
"""

import pytest

from quality_assessment.gate_tracker import (
    GateState,
    InvalidStateTransitionError,
    QualityGateTracker,
)


class TestGateTrackerInitialization:
    """Test suite for QualityGateTracker constructor."""

    def test_default_init(self):
        """Test default constructor initializes state to INITIALIZED."""
        tracker = QualityGateTracker()
        assert tracker.current_state == GateState.INITIALIZED
        assert tracker.pass_threshold == 30.0
        assert tracker.fail_threshold == 70.0
        assert tracker.recovery_debounce == 2
        assert tracker.consecutive_passes == 0
        assert len(tracker.history) == 0

    def test_pass_threshold_greater_than_fail_raises_value_error(self):
        """Test pass_threshold >= fail_threshold raises ValueError."""
        with pytest.raises(ValueError, match="pass_threshold .* must be strictly less than fail_threshold"):
            QualityGateTracker(pass_threshold=80.0, fail_threshold=50.0)

    def test_invalid_debounce_count_raises_value_error(self):
        """Test recovery_debounce < 1 raises ValueError."""
        with pytest.raises(ValueError, match="recovery_debounce must be >= 1"):
            QualityGateTracker(recovery_debounce=0)


class TestGateTransitionsAndDebounce:
    """Test suite for evaluate_risk transitions and debounce logic."""

    def test_direct_transition_from_initial_to_passed(self):
        """Test INITIALIZED transitions directly to PASSED on low risk score."""
        tracker = QualityGateTracker(pass_threshold=30.0, fail_threshold=70.0)
        state = tracker.evaluate_risk(15.0)
        assert state == GateState.PASSED
        assert tracker.current_state == GateState.PASSED
        assert tracker.consecutive_passes == 1
        assert len(tracker.history) == 1

    def test_transition_to_warning_and_recovery_debounce(self):
        """Test transition to WARNING requires 2 consecutive passes to recover to PASSED."""
        tracker = QualityGateTracker(pass_threshold=30.0, fail_threshold=70.0, recovery_debounce=2)

        # Initial to PASSED
        tracker.evaluate_risk(20.0)
        assert tracker.current_state == GateState.PASSED

        # Elevate to WARNING
        state_warn = tracker.evaluate_risk(45.0)
        assert state_warn == GateState.WARNING
        assert tracker.current_state == GateState.WARNING
        assert tracker.consecutive_passes == 0

        # First low risk run: counter increments, but state stays WARNING due to debounce
        state_step1 = tracker.evaluate_risk(25.0)
        assert state_step1 == GateState.WARNING
        assert tracker.consecutive_passes == 1

        # Second consecutive low risk run: debounce satisfied, recovers to PASSED
        state_step2 = tracker.evaluate_risk(20.0)
        assert state_step2 == GateState.PASSED
        assert tracker.current_state == GateState.PASSED
        assert tracker.consecutive_passes == 2

    def test_failed_transition_and_counter_reset(self):
        """Test FAILED transition resets debounce counter immediately."""
        tracker = QualityGateTracker(pass_threshold=30.0, fail_threshold=70.0, recovery_debounce=2)

        # Go to WARNING
        tracker.evaluate_risk(50.0)
        assert tracker.current_state == GateState.WARNING

        # 1 pass
        tracker.evaluate_risk(20.0)
        assert tracker.consecutive_passes == 1

        # Spike to FAILED -> resets pass counter
        state_fail = tracker.evaluate_risk(85.0)
        assert state_fail == GateState.FAILED
        assert tracker.consecutive_passes == 0

        # Pass 1 from FAILED -> stays FAILED
        tracker.evaluate_risk(10.0)
        assert tracker.current_state == GateState.FAILED
        assert tracker.consecutive_passes == 1

        # Pass 2 from FAILED -> recovers to PASSED
        tracker.evaluate_risk(10.0)
        assert tracker.current_state == GateState.PASSED
        assert tracker.consecutive_passes == 2

    def test_evaluate_risk_invalid_inputs(self):
        """Test invalid types and out of range values raise exceptions."""
        tracker = QualityGateTracker()
        with pytest.raises(TypeError, match="risk_score must be numeric"):
            tracker.evaluate_risk(True)
        with pytest.raises(TypeError, match="risk_score must be numeric"):
            tracker.evaluate_risk("50.0")
        with pytest.raises(ValueError, match="risk_score must be in"):
            tracker.evaluate_risk(-1.0)
        with pytest.raises(ValueError, match="risk_score must be in"):
            tracker.evaluate_risk(100.1)


class TestManualOverrideAndBlocking:
    """Test suite for manual blocking and reset operations."""

    def test_manual_block_freezes_state_transitions(self):
        """Test BLOCKED gate ignores risk evaluations until reset."""
        tracker = QualityGateTracker()
        tracker.evaluate_risk(10.0)
        assert tracker.current_state == GateState.PASSED

        tracker.block_gate("Critical vulnerability CVE-2026-9999 detected")
        assert tracker.current_state == GateState.BLOCKED

        # While BLOCKED, low risk evaluations are ignored and return BLOCKED
        state = tracker.evaluate_risk(0.0)
        assert state == GateState.BLOCKED
        assert tracker.current_state == GateState.BLOCKED

    def test_empty_block_reason_raises_value_error(self):
        """Test blocking without a valid reason raises ValueError."""
        tracker = QualityGateTracker()
        with pytest.raises(ValueError, match="Block reason must be a non-empty string"):
            tracker.block_gate("   ")

    def test_reset_from_blocked_to_initial(self):
        """Test resetting from BLOCKED transitions to INITIALIZED."""
        tracker = QualityGateTracker()
        tracker.block_gate("Emergency block")
        assert tracker.current_state == GateState.BLOCKED

        tracker.reset_to_initial("Security review signed off")
        assert tracker.current_state == GateState.INITIALIZED
        assert tracker.consecutive_passes == 0

    def test_illegal_transition_raises_error(self):
        """Test illegal direct transition (e.g. BLOCKED directly to PASSED) raises InvalidStateTransitionError."""
        tracker = QualityGateTracker()
        tracker.block_gate("Lockdown")
        with pytest.raises(InvalidStateTransitionError, match="Cannot transition gate from BLOCKED to PASSED"):
            tracker._apply_transition(GateState.PASSED, 0.0, "Forced bypass")

    def test_history_records_audit_trail(self):
        """Test history entries record transitions, reasons, and timestamps."""
        tracker = QualityGateTracker()
        tracker.evaluate_risk(10.0, reason="Sprint 1 release")
        tracker.evaluate_risk(80.0, reason="Regression detected")

        history = tracker.history
        assert len(history) == 2
        assert history[0].from_state == GateState.INITIALIZED
        assert history[0].to_state == GateState.PASSED
        assert history[0].reason == "Sprint 1 release"
        assert history[1].to_state == GateState.FAILED

