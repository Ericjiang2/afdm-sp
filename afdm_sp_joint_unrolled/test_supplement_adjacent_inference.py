"""Analytic sign, simultaneous-tail and sample-size checks; no receiver samples."""
import unittest
import numpy as np

from supplement_adjacent_inference import paired_fer


class PairedInferenceTests(unittest.TestCase):
    def test_all_new_failures_are_harm_not_benefit(self):
        row=paired_fer(np.ones(2048),np.zeros(2048),alpha=.025,comparisons=6)
        self.assertEqual(row['difference'],1)
        self.assertEqual(row['n10'],2048)
        self.assertEqual(row['n01'],0)
        self.assertGreater(row['lower'],.99)

    def test_zero_discordance_has_nonzero_exact_upper(self):
        row=paired_fer(np.zeros(2048),np.zeros(2048),alpha=.025,comparisons=6)
        expected=1-(.025/24)**(1/2048)
        self.assertAlmostEqual(row['upper'],expected,places=13)
        self.assertAlmostEqual(row['lower'],-expected,places=13)
        self.assertLess(row['upper'],.005)
        smaller=paired_fer(np.zeros(1024),np.zeros(1024),alpha=.025,comparisons=6)
        self.assertGreater(smaller['upper'],.005)

    def test_sign_reversal_preserves_pairing(self):
        a=np.array([0,0,1,0,1,0,0,1]*8)
        b=np.array([1,1,1,0,1,1,0,1]*8)
        x=paired_fer(a,b,alpha=.05,comparisons=12)
        y=paired_fer(b,a,alpha=.05,comparisons=12)
        self.assertEqual(x['difference'],-y['difference'])
        self.assertAlmostEqual(x['lower'],-y['upper'])
        self.assertAlmostEqual(x['upper'],-y['lower'])
        self.assertEqual(x['n'],64)

    def test_nonbinary_or_unpaired_inputs_rejected(self):
        for a,b in [([0,1],[0]),([0,2],[0,1]),([0,float('nan')],[0,0]),([],[])]:
            with self.assertRaises(ValueError):
                paired_fer(a,b,alpha=.025,comparisons=6)


if __name__=='__main__':
    unittest.main()
