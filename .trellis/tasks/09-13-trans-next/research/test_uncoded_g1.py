"""Small numerical and information-boundary checks, not G1 performance evidence."""
import importlib.util
from pathlib import Path
import sys
from types import ModuleType
import unittest

import numpy as np
import torch

spec = importlib.util.spec_from_file_location('uncoded',Path(__file__).with_name('uncoded-g1-v1.py'))
u = importlib.util.module_from_spec(spec)
spec.loader.exec_module(u)


class UncodedTests(unittest.TestCase):
    def test_independent_bits_and_mapping(self):
        b,x=u.uncoded_symbols(3,1024)
        np.testing.assert_array_equal(b,u.bits_of(x))
        np.testing.assert_array_equal(b,u.uncoded_symbols(3,1024)[0])
        self.assertFalse(np.array_equal(b,u.uncoded_symbols(4,1024)[0]))
        self.assertEqual(np.vdot(x,x).real/len(x),.5)

    def test_reject_truth_and_code_fields(self):
        obs=dict(y=np.ones(4,dtype=complex),pilot=np.ones(4,dtype=complex),sigma2=np.array(.1),
                 constellation=np.array([.5+.5j,.5-.5j,-.5+.5j,-.5-.5j]))
        u.validate_observed(obs,4)
        for key in ('H','data','bits','code','prior','params'):
            with self.assertRaises(ValueError):u.validate_observed(dict(obs,**{key:0}),4)
        for sigma in (0.,-1.,float('nan'),1j,np.ones(2)):
            with self.assertRaises(ValueError):u.validate_observed(dict(obs,sigma2=np.asarray(sigma)),4)

    def test_residual_scorer_independent_formula(self):
        rng=np.random.default_rng(82)
        a=rng.normal(size=(13,7))+1j*rng.normal(size=(13,7))
        y=rng.normal(size=13)+1j*rng.normal(size=13)
        support=[0,2];candidates=[1,4,5]
        residue=y-a[:,support]@np.linalg.lstsq(a[:,support],y,rcond=None)[0]
        expected=np.abs(a[:,candidates].conj().T@residue)**2/np.sum(np.abs(a[:,candidates])**2,axis=0)
        counts={'lstsq':0}
        with u.cpu_lstsq(counts):
            actual=u.residual_score(torch.from_numpy(a),torch.from_numpy(y),support,candidates,.1)
        np.testing.assert_allclose(actual.numpy(),expected,rtol=1e-12,atol=1e-12)
        self.assertEqual(counts['lstsq'],1)

    def test_forbidden_alias_restores_after_error(self):
        name='afdm_sp_joint_unrolled._uncoded_test_alias'
        fake=ModuleType(name);fake.decode_llr=lambda:True
        original=fake.decode_llr;sys.modules[name]=fake
        counts={'coding_calls':0}
        try:
            with self.assertRaises(AssertionError):
                with u.forbid_coding(counts):fake.decode_llr()
            self.assertIs(fake.decode_llr,original)
            self.assertEqual(counts['coding_calls'],1)
        finally:
            del sys.modules[name]

    def test_gels_policy_restores(self):
        original=torch.linalg.lstsq
        with self.assertRaises(ValueError):
            with u.cpu_lstsq({'lstsq':0}):
                torch.linalg.lstsq(torch.eye(2),torch.ones(2),driver='gelsy')
        self.assertIs(torch.linalg.lstsq,original)


if __name__=='__main__':unittest.main()
