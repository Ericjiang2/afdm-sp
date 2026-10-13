"""Real small-code terminal tests; not full receiver FER evidence."""
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
from . import direction_receiver as receiver
from .e1_ldpc import build_code, encode, qpsk_map


class TerminalPriorTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.code = build_code(n=24, d_v=3, d_c=6, seed=20260726, cache_dir=self.tmp.name)
        self.const = np.array([1+1j, 1-1j, -1+1j, -1-1j])/2
        self.y = np.random.default_rng(81).normal(size=12)+.2j
        self.h = np.eye(12, dtype=complex)
        self.prior = np.linspace(-4, 4, 24)

    def call(self, **options):
        return receiver.terminal_decode(self.y, self.h, .7, self.const, self.code, **options)

    def test_complete_nonzero_mode_reaches_terminal_graph_and_decoder(self):
        self.h[0, 1] = 1e-6
        default = self.call(audit=True, code_prior=self.prior)
        complete = self.call(audit=True, code_prior=self.prior, bp_complete_nonzero=True)
        self.assertEqual(default['graphs'][0]['edges'], 12)
        self.assertEqual(complete['graphs'][0]['edges'], 13)
        self.assertEqual(complete['graphs'][0]['operator'], '>')
        self.assertEqual(complete['graphs'][0]['discarded_squared_frobenius'], 0.)
        self.assertEqual(complete['decoded'].shape, (24,))
        explicit = self.call(audit=True, code_prior=self.prior, bp_complete_nonzero=False)
        for key in ('mu', 'var', 'llr', 'decoded', 'info_hat'):
            np.testing.assert_array_equal(default[key], explicit[key])

    def test_prior_is_excluded_from_channel_llr_on_diagonal_channel(self):
        result = self.call(code_prior=self.prior)
        expected = np.r_[2*self.y.real/.7, 2*self.y.imag/.7]
        np.testing.assert_allclose(result['raw_llr'], expected, atol=1e-12, rtol=1e-12)
        np.testing.assert_array_equal(result['finite_message']['prior_llr'], self.prior)
        app = expected+self.prior
        mean = .5*np.tanh(app[:12]/2)+.5j*np.tanh(app[12:]/2)
        np.testing.assert_allclose(result['mu'], mean, atol=1e-12)
        np.testing.assert_allclose(result['var'], .5-abs(mean)**2, atol=1e-12)
        np.testing.assert_array_equal(result['llr'], np.clip(result['raw_llr'], -20, 20))

    def test_zero_prior_matches_existing_finite_temperature_two_path(self):
        result = self.call(code_prior=np.zeros(24))
        expected = self.call(bp_noncircular=False)
        for key in ('mu', 'var', 'llr', 'decoded', 'info_hat', 'x_hard'):
            np.testing.assert_array_equal(result[key], expected[key])

    def test_prior_changes_interfering_symbol_likelihood(self):
        self.h[0, 1] = .8+.2j
        zero = self.call(code_prior=np.zeros(24))
        prior = np.zeros(24);prior[1] = 8;prior[13] = -8
        informed = self.call(code_prior=prior)
        self.assertGreater(abs(informed['raw_llr'][0]-zero['raw_llr'][0]), .01)

    def test_empty_graph_channel_has_no_prior_information(self):
        self.h[:] = 0
        result = self.call(code_prior=self.prior)
        np.testing.assert_array_equal(result['raw_llr'], np.zeros(24))
        self.assertGreater(np.linalg.norm(result['mu']), .1)

    def test_real_codeword_and_legacy_none(self):
        info = np.random.default_rng(71).integers(0, 2, self.code['k'], dtype=np.uint8)
        coded = encode(self.code, info)
        self.y = qpsk_map(coded, scale=np.sqrt(.5))*8
        baseline = self.call()
        explicit_none = self.call(code_prior=None)
        result = self.call(code_prior=(1-2*coded.astype(float))*2)
        for key in ('mu', 'var', 'llr', 'decoded', 'info_hat', 'x_hard'):
            np.testing.assert_array_equal(baseline[key], explicit_none[key])
        np.testing.assert_array_equal(result['decoded'], coded)
        self.assertTrue(result['decode_ok'])

    def test_invalid_prior_rejected_before_bp(self):
        bad = [np.zeros(23), np.zeros((24, 1)), np.full(24, np.nan),
               np.ones(24, dtype=complex), np.ones(24, dtype=bool)]
        with patch.object(receiver, 'mp_detect_bp_torch', side_effect=AssertionError('BP called')):
            for prior in bad:
                with self.subTest(dtype=prior.dtype, shape=prior.shape), self.assertRaises(ValueError):
                    self.call(code_prior=prior)
            for options in (dict(bp_noncircular=False), dict(cavity_observer=lambda x: None),
                            dict(convergence_observer=lambda x: None), dict(bp_pseudovariance_scale=0)):
                with self.subTest(options=options), self.assertRaises(ValueError):
                    self.call(code_prior=self.prior, **options)


if __name__ == '__main__':
    unittest.main()
