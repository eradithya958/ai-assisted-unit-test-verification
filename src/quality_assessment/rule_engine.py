"""Quality Rule Evaluation Engine.

Provides rule-based policy validation, predicate evaluation with logical combinators
(AND, OR, NOT), and dynamic quality policy verification.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Union


class LogicalOperator(str, Enum):
    """Boolean combinator for rule expressions."""
    AND = "AND"
    OR = "OR"
    NOT = "NOT"


class ComparisonOperator(str, Enum):
    """Supported comparison predicates."""
    GT = "gt"
    GTE = "gte"
    LT = "lt"
    LTE = "lte"
    EQ = "eq"
    NEQ = "neq"
    IN = "in"
    NOT_IN = "not_in"


@dataclass
class RuleCondition:
    """Atomic rule condition comparing a target payload field against an expected value."""
    field_name: str
    operator: ComparisonOperator
    expected_value: Any


class RuleEvaluationError(Exception):
    """Raised when rule evaluation fails due to schema or operational mismatch."""
    pass


class QualityRuleEngine:
    """Evaluates declarative quality criteria against metric dictionaries."""

    @classmethod
    def evaluate_condition(
        cls,
        condition: RuleCondition,
        payload: Dict[str, Any],
        strict_missing: bool = True,
    ) -> bool:
        """Evaluate a single atomic RuleCondition against a payload.

        Args:
            condition: The RuleCondition instance to evaluate.
            payload: Dictionary containing metric/telemetry key-value pairs.
            strict_missing: If True, raises RuleEvaluationError when field_name is missing.
                If False, returns False when field_name is missing.

        Returns:
            bool: Result of the predicate comparison.

        Raises:
            TypeError: If condition is not a RuleCondition or payload is not a dict.
            RuleEvaluationError: If field is missing (under strict_missing=True) or types cannot be compared.
        """
        if not isinstance(condition, RuleCondition):
            raise TypeError(f"condition must be a RuleCondition instance, got {type(condition).__name__}")
        if not isinstance(payload, dict):
            raise TypeError(f"payload must be a dict, got {type(payload).__name__}")

        if condition.field_name not in payload:
            if strict_missing:
                raise RuleEvaluationError(f"Field '{condition.field_name}' not found in payload")
            return False

        actual = payload[condition.field_name]
        expected = condition.expected_value
        op = condition.operator

        try:
            if op == ComparisonOperator.EQ:
                return actual == expected
            elif op == ComparisonOperator.NEQ:
                return actual != expected
            elif op == ComparisonOperator.GT:
                return actual > expected
            elif op == ComparisonOperator.GTE:
                return actual >= expected
            elif op == ComparisonOperator.LT:
                return actual < expected
            elif op == ComparisonOperator.LTE:
                return actual <= expected
            elif op == ComparisonOperator.IN:
                if not hasattr(expected, "__contains__"):
                    raise RuleEvaluationError(f"Expected value for 'in' operator must be iterable, got {type(expected).__name__}")
                return actual in expected
            elif op == ComparisonOperator.NOT_IN:
                if not hasattr(expected, "__contains__"):
                    raise RuleEvaluationError(f"Expected value for 'not_in' operator must be iterable, got {type(expected).__name__}")
                return actual not in expected
            else:
                raise RuleEvaluationError(f"Unsupported comparison operator: {op}")
        except TypeError as err:
            raise RuleEvaluationError(f"Comparison error for field '{condition.field_name}': {err}") from err

    @classmethod
    def evaluate_rule_group(
        cls,
        conditions: List[Union[RuleCondition, Dict[str, Any]]],
        payload: Dict[str, Any],
        operator: LogicalOperator = LogicalOperator.AND,
        strict_missing: bool = True,
    ) -> bool:
        """Evaluate a list of conditions joined by a logical combinator.

        Args:
            conditions: List of RuleCondition instances (or condition dicts).
            payload: Dictionary containing metric key-value pairs.
            operator: Logical operator to combine conditions (AND, OR, NOT).
            strict_missing: Strictness flag forwarded to evaluate_condition.

        Returns:
            bool: Aggregate boolean result of the rule group.

        Raises:
            ValueError: If conditions is empty, or NOT operator is provided with != 1 condition.
            RuleEvaluationError: If evaluation of child condition fails.
        """
        if not isinstance(conditions, list):
            raise TypeError("conditions must be a list")
        if len(conditions) == 0:
            raise ValueError("conditions list cannot be empty")

        parsed_conditions: List[RuleCondition] = []
        for idx, item in enumerate(conditions):
            if isinstance(item, RuleCondition):
                parsed_conditions.append(item)
            elif isinstance(item, dict):
                try:
                    parsed_conditions.append(
                        RuleCondition(
                            field_name=item["field_name"],
                            operator=ComparisonOperator(item["operator"]),
                            expected_value=item["expected_value"],
                        )
                    )
                except (KeyError, ValueError) as err:
                    raise RuleEvaluationError(f"Invalid condition dict format at index {idx}: {err}") from err
            else:
                raise TypeError(f"Condition at index {idx} must be RuleCondition or dict")

        if operator == LogicalOperator.NOT:
            if len(parsed_conditions) != 1:
                raise ValueError("LogicalOperator.NOT requires exactly one condition")
            return not cls.evaluate_condition(parsed_conditions[0], payload, strict_missing=strict_missing)

        results = [
            cls.evaluate_condition(cond, payload, strict_missing=strict_missing)
            for cond in parsed_conditions
        ]

        if operator == LogicalOperator.AND:
            return all(results)
        elif operator == LogicalOperator.OR:
            return any(results)
        else:
            raise ValueError(f"Unsupported logical operator: {operator}")
