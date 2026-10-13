"""Statistical sign and audit unit fixtures, not mechanism campaign evidence."""
import unittest
import numpy as np
from afdm_sp_joint_unrolled.direction_mechanism_stats import difference,interaction,paired_table


class MechanismStatisticsTests(unittest.TestCase):
    def test_improvement_sign_and_zero_bounds(self):
        result=difference([0]*32,[1]*32)
        self.assertEqual(result['FER_contrast'],-1)
        self.assertEqual(result['benefit_delta'],1)
        self.assertGreater(result['benefit_interval'][0],0)
        zero=difference([0]*32,[0]*32)
        self.assertLess(zero['benefit_interval'][0],0)
        self.assertGreater(zero['benefit_interval'][1],0)

    def test_paired_interaction_and_degenerate_flag(self):
        result=interaction([1,0,1,0],[0,0,1,0],[1,0,0,0],[0,0,0,0],[1,2,3])
        np.testing.assert_array_equal(result['blockwise_contrast'],[0,0,0,0])
        self.assertTrue(result['zero_degenerate'])
        other=interaction([1,1,0,0],[0,0,0,0],[0,0,0,0],[0,0,0,0],[1,2,3])
        self.assertEqual(other['FER_contrast'],.5)
        self.assertEqual(other['benefit_delta'],-.5)
        repeat=interaction([1,1,0,0],[0,0,0,0],[0,0,0,0],[0,0,0,0],[1,2,3])
        self.assertEqual(other,repeat)

    def test_missing_and_duplicate_fixture_records_rejected(self):
        with self.assertRaises(ValueError):paired_table([])
        row={'SNR':8,'block_id':0,'call_type':'full','arm_id':'fixture'}
        with self.assertRaises(ValueError):paired_table([row,row])


if __name__=='__main__':unittest.main()
