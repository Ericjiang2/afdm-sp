"""Actual tiny receiver schedule tests, not production cost or checkpoint selection."""
import unittest
from unittest.mock import patch
from dataclasses import FrozenInstanceError
import numpy as np
from .supplement_feedback_schedule import UniformBPSchedule
from .test_supplement_feedback_adapter import tiny_adapter
from . import test_supplement_feedback_adapter as adapter_tests
from .supplement_feedback_diagnostic import DiagnosticCodeSymbols
from . import classical_joint_unrolled as joint
from . import direction_receiver as terminal


class ScheduleTests(unittest.TestCase):
    setUp=adapter_tests.FeedbackAdapterTests.setUp
    def test_schedule_domain_immutable(self):
        for invalid in (0,21,True,1.,None):
            with self.assertRaises(ValueError):UniformBPSchedule(invalid)
        schedule=UniformBPSchedule(2)
        with self.assertRaises(FrozenInstanceError):schedule.outer_bp_iterations=3
        with self.assertRaises(ValueError):tiny_adapter(self.code).run(self.observed,bp_schedule={'outer_bp_iterations':2})

    def test_default_and_explicit_original_and_reduced_calls(self):
        adapter=tiny_adapter(self.code);baseline=adapter.run(self.observed)
        same=adapter.run(self.observed,bp_schedule=UniformBPSchedule(3))
        for key in ('H','x_soft','mu','var','llr','decoded'):
            np.testing.assert_allclose(baseline[key],same[key],rtol=1e-12,atol=1e-12)
        self.assertNotIn('bp_schedule',baseline)
        # Spies wrap actual operators: all CE/BP/LDPC arithmetic still executes.
        with patch.object(joint,'mp_detect_bp_torch',wraps=joint.mp_detect_bp_torch) as outer, \
                patch.object(terminal,'mp_detect_bp_torch',wraps=terminal.mp_detect_bp_torch) as final:
            reduced=adapter.run(self.observed,bp_schedule=UniformBPSchedule(1))
        self.assertEqual([c.kwargs['n_iter'] for c in outer.call_args_list],[1]*3)
        self.assertEqual([c.kwargs['n_iter'] for c in final.call_args_list],[20])
        self.assertEqual(adapter.receiver.model.cfg.pic_iter,3)
        self.assertEqual(adapter.receiver.model.cfg.n_outer_iter,3)
        self.assertEqual([r['executed_iterations'] for r in reduced['bp_schedule']['calls']],[1]*3)
        self.assertEqual(reduced['decoded'].shape,(64,))

    def test_diagnostic_route_schedule(self):
        adapter=tiny_adapter(self.code)
        diagnostic=DiagnosticCodeSymbols(self.code,np.full(32,.5+.5j),tag='I2realloc',checkpoint=0)
        result=adapter.run_diagnostic(self.observed,diagnostic_code_symbols=diagnostic,bp_schedule=UniformBPSchedule(2))
        self.assertEqual(result['bp_schedule']['outer_bp_iterations'],2)
        self.assertEqual(result['diagnostic_consumption_records'][0]['status'],'consumed')
        self.assertEqual(result['decoded'].shape,(64,))


if __name__=='__main__':unittest.main()
