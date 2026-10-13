import unittest
import numpy as np
from .supplement_siso_mmse import siso_mmse


class SisoMmseTests(unittest.TestCase):
    def test_matches_independent_per_symbol_cavity_solves(self):
        rng = np.random.default_rng(911)
        n = 7
        H = (rng.normal(size=(n,n))+1j*rng.normal(size=(n,n)))/np.sqrt(n)
        y = rng.normal(size=n)+1j*rng.normal(size=n)
        prior = rng.normal(size=2*n)*2
        actual = siso_mmse(y,H,.3,prior)
        mean, var = actual['prior_mean'], actual['prior_variance']
        for j in range(n):
            keep = np.arange(n)!=j
            cavity = (H[:,keep]*var[None,keep])@H[:,keep].conj().T+.3*np.eye(n)
            residual = y-H[:,keep]@mean[keep]
            eta = np.vdot(H[:,j],np.linalg.solve(cavity,residual))
            tau = np.vdot(H[:,j],np.linalg.solve(cavity,H[:,j])).real
            np.testing.assert_allclose(actual['extrinsic_natural'][j],eta,rtol=1e-12,atol=1e-12)
            np.testing.assert_allclose(actual['extrinsic_precision'][j],tau,rtol=1e-12,atol=1e-12)

    def test_diagonal_matches_enumerated_likelihood_for_power_and_priors(self):
        h = np.array([1+.7j,-.4+1j,.1-.2j])
        y = np.array([.2+.9j,-.7+.1j,.03-.4j])
        prior = np.array([1.,-2.,3.,-.3,4.,-1.])
        for a in (.5,1/np.sqrt(2)):
            const = a*np.array([1+1j,1-1j,-1+1j,-1-1j])
            likelihood = -abs(y[:,None]-h[:,None]*const[None,:])**2/.17
            logsum = lambda z: np.logaddexp.reduce(z,axis=1)
            expected = np.concatenate((logsum(likelihood[:,:2])-logsum(likelihood[:,2:]),
                logsum(likelihood[:,[0,2]])-logsum(likelihood[:,[1,3]])))
            actual = siso_mmse(y,np.diag(h),.17,prior,amplitude=a)
            np.testing.assert_allclose(actual['channel_llr'],expected,rtol=1e-12,atol=1e-12)

    def test_own_symbol_prior_exclusion_and_zero_channel(self):
        rng = np.random.default_rng(80)
        H = rng.normal(size=(4,4))+1j*rng.normal(size=(4,4))
        y = rng.normal(size=4)+1j*rng.normal(size=4)
        prior = rng.normal(size=8)
        base = siso_mmse(y,H,.8,prior)
        changed = prior.copy(); changed[[1,5]] = [7.,-6.]
        perturbed = siso_mmse(y,H,.8,changed)
        np.testing.assert_allclose(base['channel_llr'][[1,5]],perturbed['channel_llr'][[1,5]],rtol=1e-12,atol=1e-12)
        zero = siso_mmse(y,np.zeros((4,4)),.8,prior)
        np.testing.assert_array_equal(zero['channel_llr'],np.zeros(8))
        np.testing.assert_array_equal(zero['posterior_llr'],prior)

    def test_saturated_prior_does_not_create_invalid_gaussian_variance(self):
        out = siso_mmse(np.ones(2),np.eye(2),.2,np.full(4,1000.))
        self.assertTrue(np.isfinite(out['channel_llr']).all())
        self.assertTrue((out['prior_variance']==0).all())
        np.testing.assert_allclose(out['channel_llr'],[10.,10.,0.,0.])

    def test_invalid_domain_rejected(self):
        for sigma in (0.,-1.,float('nan'),True):
            with self.assertRaises(ValueError):siso_mmse(np.ones(2),np.eye(2),sigma,np.zeros(4))
        with self.assertRaises(ValueError):siso_mmse(np.ones(2),np.eye(2),1.,np.zeros(4,dtype=complex))
        with self.assertRaises(ValueError):siso_mmse(np.ones(2),np.eye(2),1.,np.zeros(3))


if __name__ == '__main__':
    unittest.main()
