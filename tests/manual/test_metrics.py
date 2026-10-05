"""Manual Unit Test Suite for QualityMetricsCalculator.

Tests arithmetic precision, division-by-zero safeguards, edge cases,
statistical distributions, and exception paths.
"""

import math
import pytest

from quality_assessment.metrics import QualityMetricsCalculator


class TestPrecisionRecallF1:
    """Test suite for calculate_precision_recall_f1."""

    def test_nominal_balanced_metrics(self):
        """Test standard scenario with balanced non-zero confusion counts."""
        res = QualityMetricsCalculator.calculate_precision_recall_f1(
            true_positives=80,
            false_positives=20,
            false_negatives=20,
        )
        assert res["precision"] == 0.8000
        assert res["recall"] == 0.8000
        assert res["f1_score"] == 0.8000

    def test_asymmetric_precision_recall(self):
        """Test scenario with asymmetric confusion counts."""
        # TP=50, FP=10 -> Precision = 50/60 = 0.8333
        # TP=50, FN=50 -> Recall = 50/100 = 0.5000
        # F1 = 2 * (0.83333 * 0.5) / (1.33333) = 0.6250
        res = QualityMetricsCalculator.calculate_precision_recall_f1(50, 10, 50)
        assert res["precision"] == 0.8333
        assert res["recall"] == 0.5000
        assert res["f1_score"] == 0.6250

    def test_zero_division_prec_and_recall_with_default(self):
        """Test zero TP, FP, FN yields 0.0 with default zero_division_value."""
        res = QualityMetricsCalculator.calculate_precision_recall_f1(0, 0, 0)
        assert res["precision"] == 0.0
        assert res["recall"] == 0.0
        assert res["f1_score"] == 0.0

    def test_custom_zero_division_value(self):
        """Test custom zero_division_value propagation."""
        res = QualityMetricsCalculator.calculate_precision_recall_f1(0, 0, 0, zero_division_value=1.0)
        assert res["precision"] == 1.0
        assert res["recall"] == 1.0
        assert res["f1_score"] == 1.0

    def test_zero_denominator_precision_only(self):
        """Test TP=0, FP=0, FN=10 (Precision denominator is 0, Recall is 0.0)."""
        res = QualityMetricsCalculator.calculate_precision_recall_f1(0, 0, 10, zero_division_value=0.5)
        assert res["precision"] == 0.5
        assert res["recall"] == 0.0
        assert res["f1_score"] == 0.0

    @pytest.mark.parametrize("invalid_count", [-1, -100])
    def test_negative_counts_raise_value_error(self, invalid_count):
        """Test that negative count inputs raise ValueError."""
        with pytest.raises(ValueError, match="cannot be negative"):
            QualityMetricsCalculator.calculate_precision_recall_f1(invalid_count, 10, 10)
        with pytest.raises(ValueError, match="cannot be negative"):
            QualityMetricsCalculator.calculate_precision_recall_f1(10, invalid_count, 10)
        with pytest.raises(ValueError, match="cannot be negative"):
            QualityMetricsCalculator.calculate_precision_recall_f1(10, 10, invalid_count)

    @pytest.mark.parametrize("invalid_type", [True, False, 1.5, "10", None])
    def test_non_integer_counts_raise_type_error(self, invalid_type):
        """Test that non-integer types raise TypeError."""
        with pytest.raises(TypeError, match="must be an integer"):
            QualityMetricsCalculator.calculate_precision_recall_f1(invalid_type, 10, 10)

    @pytest.mark.parametrize("invalid_zdiv", [-0.1, 1.1, True, "0.0"])
    def test_invalid_zero_division_value_raises(self, invalid_zdiv):
        """Test validation of zero_division_value."""
        with pytest.raises((ValueError, TypeError)):
            QualityMetricsCalculator.calculate_precision_recall_f1(0, 0, 0, zero_division_value=invalid_zdiv)


class TestBrierScore:
    """Test suite for calculate_brier_score."""

    def test_perfect_predictions(self):
        """Test Brier score is 0.0 when predictions match ground truth exactly."""
        probs = [1.0, 0.0, 1.0, 0.0]
        outcomes = [1, 0, 1, 0]
        score = QualityMetricsCalculator.calculate_brier_score(probs, outcomes)
        assert score == 0.0

    def test_worst_possible_predictions(self):
        """Test Brier score is 1.0 when predictions are 100% wrong."""
        probs = [1.0, 0.0]
        outcomes = [0, 1]
        score = QualityMetricsCalculator.calculate_brier_score(probs, outcomes)
        assert score == 1.0

    def test_nominal_calibrated_predictions(self):
        """Test standard fractional probabilities."""
        probs = [0.9, 0.1, 0.8, 0.2]
        outcomes = [1, 0, 1, 0]
        # (0.1^2 + 0.1^2 + 0.2^2 + 0.2^2) / 4 = (0.01 + 0.01 + 0.04 + 0.04) / 4 = 0.10 / 4 = 0.025
        score = QualityMetricsCalculator.calculate_brier_score(probs, outcomes)
        assert score == 0.025000

    def test_empty_lists_raise_value_error(self):
        """Test empty inputs raise ValueError."""
        with pytest.raises(ValueError, match="Input lists cannot be empty"):
            QualityMetricsCalculator.calculate_brier_score([], [])

    def test_length_mismatch_raises_value_error(self):
        """Test mismatched lengths raise ValueError."""
        with pytest.raises(ValueError, match="Length mismatch"):
            QualityMetricsCalculator.calculate_brier_score([0.5, 0.8], [1])

    @pytest.mark.parametrize("invalid_prob_type", [True, False, "0.5", None])
    def test_invalid_probability_types_raise_type_error(self, invalid_prob_type):
        """Test probability element non-numeric raises TypeError."""
        with pytest.raises(TypeError, match="Probability at index .* must be a float/int"):
            QualityMetricsCalculator.calculate_brier_score([invalid_prob_type], [1])

    @pytest.mark.parametrize("invalid_outcome_type", [True, False, 1.5, "1", None])
    def test_invalid_outcome_types_raise_type_error(self, invalid_outcome_type):
        """Test outcome element non-integer raises TypeError."""
        with pytest.raises(TypeError, match="Outcome at index .* must be an integer"):
            QualityMetricsCalculator.calculate_brier_score([0.5], [invalid_outcome_type])

    @pytest.mark.parametrize("invalid_prob", [-0.01, 1.01, float("nan"), float("inf")])
    def test_invalid_probability_values_raise_value_error(self, invalid_prob):
        """Test out of range, nan, or inf probabilities raise ValueError."""
        with pytest.raises(ValueError, match="must be in"):
            QualityMetricsCalculator.calculate_brier_score([invalid_prob], [1])

    @pytest.mark.parametrize("invalid_outcome", [2, -1, 100])
    def test_invalid_outcome_values_raise_value_error(self, invalid_outcome):
        """Test non-binary outcome integers raise ValueError."""
        with pytest.raises(ValueError, match="Outcome at index .* must be either 0 or 1"):
            QualityMetricsCalculator.calculate_brier_score([0.5], [invalid_outcome])

    def test_non_list_types_raise_type_error(self):
        """Test passing non-list containers raises TypeError."""
        with pytest.raises(TypeError, match="must be lists"):
            QualityMetricsCalculator.calculate_brier_score((0.5,), [1])


class TestCyclomaticDensity:
    """Test suite for calculate_cyclomatic_density."""

    def test_nominal_density(self):
        """Test standard calculation: complexity=15, LOC=300 -> (15/300)*100 = 5.0%."""
        density = QualityMetricsCalculator.calculate_cyclomatic_density(15, 300)
        assert density == 5.0

    def test_boundary_values(self):
        """Test minimum valid boundary: complexity=1.0, LOC=1 -> 100.0%."""
        density = QualityMetricsCalculator.calculate_cyclomatic_density(1.0, 1)
        assert density == 100.0

    def test_invalid_complexity_raises_value_error(self):
        """Test complexity < 1.0 raises ValueError."""
        with pytest.raises(ValueError, match="cyclomatic_complexity must be >= 1.0"):
            QualityMetricsCalculator.calculate_cyclomatic_density(0.5, 100)

    def test_invalid_loc_raises_value_error(self):
        """Test lines_of_code < 1 raises ValueError."""
        with pytest.raises(ValueError, match="lines_of_code must be >= 1"):
            QualityMetricsCalculator.calculate_cyclomatic_density(5, 0)

    @pytest.mark.parametrize("invalid_type", [True, "10", None])
    def test_invalid_types_raise_type_error(self, invalid_type):
        """Test type validation."""
        with pytest.raises(TypeError):
            QualityMetricsCalculator.calculate_cyclomatic_density(invalid_type, 100)
        with pytest.raises(TypeError):
            QualityMetricsCalculator.calculate_cyclomatic_density(5, invalid_type)


class TestRollingPassRate:
    """Test suite for calculate_rolling_pass_rate."""

    def test_all_passed(self):
        """Test 100% pass rate."""
        history = [True, True, True, True]
        assert QualityMetricsCalculator.calculate_rolling_pass_rate(history) == 100.0

    def test_windowed_pass_rate(self):
        """Test window takes the most recent N elements."""
        history = [False, False, True, True, True]
        # Window of 3 takes the last 3 elements (all True) -> 100%
        assert QualityMetricsCalculator.calculate_rolling_pass_rate(history, window_size=3) == 100.0
        # Window of 4 takes [False, True, True, True] -> 75%
        assert QualityMetricsCalculator.calculate_rolling_pass_rate(history, window_size=4) == 75.0

    def test_window_size_larger_than_history(self):
        """Test window larger than list uses full list."""
        history = [True, False]
        assert QualityMetricsCalculator.calculate_rolling_pass_rate(history, window_size=50) == 50.0

    def test_empty_history_raises_value_error(self):
        """Test empty history raises ValueError."""
        with pytest.raises(ValueError, match="test_history cannot be empty"):
            QualityMetricsCalculator.calculate_rolling_pass_rate([])

    def test_invalid_window_size_raises_value_error(self):
        """Test window_size < 1 raises ValueError."""
        with pytest.raises(ValueError, match="window_size must be >= 1"):
            QualityMetricsCalculator.calculate_rolling_pass_rate([True], window_size=0)

    @pytest.mark.parametrize("invalid_ws_type", [True, 2.5, "3", [2]])
    def test_invalid_window_size_type_raises_type_error(self, invalid_ws_type):
        """Test non-integer window_size raises TypeError."""
        with pytest.raises(TypeError, match="window_size must be an integer"):
            QualityMetricsCalculator.calculate_rolling_pass_rate([True], window_size=invalid_ws_type)


    def test_non_list_history_raises_type_error(self):
        """Test non-list history raises TypeError."""
        with pytest.raises(TypeError, match="test_history must be a list"):
            QualityMetricsCalculator.calculate_rolling_pass_rate((True, False))

    def test_non_boolean_items_raise_type_error(self):
        """Test items that are not bool raise TypeError."""
        with pytest.raises(TypeError, match="must be a bool"):
            QualityMetricsCalculator.calculate_rolling_pass_rate([True, 1, False])


class TestShannonEntropy:
    """Test suite for calculate_shannon_entropy."""

    def test_degenerate_single_event_is_zero(self):
        """Test deterministic outcome [1.0] has 0 bits of entropy."""
        assert QualityMetricsCalculator.calculate_shannon_entropy([1.0]) == 0.0

    def test_uniform_binary_distribution_is_one_bit(self):
        """Test fair coin [0.5, 0.5] has exactly 1.0 bit of entropy."""
        assert QualityMetricsCalculator.calculate_shannon_entropy([0.5, 0.5]) == 1.0

    def test_zero_probabilities_safely_ignored(self):
        """Test 0.0 entries do not cause log2(0) domain error."""
        entropy = QualityMetricsCalculator.calculate_shannon_entropy([0.5, 0.0, 0.5])
        assert entropy == 1.0

    def test_unnormalized_probabilities_raise_value_error(self):
        """Test probabilities not summing to 1.0 raise ValueError."""
        with pytest.raises(ValueError, match="Probabilities must sum to 1.0"):
            QualityMetricsCalculator.calculate_shannon_entropy([0.3, 0.3])

    def test_empty_list_raises_value_error(self):
        """Test empty list raises ValueError."""
        with pytest.raises(ValueError, match="probabilities list cannot be empty"):
            QualityMetricsCalculator.calculate_shannon_entropy([])

    def test_non_list_probabilities_raises_type_error(self):
        """Test non-list input raises TypeError."""
        with pytest.raises(TypeError, match="probabilities must be a list"):
            QualityMetricsCalculator.calculate_shannon_entropy((0.5, 0.5))

    @pytest.mark.parametrize("invalid_prob_type", [True, "0.5", None])
    def test_invalid_probability_type_in_list_raises_type_error(self, invalid_prob_type):
        """Test non-numeric element in list raises TypeError."""
        with pytest.raises(TypeError, match="must be float/int"):
            QualityMetricsCalculator.calculate_shannon_entropy([invalid_prob_type, 0.5])

    @pytest.mark.parametrize("invalid_prob", [-0.1, 1.5, float("nan")])
    def test_out_of_range_probability_raises_value_error(self, invalid_prob):
        """Test out of range probabilities raise ValueError."""
        with pytest.raises(ValueError):
            QualityMetricsCalculator.calculate_shannon_entropy([invalid_prob, 1.0])

