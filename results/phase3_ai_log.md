# Phase 3: AI-Assisted Test Generation Report

This report documents the empirical results, generation latency, manual repairs, code coverage, and qualitative blindspots observed from the AI-generated unit test suite.

---

## 1. Summary Metrics

| Metric | Manual Suite (Phase 2) | AI-Generated Suite (Phase 3) | Delta ($\Delta$) |
| :--- | :---: | :---: | :---: |
| **Total Test Executions** | 199 tests | 35 tests | -82.4% |
| **Total Assertions** | 131 asserts | 41 asserts | -68.7% |
| **Lines of Test Code (LOC)** | 1,144 LOC | 290 LOC | -74.6% |
| **Production / Creation Time** | 75 min (manual authoring) | 21.3s (gen) + 8 min (review/repair) | **~89% time savings** |
| **Statement Coverage** | **100.00%** | **73.03%** | -26.97 pp |
| **Branch Coverage** | **98.36%** | **51.23%** | -47.13 pp |
| **Combined Coverage** | **99.40%** | **65.01%** | -34.39 pp |

---

## 2. Per-Module Comparison: Manual vs AI Coverage

| Target Module | Manual Stmt Cov | Manual Branch Cov | AI Stmt Cov | AI Branch Cov | AI Combined Cov | AI Tests |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **`validator.py`** | 100.0% | 94.44% | 79.78% | 55.56% | 68.94% | 10 |
| **`metrics.py`** | 100.0% | 100.0% | 73.96% | 60.61% | 68.52% | 9 |
| **`risk_scorer.py`** | 100.0% | 100.0% | 58.57% | 28.95% | 48.15% | 5 |
| **`gate_tracker.py`** | 100.0% | 100.0% | 84.42% | 54.55% | 77.78% | 6 |
| **`rule_engine.py`** | 100.0% | 100.0% | 66.67% | 47.83% | 60.15% | 5 |
| **Total / Aggregate** | **100.0%** | **98.36%** | **73.03%** | **51.23%** | **65.01%** | **35** |

---

## 3. Manual Corrections & Repairs Log

| Module | Issue Detected | Root Cause | Fix Applied |
| :--- | :--- | :--- | :--- |
| **`gate_tracker.py`** | `InvalidStateTransitionError` in `test_reset_gate` | AI attempted direct state transition `PASSED -> INITIALIZED`, which violates the state transition table (only `BLOCKED -> INITIALIZED` is valid). | Updated test to block gate first before calling `reset_to_initial`. |
| **`risk_scorer.py`** | Import path resolution | Relative import in standalone test file. | Normalized import to absolute package namespace `quality_assessment.risk_scorer`. |
| **`validator.py`** | Exception class resolution | Needed verification against exported symbols. | Confirmed all 4 custom validation exceptions are properly referenced. |

---

## 4. Key Qualitative Insights & LLM Failure Modes

1. **Weak Positive Assertions**:
   - In `test_metrics.py`, the AI asserted `assert res["precision"] > 0.0` instead of asserting the exact calculated float value (`0.8333`).
   - In `test_risk_scorer.py`, the AI asserted `assert 0.0 <= res["risk_score"] <= 100.0` and `assert "tier" in res` without validating whether the score correctly mapped to `LOW`, `MEDIUM`, or `HIGH` based on specific threshold boundaries.

2. **Shallow State Machine Coverage**:
   - The AI generated 1-step direct transitions (`INITIALIZED -> PASSED`, `INITIALIZED -> FAILED`), but missed multi-step temporal invariants like the **hysteresis recovery debounce** ($N$ consecutive passes required).

3. **Operator & Predicate Sparsity**:
   - In `test_rule_engine.py`, the AI tested only 2 of 8 comparison operators (`gt`, `eq`), completely ignoring `lt`, `lte`, `gte`, `neq`, `in`, and `not_in`.

4. **Speed vs Depth Tradeoff**:
   - The AI generated 35 functional, valid tests in **21 seconds**, offering an instant foundation, but leaving 48.8% of branch logic unexercised.
