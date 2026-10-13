"""Offline AST/schedule contract only; never runs a receiver."""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

from f1_prefix_reproduce import CALL_LIMIT, FRAME_COUNT, rewrite


def test_frozen_prefix_ast_and_schedule() -> None:
    original = Path(__file__).resolve().parents[1] / \
        "cstate_necessity_stageB_20260928/f1_run_stage_b.py"
    tree, audit = rewrite(original.read_bytes())
    compile(tree, str(original), "exec")
    assert audit["maximum_attempts"] == CALL_LIMIT == 409
    assert audit["frames"] == FRAME_COUNT == 198
    assert audit["population_seal_written"] is False
    assert len(audit["patches"]) == 5
    function = next(node for node in tree.body if isinstance(node, ast.FunctionDef)
                    and node.name == "run")
    loop = next(node for node in ast.walk(function) if isinstance(node, ast.For)
                and node.lineno == 214)
    assert ast.unparse(loop.iter) == "enumerate(bound['selected'][:198])"
    completion = next(node.value for node in ast.walk(function)
                      if isinstance(node, ast.Expr) and node.lineno == 385)
    assert isinstance(completion, ast.Call)
    assert ast.unparse(completion.args[0]) == "out / 'diagnostic_prefix.json'"
    assert sum(len(("B", "Cref", "Cfast")) if index % 16 == 0 else 2
               for index in range(FRAME_COUNT)) == CALL_LIMIT


def test_source_mutation_fails_closed() -> None:
    original = Path(__file__).resolve().parents[1] / \
        "cstate_necessity_stageB_20260928/f1_run_stage_b.py"
    with pytest.raises(ValueError, match="SHA differs"):
        rewrite(original.read_bytes() + b"\n")
