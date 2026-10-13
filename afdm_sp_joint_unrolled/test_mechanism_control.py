"""Common reference is fixed before arm order; arms consume its full pools."""
import unittest
from unittest.mock import patch
import numpy as np
import torch
from afdm_sp_joint_unrolled.classical_joint_unrolled import ClassicalJointConfig, ClassicalJointUnrolled
from afdm_sp_joint_unrolled.mechanism_control import prepare_mechanism_reference, make_mechanism_transaction


class MechanismControlTests(unittest.TestCase):
    def test_shared_pools_prior_and_single_complete_transaction(self):
        cfg = ClassicalJointConfig(N=16, l_max=4, k_max=1, device='cpu')
        head = ClassicalJointUnrolled(cfg, learnable_heads=('cand_active_rel',)).cand_active_rel
        head.k_add_max = 1
        phi = torch.eye(16, dtype=torch.complex128)[:, :15]
        y = torch.arange(16, 0, -1, dtype=torch.float64).to(phi.dtype)/16
        C = torch.eye(16, dtype=phi.dtype)
        lookup = lambda dl, dk, g: (np.full(len(dl), .4), np.full(len(dl), 2.))
        reference = prepare_mechanism_reference(phi, y, [0], torch.tensor(.1), C,
            head=head, lookup=lookup, l_max=4, k_max=1, nomination_cap=1, prior_reference='fixed')
        self.assertEqual(len(reference['rounds']), 2)
        keep = make_mechanism_transaction(reference, head=head, mode='projected_stats_prior',
                                         gate_enabled=True, diagnostic_keep=True)
        with patch.object(head, 'apply_f2p_refinement', side_effect=AssertionError('keep invoked F2P')):
            result = keep(phi, y, [0], torch.tensor(.1), 1, 0, 1, None)
        self.assertEqual(result['reason'], 'diagnostic_forced_keep')
        self.assertEqual(result['complete_proposals_used'], 0)
        self.assertEqual(result['score_tables'], [])
        self.assertEqual(result['committed']['active_ids'], result['baseline']['active_ids'])
        self.assertTrue(torch.equal(result['committed']['gains'], result['baseline']['gains']))
        with patch.object(head, 'build_features', side_effect=AssertionError('refilled frozen pool')):
            for mode, gate in [('legacy_stats_prior', False), ('projected_stats_prior', True)]:
                control = make_mechanism_transaction(reference, head=head, mode=mode, gate_enabled=gate)
                result = control(phi, y, [0], torch.tensor(.1), 1, 0, 1, None)
                self.assertEqual(result['complete_proposals_used'], 1)
                self.assertLessEqual(len(result['committed']['active_ids']), 1)
                for rr, table in enumerate(result['score_tables']):
                    ref = reference['rounds'][rr]
                    for row in table['candidates']:
                        index = ref['candidate_ids'].index(row['id'])
                        self.assertEqual(row['pi'], ref['pi'][index])
                        self.assertEqual(row['sh2'], ref['sh2'][index])
        bad = make_mechanism_transaction(reference, head=head, mode='ols_no_prior', gate_enabled=True)
        with self.assertRaises(ValueError): bad(phi, y*2, [0], torch.tensor(.1), 1, 0, 1, None)


if __name__ == '__main__':
    unittest.main()
