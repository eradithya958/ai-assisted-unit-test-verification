# Phase 4: Fault & Bug Detection Rate via Mutation Testing Report

This report presents the empirical mutation testing results comparing the **Manual Test Suite** against the **AI-Generated Test Suite** across the identical 241 single-point mutant population.

---

## 1. Overall Mutation Benchmark Summary

| Metric | Manual Test Suite (Phase 2) | AI-Generated Test Suite (Phase 3) | Variance ($\Delta$) |
| :--- | :---: | :---: | :---: |
| **Total AST Mutants Generated** | 241 | 241 | — |
| **Mutants Killed (Bugs Caught)** | **179** | **59** | -67.0% |
| **Mutants Survived (Bugs Escaped)** | **62** | **182** | +193.5% |
| **Mutation Score (% Killed)** | **74.27%** | **24.48%** | **-49.79 pp** |
| **Code Coverage (Combined)** | 99.40% | 65.01% | -34.39 pp |
| **Coverage-to-Mutation Ratio** | **1.34** | **2.66** | (AI requires 2x coverage per killed bug) |

> [!IMPORTANT]
> **Key Finding**: While the AI test suite achieved a respectable **65.01% code coverage**, its mutation score was only **24.48%**. This empirically proves that code coverage is a deceptive proxy for test thoroughness when assertions are weak or boundary conditions are untested.

---

## 2. Per-Module Mutation Detection Comparison

| Target Module | Total Mutants | Manual Killed | Manual Score | AI Killed | AI Score | $\Delta$ Score |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **`validator.py`** | 41 | 34 | **82.93%** | 9 | **21.95%** | -60.98 pp |
| **`metrics.py`** | 76 | 68 | **89.47%** | 33 | **43.42%** | -46.05 pp |
| **`risk_scorer.py`** | 70 | 35 | **50.00%** | 3 | **4.29%** | -45.71 pp |
| **`gate_tracker.py`** | 26 | 16 | **61.54%** | 2 | **7.69%** | -53.85 pp |
| **`rule_engine.py`** | 28 | 26 | **92.86%** | 12 | **42.86%** | -50.00 pp |
| **Aggregate Total** | **241** | **179** | **74.27%** | **59** | **24.48%** | **-49.79 pp** |

---

## 3. Mutation Operator Breakdown

| Mutation Operator Class | Description | Mutants | Manual Killed (%) | AI Killed (%) | Vulnerability Gap |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **COR** | Conditional Operator Replacement (`and` $\leftrightarrow$ `or`) | 31 | **83.87%** (26/31) | **3.23%** (1/31) | **-80.64 pp** |
| **AOR** | Arithmetic Operator Replacement (`+`, `-`, `*`, `/`) | 40 | **62.50%** (25/40) | **12.50%** (5/40) | **-50.00 pp** |
| **BVA** | Boundary Shift ($\pm 1$ on thresholds: $0, 1, 10, 25, 30, 70, 100$) | 75 | **73.33%** (55/75) | **26.67%** (20/75) | **-46.66 pp** |
| **ROR** | Relational Operator Replacement (`<`, `<=`, `>`, `>=`, `==`, `!=`) | 71 | **76.06%** (54/71) | **32.39%** (23/71) | **-43.67 pp** |
| **CRP** | Constant Replacement (swapping booleans / numeric constants) | 12 | **58.33%** (7/12) | **25.00%** (3/12) | **-33.33 pp** |
| **LCR** | Logical Connector & Membership (`in` $\leftrightarrow$ `not in`) | 12 | **100.0%** (12/12) | **58.33%** (7/12) | **-41.67 pp** |

---

## 4. In-Depth Analysis of Mutation Escapes

### A. Why did AI tests miss 96.8% of Conditional Operator mutants (COR)?
When compound boolean conditions like:
```python
if isinstance(p, bool) or not isinstance(p, (int, float)):
```
were mutated to:
```python
if isinstance(p, bool) and not isinstance(p, (int, float)):
```
the AI suite failed to detect the bug because it never tested passing a `bool` (e.g. `True`) to see if it gets rejected. The manual suite had parameterized type rejection suites that caught this mutant instantly.

### B. Why did AI tests miss 87.5% of Arithmetic mutants (AOR)?
In `QualityMetricsCalculator`, when precision formula was mutated from:
```python
precision = (tp / prec_denom)
```
to:
```python
precision = (tp * prec_denom)
```
the AI test:
```python
res = QualityMetricsCalculator.calculate_precision_recall_f1(10, 2, 3)
assert res["precision"] > 0.0  # Weak Positive! (10 * 12 = 120 > 0.0)
```
**passed despite the code producing total garbage!** The manual test checked `assert res["precision"] == 0.8333`, killing the mutant immediately.

### C. Why did AI tests miss 95.7% of mutants in `risk_scorer.py`?
The AI suite only checked `assert "risk_score" in res` and `assert 0.0 <= res["risk_score"] <= 100.0`. Consequently, virtually every formula mutation inside the S-curve calculation, weights application, and tier boundaries survived unnoticed in the AI suite.
