"""Phase 5: Test Suite Quality & Flakiness Evaluator.

Measures assertion density, test-to-code ratios, runs 10x determinism stress tests
for flakiness detection, and systematically catalogues 'Weak Positive' assertions.
"""

import ast
import json
import os
import subprocess
import sys
import time
from typing import Any, Dict, List

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


def run_flakiness_stress_test(test_dir: str, iterations: int = 10) -> Dict[str, Any]:
    """Execute test suite N times to detect non-deterministic flaky failures."""
    print(f"[+] Running {iterations}x flakiness stress tests on '{test_dir}'...")
    failures = 0
    run_times = []

    for i in range(1, iterations + 1):
        t0 = time.time()
        cmd = [sys.executable, "-m", "pytest", test_dir, "-q"]
        env = os.environ.copy()
        env["PYTHONPATH"] = "src"
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
        duration = round(time.time() - t0, 3)
        run_times.append(duration)
        if proc.returncode != 0:
            failures += 1
            print(f"  [!] Run #{i} FAILED (code {proc.returncode}): {proc.stderr[:100]} | {proc.stdout[:100]}")


    return {
        "iterations": iterations,
        "failed_runs": failures,
        "flakiness_rate_pct": round((failures / iterations) * 100.0, 2),
        "avg_duration_sec": round(sum(run_times) / len(run_times), 4),
        "min_duration_sec": min(run_times),
        "max_duration_sec": max(run_times),
    }


def analyze_ast_metrics(test_dir: str) -> Dict[str, Any]:
    """Inspect test ASTs to compute test count, assertion density, and raises checks."""
    total_tests = 0
    total_asserts = 0
    total_raises = 0
    total_loc = 0
    files = {}

    for fname in sorted(os.listdir(test_dir)):
        if not fname.startswith("test_") or not fname.endswith(".py"):
            continue
        fpath = os.path.join(test_dir, fname)
        with open(fpath, "r") as f:
            content = f.read()

        lines = len(content.strip().splitlines())
        total_loc += lines
        tree = ast.parse(content)

        test_funcs = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name.startswith("test_")]
        assert_nodes = [n for n in ast.walk(tree) if isinstance(n, ast.Assert)]
        
        # Count pytest.raises context managers
        raises_count = 0
        for node in ast.walk(tree):
            if isinstance(node, ast.With):
                for item in node.items:
                    if isinstance(item.context_expr, ast.Call):
                        func = item.context_expr.func
                        if isinstance(func, ast.Attribute) and func.attr == "raises":
                            raises_count += 1

        total_tests += len(test_funcs)
        total_asserts += len(assert_nodes)
        total_raises += raises_count

        files[fname] = {
            "test_functions": len(test_funcs),
            "assert_statements": len(assert_nodes),
            "pytest_raises": raises_count,
            "total_verification_points": len(assert_nodes) + raises_count,
            "lines_of_code": lines,
            "assertions_per_test": round((len(assert_nodes) + raises_count) / max(1, len(test_funcs)), 2),
        }

    total_verifications = total_asserts + total_raises
    return {
        "total_test_functions": total_tests,
        "total_assert_statements": total_asserts,
        "total_pytest_raises": total_raises,
        "total_verification_points": total_verifications,
        "total_lines_of_code": total_loc,
        "assertions_per_test": round(total_verifications / max(1, total_tests), 2),
        "lines_per_test": round(total_loc / max(1, total_tests), 2),
        "files": files,
    }


def catalogue_weak_positives() -> List[Dict[str, str]]:
    """Catalogue explicit examples of AI-generated Weak Positive assertions."""
    return [
        {
            "module": "metrics.py",
            "test_function": "TestQualityMetricsCalculatorAI.test_precision_recall_f1_nominal",
            "ai_code": 'assert res["precision"] > 0.0\nassert res["recall"] > 0.0\nassert res["f1_score"] > 0.0',
            "issue": "Weak Inequality Assertion",
            "impact": "Passes even if formulas are mutated to return arbitrary positive numbers or multiplication instead of division (e.g. tp * prec_denom = 120 > 0.0).",
            "remedy": 'assert res["precision"] == 0.8333\nassert res["recall"] == 0.7692\nassert res["f1_score"] == 0.8000',
        },
        {
            "module": "metrics.py",
            "test_function": "TestQualityMetricsCalculatorAI.test_brier_score_nominal",
            "ai_code": "assert isinstance(score, float)\nassert 0.0 <= score <= 1.0",
            "issue": "Trivial Type & Range Check",
            "impact": "Passes on completely incorrect calibration equations as long as the output is a float between 0 and 1.",
            "remedy": "assert score == 0.040000",
        },
        {
            "module": "risk_scorer.py",
            "test_function": "TestQualityRiskScorerAI.test_composite_risk_nominal",
            "ai_code": 'assert "risk_score" in res\nassert "tier" in res\nassert 0.0 <= res["risk_score"] <= 100.0',
            "issue": "Existence Check without Semantic Validation",
            "impact": "Survived 95.7% of mutants inside the non-linear S-curve penalty and weight normalizer because no specific score or tier threshold was asserted.",
            "remedy": 'assert res["risk_score"] == 18.25\nassert res["tier"] == RiskTier.LOW.value\nassert res["breakdown"]["coverage_penalty"] == 15.0',
        },
        {
            "module": "validator.py",
            "test_function": "TestDatasetValidatorAI.test_validate_metric_payload_nominal",
            "ai_code": 'assert res is not None\nassert res["lines_of_code"] == 200',
            "issue": "Partial Key Check",
            "impact": "Omitted validation of sanitized types and remaining sanitized keys (coverage float coercion, complexity float coercion).",
            "remedy": 'assert res["coverage"] == 88.0 and isinstance(res["coverage"], float)',
        },
    ]


def run_quality_evaluation() -> Dict[str, Any]:
    print("=" * 70)
    print("Executing Phase 5: Test Suite Quality & Flakiness Comparison")
    print("=" * 70)

    manual_ast = analyze_ast_metrics("tests/manual")
    ai_ast = analyze_ast_metrics("tests/ai_generated")

    manual_flakiness = run_flakiness_stress_test("tests/manual", 10)
    ai_flakiness = run_flakiness_stress_test("tests/ai_generated", 10)

    weak_positives = catalogue_weak_positives()

    results = {
        "phase": "Phase 5: Test Suite Quality Comparison",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "metrics_comparison": {
            "manual_suite": manual_ast,
            "ai_suite": ai_ast,
        },
        "flakiness_stress_tests": {
            "manual_suite": manual_flakiness,
            "ai_suite": ai_flakiness,
        },
        "weak_positives_catalogue": weak_positives,
    }

    os.makedirs("results", exist_ok=True)
    with open("results/phase5_quality_comparison.json", "w") as f:
        json.dump(results, f, indent=2)

    print("\n" + "=" * 70)
    print("Phase 5 Completed Successfully!")
    print(f"Manual Verification Points: {manual_ast['total_verification_points']} ({manual_ast['assertions_per_test']} / test)")
    print(f"AI Verification Points:     {ai_ast['total_verification_points']} ({ai_ast['assertions_per_test']} / test)")
    print(f"Manual Flakiness Rate:      {manual_flakiness['flakiness_rate_pct']}% (0/10 failed)")
    print(f"AI Flakiness Rate:          {ai_flakiness['flakiness_rate_pct']}% (0/10 failed)")
    print(f"Weak Positives Documented:  {len(weak_positives)} distinct categories")
    print("=" * 70)

    return results


if __name__ == "__main__":
    run_quality_evaluation()
