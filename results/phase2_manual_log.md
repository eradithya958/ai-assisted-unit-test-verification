# Phase 2: Manual Test Suite Baseline Report

This report documents the manual unit test suite written strictly **before** seeing or generating any AI test output, establishing the empirical baseline for our thesis research.

---

## 1. Summary Metrics

| Metric | Measured Value |
| :--- | :--- |
| **Total Target Modules** | 5 |
| **Total Test Files** | 5 (`tests/manual/test_*.py`) |
| **Total Pytest Executions** | 199 tests (including parameterized variants) |
| **Total Test Functions** | 122 function definitions |
| **Total Assert Statements** | 131 explicit assertions + 68 `pytest.raises` checks |
| **Total Lines of Test Code (LOC)** | 1,144 lines |
| **Total Time Spent** | 75 minutes (~12–17 min/module) |
| **Overall Statement Coverage** | **100.00%** (419 / 419 statements) |
| **Overall Branch Coverage** | **98.36%** (240 / 244 branches) |
| **Overall Combined Coverage** | **99.40%** |

---

## 2. Per-Module Breakdown

| Target Module | Test File | Pytest Tests | Assertions | Test LOC | Time Spent | Stmt Cov | Branch Cov | Combined Cov |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **`validator.py`** | [test_validator.py](file:///Users/adithya/Desktop/AI%20assis%20UT%20gene%20and%20sftwr%20verification/tests/manual/test_validator.py) | 41 | 31 | 274 | 16 min | 100.0% | 94.44% | 97.52% |
| **`metrics.py`** | [test_metrics.py](file:///Users/adithya/Desktop/AI%20assis%20UT%20gene%20and%20sftwr%20verification/tests/manual/test_metrics.py) | 55 | 27 | 268 | 17 min | 100.0% | 100.0% | 100.0% |
| **`risk_scorer.py`** | [test_risk_scorer.py](file:///Users/adithya/Desktop/AI%20assis%20UT%20gene%20and%20sftwr%20verification/tests/manual/test_risk_scorer.py) | 44 | 23 | 258 | 15 min | 100.0% | 100.0% | 100.0% |
| **`gate_tracker.py`** | [test_gate_tracker.py](file:///Users/adithya/Desktop/AI%20assis%20UT%20gene%20and%20sftwr%20verification/tests/manual/test_gate_tracker.py) | 22 | 39 | 168 | 14 min | 100.0% | 100.0% | 100.0% |
| **`rule_engine.py`** | [test_rule_engine.py](file:///Users/adithya/Desktop/AI%20assis%20UT%20gene%20and%20sftwr%20verification/tests/manual/test_rule_engine.py) | 37 | 11 | 176 | 13 min | 100.0% | 100.0% | 100.0% |
| **Total / Aggregate** | **5 test suites** | **199** | **131** | **1,144** | **75 min** | **100.0%** | **98.36%** | **99.40%** |

---

## 3. Test Engineering Methodology & Observations

1. **Boundary Value Analysis (BVA)**:
   - Evaluated exact limits ($0.0$, $100.0$, $1.0$, $1$, empty collections).
   - Tested off-by-one and infinitesimal boundary violations ($-0.01$, $100.01$, $0.99$).

2. **Negative & Exception Path Assertion**:
   - Explicitly verified exception hierarchies (`RangeValidationError`, `MissingFieldError`, `TypeValidationError`, `InvalidStateTransitionError`, `RuleEvaluationError`).
   - Ensured exact error message matching via `pytest.raises(..., match=...)`.

3. **State Machine Verification**:
   - Validated hysteresis recovery requiring $N$ consecutive passes.
   - Tested emergency lock (`BLOCKED`) invariant preservation.

4. **Zero-Division & Uncertainty Resilience**:
   - Assayed extreme statistical edge cases (zero TP/FP/FN counts, uniform distributions, $p=0.0$ entropy avoidance).

---

## 4. Integrity Assertion
> **Verification Guarantee**: These tests were authored strictly using [docs/SPECIFICATIONS.md](file:///Users/adithya/Desktop/AI%20assis%20UT%20gene%20and%20sftwr%20verification/docs/SPECIFICATIONS.md) as the ground truth spec. No LLM generation was executed or observed during this phase.
