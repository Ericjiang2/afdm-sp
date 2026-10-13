"""Numerical auditor checks a distinct cavity system and rejects corrupt input."""
import copy
import unittest
import numpy as np
from .supplement_siso_mmse import siso_mmse
from .trans_next_siso_audit import check_siso_state, finite_arrays


class SISOAuditTests(unittest.TestCase):
    def test_cavity_checks_and_corruption(self):
        rng = np.random.default_rng(771)
        H = rng.normal(size=(7, 7))+1j*rng.normal(size=(7, 7))
        y = rng.normal(size=7)+1j*rng.normal(size=7)
        prior = rng.normal(size=14)
        state = dict(siso_mmse(y, H, .2, prior), y=y, H=H, sigma2=.2, consumed_prior=prior)
        self.assertLess(check_siso_state(state), 1e-10)
        self.assertIsNone(check_siso_state(state, cavity=False))
        altered = copy.deepcopy(state)
        altered['extrinsic_precision'][0] += .001
        with self.assertRaises(AssertionError):
            check_siso_state(altered)
        self.assertGreater(finite_arrays(state), 10)
        altered['H'][0, 0] = np.nan
        with self.assertRaises(ValueError):
            finite_arrays(altered)


if __name__ == '__main__':
    unittest.main()
