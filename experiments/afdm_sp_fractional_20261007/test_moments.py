"""Fixed boundary fixtures; numerical execution requires the owning admission."""
import unittest

import numpy as np

from .moments import PathMoments, coordinate_log_density
from .verify import DOPPLER_NODES, GAIN_COVARIANCE, GAIN_MEAN, WEIGHTS, fixed_inputs


class MomentContracts(unittest.TestCase):
    def model(self, **changes):
        values = dict(n=8, c1=5.3/16, c2=(np.sqrt(2)-1)/128, delays=np.array([0, 3]),
                      doppler_nodes=DOPPLER_NODES, weights=np.tile(WEIGHTS, (2, 1)),
                      gain_mean=GAIN_MEAN, gain_cov=GAIN_COVARIANCE)
        return PathMoments(**dict(values, **changes))

    def test_full_complex_covariance_is_retained_without_projection(self):
        covariance = np.array(GAIN_COVARIANCE)
        model = self.model(gain_cov=covariance)
        np.testing.assert_array_equal(model.covariance, covariance)
        self.assertNotEqual(model.covariance[0, 1].imag, 0.)
        covariance[0, 1] = 0
        self.assertNotEqual(model.covariance[0, 1], 0.)
        with self.assertRaisesRegex(ValueError, 'PSD'):
            self.model(gain_cov=[[.1, .4j], [-.4j, .1]])
        with self.assertRaisesRegex(ValueError, 'Hermitian'):
            self.model(gain_cov=[[.1, .2j], [.2j, .1]])

    def test_source_validation_and_model_identity(self):
        model = self.model()
        inputs = fixed_inputs(8)
        source = model.prepare_source(inputs['pilot'], inputs['data_mean'], inputs['data_variance'])
        with self.assertRaisesRegex(ValueError, 'another path model'):
            self.model().expected_quadratic(inputs['y'], source)
        with self.assertRaisesRegex(ValueError, 'negative AF'):
            model.prepare_source(inputs['pilot'], inputs['data_mean'], -np.ones(8))
        with self.assertRaisesRegex(ValueError, 'real values'):
            model.prepare_source(inputs['pilot'], inputs['data_mean'], np.ones(8, complex))

    def test_invalid_probability_mass_is_rejected_not_renormalized(self):
        for weights in ([[0., .7, .3], WEIGHTS], [[.2, .5, .4], WEIGHTS], [[-.2, .9, .3], WEIGHTS]):
            with self.assertRaises(ValueError):
                self.model(weights=weights)

    def test_coordinate_prior_support_and_constant_coefficient(self):
        coefficients = np.zeros(8, complex)
        coefficients[0] = 1+2j
        actual = coordinate_log_density(coefficients, [-.7, .2, 1.1], .5, [0., -np.inf, -.3])
        np.testing.assert_array_equal(actual, [4., -np.inf, 3.7])
        with self.assertRaisesRegex(ValueError, 'noise variance'):
            coordinate_log_density(coefficients, [0.], 0., [0.])
        with self.assertRaisesRegex(ValueError, 'log prior'):
            coordinate_log_density(coefficients, [0.], .5, [np.nan])


if __name__ == '__main__':
    unittest.main()
