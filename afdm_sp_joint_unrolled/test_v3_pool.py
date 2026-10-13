import unittest
from types import SimpleNamespace

import torch

from afdm_sp_joint_unrolled.classical_joint_unrolled import construct_sensing_matrix_torch
from afdm_sp_joint_unrolled.v3_pool_run import shadow_state


class PoolTests(unittest.TestCase):
    def test_shadow_can_find_known_missing_atom_without_truth_in_score(self):
        N=1024;cfg=SimpleNamespace(N=N,c1=5/(2*N),c2=1e-6)
        n=torch.arange(N,dtype=torch.float64)
        pilot=(.5**.5*torch.exp(-1j*torch.pi*n*(n+1)/N)).to(torch.complex64)
        phi=construct_sensing_matrix_torch(N,pilot,cfg.c1,cfg.c2,102,2,cdtype=torch.complex64)
        state=dict(y=phi[:,400]+.2*phi[:,0],mu=torch.zeros_like(pilot),H=torch.eye(N,dtype=pilot.dtype),
            finite_variance=torch.full((N,),.5),sigma2=torch.tensor(.1),support_delays=torch.tensor([0]),
            support_dopplers=torch.tensor([-2]),outer_iter=0,A=phi[:,[0]])
        first=shadow_state(state,pilot,cfg,{400:1+0j},{400})
        changed=shadow_state(state,pilot,cfg,{399:1+0j},{399})
        for a,b in zip(first['views'],changed['views']):
            self.assertEqual(a['pool'],b['pool']);self.assertEqual(a['top4'],b['top4'])
            self.assertEqual(a['current']['weighted_recall'],1.)
            self.assertIn(400,a['top4'])
            self.assertNotIn(0,a['pool'])
        self.assertEqual(first['full_scan_columns'],515)


if __name__=='__main__':unittest.main()
