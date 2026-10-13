"""Receiver capacity is independent of the simulated leakage expansion."""
import unittest

import torch

from afdm_sp_joint_unrolled.classical_joint_unrolled import (
    ClassicalJointConfig, ClassicalJointUnrolled, resolve_receiver_capacity,
)


class DirectCapacityTests(unittest.TestCase):
    def test_direct_domain_and_legacy_mapping(self):
        self.assertEqual(resolve_receiver_capacity('direct40', 40, 2, 2), (40, 0))
        self.assertEqual(resolve_receiver_capacity('legacy', 40, 2, 2), (8, 2))
        self.assertEqual(resolve_receiver_capacity('legacy', None, 2, 2), (None, 2))
        for shell, cap in [('direct40', None), ('direct40', 8), ('direct40', 40.), ('unknown', 40)]:
            with self.assertRaises(ValueError):
                resolve_receiver_capacity(shell, cap, 2, 2)

    def receiver(self):
        cfg = ClassicalJointConfig(N=16, l_max=2, k_max=1, k_leak=2,
                                   n_paths=2, n_outer_iter=2, pic_iter=2,
                                   dtype=torch.complex128, rdtype=torch.float64,
                                   device='cpu', early_stop=False, mp_mode='bp')
        model = ClassicalJointUnrolled(cfg, learnable_heads=(), use_soft_decisions=True)
        pilot = torch.ones(16, dtype=cfg.dtype) * .7
        y = pilot + torch.arange(16, dtype=torch.float64).to(cfg.dtype) * .001
        const = torch.tensor([.5+.5j, .5-.5j, -.5+.5j, -.5-.5j], dtype=cfg.dtype)
        return model, (y, pilot, torch.tensor(.1, dtype=cfg.rdtype), const)

    def test_zero_receiver_extension_preserves_simulator_config(self):
        model, args = self.receiver()
        result = model(*args, oracle_support=[1, 7], active_support_cap=2,
                       receiver_extension=0)
        self.assertEqual(model.cfg.k_leak, 2)
        self.assertEqual(len(result['support_delays']), 2)
        self.assertEqual([x['stage'] for x in result['capacity_trace']],
                         ['initial', 'outer', 'outer', 'final'])
        self.assertTrue(all(x['unique_count'] == 2 for x in result['capacity_trace']))

    def test_invalid_and_duplicate_support_rejected(self):
        model, args = self.receiver()
        for ext in [-1, .5, True]:
            with self.assertRaises(ValueError):
                model(*args, receiver_extension=ext)
        with self.assertRaises(ValueError):
            model(*args, active_support_cap=True)
        with self.assertRaisesRegex(ValueError, 'unique'):
            model(*args, oracle_support=[1, 1], active_support_cap=2, receiver_extension=0)
        with self.assertRaisesRegex(ValueError, 'capacity'):
            model(*args, oracle_support=[1, 4, 7], active_support_cap=2, receiver_extension=0)
        with self.assertRaisesRegex(ValueError, 'integer'):
            model(*args, oracle_support=[1.5], active_support_cap=2, receiver_extension=0)

    def test_temporary_union_has_separate_budget(self):
        cfg = ClassicalJointConfig(N=16, l_max=4, k_max=1, device='cpu')
        model = ClassicalJointUnrolled(cfg, learnable_heads=('cand_active_rel',))
        head = model.cand_active_rel
        head.set_refine_config(1, 10, True, 1)
        Phi = torch.eye(16, dtype=torch.complex128)[:, :15]
        y = torch.arange(1, 17, dtype=torch.float64).to(torch.complex128)
        trace = []
        support, gains = head.apply_f2p_refinement(
            Phi, y, [0, 1], torch.tensor(.1), 4, 1, 2,
            score_override=lambda P, z, S, cols, noise: cols.to(torch.float64),
            tau_override=-1e9,
            capacity_observer=lambda S, r, budget: trace.append((S, r, budget)))
        self.assertTrue(trace)
        self.assertGreater(len(trace[0][0]), 2)
        self.assertEqual(trace[0][2], 2 + head.k_add_max)
        self.assertLessEqual(len(support), 2)
        self.assertEqual(gains.numel(), len(support))

    def test_good_complex_solve_contract(self):
        torch.manual_seed(417)
        for dtype, tolerance in [(torch.complex128, 1e-10), (torch.complex64, 1e-4)]:
            A = torch.randn(12, 5, dtype=dtype)
            C = A.conj().T @ A + torch.eye(5, dtype=dtype)
            b = torch.randn(5, 2, dtype=dtype)
            x = torch.linalg.solve(C, b)
            residual = torch.linalg.vector_norm(C @ x - b) / torch.linalg.vector_norm(b)
            self.assertLessEqual(float(residual), tolerance)


if __name__ == '__main__':
    unittest.main()
