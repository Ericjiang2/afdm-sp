"""Statistical sign, pairing and multiplicity contracts on exact binary fixtures."""
import unittest
import numpy as np
from .bottleneck_analyze import cp, holm, paired


class InferenceTests(unittest.TestCase):
    def test_paired_gain_uses_discordance_and_reverses_sign(self):
        a=np.array([1,1,1,0,0,0])
        b=np.array([0,0,1,1,0,0])
        value=paired(a,b)
        self.assertEqual((value['wins'],value['losses'],value['both_wrong']),(2,1,1))
        self.assertAlmostEqual(value['delta'],1/6)
        reverse=paired(b,a)
        self.assertAlmostEqual(reverse['delta'],-value['delta'])
        self.assertAlmostEqual(reverse['CI'][0],-value['CI'][1])
        self.assertAlmostEqual(reverse['CI'][1],-value['CI'][0])
        self.assertEqual(value['mcnemar_p'],1.)

    def test_all_zero_is_not_zero_error_probability(self):
        value=paired(np.zeros(64),np.zeros(64))
        self.assertEqual(value['mcnemar_p'],1.)
        self.assertEqual(value['delta'],0.)
        self.assertLess(value['CI'][0],0)
        self.assertGreater(value['CI'][1],0)
        self.assertAlmostEqual(cp(0,64,.025)[1],1-.025**(1/64))

    def test_family_interval_is_wider_and_holm_is_monotone(self):
        a=np.ones(64,dtype=int);b=np.zeros(64,dtype=int)
        ordinary=paired(a,b)
        family=paired(a,b,.05/18)
        self.assertLess(family['CI'][0],ordinary['CI'][0])
        self.assertEqual(family['CI'][1],1.)
        np.testing.assert_allclose(holm([.03,.001,.01,1.]),[.06,.004,.03,1.])

    def test_mismatched_or_nonbinary_vectors_are_rejected(self):
        for a,b in [([],[]),([1],[1,0]),([0,2],[0,1])]:
            with self.assertRaises(ValueError):paired(a,b)


if __name__=='__main__':
    unittest.main()
