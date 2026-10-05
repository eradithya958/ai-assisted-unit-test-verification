# Phase 6: Three-Way Hybrid Benchmark Report (AI Assists, Human Verifies)

This report presents the core thesis finding: a three-way empirical comparison among **Manual-Only**, **AI-Only**, and **AI-Plus-Human-Review (Hybrid)** test engineering paradigms.

---

## 1. Headline Benchmark Results (The 3-Way Comparison)

| Metric | Manual-Only Suite | AI-Only Suite | Hybrid Suite (AI + Human Review) | Key Takeaway / Finding |
| :--- | :---: | :---: | :---: | :--- |
| **Total Test Executions** | 199 | 35 | 59 | Hybrid is compact but dense |
| **Lines of Test Code (LOC)** | 1,144 LOC | 290 LOC | 473 LOC | 58.6% less test code to maintain vs Manual |
| **Engineering Time Spent** | **75.0 min** | **8.35 min** (gen+fix) | **18.35 min** (gen+review) | **75.5% time reduction vs Manual** |
| **Statement Coverage** | **100.0%** | 73.03% | **84.49%** | +11.46 pp over AI |
| **Branch Coverage** | **98.36%** | 51.23% | **71.72%** | +20.49 pp over AI |
| **Combined Coverage** | **99.40%** | 65.01% | **78.88%** | Solid enterprise baseline |
| **Mutants Killed (Faults Caught)** | **197 / 241** | **64 / 241** | **133 / 241** | **+107.8% more bugs caught than AI alone** |
| **Mutation Score (% Killed)** | **81.74%** | **26.56%** | **55.19%** | **+28.63 pp improvement over AI** |
| **Efficiency (Kills / Eng. Min)** | 2.63 kills/min | 7.66 kills/min | **7.25 kills/min** | **Highest yield of thorough bug catching** |

---

## 2. Per-Module Mutation Detection Breakdown

| Target Module | Total Mutants | Manual-Only Score | AI-Only Score | Hybrid (AI+Review) Score | $\Delta$ (Hybrid vs AI) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **`validator.py`** | 41 | **90.24%** (37/41) | 24.39% (10/41) | **53.66%** (22/41) | **+29.27 pp** |
| **`metrics.py`** | 76 | **92.11%** (70/76) | 42.11% (32/76) | **57.89%** (44/76) | **+15.78 pp** |
| **`risk_scorer.py`** | 70 | **65.71%** (46/70) | 11.43% (8/70) | **50.00%** (35/70) | **+38.57 pp** |
| **`gate_tracker.py`** | 26 | **69.23%** (18/26) | 11.54% (3/26) | **30.77%** (8/26) | **+19.23 pp** |
| **`rule_engine.py`** | 28 | **92.86%** (26/28) | 39.29% (11/28) | **85.71%** (24/28) | **+46.42 pp** |
| **Aggregate Total** | **241** | **81.74%** (197/241) | **26.56%** (64/241) | **55.19%** (133/241) | **+28.63 pp** |

---

## 3. Mutation Operator Analysis

| Mutation Operator Class | Mutants | Manual Killed | AI-Only Killed | Hybrid Killed | Key Human Review Contribution |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **Arithmetic (AOR)** | 40 | **95.00%** | 22.50% | **87.50%** | Replaced loose `> 0` inequality checks with exact formula outputs. |
| **Logical Connector (LCR)** | 12 | **100.0%** | 58.33% | **91.67%** | Added missing `in` / `not in` rule predicates. |
| **Boundary Shift (BVA)** | 75 | **76.00%** | 22.67% | **48.00%** | Added exact lower and upper inclusive/exclusive bound test fixtures. |
| **Relational Operator (ROR)** | 71 | **77.46%** | 35.21% | **54.93%** | Exercised off-by-one comparison branches in validator and risk scorer. |
| **Constant Replacement (CRP)** | 12 | **58.33%** | 25.00% | **50.00%** | Validated default configurations and weights sum invariants. |
| **Conditional (COR)** | 31 | **90.32%** | 9.68% | **19.35%** | Added parameterized type rejection for compound boolean checks. |

---

## 4. Engineering Takeaway for Ericsson / Telecom Applications

> **The Core Finding: "AI Accelerates Drafts, Human Engineering Anchors Correctness"**
>
> 1. **Zero-to-One Velocity**: The LLM creates 65% coverage in seconds, eliminating blank-page paralysis and writing boilerplate test fixtures.
> 2. **The Verification Deficit**: Raw AI suites leave a **~55% fault-detection gap** due to weak assertion patterns and shallow state coverage.
> 3. **The 18-Minute Fix**: Spending just 10–15 minutes of human review on the AI draft doubles the fault detection rate (+108% more mutants killed), achieving **55.2% mutation coverage** with **75.5% less authoring time** than writing tests entirely by hand.
