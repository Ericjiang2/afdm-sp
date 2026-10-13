"""Exact finite-law and numerical fixtures, not new scientific populations."""
import itertools
import json
import math
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from experiments.afdm_collision_resolution import distance_reader as d


class DistanceTests(unittest.TestCase):
    def test_identical_law_has_zero_bridge_and_extremes_remain_bounded(self):
        values = d.bridge_values(np.array([0., 1e-12, -1e-12, 1e300, -1e300]))
        self.assertEqual(values['tv'][0], 0.)
        self.assertEqual(values['hellinger_squared'][0], 0.)
        self.assertAlmostEqual(values['hellinger_squared'][1]/(1e-24/4), 1., places=10)
        np.testing.assert_array_equal(values['tv'][-2:], [1., 1.])
        np.testing.assert_array_equal(values['hellinger_squared'][-2:], [2., 2.])
        with self.assertRaisesRegex(ValueError, 'finite saved'):
            d.bridge_values([np.inf])

    def test_exact_two_point_law_matches_direct_density_distances(self):
        p0, p1 = np.array([.75, .25]), np.array([.25, .75])
        bridge = d.bridge_values(np.log(p1/p0))
        mixture = (p0+p1)/2
        self.assertAlmostEqual(mixture@bridge['tv'], .5)
        self.assertAlmostEqual(mixture@bridge['hellinger_squared'], 2-np.sqrt(3))
        self.assertAlmostEqual(mixture@bridge['hellinger_squared'], np.sum((np.sqrt(p1)-np.sqrt(p0))**2))

    def test_unequal_denominators_keep_equal_distribution_weights(self):
        result = d.stratified_summary([0., 0.], [1., 1., 1., 1., 1., 1.], 1., .05, 224)
        self.assertEqual(result['estimate'], .5)
        self.assertEqual(result['group_weights'], [.5, .5])
        self.assertEqual(result['null']['groups'], 2)
        self.assertEqual(result['alternative']['groups'], 6)
        radius = np.sqrt((1/2+1/6)*np.log(2/(.05/224))/8)
        self.assertAlmostEqual(result['simultaneous']['radius'], radius)
        self.assertGreater(result['simultaneous']['radius'], result['pointwise']['radius'])

    def test_hoeffding_bound_covers_exact_finite_bernoulli_enumeration(self):
        # Enumerate both three-draw samples; no simulated random observations.
        p0, p1, failure = .2, .7, .2
        expectation = (p0+p1)/2
        outside = 0.
        for bits in itertools.product([0, 1], repeat=6):
            a, b = np.array(bits[:3]), np.array(bits[3:])
            probability = np.prod(np.where(a, p0, 1-p0))*np.prod(np.where(b, p1, 1-p1))
            band = d.hoeffding_interval((a.mean()+b.mean())/2, 3, 3, 1., failure)
            if not band['lower']<=expectation<=band['upper']:
                outside += probability
        self.assertLessEqual(outside, failure)

    def test_tensor_identity_matches_explicit_two_draw_product_law(self):
        p0, p1 = np.array([.6, .4]), np.array([.2, .8])
        h1 = np.sum((np.sqrt(p0)-np.sqrt(p1))**2)
        q0, q1 = np.outer(p0, p0).ravel(), np.outer(p1, p1).ravel()
        h2 = np.sum((np.sqrt(q0)-np.sqrt(q1))**2)
        self.assertAlmostEqual(d.tensor_hellinger(h1, 2), h2)
        np.testing.assert_array_equal(d.tensor_hellinger([0., 2.], 256), [0., 2.])
        self.assertAlmostEqual(d.tensor_hellinger(1e-14, 256)/256, 1e-14, places=24)
        with self.assertRaises(ValueError):
            d.tensor_hellinger(2.1, 4)

    def test_proxy_error_range_requires_uniform_log_ratio_certificate(self):
        self.assertIsNone(d.uniform_log_ratio_bias_bound(None))
        epsilon = .07
        x = np.array([-100., -2., -.001, 0., .1, 2., 100.])
        first, second = d.bridge_values(x), d.bridge_values(x+epsilon)
        bound = d.uniform_log_ratio_bias_bound(epsilon)
        for metric in first:
            self.assertLessEqual(np.max(abs(first[metric]-second[metric])), bound[metric])
        # Identical distributions with an inaccurate log ratio yield a positive
        # proxy. A concentration interval for it cannot certify a true distance.
        proxy = d.bridge_values([1., 1.])
        self.assertGreater(proxy['tv'].mean(), 0.)
        self.assertGreater(proxy['hellinger_squared'].mean(), 0.)

    def test_sample_variance_and_se_are_explicit_not_a_confidence_claim(self):
        result = d.sample_summary([1., 2., 3.])
        self.assertEqual(result['groups'], 3)
        self.assertEqual(result['mean'], 2.)
        self.assertEqual(result['sample_variance'], 1.)
        self.assertAlmostEqual(result['standard_error'], 1/math.sqrt(3))
        with self.assertRaises(ValueError):
            d.sample_summary([1.])

    def test_complete_reader_fixture_and_source_hash_failure(self):
        # Artificial saved ratios only. The expensive historical hash traversal
        # is mocked; record/consumed-file binding checks still execute below.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, output = root/'source', root/'output'
            source.mkdir(); output.mkdir()
            protected = root/'protected.json'
            protected.write_text('{}')
            null = np.array([[[-1., -.4, .2]], [[-2., -.5, .3]]])
            alternative = np.array([[[-.2, .5, 1.]], [[-.1, 1., 2.]]])
            np.savez(source/'oracle_control.npz', candidates=[[0., .1], [.04, .1]],
                pair_indices=[[0, 1]], repeats=[1, 4], evaluation_null_llr=null,
                evaluation_alt_llr=alternative, calibration_llr=np.full((2, 1, 3), np.nan))
            rows = [dict(family='control', pair_id=0, repeats=repeat, null_condition=0,
                alt_condition=1, false_alarm=dict(groups=3), power=dict(groups=3)) for repeat in [1, 4]]
            (source/'oracle_pairs.json').write_text(json.dumps(rows))
            (source/'input_audit.json').write_text(json.dumps([dict(family='control', reference_qualification=dict(fixture=True))]))
            registration = dict(git_head='fixture', config=dict(inputs=dict(control=dict(reference_method='exact'))))
            (source/'registration.json').write_text(json.dumps(registration))
            manifest = {str(path.relative_to(root)):d.sha(path) for path in source.iterdir()}
            (source/'attempt.json').write_text(json.dumps(dict(status='complete', artifact_sha256=manifest)))
            consumed = ['oracle_control.npz', 'oracle_pairs.json', 'input_audit.json']
            config = dict(source_stage_path='source', source_git_head='fixture',
                bound_records={name:d.sha(source/name) for name in ['registration.json', 'attempt.json']},
                consumed_artifacts={name:d.sha(source/name) for name in consumed},
                protected_manifest_sha256=d.sha(protected),
                families=dict(control=dict(pairs=1, repeats=[1, 4], evaluation_groups=3,
                    distance_target='artificial fixture', interval_target='artificial fixture')),
                interval_failure_probability=.05, simultaneous_comparisons=4, expected_rows=2,
                projection_repeats=[1, 4, 8, 16, 64, 256], expected_projection_rows=6)
            config_path = root/'config.json'
            config_path.write_text(json.dumps(config))
            with (patch.object(d, 'ROOT', root), patch.object(d, 'PROTECTED', protected),
                  patch.object(d, 'CONFIG_PATH', config_path),
                  patch.object(d, 'audit_hashes', return_value=dict(counts={'fixture':1}))):
                result = d.calculate(output)
                self.assertEqual(result['cases'], 2)
                self.assertEqual(result['projections'], 6)
                self.assertFalse(result['actual_distance_certified'])
                saved = json.loads((output/'distance_cases.json').read_text())
                self.assertEqual(saved[0]['tv']['null']['groups'], 3)
                with np.load(output/'bridge_control.npz') as archive:
                    np.testing.assert_allclose(archive['null_tv'], d.bridge_values(null)['tv'])
                    self.assertNotIn('calibration_llr', archive.files)
                    self.assertNotIn('evaluation_null_llr', archive.files)
                (source/'oracle_pairs.json').write_text('[]')
                with self.assertRaisesRegex(ValueError, 'bound evaluation artifact changed'):
                    d.verify_bindings(config)


if __name__ == '__main__':
    unittest.main()
