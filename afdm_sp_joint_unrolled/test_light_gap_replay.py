"""Small real decoder contracts; not receiver performance evidence."""
import tempfile
import unittest
from pathlib import Path

import numpy as np

from .e1_ldpc import build_code, decode_llr, encode, extract_info
from .light_gap_replay import (LightRun, calibrated_llr, check_decode_identity,
                               decoder_scores, replay_decode)
from .supplement_timing_integrity import BoundFiles


class ReplayTests(unittest.TestCase):
    def test_clip_preserves_source_and_sign(self):
        source = np.array([-20., -2., 0., 2., 20.])
        saved = source.copy()
        np.testing.assert_array_equal(calibrated_llr(source, 2., 20.), [-20., -4., 0., 4., 20.])
        np.testing.assert_array_equal(source, saved)
        for invalid in (np.array([21.]), np.array([np.nan]), np.array([1.j])):
            with self.assertRaises(ValueError):
                calibrated_llr(invalid, 1., 20.)
        for beta in (0., -1., np.nan):
            with self.assertRaises(ValueError):
                calibrated_llr(source, beta, 20.)

    def test_real_small_decoder_identity_and_truth_scope(self):
        with tempfile.TemporaryDirectory() as directory:
            code = build_code(n=48, d_v=3, d_c=6, seed=20260726, cache_dir=Path(directory))
            info = np.random.default_rng(42).integers(0, 2, code['k'], dtype=np.uint8)
            coded = encode(code, info)
            llr = (1 - 2 * coded.astype(float)) * 8
            decoded, ok = decode_llr(code, llr, maxiter=50)
            state = dict(llr=llr, decoded=decoded, info_hat=extract_info(code, decoded), decode_ok=ok)
            result = replay_decode(code, state, 1., 20., 50)
            check_decode_identity(result, state)
            self.assertEqual(decoder_scores(result, dict(coded=coded, info=info))['FER'], 0)
            wrong = dict(result, decode_ok=not result['decode_ok'])
            with self.assertRaises(ValueError):
                check_decode_identity(wrong, state)
            wrong = dict(result, info_hat=1 - result['info_hat'])
            with self.assertRaises(ValueError):
                check_decode_identity(wrong, state)

    def test_reservations_survive_failure_and_refuse_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / 'run'
            run = LightRun(root, 'engineering', dict(D=1, seconds=20), 1000000, BoundFiles({}))
            def fail():
                raise ArithmeticError('intentional contract failure')
            with self.assertRaises(ArithmeticError):
                run.call('D', {'block': 0}, fail, lambda value: {}, {})
            self.assertEqual(run.counts, {'D': 1})
            self.assertIsNotNone(run.active)
            self.assertTrue((run.out / 'D-00001-reserve.json').exists())
            with self.assertRaises(RuntimeError):
                run.reserve('D', {'block': 1})
            with self.assertRaises(FileExistsError):
                LightRun(root, 'engineering', dict(D=1, seconds=20), 1000000, BoundFiles({}))


if __name__ == '__main__':
    unittest.main()
