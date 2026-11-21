import copy
import unittest

from afdm_sp_joint_unrolled.budgeted_support_analyze import physical_matches,validate_clusters


class DiagnosticAnalysisTests(unittest.TestCase):
    def test_one_atom_cannot_match_two_physical_paths(self):
        params={'l_i':[2,2],'k_real':[.1,.2]}
        self.assertEqual(physical_matches(params,[(2,0)]),1)
        self.assertEqual(physical_matches(params,[(3,0)]),0)

    def test_cross_snr_noise_mismatch_fails(self):
        rows=[dict(replicate=0,frame_index=0,snr=s,channel_seed=1,
                   input_hashes={k:'a'*64 for k in ('H','noise','info','coded','pilot')}) for s in (7,8,9)]
        validate_clusters(rows)
        wrong=copy.deepcopy(rows)
        wrong[1]['input_hashes']['noise']='b'*64
        with self.assertRaisesRegex(ValueError,'source mismatch: noise'):
            validate_clusters(wrong)

    def test_duplicate_condition_fails(self):
        rows=[dict(replicate=0,frame_index=0,snr=s,channel_seed=1,input_hashes={}) for s in (7,7,9)]
        with self.assertRaisesRegex(ValueError,'missing or duplicate'):
            validate_clusters(rows)


if __name__=='__main__':
    unittest.main()
