"""Cached-state and numerical diagnostic contracts, not campaign evidence."""
import tempfile
import unittest
from pathlib import Path

import numpy as np

from . import supplement_a01_cache as cache
from .supplement_a01_diagnostics import fixed_design_diagnostics
from .supplement_a01 import snapshot_from_result
from .test_supplement_h01 import toy_frame, toy_result
from .e1_ldpc import build_code


class CachedStateTests(unittest.TestCase):
    def test_saved_state_is_used_and_changed_truth_or_nonfinite_state_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            code = build_code(n=24, d_v=3, d_c=6, cache_dir=tmp)
            frame = toy_frame(code)
            snap = snapshot_from_result(frame, toy_result(frame))
            proof = cache.validate_snapshot(snap, frame, code)
            self.assertTrue(proof['exact_exogenous_arrays'])
            snap['y'][0] += 1e-6
            with self.assertRaisesRegex(ValueError, 'cached observation'):
                cache.validate_snapshot(snap, frame, code)
            snap = snapshot_from_result(frame, toy_result(frame))
            snap['data'][0] *= -1
            with self.assertRaisesRegex(ValueError, 'data'):
                cache.validate_snapshot(snap, frame, code)
            snap = snapshot_from_result(frame, toy_result(frame))
            snap['x_soft'][0] = np.nan
            with self.assertRaisesRegex(ValueError, 'finite'):
                cache.validate_snapshot(snap, frame, code)

    def test_bound_file_rejects_tamper(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'snapshot.npz'
            path.write_bytes(b'original')
            binding = cache.file_binding(path)
            self.assertEqual(cache.checked_path(binding), path.resolve())
            path.write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError, 'hash'):
                cache.checked_path(binding)


class FixedDesignDiagnosticsTests(unittest.TestCase):
    def test_variance_and_projection_are_explicit_fixed_design_quantities(self):
        A = np.diag([2., 1., 4.]).astype(complex)
        W = np.eye(3, dtype=complex)[:, :1]
        truth = np.array([1., 2., 0.], complex)
        free = fixed_design_diagnostics(A, W, np.eye(3), truth, truth,
                                        'none', .2, soft_lambda=0.)
        hard = fixed_design_diagnostics(A, W, np.eye(3), truth,
                                        np.array([1., 0., 0.]), 'hard', .2,
                                        soft_lambda=0.)
        self.assertAlmostEqual(free['thermal_variance_trace_proxy'], .2 * (1/4 + 1 + 1/16))
        self.assertAlmostEqual(hard['thermal_variance_trace_proxy'], .2 / 4)
        self.assertAlmostEqual(hard['template_projection_bias_squared'], 4.)
        self.assertEqual(hard['basis_rank'], 1)
        self.assertEqual(hard['true_basis_rank'], 3)
        self.assertEqual(hard['unmatched_true_dimensions'], 2)
        self.assertEqual(hard['scope'], 'fixed-design thermal-noise proxy; adaptive selection held fixed')

    def test_rank_deficiency_and_empty_support_remain_reportable(self):
        A = np.array([[1., 1.], [0., 0.]], complex)
        W = np.ones((2, 2), complex)
        row = fixed_design_diagnostics(A, W, W, np.ones(2), np.ones(2),
                                       'hard', .1, soft_lambda=0.)
        self.assertEqual(row['response_rank'], 1)
        self.assertIsNone(row['response_condition_number'])
        self.assertEqual(row['basis_rank'], 1)
        row = fixed_design_diagnostics(np.empty((3, 0)), np.empty((0, 0)),
                                       np.empty((0, 0)), np.empty(0), np.empty(0),
                                       'none', .1, soft_lambda=0.)
        self.assertEqual(row['thermal_variance_trace_proxy'], 0.)
        self.assertEqual(row['basis_rank'], 0)


if __name__ == '__main__':
    unittest.main()
