"""Analytic finite-QPSK contracts, independent of receiver simulation truth."""
import unittest
import numpy as np
import torch
from afdm_sp_joint_unrolled.classical_joint_unrolled import _qpsk_soft_decision
from afdm_sp_joint_unrolled.budgeted_support_diagnostics import dev_rng

class SoftFeedbackTests(unittest.TestCase):
    def setUp(self):
        self.a=torch.tensor([.5+.5j,.5-.5j,-.5+.5j,-.5-.5j],dtype=torch.complex128)

    def moments(self,z,v,T=1):
        return _qpsk_soft_decision(z,torch.ones_like(z.real),torch.as_tensor(v,dtype=torch.float64),self.a,
                                   temperature=T,return_variance=True)

    def test_analytic_scalar_and_scaling(self):
        z=torch.tensor([.3+.2j,-.4+.1j],dtype=torch.complex128)
        for T in (.25,.5,1,2,4):
            mu,var=self.moments(z,.2,T)
            expected=.5*torch.tanh(z.real/(T*.2))+.5j*torch.tanh(z.imag/(T*.2))
            torch.testing.assert_close(mu,expected,atol=1e-14,rtol=1e-14)
            torch.testing.assert_close(var,.5-expected.abs()**2,atol=1e-14,rtol=1e-14)
            scaled_mu,scaled_var=_qpsk_soft_decision(z*3,torch.ones(2),torch.tensor(1.8,dtype=torch.float64),self.a*3,temperature=T,return_variance=True)
            torch.testing.assert_close(scaled_mu,mu*3)
            torch.testing.assert_close(scaled_var,var*9)

    def test_uniform_and_point_mass(self):
        mu,var=self.moments(torch.zeros(4,dtype=torch.complex128),1.)
        torch.testing.assert_close(mu,torch.zeros_like(mu))
        torch.testing.assert_close(var,torch.full_like(var,.5))
        mu,var=self.moments(self.a,1e-8)
        torch.testing.assert_close(mu,self.a)
        torch.testing.assert_close(var,torch.zeros_like(var))

    def test_identity_and_invalid_temperature(self):
        z=self.a*.3
        original=_qpsk_soft_decision(z,torch.ones(4),torch.tensor(.2),self.a)
        changed=_qpsk_soft_decision(z,torch.ones(4),torch.tensor(.2),self.a,temperature=1.)
        self.assertTrue(torch.equal(original,changed))
        for T in (0,-1,float('nan'),float('inf')):
            with self.assertRaises(ValueError):self.moments(z,.2,T)

    def test_split_preserves_old_stream_and_separates_calibration(self):
        old=np.random.default_rng(np.random.SeedSequence([20260905,1,10,3,2])).integers(0,2**31,size=20)
        np.testing.assert_array_equal(dev_rng(10,3,2).integers(0,2**31,size=20),old)
        self.assertFalse(np.array_equal(dev_rng(10,3,2,split=2).integers(0,2**31,size=20),old))
        with self.assertRaises(ValueError):dev_rng(0,0,0,split=3)

if __name__=='__main__':unittest.main()

class UncertaintyGainTests(unittest.TestCase):
    def test_structured_gram_matches_dense_with_displacement_collision(self):
        from afdm_sp_joint_unrolled.classical_joint_unrolled import data_uncertainty_gram,reconstruct_H_torch
        N=16;dl=torch.tensor([0,1,3]);dk=torch.tensor([0,-1,1]);v=torch.linspace(.01,.5,N,dtype=torch.float64)
        # displacement 0 and 3*5+1 coincide modulo N: nonzero cross term.
        Q=data_uncertainty_gram(N,dl,dk,v,.013,.003,2)
        ops=[reconstruct_H_torch(N,dl[i:i+1],dk[i:i+1],torch.ones(1,dtype=torch.complex128),.013,.003,2) for i in range(3)]
        dense=torch.stack([torch.stack([((a.conj()*b)*v).sum() for b in ops]) for a in ops])
        torch.testing.assert_close(Q,dense,atol=1e-12,rtol=1e-12)
        self.assertGreater(float(Q[0,2].abs()),.01)
        self.assertGreaterEqual(float(torch.linalg.eigvalsh(Q).min()),-1e-12)

    def test_covariance_and_objective_reductions(self):
        from afdm_sp_joint_unrolled.classical_joint_unrolled import soft_gain_update,residual_data_covariance
        torch.manual_seed(23)
        A=torch.randn(8,3,dtype=torch.complex128);y=torch.randn(8,dtype=torch.complex128)
        old=torch.randn(3,dtype=torch.complex128);H=torch.randn(8,8,dtype=torch.complex128)
        v=torch.rand(8,dtype=torch.float64);sigma=torch.tensor(.2,dtype=torch.float64);lam=torch.tensor(.03,dtype=torch.float64)
        C=residual_data_covariance(H,v,sigma)
        z=torch.randn(8,dtype=torch.complex128)
        torch.testing.assert_close(C@z,H@(v*(H.conj().T@z))+sigma*z)
        torch.linalg.cholesky(C)
        Q=torch.eye(3,dtype=torch.complex128)*v.sum()
        new=soft_gain_update(A,y,old,lam,Q=Q)
        def obj(g):return ((y-A@g).abs().square().sum()+(g.conj()@(Q@g)).real+lam*(g-old).abs().square().sum())
        self.assertLessEqual(float(obj(new)),float(obj(old))+1e-10)
        for _ in range(10):self.assertLessEqual(float(obj(new)),float(obj(new+.01*torch.randn_like(new)))+1e-10)
        zero=residual_data_covariance(H,torch.zeros_like(v),sigma)
        torch.testing.assert_close(zero,sigma*torch.eye(8,dtype=torch.complex128))
        base=soft_gain_update(A,y,old,lam,Q=torch.zeros_like(Q))
        weighted=soft_gain_update(A,y,old,lam,C=zero,sigma2=sigma)
        torch.testing.assert_close(base,weighted)
        g=soft_gain_update(A,y,old,lam,C=C,sigma2=sigma)
        def weighted_obj(g):
            r=y-A@g
            return sigma*(r.conj()@torch.linalg.solve(C,r)).real+lam*(g-old).abs().square().sum()
        self.assertLessEqual(float(weighted_obj(g)),float(weighted_obj(old))+1e-10)
        with self.assertRaises(ValueError):residual_data_covariance(H,-v,sigma)
