"""Actual receiver reconstruction consumes the finalized gain tensor."""
import unittest
from unittest.mock import patch
import torch
from afdm_sp_joint_unrolled.classical_joint_unrolled import ClassicalJointConfig, ClassicalJointUnrolled, reconstruct_H_torch
from afdm_sp_joint_unrolled.support_transaction import finalize_support_transaction
from afdm_sp_joint_unrolled.mp_detect_bp_torch import mp_detect_bp_torch


class TransactionConsumerTests(unittest.TestCase):
    def test_committed_gain_reaches_real_reconstruction_and_bp(self):
        cfg = ClassicalJointConfig(N=16, l_max=4, k_max=1, n_paths=1,
            n_outer_iter=2, pic_iter=2, device='cpu', dtype=torch.complex128,
            rdtype=torch.float64, mp_mode='bp')
        model = ClassicalJointUnrolled(cfg, learnable_heads=('cand_active_rel',))
        eye = torch.eye(16, dtype=cfg.dtype)
        y = torch.arange(1, 17, dtype=cfg.rdtype).to(cfg.dtype)/16
        pilot = torch.ones(16, dtype=cfg.dtype)/2
        const = torch.tensor([1+1j, 1-1j, -1+1j, -1-1j], dtype=cfg.dtype)/2
        calls, events = [], []
        def transaction(phi, observed, raw, noise, k_max, extension, cap, observer):
            result = finalize_support_transaction(observed, phi, eye, raw, None,
                k_max=k_max, extension=extension, active_cap=cap)
            calls.append(result)
            return result
        with patch.object(model.cand_active_rel, 'build_features', side_effect=AssertionError('legacy repair executed')), \
                patch('afdm_sp_joint_unrolled.classical_joint_unrolled.mp_detect_bp_torch', wraps=mp_detect_bp_torch) as bp:
            output = model(y, pilot, torch.tensor(.1), const, Phi=eye[:, :15],
                receiver_extension=0, active_support_cap=1,
                support_transaction=transaction, transaction_observer=events.append)
        self.assertEqual(bp.call_count, cfg.n_outer_iter)
        torch.testing.assert_close(bp.call_args_list[0].args[0], events[2]['y_data'])
        torch.testing.assert_close(bp.call_args_list[0].args[1], events[2]['H'])
        self.assertEqual(len(calls), 1)
        self.assertEqual([e['stage'] for e in events], ['committed', 't0_reconstruction', 't0_bp_input'])
        committed = calls[0]['committed']
        for event in events[:2]:
            self.assertEqual(event['active_ids'], committed['active_ids'])
            torch.testing.assert_close(event['gains'], committed['gains'])
        expected = reconstruct_H_torch(16, committed['support_delays'], committed['support_dopplers'],
            committed['gains'], cfg.c1, cfg.c2, cfg.k_max, cdtype=cfg.dtype)
        torch.testing.assert_close(events[1]['H'], expected)
        torch.testing.assert_close(events[2]['y_data'], y-events[2]['H']@pilot)
        self.assertTrue(bool(torch.isfinite(output['H_est']).all()))
        self.assertIn('support_transaction', output)


if __name__ == '__main__':
    unittest.main()
