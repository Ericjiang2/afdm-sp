"""Contracts for actual source-conditioned fixed points and Gaussian limits."""
import sys
from pathlib import Path
import unittest
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from linear_limits import run_all, posterior

class LinearLimitsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.result=run_all()
    def test_actual_ce_and_joint_fixed_points(self):
        for r in self.result['actual_known_data']:
            self.assertLess(r['ce_actual_error'],1e-10)
            self.assertLess(r['joint_actual_error'],1e-8)
            self.assertLess(r['onsager_residual'],1e-8)
            if r['p']==1:self.assertLess(r['ce_joint_gap'],1e-12)
            else:self.assertGreater(r['ce_joint_gap'],1e-7)
    def test_physical_operators_and_covariance_invariance(self):
        self.assertLess(self.result['cpp_dense_error'],1e-10)
        for r in self.result['geometry']:
            for k in ['dense_error','time_error','coordinate_error','permutation_error']:
                self.assertLess(r[k],1e-10)
        dup,near,orth,_=self.result['geometry']
        self.assertAlmostEqual(dup['weakest_direction_variance'],.5,places=12)
        self.assertGreater(near['weakest_direction_variance'],.4999)
        self.assertLess(orth['best_scalar_fro_error'],1e-12)
        self.assertGreater(orth['scalar_variance_actual'],orth['covariance_eigenvalues'][0])
        self.assertLess(dup['scalar_variance_actual'],.5)
    def test_scaling_noise_and_scalar_condition(self):
        B=np.array([[1,1],[0,.01]],complex)
        C=posterior(B,.3,.5)
        np.testing.assert_allclose(C,posterior(7*B,.3*49,.5),atol=1e-13)
        self.assertGreater(np.linalg.eigvalsh(posterior(B,1e9,.5))[0],.499999)
        self.assertLess(np.linalg.eigvalsh(posterior(B,1e-10,.5))[-1],1e-5)
        np.testing.assert_allclose(posterior(np.eye(2),.3,.5),np.eye(2)/(2+1/.3))
    def test_damping_fixed_point(self):
        for r in self.result['damping']:self.assertLess(r['error'],1e-9)

if __name__=='__main__':unittest.main()
