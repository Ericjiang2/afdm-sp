"""Deterministic audit contracts; no random observations, fitting or production run."""
import ast
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace

import numpy as np

from experiments.afdm_method_advantage import audit


def dump(path, value):
    path.write_text(json.dumps(value, allow_nan=False))


class IndependentAuditTests(unittest.TestCase):
    def test_numeric_mismatch_is_preserved_not_reported_as_success(self):
        checks = audit.Checks()
        checks.compare([1., 2.], [1., 2.], 'good', 'statistics')
        checks.compare([1., 2.1], [1., 2.], 'changed statistic', 'statistics')
        checks.compare([True, False], [True, False], 'boolean array')
        checks.compare(['a', 'b'], ['a', 'b'], 'method ordering')
        result = checks.result()
        self.assertFalse(result['passed'])
        self.assertEqual(result['failed_comparisons'], 1)
        self.assertEqual(result['failures'][0]['label'], 'changed statistic')
        self.assertAlmostEqual(result['categories']['statistics']['maximum_absolute_error'], .1)

    def test_missing_nonfinite_and_extra_summary_keys(self):
        checks = audit.Checks()
        checks.tree({'valid':1., 'extra':'allowed'}, {'valid':1., 'required':2.}, 'schema')
        checks.compare(float('nan'), 1., 'nonfinite')
        self.assertEqual(checks.result()['failed_comparisons'], 2)

    def test_power_features_are_direct_products_of_observations(self):
        y = np.array([[1+2j, 3+4j, 0+2j, 1-1j], [2., 1j, 3., 4j]])
        powers = np.array([[5., 25., 4., 2.], [4., 1., 9., 16.]])
        expected = np.column_stack([powers]+[powers[:, i]*powers[:, j] for i in range(4) for j in range(i, 4)])
        np.testing.assert_array_equal(audit.features(y), expected)
        with self.assertRaises(ValueError):
            audit.features(np.ones((2, 3)))

    def test_saved_record_corrupted_statistic_really_fails(self):
        powers = np.array([[1.,2.,3.,4.], [2.,1.,4.,3.], [4.,1.,2.,4.], [1.,4.,3.,1.]])
        y = np.sqrt(powers).astype(complex)
        observed = audit.features(y)
        contrast = powers[:, [0,2]]-powers[:, [1,3]]
        mean = contrast.mean(axis=0)
        covariance = (contrast-mean).T@(contrast-mean)/4
        statistic = float(4*mean@np.linalg.solve(covariance, mean))
        start = dict(theta=[.31,0.,0.], gradient=[0.,0.,0.], objective=1., optimizer_success=False,
                     success=False, lower_boundary=[False]*3, upper_boundary=[False]*3,
                     projected_gradient_max=0., evaluations=2)
        fit = dict(starts=[start], selected_start=0, theta=start['theta'], objective=1., success=False,
                   on_boundary=False, total_evaluations=2)
        m14 = dict(theta=start['theta'], success=False, on_boundary=False, first=copy.deepcopy(fit), second=None,
                   observed_mean=observed.mean(axis=0).tolist())
        record = dict(observations=4, fits=dict(mle=fit, m14=m14),
            statistics={name:None for name in audit.FIT_NAMES},
            r_hat={'full_score':None, 'moment_score':None},
            diagnostics=dict(second_moment=dict(mean=mean.tolist(), covariance=covariance.tolist(),
                fitted_variance_pairs=[float(powers[:,:2].mean()),float(powers[:,2:].mean())])),
            failures=[dict(method=name, kind='optimizer_failed', reason='deterministic fixture')
                      for name in ('full_score','moment_score')])
        record['statistics']['second_moment'] = statistic
        algebra = SimpleNamespace(model=lambda theta:(np.zeros(14), np.eye(14), np.zeros((14,4)), {'margin':.01}))
        config = dict(bounds=[[.22,.42],[-1,1],[-1,1]], boundary_tolerance=1e-7,
                      stationarity_tolerance=1e-3, branch_tolerance=1e-9, rcond=1e-10)
        checks = audit.Checks()
        audit.audit_record(record, y, config, algebra, checks, 'saved fixture')
        self.assertTrue(checks.result()['passed'], checks.failures)
        changed = copy.deepcopy(record)
        changed['statistics']['second_moment'] += .25
        checks = audit.Checks()
        audit.audit_record(changed, y, config, algebra, checks, 'corrupted fixture')
        self.assertFalse(checks.result()['passed'])
        self.assertTrue(any(x['label']=='corrupted fixture/second_moment' for x in checks.failures))

    def test_manifest_rejects_changed_raw_and_unregistered_artifact(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            stage = root/'stage'
            stage.mkdir()
            dump(stage/'registration.json', {'config':{'mode':'evaluation', 'condition':0}})
            raw = stage/'observations_00.npz'
            raw.write_bytes(b'fixed raw fixture, not scientific observations')
            artifacts = {str(p.relative_to(root)):audit.sha(p) for p in stage.iterdir()}
            dump(stage/'attempt.json', {'status':'complete', 'artifact_sha256':artifacts})
            with patch.object(audit, 'ROOT', root):
                binding = audit.stage_binding(stage)
                self.assertEqual(audit.verify_bindings([binding])['artifacts'], 2)
                original = raw.read_bytes()
                raw.write_bytes(b'changed raw')
                with self.assertRaisesRegex(ValueError, 'artifact hash changed'):
                    audit.verify_bindings([binding])
                raw.write_bytes(original)
                (stage/'extra').write_text('unregistered')
                with self.assertRaisesRegex(ValueError, 'inventory'):
                    audit.verify_bindings([binding])

    def test_protected_hash_failure_is_not_silently_skipped(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            protected = root/'old.bin'
            protected.write_bytes(b'original')
            manifest = root/'protected.json'
            dump(manifest, {'old.bin':audit.sha(protected)})
            with patch.object(audit, 'ROOT', root):
                self.assertEqual(audit.verify_protected(manifest), 1)
                protected.write_bytes(b'changed')
                with self.assertRaisesRegex(ValueError, 'protected baseline changed'):
                    audit.verify_protected(manifest)

    def test_exact_covariance_polynomial_at_gaussian_only_limit(self):
        # A deterministic algebra fixture: zero signal powers are approached via
        # a tiny positive base, without calling any model or generating Y.
        point = dict(base=np.full(4, 1e-10+0j), direction=np.ones(4, complex),
                     mu_derivative=np.zeros(4, complex), sigma2=2., kappa=0., margin=.01)
        states = np.ones((1, 4), complex)
        with patch.object(audit, 'qpsk_time', return_value=states), patch.object(audit, 'physical_point', return_value=point):
            mean, covariance, derivative, _ = audit.MomentAlgebra().model([.31, 0., np.log(2.)])
        # Independent complex Gaussian coordinates: |Y|^2 is exponential.
        self.assertAlmostEqual(mean[0], 2.)
        self.assertAlmostEqual(mean[4], 8.)
        self.assertAlmostEqual(mean[5], 4.)
        self.assertAlmostEqual(covariance[0, 0], 4.)
        self.assertAlmostEqual(covariance[0, 1], 0.)
        self.assertAlmostEqual(covariance[4, 4], 320.)  # E[P^4]-E[P^2]^2
        self.assertAlmostEqual(derivative[4, 3], 16.)

    def test_fit_success_cannot_ignore_projected_gradient(self):
        row = dict(theta=[.3, 0., 0.], gradient=[.2, 0., 0.], objective=1.,
                   optimizer_success=True, success=True, lower_boundary=[False]*3,
                   upper_boundary=[False]*3, projected_gradient_max=.2, evaluations=2)
        fit = dict(starts=[row], selected_start=0, theta=row['theta'], objective=1.,
                   success=True, on_boundary=False, total_evaluations=2)
        config = dict(bounds=[[.22,.42],[-1,1],[-1,1]], boundary_tolerance=1e-7, stationarity_tolerance=1e-3)
        checks = audit.Checks()
        audit.check_fit(fit, config, checks, 'fit')
        self.assertFalse(checks.result()['passed'])
        self.assertTrue(any('success' in item['label'] for item in checks.failures))

    def test_cost_charges_one_cold_construction_to_each_r(self):
        rows = {}
        for g in range(2):
            for r in (64, 256):
                rows[g, r] = dict(costs=dict(per_method_seconds={'moment_score':1., 'second_moment':.1},
                    setup_original_construction_seconds=10., setup_seconds=10. if (g,r)==(0,64) else .2,
                    setup_cache_hit=(g,r)!=(0,64)))
        dataset = dict(groups=2, records=rows)
        self.assertAlmostEqual(audit.standalone_cost(dataset, 256, 'moment_score')['standalone_seconds'], 12.4)
        self.assertAlmostEqual(audit.standalone_cost(dataset, 256, 'second_moment')['standalone_seconds'], .2)

    def test_discordance_interval_keeps_concordant_denominator(self):
        c = np.array([True]*10+[False]*90)
        b = np.zeros(100, bool)
        result = audit.discordance_interval(c, b, 84, .95)
        self.assertEqual((result['groups'],result['discordant_plus'],result['discordant_minus']), (100,10,0))
        self.assertEqual(result['difference'], .1)
        self.assertLess(result['lower'], .1)
        self.assertGreater(result['upper'], .1)
        self.assertAlmostEqual(result['tail_probability'], .05/(4*84))
        identical = audit.discordance_interval(b, b, 84, .95)
        self.assertEqual(identical['difference'], 0)
        self.assertLess(identical['lower'], 0)
        self.assertGreater(identical['upper'], 0)

    def test_supplement_power_gate_uses_two_sided_cp_and_rejects_zero_power(self):
        zero = audit.exact_rate_interval(0, 768, .95)
        all_success = audit.exact_rate_interval(768, 768, .95)
        self.assertEqual(zero['lower'], 0.)
        self.assertEqual(all_success['upper'], 1.)
        self.assertAlmostEqual(all_success['lower'], .025**(1/768))
        self.assertAlmostEqual(zero['tail_probability'], .025)
        self.assertLess(zero['lower'], .80)
        self.assertGreater(audit.exact_rate_interval(744, 768, .95)['lower'], .80)

    def test_historical_primary_binding_does_not_absorb_later_supplement(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            summary = root/'summary_v1'
            summary.mkdir()
            qualification = root/'qualification_v1'
            qualification.mkdir()
            metadata = {'registration.json':'fixed registration hash','attempt.json':'fixed attempt hash'}
            exclusion = dict(stage='qualification_v1', mode='qualification', status='invalid_partial',
                metadata_sha256=metadata, reserved_wall_seconds=180, reserved_new_observations=2048)
            dump(qualification/'attempt.json', dict(reserved_wall_seconds=180,reserved_new_observations=2048))
            dump(summary/'registration.json', dict(config=dict(excluded_stages=[exclusion])))
            dump(summary/'input_bindings.json', dict(source_bindings=[],excluded_stages=[exclusion]))
            counts = dict(stages=0,metadata=0,artifacts=0,observations_archives=0)
            dump(summary/'input_hash_counts.json', counts)
            dump(summary/'results.json', dict(input_hash_counts=counts,source_hashes_unchanged=True))
            bindings = [dict(path='qualification_v1',mode='qualification',cohort=None,status='invalid_partial',metadata=metadata),
                        dict(path='supplementary_null_v1',mode='evaluation',cohort=audit.SUPPLEMENT_COHORT,status='complete')]
            checks = audit.Checks()
            with patch.object(audit,'ROOT',root):
                audit.audit_summary_bindings(summary,bindings,checks)
            self.assertTrue(checks.result()['passed'], checks.failures)

    def test_unknown_scientific_cohort_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            stage = Path(directory)
            dump(stage/'registration.json', dict(config=dict(mode='evaluation',cohort='unregistered')))
            dump(stage/'attempt.json',dict(status='complete',artifact_sha256={}))
            with self.assertRaisesRegex(ValueError,'unregistered scientific cohort'):
                audit.stage_binding(stage)

    def test_no_method_or_analysis_implementation_is_imported(self):
        tree = ast.parse(Path(audit.__file__).read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                self.assertNotIn(node.module, ('experiments.afdm_method_advantage.methods', 'experiments.afdm_method_advantage.analysis'))
                if node.module == 'experiments.afdm_method_advantage':
                    self.assertFalse({'methods','analysis'} & {x.name for x in node.names})
        self.assertEqual(audit.FULL_RAW_GROUPS, (0,))


if __name__ == '__main__':
    unittest.main()
