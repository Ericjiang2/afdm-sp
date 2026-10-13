"""Syndrome stopping with real decoder/core, including the no-edge boundary."""
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
import torch
from .e1_ldpc import build_code, decode_llr
from .supplement_feedback import CodeFeedback
from .supplement_feedback_schedule import UniformBPSchedule
from .test_supplement_feedback_adapter import tiny_adapter
from .light_gap_receiver_run import receiver_resources, NUMERIC_FIELDS
from .trans_next_stop_run import check_prefix


class CheckpointStopTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.code = build_code(n=64, d_v=2, d_c=4, seed=91, cache_dir=self.directory.name)
        self.c = np.array([.5+.5j, .5-.5j, -.5+.5j, -.5-.5j])

    def test_real_decoder_stop_payload_and_reset(self):
        fb = CodeFeedback(self.code, checkpoint=0, stop_on_valid_codeword=True)
        fb.begin(32, 3, torch.device('cpu'))
        llr = torch.full((64,), 12., dtype=torch.float64)
        fb.capture(dict(channel_llr=llr, posterior_mean=torch.full((32,), .5+.5j, dtype=torch.complex128),
                        posterior_variance=torch.zeros(32, dtype=torch.float64)))
        fb.after_detection(0)
        result = fb.stop_result
        self.assertTrue(result['decode_ok'])
        self.assertEqual(fb.records[-1]['unsatisfied_checks'], 0)
        expected, ok = decode_llr(self.code, llr.numpy(), maxiter=50)
        np.testing.assert_array_equal(result['decoded'], expected)
        np.testing.assert_array_equal(result['decoder_input'], llr.numpy())
        self.assertTrue(ok)
        fb.begin(32, 3, torch.device('cpu'))
        self.assertIsNone(fb.stop_result)

    def test_real_chain_skips_terminal_for_bp_and_siso(self):
        # Fixed unit observation, selected to reach valid nonzero codewords in
        # both real decoders. This is a control-flow fixture, not FER evidence.
        rng = np.random.default_rng(5)
        observed = dict(y=rng.normal(size=32)+1j*rng.normal(size=32), pilot=np.ones(32, complex)/2,
                        sigma2=.2, constellation=self.c)
        for detector, no_edges in ((None, False), ('siso_mmse', False), (None, True)):
            receiver = tiny_adapter(self.code)
            receiver.estimator.lstsq_driver = 'gels'
            if no_edges:
                # Exercise BP's existing empty-graph branch after valid CE.
                receiver.receiver.model.model.cfg.bp_threshold = 1e9
                receiver.receiver.model.model.cfg.dtype = torch.complex64
            fb = CodeFeedback(self.code, checkpoint=0, retain_messages=True, stop_on_valid_codeword=True)
            options = dict(code_feedback=fb, detector=detector)
            if detector is None:
                options['bp_schedule'] = UniformBPSchedule(outer_bp_iterations=12)
            reference_options = dict(options, code_feedback=CodeFeedback(
                self.code, checkpoint=0, retain_messages=True))
            reference = receiver.run(observed, **reference_options)
            with patch('afdm_sp_joint_unrolled.direction_receiver.terminal_decode',
                       side_effect=AssertionError('terminal must not execute after valid checkpoint')):
                value = receiver.run(observed, **options)
            self.assertFalse(value['terminal_executed'])
            self.assertIsNone(value['sigma2_terminal'])
            self.assertEqual(value['decode_source'], 'checkpoint')
            self.assertEqual(value['completed_outer_detections'], 1)
            self.assertEqual(len(value['dals']), 0)
            self.assertEqual(sum(r['stage'] == 'decoder' for r in value['code_feedback_records']), 1)
            self.assertFalse(any(g['stage'] == 'final_bp' for g in value['graphs']))
            if no_edges:
                self.assertEqual(value['graphs'][0]['edges'], 0)
                np.testing.assert_array_equal(value['decoded'], np.zeros(64, dtype=np.uint8))
            else:
                self.assertGreater(int(value['decoded'].sum()), 0)
            expected, ok = decode_llr(self.code, value['llr'], maxiter=50)
            np.testing.assert_array_equal(value['decoded'], expected)
            self.assertTrue(ok)
            counts = receiver_resources(value)
            self.assertEqual(counts['LDPC_calls'], 1)
            self.assertEqual(counts['terminal_BP_calls'], 0)
            self.assertEqual(counts.get('terminal_SISO_calls', 0), 0)
            self.assertEqual(counts['CE_solves'], 0)
            self.assertTrue(check_prefix(value, reference)['prefix_exact'])
            # A stored trace must not conceal a changed consumed prior.
            value['code_feedback_records'][0]['prior_sha256'] = 'changed'
            with self.assertRaises(ValueError):
                check_prefix(value, reference)

    def test_false_default_and_failed_checkpoint_keep_terminal(self):
        rng = np.random.default_rng(912)
        observed = dict(y=rng.normal(size=32)+1j*rng.normal(size=32),
                        pilot=np.ones(32, complex)/2, sigma2=.2, constellation=self.c)
        receiver = tiny_adapter(self.code)
        receiver.estimator.lstsq_driver = 'gels'
        old = receiver.run(observed, code_feedback=CodeFeedback(self.code, checkpoint=0))
        default = receiver.run(observed, code_feedback=CodeFeedback(self.code, checkpoint=0, stop_on_valid_codeword=False))
        for field in NUMERIC_FIELDS:
            np.testing.assert_array_equal(default[field], old[field])
        self.assertEqual(set(old), set(default))
        fb = CodeFeedback(self.code, checkpoint=0, stop_on_valid_codeword=True)
        value = receiver.run(observed, code_feedback=fb)
        self.assertFalse(next(r for r in value['code_feedback_records'] if r['stage'] == 'decoder')['decode_ok'])
        self.assertTrue(value['terminal_executed'])
        for field in NUMERIC_FIELDS:
            np.testing.assert_array_equal(value[field], old[field])

    def test_invalid_stopping_controls(self):
        for options in (dict(enabled=False), dict(control='zero'), dict(consumer='detector'),
                        dict(diagnostic_perturbation=dict(bit=0, delta=0., affect_ce=False))):
            with self.assertRaises(ValueError):
                CodeFeedback(self.code, checkpoint=0, stop_on_valid_codeword=True, **options)
        with self.assertRaises(ValueError):
            CodeFeedback(self.code, checkpoint=0, stop_on_valid_codeword='yes')

    def test_actual_learned_exit_hook_is_rejected(self):
        receiver = tiny_adapter(self.code)
        receiver.receiver.model.model._early_exit_gate = {'threshold': .5}
        observed = dict(y=np.ones(32, complex), pilot=np.ones(32, complex)/2,
                        sigma2=.2, constellation=self.c)
        with self.assertRaisesRegex(ValueError, 'alternative stopping/refinement'):
            receiver.run(observed, code_feedback=CodeFeedback(
                self.code, checkpoint=0, stop_on_valid_codeword=True))


if __name__ == '__main__':
    unittest.main()
