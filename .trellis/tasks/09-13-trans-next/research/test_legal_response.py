"""Public small synthetic algebra; no G1 data or performance claims."""
import importlib.util
from pathlib import Path
import unittest
import numpy as np
import torch
from afdm_sp_joint_unrolled.classical_joint_unrolled import reconstruct_H_torch

spec = importlib.util.spec_from_file_location('legal_response', Path(__file__).with_name('e1a-legal-response-v1.py'))
module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)


class LegalResponseTests(unittest.TestCase):
    def inputs(self):
        rng = np.random.default_rng(918)
        n = 64; c1 = 3/(2*n); c2 = .000017
        ids = np.array([1, 3, 7], dtype=np.int64)
        g = torch.tensor([.8+.2j, -.3+.1j, .1-.2j], dtype=torch.complex128)
        H = reconstruct_H_torch(n,torch.tensor(ids//3),torch.tensor(ids%3-1),g,c1,c2,1).numpy()
        p = (rng.standard_normal(n)+1j*rng.standard_normal(n))/np.sqrt(2)
        mu = .2*(rng.standard_normal(n)+1j*rng.standard_normal(n))
        return dict(y=H@(p+mu),pilot=p,mu=mu,variance=np.zeros(n),Hc=H,
                    support=ids,c1=c1,c2=c2,regularization=0.,l_max=3,k_max=1)

    def test_noiseless_response_and_operator(self):
        x = self.inputs(); fit = module.fit_legal(**x)
        for name in ('S','D'):
            np.testing.assert_allclose(fit[name]['H'],x['Hc'],atol=1e-12,rtol=1e-12)
            np.testing.assert_allclose(fit[name]['H']@x['pilot'],x['Hc']@x['pilot'],atol=1e-12,rtol=1e-12)

    def test_positive_variance_against_augmented_lstsq(self):
        x = self.inputs(); x['variance'][:] = .14; x['regularization'] = .3
        fit = module.fit_legal(**x)
        for name in ('S','D'):
            v = fit[name]; n = len(v['gains'])
            A = np.vstack([v['A'],np.sqrt(x['variance'].sum())*np.eye(n),np.sqrt(.3)*np.eye(n)])
            y = np.concatenate([x['y'],np.zeros(n),np.sqrt(.3)*v['previous']])
            oracle = np.linalg.lstsq(A,y,rcond=None)[0]
            np.testing.assert_allclose(v['gains'],oracle,atol=1e-12,rtol=1e-12)
            self.assertLess(module.validate_fit(v,x['y'])['normal_residual'],1e-12)

    def test_reject_invalid_variance_and_colliding_domain(self):
        x = self.inputs(); x['variance'][0] = -.1
        with self.assertRaises(ValueError): module.fit_legal(**x)
        x = self.inputs(); x['l_max'] = 22
        with self.assertRaises(ValueError): module.fit_legal(**x)
        x = self.inputs(); x['support'][1] = x['support'][0]
        with self.assertRaises(ValueError): module.fit_legal(**x)

    def test_destination_and_half_control(self):
        x = self.inputs(); x['variance'][:] = .14; fit = module.fit_legal(**x)
        prior = np.ones(128)
        args = (x['y'],x['pilot'],x['Hc'],fit,.2,prior)
        p = module.terminal_inputs('D_P',*args); all_ = module.terminal_inputs('D_ALL',*args)
        half = module.terminal_inputs('D_P_HALF',*args)
        np.testing.assert_array_equal(p['H'],x['Hc'])
        np.testing.assert_array_equal(all_['H'],fit['D']['H'])
        np.testing.assert_array_equal(p['cancellation'],all_['cancellation'])
        np.testing.assert_allclose(half['cancellation'],.5*(p['cancellation']+x['Hc']@x['pilot']))
        with self.assertRaises(TypeError): module.fit_legal(**x,truth_channel=x['Hc'])


if __name__ == '__main__':
    torch.set_num_threads(1)
    unittest.main()
