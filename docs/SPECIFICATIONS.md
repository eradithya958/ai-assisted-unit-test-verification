# Target Modules Specification & Ground Truth Reference

This document formalizes the behavioral specification and domain contracts for the 5 target modules in `src/quality_assessment/`. These specifications serve as the **ground truth** against which both manual tests (Phase 2) and AI-generated tests (Phase 3) are evaluated.

---

## 1. `DatasetValidator` ([validator.py](file:///Users/adithya/Desktop/AI%20assis%20UT%20gene%20and%20sftwr%20verification/src/quality_assessment/validator.py))
**Logic Archetype**: Structural & Type Validation, Branching Error Handling, Domain Constraint Checking.

### Methods:
#### `validate_metric_payload(payload: Dict[str, Any], required_keys: Optional[List[str]] = None, allow_extra_keys: bool = False) -> Dict[str, Any]`
- **Purpose**: Validates dictionary payloads containing code/test metrics and sanitizes field types.
- **Default Required Keys**: `['lines_of_code', 'coverage', 'complexity', 'test_count']`
- **Domain Constraints**:
  - `lines_of_code`: Integer $\ge 1$. (Rejects `bool`, floats, strings, numbers $< 1$).
  - `coverage`: Float/Int in $[0.0, 100.0]$. Normalized to `float`.
  - `complexity`: Float/Int $\ge 1.0$. Normalized to `float`.
  - `test_count`: Integer $\ge 0$. (Rejects `bool`, floats, negative numbers).
- **Exceptions**:
  - `ValidationError`: Payload is not a `dict`, is empty (`{}`), or contains unrecognized keys when `allow_extra_keys=False`.
  - `MissingFieldError`: Any required key is missing from `payload`.
  - `TypeValidationError`: Field value fails explicit type requirements (e.g. `bool` passed for integer, `None` value).
  - `RangeValidationError`: Numeric values violate domain boundaries.

#### `validate_numeric_bounds(value: Union[int, float], min_val: Optional[float] = None, max_val: Optional[float] = None, inclusive_min: bool = True, inclusive_max: bool = True) -> bool`
- **Purpose**: Checks whether a numeric scalar lies within specified bounds.
- **Behavior**:
  - Supports strict ($>$, $<$) or inclusive ($\ge$, $\le$) bounds.
  - If `min_val` or `max_val` is `None`, that boundary is unbounded.
- **Exceptions**:
  - `TypeValidationError`: Non-numeric types (or `bool`) passed for `value`, `min_val`, or `max_val`.
  - `ValueError`: If `min_val > max_val`.

---

## 2. `QualityMetricsCalculator` ([metrics.py](file:///Users/adithya/Desktop/AI%20assis%20UT%20gene%20and%20sftwr%20verification/src/quality_assessment/metrics.py))
**Logic Archetype**: Numeric Arithmetic, Statistical Analysis, Floating-point Edge Cases, Zero-Division Safeguards.

### Methods:
#### `calculate_precision_recall_f1(true_positives: int, false_positives: int, false_negatives: int, zero_division_value: float = 0.0) -> Dict[str, float]`
- **Formulas**:
  - $\text{Precision} = \frac{TP}{TP + FP}$
  - $\text{Recall} = \frac{TP}{TP + FN}$
  - $\text{F1} = \frac{2 \cdot \text{Precision} \cdot \text{Recall}}{\text{Precision} + \text{Recall}}$
- **Return**: `{"precision": float, "recall": float, "f1_score": float}` rounded to 4 decimals.
- **Edge Cases**:
  - If denominator is 0, metric defaults to `zero_division_value`.
  - All counts 0 $\rightarrow$ all return `zero_division_value`.
- **Exceptions**: `TypeError` if non-integer/boolean counts; `ValueError` if negative counts or `zero_division_value` not in $[0.0, 1.0]$.

#### `calculate_brier_score(predicted_probabilities: List[float], actual_outcomes: List[int]) -> float`
- **Formula**: $\frac{1}{N} \sum_{i=1}^{N} (p_i - y_i)^2$
- **Constraints**: $p_i \in [0.0, 1.0]$, $y_i \in \{0, 1\}$, $N \ge 1$, $\text{len}(p) == \text{len}(y)$.
- **Return**: Brier score in $[0.0, 1.0]$ rounded to 6 decimals.
- **Exceptions**: `TypeError` on non-list/non-numeric items; `ValueError` on empty lists, length mismatch, or values out of bounds/NaN/Inf.

#### `calculate_cyclomatic_density(cyclomatic_complexity: Union[int, float], lines_of_code: int) -> float`
- **Formula**: $\frac{\text{complexity}}{\text{LOC}} \times 100.0$
- **Constraints**: $\text{complexity} \ge 1.0$, $\text{LOC} \ge 1$. Rounded to 2 decimals.

#### `calculate_rolling_pass_rate(test_history: List[bool], window_size: Optional[int] = None) -> float`
- **Formula**: $\frac{\text{passed runs}}{\text{window size}} \times 100.0$
- **Constraints**: Non-empty list of booleans; `window_size` $\ge 1$ (if provided). Rounded to 2 decimals.

#### `calculate_shannon_entropy(probabilities: List[float]) -> float`
- **Formula**: $-\sum_{i} p_i \log_2(p_i)$ for $p_i > 0$.
- **Constraints**: $p_i \in [0.0, 1.0]$, $\sum p_i = 1.0 \pm 10^{-3}$.
- **Return**: Entropy in bits rounded to 4 decimals ($\ge 0.0$).

---

## 3. `QualityRiskScorer` ([risk_scorer.py](file:///Users/adithya/Desktop/AI%20assis%20UT%20gene%20and%20sftwr%20verification/src/quality_assessment/risk_scorer.py))
**Logic Archetype**: Composite Multi-Factor Penalty Modeling, Non-Linear Saturation Curves, Tier Classification.

### Key Components:
- **Weights**: Default: `coverage_deficit=0.35`, `complexity_penalty=0.25`, `churn_factor=0.20`, `smell_density=0.20`. Must sum to 1.0.
- **Complexity Penalty S-Curve**:
  - $cc \le 10$: Linear $[1, 10] \rightarrow [0.0, 20.0]$.
  - $10 < cc \le 25$: Linear $[10, 25] \rightarrow [20.0, 60.0]$.
  - $cc > 25$: Asymptotic saturation $60 + 40 \cdot (1 - e^{-0.05 \cdot (cc - 25)})$.
- **Severity Tiers (`RiskTier`)**:
  - $[0.0, 25.0)$: `LOW`
  - $[25.0, 50.0)$: `MEDIUM`
  - $[50.0, 75.0)$: `HIGH`
  - $[75.0, 100.0]$: `CRITICAL`
- **Methods**:
  - `calculate_coverage_deficit_penalty(coverage_pct)`
  - `calculate_complexity_penalty(cyclomatic_complexity)`
  - `calculate_composite_risk(coverage_pct, cyclomatic_complexity, churn_lines, smell_count, total_loc)`

---

## 4. `QualityGateTracker` ([gate_tracker.py](file:///Users/adithya/Desktop/AI%20assis%20UT%20gene%20and%20sftwr%20verification/src/quality_assessment/gate_tracker.py))
**Logic Archetype**: Finite-State Machine, Stateful Invariant Enforcement, Debounce/Hysteresis Recovery, Audit Trail.

### States (`GateState`):
`INITIALIZED`, `PASSED`, `WARNING`, `FAILED`, `BLOCKED`.

### State Machine Rules:
1. **Direct Transitions**:
   - `INITIALIZED` $\rightarrow$ `PASSED`, `WARNING`, `FAILED`, `BLOCKED`.
   - `PASSED` $\rightarrow$ `WARNING`, `FAILED`, `BLOCKED`, `PASSED`.
   - `WARNING` $\rightarrow$ `PASSED` (only after `recovery_debounce` passes), `FAILED`, `BLOCKED`.
   - `FAILED` $\rightarrow$ `PASSED` (only after `recovery_debounce` passes), `WARNING`, `BLOCKED`.
   - `BLOCKED` $\rightarrow$ `INITIALIZED` (manual unblock only).
2. **Hysteresis Debounce**:
   - If in `WARNING` or `FAILED`, recovering to `PASSED` requires $N$ consecutive evaluations with $\text{risk} \le \text{pass\_threshold}$ (`recovery_debounce`, default 2).
   - Any evaluation with $\text{risk} \ge \text{fail\_threshold}$ immediately triggers `FAILED` and resets pass counter to 0.
3. **Manual Override**:
   - `block_gate(reason)` immediately blocks the gate from any state except if transition is illegal.
   - `reset_to_initial(reason)` resets to `INITIALIZED`.

---

## 5. `QualityRuleEngine` ([rule_engine.py](file:///Users/adithya/Desktop/AI%20assis%20UT%20gene%20and%20sftwr%20verification/src/quality_assessment/rule_engine.py))
**Logic Archetype**: Declarative Rule Evaluation, Predicate Logic, Dynamic Dispatch, Combinators (`AND`, `OR`, `NOT`).

### Key Elements:
- **`RuleCondition`**: Dataclass holding `(field_name: str, operator: ComparisonOperator, expected_value: Any)`.
- **`ComparisonOperator`**: `gt`, `gte`, `lt`, `lte`, `eq`, `neq`, `in`, `not_in`.
- **`LogicalOperator`**: `AND`, `OR`, `NOT`.
- **Methods**:
  - `evaluate_condition(condition, payload, strict_missing=True) -> bool`
  - `evaluate_rule_group(conditions, payload, operator=AND, strict_missing=True) -> bool`
- **Exceptions**:
  - `RuleEvaluationError`: If field is missing (when `strict_missing=True`), operator is unknown, or uncomparable types (e.g. string vs int).
  - `ValueError`: Empty condition list, or `NOT` used with $\ne 1$ condition.
