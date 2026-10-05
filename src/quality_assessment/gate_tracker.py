"""Stateful Quality Gate Tracking Module.

Provides finite-state machine transitions for CI/CD quality gate enforcement
with debounce / hysteresis thresholds and audit history tracking.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional


class GateState(str, Enum):
    """Discrete states of a software quality gate."""
    INITIALIZED = "INITIALIZED"
    PASSED = "PASSED"
    WARNING = "WARNING"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"


class InvalidStateTransitionError(Exception):
    """Raised when an illegal state machine transition is attempted."""
    pass


@dataclass
class StateTransitionRecord:
    """Audit log entry for quality gate state transitions."""
    from_state: GateState
    to_state: GateState
    reason: str
    risk_score: float
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())


class QualityGateTracker:
    """Stateful quality gate controller with hysteresis debounce."""

    # Allowed direct state transitions
    VALID_TRANSITIONS = {
        GateState.INITIALIZED: {GateState.PASSED, GateState.WARNING, GateState.FAILED, GateState.BLOCKED},
        GateState.PASSED: {GateState.WARNING, GateState.FAILED, GateState.BLOCKED, GateState.PASSED},
        GateState.WARNING: {GateState.PASSED, GateState.FAILED, GateState.BLOCKED, GateState.WARNING},
        GateState.FAILED: {GateState.PASSED, GateState.BLOCKED, GateState.FAILED, GateState.WARNING},
        GateState.BLOCKED: {GateState.INITIALIZED},  # Requires manual unblock/reset
    }

    def __init__(
        self,
        pass_threshold: float = 30.0,
        fail_threshold: float = 70.0,
        recovery_debounce: int = 2,
    ):
        """Initialize the quality gate state machine.

        Args:
            pass_threshold: Max risk score to transition into PASSED (default 30.0).
            fail_threshold: Min risk score that triggers FAILED (default 70.0).
            recovery_debounce: Number of consecutive evaluations meeting pass_threshold
                required to recover from WARNING/FAILED back to PASSED (>= 1).

        Raises:
            ValueError: If pass_threshold >= fail_threshold or recovery_debounce < 1.
        """
        if pass_threshold >= fail_threshold:
            raise ValueError(
                f"pass_threshold ({pass_threshold}) must be strictly less than fail_threshold ({fail_threshold})"
            )
        if recovery_debounce < 1:
            raise ValueError(f"recovery_debounce must be >= 1, got {recovery_debounce}")

        self.pass_threshold = float(pass_threshold)
        self.fail_threshold = float(fail_threshold)
        self.recovery_debounce = recovery_debounce

        self._current_state = GateState.INITIALIZED
        self._history: List[StateTransitionRecord] = []
        self._consecutive_pass_count = 0

    @property
    def current_state(self) -> GateState:
        """Get the current gate state."""
        return self._current_state

    @property
    def history(self) -> List[StateTransitionRecord]:
        """Get copy of the state transition audit history."""
        return list(self._history)

    @property
    def consecutive_passes(self) -> int:
        """Get current count of consecutive evaluations under pass_threshold."""
        return self._consecutive_pass_count

    def evaluate_risk(self, risk_score: float, reason: str = "") -> GateState:
        """Evaluate a risk score and trigger appropriate state transitions.

        Evaluation Rules:
            - If BLOCKED: No automated transition is allowed; remains BLOCKED until unblocked.
            - If risk_score >= fail_threshold:
                - Immediately transitions to FAILED.
                - Resets consecutive pass counter to 0.
            - If pass_threshold < risk_score < fail_threshold:
                - Transitions to WARNING.
                - Resets consecutive pass counter to 0.
            - If risk_score <= pass_threshold:
                - Increments consecutive pass counter.
                - If in WARNING or FAILED: requires consecutive_passes >= recovery_debounce to transition to PASSED.
                - If already PASSED or INITIALIZED: immediately transitions to/stays PASSED.

        Args:
            risk_score: Software risk score in [0.0, 100.0].
            reason: Optional context string describing the evaluation.

        Returns:
            GateState: The new or unchanged current state after evaluation.

        Raises:
            TypeError: If risk_score is non-numeric or boolean.
            ValueError: If risk_score is outside [0.0, 100.0].
        """
        if isinstance(risk_score, bool) or not isinstance(risk_score, (int, float)):
            raise TypeError(f"risk_score must be numeric, got {type(risk_score).__name__}")
        if risk_score < 0.0 or risk_score > 100.0:
            raise ValueError(f"risk_score must be in [0.0, 100.0], got {risk_score}")

        r_score = float(risk_score)

        if self._current_state == GateState.BLOCKED:
            return GateState.BLOCKED

        target_state: GateState

        if r_score >= self.fail_threshold:
            self._consecutive_pass_count = 0
            target_state = GateState.FAILED
        elif r_score > self.pass_threshold:
            self._consecutive_pass_count = 0
            target_state = GateState.WARNING
        else:
            # Score satisfies pass threshold
            self._consecutive_pass_count += 1
            if self._current_state in (GateState.WARNING, GateState.FAILED):
                if self._consecutive_pass_count >= self.recovery_debounce:
                    target_state = GateState.PASSED
                else:
                    target_state = self._current_state  # Stay in current state during debounce
            else:
                target_state = GateState.PASSED

        self._apply_transition(target_state, r_score, reason or f"Evaluated risk {r_score}")
        return self._current_state

    def block_gate(self, reason: str) -> None:
        """Manually block the quality gate (e.g. for security lockdown).

        Args:
            reason: Mandatory reason for blocking the gate.

        Raises:
            ValueError: If reason is empty or whitespace.
            InvalidStateTransitionError: If gate cannot transition to BLOCKED.
        """
        if not reason or not reason.strip():
            raise ValueError("Block reason must be a non-empty string")

        self._apply_transition(GateState.BLOCKED, 100.0, f"Manual Block: {reason.strip()}")

    def reset_to_initial(self, reason: str = "Reset") -> None:
        """Reset the state machine back to INITIALIZED state.

        Args:
            reason: Optional explanation for the reset.
        """
        self._consecutive_pass_count = 0
        self._apply_transition(GateState.INITIALIZED, 0.0, reason)

    def _apply_transition(self, target: GateState, risk_score: float, reason: str) -> None:
        """Internal helper to validate and commit state transition."""
        allowed = self.VALID_TRANSITIONS.get(self._current_state, set())
        if target not in allowed:
            raise InvalidStateTransitionError(
                f"Cannot transition gate from {self._current_state.value} to {target.value}"
            )

        prev = self._current_state
        self._current_state = target
        self._history.append(
            StateTransitionRecord(
                from_state=prev,
                to_state=target,
                reason=reason,
                risk_score=risk_score,
            )
        )
