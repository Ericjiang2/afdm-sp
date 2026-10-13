import unittest
from unittest.mock import patch

import torch

from afdm_sp_joint_unrolled.classical_joint_unrolled import (
    omp_sparse_torch, ClassicalJointConfig, ClassicalJointUnrolled,
)
from afdm_sp_joint_unrolled.v3_initial import InitialEstimator


class InitialTests(unittest.TestCase):
    def setUp(self):
        torch.manual_seed(912)
        self.A=torch.eye(48,dtype=torch.complex128)
        self.y=torch.arange(1,49,dtype=torch.float64).to(torch.complex128)/48

    def test_observer_does_not_change_omp(self):
        expected,S=omp_sparse_torch(self.y,self.A,40)
        states=[]
        actual,T=omp_sparse_torch(self.y,self.A,40,path_observer=lambda s,g,r:states.append((s,g,r)))
        self.assertEqual(S,T);self.assertEqual(len(states),41)
        torch.testing.assert_close(actual,expected)

    def test_ridge_matches_analytic_orthogonal_solution_and_same_support(self):
        reference,S=omp_sparse_torch(self.y,self.A,40)
        estimate=InitialEstimator('ridge',.1)
        h,T=estimate(self.y,self.A,40,.1)
        self.assertEqual(S,T)
        torch.testing.assert_close(h,reference/1.1)

    def test_size_search_uses_one_path_and_keeps_zero_candidate(self):
        estimator=InitialEstimator('size',2.)
        with patch('afdm_sp_joint_unrolled.v3_initial.omp_sparse_torch',wraps=omp_sparse_torch) as call:
            h,S=estimator(self.y,self.A,40,.1)
        self.assertEqual(call.call_count,1)
        self.assertEqual(len(estimator.record['objectives']),41)
        self.assertEqual(len(S),min(range(41),key=lambda i:estimator.record['objectives'][i]))

    def test_sbl_bounded_finite_and_no_ls_debias(self):
        estimator=InitialEstimator('sbl',1e-3)
        h,S=estimator(self.y,self.A,40,.1)
        self.assertTrue(torch.isfinite(h).all())
        self.assertLessEqual(estimator.record['iterations'],20)
        self.assertTrue(torch.all(h[S].abs()<self.y[S].abs()))
        with self.assertRaises(ValueError):estimator(self.y,self.A,40,0.)

    def test_sbl_matches_independent_scalar_gaussian_posteriors(self):
        import numpy as np
        estimator=InitialEstimator('sbl',1e-3)
        h,S=estimator(self.y,self.A,40,.1)
        ids=np.arange(47,7,-1);observed=self.y.numpy()[ids]
        gamma=np.abs(observed)**2
        for _ in range(20):
            mu=gamma/(gamma+.1)*observed
            variance=gamma*.1/(gamma+.1)
            updated=np.abs(mu)**2+variance
            relative=np.linalg.norm(updated-gamma)/np.linalg.norm(gamma)
            gamma=updated
            if relative<=1e-4:break
        keep=gamma>=1e-3*gamma.max()
        self.assertEqual(S,ids[keep].tolist())
        np.testing.assert_allclose(h.numpy()[S],mu[keep],rtol=1e-10,atol=1e-12)

    def test_full_receiver_initial_hook_and_empty_support(self):
        cfg=ClassicalJointConfig(N=16,l_max=2,k_max=1,n_paths=2,n_outer_iter=2,
             pic_iter=2,device='cpu',dtype=torch.complex128,rdtype=torch.float64,early_stop=False,mp_mode='bp')
        model=ClassicalJointUnrolled(cfg,learnable_heads=(),use_soft_decisions=True)
        pilot=torch.ones(16,dtype=cfg.dtype)*.7
        y=pilot+.03*torch.randn(16,dtype=cfg.dtype)
        args=(y,pilot,torch.tensor(.1),torch.tensor([.5+.5j,.5-.5j,-.5+.5j,-.5-.5j]))
        expected=model(*args,enable_support_repair=False)
        hook=lambda y,A,k,sigma:omp_sparse_torch(y,A,k)
        actual=model(*args,enable_support_repair=False,initial_estimator=hook)
        for key in ('H_est','x_soft','sigma2_final'):
            torch.testing.assert_close(actual[key],expected[key],rtol=1e-9,atol=1e-9)
        zero=lambda y,A,k,sigma:(torch.zeros(A.shape[1],dtype=y.dtype),[])
        empty=model(*args,enable_support_repair=False,initial_estimator=zero,receiver_extension=0)
        self.assertTrue(torch.isfinite(empty['H_est']).all())
        with self.assertRaises(ValueError):model(*args,initial_estimator=hook)


if __name__=='__main__':unittest.main()
