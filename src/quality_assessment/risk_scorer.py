"""Quality Risk Scoring and Severity Classification Module.

Computes multi-factor risk scores by combining code churn, test coverage deficit,
static analysis code smells, and cyclomatic complexity hotspots.
"""

from enum import Enum
import math
from typing import Dict, Optional, Union


class RiskTier(str, Enum):
    """Classification tiers for calculated risk scores."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class QualityRiskScorer:
    """Calculates normalized multi-factor software risk scores in range [0.0, 100.0]."""

    # Default weights for composite risk scoring (must sum to 1.0)
    DEFAULT_WEIGHTS = {
        "coverage_deficit": 0.35,
        "complexity_penalty": 0.25,
        "churn_factor": 0.20,
        "smell_density": 0.20,
    }

    def __init__(self, weights: Optional[Dict[str, float]] = None):
        """Initialize risk scorer with custom or default weights.

        Args:
            weights: Optional dictionary mapping component names to weights in [0.0, 1.0].
                Must include keys: 'coverage_deficit', 'complexity_penalty', 'churn_factor', 'smell_density'.

        Raises:
            TypeError: If weights is not a dict or values are non-numeric.
            ValueError: If weights are negative or do not sum to 1.0 (tolerance 1e-4), or keys are missing.
        """
        if weights is None:
            self.weights = dict(self.DEFAULT_WEIGHTS)
        else:
            if not isinstance(weights, dict):
                raise TypeError("weights must be a dictionary")
            required_keys = set(self.DEFAULT_WEIGHTS.keys())
            if set(weights.keys()) != required_keys:
                raise ValueError(f"weights must contain exactly keys {sorted(list(required_keys))}")

            total_w = 0.0
            for k, v in weights.items():
                if isinstance(v, bool) or not isinstance(v, (int, float)):
                    raise TypeError(f"Weight for '{k}' must be numeric, got {type(v).__name__}")
                if v < 0.0:
                    raise ValueError(f"Weight for '{k}' cannot be negative, got {v}")
                total_w += float(v)

            if abs(total_w - 1.0) > 1e-4:
                raise ValueError(f"Weights must sum to 1.0 (tolerance 1e-4), got sum={total_w}")

            self.weights = {k: float(v) for k, v in weights.items()}

    def calculate_coverage_deficit_penalty(self, coverage_pct: Union[int, float]) -> float:
        """Compute sub-penalty for test coverage deficit.

        Formula: 100.0 - coverage_pct (clamped to [0.0, 100.0])

        Args:
            coverage_pct: Code coverage percentage in [0.0, 100.0].

        Returns:
            float: Penalty score between 0.0 (100% coverage) and 100.0 (0% coverage).

        Raises:
            TypeError: If coverage_pct is boolean or not numeric.
            ValueError: If coverage_pct < 0.0 or > 100.0.
        """
        if isinstance(coverage_pct, bool) or not isinstance(coverage_pct, (int, float)):
            raise TypeError("coverage_pct must be numeric")
        c = float(coverage_pct)
        if c < 0.0 or c > 100.0:
            raise ValueError(f"coverage_pct must be in [0.0, 100.0], got {c}")
        return 100.0 - c

    def calculate_complexity_penalty(self, cyclomatic_complexity: Union[int, float]) -> float:
        """Compute non-linear saturation penalty for McCabe cyclomatic complexity.

        Complexity <= 10: Linear scaling from 0 to 20
        Complexity 11-25: Accelerated scaling from 20 to 60
        Complexity > 25: Saturates towards 100 asymptotically

        Args:
            cyclomatic_complexity: Cyclomatic complexity score (>= 1.0).

        Returns:
            float: Penalty score in range [0.0, 100.0], rounded to 2 decimal places.

        Raises:
            TypeError: If complexity is boolean or non-numeric.
            ValueError: If complexity < 1.0.
        """
        if isinstance(cyclomatic_complexity, bool) or not isinstance(cyclomatic_complexity, (int, float)):
            raise TypeError("cyclomatic_complexity must be numeric")
        cc = float(cyclomatic_complexity)
        if cc < 1.0:
            raise ValueError(f"cyclomatic_complexity must be >= 1.0, got {cc}")

        if cc <= 10.0:
            # Linear [1, 10] -> [0.0, 20.0]
            penalty = (cc - 1.0) * (20.0 / 9.0)
        elif cc <= 25.0:
            # [10, 25] -> [20.0, 60.0]
            penalty = 20.0 + (cc - 10.0) * (40.0 / 15.0)
        else:
            # Asymptotic approach to 100: 60 + 40 * (1 - exp(-0.05 * (cc - 25)))
            penalty = 60.0 + 40.0 * (1.0 - math.exp(-0.05 * (cc - 25.0)))

        return round(min(100.0, max(0.0, penalty)), 2)

    def calculate_composite_risk(
        self,
        coverage_pct: Union[int, float],
        cyclomatic_complexity: Union[int, float],
        churn_lines: int,
        smell_count: int,
        total_loc: int,
    ) -> Dict[str, Union[float, str]]:
        """Compute composite risk score and classify into severity tier.

        Args:
            coverage_pct: Test coverage in [0.0, 100.0].
            cyclomatic_complexity: Cyclomatic complexity (>= 1.0).
            churn_lines: Number of modified lines in recent changes (>= 0).
            smell_count: Number of static analysis code smells (>= 0).
            total_loc: Total lines of code in module (>= 1).

        Returns:
            Dict[str, Union[float, str]]:
                - 'risk_score': Composite risk in [0.0, 100.0] rounded to 2 decimals.
                - 'tier': One of 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'.
                - 'breakdown': Dictionary of individual sub-penalties.

        Raises:
            TypeError: If argument types are invalid.
            ValueError: If input values violate domain bounds.

        Tier Boundaries:
            - risk_score < 25.0 -> LOW
            - 25.0 <= risk_score < 50.0 -> MEDIUM
            - 50.0 <= risk_score < 75.0 -> HIGH
            - risk_score >= 75.0 -> CRITICAL
        """
        if isinstance(churn_lines, bool) or not isinstance(churn_lines, int) or churn_lines < 0:
            raise ValueError(f"churn_lines must be an integer >= 0, got {churn_lines}")
        if isinstance(smell_count, bool) or not isinstance(smell_count, int) or smell_count < 0:
            raise ValueError(f"smell_count must be an integer >= 0, got {smell_count}")
        if isinstance(total_loc, bool) or not isinstance(total_loc, int) or total_loc < 1:
            raise ValueError(f"total_loc must be an integer >= 1, got {total_loc}")

        cov_pen = self.calculate_coverage_deficit_penalty(coverage_pct)
        comp_pen = self.calculate_complexity_penalty(cyclomatic_complexity)

        # Churn factor: churn relative to total LOC, capped at 100% churn -> 100 penalty
        churn_ratio = min(1.0, churn_lines / total_loc)
        churn_pen = churn_ratio * 100.0

        # Smell density penalty: smells per 100 LOC, saturated at 10 smells / 100 LOC -> 100 penalty
        smell_density = (smell_count / total_loc) * 100.0
        smell_pen = min(100.0, smell_density * 10.0)

        composite = (
            self.weights["coverage_deficit"] * cov_pen
            + self.weights["complexity_penalty"] * comp_pen
            + self.weights["churn_factor"] * churn_pen
            + self.weights["smell_density"] * smell_pen
        )
        composite = round(min(100.0, max(0.0, composite)), 2)

        if composite < 25.0:
            tier = RiskTier.LOW.value
        elif composite < 50.0:
            tier = RiskTier.MEDIUM.value
        elif composite < 75.0:
            tier = RiskTier.HIGH.value
        else:
            tier = RiskTier.CRITICAL.value

        return {
            "risk_score": composite,
            "tier": tier,
            "breakdown": {
                "coverage_penalty": round(cov_pen, 2),
                "complexity_penalty": round(comp_pen, 2),
                "churn_penalty": round(churn_pen, 2),
                "smell_penalty": round(smell_pen, 2),
            },
        }
