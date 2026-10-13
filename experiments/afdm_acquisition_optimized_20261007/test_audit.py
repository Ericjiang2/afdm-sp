"""Tiny deterministic audit fixtures; never run the scientific pilot."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

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
        n, key = 4, 'quadratic_FULL'
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

    def test_screen128_stable_shortlist(self):
        key = 'optimized_SCREEN128'
        arrays = {f'{key}_hypotheses': np.arange(128),
                  f'{key}_profile_scores': np.zeros(128),
                  f'{key}_best_gain_indices': np.zeros(128, dtype=np.int64),
                  f'{key}_fourth_scores': np.ones((32, 8))}
        answer = dict(a=0, delay=0, cfo=0, objective=0., gain_index=0,
                      physical_gain_mod_C4=[.75, 0.], exact_ties=128,
                      likelihood_hypotheses=128, gain_grid_evaluations=6144, elapsed_seconds=.1)
        audit.check_selection(answer, arrays, key, 32)
        arrays[f'{key}_hypotheses'] = np.arange(128, 256)
        with self.assertRaisesRegex(ValueError, 'hypothesis order/shortlist'):
            audit.check_selection(answer, arrays, key, 32)

    def test_cp_boundary_and_extreme_counts(self):
        self.assertAlmostEqual(audit.cp_upper(0), 1-.05**(1/1024), places=12)
        self.assertAlmostEqual(audit.cp_upper(12), .018917867089388803, places=12)
        self.assertAlmostEqual(audit.cp_upper(13), .02010854052334146, places=12)
        self.assertLess(audit.cp_upper(12), .02)
        self.assertGreater(audit.cp_upper(13), .02)
        self.assertEqual(audit.cp_upper(1024), 1.)
        with self.assertRaisesRegex(ValueError, 'invalid binomial count'):
            audit.cp_upper(1025)

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

    def test_one_cell_variance_gates_and_foreign_cohort_rejection(self):
        records = []
        for within in range(1024):
            estimates = {key: dict(error=False, elapsed_seconds=1.) for key in audit.KEYS}
            estimates['optimized_FULL']['elapsed_seconds'] = 4.
            estimates['quadratic_SCREEN128']['error'] = within < 256
            records.append(dict(N=64, T=2, snr_db=5, estimates=estimates,
                                dominance={arm: True for arm in audit.ARMS}))
        result = audit.independent_summary(records)
        self.assertEqual(result['paired_improvement']['mean'], .25)
        self.assertAlmostEqual(result['paired_improvement']['standard_error'], (.25*.75/1023)**.5)
        self.assertEqual(result['proposed_speed_ratio'], 4.)
        self.assertTrue(result['positive_pilot_signal'])
        changed = copy.deepcopy(records)
        for row in changed[:12]:
            row['estimates']['optimized_SCREEN128']['error'] = True
        self.assertTrue(audit.independent_summary(changed)['gates']['noninferiority'])
        changed[12]['estimates']['optimized_SCREEN128']['error'] = True
        result = audit.independent_summary(changed)
        self.assertEqual(result['bad_discordance'], 13)
        self.assertFalse(result['gates']['noninferiority'])
        self.assertFalse(result['positive_pilot_signal'])
        with self.assertRaisesRegex(ValueError, 'incomplete or foreign'):
            audit.independent_summary(records[:256])
        foreign = copy.deepcopy(records)
        foreign[0]['T'] = 4
        with self.assertRaisesRegex(ValueError, 'incomplete or foreign'):
            audit.independent_summary(foreign)
        for row in changed[:256]:
            row['estimates']['optimized_SCREEN128']['error'] = True
        self.assertTrue(audit.independent_summary(changed)['gates']['each_cell_usable'])
        changed[256]['estimates']['optimized_SCREEN128']['error'] = True
        self.assertFalse(audit.independent_summary(changed)['gates']['each_cell_usable'])

    def test_secondary_pairing_direction_and_primary_gate_scope(self):
        from .study import summarize

        records = []
        for within in range(1024):
            estimates = {key: dict(error=False, elapsed_seconds=1.) for key in audit.KEYS}
            estimates['quadratic_SCREEN128']['error'] = within < 384
            for method in audit.METHODS:
                estimates[f'optimized_{method}']['error'] = within < 128
                estimates[f'random_{method}']['error'] = 64 <= within < 256
            estimates['optimized_FULL']['elapsed_seconds'] = 4.
            records.append(dict(N=64, T=2, snr_db=5, estimates=estimates,
                                dominance={arm: True for arm in audit.ARMS}))
        result = audit.independent_summary(records)
        secondary = result['optimized_vs_random_improvement']
        self.assertEqual(result['paired_improvement']['mean'], .25)
        self.assertEqual(secondary['mean'], .0625)
        self.assertAlmostEqual(secondary['standard_error'], (188/(1023*1024))**.5)
        self.assertAlmostEqual(secondary['interval'][0], .0625-1.959963984540054*(188/(1023*1024))**.5)
        self.assertTrue(result['positive_pilot_signal'])
        self.assertEqual(result['proposed_speed_ratio'], 4.)
        audit.compare_summary(result, summarize(records, dict(Ns=[64], snr_db=[5], groups_per_cell=1024)))
        # Better oldrandom changes the secondary inference, not the frozen gates.
        for row in records:
            row['estimates']['random_SCREEN128']['error'] = False
        result = audit.independent_summary(records)
        self.assertEqual(result['optimized_vs_random_improvement']['mean'], -.125)
        self.assertTrue(result['positive_pilot_signal'])
        altered = copy.deepcopy(result)
        altered['optimized_vs_random_improvement']['mean'] *= -1
        with self.assertRaisesRegex(ValueError, 'summary mean'):
            audit.compare_summary(result, altered)

    def test_all_four_optimized_reference_hashes_and_qualification(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            np.savez(folder/'code.npz', v=np.ones(64, complex))
            result = dict(design_qualified=True, selected_index=199,
                          code_sha256=audit.file_hash(folder/'code.npz'),
                          reference_code_sha256=audit.DESIGN_SHA256)
            (folder/'results.json').write_text(json.dumps(result))
            (folder/'attempt.json').write_text(json.dumps(dict(status='complete', exit_code=0)))
            (folder/'audit.json').write_text(json.dumps(dict(audit_pass=True, design_qualified=True, selected_index=199)))
            digests = {name: audit.file_hash(folder/name) for name in audit.OPTIMIZED_SHA256}
            # Only this isolated fixture uses synthetic reference digests.
            with patch.object(audit, 'OPTIMIZED_SHA256', digests):
                np.testing.assert_array_equal(audit.load_optimized_reference(folder), np.ones(64))
                for name in digests:
                    path, original = folder/name, (folder/name).read_bytes()
                    path.write_bytes(original+b'changed')
                    with self.assertRaisesRegex(ValueError, f'optimized reference hash: {name}'):
                        audit.load_optimized_reference(folder)
                    path.write_bytes(original)
                (folder/'audit.json').write_text(json.dumps(dict(audit_pass=False, design_qualified=True, selected_index=199)))
                digests['audit.json'] = audit.file_hash(folder/'audit.json')
                with self.assertRaisesRegex(ValueError, 'qualification/audit'):
                    audit.load_optimized_reference(folder)

    def test_reject_corrupted_design_before_reading_observations(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for folder in (root/'design_reference', root/'execution'/'P'):
                folder.mkdir(parents=True)
                (folder/'attempt.json').write_text(json.dumps({'status': 'complete'}))
            design = root/'design_reference'
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
            design = root/'design_reference'
            design.mkdir(parents=True)
            (design/'attempt.json').write_text(json.dumps({'status': 'failed'}))
            with self.assertRaisesRegex(ValueError, 'incomplete source design_reference'):
                audit.calculate_audit(root, root)


if __name__ == '__main__':
    unittest.main()
