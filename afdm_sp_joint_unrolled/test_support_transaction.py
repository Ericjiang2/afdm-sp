"""Complete-support objective and actual gain-commit counterexamples."""
import unittest
import torch
from afdm_sp_joint_unrolled.support_transaction import finalize_support_transaction
from afdm_sp_joint_unrolled.classical_joint_unrolled import ClassicalJointConfig, ClassicalJointUnrolled


class SupportTransactionTests(unittest.TestCase):
    def run_gate(self, y, before, after, **kw):
        eye = torch.eye(len(y), dtype=torch.complex128)
        return finalize_support_transaction(torch.tensor(y, dtype=eye.dtype), eye, eye,
            before, after, k_max=kw.pop('k_max', 0), extension=kw.pop('extension', 0),
            active_cap=kw.pop('active_cap', len(y)), **kw)

    def test_actual_protected_prune_rejects_pure_add_improvement(self):
        cfg = ClassicalJointConfig(N=3, l_max=0, k_max=1, device='cpu')
        model = ClassicalJointUnrolled(cfg, learnable_heads=('cand_active_rel',))
        head = model.cand_active_rel; head.k_add_max = 1
        head.set_refine_config(1, 3, True, 1)
        phi = torch.eye(3, dtype=torch.complex128)
        y = torch.tensor([1, .25, 0], dtype=phi.dtype)
        proposed, _ = head.apply_f2p_refinement(phi, y, [0], torch.tensor(.1), 0, 1, 1,
            score_override=lambda P, z, S, cols, noise: (cols == 1).to(torch.float64),
            tau_override=0.)
        self.assertEqual(proposed, [1])
        result = finalize_support_transaction(y, phi, phi, [0], proposed,
            k_max=1, extension=0, active_cap=1)
        self.assertFalse(result['accepted']); self.assertEqual(result['reason'], 'reject_worse')
        self.assertEqual(result['committed']['active_ids'], [0])
        torch.testing.assert_close(result['committed']['gains'], y[:1])
        self.assertEqual(result['stop_reason'], 'proposal_budget_exhausted')

    def test_expanded_neighbor_gains_are_refitted_before_commit(self):
        result = self.run_gate([1, 3, 2], [0], [2], k_max=1, extension=1)
        self.assertTrue(result['accepted'])
        self.assertAlmostEqual(result['baseline']['objective'], 4)
        self.assertAlmostEqual(result['proposal']['objective'], 1)
        self.assertEqual(result['committed']['active_ids'], [1, 2])
        torch.testing.assert_close(result['committed']['gains'], torch.tensor([3, 2], dtype=torch.complex128))
        self.assertEqual(result['action_kind'], 'replace')
        self.assertEqual(result['baseline']['boundary_clipped_count'], 1)

    def test_keep_drop_capacity_and_budget_have_distinct_reasons(self):
        self.assertEqual(self.run_gate([1, 0], [0], None)['reason'], 'empty_pool')
        self.assertEqual(self.run_gate([1, 0], [0], [0])['reason'], 'no_effective_support_change')
        drop = self.run_gate([1, 0], [0, 1], [0])
        self.assertEqual(drop['action_kind'], 'drop'); self.assertEqual(drop['reason'], 'reject_critical')
        self.assertEqual(self.run_gate([1, 2], [0], [0, 1], active_cap=1)['reason'], 'reject_final_capacity')
        self.assertEqual(self.run_gate([1, 2], [0, 1], [1], active_cap=1)['reason'], 'hold_current_capacity')
        self.assertEqual(self.run_gate([1, 2], [0], [1], proposal_budget=0)['reason'], 'proposal_budget_exhausted')
        with self.assertRaises(ValueError): self.run_gate([1, 2], [0], [1], lambda_size=1.)

    def test_shared_final_fit_and_full_state_restore(self):
        result = self.run_gate([1, .25], [0], [1], gate_enabled=False)
        self.assertTrue(result['accepted']); self.assertEqual(result['reason'], 'topk_no_F_gate')
        self.assertAlmostEqual(result['committed']['objective'], 1.)
        result = self.run_gate([1, .25], [0], [1])
        result['proposal']['gains'].zero_()
        torch.testing.assert_close(result['committed']['gains'], result['baseline']['gains'])
        result['committed']['gains'].zero_()
        self.assertEqual(float(result['baseline']['gains'][0].real), 1.)

    def test_rank_duplicate_covariance_and_margin_contracts(self):
        for dtype in (torch.complex128, torch.complex64):
            eye = torch.eye(3, dtype=dtype)
            phi = eye.clone(); phi[:, 2] = phi[:, 1]
            y = torch.tensor([1, 2, 0], dtype=dtype)
            kwargs = dict(k_max=0, extension=0, active_cap=3)
            proposal = finalize_support_transaction(y, phi, eye, [0], [1, 2], **kwargs)
            self.assertEqual(proposal['reason'], 'reject_final_rank')
            current = finalize_support_transaction(y, phi, eye, [1, 2], [0], **kwargs)
            self.assertEqual(current['reason'], 'hold_current_rank')
            self.assertIsNone(current['committed'])
            duplicate = finalize_support_transaction(y, eye, eye, [0], [1, 1], **kwargs)
            self.assertEqual(duplicate['reason'], 'reject_final_columns')
            with self.assertRaises(ValueError):
                finalize_support_transaction(y, eye, -eye, [0], [1], **kwargs)
            eta = 1e-10 if dtype == torch.complex128 else 1e-5
            for delta, accepted in [(eta, False), (10*eta, True)]:
                y = torch.tensor([1, (1+delta)**.5, 0], dtype=dtype)
                result = finalize_support_transaction(y, eye, eye, [0], [1], **kwargs)
                self.assertEqual(result['accepted'], accepted)
                self.assertEqual(result['margin'], eta*result['baseline']['energy'])


if __name__ == '__main__':
    unittest.main()
