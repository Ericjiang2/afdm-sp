"""Fixed small-N algebra checks; no scientific code search."""
import unittest

import numpy as np

from .core import evaluate


class PhaseContracts(unittest.TestCase):
    def test_gradient_and_restricted_energy(self):
        n = 8
        phase = .071*np.arange(n)**3+.13*np.arange(n)
        answer = evaluate(phase)
        h = 1e-6
        finite = []
        for index in range(n):
            direction = np.eye(n)[index]*h
            finite.append((evaluate(phase+direction)['loss']-evaluate(phase-direction)['loss'])/(2*h))
        np.testing.assert_allclose(answer['gradient'], finite, atol=2e-9, rtol=1e-6)
        self.assertAlmostEqual(float(answer['gradient'].sum()), 0., places=12)
        self.assertAlmostEqual(answer['energy'], (n//4-1)+(n//4)*answer['Q'], places=12)
        self.assertGreaterEqual(answer['mu']**2+1e-12, (1+answer['Q'])/(n+3))

    def test_cazac_optimal_energy_can_have_perfect_ambiguity(self):
        n = 8
        answer = evaluate(-np.pi*np.arange(n)**2/n)
        self.assertAlmostEqual(answer['energy'], n//4-1, places=12)
        self.assertAlmostEqual(answer['mu'], 1., places=12)

    def test_invalid_phases_fail(self):
        for phase in (np.zeros(6), np.zeros((2, 8)), np.full(8, np.nan)):
            with self.assertRaises(ValueError):
                evaluate(phase)


if __name__ == '__main__':
    unittest.main()
