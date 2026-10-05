"""Three-Way Mutation Benchmark Runner: Manual vs. AI-Only vs. Hybrid (AI + Human Review).

Runs the identical 241 mutant population against all three test suites to quantify
the exact ROI and fault detection rate of AI assistance combined with human verification.
"""

import ast
import json
import os
import subprocess
import sys
import time
from typing import Any, Dict

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from scripts.mutation_engine import ASTMutantGenerator, apply_mutation_to_source

TARGET_MODULES = [
    (
        "validator",
        "src/quality_assessment/validator.py",
        "tests/manual/test_validator.py",
        "tests/ai_generated/test_validator.py",
        "tests/hybrid/test_validator.py",
    ),
    (
        "metrics",
        "src/quality_assessment/metrics.py",
        "tests/manual/test_metrics.py",
        "tests/ai_generated/test_metrics.py",
        "tests/hybrid/test_metrics.py",
    ),
    (
        "risk_scorer",
        "src/quality_assessment/risk_scorer.py",
        "tests/manual/test_risk_scorer.py",
        "tests/ai_generated/test_risk_scorer.py",
        "tests/hybrid/test_risk_scorer.py",
    ),
    (
        "gate_tracker",
        "src/quality_assessment/gate_tracker.py",
        "tests/manual/test_gate_tracker.py",
        "tests/ai_generated/test_gate_tracker.py",
        "tests/hybrid/test_gate_tracker.py",
    ),
    (
        "rule_engine",
        "src/quality_assessment/rule_engine.py",
        "tests/manual/test_rule_engine.py",
        "tests/ai_generated/test_rule_engine.py",
        "tests/hybrid/test_rule_engine.py",
    ),
]


def run_pytest(test_file: str) -> bool:
    """Run pytest. Returns True if tests pass (mutant survived), False if failed (mutant killed)."""
    cmd = [sys.executable, "-m", "pytest", test_file, "-q", "--disable-warnings", "--maxfail=1"]
    env = os.environ.copy()
    env["PYTHONPATH"] = "src"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
    return proc.returncode == 0


def run_three_way_benchmark() -> Dict[str, Any]:
    print("=" * 80)
    print("Executing Phase 6: Three-Way Mutation Benchmark (Manual vs AI vs Hybrid)")
    print("=" * 80)

    start_time = time.time()
    results = {
        "phase": "Phase 6: Three-Way Hybrid Benchmark",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "summary": {
            "total_mutants": 0,
            "manual_killed": 0,
            "manual_score_pct": 0.0,
            "ai_killed": 0,
            "ai_score_pct": 0.0,
            "hybrid_killed": 0,
            "hybrid_score_pct": 0.0,
            "categories": {},
        },
        "modules": {},
    }

    category_stats = {}

    for mod_name, src_path, manual_test, ai_test, hybrid_test in TARGET_MODULES:
        print(f"\n[+] Evaluating module: '{mod_name}'")
        with open(src_path, "r") as f:
            original_source = f.read()

        generator = ASTMutantGenerator(original_source, mod_name)
        mutants = generator.generate()

        mod_res = {
            "total_mutants": len(mutants),
            "manual_killed": 0,
            "ai_killed": 0,
            "hybrid_killed": 0,
            "mutants_detail": [],
        }

        # Baseline check
        assert run_pytest(manual_test), f"Manual failed on base {mod_name}"
        assert run_pytest(ai_test), f"AI failed on base {mod_name}"
        assert run_pytest(hybrid_test), f"Hybrid failed on base {mod_name}"

        for idx, mutant in enumerate(mutants, 1):
            mutated_source = apply_mutation_to_source(original_source, mutant)
            try:
                ast.parse(mutated_source)
            except SyntaxError:
                continue

            with open(src_path, "w") as f:
                f.write(mutated_source)

            m_pass = run_pytest(manual_test)
            a_pass = run_pytest(ai_test)
            h_pass = run_pytest(hybrid_test)

            with open(src_path, "w") as f:
                f.write(original_source)

            m_killed = not m_pass
            a_killed = not a_pass
            h_killed = not h_pass

            if m_killed:
                mod_res["manual_killed"] += 1
            if a_killed:
                mod_res["ai_killed"] += 1
            if h_killed:
                mod_res["hybrid_killed"] += 1

            cat = mutant.category
            if cat not in category_stats:
                category_stats[cat] = {"total": 0, "manual_killed": 0, "ai_killed": 0, "hybrid_killed": 0}
            category_stats[cat]["total"] += 1
            if m_killed:
                category_stats[cat]["manual_killed"] += 1
            if a_killed:
                category_stats[cat]["ai_killed"] += 1
            if h_killed:
                category_stats[cat]["hybrid_killed"] += 1

            mod_res["mutants_detail"].append({
                "id": mutant.mutant_id,
                "line": mutant.line_number,
                "category": mutant.category,
                "description": mutant.description,
                "manual_status": "KILLED" if m_killed else "SURVIVED",
                "ai_status": "KILLED" if a_killed else "SURVIVED",
                "hybrid_status": "KILLED" if h_killed else "SURVIVED",
            })

        tot = mod_res["total_mutants"]
        mod_res["manual_score_pct"] = round((mod_res["manual_killed"] / tot) * 100.0, 2)
        mod_res["ai_score_pct"] = round((mod_res["ai_killed"] / tot) * 100.0, 2)
        mod_res["hybrid_score_pct"] = round((mod_res["hybrid_killed"] / tot) * 100.0, 2)

        print(f"  >>> {mod_name}: Manual = {mod_res['manual_score_pct']}% | AI = {mod_res['ai_score_pct']}% | Hybrid = {mod_res['hybrid_score_pct']}% ({mod_res['hybrid_killed']}/{tot})")

        results["modules"][f"{mod_name}.py"] = mod_res
        results["summary"]["total_mutants"] += tot
        results["summary"]["manual_killed"] += mod_res["manual_killed"]
        results["summary"]["ai_killed"] += mod_res["ai_killed"]
        results["summary"]["hybrid_killed"] += mod_res["hybrid_killed"]

    agg_tot = results["summary"]["total_mutants"]
    results["summary"]["manual_score_pct"] = round((results["summary"]["manual_killed"] / agg_tot) * 100.0, 2)
    results["summary"]["ai_score_pct"] = round((results["summary"]["ai_killed"] / agg_tot) * 100.0, 2)
    results["summary"]["hybrid_score_pct"] = round((results["summary"]["hybrid_killed"] / agg_tot) * 100.0, 2)

    for cat, stats in category_stats.items():
        c_tot = stats["total"]
        stats["manual_score_pct"] = round((stats["manual_killed"] / c_tot) * 100.0, 2) if c_tot else 0.0
        stats["ai_score_pct"] = round((stats["ai_killed"] / c_tot) * 100.0, 2) if c_tot else 0.0
        stats["hybrid_score_pct"] = round((stats["hybrid_killed"] / c_tot) * 100.0, 2) if c_tot else 0.0

    results["summary"]["categories"] = category_stats
    results["summary"]["total_duration_sec"] = round(time.time() - start_time, 2)

    with open("results/phase6_hybrid_results.json", "w") as f:
        json.dump(results, f, indent=2)

    print("\n" + "=" * 80)
    print("Three-Way Benchmark Complete!")
    print(f"Manual-Only Score:  {results['summary']['manual_score_pct']}% ({results['summary']['manual_killed']}/{agg_tot})")
    print(f"AI-Only Score:      {results['summary']['ai_score_pct']}% ({results['summary']['ai_killed']}/{agg_tot})")
    print(f"Hybrid (AI+Review): {results['summary']['hybrid_score_pct']}% ({results['summary']['hybrid_killed']}/{agg_tot})")
    print("=" * 80)

    return results


if __name__ == "__main__":
    run_three_way_benchmark()
