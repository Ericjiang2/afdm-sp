"""Numerical physical-operator contracts; these tests are not FER trials."""
import unittest
import tempfile
from pathlib import Path
from types import SimpleNamespace

import numpy as np

from .afdm_env import AFDMEnvMixin
from .supplement_g1 import (physical_channel_matrix, physical_observation,
                           evidence_arrays, audit_frame_evidence, summarize_physical_records)
from .budgeted_support_diagnostics import array_hash
from .supplement_pilots import propagate_cpp, transform


class PhysicalG1Tests(unittest.TestCase):
    def environment(self, n=16):
        env = object.__new__(AFDMEnvMixin)
        env.N_total, env.c1, env.c2 = n, 5 / (2 * n), .002
        env.k_max_cap, env.l_max_cap, env.rho = 2, 3, .5
        return env

    def test_zero_path_and_integer_paths_match_actual_dictionary(self):
        from .afdm_baselines import construct_sensing_matrix
        env = self.environment()
        args = (16, env.c1, env.c2)
        identity = physical_channel_matrix(*args, [0], [0], [1], prefix_length=3)
        np.testing.assert_allclose(identity, np.eye(16), atol=1e-13, rtol=0)
        delays, dopplers, gains = np.array([0, 2, 3]), np.array([-2, 1, 0]), np.array([.3j, 2, -.2j])
        h = physical_channel_matrix(*args, delays, dopplers, gains, prefix_length=3)
        reference = env.gen_h_daft(gains, delays, dopplers)
        np.testing.assert_allclose(h, reference, atol=2e-13, rtol=0)
        pilot = np.exp(.31j * np.arange(16))
        phi = construct_sensing_matrix(16, pilot, env.c1, env.c2, 3, 2)
        np.testing.assert_allclose(h @ pilot, phi[:, delays * 5 + dopplers + 2] @ gains,
                                   atol=3e-13, rtol=0)

    def test_fractional_paths_match_direct_cpp_for_general_chirps(self):
        rng = np.random.default_rng(912)
        for n, c1, c2 in ((16, 5 / 32, .002), (31, .09213, -.0017)):
            x = rng.standard_normal(n) + 1j * rng.standard_normal(n)
            delays, nu, gains = [0, 2, 3], [-1.27, .38, 1.61], [.3j, -.7, .6 + .2j]
            h = physical_channel_matrix(n, c1, c2, delays, nu, gains, prefix_length=3)
            waveform = transform(x, c1, c2, inverse=True)
            direct = transform(propagate_cpp(waveform, c1, delays, nu, gains,
                                            prefix_length=3), c1, c2)
            np.testing.assert_allclose(h @ x, direct, atol=2e-12, rtol=0)

    def test_physical_operator_does_not_rescale_gains(self):
        args = (16, 5 / 32, .002, [2], [.37])
        h = physical_channel_matrix(*args, [1], prefix_length=3)
        scaled = physical_channel_matrix(*args, [2 + 3j], prefix_length=3)
        np.testing.assert_allclose(scaled, (2 + 3j) * h, atol=1e-14)
        self.assertAlmostEqual(float(np.linalg.norm(scaled)**2 / 16), 13.)

    def test_invalid_physical_geometry_fails(self):
        base = dict(n=16, c1=5 / 32, c2=.002, delays=[1], dopplers=[.2],
                    gains=[1], prefix_length=3)
        for change in (dict(n=True), dict(prefix_length=16), dict(delays=[4]),
                       dict(delays=[1.5]), dict(delays=[]), dict(dopplers=[np.nan]),
                       dict(gains=[1, 2]), dict(c1=np.inf)):
            with self.subTest(change=change), self.assertRaises(ValueError):
                physical_channel_matrix(**dict(base, **change))

    def test_observation_retains_common_gains_and_labels_model_errors(self):
        env = self.environment()
        rng = np.random.default_rng(121)
        gains, delays, nu = np.array([.7, .3j]), np.array([0, 2]), np.array([.37, -1.26])
        h0 = env.gen_h_daft(gains, delays, np.rint(nu).astype(int))
        raw = dict(H=h0, params=dict(g_i=gains, g_i_raw=gains / 1.3, fro_scale=1.3,
                   l_i=delays, k_real=nu, P_actual=2, chan_coef_exp=gains,
                   l_exp=delays, k_exp=np.rint(nu).astype(int)),
                   pilot=np.ones(16, complex) / np.sqrt(2),
                   data=(rng.choice([-1., 1.], 16) + 1j * rng.choice([-1., 1.], 16)) / 2,
                   noise=(rng.standard_normal(16) + 1j * rng.standard_normal(16)) / np.sqrt(2),
                   sigma2=.1)
        raw['y'] = h0 @ (raw['pilot'] + raw['data']) + np.sqrt(.1) * raw['noise']
        out, diag = physical_observation(raw, env, prefix_length=3)
        self.assertIs(raw['H'], h0)
        self.assertNotIn('P_actual', out['params'])
        self.assertNotIn('chan_coef_exp', out['params'])
        np.testing.assert_array_equal(out['params']['g_i'], gains)
        self.assertEqual(out['g0_reference']['params']['P_actual'], 2)
        np.testing.assert_allclose(out['y'], out['H'] @ (out['pilot'] + out['data']) +
                                   np.sqrt(.1) * out['noise'], atol=2e-12, rtol=0)
        # Verify the finite dictionary projection by independent Frobenius inner products.
        projected = np.zeros_like(out['H'])
        for delay in range(env.l_max_cap + 1):
            for k in range(-env.k_max_cap, env.k_max_cap + 1):
                atom = env.gen_h_daft(np.array([1.]), np.array([delay]), np.array([k]))
                projected += np.vdot(atom, out['H']) / 16 * atom
        expected = np.linalg.norm(out['H'] - projected)**2 / np.linalg.norm(out['H'])**2
        self.assertAlmostEqual(diag['finite_dictionary_projection_nmse'], expected, places=12)
        self.assertGreater(diag['g0_reference_operator_nmse'], 0.)
        self.assertNotEqual(diag['g0_reference_operator_nmse'], expected)
        self.assertEqual(diag['gain_normalization'], 'reuse_g0_physical_gains_without_rescaling')
        self.assertEqual(diag['transmit_normalization'], 'none')
        self.assertAlmostEqual(diag['nominal_data_snr_db'], 10 * np.log10(.5 / .1))

    def test_raw_array_audit_recomputes_bits_and_rejects_tampering(self):
        from .direction_logging import publish_snapshot
        from .supplement_profile import score_errors
        h = np.eye(4, dtype=complex)
        arrays = dict(H=h, info=np.zeros(4, np.uint8), coded=np.zeros(8, np.uint8),
                      data=np.ones(4, complex), noise=np.zeros(4, complex))
        observed = dict(y=np.ones(4, complex) * 2, pilot=np.ones(4, complex), sigma2=np.array(.1))
        params = dict(l_i=np.array([0]), k_real=np.array([0.]), g_i=np.array([1.]),
                      g_i_raw=np.array([1.]), fro_scale=np.array(1.))
        frame = SimpleNamespace(observed=observed,
            _truth=dict(arrays, params=params, g0_reference=dict(H=h)))
        result = dict(H=h, llr=np.ones(8), decoded=np.zeros(8, np.uint8),
            info_hat=np.zeros(4, np.uint8), x_hard=np.ones(4, complex), x_soft=np.ones(4, complex),
            support=np.array([0]), gains=np.array([1.]), mu=np.ones(4, complex), var=np.ones(4))
        raw = evidence_arrays(frame, result)
        diag = dict(generator='physical_cpp_untruncated',
                    gain_normalization='reuse_g0_physical_gains_without_rescaling',
                    g0_reference_H_sha256=array_hash(h), physical_gains_sha256=array_hash(params['g_i']))
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            receipt = publish_snapshot(root / 'raw.npz', raw)
            row = dict(raw_evidence=receipt, physical_model=diag,
                input_hashes={k: array_hash(raw[k]) for k in ('y', 'H', 'pilot', 'info', 'coded', 'data', 'noise')},
                **score_errors(result, frame._truth))
            audit_frame_evidence(row, root)
            with self.assertRaisesRegex(ValueError, 'reported error counts'):
                audit_frame_evidence(dict(row, FER=1), root)
            (root / 'raw.npz').write_bytes((root / 'raw.npz').read_bytes() + b'changed')
            with self.assertRaisesRegex(ValueError, 'SHA-256 mismatch'):
                audit_frame_evidence(row, root)

    def test_summary_rejects_falsely_paired_snr_blocks(self):
        hashes = {k: k for k in ('H', 'noise', 'info', 'coded', 'pilot', 'data')}
        rows = [dict(block_id=0, SNR=snr, input_hashes=dict(hashes)) for snr in (7, 8, 9)]
        rows[1]['input_hashes']['H'] = 'different'
        with self.assertRaisesRegex(ValueError, 'pairing changed'):
            summarize_physical_records(rows, [0], (7, 8, 9))


if __name__ == '__main__':
    unittest.main()
