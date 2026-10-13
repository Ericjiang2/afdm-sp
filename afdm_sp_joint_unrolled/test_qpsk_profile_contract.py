"""Projection engineering gate separates floating tolerance from hard equality."""
import unittest
import numpy as np
from .trans_next_profile_run import compare_projection
from .light_gap_receiver_run import NUMERIC_FIELDS


class ProjectionContractTests(unittest.TestCase):
    def test_absent_terminal_variance_requires_matching_absence(self):
        reference={name:np.ones(2) for name in NUMERIC_FIELDS}
        reference['sigma2_terminal']=None
        compare_projection(dict(reference),reference,True)
        changed=dict(reference,sigma2_terminal=.2)
        with self.assertRaises(AssertionError):compare_projection(changed,reference,True)

    def test_soft_roundoff_allowed_but_changed_decoding_rejected(self):
        reference = {name: np.ones(2) for name in NUMERIC_FIELDS}
        changed = {name: value.copy() for name, value in reference.items()}
        changed['llr'][0] += 1e-7
        self.assertGreater(compare_projection(changed, reference, True)['llr'], 0)
        with self.assertRaises(AssertionError):
            compare_projection(changed, reference, False)
        changed['decoded'][0] = 0
        with self.assertRaises(AssertionError):
            compare_projection(changed, reference, True)
        changed['decoded'][0] = 1
        changed['llr'][0] += .01
        with self.assertRaises(AssertionError):
            compare_projection(changed, reference, True)


if __name__ == '__main__':
    unittest.main()
