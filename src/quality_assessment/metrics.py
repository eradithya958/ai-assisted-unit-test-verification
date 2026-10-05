"""Numeric and Statistical Quality Metrics Module.

Provides mathematical computations for software verification, classification metrics,
uncertainty estimation (Brier score, Shannon entropy), and code complexity densities.
"""

import math
from typing import Dict, List, Optional, Tuple, Union


class QualityMetricsCalculator:
    """Calculates software quality, model evaluation, and verification metrics."""

    @staticmethod
    def calculate_precision_recall_f1(
        true_positives: int,
        false_positives: int,
        false_negatives: int,
        zero_division_value: float = 0.0,
    ) -> Dict[str, float]:
        """Compute Precision, Recall, and F1-score from confusion counts.

        Args:
            true_positives: Number of correctly identified positive instances (>= 0).
            false_positives: Number of negative instances wrongly identified as positive (>= 0).
            false_negatives: Number of positive instances wrongly identified as negative (>= 0).
            zero_division_value: Value to return when denominator is zero (default 0.0).

        Returns:
            Dict[str, float]: Dictionary with keys 'precision', 'recall', 'f1_score',
                each rounded to 4 decimal places.

        Raises:
            TypeError: If counts are not integers or are booleans.
            ValueError: If any count is negative or zero_division_value is not in [0.0, 1.0].

        Preconditions:
            - true_positives >= 0, false_positives >= 0, false_negatives >= 0
            - 0.0 <= zero_division_value <= 1.0

        Edge Cases:
            - When TP + FP == 0, precision defaults to zero_division_value.
            - When TP + FN == 0, recall defaults to zero_division_value.
            - When Precision + Recall == 0, F1 defaults to zero_division_value.
            - When all counts are 0, all metrics return zero_division_value.
        """
        for name, val in [
            ("true_positives", true_positives),
            ("false_positives", false_positives),
            ("false_negatives", false_negatives),
        ]:
            if isinstance(val, bool) or not isinstance(val, int):
                raise TypeError(f"'{name}' must be an integer, got {type(val).__name__}")
            if val < 0:
                raise ValueError(f"'{name}' cannot be negative, got {val}")

        if isinstance(zero_division_value, bool) or not isinstance(zero_division_value, (int, float)):
            raise TypeError("zero_division_value must be a numeric float/int")
        if not (0.0 <= zero_division_value <= 1.0):
            raise ValueError(f"zero_division_value must be in [0.0, 1.0], got {zero_division_value}")

        tp, fp, fn = true_positives, false_positives, false_negatives

        # Precision = TP / (TP + FP)
        prec_denom = tp + fp
        precision = (tp / prec_denom) if prec_denom > 0 else float(zero_division_value)

        # Recall = TP / (TP + FN)
        rec_denom = tp + fn
        recall = (tp / rec_denom) if rec_denom > 0 else float(zero_division_value)

        # F1 = 2 * (Precision * Recall) / (Precision + Recall)
        f1_denom = precision + recall
        if f1_denom > 0:
            f1 = 2.0 * (precision * recall) / f1_denom
        else:
            f1 = float(zero_division_value)

        return {
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1_score": round(f1, 4),
        }

    @staticmethod
    def calculate_brier_score(
        predicted_probabilities: List[float],
        actual_outcomes: List[int],
    ) -> float:
        """Compute the Brier Score for probabilistic prediction calibration.

        Formula: (1 / N) * sum((p_i - y_i)^2)

        Args:
            predicted_probabilities: List of predicted probabilities p_i in [0.0, 1.0].
            actual_outcomes: List of binary outcomes y_i in {0, 1}.

        Returns:
            float: Brier score in range [0.0, 1.0], rounded to 6 decimal places.

        Raises:
            TypeError: If inputs are not lists or contain non-numeric types.
            ValueError: If lists are empty, have mismatched lengths, or contain out-of-range values.

        Edge Cases:
            - Perfect predictions (probabilities equal outcomes) yield 0.0.
            - Total miscalibration (predicting 1 when outcome is 0) yields 1.0.
            - Single-element list is handled correctly.
        """
        if not isinstance(predicted_probabilities, list) or not isinstance(actual_outcomes, list):
            raise TypeError("Both predicted_probabilities and actual_outcomes must be lists")

        if len(predicted_probabilities) == 0:
            raise ValueError("Input lists cannot be empty")

        if len(predicted_probabilities) != len(actual_outcomes):
            raise ValueError(
                f"Length mismatch: {len(predicted_probabilities)} probabilities vs {len(actual_outcomes)} outcomes"
            )

        n = len(predicted_probabilities)
        squared_errors_sum = 0.0

        for idx, (p, y) in enumerate(zip(predicted_probabilities, actual_outcomes)):
            if isinstance(p, bool) or not isinstance(p, (int, float)):
                raise TypeError(f"Probability at index {idx} must be a float/int, got {type(p).__name__}")
            if math.isnan(p) or math.isinf(p) or p < 0.0 or p > 1.0:
                raise ValueError(f"Probability at index {idx} must be in [0.0, 1.0], got {p}")

            if isinstance(y, bool) or not isinstance(y, int):
                raise TypeError(f"Outcome at index {idx} must be an integer (0 or 1), got {type(y).__name__}")
            if y not in (0, 1):
                raise ValueError(f"Outcome at index {idx} must be either 0 or 1, got {y}")

            squared_errors_sum += (p - y) ** 2

        return round(squared_errors_sum / n, 6)

    @staticmethod
    def calculate_cyclomatic_density(
        cyclomatic_complexity: Union[int, float],
        lines_of_code: int,
    ) -> float:
        """Compute cyclomatic density (complexity per 100 lines of code).

        Formula: (cyclomatic_complexity / lines_of_code) * 100.0

        Args:
            cyclomatic_complexity: McCabe cyclomatic complexity (>= 1.0).
            lines_of_code: Total executable or physical lines of code (>= 1).

        Returns:
            float: Density metric rounded to 2 decimal places.

        Raises:
            TypeError: If types are invalid (e.g. booleans or non-numbers).
            ValueError: If complexity < 1.0 or lines_of_code < 1.
        """
        if isinstance(cyclomatic_complexity, bool) or not isinstance(cyclomatic_complexity, (int, float)):
            raise TypeError(f"cyclomatic_complexity must be numeric, got {type(cyclomatic_complexity).__name__}")
        if isinstance(lines_of_code, bool) or not isinstance(lines_of_code, int):
            raise TypeError(f"lines_of_code must be an integer, got {type(lines_of_code).__name__}")

        if cyclomatic_complexity < 1.0:
            raise ValueError(f"cyclomatic_complexity must be >= 1.0, got {cyclomatic_complexity}")
        if lines_of_code < 1:
            raise ValueError(f"lines_of_code must be >= 1, got {lines_of_code}")

        density = (float(cyclomatic_complexity) / float(lines_of_code)) * 100.0
        return round(density, 2)

    @staticmethod
    def calculate_rolling_pass_rate(
        test_history: List[bool],
        window_size: Optional[int] = None,
    ) -> float:
        """Compute pass rate over the most recent execution window.

        Args:
            test_history: List of boolean pass/fail results (True = passed, False = failed).
            window_size: Number of recent runs to include. If None or greater than len(test_history),
                uses all runs in history. Must be >= 1 if provided.

        Returns:
            float: Pass rate percentage [0.0, 100.0] rounded to 2 decimal places.

        Raises:
            TypeError: If test_history is not a list or elements are not booleans.
            ValueError: If test_history is empty or window_size < 1.
        """
        if not isinstance(test_history, list):
            raise TypeError(f"test_history must be a list, got {type(test_history).__name__}")
        if len(test_history) == 0:
            raise ValueError("test_history cannot be empty")

        for idx, item in enumerate(test_history):
            if not isinstance(item, bool):
                raise TypeError(f"Item at index {idx} must be a bool, got {type(item).__name__}")

        if window_size is not None:
            if isinstance(window_size, bool) or not isinstance(window_size, int):
                raise TypeError(f"window_size must be an integer, got {type(window_size).__name__}")
            if window_size < 1:
                raise ValueError(f"window_size must be >= 1, got {window_size}")
            slice_data = test_history[-window_size:]
        else:
            slice_data = test_history

        passed_count = sum(1 for run in slice_data if run is True)
        rate = (passed_count / len(slice_data)) * 100.0
        return round(rate, 2)

    @staticmethod
    def calculate_shannon_entropy(probabilities: List[float]) -> float:
        """Compute the Shannon Entropy in bits for a discrete distribution.

        Formula: -sum(p_i * log2(p_i)) for all p_i > 0

        Args:
            probabilities: List of probabilities summing to 1.0 (tolerance 1e-4).

        Returns:
            float: Shannon entropy in bits, rounded to 4 decimal places (>= 0.0).

        Raises:
            TypeError: If input is not a list or contains non-numeric types.
            ValueError: If list is empty, contains elements outside [0, 1], or does not sum to 1.0.

        Edge Cases:
            - Single event with p=1.0 yields 0.0 bits.
            - Events with p=0.0 are ignored (0 * log2(0) = 0).
            - Equal distribution of 2 elements (0.5, 0.5) yields 1.0 bit.
        """
        if not isinstance(probabilities, list):
            raise TypeError("probabilities must be a list")
        if len(probabilities) == 0:
            raise ValueError("probabilities list cannot be empty")

        total_prob = 0.0
        for idx, p in enumerate(probabilities):
            if isinstance(p, bool) or not isinstance(p, (int, float)):
                raise TypeError(f"Element at index {idx} must be float/int, got {type(p).__name__}")
            if math.isnan(p) or math.isinf(p) or p < 0.0 or p > 1.0:
                raise ValueError(f"Element at index {idx} must be in [0.0, 1.0], got {p}")
            total_prob += p

        if abs(total_prob - 1.0) > 1e-3:
            raise ValueError(f"Probabilities must sum to 1.0 (within 1e-3), got sum={total_prob}")

        entropy = 0.0
        for p in probabilities:
            if p > 0.0:
                entropy -= p * math.log2(p)

        return round(max(0.0, entropy), 4)
