"""Real tiny CE/SISO/LDPC integration; separate from N1024 qualification."""
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
import torch
from .e1_ldpc import build_code, decode_llr
from .supplement_feedback import CodeFeedback
from .supplement_feedback_schedule import UniformBPSchedule
from .test_supplement_feedback_adapter import tiny_adapter
from .direction_receiver import terminal_decode
from .light_gap_receiver_run import run_arm, receiver_resources


class SISOReceiverTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.code = build_code(n=64, d_v=2, d_c=4, seed=91, cache_dir=self.directory.name)
        rng = np.random.default_rng(912)
        self.observed = dict(y=rng.normal(size=32)+1j*rng.normal(size=32),
            pilot=np.ones(32, dtype=complex)/2, sigma2=.2,
            constellation=np.array([.5+.5j, .5-.5j, -.5+.5j, -.5-.5j]))

    def test_real_feedback_chain_uses_prior_and_common_terminal_decoder(self):
        receiver = tiny_adapter(self.code)
        fb = CodeFeedback(self.code, checkpoint=0, retain_messages=True, retain_detector_messages=True)
        with patch('afdm_sp_joint_unrolled.classical_joint_unrolled.mp_detect_bp_torch',
                   side_effect=AssertionError('SISO must not execute outer BP')), \
             patch('afdm_sp_joint_unrolled.direction_receiver.mp_detect_bp_torch',
                   side_effect=AssertionError('SISO must not execute terminal BP')):
            result = receiver.run(self.observed, detector='siso_mmse', code_feedback=fb)
        self.assertEqual(len(result['siso_calls']), 3)
        self.assertEqual(len(result['siso_states']), 3)
        self.assertEqual(len(result['dals']), 2)
        self.assertEqual(result['graphs'], [])
        self.assertNotIn('bp_schedule', result)
        decoder = next(r for r in result['code_feedback_records'] if r['stage'] == 'decoder')
        prior = decoder['prior_after']
        self.assertGreater(np.max(np.abs(prior)), 1e-8)
        np.testing.assert_array_equal(result['siso_states'][0]['consumed_prior'], np.zeros(64))
        for state in result['siso_states'][1:]+[result['terminal_siso_state']]:
            np.testing.assert_array_equal(state['consumed_prior'], prior)
            expected = .5*(np.tanh(prior[:32]/2)+1j*np.tanh(prior[32:]/2))
            np.testing.assert_allclose(state['prior_mean'], expected, rtol=0, atol=1e-15)
            self.assertLess(state['linear_relative_residual'], 1e-12)
        # The next non-checkpoint CE consumes actual SISO discrete moments.
        np.testing.assert_allclose(result['dals'][1]['mu'],
            result['siso_states'][1]['posterior_mean'].astype(result['dals'][1]['mu'].dtype), rtol=0, atol=0)
        terminal = result['terminal_siso_state']
        np.testing.assert_array_equal(result['llr'], np.clip(terminal['channel_llr'], -20, 20))
        self.assertFalse(np.array_equal(result['llr'], np.clip(terminal['posterior_llr'], -20, 20)))
        decoded, ok = decode_llr(self.code, result['llr'], maxiter=50)
        np.testing.assert_array_equal(result['decoded'], decoded)
        self.assertEqual(result['decode_ok'], bool(ok))
        self.assertEqual(sum(r['linear_solves'] for r in result['siso_calls'])+
                         result['terminal_siso']['linear_solves'], 4)

    def test_invalid_combinations_reject_before_running(self):
        receiver = tiny_adapter(self.code)
        for options in (dict(detector='unknown'), dict(detector='siso_mmse'),
                        dict(detector='siso_mmse', bp_schedule=UniformBPSchedule(outer_bp_iterations=12))):
            kwargs = dict(code_feedback=CodeFeedback(self.code, checkpoint=0))
            if options == dict(detector='siso_mmse'):
                kwargs = {}
            with self.assertRaises(ValueError):
                receiver.run(self.observed, **kwargs, **options)
        y, c = self.observed['y'], self.observed['constellation']
        for options in (dict(bp_temperature=2), dict(bp_noncircular=False), dict(device='cuda')):
            with self.assertRaises(ValueError):
                terminal_decode(y, np.eye(32), .2, c, self.code, detector='siso_mmse', **options)

    def test_registered_runner_counts_actual_siso_work(self):
        result = run_arm(tiny_adapter(self.code), self.code, self.observed,
                         dict(name='SISO_MEAN', receiver=dict(detector='siso_mmse')))
        counts = receiver_resources(result)
        self.assertEqual(counts, dict(LDPC_calls=2, CE_solves=2,
            outer_BP_calls=0, outer_BP_iterations=0, terminal_BP_calls=0, terminal_BP_iterations=0,
            outer_SISO_calls=3, terminal_SISO_calls=1, SISO_factorizations=4, SISO_rhs=132))


if __name__ == '__main__':
    unittest.main()
