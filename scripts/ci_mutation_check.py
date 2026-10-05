"""Lightweight CI Mutation Testing Regression Check.

Runs a fast, representative mutation sampling across all 5 modules suitable for
fast GitHub Actions CI workflows (<10 seconds).
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
    ("validator", "src/quality_assessment/validator.py", "tests/hybrid/test_validator.py"),
    ("metrics", "src/quality_assessment/metrics.py", "tests/hybrid/test_metrics.py"),
    ("risk_scorer", "src/quality_assessment/risk_scorer.py", "tests/hybrid/test_risk_scorer.py"),
    ("gate_tracker", "src/quality_assessment/gate_tracker.py", "tests/hybrid/test_gate_tracker.py"),
    ("rule_engine", "src/quality_assessment/rule_engine.py", "tests/hybrid/test_rule_engine.py"),
]


def run_test(test_file: str) -> bool:
    cmd = [sys.executable, "-m", "pytest", test_file, "-q", "--disable-warnings", "--maxfail=1"]
    env = os.environ.copy()
    env["PYTHONPATH"] = "src"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
    return proc.returncode == 0


def run_ci_check(sample_size_per_module: int = 5) -> int:
    print("=" * 70)
    print(f"Executing CI Mutation Regression Check (Sample: {sample_size_per_module} mutants/module)")
    print("=" * 70)

    total_mutants = 0
    total_killed = 0

    for mod_name, src_path, test_file in TARGET_MODULES:
        with open(src_path, "r") as f:
            original = f.read()

        generator = ASTMutantGenerator(original, mod_name)
        all_mutants = generator.generate()
        # Take evenly spaced sample
        step = max(1, len(all_mutants) // sample_size_per_module)
        sample = all_mutants[::step][:sample_size_per_module]

        m_killed = 0
        for m in sample:
            mutated = apply_mutation_to_source(original, m)
            with open(src_path, "w") as f:
                f.write(mutated)
            passed = run_test(test_file)
            with open(src_path, "w") as f:
                f.write(original)
            if not passed:
                m_killed += 1

        total_mutants += len(sample)
        total_killed += m_killed
        score = (m_killed / len(sample)) * 100.0 if sample else 0.0
        print(f"  - {mod_name:12s}: {m_killed}/{len(sample)} killed ({score:.1f}%)")

    overall_score = (total_killed / total_mutants) * 100.0 if total_mutants else 0.0
    print("=" * 70)
    print(f"CI Mutation Score: {overall_score:.1f}% ({total_killed}/{total_mutants} killed)")
    print("=" * 70)

    # Threshold: CI passes if mutation score >= 40% on hybrid suite
    if overall_score < 40.0:
        print(f"ERROR: Mutation score {overall_score:.1f}% below minimum CI threshold 40.0%")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(run_ci_check())
