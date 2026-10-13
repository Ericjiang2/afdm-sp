"""Interface contracts use mocks; the production off replay belongs to quote."""
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import numpy as np

from experiments.afdm_structured_inference_20261003 import local_receiver as adapter


class ReceiverContract(unittest.TestCase):
    def setUp(self):
        self.obs = dict(y=np.zeros(1024, complex), pilot=np.ones(1024, complex), sigma2=.1)
        self.system = SimpleNamespace(N_total=1024, rho=.5, c1=.1, c2=.01)
        self.code = object()

    def test_off_is_direct_delegation_without_candidate_import(self):
        result = object()
        native = SimpleNamespace(receive=Mock(return_value=result))
        with patch.object(adapter, '_native', return_value=native), patch.object(adapter, '_candidate') as candidate:
            self.assertIs(adapter.receive(self.obs, self.system, self.code), result)
        native.receive.assert_called_once_with(self.obs, self.system, self.code, rounds=2, iterations=20)
        candidate.assert_not_called()

    def test_observed_boundary_and_schedule_reject_before_computation(self):
        cases = [(dict(self.obs, truth=1), {}), (dict(self.obs, sigma2=np.nan), {}),
                 (dict(self.obs, pilot=np.zeros(3)), {}), (self.obs, dict(enabled=1)),
                 (self.obs, dict(enabled=True, rounds=2)),
                 (self.obs, dict(enabled=True, rounds=1, block_size=True))]
        with patch.object(adapter, '_native', return_value=Mock()) as native, patch.object(adapter, '_candidate') as candidate:
            for obs, options in cases:
                with self.subTest(options=options), self.assertRaises((ValueError, TypeError)):
                    adapter.receive(obs, self.system, self.code, **options)
        candidate.assert_not_called()
        native.return_value.pilot_front.assert_not_called()

    def test_one_pass_uniform_gain_prior_and_original_decoder(self):
        channel = SimpleNamespace(p=2, delays=np.array([0, 1]), dopplers=np.array([.1, -.2]), gains=np.array([9j, 7.]))
        state = dict(mu=np.zeros(1024), v=np.full(1024, .5), delays=channel.delays,
                     dopplers=channel.dopplers, gains=channel.gains)
        ext = np.linspace(-30, 30, 2048)
        decoder = dict(decoded=np.zeros(2048), incoming_llr=np.clip(ext,-20,20),
                       raw_app=np.zeros(2048), raw_check_extrinsic=np.ones(2048), iterations=3)
        native = SimpleNamespace(pilot_front=Mock(return_value=state),
                                 time_refine=Mock(return_value=(channel, dict(history=[1.], gamma=np.eye(2), evaluations=3, fft_count=3))),
                                 decoder_messages=Mock(return_value=decoder), scalar_joint=Mock())
        candidate = SimpleNamespace(CollapsedModel=Mock(), gaussian_pair_pass=Mock(return_value=dict(
            app=ext, extrinsic=ext, blocks=512, likelihood_evaluations=8192, fft_count=1026)))
        with patch.object(adapter, '_native', return_value=native), patch.object(adapter, '_candidate', return_value=candidate):
            result, arrays, timing = adapter.receive(self.obs, self.system, self.code, enabled=True, rounds=1)
        self.assertIs(result, decoder)
        native.scalar_joint.assert_not_called()
        self.assertEqual(native.decoder_messages.call_count, 1)
        np.testing.assert_array_equal(native.decoder_messages.call_args.args[1], np.clip(ext,-20,20))
        self.assertEqual(native.decoder_messages.call_args.kwargs, dict(maxiter=50))
        args = candidate.CollapsedModel.call_args.args
        np.testing.assert_array_equal(args[1], np.zeros(2))
        np.testing.assert_array_equal(args[2], np.eye(2)/2)
        np.testing.assert_array_equal(candidate.gaussian_pair_pass.call_args.args[3], np.zeros(2048))
        self.assertNotIn('r0_gains', arrays)
        self.assertEqual(len(timing['events']), 1)


if __name__ == '__main__':
    unittest.main()
