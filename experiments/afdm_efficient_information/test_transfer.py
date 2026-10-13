"""Tiny deterministic/continuous fixtures; not registered research evidence."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from experiments.afdm_efficient_information import features
from experiments.afdm_efficient_information.prior_likelihood import ActualPrior, daft
from experiments.afdm_efficient_information.score import ScoreRegressor
from experiments.afdm_efficient_information.transfer import (
    INPUTS, Costs, InputPrior, amortization, anchored_features, binomial_interval,
    draw_inputs, forward_daft, input_states, inverse_daft, phase_diagnostics,
    rejection_threshold, restore_regressor, sample_observations, stage_cost_inventory,
)


class TransferContracts(unittest.TestCase):
    def test_preloaded_sources_exclude_torch_virtual_namespace_filenames(self):
        from experiments.afdm_efficient_information.transfer_study import preloaded_sources
        paths = preloaded_sources()
        self.assertTrue(paths)
        self.assertTrue(all(path.is_file() for path in paths))
        self.assertIn(Path(__file__).resolve(), paths)

    def test_fft_transform_matches_independent_dense(self):
        rng = np.random.default_rng(8)
        for n in (4, 16, 64):
            y = rng.normal(size=(3, n))+1j*rng.normal(size=(3, n))
            np.testing.assert_allclose(inverse_daft(y), y@daft(n).conj(), atol=2e-12)
            np.testing.assert_allclose(forward_daft(y), y@daft(n).T, atol=2e-12)
            np.testing.assert_allclose(inverse_daft(forward_daft(y)), y, atol=2e-12)

    def test_legal_input_masses_constraints_and_nonuniform_mean(self):
        counts = {'uniform': 256, 'pilot': 64, 'biased': 256, 'repetition': 16}
        for kind in INPUTS:
            words, mass = input_states(4, kind)
            self.assertEqual(len(words), counts[kind])
            self.assertAlmostEqual(float(mass.sum()), 1.)
            self.assertTrue(np.all(mass > 0))
            drawn = draw_inputs(16, 7, kind, np.random.default_rng(11))
            if kind == 'pilot':
                np.testing.assert_allclose(words[:, 0], np.exp(1j*np.pi/4))
                np.testing.assert_allclose(drawn[:, 0], np.exp(1j*np.pi/4))
            if kind == 'repetition':
                np.testing.assert_allclose(words[:, ::2], words[:, 1::2])
                np.testing.assert_allclose(drawn[:, ::2], drawn[:, 1::2])
        words, mass = input_states(4, 'biased')
        self.assertGreater(abs(mass@words[:, 0]), .2)
        uniform, mass = input_states(4, 'uniform')
        self.assertLess(abs(mass@uniform[:, 0]), 1e-14)

    def test_uniform_sampler_matches_actual_pushforward_and_replays_raw(self):
        theta = np.array([.2, .35, 0., np.log(.8)])
        expected = ActualPrior(n=4).sample(theta, 5, [913])
        raw, _, _ = sample_observations(4, theta, 5, [913])
        np.testing.assert_allclose(raw['y_time'], expected, atol=3e-13)
        response = raw['gain']@raw['response_atoms'].T
        replay = np.exp(theta[2]/2)*response*raw['time_input']+np.exp(theta[3]/2)*raw['noise_base']
        np.testing.assert_array_equal(raw['y_time'], replay)
        with self.assertRaisesRegex(ValueError, 'Gaussian control'):
            sample_observations(4, theta, 1, [1], gain_prior='gaussian', generator='g0')

    def test_full_uniform_words_equal_orbit_reduction(self):
        theta = np.array([.2, .35, 0., np.log(.8)])
        y = np.array([[.2+.1j, -.4+.3j, .8-.2j, .1+.6j]])
        orbit = ActualPrior(n=4, order=4, phases=8)
        full = InputPrior(n=4, order=4, phases=8, input_kind='uniform')
        np.testing.assert_allclose(full.logpdf(y, theta), orbit.logpdf(y, theta), atol=2e-12)
        np.testing.assert_allclose(full.logpdf(y*np.exp(.31j), theta), full.logpdf(y, theta), atol=2e-12)
        with self.assertRaisesRegex(ValueError, 'not score'):
            full.evaluate(y, theta)

    def test_platform_density_identity_with_legal_inputs(self):
        first = np.array([.005, .04, 0., 0.])
        second = np.array([.015, .04, 0., 0.])
        y = np.array([[.2+.1j, -.4+.3j, .8-.2j, .1+.6j]])
        for kind in INPUTS:
            model = InputPrior(n=4, order=4, phases=8, input_kind=kind)
            self.assertTrue(model.branch(first)['platform'])
            self.assertTrue(model.branch(second)['platform'])
            np.testing.assert_allclose(model.logpdf(y, first), model.logpdf(y, second), atol=2e-12)
        singular = ActualPrior(n=4, model='g1').branch(second)
        self.assertEqual(singular['moments']['second'], 'infinite')

    def test_anchors_only_and_canonical_dense_equivalence(self):
        rng = np.random.default_rng(15)
        y = rng.normal(size=(4, 16))+1j*rng.normal(size=(4, 16))
        first, cost = anchored_features(y)
        changed = y.copy()
        changed[:, 1] += 100
        second, _ = anchored_features(changed)
        np.testing.assert_array_equal(first['phase'], second['phase'])
        self.assertEqual(cost['discarded_observation_coordinates'], 12)
        expected, _ = features.observed_features(y[:, [0, 4, 8, 12]])
        np.testing.assert_array_equal(first['phase'], expected['phase'])
        diagnostics = phase_diagnostics(y)
        self.assertLess(diagnostics['max_dense_reconstruction_error'], 2e-13)
        self.assertLess(diagnostics['max_rotation_representation_error'], 2e-13)
        self.assertGreater(diagnostics['dense_output_bytes'], diagnostics['canonical_output_bytes'])
        zero, anchor = features.canonical_phase(np.zeros((1, 4), complex))
        np.testing.assert_array_equal(zero, 0)
        self.assertEqual(anchor[0], 0)

    def test_frozen_model_roundtrip_and_calibration(self):
        rng = np.random.default_rng(99)
        x, score = rng.normal(size=(12, 3)), rng.normal(size=(12, 4))
        model = ScoreRegressor(.01).fit(x, score)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'model.npz'
            np.savez(path, **model.state())
            restored = restore_regressor(path)
            np.testing.assert_array_equal(restored.predict(x), model.predict(x))
        self.assertEqual(rejection_threshold(np.arange(100), .05), 95)
        interval = binomial_interval(0, 128)
        self.assertEqual(interval['count'], 128)
        self.assertAlmostEqual(interval['wilson95'][0], 0)
        self.assertGreater(interval['wilson95'][1], 0)

    def test_complete_cost_and_failure_measurements(self):
        meter = Costs()
        self.assertEqual(meter.measure('fixture', 'success', lambda: 3), 3)
        def fail():
            raise RuntimeError('fixture failure')
        with self.assertRaisesRegex(RuntimeError, 'fixture failure'):
            meter.measure('fixture', 'failure', fail)
        self.assertEqual(len(meter.rows), 2)
        self.assertEqual(meter.rows[-1]['status'], 'failed')
        self.assertGreaterEqual(meter.rows[-1]['wall_seconds'], 0)
        self.assertIsNone(amortization(10, .5, .1, False)['break_even_items'])
        self.assertIsNone(amortization(10, .1, .2, True)['break_even_items'])
        self.assertEqual(amortization(10, .5, .1, True)['break_even_items'], 25)

    def test_stage_inventory_counts_failed_and_missing_attempts(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for index, status in enumerate(('complete', 'invalid_partial', None)):
                stage = root/f'stage{index}'
                stage.mkdir()
                (stage/'registration.json').write_text(json.dumps(dict(stage=stage.name, wall_cap_seconds=10,
                                                                      config=dict(new_observations=index))))
                if status:
                    (stage/'attempt.json').write_text(json.dumps(dict(status=status, wall_seconds=2, cpu_seconds=1)))
            result = stage_cost_inventory(root)
            self.assertEqual(result['total_reserved_wall_seconds'], 30)
            self.assertEqual(result['total_reserved_observations'], 3)
            self.assertEqual(result['recorded_actual_wall_seconds'], 4)
            self.assertEqual(result['missing_attempts'], ['stage2'])

    def test_tiny_complete_stage_fixture_keeps_all_denominators(self):
        from experiments.afdm_efficient_information import transfer_study as study
        rng = np.random.default_rng(9)
        model = ScoreRegressor(.01).fit(rng.normal(size=(12, 90)), rng.normal(size=(12, 4)))
        config = dict(study.CONFIG, dimensions=[4], calibration_per_dimension=8,
                      test_per_hypothesis=2, new_observations=12, alpha=.2,
                      reference_observations_per_hypothesis=1, geometry_centers=[.04],
                      geometry_relative_deltas=[.25],
                      reference_rules=[dict(order=4, phases=8, rule='product', seed=1),
                                       dict(order=6, phases=12, rule='product', seed=2),
                                       dict(order=4, phases=8, rule='sobol', seed=3)])
        # Keep model path under ROOT because real reports demand project-relative provenance.
        with tempfile.TemporaryDirectory(dir=study.ARTIFACT.parent) as directory:
            root = Path(directory)
            model_path = root/'fixture_model.npz'
            np.savez(model_path, **model.state(), efficient_beta=np.zeros(3))
            output = root/'fixture'
            output.mkdir()
            with patch.object(study, 'CONFIG', config), patch.object(study, 'SCENARIOS', study.SCENARIOS[:1]):
                result = study.calculate(output, model_path)
            self.assertEqual(result['new_observations'], 12)
            self.assertEqual(result['calibration_observations'], 8)
            self.assertEqual(result['test_observations'], 4)
            self.assertEqual(result['retained_performance_groups'], 2)
            costs = json.loads((output/'costs.json').read_text())
            self.assertTrue(any(row['category'] == 'reference_setup' for row in costs))
            self.assertTrue(all(row['status'] == 'complete' for row in costs))


if __name__ == '__main__':
    unittest.main()
