"""Selected-cohort contracts using synthetic saved metadata, never sampled observations."""
import copy
import gzip
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np

from experiments.afdm_method_advantage import analysis, supplement
from experiments.afdm_method_advantage.test_analysis import fixture_config, fixture_record, write_json


class SupplementTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.artifact = self.root/'results'
        self.artifact.mkdir()
        self.primary = fixture_config()
        self.primary.update(calibration_groups=128, failure_policy=dict(fixture='explicit failure'))
        self.config = copy.deepcopy(self.primary)
        null = dict(self.primary['null_points'][0], role='selected_fresh_null')
        alternative = dict(null, delta=.12, role='selected_finite_separation')
        self.config.update(schema='method-advantage-supplement/1', seed=[2026, 10, 5, 0, 99], repeats=[256],
            evaluation_groups=80, evaluation_points=[null, alternative], selection='fixture selected after primary analysis',
            new_confirmation_stream=False, receiver_calls=0, decoder_calls=0,
            calibration_reference='results/summary_v1/calibration.json', primary_metrics_reference='results/summary_v1/metrics.json',
            primary_costs_reference='results/summary_v1/costs.json')
        self.config['comparison'] = dict(candidate='moment_score', baselines=['moment_j', 'full_score'],
            family_size=2, confidence=.95, minimum_power_gain=.1, noninferiority_margin=.1,
            minimum_cost_ratio=2., minimum_useful_power_lower=.8, null_wilson_upper_limit=.1)
        self.config_path = self.artifact/'SUPPLEMENT_CONFIG.json'
        write_json(self.config_path, self.config)
        self.study_path, self.methods_path = self.root/'study.py', self.root/'methods.py'
        self.study_path.write_text('# source-bound fixture only\n')
        self.methods_path.write_text('# source-bound fixture only\n')
        for patched in (patch.multiple(supplement, ROOT=self.root, ARTIFACT=self.artifact, CONFIG_PATH=self.config_path,
                                       STUDY_PATH=self.study_path, METHODS_PATH=self.methods_path),
                        patch.multiple(analysis, ROOT=self.root, ARTIFACT=self.artifact)):
            patched.start()
            self.addCleanup(patched.stop)
        self.make_reference()
        self.reference = supplement.bind_reference(self.config)
        for phase in ('null', 'alt'):
            self.make_cohort(phase)

    def seal(self, folder):
        attempt = analysis.read_json(folder/'attempt.json')
        attempt['artifact_sha256'] = {str(path.relative_to(self.root)):analysis.sha(path)
            for path in folder.rglob('*') if path.is_file() and path.name != 'attempt.json'}
        write_json(folder/'attempt.json', attempt)

    def make_reference(self):
        folder = self.artifact/'summary_v1'
        folder.mkdir()
        write_json(folder/'registration.json', dict(config=dict(mode='analysis', frozen_config=self.primary)))
        write_json(folder/'results.json', dict(family_size=84, source_hashes_unchanged=True))
        write_json(folder/'metrics.json', [dict(scope='selection evidence fixture')])
        thresholds, costs = [], []
        for method in self.config['methods']:
            grid = dict(condition=0, point=self.primary['null_points'][0], groups=128,
                order_index_one_based=123, threshold=19., finite_threshold=True, failed=0, comparison='strictly greater')
            thresholds.append(dict(repeats=256, method=method, threshold=19., finite_threshold=True,
                failed=0, null_grid=[grid], calibration_groups=128, comparison='strictly greater'))
            calibration = 40. if method == 'full_score' else 20.
            costs.append(dict(repeats=256, method=method, calibration_groups=128,
                calibration_path_seconds=calibration-2., calibration_setup_seconds=2., calibration_seconds=calibration))
        write_json(folder/'calibration.json', thresholds)
        write_json(folder/'costs.json', costs)
        write_json(folder/'attempt.json', dict(status='complete'))
        self.seal(folder)

    def cohort_folder(self, phase):
        return self.artifact/supplement.STAGES[phase]

    def make_cohort(self, phase):
        condition = 0 if phase == 'null' else 1
        folder = self.cohort_folder(phase)
        folder.mkdir()
        point = self.config['evaluation_points'][condition]
        groups = self.config['evaluation_groups']
        source = supplement.implementation_hashes()
        specification = dict(seed=self.config['seed'], mode='evaluation', cohort='selected_supplement', phase=phase,
            condition=condition, frozen_config=self.config, reference_binding=self.reference,
            implementation_sha256=source, new_observations=groups*256,
            supplement_config_sha256=analysis.sha(self.config_path))
        write_json(folder/'registration.json', dict(config=specification, git_head='fixture', source_sha256=source))
        write_json(folder/'results.json', dict(mode='evaluation', condition=condition, points=[point],
            groups=groups, records=groups, new_observations=groups*256))
        write_json(folder/'generation.json', [dict(point=point, seed=[*self.config['seed'], 2, condition, 0],
                                                 seconds=.01, branch='saved fixture')])
        rows = []
        for group in range(groups):
            row = fixture_record(point, group, 256, 'evaluation')
            for method in ('moment_score', 'moment_raw', 'full_score'):
                row['statistics'][method] = 20. if phase == 'alt' else 0.
            row['costs'].update(setup_cache_hit=group != 0, setup_seconds=10. if group == 0 else .1)
            for method in ('moment_score', 'full_score'):
                row['r_hat'][method].update(fitted_delta_branch_radius=.04, r_branch_max=.01,
                    outside_fitted_local_branch=phase == 'alt', unconstrained_below_zero=False)
            rows.append(row)
        self.write_records(folder, rows)
        (folder/'observations_00.npz').write_bytes(b'deterministic fixture bytes; not research samples')
        write_json(folder/'attempt.json', dict(status='complete', reserved_new_observations=groups*256,
                                              reserved_wall_seconds=120., wall_seconds=2., cpu_seconds=1.5))
        self.seal(folder)

    def write_records(self, folder, rows):
        import json
        (folder/'records.json.gz').write_bytes(gzip.compress(json.dumps(rows, allow_nan=False).encode(), mtime=0))

    def calculations(self):
        bindings = supplement.bind_cohort(self.config, self.reference)
        datasets = analysis.load_records(bindings, self.config)
        thresholds, old_costs = supplement.read_calibration(self.config, self.reference)
        metrics, decisions = analysis.rates(datasets, thresholds, self.config)
        for row in metrics.values():
            row['clopper_pearson'] = dict(**analysis.cp_bounds(row['rejections'], row['groups'], .025),
                                         confidence=.95, tail_probability=.025)
        totals, costs, actual = supplement.cost_analysis(datasets, old_costs, self.config)
        return thresholds, metrics, decisions, totals, costs, actual

    def summary_output(self):
        output = self.artifact/supplement.STAGES['summary']
        output.mkdir()
        write_json(output/'registration.json', dict(config=dict(phase='summary', frozen_config=self.config,
            reference_binding=self.reference, source_bindings=supplement.bind_cohort(self.config, self.reference),
            supplement_config_sha256=analysis.sha(self.config_path))))
        return output

    def test_config_preserves_solver_grid_and_independent_seed(self):
        supplement.validate_config(self.config, self.primary)
        for field, value in (('seed', self.primary['seed']), ('method_config', {'changed':True}),
                             ('null_points', []), ('alpha', .1)):
            with self.subTest(field=field):
                config = copy.deepcopy(self.config)
                config[field] = value
                with self.assertRaises(ValueError):
                    supplement.validate_config(config, self.primary)

    def test_reference_and_old_full_grid_thresholds_are_immutable(self):
        thresholds, costs = supplement.read_calibration(self.config, self.reference)
        self.assertEqual(thresholds[256, 'moment_score']['threshold'], 19.)
        self.assertEqual(costs[256, 'moment_score']['calibration_seconds'], 20.)
        path = self.artifact/'summary_v1/calibration.json'
        path.write_bytes(path.read_bytes()+b' ')
        with self.assertRaisesRegex(ValueError, 'bound primary reference changed'):
            supplement.verify_reference(self.reference)

    def test_only_two_explicit_supplementary_stages_are_inputs(self):
        unrelated = self.artifact/'evaluation_00_v1'
        unrelated.mkdir()
        write_json(unrelated/'registration.json', dict(config=dict(mode='evaluation')))
        write_json(unrelated/'attempt.json', dict(status='invalid_partial'))
        bindings = supplement.bind_cohort(self.config, self.reference)
        self.assertEqual([row['stage'] for row in bindings], [supplement.STAGES['null'], supplement.STAGES['alt']])
        self.assertEqual(analysis.verify_inputs(bindings)['observations_archives'], 2)

    def test_failed_supplement_cannot_fall_back_to_primary_data(self):
        path = self.cohort_folder('alt')/'attempt.json'
        attempt = analysis.read_json(path)
        attempt['status'] = 'invalid_partial'
        write_json(path, attempt)
        with self.assertRaisesRegex(ValueError, 'no fallback'):
            supplement.bind_cohort(self.config, self.reference)

    def test_study_and_method_sources_must_be_bound(self):
        path = self.cohort_folder('alt')/'registration.json'
        registration = analysis.read_json(path)
        registration['source_sha256'].pop('methods.py')
        write_json(path, registration)
        self.seal(path.parent)
        with self.assertRaisesRegex(ValueError, 'not source-bound'):
            supplement.bind_cohort(self.config, self.reference)

    def test_no_old_seed_or_condition_alias_can_replace_new_cohort(self):
        folder = self.cohort_folder('alt')
        generation = analysis.read_json(folder/'generation.json')
        generation[0]['seed'] = [*self.primary['seed'], 2, 1, 0]
        write_json(folder/'generation.json', generation)
        self.seal(folder)
        bindings = supplement.bind_cohort(self.config, self.reference)
        with self.assertRaisesRegex(ValueError, 'split/condition seed'):
            analysis.load_records(bindings, self.config)

    def test_registered_family_two_and_useful_cost_gate_pass_on_fixture(self):
        thresholds, metrics, decisions, _, costs, _ = self.calculations()
        comparisons = supplement.compare(metrics, decisions, thresholds, costs, self.config)
        self.assertEqual(len(comparisons), 2)
        self.assertAlmostEqual(comparisons[0]['paired']['tail_probability'], .05/8)
        self.assertTrue(comparisons[0]['power_advantage'])
        self.assertTrue(comparisons[1]['useful_cost_advantage'])
        self.assertGreater(comparisons[1]['useful_power_cp']['lower'], .8)
        self.assertFalse(comparisons[1]['power_advantage'])
        self.assertFalse(comparisons[0]['useful_cost_advantage'])

    def test_low_power_speed_does_not_become_useful_cost_advantage(self):
        thresholds, metrics, decisions, _, costs, _ = self.calculations()
        for method in ('moment_score', 'full_score'):
            decisions[1, 256, method]['rejected'][30:] = False
            metrics[1, 256, method]['clopper_pearson'] = analysis.cp_bounds(30, 80, .025)
        row = supplement.compare(metrics, decisions, thresholds, costs, self.config)[1]
        self.assertTrue(row['noninferiority_passed'])
        self.assertTrue(row['cost_ratio_passed'])
        self.assertFalse(row['useful_power_passed'])
        self.assertFalse(row['useful_cost_advantage'])

    def test_calibration_failure_and_fresh_null_gate_disable_claims(self):
        thresholds, metrics, decisions, _, costs, _ = self.calculations()
        thresholds[256, 'moment_score']['failed'] = 1
        rows = supplement.compare(metrics, decisions, thresholds, costs, self.config)
        self.assertTrue(all(not row['power_advantage'] and not row['useful_cost_advantage'] for row in rows))
        thresholds[256, 'moment_score']['failed'] = 0
        metrics[0, 256, 'full_score']['wilson']['upper'] = .10001
        self.assertFalse(supplement.compare(metrics, decisions, thresholds, costs, self.config)[1]['useful_cost_advantage'])

    def test_evaluation_failure_keeps_denominator_and_arbitrary_outcome_bounds(self):
        folder = self.cohort_folder('alt')
        rows = analysis.read_json(folder/'records.json.gz')
        rows[0]['statistics']['full_score'] = None
        rows[0]['fits']['mle']['success'] = False
        rows[0]['r_hat']['full_score'] = None
        rows[0]['failures'] = [dict(method='full_score', kind='optimizer_failed', reason='fixture failure')]
        self.write_records(folder, rows)
        self.seal(folder)
        thresholds, metrics, decisions, _, costs, _ = self.calculations()
        metric = metrics[1, 256, 'full_score']
        self.assertEqual((metric['groups'], metric['rejections'], metric['statistic_failures']), (80, 79, 1))
        self.assertEqual(metric['failure_bounds']['upper'], 1.)
        row = supplement.compare(metrics, decisions, thresholds, costs, self.config)[1]
        self.assertFalse(row['useful_cost_advantage'])
        self.assertEqual(row['failure_difference_bounds']['lower'], 0.)
        self.assertEqual(row['failure_difference_bounds']['upper'], 1/80)

    def test_calibration_is_recharged_over_new_workload_and_setup_is_retained(self):
        _, _, _, totals, costs, actual = self.calculations()
        row = costs[1, 256, 'moment_score']
        self.assertEqual(row['calibration_allocation_denominator'], 160)
        self.assertEqual(row['calibration_allocation_seconds_per_group'], 20/160)
        self.assertEqual(row['cold_setup_seconds'], 10.)
        self.assertAlmostEqual(row['complete_amortized_seconds_per_group'], (80+10+7.9)/80+20/160)
        self.assertEqual(totals[256, 'moment_score']['calibration_seconds'], 20.)
        self.assertEqual(costs[1, 256, 'second_moment']['cold_setup_seconds'], 0.)
        self.assertEqual(actual[1]['actual_joint_inference_seconds'], 80*7.)

    def test_saved_r_is_reported_without_physical_delta_interpretation(self):
        bindings = supplement.bind_cohort(self.config, self.reference)
        datasets = analysis.load_records(bindings, self.config)
        rows = list(datasets['evaluation', 1]['records'].values())
        result = supplement.saved_r_diagnostics(rows, 'moment_score')
        self.assertEqual(result['outside_fitted_local_branch'], 80)
        self.assertEqual(result['unconstrained']['count'], 80)
        self.assertFalse(analysis.local_estimation(rows, 'moment_score', self.config['evaluation_points'][1])['eligible'])

    def test_summary_fixture_preserves_primary_and_reports_only_two_comparisons(self):
        before = supplement.verify_reference(self.reference)
        output = self.summary_output()
        result = supplement.calculate(output)
        self.assertEqual(result['new_observations'], 0)
        self.assertEqual((result['comparison_rows'], result['metric_rows']), (2, 10))
        self.assertTrue(result['primary_84_comparisons_unchanged'])
        self.assertEqual(result['useful_cost_advantages'], 1)
        self.assertEqual(supplement.verify_reference(self.reference), before)
        metrics = analysis.read_json(output/'metrics.json')
        self.assertTrue(all(not row['finite_grid_theorem_applies'] for row in metrics))
        self.assertAlmostEqual(metrics[0]['clopper_pearson']['tail_probability'], .025)
        self.assertIn('selected after primary', (output/'SUPPLEMENT_RESULTS.md').read_text())
        with np.load(output/'decisions.npz') as decisions:
            self.assertEqual(decisions['rejected'].shape, (2, 5, 80))

    def test_registered_config_cannot_change_before_summary(self):
        output = self.summary_output()
        self.config_path.write_bytes(self.config_path.read_bytes()+b' ')
        with self.assertRaisesRegex(ValueError, 'configuration changed'):
            supplement.calculate(output)

    def test_sampling_wrapper_delegates_without_changing_study_inputs(self):
        folder = self.cohort_folder('alt')
        fake = SimpleNamespace(calculate=lambda output: dict(mode='evaluation', condition=1, new_observations=80*256))
        with patch.object(supplement, 'study_instance', return_value=fake) as delegated:
            result = supplement.calculate(folder)
        delegated.assert_called_once_with('alt')
        self.assertEqual(result['cohort'], 'selected_supplement')
        self.assertEqual(result['new_observations'], 80*256)


if __name__ == '__main__':
    unittest.main()
