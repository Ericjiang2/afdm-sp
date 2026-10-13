"""Configuration reaches both OMP consumers and the actual receiver forward."""
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
import torch

from afdm_sp_joint_unrolled import budgeted_support_eval as runner
from afdm_sp_joint_unrolled import classical_joint_unrolled as receiver


class DirectWiringTests(unittest.TestCase):
    def test_builder_runner_and_forward_share_capacity(self):
        N = 64
        params = dict(P_actual=3, taps=2, l_i=[0,1], k_real=[0.,0.], g_i=[1.+0j,.1+0j],
                      l_exp=[0,0,1], k_exp=[0,1,0], chan_coef_exp=[1.+0j,.1+0j,.1+0j],
                      fro_scale=1., k_leak=2)
        system = SimpleNamespace(N_total=N, rho=.5, _zc_seq=np.ones(N, dtype=complex),
                                 l_max_cap=20, k_max_cap=1, c1=.02, c2=.001,
                                 generate_channel_matrix=lambda:(np.eye(N),None,params),
                                 gen_h_daft=lambda g,l,k:np.eye(N,dtype=complex)*sum(g))
        cfg = receiver.ClassicalJointConfig(N=N,l_max=20,k_max=1,c1=.02,c2=.001,device='cpu')
        original = receiver.ClassicalJointUnrolled(cfg,learnable_heads=('cand_active_rel',),use_soft_decisions=True)
        with tempfile.TemporaryDirectory() as tmp:
            checkpoint=Path(tmp)/'weights.pt'
            torch.save(original.state_dict(),checkpoint)
            model=runner.build_receiver(checkpoint,system,N,'cpu',receiver_shell='direct40',active_cap=40)
        self.assertEqual(model.cfg.n_paths,40)
        model.cfg.n_outer_iter=2
        model.cfg.pic_iter=2
        frame=runner.make_frame(system,{'n':2*N,'k':N},0,0,8,uncoded=True)
        def scorer(H,rho,lookup,k,K):
            return lambda Phi,y,S,c,noise:torch.arange(len(c),device=c.device,dtype=torch.float32)
        with patch.object(runner.afb,'omp_sparse',wraps=runner.afb.omp_sparse) as host, \
             patch.object(receiver,'omp_sparse_torch',wraps=receiver.omp_sparse_torch) as device, \
             patch.object(runner,'make_genie_lambda',side_effect=scorer):
            result=runner.run_frame(model,system,{},frame,None,['a0','baseline'],0,0,8,
                                    active_cap=40,receiver_shell='direct40')
        self.assertEqual(host.call_count,1)
        self.assertEqual(host.call_args.args[2],40)
        self.assertEqual([c.args[2] for c in device.call_args_list],[40,40])
        self.assertEqual(frame['params']['k_leak'],2)
        self.assertEqual(result['receiver_extension'],0)
        for arm in result['arms'].values():
            trace=arm['capacity_trace']
            self.assertTrue(any(x['stage']=='final' for x in trace))
            self.assertTrue(all(x['unique_count']<=40 for x in trace if x['stage']!='temporary'))


if __name__=='__main__':
    unittest.main()
