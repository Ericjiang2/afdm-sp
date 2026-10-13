"""Pilot identity, intervention and accounting contracts on small fixtures."""
import json
from pathlib import Path
import tempfile
import time
import unittest

import numpy as np

from .bottleneck_pilot import (Run, compare_full, generate_exogenous, hashes,
    load_state, observed_at_snr, offline_scores, pilot_rng, terminal_inputs)
from .direction_data import validate_observed
from .e1_ldpc import build_code
from .supplement_adjacent_run import save_state
from .supplement_timing_integrity import OutputMeter


class PilotTests(unittest.TestCase):
    def test_new_namespace_and_split_are_distinct_and_snr_reuses_exogenous(self):
        class ToySystem:
            N_total = 4
            rho = .5
            _zc_seq = np.ones(4, dtype=complex)
            def generate_channel_matrix(self):
                return np.diag(np.random.randn(4)+1j*np.random.randn(4)), None, {}
        with tempfile.TemporaryDirectory() as tmp:
            code = build_code(n=8, d_v=2, d_c=4, seed=11, cache_dir=tmp)
            before = np.random.get_state()
            raw = generate_exogenous(ToySystem(), code, 0, split=2)
            after = np.random.get_state()
            np.testing.assert_array_equal(before[1], after[1])
            self.assertEqual(before[2:], after[2:])
            a, b = observed_at_snr(raw, 7), observed_at_snr(raw, 8)
            signal = raw['H']@(raw['pilot']+raw['data'])
            np.testing.assert_allclose((a['y']-signal)/np.sqrt(a['sigma2']), raw['noise'], atol=1e-14)
            np.testing.assert_allclose((b['y']-signal)/np.sqrt(b['sigma2']), raw['noise'], atol=1e-14)
            self.assertFalse(a['y'].flags.writeable)
            self.assertEqual(set(a), {'y','pilot','sigma2','constellation'})
            repeat = generate_exogenous(ToySystem(), code, 0, split=2)
            self.assertEqual(hashes({k: raw[k] for k in ('H','coded','noise')}),
                             hashes({k: repeat[k] for k in ('H','coded','noise')}))
        self.assertFalse(np.array_equal(pilot_rng(0, 1, split=1).random(8),
                                       pilot_rng(0, 1, split=2).random(8)))
        for args in ((True,1,1), (0,4,1), (0,1,3)):
            with self.assertRaises(ValueError):
                pilot_rng(args[0], args[1], split=args[2])

    def test_terminal_cancellation_and_sigma_follow_the_declared_factor(self):
        observed = dict(y=np.array([2+1j,3-1j]), pilot=np.array([.5+0j,.5+0j]),
                        sigma2=np.asarray(.2), constellation=np.array([.5+.5j,.5-.5j,-.5+.5j,-.5-.5j]))
        estimated, truth = np.eye(2, dtype=complex), 2*np.eye(2, dtype=complex)
        for arm, expected, sigma in [('BP_EST_NOISE',estimated,.2),
                ('EP_EST_NOISE',estimated,.2), ('BP_TRUE_BASE',truth,.3),
                ('BP_TRUE_NOISE',truth,.2), ('EP_TRUE_NOISE',truth,.2)]:
            z, H, actual = terminal_inputs(observed, estimated, truth, .3, arm)
            np.testing.assert_array_equal(H, expected)
            np.testing.assert_array_equal(z, observed['y']-expected@observed['pilot'])
            self.assertEqual(actual, sigma)
        with self.assertRaises(ValueError):
            validate_observed(dict(observed, H=truth))

    def test_raw_readback_binds_inventory_dtype_shape_and_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            # The shared writer reserves 1 MiB of archive overhead plus raw bytes.
            meter = OutputMeter(root, 8*1024*1024)
            value = dict(H=np.eye(2, dtype=np.complex64), trace=[np.array([1,0], dtype=np.uint8)])
            artifact = save_state(root/'state.npz', value, meter, readback=True)
            back = load_state(artifact)
            np.testing.assert_array_equal(back['H'], value['H'])
            meter.verify()
            with (root/'state.npz').open('ab') as f:
                f.write(b'corruption')
            with self.assertRaises(ValueError):
                load_state(artifact)

    def test_reservation_precedes_work_and_deadline_and_limits_stop_new_calls(self):
        class Guard:
            def check(self):
                pass
        with tempfile.TemporaryDirectory() as tmp:
            run = Run(tmp, 'engineering', dict(total_bounds={'output_bytes':10000},
                bounds={'engineering':{'F':1,'T':1,'seconds':60}}), Guard())
            token = run.reserve('F', dict(block=0, snr=7, arm='I1'))
            saved = json.loads((run.out/(token+'-reserve.json')).read_text())
            self.assertEqual(saved['arm'], 'I1')
            self.assertEqual(run.counts, {'F':1,'T':0})
            with self.assertRaises(RuntimeError):
                run.reserve('F', {})
            run.deadline = time.monotonic()-1
            with self.assertRaises(TimeoutError):
                run.reserve('T', {})
            self.assertEqual(run.counts, {'F':1,'T':0})

    def test_information_error_is_not_decoder_success_and_replay_checks_decisions(self):
        truth = dict(H=np.eye(1, dtype=complex), info=np.array([0]), coded=np.array([0,0]))
        result = dict(info_hat=np.array([1]), decoded=np.array([1,1]), x_hard=np.array([-.5-.5j]),
                      llr=np.array([-5.,-5.]), decode_ok=True)
        scores = offline_scores(result, truth, truth['H'])
        self.assertEqual(scores['FER'], 1)
        self.assertTrue(scores['decode_ok'])
        self.assertEqual(scores['coded_bits_denominator'], 1)
        self.assertEqual(scores['raw_bits_denominator'], 2)
        self.assertEqual(scores['high_confidence_wrong'], 2)
        full = dict(result, H=truth['H'], sigma2=.2, sigma2_terminal=.1,
                    x_soft=np.array([.1j]), gains=np.array([1.]), mu=np.array([.1j]),
                    var=np.array([.4]), support=[0])
        compare_full(full, full)
        with self.assertRaises(ValueError):
            compare_full(dict(full, info_hat=np.array([0])), full)
        with self.assertRaises(ValueError):
            compare_full(dict(full, sigma2=.3), full)


if __name__=='__main__':
    unittest.main()
