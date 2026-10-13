"""Tiny deterministic audit fixtures; never run the scientific pilot."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

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
                  f'{key}_best_gain_indices': np.array([0, 32, 0, 0]),
                  f'{key}_fourth_scores': np.empty(0)}
        answer = dict(a=1, delay=0, cfo=1, objective=7., gain_index=32,
                      physical_gain_mod_C4=[1., 0.], exact_ties=2,
                      likelihood_hypotheses=4, gain_grid_evaluations=384, elapsed_seconds=.1)
        audit.check_selection(answer, arrays, key, n)
        wrong = dict(answer, a=2, cfo=2)
        with self.assertRaisesRegex(ValueError, 'selected parameters'):
            audit.check_selection(wrong, arrays, key, n)
        with self.assertRaisesRegex(ValueError, 'objective/ties'):
            audit.check_selection(dict(answer, exact_ties=1), arrays, key, n)

    def test_screen512_stable_shortlist(self):
        key = 'random_SCREEN512'
        arrays = {f'{key}_hypotheses': np.arange(512),
                  f'{key}_profile_scores': np.zeros(512),
                  f'{key}_best_gain_indices': np.zeros(512, dtype=np.int64),
                  f'{key}_fourth_scores': np.ones((64, 16))}
        answer = dict(a=0, delay=0, cfo=0, objective=0., gain_index=0,
                      physical_gain_mod_C4=[.75, 0.], exact_ties=512,
                      likelihood_hypotheses=512, gain_grid_evaluations=49152, elapsed_seconds=.1)
        audit.check_selection(answer, arrays, key, 64)
        arrays[f'{key}_hypotheses'] = np.arange(512, 1024)
        with self.assertRaisesRegex(ValueError, 'hypothesis order/shortlist'):
            audit.check_selection(answer, arrays, key, 64)

    def test_cp_boundary_and_extreme_counts(self):
        self.assertAlmostEqual(audit.cp_upper(0), 1-.05**(1/256), places=12)
        p = audit.cp_upper(1)
        self.assertAlmostEqual((1-p)**256+256*p*(1-p)**255, .05, places=12)
        self.assertLess(audit.cp_upper(1), .02)
        self.assertGreater(audit.cp_upper(2), .02)
        self.assertEqual(audit.cp_upper(256), 1.)
        for bad in (-1, 257, True, 1.5):
            with self.assertRaisesRegex(ValueError, 'invalid binomial count'):
                audit.cp_upper(bad)

    def test_explicit_mixture_normalization_and_nonzero_coordinates(self):
        x = np.array([[.2+.3j, -.4+.1j, .6-.7j, -.8-.2j]])
        scores = audit.direct_mixture(x, np.ones(4, complex), .7, 0)
        for idx, rho in enumerate((.75, 1., 1.25)):
            # Phase-zero mixture separates into two independent QPSK signs.
            u = np.sqrt(2)*rho*x/.7
            expected = np.sum(np.log(np.cosh(u.real))+np.log(np.cosh(u.imag))-rho*rho/.7)
            self.assertAlmostEqual(scores[idx*32], expected, places=12)
        zero = audit.direct_mixture(np.zeros((1, 4), complex), np.ones(4), 1., 0)
        self.assertTrue(np.allclose(zero[:32], -4*.75**2))

    def test_explicit_mixture_nonzero_delay_and_phase(self):
        x = np.array([[.2+.3j, -.4+.1j, .6-.7j, -.8-.2j,
                       .4-.2j, .6+.9j, -.3-.2j, .1-.5j]])
        v = np.exp(1j*np.array([.1, -.2, .31, .05, -.4, .62, -.55, .27]))
        # Hypothesis a=3, delay=1; an interior nonzero phase from the 96 grid.
        values = audit.direct_mixture(x, v, .7, 7)
        gain = 1.25*np.exp(1j*17*np.pi/64)
        expected = 0.
        for j in range(8):
            k = (j-3) % 8
            z = x[0, j]*v[k].conjugate()*np.exp(2j*np.pi*k/8)
            u = np.sqrt(2)*z*gain.conjugate()/.7
            expected += np.log(np.cosh(u.real))+np.log(np.cosh(u.imag))-abs(gain)**2/.7
        self.assertAlmostEqual(values[81], expected, places=12)
        with self.assertRaisesRegex(ValueError, 'mixture noise'):
            audit.direct_mixture(x, v, 0., 7)
        with self.assertRaisesRegex(ValueError, 'mixture hypothesis'):
            audit.direct_mixture(x, v, .7, 16)

    def test_physical_gain_delay_correction_and_invalid_grid(self):
        n, key = 8, 'random_FULL'
        arrays = {f'{key}_hypotheses': np.arange(16),
                  f'{key}_profile_scores': np.zeros(16),
                  f'{key}_best_gain_indices': np.zeros(16, dtype=np.int64),
                  f'{key}_fourth_scores': np.empty(0)}
        arrays[f'{key}_profile_scores'][7] = 1.
        arrays[f'{key}_best_gain_indices'][7] = 81
        physical = 1.25*np.exp(1j*(17*np.pi/64+5*np.pi/8))
        answer = dict(a=3, delay=1, cfo=6, objective=1., gain_index=81,
                      physical_gain_mod_C4=[physical.real, physical.imag], exact_ties=1,
                      likelihood_hypotheses=16, gain_grid_evaluations=1536, elapsed_seconds=.1)
        audit.check_selection(answer, arrays, key, n)
        with self.assertRaisesRegex(ValueError, 'likelihood work counts'):
            audit.check_selection(dict(answer, gain_grid_evaluations=768), arrays, key, n)
        arrays[f'{key}_best_gain_indices'][7] = 96
        with self.assertRaisesRegex(ValueError, 'gain indices'):
            audit.check_selection(answer, arrays, key, n)
        arrays[f'{key}_profile_scores'][7] = np.nan
        with self.assertRaisesRegex(ValueError, 'nonfinite'):
            audit.check_selection(answer, arrays, key, n)

    def test_one_cell_variance_gates_and_foreign_cohort_rejection(self):
        records = []
        for within in range(256):
            estimates = {key: dict(error=False, elapsed_seconds=1.) for key in audit.KEYS}
            estimates['random_FULL']['elapsed_seconds'] = 4.
            estimates['quadratic_SCREEN512']['error'] = within < 64
            records.append(dict(N=128, T=2, snr_db=5, estimates=estimates,
                                dominance={arm: True for arm in audit.ARMS}))
        result = audit.independent_summary(records)
        self.assertEqual(result['paired_improvement']['mean'], .25)
        self.assertAlmostEqual(result['paired_improvement']['standard_error'], (.25*.75/255)**.5)
        self.assertEqual(result['random_speed_ratio'], 4.)
        self.assertTrue(result['positive_pilot_signal'])
        changed = copy.deepcopy(records)
        for row in changed[:1]:
            row['estimates']['random_SCREEN512']['error'] = True
        self.assertTrue(audit.independent_summary(changed)['gates']['noninferiority'])
        changed[1]['estimates']['random_SCREEN512']['error'] = True
        result = audit.independent_summary(changed)
        self.assertEqual(result['bad_discordance'], 2)
        self.assertFalse(result['gates']['noninferiority'])
        self.assertFalse(result['positive_pilot_signal'])
        with self.assertRaisesRegex(ValueError, 'incomplete or foreign'):
            audit.independent_summary(records[:64])
        foreign = copy.deepcopy(records)
        foreign[0]['T'] = 4
        with self.assertRaisesRegex(ValueError, 'incomplete or foreign'):
            audit.independent_summary(foreign)
        for row in changed[:64]:
            row['estimates']['random_SCREEN512']['error'] = True
        self.assertTrue(audit.independent_summary(changed)['gates']['each_cell_usable'])
        changed[64]['estimates']['random_SCREEN512']['error'] = True
        self.assertFalse(audit.independent_summary(changed)['gates']['each_cell_usable'])

    def test_reject_incomplete_source_before_reading_data(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            design = root/'execution'/'D'
            design.mkdir(parents=True)
            (design/'attempt.json').write_text(json.dumps({'status': 'failed'}))
            with self.assertRaisesRegex(ValueError, 'incomplete source D'):
                audit.calculate_audit(root, root)

    def test_pilot_completion_binding_precedes_result_or_observation_consumption(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            pilot = root/'execution'/'P'
            pilot.mkdir(parents=True)
            names = ('records.json', 'results.json', 'registration.json', 'committed_project_sources.json')
            for name in names:
                (pilot/name).write_text('{}')
            completion = dict(status='complete', exit_code=0,
                              artifact_sha256={f'/data/guoyikun/fixture/execution/P/{name}':
                                               audit.file_hash(pilot/name) for name in names})
            (pilot/'attempt.json').write_text(json.dumps(completion))
            with mock.patch.object(audit, 'load_verified_design', return_value=({}, {})), \
                 mock.patch.object(audit, 'check_source_identity', side_effect=AssertionError('must not read')):
                for name in names:
                    (pilot/name).write_text('{"modified": true}')
                    with self.assertRaisesRegex(ValueError, 'completion artifact hash'):
                        audit.calculate_audit(root, root)
                    (pilot/name).write_text('{}')
                completion['exit_code'] = 1
                (pilot/'attempt.json').write_text(json.dumps(completion))
                with self.assertRaisesRegex(ValueError, 'completion exit code'):
                    audit.calculate_audit(root, root)

    def test_source_commit_and_current_bytes_bound_across_stages(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root/'fixture.py'
            source.write_text('fixture = True\n')
            identity = dict(head='a'*40, project_python_sha256={'fixture.py': audit.file_hash(source)})
            folders = [root/'execution'/stage for stage in ('D', 'P', 'A')]
            for folder in folders:
                folder.mkdir(parents=True)
                (folder/'committed_project_sources.json').write_text(json.dumps(identity))
            self.assertEqual(audit.check_source_identity(folders[2], root, project_root=root), identity)
            source.write_text('fixture = False\n')
            with self.assertRaisesRegex(ValueError, 'current Python source mismatch'):
                audit.check_source_identity(folders[2], root, project_root=root)
            changed = dict(identity, head='b'*40)
            (folders[1]/'committed_project_sources.json').write_text(json.dumps(changed))
            with self.assertRaisesRegex(ValueError, 'D/P/A committed source identity mismatch'):
                audit.check_source_identity(folders[2], root, project_root=root)


if __name__ == '__main__':
    unittest.main()
