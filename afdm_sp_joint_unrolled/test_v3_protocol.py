import math
import unittest

from afdm_sp_joint_unrolled.v3_protocol import (
    binomial_interval, classify_interval, color_cells, frozen_contract,
    identity_manifest, paired_fer_interval, seed_words, coherent_error_components,
)


class ProtocolTests(unittest.TestCase):
    def test_nonorthogonal_error_cancellation_retains_cross_terms(self):
        import numpy as np
        a=np.array([[1+2j,3-1j]])
        zero=np.zeros_like(a)
        result=coherent_error_components(a,dict(missing=a,gain=-a,false=zero,representation=zero))
        self.assertEqual(result['total'],0.)
        self.assertEqual(result['energies']['missing'],1.)
        self.assertEqual(result['cross_terms']['missing:gain'],-2.)
        self.assertAlmostEqual(result['closure_error'],0.)
        with self.assertRaises(ValueError):
            coherent_error_components(zero,dict(missing=a,gain=-a,false=zero,representation=zero))

    def test_registered_identities_are_disjoint_and_component_separated(self):
        hold = identity_manifest('holdout')
        engineering = identity_manifest('color_engineering')
        color = identity_manifest('color_repeat')
        self.assertEqual([len(hold),len(engineering),len(color)],[384,8,48])
        words=[tuple(seed) for row in hold+engineering+color for seed in row['seeds'].values()]
        self.assertEqual(len(words),len(set(words)))
        self.assertEqual(seed_words('holdout',0,0,'noise'),hold[0]['seeds']['noise'])
        self.assertNotEqual(seed_words('color_repeat',30,0,'noise',1),seed_words('color_repeat',30,0,'noise',2))
        with self.assertRaises(ValueError):identity_manifest('D_test')
        with self.assertRaises(ValueError):seed_words('holdout',-1,0,'noise')

    def test_zero_error_bound_is_not_zero_and_matches_closed_form(self):
        low,high=binomial_interval(0,384,.05)
        self.assertEqual(low,0.)
        self.assertAlmostEqual(high,1-math.pow(.025,1/384),places=12)
        result=paired_fer_interval([False]*384,[False]*384,4)
        self.assertLess(result['interval'][0],0.)
        self.assertGreater(result['interval'][1],.01)
        self.assertEqual(classify_interval(result['interval'],.01),'INCONCLUSIVE')

    def test_pairing_orientation_and_family_widening(self):
        ref=[True]*36+[False]*156
        cand=[False]*192
        one=paired_fer_interval(ref,cand)
        four=paired_fer_interval(ref,cand,4)
        self.assertEqual((one['wins'],one['harms'],one['delta']),(36,0,-36/192))
        self.assertLessEqual(four['interval'][0],one['interval'][0])
        self.assertGreaterEqual(four['interval'][1],one['interval'][1])
        swapped=paired_fer_interval(cand,ref)
        self.assertAlmostEqual(swapped['interval'][0],-one['interval'][1])
        with self.assertRaises(ValueError):paired_fer_interval([0],[False])

    def test_matrix_and_budget_totals(self):
        self.assertEqual(len(color_cells()),12)
        self.assertEqual(48*4*12+8*2*12+48*4*9,4224)
        c=frozen_contract()
        self.assertEqual(sum(c['maxima'][k] for k in ('initial','full_receiver','terminal')),13424)
        self.assertEqual(classify_interval([-.009,.009],.01),'EQUIVALENT_WITHIN_MARGIN')
        self.assertEqual(classify_interval([-.03,-.02],.01),'IMPROVEMENT_BEYOND_MARGIN')


if __name__=='__main__':
    unittest.main()
