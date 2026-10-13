"""Tiny deterministic audit fixtures; never run the scientific pilot."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np

from . import audit


class AuditFixtures(unittest.TestCase):
    def test_hash_binds_dtype_shape_and_bytes(self):
        value = np.array([[1., 2.]])
        expected = hashlib.sha256(b'float64'+b'[1, 2]'+value.tobytes()).hexdigest()
        self.assertEqual(audit.array_hash(value), expected)
        self.assertNotEqual(audit.array_hash(value), audit.array_hash(value.ravel()))
        self.assertNotEqual(audit.array_hash(value), audit.array_hash(value.astype('float32')))

    def test_saved_selection_exact_tie_and_gain(self):
        n, key = 4, 'current_FULL'
        arrays = {f'{key}_hypotheses': np.arange(4),
                  f'{key}_profile_scores': np.array([2., 7., 7., 1.]),
                  f'{key}_best_gain_indices': np.array([0, 16, 0, 0]),
                  f'{key}_fourth_scores': np.empty(0)}
        answer = dict(a=1, delay=0, cfo=1, objective=7., gain_index=16,
                      physical_gain_mod_C4=[1., 0.], exact_ties=2,
                      likelihood_hypotheses=4, gain_grid_evaluations=192, elapsed_seconds=.1)
        audit.check_selection(answer, arrays, key, n)
        wrong = dict(answer, a=2, cfo=2)
        with self.assertRaisesRegex(ValueError, 'selected parameters'):
            audit.check_selection(wrong, arrays, key, n)
        with self.assertRaisesRegex(ValueError, 'objective/ties'):
            audit.check_selection(dict(answer, exact_ties=1), arrays, key, n)

    def test_fourth_gain_unavailable(self):
        key = 'random_FOURTH'
        arrays = {f'{key}_{name}': np.empty(0) for name in audit.ARRAYS}
        arrays[f'{key}_fourth_scores'] = np.array([[1.], [3.], [3.], [0.]])
        answer = dict(a=1, delay=0, cfo=1, objective=3., gain_index=None,
                      physical_gain_mod_C4=None, exact_ties=2,
                      likelihood_hypotheses=0, gain_grid_evaluations=0, elapsed_seconds=.1)
        audit.check_selection(answer, arrays, key, 4)
        with self.assertRaisesRegex(ValueError, 'unavailable'):
            audit.check_selection(dict(answer, physical_gain_mod_C4=[0., 0.]), arrays, key, 4)

    def test_explicit_mixture_normalization_and_nonzero_coordinates(self):
        x = np.array([[.2+.3j, -.4+.1j, .6-.7j, -.8-.2j]])
        scores = audit.direct_mixture(x, np.ones(4, complex), .7, 0)
        for idx, rho in enumerate((.75, 1., 1.25)):
            # Phase-zero mixture separates into two independent QPSK signs.
            u = np.sqrt(2)*rho*x/.7
            expected = np.sum(np.log(np.cosh(u.real))+np.log(np.cosh(u.imag))-rho*rho/.7)
            self.assertAlmostEqual(scores[idx*16], expected, places=12)
        zero = audit.direct_mixture(np.zeros((1, 4), complex), np.ones(4), 1., 0)
        self.assertTrue(np.allclose(zero[:16], -4*.75**2))

    def test_stratified_gates_count_bad_direction_and_reject_incomplete(self):
        records = []
        for n in (32, 64):
            for snr in (5, 15):
                for within in range(64):
                    estimates = {key: dict(error=False, elapsed_seconds=1.) for key in audit.KEYS}
                    estimates['random_FULL']['elapsed_seconds'] = 4.
                    estimates['quadratic_SCREEN32']['error'] = within < 16
                    records.append(dict(N=n, snr_db=snr, estimates=estimates,
                                        dominance={arm: True for arm in audit.ARMS}))
        result = audit.independent_summary(records)
        self.assertEqual(result['paired_improvement']['mean'], .25)
        self.assertEqual(result['random_speed_ratio'], 4.)
        self.assertTrue(result['positive_pilot_signal'])
        changed = copy.deepcopy(records)
        for row in changed[:2]:
            row['estimates']['random_SCREEN32']['error'] = True
        result = audit.independent_summary(changed)
        self.assertEqual(result['bad_discordance'], 2)
        self.assertFalse(result['gates']['noninferiority'])
        self.assertFalse(result['positive_pilot_signal'])
        with self.assertRaisesRegex(ValueError, 'incomplete cell'):
            audit.independent_summary(records[:-1])

    def test_reject_corrupted_design_before_reading_observations(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for stage in ('D', 'P'):
                folder = root/'execution'/stage
                folder.mkdir(parents=True)
                (folder/'attempt.json').write_text(json.dumps({'status': 'complete'}))
            design = root/'execution'/'D'
            (design/'codes.npz').write_bytes(b'corrupted fixture bytes')
            receipt = {'code_file_sha256': '0'*64}
            for filename in ('results.json', 'design.json'):
                (design/filename).write_text(json.dumps(receipt))
            (root/'execution'/'P'/'results.json').write_text(json.dumps({'waveform_design_sha256': '0'*64}))
            with self.assertRaisesRegex(ValueError, 'design file binding'):
                audit.calculate_audit(root, root)

    def test_reject_incomplete_source_before_reading_data(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            design = root/'execution'/'D'
            design.mkdir(parents=True)
            (design/'attempt.json').write_text(json.dumps({'status': 'failed'}))
            with self.assertRaisesRegex(ValueError, 'incomplete source D'):
                audit.calculate_audit(root, root)


if __name__ == '__main__':
    unittest.main()
