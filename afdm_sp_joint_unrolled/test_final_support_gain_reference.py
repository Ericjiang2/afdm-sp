import unittest
from afdm_sp_joint_unrolled.final_support_gain_reference import frozen_support

class FrozenSupportTests(unittest.TestCase):
    def test_uses_actual_final_support_and_rejects_changed_trajectory(self):
        ids=list(range(40))
        record={'arms':{'baseline':{'capacity_trace':[{'stage':'outer','outer_iter':i,'atom_ids':ids.copy()} for i in range(10)]+[{'stage':'final','atom_ids':ids.copy()}],'sigma2_final':.1,'nmse':.1}}}
        self.assertEqual(frozen_support(record,2,1024).tolist(),ids)
        record['arms']['baseline']['capacity_trace'][-1]['atom_ids'][-1]=39.5
        with self.assertRaisesRegex(ValueError,'integer support'):frozen_support(record,2,1024)
        record['arms']['baseline']['capacity_trace'][-1]['atom_ids'][-1]=39
        record['arms']['baseline']['capacity_trace'][0]['atom_ids'][-1]=99
        with self.assertRaisesRegex(ValueError,'fixed outer support'):frozen_support(record,2,1024)

if __name__=='__main__':unittest.main()
