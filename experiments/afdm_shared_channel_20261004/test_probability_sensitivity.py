import unittest
from experiments.afdm_shared_channel_20261004.probability_sensitivity import envelope


class SensitivityContracts(unittest.TestCase):
    def test_rule_disagreement_is_not_called_a_stable_sign(self):
        self.assertEqual(envelope([.02,-.001])['sign'],'unresolved')
        self.assertEqual(envelope([.001,.02])['sign'],'positive')
        self.assertEqual(envelope([-.001,-.02])['sign'],'negative')
        self.assertEqual(envelope([0.,.02])['sign'],'unresolved')
        self.assertEqual(envelope([1e-15,1e-12])['sign'],'unresolved')


if __name__=='__main__': unittest.main()
