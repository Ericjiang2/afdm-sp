"""Algebra tests only; real cached-state validation is separately budgeted."""
import importlib.util
from pathlib import Path
import unittest
import numpy as np
spec=importlib.util.spec_from_file_location('active_gram',Path(__file__).with_name('g1-active-observability-v1.py'))
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)

class GeometryTests(unittest.TestCase):
    def test_orthogonal_columns_and_scale(self):
        result=module.geometry(np.diag([2.,5.,8.]))
        np.testing.assert_allclose(result['gram'],np.eye(3),atol=1e-14)
        self.assertEqual(result['metrics']['white_ls_geometry_factor'],1.)
        self.assertEqual(result['metrics']['gram_condition'],1.)
    def test_known_two_column_correlation(self):
        a=np.array([[1.,.6],[0.,.8],[0.,0.]])
        metrics=module.geometry(a)['metrics']
        self.assertAlmostEqual(metrics['max_coherence'],.6)
        self.assertAlmostEqual(metrics['gram_condition'],4.)
        self.assertAlmostEqual(metrics['white_ls_geometry_factor'],1/.64)
    def test_rank_deficiency_is_reported(self):
        metrics=module.geometry(np.array([[1,1],[2,2],[3,3]],complex))['metrics']
        self.assertFalse(metrics['full_rank'])
        self.assertEqual(metrics['rank'],1)
        self.assertIsNone(metrics['gram_condition'])
    def test_zero_column_rejected(self):
        with self.assertRaises(AssertionError):module.geometry(np.zeros((3,2)))

if __name__=='__main__':unittest.main()
