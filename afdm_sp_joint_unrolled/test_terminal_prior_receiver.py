"""Real small receiver wiring; full-size qualification is separately budgeted."""
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


class TerminalPriorReceiverTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.code = build_code(n=64,d_v=2,d_c=4,seed=91,cache_dir=self.tmp.name)
        self.receiver = tiny_adapter(self.code);self.receiver.estimator.lstsq_driver = 'gels'
        rng=np.random.default_rng(912)
        self.observed=dict(y=rng.normal(size=32)+1j*rng.normal(size=32),pilot=np.ones(32,complex)/2,
            sigma2=.2,constellation=np.array([.5+.5j,.5-.5j,-.5+.5j,-.5-.5j]))

    def feedback(self, **options):
        return CodeFeedback(self.code,checkpoint=0,retain_messages=True,**options)

    def test_default_and_actual_terminal_delivery_with_unchanged_outer_state(self):
        old=self.receiver.run(self.observed,code_feedback=self.feedback())
        default=self.receiver.run(self.observed,code_feedback=self.feedback(),terminal_check_prior=None)
        same_receiver_state(default,old)
        feedback=self.feedback()
        value=self.receiver.run(self.observed,code_feedback=feedback,terminal_check_prior='retain')
        for field in ('H','x_soft','support','gains','dals','code_feedback_records'):
            same_receiver_state({'state':value[field]},{'state':old[field]})
        np.testing.assert_array_equal(value['finite_message']['prior_llr'],feedback.prior.numpy())
        ref=api.terminal_decode(self.observed['y']-value['H']@self.observed['pilot'],value['H'],
            value['sigma2_terminal'],self.observed['constellation'],self.code,code_prior=feedback.prior.numpy())
        for field in ('mu','var','llr','decoded','info_hat','x_hard'):
            np.testing.assert_array_equal(value[field],ref[field])
        self.assertTrue(value['terminal_check_prior_consumed'])

    def test_actual_stop_never_consumes_terminal_prior(self):
        rng=np.random.default_rng(5);self.observed['y']=rng.normal(size=32)+1j*rng.normal(size=32)
        schedule=UniformBPSchedule(outer_bp_iterations=12)
        old=self.receiver.run(self.observed,code_feedback=self.feedback(stop_on_valid_codeword=True),bp_schedule=schedule)
        self.assertFalse(old['terminal_executed'])
        with patch.object(api,'terminal_decode',side_effect=AssertionError('terminal ran after stop')):
            value=self.receiver.run(self.observed,code_feedback=self.feedback(stop_on_valid_codeword=True),
                terminal_check_prior='retain',bp_schedule=schedule)
        self.assertFalse(value['terminal_executed']);self.assertFalse(value['terminal_check_prior_consumed'])
        self.assertNotIn('finite_message',value)
        for field in NUMERIC_FIELDS:np.testing.assert_array_equal(value[field],old[field])
        self.assertEqual(receiver_resources(value)['terminal_BP_calls'],0)

    def test_runner_and_failed_stop_consume_prior(self):
        value=run_arm(self.receiver,self.code,self.observed,
            dict(name='RETAIN',receiver=dict(terminal_check_prior='retain'),
                 feedback=dict(retain_messages=True,stop_on_valid_codeword=True)))
        self.assertTrue(value['terminal_executed'])
        self.assertTrue(value['terminal_check_prior_consumed'])
        self.assertEqual(receiver_resources(value)['terminal_BP_calls'],1)
        last=[r for r in value['code_feedback_records'] if r['stage']=='decoder'][-1]
        np.testing.assert_array_equal(value['finite_message']['prior_llr'],last['prior_after'])

    def test_invalid_route_rejected_before_receiver(self):
        for options in (dict(terminal_check_prior=True),dict(terminal_check_prior='reset'),
                        dict(terminal_check_prior='retain',detector='siso_mmse'),
                        dict(terminal_check_prior='retain',terminal_transform=lambda **k:None)):
            with self.subTest(options=options), self.assertRaises(ValueError):
                self.receiver.run(self.observed,code_feedback=self.feedback(),**options)
        for feedback in (None,self.feedback(enabled=False),self.feedback(control='zero'),self.feedback(consumer='detector')):
            with self.subTest(feedback=feedback),self.assertRaises(ValueError):
                self.receiver.run(self.observed,code_feedback=feedback,terminal_check_prior='retain')


if __name__=='__main__':unittest.main()
