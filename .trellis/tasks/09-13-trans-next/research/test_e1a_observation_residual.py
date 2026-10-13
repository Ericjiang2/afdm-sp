import importlib.util
from pathlib import Path
import unittest
import numpy as np

path = Path(__file__).with_name('e1a-observation-residual-v1.py')
spec = importlib.util.spec_from_file_location('observation_residual', path)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class ObservationResidualTest(unittest.TestCase):
    def inputs(self):
        rng = np.random.default_rng(5821)
        def z(shape):
            return rng.normal(size=shape) + 1j*rng.normal(size=shape)
        H, B, p, d, c, noise = z((7, 7)), z((7, 7)), z(7), z(7), z(7), z(7)
        return [H@(p+d)+noise, H, B, p, d, c, noise, .4]

    def test_reconstruction_and_independent_gram(self):
        args = self.inputs()
        y, H, B, p, d, c, n, sigma = args
        out = m.decompose(*args)
        np.testing.assert_allclose(out['residual'], y-c-B@d, atol=1e-12)
        np.testing.assert_allclose(out['terms'][0], H@p-c, atol=1e-12)
        np.testing.assert_allclose(out['terms'][1], H@d-B@d, atol=1e-12)
        explicit = np.array([[np.vdot(a, b) for b in out['terms']] for a in out['terms']])
        np.testing.assert_allclose(out['gram'], explicit, atol=1e-12)
        self.assertAlmostEqual(out['metrics']['total_over_noise'], np.linalg.norm(y-c-B@d)**2/(7*sigma))

    def test_exact_channel_leaves_only_noise(self):
        args = self.inputs()
        args[2] = args[1].copy()
        args[5] = args[1]@args[3]
        out = m.decompose(*args)
        self.assertEqual(out['metrics']['clean_over_noise'], 0.)
        np.testing.assert_allclose(out['residual'], args[6], atol=1e-12)

    def test_noise_fitting_is_not_clean_accuracy(self):
        H = np.eye(2, dtype=complex)
        d = np.ones(2, dtype=complex)
        out = m.decompose(2*d, H, 2*H, 0*d, d, 0*d, d, 1.)
        self.assertEqual(out['metrics']['total_over_noise'], 0.)
        self.assertEqual(out['metrics']['clean_over_noise'], 1.)
        self.assertEqual(out['metrics']['clean_noise_cross_over_noise'], -2.)

    def test_paired_detector_identity(self):
        args = self.inputs()
        first = m.decompose(*args)
        second_args = list(args)
        second_args[2] = args[2] + .2*args[1]
        second = m.decompose(*second_args)
        delta = (second_args[2]-args[2])@args[4]
        direct = np.vdot(second['residual'], second['residual']).real - np.vdot(first['residual'], first['residual']).real
        predicted = np.vdot(delta, delta).real - 2*np.vdot(delta, first['residual']).real
        self.assertAlmostEqual(direct, predicted, places=10)

    def test_saved_rounding_preserved_large_defect_rejected(self):
        args = self.inputs()
        args[0] = args[0]+1e-8
        out = m.decompose(*args)
        self.assertGreater(np.linalg.norm(out['terms'][3]), 0)
        args[0] = args[0]+.01
        with self.assertRaises(ValueError):
            m.decompose(*args)

    def test_invalid_inputs_rejected(self):
        for sigma in (0, -1, np.nan, np.inf):
            args = self.inputs()
            args[-1] = sigma
            with self.assertRaises(ValueError):
                m.decompose(*args)
        args = self.inputs()
        args[4][0] = np.nan
        with self.assertRaises(ValueError):
            m.decompose(*args)
        args = self.inputs()
        args[2] = args[2][:-1]
        with self.assertRaises(ValueError):
            m.decompose(*args)


if __name__ == '__main__':
    unittest.main()
