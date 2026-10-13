import unittest
import numpy as np

from afdm_sp_joint_unrolled.v3_color import coded_second_moments, matched_observations, proper_gaussian, actual_coded_moments, augmented_factor


class ColorTests(unittest.TestCase):
    def test_duplicate_bits_exact_covariance_and_pseudo_covariance(self):
        g=np.array([[1,0],[0,1],[1,0],[1,1]],dtype=np.uint8)
        messages=np.array([[0,0],[0,1],[1,0],[1,1]])
        bits=messages@g.T%2
        data=.5*((1-2*bits[:,:2])+1j*(1-2*bits[:,2:]))
        R,P,groups=actual_coded_moments(g,.5)
        np.testing.assert_allclose(R,data.T@data.conj()/4,atol=1e-15)
        np.testing.assert_allclose(P,data.T@data/4,atol=1e-15)
        self.assertEqual(groups,[[0,2]])
        self.assertGreater(np.linalg.norm(P),0)
        H=np.array([[1+1j,2],[.1j,3-1j]])
        factor=augmented_factor(H,g,.5)
        np.testing.assert_allclose(factor@factor.conj().T,H@R@H.conj().T,atol=1e-14)
        np.testing.assert_allclose(factor@factor.T,H@P@H.T,atol=1e-14)
        with self.assertRaises(ValueError):coded_second_moments(g,.5)

    def test_exact_coded_population_moments_and_bad_generators(self):
        g=np.array([[1,0,0],[0,1,0],[0,0,1],[1,1,0]],dtype=np.uint8)
        coded_second_moments(g,.5)
        messages=np.array([[int(x) for x in f'{i:03b}'] for i in range(8)])
        bits=(messages@g.T)%2
        data=np.sqrt(.5/2)*((1-2*bits[:,:2])+1j*(1-2*bits[:,2:]))
        np.testing.assert_allclose(data.mean(0),0,atol=1e-15)
        np.testing.assert_allclose(data.T@data.conj()/8,.5*np.eye(2),atol=1e-15)
        np.testing.assert_allclose(data.T@data/8,0,atol=1e-15)
        for bad in (np.zeros_like(g),np.tile(g[0],(4,1))):
            with self.assertRaises(ValueError):coded_second_moments(bad,.5)

    def test_shared_gaussian_isotropic_limit_and_power_scaling(self):
        rng=np.random.default_rng(5);z=proper_gaussian(rng,4)
        H=2*np.eye(4);pilot=np.ones(4);noise=np.arange(4)*.1;data=z*np.sqrt(.5)
        xi=np.concatenate((z.real,z.imag))*np.sqrt(2)
        factor=augmented_factor(H,np.eye(8,dtype=int),.5)
        full,_=matched_observations(H,pilot,data,noise,xi,factor)
        low,_=matched_observations(H,pilot,data,noise,xi,factor,.25)
        np.testing.assert_allclose(full['G'],full['W'])
        for arm in full:
            np.testing.assert_allclose(low[arm]-(H@pilot+noise),.5*(full[arm]-(H@pilot+noise)))

    def test_singular_zero_channels_and_invalid_inputs(self):
        z=np.ones(3,dtype=complex)
        for H in (np.zeros((3,3)),np.diag([1.,0,0])):
            factor=augmented_factor(H,np.eye(6,dtype=int),.5)
            arms,meta=matched_observations(H,z,z,z,np.ones(6),factor)
            self.assertAlmostEqual(meta['trace'],.5*np.linalg.norm(H)**2)
            self.assertTrue(all(np.isfinite(v).all() for v in arms.values()))
        with self.assertRaises(ValueError):augmented_factor(np.eye(3),np.eye(6,dtype=int),-1.)
        with self.assertRaises(ValueError):matched_observations(np.eye(3),z,z,z,np.ones(6),factor,.5)


if __name__=='__main__':unittest.main()
