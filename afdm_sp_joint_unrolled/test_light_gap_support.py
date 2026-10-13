"""Known integer-atom fixtures test representation and fitting boundaries."""
import unittest
import numpy as np
import torch
from .classical_joint_unrolled import reconstruct_H_torch
from .light_gap_support import make_cases


class SupportTests(unittest.TestCase):
    def setUp(self):
        N, c1, c2 = 16, 5/32, 1e-4
        dl, dk = np.array([0,1,6]), np.array([0,1,-1])
        gains = np.array([1+.2j, .3-.1j, .1+.05j])
        self.params = dict(c1=c1,c2=c2,l_exp=dl,k_exp=dk,chan_coef_exp=gains,taps=3)
        self.H = reconstruct_H_torch(N,torch.tensor(dl),torch.tensor(dk),torch.tensor(gains),c1,c2,2).numpy()
        self.Hhat = reconstruct_H_torch(N,torch.tensor(dl[:2]),torch.tensor(dk[:2]),torch.tensor(.8*gains[:2]),c1,c2,2).numpy()
        rng = np.random.default_rng(918)
        self.pilot = np.exp(1j*rng.normal(size=N))/np.sqrt(2)
        self.data = .5*rng.choice([-1,1],N)+.5j*rng.choice([-1,1],N)
        self.raw = dict(H=self.H,params=self.params,data=self.data)
        self.i1 = dict(H=self.Hhat,support=[2,8],x_soft=self.data.copy())
        self.observed = dict(pilot=self.pilot,y=self.H@(self.pilot+self.data))

    def test_projection_decomposition_domain_and_power(self):
        cases, metrics, state = make_cases(self.raw,self.i1,self.observed,lmax=3,kmax=2)
        self.assertEqual(metrics['K_current'],2)
        self.assertEqual(metrics['K_top'],2)
        self.assertEqual(metrics['K_outside_domain'],1)
        self.assertLess(metrics['generator_reconstruction_relative_l2'],1e-12)
        self.assertAlmostEqual(metrics['NMSE']['I1_CPU'],metrics['current_representation_error']+
                               metrics['current_coefficient_error']+metrics['decomposition_cross_term'],places=12)
        self.assertLess(abs(metrics['decomposition_cross_term']),1e-12)
        np.testing.assert_allclose(cases['PROJ_CURRENT'],self.Hhat/.8,rtol=1e-12,atol=1e-12)
        np.testing.assert_allclose(cases['TRUE_DATA_LS_CURRENT'],cases['OBS_LS_CURRENT'],rtol=1e-12,atol=1e-12)
        self.assertEqual(state['fits']['TRUE_DATA_LS_CURRENT']['rank'],2)
        self.assertGreater(metrics['NMSE']['DOMAIN_TRUTH'],0)

    def test_mismatched_normalization_is_not_hidden(self):
        raw = dict(self.raw,H=2*self.H)
        with self.assertRaisesRegex(ValueError,'reconstruct trueH'):
            make_cases(raw,self.i1,self.observed,lmax=3,kmax=2)
        wrong = dict(self.i1,support=[2,2])
        with self.assertRaisesRegex(ValueError,'support'):
            make_cases(self.raw,wrong,self.observed,lmax=3,kmax=2)


if __name__=='__main__':
    unittest.main()
