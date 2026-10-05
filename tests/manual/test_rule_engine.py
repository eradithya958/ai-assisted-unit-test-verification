"""Manual Unit Test Suite for QualityRuleEngine.

Tests predicate comparisons (gt, gte, lt, lte, eq, neq, in, not_in),
logical combinators (AND, OR, NOT), strict vs lenient missing-key policies,
and type mismatch error propagation.
"""

import pytest

from quality_assessment.rule_engine import (
    ComparisonOperator,
    LogicalOperator,
    QualityRuleEngine,
    RuleCondition,
    RuleEvaluationError,
)


class TestEvaluateCondition:
    """Test suite for QualityRuleEngine.evaluate_condition."""

    @pytest.mark.parametrize(
        "op, val, expected_res",
        [
            (ComparisonOperator.EQ, 80.0, True),
            (ComparisonOperator.EQ, 90.0, False),
            (ComparisonOperator.NEQ, 90.0, True),
            (ComparisonOperator.NEQ, 80.0, False),
            (ComparisonOperator.GT, 75.0, True),
            (ComparisonOperator.GT, 80.0, False),
            (ComparisonOperator.GTE, 80.0, True),
            (ComparisonOperator.GTE, 85.0, False),
            (ComparisonOperator.LT, 90.0, True),
            (ComparisonOperator.LT, 80.0, False),
            (ComparisonOperator.LTE, 80.0, True),
            (ComparisonOperator.LTE, 70.0, False),
        ],
    )
    def test_numeric_comparison_operators(self, op, val, expected_res):
        """Test numeric comparison predicates."""
        cond = RuleCondition(field_name="coverage", operator=op, expected_value=val)
        payload = {"coverage": 80.0}
        assert QualityRuleEngine.evaluate_condition(cond, payload) is expected_res

    def test_membership_in_and_not_in(self):
        """Test 'in' and 'not_in' membership predicates with collections."""
        cond_in = RuleCondition(field_name="tier", operator=ComparisonOperator.IN, expected_value=["LOW", "MEDIUM"])
        cond_not_in = RuleCondition(field_name="tier", operator=ComparisonOperator.NOT_IN, expected_value=["CRITICAL"])

        assert QualityRuleEngine.evaluate_condition(cond_in, {"tier": "LOW"}) is True
        assert QualityRuleEngine.evaluate_condition(cond_in, {"tier": "HIGH"}) is False
        assert QualityRuleEngine.evaluate_condition(cond_not_in, {"tier": "LOW"}) is True
        assert QualityRuleEngine.evaluate_condition(cond_not_in, {"tier": "CRITICAL"}) is False

    def test_non_iterable_expected_for_in_raises_rule_evaluation_error(self):
        """Test non-iterable expected_value for IN operator raises RuleEvaluationError."""
        cond = RuleCondition(field_name="tier", operator=ComparisonOperator.IN, expected_value=123)
        with pytest.raises(RuleEvaluationError, match="must be iterable"):
            QualityRuleEngine.evaluate_condition(cond, {"tier": "LOW"})

    def test_non_iterable_expected_for_not_in_raises_rule_evaluation_error(self):
        """Test non-iterable expected_value for NOT_IN operator raises RuleEvaluationError."""
        cond = RuleCondition(field_name="tier", operator=ComparisonOperator.NOT_IN, expected_value=123)
        with pytest.raises(RuleEvaluationError, match="must be iterable"):
            QualityRuleEngine.evaluate_condition(cond, {"tier": "LOW"})

    def test_unsupported_comparison_operator_raises_rule_evaluation_error(self):
        """Test unhandled comparison operator enum raises RuleEvaluationError."""
        cond = RuleCondition(field_name="tier", operator="unknown_op", expected_value="LOW")
        with pytest.raises(RuleEvaluationError, match="Unsupported comparison operator"):
            QualityRuleEngine.evaluate_condition(cond, {"tier": "LOW"})

    def test_strict_missing_field_raises_error(self):
        """Test missing field with strict_missing=True raises RuleEvaluationError."""
        cond = RuleCondition(field_name="missing_metric", operator=ComparisonOperator.EQ, expected_value=10)
        with pytest.raises(RuleEvaluationError, match="Field 'missing_metric' not found"):
            QualityRuleEngine.evaluate_condition(cond, {"coverage": 80.0}, strict_missing=True)

    def test_lenient_missing_field_returns_false(self):
        """Test missing field with strict_missing=False returns False."""
        cond = RuleCondition(field_name="missing_metric", operator=ComparisonOperator.EQ, expected_value=10)
        assert QualityRuleEngine.evaluate_condition(cond, {"coverage": 80.0}, strict_missing=False) is False

    def test_incompatible_type_comparison_raises_rule_evaluation_error(self):
        """Test unorderable types (e.g. string > int) raise RuleEvaluationError."""
        cond = RuleCondition(field_name="name", operator=ComparisonOperator.GT, expected_value=42)
        with pytest.raises(RuleEvaluationError, match="Comparison error"):
            QualityRuleEngine.evaluate_condition(cond, {"name": "module_a"})

    def test_invalid_argument_types_raise_type_error(self):
        """Test non-RuleCondition or non-dict payload raises TypeError."""
        cond = RuleCondition(field_name="coverage", operator=ComparisonOperator.EQ, expected_value=80.0)
        with pytest.raises(TypeError):
            QualityRuleEngine.evaluate_condition("not_a_condition", {"coverage": 80.0})
        with pytest.raises(TypeError):
            QualityRuleEngine.evaluate_condition(cond, ["not_a_dict"])


class TestEvaluateRuleGroup:
    """Test suite for QualityRuleEngine.evaluate_rule_group."""

    def test_non_list_conditions_raises_type_error(self):
        """Test passing non-list to evaluate_rule_group raises TypeError."""
        with pytest.raises(TypeError, match="conditions must be a list"):
            QualityRuleEngine.evaluate_rule_group("not_a_list", {"coverage": 80.0})

    def test_invalid_condition_element_type_raises_type_error(self):
        """Test element in conditions that is not RuleCondition or dict raises TypeError."""
        with pytest.raises(TypeError, match="must be RuleCondition or dict"):
            QualityRuleEngine.evaluate_rule_group([123], {"coverage": 80.0})

    def test_unsupported_logical_operator_raises_value_error(self):
        """Test unsupported logical operator string raises ValueError."""
        cond = RuleCondition("coverage", ComparisonOperator.GT, 50.0)
        with pytest.raises(ValueError, match="Unsupported logical operator"):
            QualityRuleEngine.evaluate_rule_group([cond], {"coverage": 80.0}, operator="XOR")


    def test_and_operator_all_true(self):
        """Test AND combinator evaluates to True when all conditions hold."""
        cond1 = RuleCondition("coverage", ComparisonOperator.GTE, 80.0)
        cond2 = RuleCondition("complexity", ComparisonOperator.LTE, 5.0)
        payload = {"coverage": 85.0, "complexity": 3.0}

        assert QualityRuleEngine.evaluate_rule_group([cond1, cond2], payload, operator=LogicalOperator.AND) is True

    def test_and_operator_one_false(self):
        """Test AND combinator evaluates to False when any condition fails."""
        cond1 = RuleCondition("coverage", ComparisonOperator.GTE, 80.0)
        cond2 = RuleCondition("complexity", ComparisonOperator.LTE, 5.0)
        payload = {"coverage": 85.0, "complexity": 10.0}

        assert QualityRuleEngine.evaluate_rule_group([cond1, cond2], payload, operator=LogicalOperator.AND) is False

    def test_or_operator_partial_true(self):
        """Test OR combinator evaluates to True when at least one condition holds."""
        cond1 = RuleCondition("coverage", ComparisonOperator.GTE, 90.0)
        cond2 = RuleCondition("test_count", ComparisonOperator.GT, 10)
        payload = {"coverage": 70.0, "test_count": 15}

        assert QualityRuleEngine.evaluate_rule_group([cond1, cond2], payload, operator=LogicalOperator.OR) is True

    def test_not_operator_single_condition(self):
        """Test NOT combinator inverts the underlying single condition."""
        cond = RuleCondition("coverage", ComparisonOperator.LT, 50.0)
        payload = {"coverage": 80.0}

        # coverage < 50 is False -> NOT False is True
        assert QualityRuleEngine.evaluate_rule_group([cond], payload, operator=LogicalOperator.NOT) is True

    def test_not_operator_with_multiple_conditions_raises_value_error(self):
        """Test NOT combinator with >1 conditions raises ValueError."""
        cond1 = RuleCondition("coverage", ComparisonOperator.LT, 50.0)
        cond2 = RuleCondition("complexity", ComparisonOperator.GT, 10.0)
        with pytest.raises(ValueError, match="LogicalOperator.NOT requires exactly one condition"):
            QualityRuleEngine.evaluate_rule_group([cond1, cond2], {"coverage": 80.0}, operator=LogicalOperator.NOT)

    def test_parse_condition_dict_format(self):
        """Test passing conditions as raw dictionaries instead of RuleCondition objects."""
        raw_conds = [
            {"field_name": "coverage", "operator": "gte", "expected_value": 75.0},
            {"field_name": "status", "operator": "eq", "expected_value": "active"},
        ]
        payload = {"coverage": 80.0, "status": "active"}
        assert QualityRuleEngine.evaluate_rule_group(raw_conds, payload, operator=LogicalOperator.AND) is True

    def test_invalid_condition_dict_format_raises_error(self):
        """Test condition dictionary missing keys raises RuleEvaluationError."""
        bad_conds = [{"field_name": "coverage"}]  # missing operator
        with pytest.raises(RuleEvaluationError, match="Invalid condition dict format"):
            QualityRuleEngine.evaluate_rule_group(bad_conds, {"coverage": 80.0})

    def test_empty_conditions_list_raises_value_error(self):
        """Test empty conditions list raises ValueError."""
        with pytest.raises(ValueError, match="conditions list cannot be empty"):
            QualityRuleEngine.evaluate_rule_group([], {"coverage": 80.0})
