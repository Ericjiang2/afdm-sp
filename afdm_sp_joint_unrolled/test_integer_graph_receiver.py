"""Real small full-chain equivalence; N1024 qualification remains separate."""
import unittest
from unittest.mock import patch
import numpy as np
import torch
from . import classical_joint_unrolled as model_api
from . import test_terminal_prior_receiver as fixtures
from .supplement_feedback_schedule import UniformBPSchedule
from .light_gap_receiver_run import run_arm
from .trans_next_stop_run import same_receiver_state


class IntegerGraphReceiverTests(unittest.TestCase):
    setUp = fixtures.TerminalPriorReceiverTests.setUp
    feedback = fixtures.TerminalPriorReceiverTests.feedback

    def test_default_none_exact_and_real_coo_delivery(self):
        old = self.receiver.run(self.observed, code_feedback=self.feedback())
        default = self.receiver.run(self.observed, code_feedback=self.feedback(), outer_bp_graph=None)
        same_receiver_state(default, old)
        layouts = []
        original = model_api.mp_detect_bp_torch
        def capture(y, H, *args, **kwargs):
            layouts.append(H.layout)
            return original(y, H, *args, **kwargs)
        with patch.object(model_api, 'mp_detect_bp_torch', side_effect=capture):
            value = self.receiver.run(self.observed, code_feedback=self.feedback(), outer_bp_graph='integer')
        self.assertEqual(layouts, [torch.sparse_coo]*3)
        same_receiver_state(value, old)
        self.assertEqual(value['outer_bp_graph'], 'integer')

    def test_retained_prior_and_qpsk_full_numeric_exact(self):
        for projection in (None, 'qpsk_tanh'):
            options=dict(terminal_check_prior='retain', bp_edge_projection=projection)
            old=self.receiver.run(self.observed, code_feedback=self.feedback(), **options)
            value=self.receiver.run(self.observed, code_feedback=self.feedback(), outer_bp_graph='integer', **options)
            same_receiver_state(value, old)

    def test_registered_runner_retained_terminal_exact(self):
        rng=np.random.default_rng(5);self.observed['y']=rng.normal(size=32)+1j*rng.normal(size=32)
        arm=dict(name='REFERENCE',receiver=dict(terminal_check_prior='retain'),
                 feedback=dict(retain_messages=True,stop_on_valid_codeword=True))
        old=run_arm(self.receiver,self.code,self.observed,arm)
        self.assertTrue(old['terminal_executed'])
        arm['receiver']['outer_bp_graph']='integer'
        value=run_arm(self.receiver,self.code,self.observed,arm)
        same_receiver_state(value,old)
        self.assertTrue(value['terminal_check_prior_consumed'])

    def test_real_stop_exact(self):
        rng=np.random.default_rng(5);self.observed['y']=rng.normal(size=32)+1j*rng.normal(size=32)
        options=dict(terminal_check_prior='retain',bp_schedule=UniformBPSchedule(outer_bp_iterations=12))
        old=self.receiver.run(self.observed,code_feedback=self.feedback(stop_on_valid_codeword=True),**options)
        self.assertFalse(old['terminal_executed'])
        value=self.receiver.run(self.observed,code_feedback=self.feedback(stop_on_valid_codeword=True),
            outer_bp_graph='integer',**options)
        same_receiver_state(value,old)
        self.assertFalse(value['terminal_check_prior_consumed'])

    def test_invalid_mode_and_extra_support_routes_rejected(self):
        for mode in (True,'sparse','dense'):
            with self.subTest(mode=mode),self.assertRaises(ValueError):
                self.receiver.run(self.observed,outer_bp_graph=mode)
        with self.assertRaises(ValueError):
            self.receiver.run(self.observed,code_feedback=self.feedback(),outer_bp_graph='integer',detector='siso_mmse')
        model=self.receiver.receiver.model.model
        with patch.object(model,'off_support_corr',object()), self.assertRaises(ValueError):
            self.receiver.run(self.observed,outer_bp_graph='integer')


if __name__ == '__main__':
    unittest.main()
