"""Independent small matrix checks for conditional complex GCV."""
import unittest
import numpy as np
from gcv_ridge_selector import select_ridge


class GCVSelectorTests(unittest.TestCase):
    def arrays(self):
        rng=np.random.default_rng(32091)
        A=rng.standard_normal((17,5))+1j*rng.standard_normal((17,5))
        y=rng.standard_normal(17)+1j*rng.standard_normal(17)
        previous=rng.standard_normal(5)+1j*rng.standard_normal(5)
        return A,y,previous

    def test_coefficients_against_direct_normal_solve(self):
        A,y,g=self.arrays();actual=select_ridge(A,y,g)
        for row,delta in zip(actual['candidates'][:-1],actual['candidate_deltas'][:-1]):
            direct=np.linalg.solve(A.conj().T@A+row['regularization']*np.eye(5),A.conj().T@(y-A@g))
            np.testing.assert_allclose(delta,direct,atol=1e-12,rtol=1e-12)

    def test_scores_against_explicit_smoother(self):
        A,y,g=self.arrays();actual=select_ridge(A,y,g);residual=y-A@g
        for row in actual['candidates'][:-1]:
            smoother=A@np.linalg.solve(A.conj().T@A+row['regularization']*np.eye(5),A.conj().T)
            freedom=np.trace(smoother).real
            remain=(np.eye(17)-smoother)@residual
            score=np.vdot(remain,remain).real/17/(1-freedom/17)**2
            np.testing.assert_allclose([row['degrees_of_freedom'],row['score']],[freedom,score],atol=1e-12,rtol=1e-12)

    def test_zero_innovation_selects_exact_no_update(self):
        A,_,_=self.arrays();actual=select_ridge(A,np.zeros(17),np.zeros(5))
        self.assertTrue(actual['no_update']);self.assertIsNone(actual['selected_regularization'])
        np.testing.assert_array_equal(actual['delta'],np.zeros(5,dtype=np.complex128))

    def test_invalid_design_rejected(self):
        A,y,g=self.arrays()
        for bad in (np.zeros_like(A),np.full_like(A,np.nan),A.T):
            with self.assertRaises(ValueError):select_ridge(bad,y,g)


if __name__=='__main__':unittest.main()
