"""Algebra and evidence-boundary checks for the offline C runner."""

import pathlib
import sys
import json
import tempfile
import unittest
from unittest.mock import patch

import numpy as np


HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'experiments/sp_afdm_frozen_20260920/src'))
sys.path.insert(0, str(ROOT / 'experiments/sp_afdm_native_joint_20260921/src'))
sys.path.insert(0, str(ROOT / 'experiments/sp_afdm_frozen_20260920/upstream/spafdm_receiver_handoff'))
sys.path.insert(0, str(HERE))

from physical import Channel, daft, projected_variance
import metrics
import witness_analysis as witness


class WitnessTests(unittest.TestCase):
    def setUp(self):
        self.n = 9
        self.c1, self.c2 = .13 / self.n, .07 / self.n
        self.l = np.array([1, 1, 3])
        self.nu = np.array([-.7, .5, 1.1])
        self.h = np.array([.5+.1j, -.3+.2j, .2-.1j])
        self.c = Channel(self.n, self.c1, self.c2, self.l, self.nu, self.h)
        rng = np.random.default_rng(123)
        self.pilot = rng.normal(size=self.n) + 1j*rng.normal(size=self.n)

    def test_observed_pilot_gain_uses_declared_soft_ridge(self):
        sigma2, pd = .2, .5
        Y = daft(self.c.apply(self.pilot), self.c1, self.c2, True)
        h, gamma = witness._pilot_gain(Y, self.pilot, self.l, self.nu,
                                       self.c1, self.c2, sigma2, pd)
        B = metrics.response_matrix(self.pilot, self.l, self.nu, self.c1, self.c2)
        np.testing.assert_allclose(gamma, projected_variance(np.full(self.n, pd),
                                                                self.l, self.nu, self.c1))
        np.testing.assert_allclose((B.conj().T @ B + gamma + sigma2*np.eye(len(self.l))) @ h,
                                   B.conj().T @ Y, atol=1e-11)
        self.assertGreater(np.linalg.norm(h-self.h), 0)

    def test_operator_projection_uses_exact_sparse_code_covariance(self):
        G = np.eye(2*self.n, dtype=np.uint8)
        G[self.n + 1] = G[0]
        moments = metrics.exact_code_moments(G, .5)
        result = witness._operator_projection(self.c, self.c, self.pilot, moments)
        self.assertEqual(result['operator_projection_rank'], 3)
        self.assertLess(result['projected_mismatch_fraction'], 1e-12)
        self.assertLess(result['actual_mismatch_fraction'], 1e-12)
        self.assertEqual(result['missing_distinct_delay_energy_fraction'], 0)
        shifted = Channel(self.n, self.c1, self.c2, [0], [0.], [1.])
        result = witness._operator_projection(shifted, self.c, self.pilot, moments)
        self.assertGreater(result['missing_distinct_delay_energy_fraction'], 0)

    def test_initial_containment_keeps_multiplicity(self):
        acquisition = {'delays': np.array([1, 3, 5]),
                       'dopplers': np.array([-.6, 1.9, 0.])}
        result = witness._initial_containment(acquisition, [1, 1, 3, 6],
                                               [-.7, 1.0, 1.1, 0.])
        self.assertEqual(result['true_paths_with_acquired_delay'], 3)
        self.assertEqual(result['true_paths_in_acquisition_nominal_window'], 1)
        refit = dict(selected_delays=np.array([1, 3]),
                     bounds=np.array([[-1., 1.2], [.8, 1.4]]))
        actual = witness._first_refit_containment(refit, [1, 1, 3, 6],
                                                   [-.7, 1.0, 1.1, 0.])
        self.assertEqual(actual['first_refit_true_paths_with_selected_delay_slots'], 2)
        self.assertEqual(actual['first_refit_true_paths_in_local_window'], 2)
        self.assertEqual(actual['first_refit_true_path_window_coverage_fraction'], .5)

    def test_selection_rejects_ledger_drift(self):
        records = [{'snr_centi_db':650, 'frame': i, 'arm':'TF_J20_R2',
                    'info_errors': 1 if i < 32 else 0} for i in range(64)]
        selected = {'observations':[{'observation_id':f's650_f{i:04d}',
                   'frame':i, 'baseline_record':r} for i, r in enumerate(records)]}
        with patch.object(witness.audit_io, 'selected_records', return_value=records):
            self.assertEqual(len(witness._first32_selection(selected, records)), 64)
            selected['observations'][0]['baseline_record'] = dict(records[0], info_errors=0)
            with self.assertRaises(ValueError):
                witness._first32_selection(selected, records)

    def test_broad_search_charges_every_candidate_fit(self):
        Y = daft(self.c.apply(self.pilot), self.c1, self.c2, True)
        working = Channel(self.n, self.c1, self.c2, self.l, self.nu, self.h*.3)
        candidates = {'baseline': np.zeros(self.n, complex),
                      'truth': np.zeros(self.n, complex)}
        runs, conditional, costs = witness._broad_scores(Y, self.pilot, candidates,
                                                          working, .2, .6)
        self.assertEqual(len(costs), 4)
        self.assertEqual({(x['candidate'], x['objective']) for x in costs},
                         {('baseline', 'profile'), ('baseline', 'marginal'),
                          ('truth', 'profile'), ('truth', 'marginal')})
        for cost in costs:
            self.assertEqual(cost['candidate_evaluations'],
                             runs[cost['candidate']][cost['objective']]['evaluations'])
            self.assertGreater(cost['seconds'], 0)
        self.assertIn('conditional_score', conditional['baseline'])
        fitted_nu = runs['baseline']['profile']['dopplers']
        B = metrics.response_matrix(self.pilot, self.l, fitted_nu, self.c1, self.c2)
        expected = np.linalg.norm(Y - B @ working.gains)**2 / .2
        self.assertAlmostEqual(conditional['baseline']['conditional_score'], expected)
        self.assertGreater(abs(expected-runs['baseline']['profile']['score']), 1e-4)

    def test_hash_bound_heavy_exemplar_mapping(self):
        pd = .5
        coded = np.zeros(2*self.n, np.uint8)
        coded[1] = 1
        compact = dict(coded=dict(packed=np.packbits(coded), length=len(coded)),
                       info=dict(packed=np.packbits(coded), length=len(coded)), unit_scale=1.)
        heavy = dict(coded=coded.copy(), info=coded.copy(),
                     unit_scale=1., data=witness._map(coded, pd))
        record = dict(snr_centi_db=650, frame=0, frame_sha256='a'*64)
        with tempfile.TemporaryDirectory() as folder:
            run = pathlib.Path(folder) / 'run'
            run.mkdir()
            inventory = dict(status='pass', entries=[
                dict(path='run/heavy/s650_f0000_truth.npz', sha256='b'*64),
                dict(path='run/frames/s650_f0000_truth.npz', sha256='a'*64)])
            (run.parent / 'remote_inventory.json').write_text(json.dumps(inventory))
            with patch.object(witness.audit_io, 'load_bound', side_effect=[compact, heavy]) as loader:
                result = witness._heavy_mapping_check(run, [record], object(), pd)
            self.assertTrue(result['mapped_data_equal'])
            self.assertEqual(loader.call_args_list[1].args[2], 'b'*64)
            heavy['data'] = heavy['data'] + 1
            with patch.object(witness.audit_io, 'load_bound', side_effect=[compact, heavy]):
                with self.assertRaises(ValueError):
                    witness._heavy_mapping_check(run, [record], object(), pd)

    def test_observable_features_need_no_truth(self):
        n = self.n
        zeros = np.zeros(2*n, np.uint8)
        changed = zeros.copy()
        changed[0] = 1
        snapshot = dict(delays=self.l, dopplers=self.nu, gains=self.h,
            mu=np.zeros(n, complex), app=np.r_[np.zeros(3), np.full(2*n-3, 4.)],
            inference_trace=[dict(data_precision_floor=False, gain_precision_floor=True)])
        pack = lambda bits: dict(packed=np.packbits(bits), length=len(bits))
        checkpoints = [dict(snapshot=snapshot, decoded=pack(changed)),
                       dict(snapshot=snapshot, decoded=pack(zeros))]
        replay = dict(trace=dict(refits=[{}, dict(bounds=np.column_stack((self.nu-.75, self.nu+.75)))]))
        obs = dict(y=self.c.apply(self.pilot), pilot=self.pilot, sigma2=.2)
        features = witness._observable(obs, checkpoints, replay, np.eye(2*n, dtype=np.uint8),
                                       self.c1, self.c2)
        self.assertEqual(features['syndrome_weight'], 0)
        self.assertEqual(features['round_disagreement'], 1)
        self.assertAlmostEqual(features['app_abs_below2_fraction'], 3/(2*n))
        self.assertLess(features['observed_residual_over_noise'], 1e-20)
        self.assertEqual(features['fitted_path_count'], 3)

    def test_bound_b_ledger_and_recoverability(self):
        selected = [dict(observation_id=f's650_f{i:04d}', frame=i,
                         baseline_error=i<32) for i in range(64)]
        records = []
        for item in selected:
            for arm in ('baseline_replay', *witness.ARMS):
                error = int(item['baseline_error'] and item['frame'] >= 8)
                if arm == 'baseline_replay':
                    error = int(item['baseline_error'])
                records.append(dict(observation_id=item['observation_id'], arm=arm,
                    status='ok', info_errors=error, baseline_error=item['baseline_error'],
                    rescue=bool(item['baseline_error'] and error == 0),
                    harm=bool(not item['baseline_error'] and error > 0)))
        with tempfile.TemporaryDirectory() as folder:
            ledger = pathlib.Path(folder) / 'ledger.jsonl'
            ledger.write_text(''.join(json.dumps(record)+'\n' for record in records))
            digest = witness.audit_io.sha256(ledger)
            receipt = dict(ledger_sha256=digest, files={'ledger.jsonl':digest})
            indexed = witness._bound_b_ledger(pathlib.Path(folder), receipt, selected)
            feature = dict(syndrome_weight=0, app_abs_mean=4., app_abs_below2_fraction=.1,
                observed_residual_over_noise=1.5, round_disagreement=1,
                refit_boundary_hit=False, refit_min_boundary_distance=.2,
                fitted_path_count=8)
            observables = {x['observation_id']:dict(feature) for x in selected}
            rows = witness._recoverability_rows(selected, observables, indexed)
            summary = witness._recoverability_summary(rows)
            self.assertEqual(len(rows), 64)
            self.assertEqual(summary['by_arm']['J40R2']['rescued_failures']['count'], 8)
            self.assertEqual(summary['by_arm']['J40R2']['selected_success_controls']['count'], 32)
            self.assertEqual(rows[0]['j40r2_rescue'], True)
            self.assertEqual(rows[-1]['j40r2_harm'], False)
            ledger.write_text(ledger.read_text() + '{}\n')
            with self.assertRaises(ValueError):
                witness._bound_b_ledger(pathlib.Path(folder), receipt, selected)


if __name__ == '__main__':
    unittest.main()
