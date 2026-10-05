"""Mutation Testing Orchestrator.

Executes a side-by-side mutation testing benchmark comparing Manual vs. AI test suites
against identical mutant populations across all 5 target modules.
"""

import ast
import json
import os
import shutil
import subprocess
import sys
import time
from typing import Any, Dict, List

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from scripts.mutation_engine import ASTMutantGenerator, Mutant, apply_mutation_to_source

TARGET_MODULES = [
    ("validator", "src/quality_assessment/validator.py", "tests/manual/test_validator.py", "tests/ai_generated/test_validator.py"),
    ("metrics", "src/quality_assessment/metrics.py", "tests/manual/test_metrics.py", "tests/ai_generated/test_metrics.py"),
    ("risk_scorer", "src/quality_assessment/risk_scorer.py", "tests/manual/test_risk_scorer.py", "tests/ai_generated/test_risk_scorer.py"),
    ("gate_tracker", "src/quality_assessment/gate_tracker.py", "tests/manual/test_gate_tracker.py", "tests/ai_generated/test_gate_tracker.py"),
    ("rule_engine", "src/quality_assessment/rule_engine.py", "tests/manual/test_rule_engine.py", "tests/ai_generated/test_rule_engine.py"),
]


def run_pytest_on_test_file(test_file: str) -> bool:
    """Run pytest on a single test file. Returns True if tests passed (mutant survived), False if failed (mutant killed)."""
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        test_file,
        "-q",
        "--disable-warnings",
        "--maxfail=1",
    ]
    env = os.environ.copy()
    env["PYTHONPATH"] = "src"
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
    return proc.returncode == 0


def run_mutation_benchmark() -> Dict[str, Any]:
    """Run comprehensive mutation benchmark across all modules."""
    print("=" * 80)
    print("Executing Phase 4: Mutation Testing Benchmark (Manual vs AI-Generated)")
    print("=" * 80)

    start_total_time = time.time()
    results: Dict[str, Any] = {
        "phase": "Phase 4: Mutation Testing Benchmark",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "summary": {
            "total_mutants": 0,
            "manual_killed": 0,
            "manual_survived": 0,
            "manual_mutation_score_pct": 0.0,
            "ai_killed": 0,
            "ai_survived": 0,
            "ai_mutation_score_pct": 0.0,
            "categories": {},
        },
        "modules": {},
    }

    category_stats = {}

    for mod_name, src_path, manual_test, ai_test in TARGET_MODULES:
        print(f"\n[+] Analyzing module: '{mod_name}' ({src_path})")
        with open(src_path, "r") as f:
            original_source = f.read()

        generator = ASTMutantGenerator(original_source, mod_name)
        mutants = generator.generate()
        print(f"  - Generated {len(mutants)} AST mutants")

        mod_results = {
            "source_file": src_path,
            "total_mutants": len(mutants),
            "manual_killed": 0,
            "manual_survived": 0,
            "manual_score_pct": 0.0,
            "ai_killed": 0,
            "ai_survived": 0,
            "ai_score_pct": 0.0,
            "mutants_detail": [],
        }

        # Baseline check before mutation
        assert run_pytest_on_test_file(manual_test), f"Manual suite failed on unmutated {mod_name}"
        assert run_pytest_on_test_file(ai_test), f"AI suite failed on unmutated {mod_name}"

        for idx, mutant in enumerate(mutants, 1):
            mutated_source = apply_mutation_to_source(original_source, mutant)
            
            # Skip if mutation was no-op or syntactically invalid
            try:
                ast.parse(mutated_source)
            except SyntaxError:
                continue

            # Write mutated source
            with open(src_path, "w") as f:
                f.write(mutated_source)

            # Test against manual suite
            manual_passed = run_pytest_on_test_file(manual_test)
            manual_status = "SURVIVED" if manual_passed else "KILLED"
            if not manual_passed:
                mod_results["manual_killed"] += 1
            else:
                mod_results["manual_survived"] += 1

            # Test against AI suite
            ai_passed = run_pytest_on_test_file(ai_test)
            ai_status = "SURVIVED" if ai_passed else "KILLED"
            if not ai_passed:
                mod_results["ai_killed"] += 1
            else:
                mod_results["ai_survived"] += 1

            # Restore original immediately
            with open(src_path, "w") as f:
                f.write(original_source)

            cat = mutant.category
            if cat not in category_stats:
                category_stats[cat] = {"total": 0, "manual_killed": 0, "ai_killed": 0}
            category_stats[cat]["total"] += 1
            if not manual_passed:
                category_stats[cat]["manual_killed"] += 1
            if not ai_passed:
                category_stats[cat]["ai_killed"] += 1

            mod_results["mutants_detail"].append({
                "id": mutant.mutant_id,
                "line": mutant.line_number,
                "category": mutant.category,
                "description": mutant.description,
                "manual_status": manual_status,
                "ai_status": ai_status,
            })

            if idx % 10 == 0 or idx == len(mutants):
                print(f"  ... Evaluated {idx}/{len(mutants)} mutants")

        # Compute module scores
        tot = mod_results["total_mutants"]
        if tot > 0:
            mod_results["manual_score_pct"] = round((mod_results["manual_killed"] / tot) * 100.0, 2)
            mod_results["ai_score_pct"] = round((mod_results["ai_killed"] / tot) * 100.0, 2)

        print(f"  >>> Score for {mod_name}: Manual = {mod_results['manual_score_pct']}% ({mod_results['manual_killed']}/{tot}) | AI = {mod_results['ai_score_pct']}% ({mod_results['ai_killed']}/{tot})")

        results["modules"][f"{mod_name}.py"] = mod_results
        results["summary"]["total_mutants"] += tot
        results["summary"]["manual_killed"] += mod_results["manual_killed"]
        results["summary"]["manual_survived"] += mod_results["manual_survived"]
        results["summary"]["ai_killed"] += mod_results["ai_killed"]
        results["summary"]["ai_survived"] += mod_results["ai_survived"]

    # Compute aggregate scores
    agg_tot = results["summary"]["total_mutants"]
    if agg_tot > 0:
        results["summary"]["manual_mutation_score_pct"] = round(
            (results["summary"]["manual_killed"] / agg_tot) * 100.0, 2
        )
        results["summary"]["ai_mutation_score_pct"] = round(
            (results["summary"]["ai_killed"] / agg_tot) * 100.0, 2
        )

    # Category breakdowns
    for cat, stats in category_stats.items():
        c_tot = stats["total"]
        stats["manual_score_pct"] = round((stats["manual_killed"] / c_tot) * 100.0, 2) if c_tot else 0.0
        stats["ai_score_pct"] = round((stats["ai_killed"] / c_tot) * 100.0, 2) if c_tot else 0.0

    results["summary"]["categories"] = category_stats
    results["summary"]["total_execution_time_sec"] = round(time.time() - start_total_time, 2)

    # Save results JSON
    os.makedirs("results", exist_ok=True)
    with open("results/phase4_mutation_results.json", "w") as f:
        json.dump(results, f, indent=2)

    print("\n" + "=" * 80)
    print(f"Phase 4 Complete in {results['summary']['total_execution_time_sec']}s!")
    print(f"Overall Manual Mutation Score: {results['summary']['manual_mutation_score_pct']}% ({results['summary']['manual_killed']}/{agg_tot})")
    print(f"Overall AI Mutation Score:     {results['summary']['ai_mutation_score_pct']}% ({results['summary']['ai_killed']}/{agg_tot})")
    print("=" * 80)

    return results


if __name__ == "__main__":
    run_mutation_benchmark()
