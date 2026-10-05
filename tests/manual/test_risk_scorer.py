"""Manual Unit Test Suite for QualityRiskScorer.

Tests non-linear S-curves, weight normalization, risk tier thresholds,
boundary conditions, and input validation.
"""

import pytest

from quality_assessment.risk_scorer import QualityRiskScorer, RiskTier


class TestRiskScorerInitialization:
    """Test suite for QualityRiskScorer constructor."""

    def test_default_weights(self):
        """Test default weights initialization."""
        scorer = QualityRiskScorer()
        assert scorer.weights["coverage_deficit"] == 0.35
        assert scorer.weights["complexity_penalty"] == 0.25
        assert scorer.weights["churn_factor"] == 0.20
        assert scorer.weights["smell_density"] == 0.20

    def test_valid_custom_weights(self):
        """Test custom weights that properly sum to 1.0."""
        custom = {
            "coverage_deficit": 0.5,
            "complexity_penalty": 0.2,
            "churn_factor": 0.2,
            "smell_density": 0.1,
        }
        scorer = QualityRiskScorer(weights=custom)
        assert scorer.weights["coverage_deficit"] == 0.5

    @pytest.mark.parametrize("invalid_weight_val", [True, False, "0.25", None, [0.25]])
    def test_non_numeric_weight_value_raises_type_error(self, invalid_weight_val):
        """Test non-numeric weight values raise TypeError."""
        invalid = {
            "coverage_deficit": invalid_weight_val,
            "complexity_penalty": 0.25,
            "churn_factor": 0.25,
            "smell_density": 0.25,
        }
        with pytest.raises(TypeError, match="must be numeric"):
            QualityRiskScorer(weights=invalid)

    def test_weights_not_summing_to_one_raises_value_error(self):
        """Test weights summing to != 1.0 raise ValueError."""
        invalid = {
            "coverage_deficit": 0.5,
            "complexity_penalty": 0.2,
            "churn_factor": 0.2,
            "smell_density": 0.2,  # sum = 1.1
        }
        with pytest.raises(ValueError, match="Weights must sum to 1.0"):
            QualityRiskScorer(weights=invalid)

    def test_missing_weight_key_raises_value_error(self):
        """Test missing key in custom weights raises ValueError."""
        invalid = {"coverage_deficit": 0.5, "complexity_penalty": 0.5}
        with pytest.raises(ValueError, match="weights must contain exactly keys"):
            QualityRiskScorer(weights=invalid)

    def test_negative_weight_raises_value_error(self):
        """Test negative weight raises ValueError."""
        invalid = {
            "coverage_deficit": -0.2,
            "complexity_penalty": 0.6,
            "churn_factor": 0.3,
            "smell_density": 0.3,
        }
        with pytest.raises(ValueError, match="cannot be negative"):
            QualityRiskScorer(weights=invalid)

    def test_non_dict_weights_raises_type_error(self):
        """Test non-dict weights raise TypeError."""
        with pytest.raises(TypeError, match="weights must be a dictionary"):
            QualityRiskScorer(weights=[0.25, 0.25, 0.25, 0.25])



class TestCoverageDeficitPenalty:
    """Test suite for calculate_coverage_deficit_penalty."""

    def test_full_coverage_zero_penalty(self):
        """Test 100% coverage results in 0 penalty."""
        scorer = QualityRiskScorer()
        assert scorer.calculate_coverage_deficit_penalty(100.0) == 0.0

    def test_zero_coverage_max_penalty(self):
        """Test 0% coverage results in 100 penalty."""
        scorer = QualityRiskScorer()
        assert scorer.calculate_coverage_deficit_penalty(0.0) == 100.0

    def test_intermediate_coverage(self):
        """Test 85% coverage results in 15 penalty."""
        scorer = QualityRiskScorer()
        assert scorer.calculate_coverage_deficit_penalty(85.0) == 15.0

    @pytest.mark.parametrize("invalid_cov", [-0.1, 100.1, 150])
    def test_out_of_bounds_coverage_raises_value_error(self, invalid_cov):
        """Test coverage outside [0.0, 100.0] raises ValueError."""
        scorer = QualityRiskScorer()
        with pytest.raises(ValueError):
            scorer.calculate_coverage_deficit_penalty(invalid_cov)

    @pytest.mark.parametrize("invalid_type", [True, "80", None])
    def test_invalid_type_raises_type_error(self, invalid_type):
        """Test non-numeric types raise TypeError."""
        scorer = QualityRiskScorer()
        with pytest.raises(TypeError):
            scorer.calculate_coverage_deficit_penalty(invalid_type)


class TestComplexityPenalty:
    """Test suite for calculate_complexity_penalty."""

    def test_minimum_complexity_one(self):
        """Test cc=1.0 yields 0.0 penalty."""
        scorer = QualityRiskScorer()
        assert scorer.calculate_complexity_penalty(1.0) == 0.0

    def test_low_bracket_linear(self):
        """Test cc=10.0 yields 20.0 penalty."""
        scorer = QualityRiskScorer()
        assert scorer.calculate_complexity_penalty(10.0) == 20.0

    def test_intermediate_bracket_linear(self):
        """Test cc=15.0 in medium bracket [10, 25] yields 33.33 penalty."""
        scorer = QualityRiskScorer()
        # 20.0 + (15.0 - 10.0) * (40.0 / 15.0) = 20.0 + 13.333 = 33.33
        assert scorer.calculate_complexity_penalty(15.0) == 33.33

    def test_medium_bracket_linear(self):
        """Test cc=25.0 yields 60.0 penalty."""
        scorer = QualityRiskScorer()
        assert scorer.calculate_complexity_penalty(25.0) == 60.0


    def test_high_bracket_asymptotic_saturation(self):
        """Test cc=50 yields penalty approaching 100."""
        scorer = QualityRiskScorer()
        pen = scorer.calculate_complexity_penalty(50.0)
        assert 88.0 <= pen <= 95.0

    def test_extreme_complexity_clamped_at_100(self):
        """Test cc=1000 saturates at 100.0."""
        scorer = QualityRiskScorer()
        assert scorer.calculate_complexity_penalty(1000.0) == 100.0

    def test_invalid_complexity_less_than_one(self):
        """Test cc < 1.0 raises ValueError."""
        scorer = QualityRiskScorer()
        with pytest.raises(ValueError, match="cyclomatic_complexity must be >= 1.0"):
            scorer.calculate_complexity_penalty(0.9)

    @pytest.mark.parametrize("invalid_cc_type", [True, False, "10", None, [5]])
    def test_invalid_complexity_type_raises_type_error(self, invalid_cc_type):
        """Test non-numeric complexity raises TypeError."""
        scorer = QualityRiskScorer()
        with pytest.raises(TypeError, match="cyclomatic_complexity must be numeric"):
            scorer.calculate_complexity_penalty(invalid_cc_type)



class TestCompositeRisk:
    """Test suite for calculate_composite_risk and Tier Classification."""

    def test_low_risk_tier(self):
        """Test high quality module gets LOW tier."""
        scorer = QualityRiskScorer()
        # 95% coverage (pen=5), cc=2 (pen=2.22), churn=5/500 (1%), smells=0
        res = scorer.calculate_composite_risk(
            coverage_pct=95.0,
            cyclomatic_complexity=2.0,
            churn_lines=5,
            smell_count=0,
            total_loc=500,
        )
        assert res["tier"] == RiskTier.LOW.value
        assert res["risk_score"] < 25.0

    def test_medium_risk_tier(self):
        """Test moderately degraded module gets MEDIUM tier."""
        scorer = QualityRiskScorer()
        # coverage=60% (pen=40 -> 14.0), cc=12 (pen=25.33 -> 6.33), churn=50/200 (25% -> 5.0), smells=2/200 (10 pen -> 2.0)
        # total composite = 27.33 -> MEDIUM
        res = scorer.calculate_composite_risk(
            coverage_pct=60.0,
            cyclomatic_complexity=12.0,
            churn_lines=50,
            smell_count=2,
            total_loc=200,
        )
        assert res["tier"] == RiskTier.MEDIUM.value
        assert 25.0 <= res["risk_score"] < 50.0


    def test_high_risk_tier(self):
        """Test degraded module gets HIGH tier."""
        scorer = QualityRiskScorer()
        # coverage=40% (pen=60), cc=20 (pen=46.67), churn=100/200 (50%), smells=8/200 (40 pen)
        res = scorer.calculate_composite_risk(
            coverage_pct=40.0,
            cyclomatic_complexity=20.0,
            churn_lines=100,
            smell_count=8,
            total_loc=200,
        )
        assert res["tier"] == RiskTier.HIGH.value
        assert 50.0 <= res["risk_score"] < 75.0

    def test_critical_risk_tier(self):
        """Test severe defect module gets CRITICAL tier."""
        scorer = QualityRiskScorer()
        # 0% coverage (pen=100), cc=40 (pen>80), churn=200/200 (100%), smells=30/200 (100%)
        res = scorer.calculate_composite_risk(
            coverage_pct=0.0,
            cyclomatic_complexity=40.0,
            churn_lines=200,
            smell_count=30,
            total_loc=200,
        )
        assert res["tier"] == RiskTier.CRITICAL.value
        assert res["risk_score"] >= 75.0

    def test_churn_lines_exceeding_total_loc_capped_at_one(self):
        """Test churn_lines > total_loc is safely capped at 100% penalty."""
        scorer = QualityRiskScorer()
        res = scorer.calculate_composite_risk(
            coverage_pct=100.0,
            cyclomatic_complexity=1.0,
            churn_lines=1000,
            smell_count=0,
            total_loc=100,
        )
        assert res["breakdown"]["churn_penalty"] == 100.0

    @pytest.mark.parametrize(
        "kwargs, err_match",
        [
            ({"churn_lines": -1, "smell_count": 0, "total_loc": 100}, "churn_lines must be an integer >= 0"),
            ({"churn_lines": 0, "smell_count": -5, "total_loc": 100}, "smell_count must be an integer >= 0"),
            ({"churn_lines": 0, "smell_count": 0, "total_loc": 0}, "total_loc must be an integer >= 1"),
        ],
    )
    def test_invalid_counts_raise_value_error(self, kwargs, err_match):
        """Test invalid churn, smell, and loc counts raise ValueError."""
        scorer = QualityRiskScorer()
        base = {
            "coverage_pct": 80.0,
            "cyclomatic_complexity": 2.0,
            "churn_lines": 10,
            "smell_count": 0,
            "total_loc": 100,
        }
        base.update(kwargs)
        with pytest.raises(ValueError, match=err_match):
            scorer.calculate_composite_risk(**base)
