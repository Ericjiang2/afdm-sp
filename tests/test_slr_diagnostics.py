"""Exact posterior affine projection identities; no receiver workloads."""
from pathlib import Path
import sys
import unittest
import numpy as np
from numpy.testing import assert_allclose

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from experiments.afdm_inference_causal_20261002.slr_diagnostics import slr_moments


class SLRTests(unittest.TestCase):
    def test_known_data_exact_linear(self):
        ops=np.array([np.eye(2),[[0,1j],[1,0]]],complex)
        r=slr_moments(ops,[.1j,.2],[[.5+.5j,-.5j]],[1.],[[.2j,.3]],np.eye(2)[None]/2,.4)
        self.assertLess(r['metrics']['residual_energy'],1e-26)
        self.assertLess(r['metrics']['orthogonality_full_fro'],1e-12)

    def test_known_gain_exact_linear(self):
        ops=np.array([np.eye(2),[[0,1j],[1,0]]],complex)
        d=np.array([[.5+.5j,-.5j],[-.5+.5j,.5j],[.5-.5j,.5]])
        r=slr_moments(ops,[.1j,.2],d,[.2,.3,.5],np.tile([.2j,.3],(3,1)),np.zeros((3,2,2)),.4)
        self.assertLess(r['metrics']['residual_energy'],1e-25)

    def test_correlated_two_point_removes_tangent_error(self):
        r=slr_moments(np.ones((1,1,1)),[.2],[[-1],[1]],[.25,.75],[[-1],[1]],np.zeros((2,1,1)),.5)
        self.assertLess(r['metrics']['residual_energy'],1e-27)
        self.assertGreater(r['metrics']['tangent_uncentered_energy'],1.)
        self.assertEqual(r['metrics']['retained_rank'],1)

    def test_quadratic_three_point_positive_affine_lower_bound(self):
        r=slr_moments(np.ones((1,1,1)),[0],[[-1],[0],[1]],[.25,.5,.25],[[-1],[0],[1]],np.zeros((3,1,1)),.5)
        assert_allclose(r['metrics']['residual_energy'],.25,atol=1e-14)
        assert_allclose(r['arrays']['intercept'],[.5,0],atol=1e-14)
        assert_allclose(r['arrays']['A'],0,atol=1e-14)
        self.assertFalse(r['metrics']['screen_pass'])

    def test_tiny_discarded_mass_can_hide_large_predictive_energy(self):
        r=slr_moments(np.array([[[0]],[[1e8]]]),[1],[[0]],[1],[[0,0]],
                      np.diag([1.,1e-16])[None],.1)
        self.assertLess(r['metrics']['discarded_positive_mass'],1e-15)
        assert_allclose(r['metrics']['residual_energy'],1.,atol=1e-13)
        self.assertLess(r['metrics']['full_positive_residual_energy'],1e-25)
        self.assertGreater(r['metrics']['full_positive_energy_sensitivity'],.9)
        self.assertEqual(r['metrics']['lower_bound_status'],'rank_ambiguous_no_all_affine_certificate')

    def test_joint_covariance_and_real_improper_structure(self):
        r=slr_moments(np.ones((1,1,1)),[.2],[[-1],[1]],[.25,.75],[[-1],[1]],np.zeros((2,1,1)),.5)
        c=r['arrays']['Czz']
        assert_allclose(c,np.array([[.75,0,.75,0],[0,0,0,0],[.75,0,.75,0],[0,0,0,0]]),atol=1e-14)
        self.assertGreaterEqual(np.linalg.eigvalsh(r['arrays']['residual_cov']).min(),-1e-14)
        self.assertLess(r['metrics']['residual_formula_error'],1e-12)


if __name__=='__main__':unittest.main()
