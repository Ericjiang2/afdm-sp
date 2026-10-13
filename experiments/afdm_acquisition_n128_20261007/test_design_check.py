"""Deterministic tiny design contracts; no scientific design or random sampling."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import numpy as np

from . import design_check as check


def fixed_design(n=8):
    """Fabricated saved metadata for boundary tests, not design evidence."""
    candidates = np.r_[1/(10*n*n), (np.arange(128)+np.sqrt(2))/(4*129)]
    current = np.exp(-2j*np.pi*candidates[0]*np.arange(n)**2)
    values = dict(current=current, quadratic=current.copy(), random=np.ones(n, complex),
                  candidate_c2=candidates, candidate_objectives=np.ones(129),
                  random_objective=np.array(1.))
    codes = {f'n{n}_{key}': value for key, value in values.items()}
    record = dict(array_sha256={k: check.array_hash(v) for k, v in codes.items()},
                  designs=[dict(N=n, quadratic_index=0, quadratic_c2=float(candidates[0]),
                                quadratic_objective=1., current_objective=1., random_objective=1.)],
                  design_phase_draws=n, new_observations=0, geometry_probes=130*(n-1)*(n//4))
    return codes, record


def write_json(path, value):
    path.write_text(json.dumps(value, allow_nan=False))


def seal_fixture(root):
    completion = dict(status='complete', exit_code=0,
                      artifact_sha256={str(p.resolve()): check.file_hash(p)
                                       for p in root.iterdir() if p.name != 'attempt.json'})
    write_json(root/'attempt.json', completion)
    return completion


class DesignFixtures(unittest.TestCase):
    def test_completion_receipt_rejects_failed_exit_and_ambiguous_remote_paths(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)/'execution'/'P'
            root.mkdir(parents=True)
            write_json(root/'results.json', {'fixture': True})
            remote = '/data/guoyikun/fixture/execution/P/results.json'
            completion = dict(status='complete', exit_code=0,
                              artifact_sha256={remote: check.file_hash(root/'results.json')})
            write_json(root/'attempt.json', completion)
            check.verify_stage_completion(root, ('results.json',))
            for code in (1, False, None):
                write_json(root/'attempt.json', dict(completion, exit_code=code))
                with self.assertRaisesRegex(ValueError, 'completion exit code'):
                    check.verify_stage_completion(root, ('results.json',))
            duplicate = dict(completion['artifact_sha256'])
            duplicate['another/execution/P/results.json'] = duplicate[remote]
            write_json(root/'attempt.json', dict(completion, artifact_sha256=duplicate))
            with self.assertRaisesRegex(ValueError, 'match must be unique'):
                check.verify_stage_completion(root, ('results.json',))
            write_json(root/'attempt.json', dict(completion, artifact_sha256={'results.json': duplicate[remote]}))
            with self.assertRaisesRegex(ValueError, 'match must be unique'):
                check.verify_stage_completion(root, ('results.json',))

    def test_forward_fft_matches_explicit_sums_on_fixed_code(self):
        # Only two fixed N8 unit codes, never the N128 design cohort.
        for v in (np.ones(8, complex), np.exp(1j*np.array([.1, -.2, .31, .05, -.4, .62, -.55, .27]))):
            objective, values = check.independent_geometry(v)
            expected = np.empty((7, 2))
            for a in range(1, 8):
                for delay in range(2):
                    expected[a-1, delay] = abs(sum(v[j]**4*np.conj(v[(j-a) % 8]**4)*
                                                   np.exp(8j*np.pi*delay*j/8) for j in range(8))/8)
            np.testing.assert_allclose(values, expected, atol=1e-14, rtol=0)
            self.assertAlmostEqual(objective, expected.max(), places=14)

    def test_design_validation_binds_shape_hash_formula_and_earliest_tie(self):
        codes, record = fixed_design()
        _, _, choice = check.check_design_arrays(codes, record, n=8)
        self.assertEqual(choice, 0)
        changed = copy.deepcopy(record)
        changed['designs'][0]['quadratic_index'] = 1
        with self.assertRaisesRegex(ValueError, 'earliest selection'):
            check.check_design_arrays(codes, changed, n=8)
        changed_codes = dict(codes, n8_current=codes['n8_current'].reshape(2, 4))
        with self.assertRaisesRegex(ValueError, 'array hash'):
            check.check_design_arrays(changed_codes, record, n=8)
        changed_codes = copy.deepcopy(codes)
        changed_codes['n8_candidate_c2'][3] += .01
        changed = copy.deepcopy(record)
        changed['array_sha256']['n8_candidate_c2'] = check.array_hash(changed_codes['n8_candidate_c2'])
        with self.assertRaisesRegex(ValueError, 'quadratic candidates'):
            check.check_design_arrays(changed_codes, changed, n=8)

    def test_nonfinite_and_wrong_principal_root_rejected(self):
        for value, error in ((np.full(8, np.nan), 'nonfinite'),
                             (-np.ones(8, complex), 'principal fourth-root')):
            codes, record = fixed_design()
            codes['n8_random'] = value
            record['array_sha256']['n8_random'] = check.array_hash(value)
            with self.assertRaisesRegex(ValueError, error):
                check.check_design_arrays(codes, record, n=8)
        with self.assertRaisesRegex(ValueError, 'shape mismatch'):
            check.close(np.ones(8), 1., 'no broadcast')

    def test_corrupted_file_rejected_before_any_geometry(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            write_json(root/'design.json', {'code_file_sha256': '0'*64})
            (root/'codes.npz').write_bytes(b'corrupt fixture')
            with mock.patch.object(check, 'independent_geometry', side_effect=AssertionError('must not run')):
                with self.assertRaisesRegex(ValueError, 'design file binding'):
                    check.calculate_design_check(root)

    def test_verification_orchestration_counts_all_objectives_and_rejects_mismatch(self):
        # The objective kernel is mocked: this checks orchestration/counts only.
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            codes, record = fixed_design()
            with (root/'codes.npz').open('wb') as handle:
                np.savez(handle, **codes)
            record['code_file_sha256'] = check.file_hash(root/'codes.npz')
            write_json(root/'design.json', record)
            with mock.patch.object(check, 'N', 8), mock.patch.object(check, 'DESIGN_PROBES', 1820), \
                 mock.patch.object(check, 'independent_geometry', return_value=(1., np.ones((7, 2)))) as geometry:
                result = check.calculate_design_check(root)
                self.assertEqual(geometry.call_count, 130)
                self.assertEqual(result['geometry_probes'], 1820)
                self.assertEqual(result['design_phase_draws'], 0)
                self.assertTrue(result['audit_pass'])
                self.assertEqual(check.read_json(root/'design_audit.json'), result)
            with mock.patch.object(check, 'N', 8), \
                 mock.patch.object(check, 'independent_geometry', return_value=(.5, np.ones((7, 2)))):
                with self.assertRaisesRegex(ValueError, 'independent quadratic objectives'):
                    check.calculate_design_check(root)

    def test_receipt_loading_checks_binding_without_geometry(self):
        # Hash-only receipt fixture: mock the N128 array validator so no real
        # scientific design is constructed or claimed by this test.
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            codes, record = fixed_design()
            with (root/'codes.npz').open('wb') as handle:
                np.savez(handle, **codes)
            record['code_file_sha256'] = check.file_hash(root/'codes.npz')
            write_json(root/'design.json', record)
            checked = dict(audit_pass=True, geometry_probes=528320, verified_objectives=130,
                           design_phase_draws=0, new_observations=0, acquisition_calls=0,
                           design_json_sha256=check.file_hash(root/'design.json'),
                           code_file_sha256=record['code_file_sha256'],
                           array_sha256=record['array_sha256'], candidate_objectives=[1.]*129,
                           random_objective=1., quadratic_index=0)
            write_json(root/'design_audit.json', checked)
            receipt = dict(record, design_audit_pass=True,
                           design_audit_sha256=check.file_hash(root/'design_audit.json'),
                           geometry_probes=1056640, design_geometry_probes=528320,
                           design_verification_geometry_probes=528320, design_phase_draws=128)
            write_json(root/'results.json', receipt)
            write_json(root/'registration.json', {'fixture': True})
            write_json(root/'committed_project_sources.json', {'fixture': True})
            completion = seal_fixture(root)
            loaded_codes = dict(codes, n128_random_objective=np.array(1.))
            with mock.patch.object(check, 'independent_geometry', side_effect=AssertionError('must not run')), \
                 mock.patch.object(check, 'check_design_arrays', return_value=(None, np.ones(129), 0)), \
                 mock.patch.object(check, 'read_npz', return_value=loaded_codes):
                _, loaded = check.load_verified_design(root)
                self.assertEqual(loaded['geometry_probes'], 1056640)
                for name in ('results.json', 'codes.npz', 'design.json', 'design_audit.json',
                             'registration.json', 'committed_project_sources.json'):
                    path = root/name
                    original = path.read_bytes()
                    path.write_bytes(original+b' ')
                    with self.assertRaisesRegex(ValueError, 'completion artifact hash'):
                        check.load_verified_design(root)
                    path.write_bytes(original)
                write_json(root/'attempt.json', dict(completion, exit_code=1))
                with self.assertRaisesRegex(ValueError, 'completion exit code'):
                    check.load_verified_design(root)
                write_json(root/'attempt.json', completion)
                checked['audit_pass'] = False
                write_json(root/'design_audit.json', checked)
                seal_fixture(root)
                with self.assertRaisesRegex(ValueError, 'design audit not passed'):
                    check.load_verified_design(root)
                checked['audit_pass'] = True
                checked['random_objective'] = .5
                write_json(root/'design_audit.json', checked)
                seal_fixture(root)
                with self.assertRaisesRegex(ValueError, 'design audit file binding'):
                    check.load_verified_design(root)


if __name__ == '__main__':
    unittest.main()
