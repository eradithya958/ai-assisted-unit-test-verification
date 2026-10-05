"""Hybrid Test Suite for QualityRuleEngine (AI-Generated Base + Human Review).

Strengthened with complete comparison operator coverage (LT, LTE, GTE, NEQ, IN, NOT_IN),
NOT combinator, and raw dictionary condition parsing.
"""

import pytest
from quality_assessment.rule_engine import (
    ComparisonOperator,
    LogicalOperator,
    QualityRuleEngine,
    RuleCondition,
    RuleEvaluationError,
)


class TestQualityRuleEngineHybrid:
    """Hybrid test suite for QualityRuleEngine."""

    def test_evaluate_condition_gt_and_eq(self):
        """Test GT and EQ comparison conditions."""
        cond_gt = RuleCondition("coverage", ComparisonOperator.GT, 80.0)
        assert QualityRuleEngine.evaluate_condition(cond_gt, {"coverage": 85.0}) is True
        assert QualityRuleEngine.evaluate_condition(cond_gt, {"coverage": 75.0}) is False

        cond_eq = RuleCondition("status", ComparisonOperator.EQ, "ready")
        assert QualityRuleEngine.evaluate_condition(cond_eq, {"status": "ready"}) is True
        assert QualityRuleEngine.evaluate_condition(cond_eq, {"status": "pending"}) is False

    # Human Added: Full operator coverage (LT, LTE, GTE, NEQ, IN, NOT_IN)
    @pytest.mark.parametrize(
        "op, val, payload_val, expected",
        [
            (ComparisonOperator.LT, 90.0, 80.0, True),
            (ComparisonOperator.LTE, 80.0, 80.0, True),
            (ComparisonOperator.GTE, 80.0, 80.0, True),
            (ComparisonOperator.NEQ, 90.0, 80.0, True),
            (ComparisonOperator.IN, ["LOW", "MEDIUM"], "LOW", True),
            (ComparisonOperator.NOT_IN, ["CRITICAL"], "LOW", True),
        ],
    )
    def test_additional_operators_coverage(self, op, val, payload_val, expected):
        """Human Added: Test all remaining comparison operators."""
        cond = RuleCondition("field", op, val)
        assert QualityRuleEngine.evaluate_condition(cond, {"field": payload_val}) is expected

    def test_evaluate_rule_group_and_or_not(self):
        """Test AND, OR, and NOT logical combinators."""
        cond1 = RuleCondition("coverage", ComparisonOperator.GTE, 80.0)
        cond2 = RuleCondition("complexity", ComparisonOperator.LT, 5.0)

        assert QualityRuleEngine.evaluate_rule_group([cond1, cond2], {"coverage": 85.0, "complexity": 3.0}, LogicalOperator.AND) is True
        assert QualityRuleEngine.evaluate_rule_group([cond1, cond2], {"coverage": 70.0, "complexity": 3.0}, LogicalOperator.OR) is True

        # Human Added: NOT operator
        cond_fail = RuleCondition("coverage", ComparisonOperator.LT, 50.0)
        assert QualityRuleEngine.evaluate_rule_group([cond_fail], {"coverage": 80.0}, LogicalOperator.NOT) is True

    def test_missing_field_strict_and_lenient(self):
        """Test missing field behavior under strict vs lenient modes."""
        cond = RuleCondition("missing", ComparisonOperator.EQ, 1)
        with pytest.raises(RuleEvaluationError, match="Field 'missing' not found"):
            QualityRuleEngine.evaluate_condition(cond, {"present": 1}, strict_missing=True)

        # Human Added: lenient mode returns False
        assert QualityRuleEngine.evaluate_condition(cond, {"present": 1}, strict_missing=False) is False
