# Phase 5: Test Suite Quality & Flakiness Comparison Report

This report documents the structural quality metrics, verification densities, flakiness stress tests, and "Weak Positive" failure modes across the Manual and AI test suites.

---

## 1. Structural Test Quality Metrics

| Metric | Manual Test Suite | AI-Generated Test Suite | Variance ($\Delta$) |
| :--- | :---: | :---: | :---: |
| **Total Test Functions** | **122** | **33** | -72.95% |
| **Explicit `assert` Statements** | **131** | **41** | -68.70% |
| **`pytest.raises` Exception Checks** | **73** | **11** | -84.93% |
| **Total Verification Points** | **204** | **52** | -74.51% |
| **Verification Points per Test** | **1.67** | **1.58** | -5.39% |
| **Lines of Test Code (LOC)** | **1,144** | **290** | -74.65% |
| **LOC per Test Function** | **9.38** | **8.79** | -6.29% |

---

## 2. Flakiness & Non-Determinism Stress Test (10x Iterations)

| Test Suite | Runs Executed | Failed Runs | Flakiness Rate (%) | Avg Duration | Min Duration | Max Duration |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Manual Suite** (`tests/manual`) | 10 | 0 | **0.00%** (Deterministic) | 0.061s | 0.054s | 0.078s |
| **AI Suite** (`tests/ai_generated`) | 10 | 0 | **0.00%** (Deterministic) | 0.024s | 0.021s | 0.035s |

> **Conclusion**: Both suites exhibit zero non-deterministic flakiness under rapid repeated execution in isolated environments.

---

## 3. Systematic Catalogue of "Weak Positive" AI Assertions

"Weak Positives" are tests that execute code paths and pass without asserting semantic correctness, allowing critical bugs to escape into production.

### Case 1: Loose Inequality on Numerical Outputs
- **Location**: `TestQualityMetricsCalculatorAI.test_precision_recall_f1_nominal`
- **AI Assertion**:
  ```python
  res = QualityMetricsCalculator.calculate_precision_recall_f1(10, 2, 3)
  assert res["precision"] > 0.0
  assert res["recall"] > 0.0
  assert res["f1_score"] > 0.0
  ```
- **Flaw**: Passes even if the formula is mutated from `tp / (tp + fp)` to `tp * (tp + fp)` (e.g. $120 > 0.0$).
- **Remedy**: `assert res["precision"] == 0.8333` and `assert res["f1_score"] == 0.8000`.

### Case 2: Trivial Type and Range Bounds
- **Location**: `TestQualityMetricsCalculatorAI.test_brier_score_nominal`
- **AI Assertion**:
  ```python
  score = QualityMetricsCalculator.calculate_brier_score(probs, outcomes)
  assert isinstance(score, float)
  assert 0.0 <= score <= 1.0
  ```
- **Flaw**: Validates that the return type is float, but ignores whether the calculation matches the $(1/N)\sum(p_i - y_i)^2$ formula.
- **Remedy**: `assert score == 0.040000`.

### Case 3: Structure Existence Check without Value Verification
- **Location**: `TestQualityRiskScorerAI.test_composite_risk_nominal`
- **AI Assertion**:
  ```python
  res = scorer.calculate_composite_risk(coverage_pct=85.0, cyclomatic_complexity=3.0, churn_lines=20, smell_count=1, total_loc=200)
  assert "risk_score" in res
  assert "tier" in res
  assert 0.0 <= res["risk_score"] <= 100.0
  ```
- **Flaw**: Survived 95.7% of mutants inside the S-curve penalty and weight normalizer because no specific score or tier threshold was asserted.
- **Remedy**: `assert res["risk_score"] == 18.25` and `assert res["tier"] == RiskTier.LOW.value`.

### Case 4: Incomplete Object State Inspection
- **Location**: `TestDatasetValidatorAI.test_validate_metric_payload_nominal`
- **AI Assertion**:
  ```python
  assert res is not None
  assert res["lines_of_code"] == 200
  ```
- **Flaw**: Does not assert sanitized float types or presence/absence of optional fields.
- **Remedy**: Assert all dictionary key-value types and sanitized values.
