"""Deterministic saved-record fixtures, never sampled scientific observations."""
import copy
import gzip
import json
import math
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from experiments.afdm_method_advantage import analysis


def write_json(path, value):
    Path(path).write_text(json.dumps(value, allow_nan=False))


def fixture_config():
    null = dict(mu=.31, tau=1., sigma2=.2, delta=0., role='grid_null')
    alternative = dict(null, delta=.015, role='within_branch')
    return dict(seed=[2026, 10, 5, 0], repeats=[64, 256], calibration_groups=19,
        evaluation_groups=40, alpha=.05, null_points=[null], evaluation_points=[null, alternative],
        methods=['full_score', 'moment_score', 'moment_raw', 'moment_j', 'second_moment'],
        method_config=dict(fixture=True), comparison=dict(primary_candidate='moment_score',
            baselines=['moment_j', 'second_moment', 'full_score'], family_size=6, confidence=.95,
            null_wilson_upper_limit=.1, minimum_power_gain=.1, noninferiority_margin=.1,
            minimum_cost_ratio=2.))


def fixture_record(point, group, repeat, mode):
    values = {}
    for method in fixture_config()['methods']:
        if mode == 'calibration':
            value = float(group)
        elif point['delta'] == 0:
            value = 0.
        else:
            limit = 30 if method in ('moment_score', 'moment_raw') else 10
            value = 20. if group < limit else 0.
        values[method] = value
    fit = dict(theta=[point['mu'], math.log(point['tau']), math.log(point['sigma2'])],
               success=True, on_boundary=False, total_evaluations=3)
    true_r = point['delta']**2*math.log(1/point['delta']**2) if point['delta'] else 0.
    estimate = dict(unconstrained=true_r, one_sided=true_r, local_only=True)
    cold = group == 0 and repeat == 64
    return dict(local_condition=0, group=group, repeats=repeat, complete_seconds=7.1,
        statistics=values, fits=dict(mle=copy.deepcopy(fit), m14=copy.deepcopy(fit)),
        r_hat=dict(full_score=copy.deepcopy(estimate), moment_score=copy.deepcopy(estimate)),
        diagnostics=dict(second_moment=dict(fitted_variance_pairs=[1., 2.])), failures=[],
        observations=repeat, costs=dict(setup_seconds=10. if cold else .1,
            setup_original_construction_seconds=9., setup_cache_hit=not cold,
            per_method_setup_included=False, joint_complete_seconds=7., shared_result_conversion_seconds=.01,
            per_method_seconds=dict(full_score=4., moment_score=1., moment_raw=1., moment_j=2., second_moment=.5)))


class ProbabilityTests(unittest.TestCase):
    def test_rank_128_is_123_and_rejection_is_strict(self):
        cutoff = analysis.rank_threshold(list(range(128)), .05)
        self.assertEqual(cutoff['order_index_one_based'], 123)
        self.assertEqual(cutoff['threshold'], 122)
        rejected, failed = analysis.apply_threshold([121., 122., 123., None], cutoff)
        self.assertEqual(rejected.tolist(), [False, False, True, False])
        self.assertEqual(failed.tolist(), [False, False, False, True])
        tied = analysis.rank_threshold([1.]*128, .05)
        self.assertFalse(analysis.apply_threshold([1.], tied)[0][0])

    def test_calibration_failures_rank_as_infinity_without_dropping(self):
        few = analysis.rank_threshold([0.]*123+[None]*5, .05)
        self.assertTrue(few['finite_threshold'])
        self.assertEqual((few['groups'], few['failed'], few['threshold']), (128, 5, 0.))
        many = analysis.rank_threshold([0.]*122+[None]*6, .05)
        self.assertFalse(many['finite_threshold'])
        self.assertIsNone(many['threshold'])
        rejected, failed = analysis.apply_threshold([1e10, None], many)
        self.assertEqual(rejected.tolist(), [False, False])
        self.assertEqual(failed.tolist(), [False, True])
        self.assertIsNone(analysis.rank_threshold([0.]*10, .05)['threshold'])

    def test_wilson_known_counts_and_endpoints(self):
        zero = analysis.wilson(0, 192)
        self.assertAlmostEqual(zero['lower'], 0.)
        self.assertAlmostEqual(zero['upper'], 0.01961514606675412)
        full = analysis.wilson(192, 192)
        self.assertAlmostEqual(full['lower'], 1-zero['upper'])
        self.assertAlmostEqual(full['upper'], 1.)
        half = analysis.wilson(96, 192)
        self.assertAlmostEqual(half['lower']+half['upper'], 1.)
        self.assertGreater(analysis.wilson(12, 192)['upper'], .1)

    def test_binomial_intervals_reject_invalid_counts(self):
        for counts in ((1, 0), (-1, 10), (11, 10), (.5, 10), (True, 10)):
            with self.subTest(counts=counts):
                with self.assertRaises(ValueError):
                    analysis.wilson(*counts)
                with self.assertRaises(ValueError):
                    analysis.cp_bounds(*counts, .01)

    def test_cp_endpoints_and_family_tail(self):
        tail, total = .05/(4*84), 192
        zero, full = analysis.cp_bounds(0, total, tail), analysis.cp_bounds(total, total, tail)
        self.assertEqual(zero['lower'], 0.)
        self.assertAlmostEqual(zero['upper'], 1-tail**(1/total))
        self.assertEqual(full['upper'], 1.)
        self.assertAlmostEqual(full['lower'], tail**(1/total))
        paired = analysis.paired_interval([True]*192, [False]*192)
        self.assertAlmostEqual(paired['tail_probability'], tail)
        self.assertAlmostEqual(paired['lower'], 2*tail**(1/total)-1)
        self.assertEqual((paired['discordant_plus'], paired['discordant_minus']), (192, 0))
        self.assertEqual(paired['difference'], 1.)

    def test_paired_interval_uses_discordance_not_unpaired_marginals(self):
        paired = analysis.paired_interval([True, True, False, False], [True, False, True, False], 1)
        self.assertEqual((paired['discordant_plus'], paired['discordant_minus'], paired['concordant']), (1, 1, 2))
        self.assertAlmostEqual(paired['lower'], -paired['upper'])
        same = analysis.paired_interval([True, True, False, False], [True, True, False, False], 1)
        self.assertGreater(same['lower'], paired['lower'])
        larger_family = analysis.paired_interval([True]*192, [False]*192, 84)
        smaller_family = analysis.paired_interval([True]*192, [False]*192, 1)
        self.assertLess(larger_family['lower'], smaller_family['lower'])

    def test_failure_difference_bounds_keep_paired_denominator(self):
        bounds = analysis.failure_difference_bounds([1, 0, 0, 0], [0, 1, 0, 0],
                                                     [0, 0, 1, 1], [0, 0, 0, 1])
        self.assertEqual(bounds['lower'], -.25)
        self.assertEqual(bounds['upper'], .5)


class SavedStudyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.artifact = self.root/'results'
        self.artifact.mkdir()
        self.config = fixture_config()
        self.config_path = self.artifact/'METHOD_CONFIG.json'
        write_json(self.config_path, self.config)
        patched = patch.multiple(analysis, ROOT=self.root, ARTIFACT=self.artifact, CONFIG_PATH=self.config_path)
        patched.start()
        self.addCleanup(patched.stop)
        self.make_all_sources()

    def source_path(self, mode, condition):
        return self.artifact/f'{mode}_{condition}'

    def make_all_sources(self):
        for mode in ('calibration', 'evaluation'):
            points = self.config['null_points' if mode == 'calibration' else 'evaluation_points']
            for condition in range(len(points)):
                if not self.source_path(mode, condition).exists():
                    self.make_source(mode, condition)

    def make_source(self, mode, condition):
        folder = self.source_path(mode, condition)
        folder.mkdir()
        point = self.config['null_points' if mode == 'calibration' else 'evaluation_points'][condition]
        groups = self.config[mode+'_groups']
        observations = groups*max(self.config['repeats'])
        write_json(folder/'registration.json', dict(git_head='deterministic-fixture',
            config=dict(mode=mode, condition=condition, new_observations=observations,
                        frozen_config=copy.deepcopy(self.config))))
        write_json(folder/'results.json', dict(mode=mode, condition=condition, points=[point], groups=groups,
            records=groups*len(self.config['repeats']), new_observations=observations))
        write_json(folder/'generation.json', [dict(point=point,
            seed=[*self.config['seed'], 1 if mode == 'calibration' else 2, condition, 0],
            seconds=.1, branch='deterministic metadata fixture')])
        write_json(folder/'records.json', [fixture_record(point, group, repeat, mode)
            for group in range(groups) for repeat in self.config['repeats']])
        # The reader must hash opaque observation bytes, never load/generate data.
        (folder/'observations_00.npz').write_bytes(b'fixture only: no sampled observations')
        write_json(folder/'attempt.json', dict(status='complete', wall_seconds=2., cpu_seconds=1.5,
            reserved_wall_seconds=5., reserved_new_observations=observations))
        self.seal(folder)
        return folder

    def seal(self, folder):
        attempt = analysis.read_json(folder/'attempt.json')
        attempt['artifact_sha256'] = {str(path.relative_to(self.root)):analysis.sha(path)
            for path in folder.rglob('*') if path.is_file() and path.name != 'attempt.json'}
        write_json(folder/'attempt.json', attempt)

    def compress_records(self, folder):
        plain = folder/'records.json'
        compressed = folder/'records.json.gz'
        compressed.write_bytes(gzip.compress(plain.read_bytes(), mtime=0))
        plain.unlink()
        self.seal(folder)
        return compressed

    def bindings(self):
        return analysis.discover_inputs(self.artifact, self.config)[0]

    def datasets(self):
        return analysis.load_records(self.bindings(), self.config)

    def mutate_record(self, mutate, mode='evaluation', condition=1):
        folder = self.source_path(mode, condition)
        records = analysis.read_json(folder/'records.json')
        mutate(records)
        write_json(folder/'records.json', records)
        self.seal(folder)

    def calculations(self):
        datasets = self.datasets()
        cutoffs = analysis.calibrate(datasets, self.config)
        metrics, decisions = analysis.rates(datasets, cutoffs, self.config)
        totals, point_costs, actual = analysis.cost_analysis(datasets, self.config)
        return datasets, cutoffs, metrics, decisions, totals, point_costs, actual

    def test_full_unique_coverage_and_archive_bindings(self):
        bindings, excluded = analysis.discover_inputs(self.artifact, self.config)
        self.assertEqual(len(bindings), 3)
        self.assertEqual(excluded, [])
        checked = analysis.verify_inputs(bindings)
        self.assertEqual(checked['stages'], 3)
        self.assertEqual(checked['observations_archives'], 3)
        datasets = analysis.load_records(bindings, self.config)
        self.assertEqual(len(datasets['evaluation', 1]['records']), 80)

    def test_missing_stage_is_not_silently_skipped(self):
        shutil.rmtree(self.source_path('evaluation', 1))
        with self.assertRaisesRegex(ValueError, 'coverage mismatch'):
            self.bindings()

    def test_duplicate_condition_is_rejected(self):
        shutil.copytree(self.source_path('evaluation', 1), self.artifact/'other-name')
        with self.assertRaisesRegex(ValueError, 'duplicate completed'):
            self.bindings()

    def test_failed_scientific_stages_are_not_skipped(self):
        for mode in ('calibration', 'evaluation'):
            with self.subTest(mode=mode):
                folder = self.source_path(mode, 0)
                attempt = analysis.read_json(folder/'attempt.json')
                attempt['status'] = 'invalid_partial'
                write_json(folder/'attempt.json', attempt)
                with self.assertRaisesRegex(ValueError, 'cannot be silently skipped'):
                    self.bindings()
                attempt['status'] = 'complete'
                write_json(folder/'attempt.json', attempt)

    def test_failed_qualification_is_explicitly_excluded(self):
        folder = self.artifact/'qualification_v1'
        folder.mkdir()
        write_json(folder/'registration.json', dict(config=dict(mode='qualification')))
        write_json(folder/'attempt.json', dict(status='invalid_partial', reserved_wall_seconds=10,
                                              reserved_new_observations=2048))
        bindings, excluded = analysis.discover_inputs(self.artifact, self.config)
        self.assertEqual(len(bindings), 3)
        self.assertEqual(excluded[0]['status'], 'invalid_partial')
        self.assertEqual(excluded[0]['reserved_new_observations'], 2048)
        self.assertIn('never counted as evaluation', excluded[0]['reason'])

    def test_source_point_and_observation_count_must_match_registration(self):
        folder = self.source_path('evaluation', 1)
        result = analysis.read_json(folder/'results.json')
        result['new_observations'] -= 1
        write_json(folder/'results.json', result)
        with self.assertRaisesRegex(ValueError, 'observation allocation'):
            self.bindings()

    def test_bound_records_and_observation_tampering_are_rejected(self):
        for name in ('records.json', 'observations_00.npz'):
            with self.subTest(name=name):
                bindings = self.bindings()
                path = self.source_path('evaluation', 1)/name
                original = path.read_bytes()
                path.write_bytes(original+b' ')
                with self.assertRaisesRegex(ValueError, 'changed'):
                    analysis.verify_inputs(bindings)
                path.write_bytes(original)

    def test_compressed_records_bind_actual_compressed_bytes(self):
        folder = self.source_path('evaluation', 1)
        expected = analysis.read_json(folder/'records.json')
        compressed = self.compress_records(folder)
        self.assertEqual(analysis.read_json(compressed), expected)
        bindings = self.bindings()
        binding = next(row for row in bindings if row['mode'] == 'evaluation' and row['condition'] == 1)
        self.assertIn('records.json.gz', binding['metadata_sha256'])
        self.assertNotIn('records.json', binding['metadata_sha256'])
        self.assertEqual(binding['metadata_sha256']['records.json.gz'], analysis.sha(compressed))
        analysis.verify_inputs(bindings)
        self.assertEqual(len(analysis.load_records(bindings, self.config)['evaluation', 1]['records']), 80)
        compressed.write_bytes(compressed.read_bytes()+b' ')
        with self.assertRaisesRegex(ValueError, 'changed'):
            analysis.verify_inputs(bindings)

    def test_duplicate_plain_and_compressed_records_are_rejected(self):
        folder = self.source_path('evaluation', 1)
        bindings = self.bindings()
        (folder/'records.json.gz').write_bytes(gzip.compress((folder/'records.json').read_bytes(), mtime=0))
        with self.assertRaisesRegex(ValueError, 'exactly one records'):
            self.bindings()
        with self.assertRaisesRegex(ValueError, 'exactly one records'):
            analysis.load_records(bindings, self.config)

    def test_missing_or_invalid_compressed_records_do_not_fall_back(self):
        folder = self.source_path('evaluation', 1)
        (folder/'records.json').unlink()
        with self.assertRaisesRegex(ValueError, 'exactly one records'):
            self.bindings()
        (folder/'records.json.gz').write_bytes(b'not a gzip file')
        self.seal(folder)
        with self.assertRaises(gzip.BadGzipFile):
            self.datasets()

    def test_record_encoding_cannot_change_after_binding(self):
        bindings = self.bindings()
        self.compress_records(self.source_path('evaluation', 1))
        with self.assertRaisesRegex(ValueError, 'not bound'):
            analysis.load_records(bindings, self.config)

    def test_unbound_extra_file_and_missing_archive_are_rejected(self):
        bindings = self.bindings()
        extra = self.source_path('evaluation', 1)/'unregistered.txt'
        extra.write_text('not in manifest')
        with self.assertRaisesRegex(ValueError, 'inventory changed'):
            analysis.verify_inputs(bindings)
        extra.unlink()
        folder = self.source_path('evaluation', 1)
        (folder/'observations_00.npz').unlink()
        self.seal(folder)
        with self.assertRaisesRegex(ValueError, 'exactly one saved observation'):
            analysis.verify_inputs(self.bindings())

    def test_records_require_all_unique_group_prefixes(self):
        self.mutate_record(lambda rows: rows.__setitem__(1, copy.deepcopy(rows[0])))
        with self.assertRaisesRegex(ValueError, 'duplicate group/R'):
            self.datasets()

    def test_generation_split_seed_is_verified(self):
        folder = self.source_path('evaluation', 1)
        generation = analysis.read_json(folder/'generation.json')
        generation[0]['seed'][-3] = 1
        write_json(folder/'generation.json', generation)
        self.seal(folder)
        with self.assertRaisesRegex(ValueError, 'split/condition seed'):
            self.datasets()

    def test_unrelated_failure_cannot_hide_missing_statistic(self):
        def mutate(rows):
            rows[0]['statistics']['moment_score'] = None
            rows[0]['failures'] = [dict(method='full_score', kind='tangent_unavailable', reason='fixture')]
        self.mutate_record(mutate)
        with self.assertRaisesRegex(ValueError, 'matching method failure'):
            self.datasets()

    def test_tangent_failure_preserves_j_but_optimizer_failure_disables_it(self):
        def tangent(rows):
            for method in ('moment_score', 'moment_raw'):
                rows[0]['statistics'][method] = None
            rows[0]['r_hat']['moment_score'] = None
            rows[0]['failures'] = [dict(method='moment_score', kind='tangent_unavailable', reason='fixture')]
        self.mutate_record(tangent)
        self.assertIsNotNone(self.datasets()['evaluation', 1]['records'][0, 64]['statistics']['moment_j'])
        self.mutate_record(lambda rows: rows[0]['statistics'].__setitem__('moment_j', None))
        with self.assertRaisesRegex(ValueError, 'matching method failure'):
            self.datasets()
        def optimizer(rows):
            rows[0]['fits']['m14']['success'] = False
            rows[0]['failures'][0]['kind'] = 'optimizer_failed'
        self.mutate_record(optimizer)
        self.assertIsNone(self.datasets()['evaluation', 1]['records'][0, 64]['statistics']['moment_j'])

    def test_failed_fit_cannot_return_finite_statistic(self):
        self.mutate_record(lambda rows: rows[0]['fits']['mle'].__setitem__('success', False))
        with self.assertRaisesRegex(ValueError, 'failed fit returned'):
            self.datasets()

    def test_missing_conversion_cost_is_not_silently_zero(self):
        self.mutate_record(lambda rows: rows[0]['costs'].pop('shared_result_conversion_seconds'))
        with self.assertRaises(KeyError):
            self.datasets()

    def test_evaluation_failure_remains_in_rate_and_disables_advantage(self):
        def mutate(rows):
            row = rows[0]
            for method in ('moment_score', 'moment_raw', 'moment_j'):
                row['statistics'][method] = None
            row['fits']['m14']['success'] = False
            row['r_hat']['moment_score'] = None
            row['failures'] = [dict(method='moment_score', kind='optimizer_failed', reason='fixture')]
        self.mutate_record(mutate)
        _, cutoffs, metrics, decisions, _, costs, _ = self.calculations()
        row = metrics[1, 64, 'moment_score']
        self.assertEqual((row['groups'], row['rejections'], row['statistic_failures']), (40, 29, 1))
        self.assertEqual(row['rate'], 29/40)
        self.assertEqual(row['failure_bounds']['upper'], 30/40)
        comparisons = analysis.compare(metrics, decisions, cutoffs, costs, self.config)
        self.assertTrue(all(not row['power_advantage'] and not row['cost_advantage'] for row in comparisons if row['repeats'] == 64))
        self.assertTrue(any(row['power_advantage'] for row in comparisons if row['repeats'] == 256))

    def test_advantage_requires_each_registered_gate(self):
        _, cutoffs, metrics, decisions, _, costs, _ = self.calculations()
        def compare():
            return analysis.compare(metrics, decisions, cutoffs, costs, self.config)
        first = compare()[0]
        self.assertTrue(first['power_advantage'])
        full = next(row for row in compare() if row['baseline'] == 'full_score' and row['repeats'] == 64)
        self.assertTrue(full['cost_advantage'])
        self.assertFalse(first['cost_advantage'])  # Cold setup takes the J ratio below two.
        cutoffs[64, 'moment_score']['failed'] = 1
        self.assertFalse(compare()[0]['power_advantage'])
        cutoffs[64, 'moment_score']['failed'] = 0
        metrics[0, 64, 'moment_j']['wilson']['upper'] = .1001
        self.assertFalse(compare()[0]['power_advantage'])
        metrics[0, 64, 'moment_j']['wilson']['upper'] = .1
        self.assertTrue(compare()[0]['power_advantage'])
        metrics[0, 64, 'moment_j']['statistic_failures'] = 1
        self.assertFalse(compare()[0]['power_advantage'])

    def test_large_cost_ratio_does_not_override_noninferiority(self):
        _, cutoffs, metrics, decisions, _, costs, _ = self.calculations()
        decisions[1, 64, 'moment_score']['rejected'][:] = False
        decisions[1, 64, 'full_score']['rejected'][:] = True
        costs[1, 64, 'full_score']['complete_amortized_seconds_per_group'] = 1e6
        comparisons = analysis.compare(metrics, decisions, cutoffs, costs, self.config)
        row = next(row for row in comparisons if row['baseline'] == 'full_score' and row['repeats'] == 64)
        self.assertGreater(row['cost_ratio'], 2.)
        self.assertFalse(row['cost_advantage'])

    def test_off_grid_append_is_not_in_primary_family_or_theorem(self):
        previous = copy.deepcopy(self.config)
        point = dict(mu=.3, tau=.9, sigma2=.5, delta=0., role='off_grid_null')
        self.config['evaluation_points'].append(point)
        analysis.compatible_config(previous, self.config)
        self.make_all_sources()
        _, cutoffs, metrics, decisions, _, costs, _ = self.calculations()
        self.assertFalse(metrics[2, 64, 'moment_score']['finite_grid_theorem_applies'])
        self.assertTrue(metrics[0, 64, 'moment_score']['finite_grid_theorem_applies'])
        comparisons = analysis.compare(metrics, decisions, cutoffs, costs, self.config)
        self.assertEqual(len(comparisons), 6)
        self.assertTrue(all(row['condition'] == 1 for row in comparisons))
        self.assertEqual(costs[1, 64, 'moment_score']['calibration_allocation_denominator'], 120)

    def test_config_changes_cannot_sneak_in_alternatives_or_grid_duplicates(self):
        changed = copy.deepcopy(self.config)
        changed['evaluation_points'].append(dict(changed['evaluation_points'][1], delta=.025))
        with self.assertRaisesRegex(ValueError, 'post-source alternative'):
            analysis.compatible_config(self.config, changed)
        changed = copy.deepcopy(self.config)
        changed['null_points'].append(changed['null_points'][0])
        with self.assertRaisesRegex(ValueError, 'unique scientific points'):
            analysis.validate_config(changed)
        changed = copy.deepcopy(self.config)
        changed['evaluation_points'][1]['sigma2'] = float('nan')
        with self.assertRaisesRegex(ValueError, 'finite number'):
            analysis.validate_config(changed)

    def test_coordinate_and_physical_rmse_keep_failed_fit_denominator(self):
        point = self.config['evaluation_points'][1]
        rows = [fixture_record(point, i, 64, 'evaluation') for i in range(2)]
        rows[1]['fits']['m14'].update(theta=[point['mu']+.02, math.log(2.), math.log(.4)],
                                       success=False, on_boundary=True)
        result = analysis.fit_summary(rows, 'moment_score', point)
        self.assertEqual((result['failed_fits'], result['boundary']), (1, 1))
        np.testing.assert_allclose(result['all_coordinate_errors']['rmse'], [.02, math.log(2), math.log(2)]/np.sqrt(2))
        np.testing.assert_allclose(result['all_physical_errors']['rmse'], np.array([.02, 1., .2])/np.sqrt(2))
        self.assertEqual(result['successful_physical_errors']['count'], 1)
        self.assertEqual(result['successful_physical_errors']['rmse'], [0., 0., 0.])
        self.assertIn('model mismatch', result['scope'])

    def test_local_r_error_only_interpreted_on_true_fixed_branch(self):
        point = self.config['evaluation_points'][1]
        rows = [fixture_record(point, 0, 64, 'evaluation')]
        local = analysis.local_estimation(rows, 'moment_score', point)
        self.assertTrue(local['eligible'])
        self.assertEqual(local['one_sided']['relative_rmse'], 0.)
        for delta in (.06, .12):
            with self.subTest(delta=delta):
                outside = dict(point, delta=delta, role='finite_separation')
                result = analysis.local_estimation(rows, 'moment_score', outside)
                self.assertFalse(result['eligible'])
                self.assertFalse(result['true_branch_preserved'])
                self.assertNotIn('true_r', result)
        boundary_cross = dict(point, mu=.27, delta=.005, role='original_weak_signal')
        self.assertFalse(analysis.local_estimation(rows, 'moment_score', boundary_cross)['eligible'])
        self.assertFalse(analysis.local_estimation(rows, 'moment_score', self.config['null_points'][0])['eligible'])

    def test_setup_is_charged_for_r256_and_c2_avoids_family_setup(self):
        datasets = self.datasets()
        dataset = datasets['evaluation', 1]
        first = analysis.path_cost(dataset, 64, 'moment_score', 40)
        second = analysis.path_cost(dataset, 256, 'moment_score', 40)
        c2 = analysis.path_cost(dataset, 256, 'second_moment', 40)
        self.assertEqual((first['cold_setup_seconds'], second['cold_setup_seconds']), (10., 10.))
        self.assertEqual(second['standalone_seconds'], 40+10+4)
        self.assertEqual(second['cold_first_group_seconds'], 11.)
        self.assertEqual((c2['cold_setup_seconds'], c2['warm_setup_seconds']), (0., 0.))
        self.assertEqual(c2['standalone_seconds'], 20.)

    def test_calibration_is_amortized_over_whole_fixed_evaluation_workload(self):
        datasets = self.datasets()
        totals, costs, actual = analysis.cost_analysis(datasets, self.config)
        row = totals[256, 'moment_score']
        calibration = 19+10+1.9
        evaluation = 2*(40+10+4)
        self.assertAlmostEqual(row['calibration_seconds'], calibration)
        self.assertAlmostEqual(row['fixed_workload_amortized_seconds'], (calibration+evaluation)/80)
        self.assertAlmostEqual(costs[1, 256, 'moment_score']['complete_amortized_seconds_per_group'], 54/40+calibration/80)
        self.assertEqual(actual[0]['actual_joint_inference_seconds'], 19*2*7.)
        self.assertNotEqual(sum(item['calibration_seconds'] for item in totals.values()), actual[0]['actual_joint_inference_seconds'])

    def test_small_saved_data_pipeline_no_sampling_or_refitting(self):
        self.assert_saved_pipeline()

    def test_small_gzip_saved_data_pipeline_no_sampling_or_refitting(self):
        for mode, condition in (('calibration', 0), ('evaluation', 0), ('evaluation', 1)):
            self.compress_records(self.source_path(mode, condition))
        self.assert_saved_pipeline()

    def assert_saved_pipeline(self):
        output = self.artifact/'summary_fixture'
        output.mkdir()
        bindings, excluded = analysis.discover_inputs(self.artifact, self.config, output.name)
        write_json(output/'registration.json', dict(config=dict(frozen_config=self.config,
            source_bindings=bindings, excluded_stages=excluded,
            method_config_sha256=analysis.sha(self.config_path))))
        before = analysis.verify_inputs(bindings)
        result = analysis.calculate(output)
        self.assertEqual(result['new_observations'], 0)
        self.assertEqual(result['comparison_rows'], 6)
        self.assertEqual(result['metric_rows'], 20)
        self.assertEqual(result['input_hash_counts'], before)
        self.assertTrue((output/'COST_RESULTS.md').exists())
        self.assertEqual(len(analysis.read_json(output/'comparisons.json')), 6)
        with np.load(output/'decisions.npz') as decisions:
            self.assertEqual(decisions['rejected'].shape, (2, 2, 5, 40))
            self.assertEqual(decisions['failed'].sum(), 0)


if __name__ == '__main__':
    unittest.main()
