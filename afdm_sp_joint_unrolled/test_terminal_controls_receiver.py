"""Real small receiver controls; full-size qualification remains separate."""
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
from . import direction_receiver as api
from .e1_ldpc import build_code
from .supplement_feedback import CodeFeedback
from .supplement_feedback_schedule import UniformBPSchedule
from .test_supplement_feedback_adapter import tiny_adapter
from .light_gap_receiver_run import run_arm, NUMERIC_FIELDS, receiver_resources
from .trans_next_stop_run import same_receiver_state


class TerminalControlsReceiverTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.code = build_code(n=64, d_v=2, d_c=4, seed=91, cache_dir=self.tmp.name)
        self.receiver = tiny_adapter(self.code)
        self.receiver.estimator.lstsq_driver = 'gels'
        rng = np.random.default_rng(912)
        self.observed = dict(y=rng.normal(size=32)+1j*rng.normal(size=32),
            pilot=np.ones(32, complex)/2, sigma2=.2,
            constellation=np.array([.5+.5j, .5-.5j, -.5+.5j, -.5-.5j]))

    def feedback(self, **options):
        return CodeFeedback(self.code, checkpoint=0, retain_messages=True, **options)

    def test_public_controls_use_physical_variance_and_temperature_with_same_prefix(self):
        old = self.receiver.run(self.observed, code_feedback=self.feedback(), terminal_check_prior='retain')
        feedback = self.feedback()
        with patch.object(api, 'terminal_decode', wraps=api.terminal_decode) as terminal:
            value = self.receiver.run(self.observed, code_feedback=feedback,
                terminal_check_prior='retain', terminal_bp_temperature=1., terminal_variance_source='physical')
        self.assertEqual(terminal.call_count, 1)
        self.assertEqual(terminal.call_args.args[2], self.observed['sigma2'])
        self.assertEqual(terminal.call_args.kwargs['bp_temperature'], 1.)
        self.assertEqual(value['sigma2_terminal'], self.observed['sigma2'])
        self.assertTrue(value['terminal_controls_consumed'])
        self.assertFalse(value['terminal_scale_applied'])
        for field in ('H', 'x_soft', 'support', 'gains', 'dals', 'code_feedback_records', 'sigma2'):
            same_receiver_state({'state': value[field]}, {'state': old[field]})
        reference = api.terminal_decode(self.observed['y']-value['H']@self.observed['pilot'],
            value['H'], self.observed['sigma2'], self.observed['constellation'], self.code,
            code_prior=feedback.prior.numpy(), bp_temperature=1.)
        for key in ('mu', 'var', 'llr', 'decoded', 'info_hat', 'x_hard', 'decode_ok'):
            np.testing.assert_array_equal(value[key], reference[key])

    def test_explicit_none_keeps_legacy_keys_and_outputs(self):
        old = self.receiver.run(self.observed, code_feedback=self.feedback(), terminal_check_prior='retain')
        value = self.receiver.run(self.observed, code_feedback=self.feedback(), terminal_check_prior='retain',
            terminal_bp_temperature=None, terminal_variance_source=None)
        self.assertEqual(set(value), set(old))
        same_receiver_state(value, old)

    def test_stop_does_not_consume_terminal_controls(self):
        rng = np.random.default_rng(5)
        self.observed['y'] = rng.normal(size=32)+1j*rng.normal(size=32)
        old = self.receiver.run(self.observed, code_feedback=self.feedback(stop_on_valid_codeword=True),
            bp_schedule=UniformBPSchedule(outer_bp_iterations=12), terminal_check_prior='retain')
        self.assertFalse(old['terminal_executed'])
        with patch.object(api, 'terminal_decode', side_effect=AssertionError('terminal after stop')):
            value = self.receiver.run(self.observed, code_feedback=self.feedback(stop_on_valid_codeword=True),
                bp_schedule=UniformBPSchedule(outer_bp_iterations=12), terminal_check_prior='retain',
                terminal_bp_temperature=1., terminal_variance_source='physical')
        self.assertFalse(value['terminal_controls_consumed'])
        self.assertIsNone(value['sigma2_terminal'])
        self.assertNotIn('finite_message', value)
        for field in NUMERIC_FIELDS:
            np.testing.assert_array_equal(value[field], old[field])
        self.assertEqual(receiver_resources(value)['terminal_BP_calls'], 0)

    def test_registered_runner_delivers_controls_after_failed_stop(self):
        with patch.object(api, 'terminal_decode', wraps=api.terminal_decode) as terminal:
            value = run_arm(self.receiver, self.code, self.observed,
                dict(name='UNTEMPERED', receiver=dict(terminal_check_prior='retain',
                    terminal_bp_temperature=1., terminal_variance_source='physical'),
                    feedback=dict(retain_messages=True, stop_on_valid_codeword=True)))
        self.assertTrue(value['terminal_executed'])
        self.assertEqual(terminal.call_args.args[2], self.observed['sigma2'])
        self.assertEqual(terminal.call_args.kwargs['bp_temperature'], 1.)
        self.assertEqual(receiver_resources(value)['terminal_BP_calls'], 1)

    def test_invalid_or_unqualified_controls_reject_before_forward(self):
        bad = [dict(terminal_bp_temperature=v) for v in (True, 0., 3., float('nan'), '1')]
        bad += [dict(terminal_variance_source=v) for v in (True, 'residual', 'oracle')]
        bad += [dict(terminal_bp_temperature=1., detector='siso_mmse'),
                dict(terminal_variance_source='physical', terminal_transform=lambda **k: None)]
        for options in bad:
            with self.subTest(options=options), patch.object(type(self.receiver.receiver.model), '__call__',
                    side_effect=AssertionError('invalid controls reached model')):
                with self.assertRaises(ValueError):
                    self.receiver.run(self.observed, code_feedback=self.feedback(),
                        terminal_check_prior='retain', **options)
        with self.assertRaises(ValueError):
            self.receiver.run(self.observed, terminal_bp_temperature=1.)


if __name__ == '__main__':
    unittest.main()
