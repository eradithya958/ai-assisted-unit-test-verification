"""AST-Based Deterministic Mutation Testing Engine.

Generates standard mutation operators (Relational, Arithmetic, Logical, Constant, Boundary)
and executes test suites in isolated runner environments to measure exact mutation killing rates.
"""

import ast
import copy
import importlib
import os
import subprocess
import sys
import tempfile
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class MutationCategory(str, Enum):
    """Standard Software Mutation Testing Operator Categories."""
    ROR = "Relational Operator Replacement"  # <, <=, >, >=, ==, !=
    COR = "Conditional Operator Replacement"  # and, or, not
    AOR = "Arithmetic Operator Replacement"  # +, -, *, /, **
    CRP = "Constant Replacement"  # Literals, thresholds, numbers, strings
    LCR = "Logical Connector / Membership"  # in, not in, is, is not
    BVA = "Boundary Shift"  # +1, -1 on boundary constants


@dataclass
class Mutant:
    """Representation of an individual code mutation."""
    mutant_id: int
    module_name: str
    category: str
    line_number: int
    original_code: str
    mutated_code: str
    description: str


class ASTMutantGenerator(ast.NodeVisitor):
    """Walks the AST and produces all candidate single-point mutations."""

    def __init__(self, source_code: str, module_name: str):
        self.source_code = source_code
        self.module_name = module_name
        self.lines = source_code.splitlines()
        self.mutants: List[Mutant] = []
        self._next_id = 1

    def generate(self) -> List[Mutant]:
        tree = ast.parse(self.source_code)
        self.visit(tree)
        return self.mutants

    def _get_line_text(self, lineno: int) -> str:
        if 1 <= lineno <= len(self.lines):
            return self.lines[lineno - 1].strip()
        return ""

    def visit_Compare(self, node: ast.Compare):
        lineno = node.lineno
        orig_line = self._get_line_text(lineno)

        op_map = {
            ast.Lt: (ast.LtE, "<", "<=", MutationCategory.ROR),
            ast.LtE: (ast.Lt, "<=", "<", MutationCategory.ROR),
            ast.Gt: (ast.GtE, ">", ">=", MutationCategory.ROR),
            ast.GtE: (ast.Gt, ">=", ">", MutationCategory.ROR),
            ast.Eq: (ast.NotEq, "==", "!=", MutationCategory.ROR),
            ast.NotEq: (ast.Eq, "!=", "==", MutationCategory.ROR),
            ast.In: (ast.NotIn, "in", "not in", MutationCategory.LCR),
            ast.NotIn: (ast.In, "not in", "in", MutationCategory.LCR),
        }

        for idx, op in enumerate(node.ops):
            op_type = type(op)
            if op_type in op_map:
                mut_op_class, orig_sym, mut_sym, cat = op_map[op_type]
                desc = f"Changed '{orig_sym}' to '{mut_sym}' at line {lineno}"
                mut_line = orig_line.replace(orig_sym, mut_sym, 1)
                self.mutants.append(
                    Mutant(
                        mutant_id=self._next_id,
                        module_name=self.module_name,
                        category=cat.value,
                        line_number=lineno,
                        original_code=orig_line,
                        mutated_code=mut_line,
                        description=desc,
                    )
                )
                self._next_id += 1

        self.generic_visit(node)

    def visit_BinOp(self, node: ast.BinOp):
        lineno = node.lineno
        orig_line = self._get_line_text(lineno)

        bin_map = {
            ast.Add: (ast.Sub, "+", "-", MutationCategory.AOR),
            ast.Sub: (ast.Add, "-", "+", MutationCategory.AOR),
            ast.Mult: (ast.Div, "*", "/", MutationCategory.AOR),
            ast.Div: (ast.Mult, "/", "*", MutationCategory.AOR),
        }

        op_type = type(node.op)
        if op_type in bin_map:
            mut_class, orig_sym, mut_sym, cat = bin_map[op_type]
            if orig_sym in orig_line:
                desc = f"Changed arithmetic '{orig_sym}' to '{mut_sym}' at line {lineno}"
                mut_line = orig_line.replace(orig_sym, mut_sym, 1)
                self.mutants.append(
                    Mutant(
                        mutant_id=self._next_id,
                        module_name=self.module_name,
                        category=cat.value,
                        line_number=lineno,
                        original_code=orig_line,
                        mutated_code=mut_line,
                        description=desc,
                    )
                )
                self._next_id += 1

        self.generic_visit(node)

    def visit_BoolOp(self, node: ast.BoolOp):
        lineno = node.lineno
        orig_line = self._get_line_text(lineno)

        bool_map = {
            ast.And: (ast.Or, " and ", " or ", MutationCategory.COR),
            ast.Or: (ast.And, " or ", " and ", MutationCategory.COR),
        }

        op_type = type(node.op)
        if op_type in bool_map:
            mut_class, orig_sym, mut_sym, cat = bool_map[op_type]
            if orig_sym in orig_line:
                desc = f"Replaced boolean '{orig_sym.strip()}' with '{mut_sym.strip()}' at line {lineno}"
                mut_line = orig_line.replace(orig_sym, mut_sym, 1)
                self.mutants.append(
                    Mutant(
                        mutant_id=self._next_id,
                        module_name=self.module_name,
                        category=cat.value,
                        line_number=lineno,
                        original_code=orig_line,
                        mutated_code=mut_line,
                        description=desc,
                    )
                )
                self._next_id += 1

        self.generic_visit(node)

    def visit_Constant(self, node: ast.Constant):
        lineno = getattr(node, "lineno", 0)
        if lineno == 0:
            return

        orig_line = self._get_line_text(lineno)
        val = node.value

        # Mutate booleans
        if isinstance(val, bool):
            orig_sym = "True" if val else "False"
            mut_sym = "False" if val else "True"
            if orig_sym in orig_line:
                desc = f"Swapped boolean constant '{orig_sym}' to '{mut_sym}' at line {lineno}"
                mut_line = orig_line.replace(orig_sym, mut_sym, 1)
                self.mutants.append(
                    Mutant(
                        mutant_id=self._next_id,
                        module_name=self.module_name,
                        category=MutationCategory.CRP.value,
                        line_number=lineno,
                        original_code=orig_line,
                        mutated_code=mut_line,
                        description=desc,
                    )
                )
                self._next_id += 1

        # Mutate numeric boundaries (0.0, 1.0, 100.0, 25.0, 30.0, 70.0)
        elif isinstance(val, (int, float)) and not isinstance(val, bool):
            if val in (0.0, 0, 1.0, 1, 10.0, 25.0, 30.0, 70.0, 100.0):
                orig_sym = str(val)
                # Shift boundary
                mut_val = val + (1.0 if isinstance(val, float) else 1)
                mut_sym = str(mut_val)
                if orig_sym in orig_line:
                    desc = f"Shifted constant '{orig_sym}' to '{mut_sym}' at line {lineno}"
                    mut_line = orig_line.replace(orig_sym, mut_sym, 1)
                    self.mutants.append(
                        Mutant(
                            mutant_id=self._next_id,
                            module_name=self.module_name,
                            category=MutationCategory.BVA.value,
                            line_number=lineno,
                            original_code=orig_line,
                            mutated_code=mut_line,
                            description=desc,
                        )
                    )
                    self._next_id += 1

        self.generic_visit(node)


def apply_mutation_to_source(source_code: str, mutant: Mutant) -> str:
    """Apply the mutant change to the source code string."""
    lines = source_code.splitlines()
    target_idx = mutant.line_number - 1
    if 0 <= target_idx < len(lines):
        orig_line = lines[target_idx]
        if mutant.original_code in orig_line or orig_line.strip() == mutant.original_code:
            # Replace exact substring
            indent = orig_line[: len(orig_line) - len(orig_line.lstrip())]
            lines[target_idx] = indent + mutant.mutated_code
            return "\n".join(lines)
    return source_code
