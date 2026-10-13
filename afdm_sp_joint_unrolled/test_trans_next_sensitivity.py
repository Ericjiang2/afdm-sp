"""Independent finite differences and observed-only bit selection contracts."""
import unittest
import numpy as np
from .trans_next_sensitivity import ce_direction, mean_design_direction, eligible_bits


class SensitivityTests(unittest.TestCase):
    def test_complex_proximal_derivative_matches_refits(self):
        rng = np.random.default_rng(213)
        z = lambda shape: rng.normal(size=shape) + 1j * rng.normal(size=shape)
        A, dA, y, old = z((17, 4)), z((17, 4)), z(17), z(4)
        _, derivative = ce_direction(A, y, old, .3, dA)
        def refit(B):
            return np.linalg.lstsq(np.vstack((B, np.sqrt(.3) * np.eye(4))),
                np.concatenate((y, np.sqrt(.3) * old)), rcond=None)[0]
        step = 1e-5
        numerical = (refit(A + step*dA) - refit(A - step*dA))/(2*step)
        np.testing.assert_allclose(derivative, numerical, rtol=1e-7, atol=1e-9)
        np.testing.assert_array_equal(ce_direction(A, y, old, .3, np.zeros_like(A))[1], 0)

    def test_integer_atom_mean_derivative_both_bit_components(self):
        n = 32; dl = np.array([0, 1, 3]); dk = np.array([0, -1, 1])
        app = np.linspace(-3, 3, 2*n); c1 = 5/(2*n); c2 = .013
        def design(llr):
            mean=.5*(np.tanh(llr[:n]/2)+1j*np.tanh(llr[n:]/2))
            B=np.zeros((n,len(dl)),complex)
            for j in range(len(dl)):
                for x in range(n):
                    out=(x+5*dl[j]+dk[j])%n
                    B[out,j]=np.exp(2j*np.pi*(-c1*dl[j]**2+c2*(out**2-x**2)-x*dl[j]/n))*mean[x]
            return B
        for bit in (5, n+5):
            delta=np.zeros(2*n);delta[bit]=1e-5
            numerical=(design(app+delta)-design(app-delta))/(2e-5)
            np.testing.assert_allclose(mean_design_direction(app,bit,dl,dk,c1,c2),
                                       numerical,rtol=1e-8,atol=1e-11)

    def test_truth_free_selection_and_rejections(self):
        self.assertEqual(eligible_bits([8,0,0,9],[0,0,0,0]),[1,2])
        self.assertEqual(eligible_bits([9,9,9,9],[0,0,0,0]),[])
        self.assertEqual(eligible_bits([-19.95,0,0,0],[19.95,0,0,0]),[1,2])
        with self.assertRaises(ValueError):eligible_bits([float('nan'),0],[0,0])
        with self.assertRaises(ValueError):
            ce_direction(np.ones((2,1)),np.ones(2),np.ones(1),0,np.ones((2,1)))


if __name__ == '__main__':unittest.main()
