"""Frozen pools enter the real F2P generation boundary, without MF refill."""
import unittest
from unittest.mock import patch
import torch
from afdm_sp_joint_unrolled.classical_joint_unrolled import ClassicalJointConfig, ClassicalJointUnrolled


class FrozenProposalTests(unittest.TestCase):
    def test_no_dynamic_pool_and_exact_tie_uses_frozen_order(self):
        cfg = ClassicalJointConfig(N=16, l_max=4, k_max=1, device='cpu')
        head = ClassicalJointUnrolled(cfg, learnable_heads=('cand_active_rel',)).cand_active_rel
        head.k_add_max = 1
        head.set_refine_config(1, 3, True, 1)
        phi = torch.eye(16, dtype=torch.complex128)[:, :15]
        y = torch.zeros(16, dtype=phi.dtype); y[0] = 10; y[14] = 1
        snapshots = [[0, 14, 13]]; events = []
        def score(P, z, S, columns, noise):
            self.assertEqual(columns.tolist(), [14, 13])
            return torch.ones(2, dtype=torch.float64)
        with patch.object(head, 'build_features', side_effect=AssertionError('dynamic pool used')):
            selected, _ = head.apply_f2p_refinement(phi, y, [0], torch.tensor(.1), 4, 1, 1,
                score_override=score, tau_override=float('-inf'), frozen_candidates=snapshots,
                stable_selection=True, proposal_covariance=torch.eye(16, dtype=phi.dtype),
                proposal_observer=events.append)
        self.assertEqual(selected, [14]); self.assertEqual(snapshots, [[0, 14, 13]])
        self.assertEqual(events[0]['frozen_count'], 3)
        self.assertEqual(events[0]['candidate_ids'], [14, 13])
        self.assertEqual(events[-1]['protected_ids'], [14])
        self.assertEqual(events[-1]['pruned_ids'], [0])


if __name__ == '__main__':
    unittest.main()
