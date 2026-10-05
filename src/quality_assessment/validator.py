"""Input and Schema Validation Module for Software Verification.

Provides validation logic for metrics dictionaries, benchmark datasets,
and quality score payloads with structural and range constraints.
"""

from typing import Any, Dict, List, Optional, Tuple, Union


class ValidationError(Exception):
    """Base exception for all validation errors."""
    pass


class MissingFieldError(ValidationError):
    """Raised when a required schema field is missing."""
    pass


class TypeValidationError(ValidationError):
    """Raised when a field type does not match the schema specification."""
    pass


class RangeValidationError(ValidationError):
    """Raised when a numeric value violates allowed range boundaries."""
    pass


class DatasetValidator:
    """Validator for quality assessment metrics, telemetry, and test payloads.

    Enforces schema compliance, type integrity, and value boundaries for
    verification pipelines.
    """

    @staticmethod
    def validate_metric_payload(
        payload: Dict[str, Any],
        required_keys: Optional[List[str]] = None,
        allow_extra_keys: bool = False,
    ) -> Dict[str, Any]:
        """Validate a single metric payload against structural and typing rules.

        Args:
            payload: Dictionary containing metric key-value pairs.
            required_keys: Optional list of keys that must be present in the payload.
                Defaults to ['lines_of_code', 'coverage', 'complexity', 'test_count'].
            allow_extra_keys: If False, raises ValidationError when unlisted keys are found.

        Returns:
            Dict[str, Any]: The validated and sanitized payload with normalized types.

        Raises:
            ValidationError: If payload is not a dictionary or is empty.
            MissingFieldError: If any required key is absent.
            TypeValidationError: If values do not match expected types.
            RangeValidationError: If numeric values are outside physical/domain bounds.

        Preconditions:
            - payload must be a non-empty dictionary.
            - lines_of_code >= 1 (integer)
            - 0.0 <= coverage <= 100.0 (float or int)
            - complexity >= 1.0 (float or int)
            - test_count >= 0 (integer)

        Edge Cases:
            - float values for integer fields (e.g. lines_of_code=100.0) are rejected if not exact integers.
            - None values for any required field raise TypeValidationError.
            - Extra unrecognized keys rejected if allow_extra_keys is False.
        """
        if not isinstance(payload, dict):
            raise ValidationError(f"Payload must be a dictionary, got {type(payload).__name__}")
        if len(payload) == 0:
            raise ValidationError("Payload dictionary cannot be empty")

        if required_keys is None:
            required_keys = ["lines_of_code", "coverage", "complexity", "test_count"]

        # Check missing keys
        for key in required_keys:
            if key not in payload:
                raise MissingFieldError(f"Missing required metric field: '{key}'")

        # Check unexpected keys
        if not allow_extra_keys:
            extra = set(payload.keys()) - set(required_keys)
            if extra:
                raise ValidationError(f"Unrecognized metric keys found: {sorted(list(extra))}")

        sanitized: Dict[str, Any] = {}

        # Validate lines_of_code
        if "lines_of_code" in payload:
            loc = payload["lines_of_code"]
            if isinstance(loc, bool) or not isinstance(loc, int):
                raise TypeValidationError(f"'lines_of_code' must be an integer, got {type(loc).__name__}")
            if loc < 1:
                raise RangeValidationError(f"'lines_of_code' must be >= 1, got {loc}")
            sanitized["lines_of_code"] = loc

        # Validate coverage
        if "coverage" in payload:
            cov = payload["coverage"]
            if isinstance(cov, bool) or not isinstance(cov, (int, float)):
                raise TypeValidationError(f"'coverage' must be a float or int, got {type(cov).__name__}")
            cov_float = float(cov)
            if cov_float < 0.0 or cov_float > 100.0:
                raise RangeValidationError(f"'coverage' must be between 0.0 and 100.0, got {cov_float}")
            sanitized["coverage"] = cov_float

        # Validate complexity
        if "complexity" in payload:
            comp = payload["complexity"]
            if isinstance(comp, bool) or not isinstance(comp, (int, float)):
                raise TypeValidationError(f"'complexity' must be a float or int, got {type(comp).__name__}")
            comp_float = float(comp)
            if comp_float < 1.0:
                raise RangeValidationError(f"'complexity' must be >= 1.0, got {comp_float}")
            sanitized["complexity"] = comp_float

        # Validate test_count
        if "test_count" in payload:
            tc = payload["test_count"]
            if isinstance(tc, bool) or not isinstance(tc, int):
                raise TypeValidationError(f"'test_count' must be an integer, got {type(tc).__name__}")
            if tc < 0:
                raise RangeValidationError(f"'test_count' must be >= 0, got {tc}")
            sanitized["test_count"] = tc

        # Copy over permitted extra keys
        if allow_extra_keys:
            for k, v in payload.items():
                if k not in sanitized:
                    sanitized[k] = v

        return sanitized

    @staticmethod
    def validate_numeric_bounds(
        value: Union[int, float],
        min_val: Optional[float] = None,
        max_val: Optional[float] = None,
        inclusive_min: bool = True,
        inclusive_max: bool = True,
    ) -> bool:
        """Validate whether a numeric scalar lies within specified boundaries.

        Args:
            value: The numeric value to validate.
            min_val: Optional lower bound.
            max_val: Optional upper bound.
            inclusive_min: Whether the lower bound is inclusive (>=) or strict (>).
            inclusive_max: Whether the upper bound is inclusive (<=) or strict (<).

        Returns:
            bool: True if value satisfies the boundary constraints.

        Raises:
            TypeValidationError: If value or bounds are not numeric (or are boolean).
            ValueError: If min_val > max_val.

        Edge Cases:
            - Passing booleans (e.g. True/False) is rejected as TypeValidationError.
            - If min_val and max_val are None, any numeric value returns True.
        """
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TypeValidationError(f"Value must be a numeric type, got {type(value).__name__}")

        if min_val is not None:
            if isinstance(min_val, bool) or not isinstance(min_val, (int, float)):
                raise TypeValidationError("min_val must be numeric or None")
        if max_val is not None:
            if isinstance(max_val, bool) or not isinstance(max_val, (int, float)):
                raise TypeValidationError("max_val must be numeric or None")

        if min_val is not None and max_val is not None and min_val > max_val:
            raise ValueError(f"Lower bound ({min_val}) cannot exceed upper bound ({max_val})")

        val = float(value)

        if min_val is not None:
            min_f = float(min_val)
            if inclusive_min:
                if val < min_f:
                    return False
            else:
                if val <= min_f:
                    return False

        if max_val is not None:
            max_f = float(max_val)
            if inclusive_max:
                if val > max_f:
                    return False
            else:
                if val >= max_f:
                    return False

        return True
