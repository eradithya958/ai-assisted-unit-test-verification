"""Hybrid Test Suite for QualityMetricsCalculator (AI-Generated Base + Human Review).

Strengthened with exact mathematical assertions (killing AOR mutants),
discrete entropy constraints, and zero-division overrides.
"""

import pytest
from quality_assessment.metrics import QualityMetricsCalculator


class TestQualityMetricsCalculatorHybrid:
    """Hybrid test suite for QualityMetricsCalculator."""

    # AI Base - Strengthened with exact decimal assertions (replacing weak > 0.0)
    def test_precision_recall_f1_nominal(self):
        """Test standard precision, recall, and F1 calculations with exact assertions."""
        res = QualityMetricsCalculator.calculate_precision_recall_f1(10, 2, 3)
        # Precision: 10/12 = 0.8333, Recall: 10/13 = 0.7692, F1: 2*(0.8333*0.7692)/(0.8333+0.7692) = 0.8000
        assert res["precision"] == 0.8333
        assert res["recall"] == 0.7692
        assert res["f1_score"] == 0.8000

    def test_precision_recall_f1_zero_division(self):
        """Test zero division edge case returns default 0.0."""
        res = QualityMetricsCalculator.calculate_precision_recall_f1(0, 0, 0)
        assert res["precision"] == 0.0
        assert res["recall"] == 0.0
        assert res["f1_score"] == 0.0

    def test_precision_recall_custom_zero_division(self):
        """Human Added: Test custom zero division parameter."""
        res = QualityMetricsCalculator.calculate_precision_recall_f1(0, 0, 0, zero_division_value=0.5)
        assert res["precision"] == 0.5
        assert res["recall"] == 0.5
        assert res["f1_score"] == 0.5

    def test_precision_recall_negative_counts(self):
        """Test negative inputs raise ValueError."""
        with pytest.raises(ValueError, match="cannot be negative"):
            QualityMetricsCalculator.calculate_precision_recall_f1(-1, 5, 5)

    @pytest.mark.parametrize("invalid_type", [True, False, 1.5, "10", None])
    def test_precision_recall_type_errors(self, invalid_type):
        """Human Added: Rejects booleans and non-integers."""
        with pytest.raises(TypeError, match="must be an integer"):
            QualityMetricsCalculator.calculate_precision_recall_f1(invalid_type, 5, 5)

    def test_brier_score_nominal(self):
        """Test Brier score computation with exact expectation."""
        probs = [0.8, 0.2]
        outcomes = [1, 0]
        # ( (0.8-1)^2 + (0.2-0)^2 ) / 2 = (0.04 + 0.04) / 2 = 0.040000
        score = QualityMetricsCalculator.calculate_brier_score(probs, outcomes)
        assert score == 0.040000

    def test_brier_score_mismatched_length(self):
        """Test mismatched lists raise ValueError."""
        with pytest.raises(ValueError, match="Length mismatch"):
            QualityMetricsCalculator.calculate_brier_score([0.5], [1, 0])

    def test_cyclomatic_density_nominal(self):
        """Test cyclomatic density calculation."""
        density = QualityMetricsCalculator.calculate_cyclomatic_density(10, 200)
        assert density == 5.0

    def test_cyclomatic_density_invalid_loc(self):
        """Test LOC < 1 raises ValueError."""
        with pytest.raises(ValueError, match="lines_of_code must be >= 1"):
            QualityMetricsCalculator.calculate_cyclomatic_density(5, 0)

    def test_rolling_pass_rate_nominal(self):
        """Test pass rate calculation over history and sliding window."""
        history = [True, True, False, True]
        rate = QualityMetricsCalculator.calculate_rolling_pass_rate(history)
        assert rate == 75.0
        # Window of 2 takes [False, True] -> 50%
        assert QualityMetricsCalculator.calculate_rolling_pass_rate(history, window_size=2) == 50.0

    def test_shannon_entropy_nominal(self):
        """Test Shannon entropy calculation."""
        probs = [0.5, 0.5]
        entropy = QualityMetricsCalculator.calculate_shannon_entropy(probs)
        assert entropy == 1.0

    def test_shannon_entropy_unnormalized_error(self):
        """Human Added: Catch unnormalized probabilities sum check."""
        with pytest.raises(ValueError, match="Probabilities must sum to 1.0"):
            QualityMetricsCalculator.calculate_shannon_entropy([0.3, 0.3])
