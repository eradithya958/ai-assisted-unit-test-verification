"""Hybrid Test Suite for QualityRiskScorer (AI-Generated Base + Human Review).

Strengthened with multi-bracket S-curve verification, exact tier boundaries,
weight normalization checks, and sub-penalty breakdown assertions.
"""

import pytest
from quality_assessment.risk_scorer import QualityRiskScorer, RiskTier


class TestQualityRiskScorerHybrid:
    """Hybrid test suite for QualityRiskScorer."""

    def test_default_init(self):
        """Test default weights initialization."""
        scorer = QualityRiskScorer()
        assert scorer.weights["coverage_deficit"] == 0.35
        assert scorer.weights["complexity_penalty"] == 0.25
        assert scorer.weights["churn_factor"] == 0.20
        assert scorer.weights["smell_density"] == 0.20

    def test_custom_weights_and_validation(self):
        """Human Added: Test custom weights and invalid sums."""
        custom = {
            "coverage_deficit": 0.4,
            "complexity_penalty": 0.3,
            "churn_factor": 0.2,
            "smell_density": 0.1,
        }
        scorer = QualityRiskScorer(weights=custom)
        assert scorer.weights["coverage_deficit"] == 0.4

        with pytest.raises(ValueError, match="Weights must sum to 1.0"):
            QualityRiskScorer(weights={"coverage_deficit": 0.5, "complexity_penalty": 0.2, "churn_factor": 0.2, "smell_density": 0.3})

    def test_coverage_deficit_penalty(self):
        """Test coverage deficit penalty calculation."""
        scorer = QualityRiskScorer()
        assert scorer.calculate_coverage_deficit_penalty(100.0) == 0.0
        assert scorer.calculate_coverage_deficit_penalty(0.0) == 100.0
        assert scorer.calculate_coverage_deficit_penalty(75.0) == 25.0

    def test_complexity_penalty_multi_bracket_curves(self):
        """Human Added: Test all 3 brackets of complexity penalty S-curve."""
        scorer = QualityRiskScorer()
        assert scorer.calculate_complexity_penalty(1.0) == 0.0
        assert scorer.calculate_complexity_penalty(10.0) == 20.0
        assert scorer.calculate_complexity_penalty(15.0) == 33.33
        assert scorer.calculate_complexity_penalty(25.0) == 60.0
        pen_50 = scorer.calculate_complexity_penalty(50.0)
        assert 88.0 <= pen_50 <= 95.0

    def test_composite_risk_exact_low_tier(self):
        """Test composite risk score generation and LOW tier."""
        scorer = QualityRiskScorer()
        res = scorer.calculate_composite_risk(
            coverage_pct=90.0,
            cyclomatic_complexity=2.0,
            churn_lines=5,
            smell_count=0,
            total_loc=200,
        )
        assert res["tier"] == RiskTier.LOW.value
        assert res["risk_score"] < 25.0
        assert res["breakdown"]["coverage_penalty"] == 10.0

    def test_composite_risk_medium_and_critical_tiers(self):
        """Human Added: Verify MEDIUM and CRITICAL tier boundary classifications."""
        scorer = QualityRiskScorer()
        # Medium tier
        res_med = scorer.calculate_composite_risk(60.0, 12.0, 50, 2, 200)
        assert res_med["tier"] == RiskTier.MEDIUM.value
        assert 25.0 <= res_med["risk_score"] < 50.0

        # Critical tier
        res_crit = scorer.calculate_composite_risk(0.0, 40.0, 200, 30, 200)
        assert res_crit["tier"] == RiskTier.CRITICAL.value
        assert res_crit["risk_score"] >= 75.0

    def test_composite_risk_invalid_churn(self):
        """Test negative churn lines raises ValueError."""
        scorer = QualityRiskScorer()
        with pytest.raises(ValueError, match="churn_lines must be an integer >= 0"):
            scorer.calculate_composite_risk(80.0, 2.0, -10, 0, 100)
