"""Real tiny CE/BP/LDPC checks for the explicit QPSK projection route."""
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
from .e1_ldpc import build_code
from .test_supplement_feedback_adapter import tiny_adapter
from .light_gap_receiver_run import run_arm, NUMERIC_FIELDS, receiver_resources
from .mp_detect_bp_torch import mp_detect_bp_torch


class QPSKReceiverTests(unittest.TestCase):
    def test_common_chain_and_actual_kernel_delivery(self):
        with tempfile.TemporaryDirectory() as directory:
            code = build_code(n=64, d_v=2, d_c=4, seed=91, cache_dir=directory)
            rng = np.random.default_rng(912)
            observed = dict(y=rng.normal(size=32)+1j*rng.normal(size=32),
                pilot=np.ones(32, complex)/2, sigma2=.2,
                constellation=np.array([.5+.5j, .5-.5j, -.5+.5j, -.5-.5j]))
            receiver = tiny_adapter(code)
            old = run_arm(receiver, code, observed, dict(name='MEAN', receiver={}))
            with patch('afdm_sp_joint_unrolled.classical_joint_unrolled.mp_detect_bp_torch', wraps=mp_detect_bp_torch) as outer, \
                 patch('afdm_sp_joint_unrolled.direction_receiver.mp_detect_bp_torch', wraps=mp_detect_bp_torch) as terminal:
                new = run_arm(receiver, code, observed,
                    dict(name='QPSK_MEAN', receiver=dict(bp_edge_projection='qpsk_tanh')))
            self.assertEqual(outer.call_count, 3)
            self.assertEqual(terminal.call_count, 1)
            for call in outer.call_args_list+terminal.call_args_list:
                self.assertEqual(call.kwargs['edge_projection'], 'qpsk_tanh')
            for field in NUMERIC_FIELDS:
                if field in ('support', 'x_hard', 'decoded', 'info_hat', 'decode_ok'):
                    np.testing.assert_array_equal(new[field], old[field])
                else:
                    np.testing.assert_allclose(new[field], old[field], rtol=1e-6, atol=1e-7)
            self.assertEqual(new['bp_edge_projection'], 'qpsk_tanh')
            self.assertEqual(receiver_resources(new), receiver_resources(old))
            with self.assertRaises(ValueError):
                run_arm(receiver, code, observed, dict(name='INVALID', receiver=dict(
                    detector='siso_mmse', bp_edge_projection='qpsk_tanh')))


if __name__ == '__main__':
    unittest.main()
