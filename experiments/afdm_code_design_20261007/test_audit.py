"""Fixed algebra and artifact fixtures only; never run the scientific design/audit."""
import math
from pathlib import Path
import tempfile
import unittest

import numpy as np

from .audit import (check_adam_updates, check_checkpoint, check_energy,
                    check_saved_hash, direct_values, file_hash)


class DirectSumContracts(unittest.TestCase):
    def test_all_unlocked_gradients_by_finite_difference(self):
        phase = .09*np.arange(8)**2+.13*np.arange(8)
        answer = direct_values(phase)
        finite = []
        for coordinate in range(8):
            delta = np.eye(8)[coordinate]*1e-6
            finite.append((direct_values(phase+delta)['loss']-
                           direct_values(phase-delta)['loss'])/2e-6)
        np.testing.assert_allclose(answer['gradient'], finite, atol=3e-9, rtol=1e-7)
        self.assertGreater(abs(answer['gradient'][0]), 1e-4)
        self.assertLess(check_energy(answer, 8), 1e-12)

    def test_character_convention_against_explicit_scalar_sum(self):
        phase = .073*np.arange(8)**3
        w = np.exp(1j*phase)
        values = [sum(w[j]*w[(j-k) % 8].conjugate()*
                      np.exp(8j*np.pi*d*j/8) for j in range(8))/8
                  for k in range(1, 8) for d in range(2)]
        answer = direct_values(phase)
        self.assertAlmostEqual(answer['loss'], sum(abs(v)**16 for v in values)**(1/8), places=13)
        self.assertAlmostEqual(answer['mu'], max(abs(v) for v in values), places=13)

    def test_exact_n64_counterexamples_are_not_good_coherence_designs(self):
        # These two fixed formula checks are not a code search or optimization.
        j = np.arange(64, dtype=float)
        quadratic = direct_values(-np.pi*j*j/64)
        self.assertAlmostEqual(quadratic['mu'], 1., places=12)
        self.assertAlmostEqual(quadratic['Q'], 0., places=12)
        self.assertAlmostEqual(quadratic['energy'], 15., places=11)
        check_energy(quadratic, 64)
        cubic = direct_values(2*np.pi*j**3/64)
        self.assertAlmostEqual(cubic['mu'], 1., places=12)
        check_energy(cubic, 64)

    def test_energy_corruption_rejected(self):
        answer = direct_values(.13*np.arange(8)**2)
        answer['energy'] += .01
        with self.assertRaisesRegex(ValueError, 'restricted energy'):
            check_energy(answer, 8)

    def test_invalid_phase_inputs_rejected(self):
        for phase in (np.zeros((2, 8)), np.zeros(6), np.full(8, np.nan),
                      np.zeros(8, dtype=complex), np.array(['a']*8)):
            with self.subTest(dtype=phase.dtype, shape=phase.shape):
                with self.assertRaises(ValueError):
                    direct_values(phase)


class SavedTransitionContracts(unittest.TestCase):
    @staticmethod
    def two_step_trace():
        # Hand-specified gradients, not gradients of a scientific design.
        gradients = np.array([[17., 2., -3.], [-19., -4., 6.], [23., 0., 0.]])
        start = np.array([.37, 3.4, -3.4])
        first = start-.05*np.array([0., 2., -3.])/(np.array([0., 2., 3.])+1e-8)
        m = np.array([0., -.22, .33])/(1-.9**2)
        v = np.array([0., .019996, .044991])/(1-.999**2)
        rate = .001+.049*(1+math.cos(math.pi/199))/2
        second = first-rate*m/(np.sqrt(v)+1e-8)
        return np.array([start, first, second]), gradients

    def test_saved_adam_bias_correction_lock_and_no_wrap(self):
        phases, gradients = self.two_step_trace()
        self.assertLess(check_adam_updates(phases, gradients), 1e-12)
        self.assertGreater(phases[1, 1], np.pi)
        self.assertNotEqual(gradients[0, 0], 0.)

    def test_last_registered_rate_is_point_zero_zero_one(self):
        # A synthetic saved transition with only the last update nonzero.
        phases = np.tile(np.array([.37, .2]), (201, 1))
        gradients = np.zeros_like(phases)
        gradients[199] = [123., 2.]
        phases[200, 1] -= .001*(.2/(1-.9**200))/(math.sqrt(.004/(1-.999**200))+1e-8)
        self.assertLess(check_adam_updates(phases, gradients), 1e-12)

    def test_changed_update_and_gauge_rejected(self):
        phases, gradients = self.two_step_trace()
        changed = phases.copy()
        changed[1, 1] += 1e-5
        with self.assertRaisesRegex(ValueError, 'Adam step 1'):
            check_adam_updates(changed, gradients)
        changed = phases.copy()
        changed[:, 0] = 0.
        # A globally reset gauge is caught by the separate initial-phase check;
        # here check the update invariant rather than assuming gauge zero.
        changed[1, 0] = .01
        with self.assertRaisesRegex(ValueError, 'locked phase'):
            check_adam_updates(changed, gradients)
        changed = gradients.copy()
        changed[0, 1] = -2.
        with self.assertRaisesRegex(ValueError, 'Adam step 1'):
            check_adam_updates(phases, changed)

    def test_earliest_minimum_and_principal_root(self):
        phases = np.array([[.1, .2], [4., -4.], [5., -5.]])
        mus = np.array([.8, .6, .6])
        expected = np.exp(.25j*np.array([4.-2*np.pi, -4.+2*np.pi]))
        answer = check_checkpoint(phases, mus, expected, 1)
        self.assertTrue(answer['design_qualified'])
        with self.assertRaisesRegex(ValueError, 'earliest minimum mu'):
            check_checkpoint(phases, mus, expected, 2)
        with self.assertRaisesRegex(ValueError, 'principal fourth root'):
            check_checkpoint(phases, mus, 1j*expected, 1)

    def test_consistent_unqualified_checkpoint_is_not_audit_failure(self):
        phases = np.array([[.1, .2], [.2, .3]])
        answer = check_checkpoint(phases, np.array([.8, .79]), np.exp(.25j*phases[1]), 1)
        self.assertFalse(answer['design_qualified'])

    def test_tampered_or_missing_artifact_hash_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)/'D'
            folder.mkdir()
            path = folder/'code.npz'
            path.write_bytes(b'fixed fixture bytes, not a waveform')
            record = dict(artifact_sha256={'/remote/execution/D/code.npz': file_hash(path)})
            check_saved_hash(folder, 'code.npz', record)
            path.write_bytes(b'tampered fixture')
            with self.assertRaisesRegex(ValueError, 'artifact hash'):
                check_saved_hash(folder, 'code.npz', record)
            with self.assertRaisesRegex(ValueError, 'artifact hash'):
                check_saved_hash(folder, 'code.npz', dict(artifact_sha256={}))


if __name__ == '__main__':
    unittest.main()
