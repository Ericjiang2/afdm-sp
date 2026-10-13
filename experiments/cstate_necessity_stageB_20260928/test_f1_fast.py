"""Synthetic F1-fast equivalence only; no receiver or observed frames."""
from __future__ import annotations

import ast
import os
from pathlib import Path
import sys
import unittest

import numpy as np


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BASELINE = Path(os.environ.get('STAGE_B_BASELINE',
    ROOT / 'experiments/sp_afdm_frozen_20260920'))
STAGE_A = ROOT / 'experiments/cstate_necessity_stageA_20260928'
sys.path[:0] = [str(BASELINE / 'src'), str(STAGE_A), str(HERE)]

from f1 import PhysicalF1, response  # noqa: E402
from f1_fast import PhysicalF1Fast  # noqa: E402
from physical import daft  # noqa: E402
from profile_f1 import assert_equivalent  # noqa: E402


class TestF1Fast(unittest.TestCase):
    def test_native_handoff_is_only_class_substitution(self) -> None:
        original = ast.parse((STAGE_A / 'native_f1.py').read_text())
        fast = ast.parse((HERE / 'f1_fast_native.py').read_text())
        old_function = next(node for node in original.body
                            if isinstance(node, ast.FunctionDef) and node.name == 'receive_f1')
        fast_function = next(node for node in fast.body
                             if isinstance(node, ast.FunctionDef) and node.name == 'receive_f1_fast')

        class Normalize(ast.NodeTransformer):
            def visit_Name(self, node: ast.Name) -> ast.AST:
                if node.id == 'PhysicalF1Fast':
                    node.id = 'PhysicalF1'
                return node

        self.assertEqual(ast.dump(old_function.args), ast.dump(fast_function.args))
        self.assertEqual([ast.dump(node) for node in old_function.body],
                         [ast.dump(Normalize().visit(node)) for node in fast_function.body])

    def pair(self, n: int, lmax: int, y: np.ndarray, pilot: np.ndarray,
             sigma2: float) -> None:
        c1 = 5 / (2 * n)
        c2 = (np.sqrt(2) - 1) / (2 * n * n)
        old = PhysicalF1(n, c1, c2, lmax).acquire(y, pilot, sigma2)
        fast_receiver = PhysicalF1Fast(n, c1, c2, lmax)
        new = fast_receiver.acquire(y, pilot, sigma2)
        assert_equivalent(old, new)
        time_pilot = daft(pilot, c1, c2, True)
        for delay, nu in ((0, -2.1), (min(3, lmax), .37), (lmax, 2.81)):
            np.testing.assert_allclose(fast_receiver._response(delay, nu),
                response(time_pilot, delay, nu, c1), atol=2e-10, rtol=0)

    def test_random_observed_shape(self) -> None:
        for seed in (928, 929, 930):
            rng = np.random.default_rng(seed)
            n = 31
            pilot = rng.normal(size=n) + 1j * rng.normal(size=n)
            y = rng.normal(size=n) + 1j * rng.normal(size=n)
            self.pair(n, 3, y, pilot, .2)

    def test_same_delay_and_cpp_boundary(self) -> None:
        n = 63
        c1 = 5 / (2 * n)
        c2 = (np.sqrt(2) - 1) / (2 * n * n)
        rng = np.random.default_rng(931)
        pilot = rng.normal(size=n) + 1j * rng.normal(size=n)
        time_pilot = daft(pilot, c1, c2, True)
        z = (response(time_pilot, n-1, -.8, c1)
             + .7 * response(time_pilot, n-1, 1.2, c1)
             + .2 * response(time_pilot, 4, .25, c1))
        self.pair(n, n-1, daft(z, c1, c2), pilot, .05)

    def test_invalid_input_boundary(self) -> None:
        n = 31
        c1 = 5 / (2 * n)
        c2 = (np.sqrt(2) - 1) / (2 * n * n)
        for receiver in (PhysicalF1, PhysicalF1Fast):
            with self.assertRaisesRegex(ValueError, 'zero/nonfinite known pilot energy'):
                receiver(n, c1, c2, 3).acquire(np.zeros(n), np.zeros(n), .1)


if __name__ == '__main__':
    unittest.main()
