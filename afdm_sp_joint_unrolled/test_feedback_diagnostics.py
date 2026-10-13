import unittest
import numpy as np
import torch
from unittest.mock import patch
from afdm_sp_joint_unrolled.feedback_diagnostics import reliability_statistics, compare_frozen_state


class FeedbackDiagnosticsTests(unittest.TestCase):
    def test_real_forward_snapshots_precede_all_dals_solves(self):
        from afdm_sp_joint_unrolled.classical_joint_unrolled import ClassicalJointConfig, ClassicalJointUnrolled, soft_gain_update
        cfg=ClassicalJointConfig(N=16,l_max=4,k_max=1,n_paths=1,n_outer_iter=3,
            pic_iter=2,device='cpu',dtype=torch.complex128,rdtype=torch.float64,mp_mode='bp')
        model=ClassicalJointUnrolled(cfg,use_soft_decisions=True)
        y=torch.arange(1,17,dtype=torch.float64).to(torch.complex128)/16
        pilot=torch.ones(16,dtype=torch.complex128)/2
        constellation=torch.tensor([.5+.5j,.5-.5j,-.5+.5j,-.5-.5j],dtype=torch.complex128)
        for mode in ('mean','covariance_uniform','covariance'):
            snapshots=[]
            with patch('afdm_sp_joint_unrolled.classical_joint_unrolled.soft_gain_update',wraps=soft_gain_update) as solve:
                result=model(y,pilot,torch.tensor(.1),constellation,
                    Phi=torch.eye(16,dtype=cfg.dtype)[:,:15],enable_support_repair=False,
                    active_support_cap=1,receiver_extension=0,dals_mode=mode,
                    diagnostic_dals_observer=snapshots.append)
            self.assertEqual([s['outer_iter'] for s in snapshots],[1,2])
            self.assertEqual(solve.call_count,2)
            self.assertTrue(torch.isfinite(result['H_est']).all())
            for state,call in zip(snapshots,solve.call_args_list):
                for name,arg in zip(('A','y','g_previous','regularization'),call.args):
                    self.assertTrue(torch.equal(state[name],arg))
                self.assertEqual('C' in call.kwargs,mode!='mean')
                if mode=='covariance_uniform':
                    v0=(constellation-constellation.mean()).abs().square().mean()
                    expected=v0*(state['H']@state['H'].conj().T)+state['sigma2']*torch.eye(16,dtype=cfg.dtype)
                    torch.testing.assert_close(call.kwargs['C'],expected)

    def test_uniform_and_confident_wrong_keep_distinct_denominators(self):
        constellation = np.array([.5+.5j,.5-.5j,-.5+.5j,-.5-.5j])
        p = np.array([[.25]*4,[1.,0.,0.,0.]])
        result = reliability_statistics(p,constellation,constellation[[0,1]],.5)
        self.assertEqual(result['high_confidence_count'],1)
        self.assertEqual(result['high_confidence_errors'],1)
        self.assertEqual(result['high_confidence_error_rate'],1)
        self.assertEqual(result['high_confidence_error_frequency'],.5)
        self.assertEqual(result['bins'][-1]['count'],1)
        self.assertEqual(result['bins'][0]['count'],1)
        self.assertEqual(result['out_of_range_count'],0)

    def test_frozen_solutions_match_independent_dense_normal_equations(self):
        rng=np.random.default_rng(321)
        def z(shape): return rng.normal(size=shape)+1j*rng.normal(size=shape)
        A,y,g,H=z((8,3)),z(8),z(3),z((8,8)); v=np.linspace(0,.5,8)
        state={k:torch.as_tensor(x) for k,x in dict(A=A,y=y,g_previous=g,H=H,
            finite_variance=v,sigma2=np.array(.2),regularization=np.array(.03),
            constellation=np.array([.5+.5j,.5-.5j,-.5+.5j,-.5-.5j])).items()}
        result=compare_frozen_state(state)
        for mode,variance in [('unweighted',None),('uniform',np.full(8,.5)),('dynamic',v)]:
            C=np.eye(8) if variance is None else H@np.diag(variance)@H.conj().T+.2*np.eye(8)
            W=np.eye(8) if variance is None else .2*np.linalg.solve(C,np.eye(8))
            expected=np.linalg.solve(A.conj().T@W@A+.03*np.eye(3),A.conj().T@W@y+.03*g)
            np.testing.assert_allclose(result[mode]['gains'].numpy(),expected,rtol=1e-11,atol=1e-11)
            self.assertLessEqual(result[mode]['own_objective_after'],result[mode]['own_objective_before']+1e-10)


if __name__=='__main__':unittest.main()
