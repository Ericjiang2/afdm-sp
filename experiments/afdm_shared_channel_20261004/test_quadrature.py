import unittest
import numpy as np
from experiments.afdm_shared_channel_20261004.quadrature import (
    gaussian_nodes,sphere_nodes,independent_nodes,legal_potential,response_checks)


class QuadratureContracts(unittest.TestCase):
    def test_gaussian_support_and_complex_covariance(self):
        cov=np.array([[.4,.2j],[-.2j,.6]])
        mean=np.array([.3j,.2])
        nodes,w=gaussian_nodes(mean,cov,4)
        np.testing.assert_allclose(w@nodes,mean,atol=1e-14)
        z=nodes-mean
        np.testing.assert_allclose(np.einsum('t,ti,tj->ij',w,z,z.conj()),cov,atol=1e-14)
        singular=np.array([[1,1j],[-1j,1]])
        z,w=gaussian_nodes([0,0],singular,4)
        self.assertEqual(len(z),16)
        np.testing.assert_allclose(z[:,1],-1j*z[:,0],atol=1e-14)
        with self.assertRaises(ValueError): gaussian_nodes([0],[[1]],1000)
        with self.assertRaises(ValueError): gaussian_nodes([0],[[-1]],2)

    def test_sphere_total_energy_and_fourth_tensor(self):
        nodes,w=sphere_nodes(2,1.3,5)
        np.testing.assert_allclose(np.sum(abs(nodes)**2,axis=1),1.3,atol=1e-14)
        self.assertAlmostEqual(float(w@abs(nodes[:,0])**4),1.3**2/3)
        self.assertAlmostEqual(float(w@(abs(nodes[:,0]*nodes[:,1])**2)),1.3**2/6)
        self.assertTrue(np.all(w>0)); self.assertAlmostEqual(float(w.sum()),1.)

    def test_independent_seed_namespace(self):
        nodes,w=independent_nodes(2,1,4,[20261004,7],normalized=True)
        other,_=independent_nodes(2,1,4,[20261004,7],normalized=True)
        np.testing.assert_array_equal(nodes,other)
        np.testing.assert_allclose(np.sum(abs(nodes)**2,axis=1),1.)

    def test_response_identities_and_missing_chain(self):
        checks,_=response_checks()
        for key in ('mean_error','covariance_error','mixed_error','support_variance_error','dependent_corrected_error'):
            self.assertLess(checks[key],2e-8,key)
        self.assertGreater(abs(checks['dependent_missing_chain']),.01)
        self.assertGreater(abs(checks['dependent_total_fd']-checks['dependent_fixed_base']),.01)

    def test_invalid_states_or_changed_prior_normalization_rejected(self):
        with self.assertRaises(ValueError):
            legal_potential(np.array([[.3+.5j]]),np.array([[.2j]]),[1.],[0,0],[0,0],1.)
        with self.assertRaises(ValueError):
            legal_potential(np.array([[.5+.5j]]),np.array([[.2j]]),[2.],[0,0],[0,0],1.)


if __name__=='__main__': unittest.main()
