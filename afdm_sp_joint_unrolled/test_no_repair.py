"""A0 must avoid repair computation rather than discard its result."""
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
import torch

from afdm_sp_joint_unrolled.classical_joint_unrolled import ClassicalJointConfig, ClassicalJointUnrolled
from afdm_sp_joint_unrolled.budgeted_support_eval import make_frame, run_frame


class NoRepairTests(unittest.TestCase):
    def setup_receiver(self, heads):
        cfg = ClassicalJointConfig(N=16, l_max=2, k_max=1, n_paths=2,
                                   n_outer_iter=2, pic_iter=2, device='cpu',
                                   dtype=torch.complex128, rdtype=torch.float64,
                                   early_stop=False, mp_mode='bp')
        return ClassicalJointUnrolled(cfg, learnable_heads=heads, use_soft_decisions=True)

    def test_forward_bypass_matches_no_head_receiver(self):
        torch.manual_seed(138)
        model = self.setup_receiver(('cand_active_rel',))
        base = self.setup_receiver(())
        pilot = torch.ones(16, dtype=torch.complex128) * .7
        y = pilot + .03 * torch.randn(16, dtype=torch.complex128)
        args = (y, pilot, torch.tensor(.1), torch.tensor([.5+.5j, .5-.5j, -.5+.5j, -.5-.5j]))
        head = model.cand_active_rel
        with patch.object(head, 'build_features', side_effect=AssertionError('A0 built features')), \
             patch.object(head, 'apply_f2p_refinement', side_effect=AssertionError('A0 ran F2P')):
            actual = model(*args, enable_support_repair=False)
        expected = base(*args)
        for key in ['H_est', 'x_soft', 'gains', 'sigma2_final']:
            torch.testing.assert_close(actual[key], expected[key], rtol=1e-9, atol=1e-9)
        with self.assertRaises(ValueError):
            model(*args, enable_support_repair='false')

    def test_a0_runner_never_prepares_H0_or_scorer(self):
        model = self.setup_receiver(('cand_active_rel',))
        params = dict(P_actual=2, taps=2, l_i=[0,1], k_real=[0.,0.], g_i=[1.+0j,.1+0j],
                      l_exp=[0,1], k_exp=[0,0], chan_coef_exp=[1.+0j,.1+0j], fro_scale=1., k_leak=2)
        system = SimpleNamespace(N_total=16, rho=.5, _zc_seq=np.ones(16, dtype=complex),
                                 generate_channel_matrix=lambda: (np.eye(16), None, params),
                                 gen_h_daft=lambda *args: (_ for _ in ()).throw(AssertionError('unused H0')))
        frame = make_frame(system, {'n':32,'k':16}, 0, 0, 8, uncoded=True)
        with patch('afdm_sp_joint_unrolled.budgeted_support_eval.afb.omp_sparse', side_effect=AssertionError('unused host OMP')), \
             patch('afdm_sp_joint_unrolled.budgeted_support_eval.make_genie_lambda', side_effect=AssertionError('unused scorer')):
            result = run_frame(model, system, {}, frame, None, ['a0'], 0, 0, 8)
        arm = result['arms']['a0']
        self.assertTrue(arm['finite'])
        self.assertEqual(arm['shared_scorer_preparation_seconds'], 0.)
        self.assertEqual(arm['rounds'], [])
        self.assertFalse(arm['support_repair_enabled'])


if __name__ == '__main__':
    unittest.main()
