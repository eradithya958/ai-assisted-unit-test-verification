"""Hybrid Test Suite for DatasetValidator (AI-Generated Base + Human Review).

Strengthened with strict type rejection, inverted bounds checks,
and exact boundary edge cases.
"""

import pytest
from quality_assessment.validator import (
    DatasetValidator,
    ValidationError,
    MissingFieldError,
    TypeValidationError,
    RangeValidationError,
)


class TestDatasetValidatorHybrid:
    """Hybrid test suite for DatasetValidator."""

    # AI Base - Strengthened with exact type & value assertions
    def test_validate_metric_payload_nominal(self):
        """Happy path test with valid payload."""
        payload = {
            "lines_of_code": 200,
            "coverage": 88.0,
            "complexity": 3.5,
            "test_count": 15,
        }
        res = DatasetValidator.validate_metric_payload(payload)
        assert res["lines_of_code"] == 200
        assert res["coverage"] == 88.0
        assert isinstance(res["coverage"], float)
        assert res["complexity"] == 3.5
        assert isinstance(res["complexity"], float)
        assert res["test_count"] == 15

    def test_validate_metric_payload_empty_dict(self):
        """Test rejection of empty dictionary."""
        with pytest.raises(ValidationError, match="Payload dictionary cannot be empty"):
            DatasetValidator.validate_metric_payload({})

    def test_validate_metric_payload_missing_field(self):
        """Test missing required field raises error."""
        payload = {"lines_of_code": 100, "coverage": 50.0}
        with pytest.raises(MissingFieldError, match="Missing required metric field"):
            DatasetValidator.validate_metric_payload(payload)

    def test_validate_metric_payload_extra_keys_disallowed(self):
        """Test unrecognized key rejection."""
        payload = {
            "lines_of_code": 100,
            "coverage": 50.0,
            "complexity": 2.0,
            "test_count": 5,
            "extra_field": "disallowed",
        }
        with pytest.raises(ValidationError, match="Unrecognized metric keys found"):
            DatasetValidator.validate_metric_payload(payload, allow_extra_keys=False)

    # Human Added: Boundary & Strict Type Rejections (Killing COR/BVA mutants)
    @pytest.mark.parametrize("cov", [-1.0, -0.01, 100.01, 105.0])
    def test_validate_metric_payload_coverage_range(self, cov):
        """Test out of range coverage."""
        payload = {
            "lines_of_code": 100,
            "coverage": cov,
            "complexity": 2.0,
            "test_count": 5,
        }
        with pytest.raises(RangeValidationError, match="'coverage' must be between"):
            DatasetValidator.validate_metric_payload(payload)

    @pytest.mark.parametrize("loc", [0, -1, -5])
    def test_validate_metric_payload_loc_range(self, loc):
        """Test lines of code range check."""
        payload = {
            "lines_of_code": loc,
            "coverage": 80.0,
            "complexity": 2.0,
            "test_count": 5,
        }
        with pytest.raises(RangeValidationError, match="'lines_of_code' must be >= 1"):
            DatasetValidator.validate_metric_payload(payload)

    @pytest.mark.parametrize("invalid_type", [True, False, "100", None, [10]])
    def test_type_rejection_on_all_fields(self, invalid_type):
        """Human Added: Catch COR mutants where 'isinstance(x, bool) or not isinstance' is mutated."""
        with pytest.raises(TypeValidationError):
            DatasetValidator.validate_metric_payload(
                {"lines_of_code": invalid_type, "coverage": 80.0, "complexity": 2.0, "test_count": 5}
            )
        with pytest.raises(TypeValidationError):
            DatasetValidator.validate_metric_payload(
                {"lines_of_code": 100, "coverage": invalid_type, "complexity": 2.0, "test_count": 5}
            )

    # Human Added: Numeric Bounds Invariant & Single-Sided Checks
    def test_validate_numeric_bounds_nominal(self):
        """Test scalar within bounds."""
        assert DatasetValidator.validate_numeric_bounds(50.0, 0.0, 100.0) is True
        assert DatasetValidator.validate_numeric_bounds(150.0, 0.0, 100.0) is False

    def test_validate_numeric_bounds_exact_hits(self):
        """Test exact boundary hits inclusive and exclusive."""
        assert DatasetValidator.validate_numeric_bounds(0.0, 0.0, 100.0, inclusive_min=True) is True
        assert DatasetValidator.validate_numeric_bounds(0.0, 0.0, 100.0, inclusive_min=False) is False
        assert DatasetValidator.validate_numeric_bounds(100.0, 0.0, 100.0, inclusive_max=True) is True
        assert DatasetValidator.validate_numeric_bounds(100.0, 0.0, 100.0, inclusive_max=False) is False

    def test_validate_numeric_bounds_inverted_error(self):
        """Human Added: Catch min > max inverted bound check."""
        with pytest.raises(ValueError, match="Lower bound .* cannot exceed upper bound"):
            DatasetValidator.validate_numeric_bounds(10.0, min_val=100.0, max_val=50.0)

    def test_validate_numeric_bounds_type_error(self):
        """Test non-numeric scalar rejection."""
        with pytest.raises(TypeValidationError):
            DatasetValidator.validate_numeric_bounds("fifty", 0.0, 100.0)
        with pytest.raises(TypeValidationError):
            DatasetValidator.validate_numeric_bounds(True, 0.0, 100.0)
