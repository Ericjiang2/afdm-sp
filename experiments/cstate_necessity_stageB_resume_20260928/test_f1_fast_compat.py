"""Synthetic conservative F1 candidate tests; no observed-frame calls."""
from __future__ import annotations

import ast
import os
from pathlib import Path
import sys

import numpy as np
import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BASELINE = Path(os.environ.get("STAGE_B_BASELINE",
                               ROOT / "experiments/sp_afdm_frozen_20260920"))
STAGE_A = ROOT / "experiments/cstate_necessity_stageA_20260928"
STAGE_B = ROOT / "experiments/cstate_necessity_stageB_20260928"
sys.path[:0] = [str(BASELINE / "src"), str(STAGE_A), str(STAGE_B), str(HERE)]

from f1 import PhysicalF1, response  # noqa: E402
from f1_fast_compat import PhysicalF1FastCompat  # noqa: E402
from physical import daft  # noqa: E402
from profile_f1 import assert_equivalent  # noqa: E402


def pair(n: int, lmax: int, y: np.ndarray, pilot: np.ndarray, sigma2: float) -> None:
    c1 = 5 / (2 * n)
    c2 = (np.sqrt(2) - 1) / (2 * n * n)
    old = PhysicalF1(n, c1, c2, lmax).acquire(y, pilot, sigma2)
    new = PhysicalF1FastCompat(n, c1, c2, lmax).acquire(y, pilot, sigma2)
    assert_equivalent(old, new)
    assert PhysicalF1FastCompat._coordinate is PhysicalF1._coordinate
    assert new["acquisition_seconds"] >= new["bank_build_seconds"] >= 0


def test_native_handoff_only_class_and_entrypoint_change() -> None:
    original = ast.parse((STAGE_A / "native_f1.py").read_text())
    candidate = ast.parse((HERE / "f1_fast_compat_native.py").read_text())
    old = next(node for node in original.body
               if isinstance(node, ast.FunctionDef) and node.name == "receive_f1")
    new = next(node for node in candidate.body
               if isinstance(node, ast.FunctionDef) and node.name == "receive_f1_fast_compat")
    class Normalize(ast.NodeTransformer):
        def visit_Name(self, node: ast.Name) -> ast.AST:
            if node.id == "PhysicalF1FastCompat":
                node.id = "PhysicalF1"
            return node
    assert ast.dump(old.args) == ast.dump(new.args)
    assert [ast.dump(node) for node in old.body] == \
        [ast.dump(Normalize().visit(node)) for node in new.body]


def test_synthetic_random_and_same_delay_cpp() -> None:
    for seed in (928, 929, 930):
        rng = np.random.default_rng(seed)
        n = 31
        pair(n, 3, rng.normal(size=n) + 1j * rng.normal(size=n),
             rng.normal(size=n) + 1j * rng.normal(size=n), .2)
    n = 63
    c1 = 5 / (2 * n)
    c2 = (np.sqrt(2) - 1) / (2 * n * n)
    rng = np.random.default_rng(931)
    pilot = rng.normal(size=n) + 1j * rng.normal(size=n)
    time_pilot = daft(pilot, c1, c2, True)
    z = (response(time_pilot, n-1, -.8, c1)
         + .7 * response(time_pilot, n-1, 1.2, c1)
         + .2 * response(time_pilot, 4, .25, c1))
    pair(n, n-1, daft(z, c1, c2), pilot, .05)


def test_zero_pilot_rejected() -> None:
    n = 31
    c1 = 5 / (2 * n)
    c2 = (np.sqrt(2) - 1) / (2 * n * n)
    with pytest.raises(ValueError, match="zero/nonfinite known pilot energy"):
        PhysicalF1FastCompat(n, c1, c2, 3).acquire(np.zeros(n), np.zeros(n), .1)
