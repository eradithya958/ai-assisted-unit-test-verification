"""Manual Unit Test Suite for DatasetValidator.

Tests nominal paths, boundary values, invalid data types, range violations,
missing required keys, and custom exception assertions.
"""

import pytest

from quality_assessment.validator import (
    DatasetValidator,
    MissingFieldError,
    RangeValidationError,
    TypeValidationError,
    ValidationError,
)


class TestValidateMetricPayload:
    """Test suite for DatasetValidator.validate_metric_payload."""

    # Nominal Cases
    def test_valid_standard_payload(self):
        """Test with valid nominal payload matching default required keys."""
        payload = {
            "lines_of_code": 150,
            "coverage": 85.5,
            "complexity": 4.2,
            "test_count": 25,
        }
        sanitized = DatasetValidator.validate_metric_payload(payload)
        assert sanitized["lines_of_code"] == 150
        assert sanitized["coverage"] == 85.5
        assert sanitized["complexity"] == 4.2
        assert sanitized["test_count"] == 25

    def test_valid_boundary_values(self):
        """Test minimum and maximum boundary values for all fields."""
        payload = {
            "lines_of_code": 1,
            "coverage": 0.0,
            "complexity": 1.0,
            "test_count": 0,
        }
        sanitized = DatasetValidator.validate_metric_payload(payload)
        assert sanitized["lines_of_code"] == 1
        assert sanitized["coverage"] == 0.0
        assert sanitized["complexity"] == 1.0
        assert sanitized["test_count"] == 0

        # Maximum boundary for coverage
        payload["coverage"] = 100.0
        sanitized = DatasetValidator.validate_metric_payload(payload)
        assert sanitized["coverage"] == 100.0

    def test_integer_coverage_and_complexity_normalized_to_float(self):
        """Test that integer inputs for coverage and complexity are converted to float."""
        payload = {
            "lines_of_code": 50,
            "coverage": 80,
            "complexity": 2,
            "test_count": 10,
        }
        sanitized = DatasetValidator.validate_metric_payload(payload)
        assert isinstance(sanitized["coverage"], float)
        assert sanitized["coverage"] == 80.0
        assert isinstance(sanitized["complexity"], float)
        assert sanitized["complexity"] == 2.0

    def test_custom_required_keys(self):
        """Test with custom required key subset omitting complexity/test_count."""
        payload = {"lines_of_code": 500, "coverage": 80.0}
        sanitized = DatasetValidator.validate_metric_payload(
            payload, required_keys=["lines_of_code", "coverage"]
        )
        assert "lines_of_code" in sanitized
        assert "coverage" in sanitized
        assert "complexity" not in sanitized
        assert "test_count" not in sanitized

    def test_allow_extra_keys_flag(self):
        """Test that allow_extra_keys=True preserves extra unrecognized keys."""
        payload = {
            "lines_of_code": 100,
            "coverage": 75.0,
            "complexity": 2.5,
            "test_count": 12,
            "author": "engineer@ericsson.se",
            "branch": "main",
        }
        sanitized = DatasetValidator.validate_metric_payload(payload, allow_extra_keys=True)
        assert sanitized["author"] == "engineer@ericsson.se"
        assert sanitized["branch"] == "main"


    # Error & Exception Paths
    def test_reject_non_dict_payload(self):
        """Test that passing non-dict types raises ValidationError."""
        with pytest.raises(ValidationError, match="Payload must be a dictionary"):
            DatasetValidator.validate_metric_payload(["not", "a", "dict"])

    def test_reject_empty_dict(self):
        """Test that an empty dictionary raises ValidationError."""
        with pytest.raises(ValidationError, match="Payload dictionary cannot be empty"):
            DatasetValidator.validate_metric_payload({})

    def test_missing_required_field_raises_missing_field_error(self):
        """Test that missing required field raises MissingFieldError."""
        payload = {
            "lines_of_code": 100,
            "coverage": 90.0,
            "complexity": 2.0,
            # missing test_count
        }
        with pytest.raises(MissingFieldError, match="Missing required metric field: 'test_count'"):
            DatasetValidator.validate_metric_payload(payload)

    def test_disallowed_extra_keys_raise_validation_error(self):
        """Test that extra keys raise ValidationError when allow_extra_keys=False."""
        payload = {
            "lines_of_code": 100,
            "coverage": 90.0,
            "complexity": 2.0,
            "test_count": 5,
            "unexpected_metric": 42,
        }
        with pytest.raises(ValidationError, match="Unrecognized metric keys found"):
            DatasetValidator.validate_metric_payload(payload, allow_extra_keys=False)

    @pytest.mark.parametrize(
        "invalid_loc",
        [True, False, 12.5, "100", None, [100]],
    )
    def test_invalid_loc_types(self, invalid_loc):
        """Test type validation rejection for lines_of_code."""
        payload = {
            "lines_of_code": invalid_loc,
            "coverage": 80.0,
            "complexity": 2.0,
            "test_count": 5,
        }
        with pytest.raises(TypeValidationError):
            DatasetValidator.validate_metric_payload(payload)

    def test_loc_less_than_one_raises_range_error(self):
        """Test that lines_of_code < 1 raises RangeValidationError."""
        payload = {
            "lines_of_code": 0,
            "coverage": 80.0,
            "complexity": 2.0,
            "test_count": 5,
        }
        with pytest.raises(RangeValidationError, match="'lines_of_code' must be >= 1"):
            DatasetValidator.validate_metric_payload(payload)

    @pytest.mark.parametrize("invalid_cov", [True, False, "80", None, {}])
    def test_invalid_coverage_types(self, invalid_cov):
        """Test type validation rejection for coverage."""
        payload = {
            "lines_of_code": 100,
            "coverage": invalid_cov,
            "complexity": 2.0,
            "test_count": 5,
        }
        with pytest.raises(TypeValidationError):
            DatasetValidator.validate_metric_payload(payload)

    @pytest.mark.parametrize("out_of_bounds_cov", [-0.1, 100.01, -50.0, 150.0])
    def test_coverage_out_of_bounds_raises_range_error(self, out_of_bounds_cov):
        """Test that coverage outside [0.0, 100.0] raises RangeValidationError."""
        payload = {
            "lines_of_code": 100,
            "coverage": out_of_bounds_cov,
            "complexity": 2.0,
            "test_count": 5,
        }
        with pytest.raises(RangeValidationError, match="'coverage' must be between 0.0 and 100.0"):
            DatasetValidator.validate_metric_payload(payload)

    @pytest.mark.parametrize("invalid_comp", [True, "2.0", None])
    def test_invalid_complexity_types(self, invalid_comp):
        """Test type validation rejection for complexity."""
        payload = {
            "lines_of_code": 100,
            "coverage": 80.0,
            "complexity": invalid_comp,
            "test_count": 5,
        }
        with pytest.raises(TypeValidationError):
            DatasetValidator.validate_metric_payload(payload)

    def test_complexity_less_than_one_raises_range_error(self):
        """Test complexity < 1.0 raises RangeValidationError."""
        payload = {
            "lines_of_code": 100,
            "coverage": 80.0,
            "complexity": 0.99,
            "test_count": 5,
        }
        with pytest.raises(RangeValidationError, match="'complexity' must be >= 1.0"):
            DatasetValidator.validate_metric_payload(payload)

    @pytest.mark.parametrize("invalid_tc", [True, 4.5, "10", None])
    def test_invalid_test_count_types(self, invalid_tc):
        """Test type validation rejection for test_count."""
        payload = {
            "lines_of_code": 100,
            "coverage": 80.0,
            "complexity": 2.0,
            "test_count": invalid_tc,
        }
        with pytest.raises(TypeValidationError):
            DatasetValidator.validate_metric_payload(payload)

    def test_negative_test_count_raises_range_error(self):
        """Test negative test_count raises RangeValidationError."""
        payload = {
            "lines_of_code": 100,
            "coverage": 80.0,
            "complexity": 2.0,
            "test_count": -1,
        }
        with pytest.raises(RangeValidationError, match="'test_count' must be >= 0"):
            DatasetValidator.validate_metric_payload(payload)


class TestValidateNumericBounds:
    """Test suite for DatasetValidator.validate_numeric_bounds."""

    def test_within_inclusive_bounds(self):
        """Test nominal value squarely within bounds."""
        assert DatasetValidator.validate_numeric_bounds(50.0, min_val=0.0, max_val=100.0) is True

    def test_exact_boundary_hits_inclusive(self):
        """Test exact lower and upper boundary hits with inclusive=True."""
        assert DatasetValidator.validate_numeric_bounds(0.0, min_val=0.0, max_val=100.0, inclusive_min=True) is True
        assert DatasetValidator.validate_numeric_bounds(100.0, min_val=0.0, max_val=100.0, inclusive_max=True) is True

    def test_exact_boundary_hits_exclusive(self):
        """Test exact lower and upper boundary hits with inclusive=False."""
        assert DatasetValidator.validate_numeric_bounds(0.0, min_val=0.0, max_val=100.0, inclusive_min=False) is False
        assert DatasetValidator.validate_numeric_bounds(100.0, min_val=0.0, max_val=100.0, inclusive_max=False) is False

    def test_out_of_bounds(self):
        """Test values outside bounds."""
        assert DatasetValidator.validate_numeric_bounds(-0.01, min_val=0.0, max_val=100.0) is False
        assert DatasetValidator.validate_numeric_bounds(100.01, min_val=0.0, max_val=100.0) is False

    def test_unbounded_limits(self):
        """Test when min_val or max_val is None."""
        assert DatasetValidator.validate_numeric_bounds(-999.0, min_val=None, max_val=0.0) is True
        assert DatasetValidator.validate_numeric_bounds(10.0, min_val=None, max_val=0.0) is False
        assert DatasetValidator.validate_numeric_bounds(999.0, min_val=0.0, max_val=None) is True
        assert DatasetValidator.validate_numeric_bounds(-5.0, min_val=0.0, max_val=None) is False
        assert DatasetValidator.validate_numeric_bounds(42, min_val=None, max_val=None) is True


    def test_inverted_bounds_raises_value_error(self):
        """Test that min_val > max_val raises ValueError."""
        with pytest.raises(ValueError, match="Lower bound .* cannot exceed upper bound"):
            DatasetValidator.validate_numeric_bounds(10.0, min_val=100.0, max_val=50.0)

    @pytest.mark.parametrize("invalid_val", [True, False, "50", None, [10]])
    def test_invalid_value_type_raises_type_error(self, invalid_val):
        """Test type validation on value."""
        with pytest.raises(TypeValidationError):
            DatasetValidator.validate_numeric_bounds(invalid_val, min_val=0.0, max_val=100.0)

    @pytest.mark.parametrize("invalid_bound", [True, "0", []])
    def test_invalid_bounds_types_raise_type_error(self, invalid_bound):
        """Test type validation on min_val and max_val."""
        with pytest.raises(TypeValidationError):
            DatasetValidator.validate_numeric_bounds(10, min_val=invalid_bound)
        with pytest.raises(TypeValidationError):
            DatasetValidator.validate_numeric_bounds(10, max_val=invalid_bound)
