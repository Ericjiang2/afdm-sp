"""Tiny known fixtures for the independent reader, never research populations."""
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np

from experiments.afdm_efficient_information import audit as a
from experiments.afdm_efficient_information.features import observed_features
from experiments.afdm_efficient_information.features_study import evaluate_layer
from experiments.afdm_efficient_information.inference import MomentBank, calibrate, evaluate_grid
from experiments.afdm_efficient_information.prior_likelihood import ActualPrior
from experiments.afdm_efficient_information.score import ScoreRegressor, linear_information
from experiments.afdm_higher_order_information.moments import FiniteControl


class IndependentReaderTests(unittest.TestCase):
    def test_closed_feature_products_reconstruct_every_column(self):
        rng = np.random.default_rng(371)
        for n in (4, 8):
            y = rng.normal(size=(7, n))+1j*rng.normal(size=(7, n))
            original, _ = observed_features(y)
            reconstructed = a.observed_polynomials(y)
            for key in original:
                np.testing.assert_allclose(reconstructed[key], original[key], rtol=1e-12, atol=1e-12)

    def test_augmented_fit_and_data_projection_are_independent(self):
        rng = np.random.default_rng(372)
        x, score = rng.normal(size=(80, 6)), rng.normal(size=(80, 4))
        x[:, 5] = x[:, 0]+x[:, 1]
        for ridge in (0., .01):
            original = ScoreRegressor(ridge).fit(x, score)
            rebuilt = a.fit_ridge(x, score, ridge)
            np.testing.assert_allclose(a.predict(x, rebuilt), original.predict(x), rtol=1e-9, atol=1e-10)
        first, second = linear_information(x, score), a.linear_moment(x, score)
        self.assertAlmostEqual(first['effective'], second['effective'], places=10)
        self.assertEqual(first['feature_rank'], second['rank'])

    def test_gaussian_spectral_teacher_against_cholesky(self):
        model = FiniteControl.uniform(4)
        y = np.array([[.1+.2j, .4-.3j, -.1+.7j, .4j], [.4+.1j, .1+.5j, .1+.3j, .5j]])
        for theta in ([0., .4, 1.3, .7], [.04, .1, .8, .4]):
            logpdf, score = model.evaluate(y, *theta)
            rebuilt = a.gaussian_teacher(y, model.time_words, model.weights, theta)
            np.testing.assert_allclose(rebuilt['logpdf'], logpdf, atol=1e-12)
            np.testing.assert_allclose(rebuilt['score'], score, atol=1e-10)

    def test_component_bessel_and_existing_rule_reconstruction(self):
        theta = np.array([.2, .35, 0., np.log(.8)])
        rule = dict(order=4, phases=8, rule='product', seed=7)
        model = ActualPrior(n=4, **rule)
        y = np.array([[.1+.2j, .4-.3j, -.1+.7j, .4j]])
        expected = model.evaluate(y, theta)
        saved = model._components(theta, .0001)
        replay = a.component_teacher(y, saved, .8)
        np.testing.assert_allclose(replay['logpdf'], expected['logpdf'], atol=1e-12)
        np.testing.assert_allclose(replay['score'], expected['score'], atol=1e-10)
        reconstructed = a._prior_components(dict(model='g0', pdp='marginal'), rule, theta, 4, .0001)
        independent = a.component_teacher(y, reconstructed, .8)
        np.testing.assert_allclose(independent['logpdf'], expected['logpdf'], atol=1e-11)
        np.testing.assert_allclose(independent['score'], expected['score'], atol=1e-8)

    def test_bank_quadratic_and_full_grid_statistics(self):
        rng = np.random.default_rng(373)
        candidates = np.array([[0., .1], [0., .2], [.1, .1], [.1, .2]])
        means = rng.normal(size=(4, 3))
        train = rng.normal(size=(40, 3))
        train_means = np.broadcast_to(means[0], train.shape)
        bank = MomentBank(train, train_means, means)
        rebuilt = a.reconstruct_bank(train, train_means, means)
        observation = rng.normal(size=(20, 3))
        original, _ = bank.objective(observation, 2)
        np.testing.assert_allclose(a.bank_objectives(observation, rebuilt, 2), original, atol=1e-10)
        calibration_objectives = [rng.uniform(0, 5, size=(30, 4)) for _ in candidates]
        calibration = calibrate(calibration_objectives, candidates, 0., .1)
        reconstructed = a.calibrate_grid(calibration_objectives, candidates, 0., .1)
        self.assertEqual(reconstructed['conditions'], calibration['conditions'])
        row, raw = evaluate_grid(original, candidates, 0, 0., calibration, interest='q')
        row.update(method='fixture', repeats=2)
        checks = a.Checks()
        a.audit_grid_case(original, candidates, 0, 0., calibration, 'q', row, raw, checks)
        self.assertTrue(checks.result()['passed'], checks.result())

    def test_hash_reader_rejects_corrupt_raw_and_missing_cost(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root/'source.py'
            source.write_text('fixture = 1\n')
            protected = root/'protected.json'
            protected.write_text(json.dumps({str(source):a.sha(source)}))
            stage = root/'fixture'
            stage.mkdir()
            snapshot = stage/'source_snapshot'
            snapshot.mkdir()
            (snapshot/'000_source.py').write_bytes(source.read_bytes())
            reg = dict(source_sha256={str(source):a.sha(source)}, git=dict(committed_task_source_sha256={}),
                       git_head='fixture', wall_cap_seconds=10, config=dict(new_observations=0))
            (stage/'registration.json').write_text(json.dumps(reg))
            raw = stage/'raw.json'
            raw.write_text('{"fixture": true}')
            attempt = dict(status='complete', wall_seconds=.1, cpu_seconds=.1, peak_rss_bytes=1,
                           reserved_wall_seconds=10, reserved_new_observations=0,
                           artifact_sha256={str(p):a.sha(p) for p in stage.rglob('*') if p.is_file()})
            (stage/'attempt.json').write_text(json.dumps(attempt))
            self.assertEqual(a.audit_hashes([stage], protected)['counts']['artifacts'], 3)
            raw.write_text('{"fixture": false}')
            with self.assertRaisesRegex(ValueError, 'artifact changed'):
                a.audit_hashes([stage], protected)
            raw.write_text('{"fixture": true}')
            del attempt['cpu_seconds']
            (stage/'attempt.json').write_text(json.dumps(attempt))
            with self.assertRaisesRegex(ValueError, 'invalid/missing attempt cost.*cpu_seconds'):
                a.audit_hashes([stage], protected)

    def test_preloaded_sources_only_exclude_exact_virtual_metadata(self):
        missing = a.ROOT/'not_present_audit_fixture.py'
        modules = {'torch.ops':SimpleNamespace(__file__='_ops.py'),
                   'torch.classes':SimpleNamespace(__file__='_classes.py'),
                   'ordinary':SimpleNamespace(__file__=str(missing)),
                   'audit':SimpleNamespace(__file__=a.__file__)}
        self.assertEqual(a.loaded_project_sources(modules), sorted([Path(a.__file__).resolve(), missing]))
        modules['torch.ops'] = SimpleNamespace(__file__=str(missing))
        self.assertIn(missing, a.loaded_project_sources(modules))

    def test_unknown_complete_schema_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            (folder/'attempt.json').write_text(json.dumps(dict(status='complete')))
            with self.assertRaisesRegex(ValueError, 'unrecognized completed scientific stage'):
                a.audit_stage(folder, a.Checks())

    def test_full_feature_adapter_recomputes_fit_bootstrap_and_uncertainty(self):
        rng = np.random.default_rng(374)
        features = rng.normal(size=(100, 6))
        scores = features@rng.normal(size=(6, 4))+.5*rng.normal(size=(100, 4))
        splits, ridges, bootstrap, seed = [48, 20, 32], [0., .01, .1], 8, [37, 4]
        model, row, raw = evaluate_layer(features[:48], features[48:68], features[68:],
            scores[:48], scores[48:68], scores[68:], ridges, bootstrap, seed)
        row.update(point=0, level='fixture')
        raw['features_test'] = features[68:]
        state = dict(**model.state(), efficient_beta=row['frozen_beta'])
        checks = a.Checks()
        a.audit_feature_layer(features, scores, state, raw, row, splits, ridges, bootstrap, seed, checks)
        self.assertTrue(checks.result()['passed'], checks.result())

    def test_admission_rejection_has_no_stage_or_cost(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            record = root/'rejection.json'
            record.write_text(json.dumps(dict(stage_requested='failed_admission',
                status='rejected_before_registration', new_observations=0,
                reserved_wall_seconds=0, retry_stage='retry')))
            with patch.object(a, 'ARTIFACT', root):
                self.assertEqual(a.audit_admission_rejections(record)[0]['reserved_wall_seconds'], 0)
                (root/'failed_admission').mkdir()
                with self.assertRaisesRegex(ValueError, 'unexpectedly created a stage'):
                    a.audit_admission_rejections(record)

    def test_checks_distinguish_boolean_mismatch_and_nonfinite(self):
        checks = a.Checks()
        checks.close(np.array([True, False]), np.array([True, False]), 'same')
        checks.equal(1, 2, 'mismatch')
        self.assertFalse(checks.result()['passed'])
        with self.assertRaisesRegex(ValueError, 'nonfinite'):
            checks.close([np.nan], [0.], 'bad')


if __name__ == '__main__':
    unittest.main()
