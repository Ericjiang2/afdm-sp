"""Focused offline ranking and fallback contracts."""

import pathlib
import hashlib
import json
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

import numpy as np


sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from analyze_reopening import (_check_seal_binding, _check_trace,
                               add_geometry_proximity,
                               check_checkpoint_bits, check_observed_branch_inputs,
                               cost_summary, global_trace_tables,
                               latest_available, paired_2x2, rank_score_grid,
                               recount, truth_rank_rows, observation_hash)


class ReopeningAnalysisTests(unittest.TestCase):
    def test_complete_grid_ties_and_masked_replacement(self):
        delays = np.array([1, 1, 2, 2])
        nus = np.array([-.25, .25, -.25, .25])
        scores = np.array([[1., 1., 1., 3.],
                           [1., 1., 2., 2.]])
        valid = np.array([[1, 0, 1, 1],
                          [1, 1, 1, 1]], bool)
        ranks = rank_score_grid(scores, valid, delays, nus)
        self.assertEqual(ranks[0, 0], 1)
        self.assertEqual(ranks[0, 2], 2)
        self.assertEqual(ranks[1, 0], 3)
        self.assertEqual(ranks[1, 1], 4)
        self.assertEqual(ranks[0, 1], 0)
        rows = truth_rank_rows(scores, valid, delays, nus,
                               [1, 1, 2, 3], [0., .25, .25, 0.],
                               [1., 2., 3., 4.], observation_id='frame', global_step=1)
        self.assertEqual([row['true_path_index'] for row in rows], [0, 1, 2, 3])
        self.assertEqual(rows[0]['nearest_grid_doppler'], -.25)  # lower-nu tie
        self.assertEqual(rows[0]['best_global_rank'], 1)
        self.assertEqual(rows[1]['rank_by_replacement_slot'], [None, 4])
        self.assertEqual(rows[1]['true_nominal_gain_energy'], 4.)
        self.assertIsNone(rows[3]['best_global_rank'])
        self.assertTrue(rows[3]['missing_or_all_slots_masked'])

    def test_rank_can_be_exactly_outside_stored_top20(self):
        delays = np.arange(25)
        nus = np.zeros(25)
        score = np.arange(25, dtype=float)[None, :]
        row = truth_rank_rows(score, np.ones_like(score, bool), delays, nus,
                              [24], [0.], [1.], observation_id='x', global_step=0)[0]
        self.assertEqual(row['best_global_rank'], 25)
        self.assertFalse(row['in_top20'])
        self.assertTrue(row['outside_top20'])

    def test_topk_score_tamper_is_rejected_without_rank_change(self):
        trace = dict(scores=np.array([[1e8, 1e8+10]]),
                     valid=np.ones((1, 2), bool),
                     candidate_delays=np.array([1, 2], dtype=int),
                     candidate_dopplers=np.array([0., 0.]),
                     top_k=[dict(rank=1, slot=0,
                                 replacement=dict(delay=1, doppler=0.),
                                 frozen_score=1e8+1),
                            dict(rank=2, slot=0,
                                 replacement=dict(delay=2, doppler=0.),
                                 frozen_score=1e8+10)])
        with self.assertRaisesRegex(ValueError, 'inconsistent'):
            _check_trace(trace)
        trace['top_k'][0]['frozen_score'] = 1e8
        _check_trace(trace)

    def test_global_trace_csv_rows_keep_full_geometry_and_counts(self):
        entering = [dict(delay=1, doppler=0.)]
        trace = dict(step=0, entering_paths=entering,
                     entering_gains=np.array([1+2j]), entering_objective=5.,
                     scores=np.array([[2., 3.]]), valid=np.ones((1, 2), bool),
                     candidate_delays=np.array([1, 2], dtype=int),
                     candidate_dopplers=np.array([0., 0.]),
                     top_k=[dict(rank=1, slot=0, replacement=dict(delay=1, doppler=0.),
                                 paths=[dict(delay=1, doppler=0.)], frozen_score=2.),
                            dict(rank=2, slot=0, replacement=dict(delay=2, doppler=0.),
                                 paths=[dict(delay=2, doppler=0.)], frozen_score=3.)],
                     selected=None,
                     accepted=dict(new=dict(delay=2, doppler=0.), direct_score=4.),
                     candidate_columns=2, slot_tests=2, valid_slot_tests=2,
                     duplicate_rejections=0, elapsed_seconds=.2)
        step, top = global_trace_tables('frame', 'trigger', trace)
        self.assertEqual(step['entering_gains_real'], [1.])
        self.assertEqual(step['entering_gains_imag'], [2.])
        self.assertEqual(step['after_global_objective'], 4.)
        self.assertEqual(step['slot_tests'], 2)
        self.assertEqual([r['rank'] for r in top], [1, 2])
        self.assertEqual(top[1]['full_candidate_geometry'], [dict(delay=2, doppler=0.)])

    def test_truth_rank_distinguishes_incumbent_and_accepted_atom(self):
        rows = [dict(true_delay=2, true_doppler=.3),
                dict(true_delay=2, true_doppler=.3),
                dict(true_delay=7, true_doppler=-.4)]
        add_geometry_proximity(rows,
            [dict(delay=2, doppler=.25), dict(delay=5, doppler=0.)],
            dict(new=dict(delay=7, doppler=-.5)))
        self.assertEqual([r['entering_same_delay_path_count'] for r in rows], [1, 1, 0])
        self.assertTrue(rows[0]['entering_same_delay_within_half_grid_step'])
        self.assertIsNone(rows[2]['entering_same_delay_min_doppler_distance'])
        self.assertIsNone(rows[0]['accepted_new_same_delay_doppler_distance'])
        self.assertAlmostEqual(rows[2]['accepted_new_same_delay_doppler_distance'], .1)

    def test_deadline_keeps_earlier_checkpoint(self):
        decisions = [dict(name='round1', ready_seconds=.35),
                     dict(name='round2', ready_seconds=.72),
                     dict(name='branch', ready_seconds=1.25)]
        self.assertEqual(latest_available(decisions, .5)['name'], 'round1')
        self.assertEqual(latest_available(decisions, 1.)['name'], 'round2')
        self.assertEqual(latest_available(decisions, 2.)['name'], 'branch')
        self.assertIsNone(latest_available(decisions, .2))

    def test_paired_outcome_and_cost(self):
        rows = [dict(LOCAL20_correct=False, GLOBAL20_correct=False),
                dict(LOCAL20_correct=False, GLOBAL20_correct=True),
                dict(LOCAL20_correct=True, GLOBAL20_correct=False),
                dict(LOCAL20_correct=True, GLOBAL20_correct=True)]
        result = paired_2x2(rows)
        self.assertEqual(result['total'], 4)
        self.assertEqual(result['net_global_extra_correct'], 0)
        self.assertEqual(result['global_only_correct'], 1)
        timing = cost_summary([.1, .2, .3])
        self.assertAlmostEqual(timing['mean_seconds'], .2)
        self.assertEqual(timing['max_seconds'], .3)

    def test_seal_binding_requires_exact_committed_bytes(self):
        commit = 'a' * 40
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            seal, binding = root/'observed_seal.json', root/'binding.json'
            content = b'{"status":"pass"}\n'
            seal.write_bytes(content)
            payload = dict(git_commit=commit,
                           committed_path='experiments/reopen/observed_seal.json',
                           observed_seal_sha256=hashlib.sha256(content).hexdigest(),
                           committed_blob_sha1=hashlib.sha1(
                               b'blob '+str(len(content)).encode()+b'\0'+content).hexdigest())
            binding.write_text(json.dumps(payload))
            self.assertEqual(_check_seal_binding(commit, binding, seal)['committed_blob_sha1'],
                             payload['committed_blob_sha1'])
            seal.write_bytes(content + b' ')
            with self.assertRaisesRegex(ValueError, 'binding differs'):
                _check_seal_binding(commit, binding, seal)
            seal.write_bytes(content)
            with self.assertRaisesRegex(ValueError, 'explicit full Git SHA'):
                _check_seal_binding('a'*39, binding, seal)

    def test_recount_exposes_valid_but_wrong(self):
        H = np.array([[1, 1, 0, 0], [0, 0, 1, 1]], dtype=np.uint8)
        coded = np.array([0, 0, 0, 0], dtype=np.uint8)
        info = np.array([0, 0], dtype=np.uint8)
        wrong = np.array([1, 1, 0, 0], dtype=np.uint8)
        count = recount(wrong, coded, info, H, np.array([0, 2]))
        self.assertEqual(count['syndrome_weight'], 0)
        self.assertEqual(count['info_errors'], 1)
        self.assertEqual(count['coded_errors'], 2)
        self.assertTrue(count['valid_but_wrong'])

    def test_checkpoint_replay_rejects_same_syndrome_different_bits(self):
        first = np.array([0, 0, 0, 0], dtype=np.uint8)
        second = np.array([1, 1, 0, 0], dtype=np.uint8)
        third = np.array([1, 1, 1, 1], dtype=np.uint8)
        raw = dict(decoder=dict(decoded=third.copy()),
                   baseline_arrays=dict(r0_decoded=first.copy(), r1_decoded=second.copy()))
        check_checkpoint_bits([first, second], [first.copy(), second.copy(), third.copy()], raw)
        altered = second.copy()
        altered[:] = [0, 0, 1, 1]  # parity/syndrome can still match
        with self.assertRaisesRegex(ValueError, 'bits differ'):
            check_checkpoint_bits([first, second], [first, altered, third], raw)

    def test_branch_inputs_came_from_observed_app_and_check(self):
        app = np.array([30., -3.])
        prior = np.array([-25., 2.])
        clipped_app, clipped_prior = np.clip(app, -20, 20), np.clip(prior, -20, 20)
        raw = dict(baseline_arrays=dict(r1_app=app, r1_check=prior,
                                        r1_mu=np.array([1.]), r1_variance=np.array([.2])),
                   app_input=clipped_app.copy(), check_prior=clipped_prior.copy(),
                   ce_mu=clipped_app/2, ce_variance=np.ones(2),
                   native_round2_detector_mu=np.array([1.]),
                   native_round2_detector_variance=np.array([.2]))
        fake_messages = types.SimpleNamespace(moments=lambda x, power: (x/2, np.ones(2), None))
        with patch.dict(sys.modules, {'messages': fake_messages}):
            check_observed_branch_inputs(raw, .5)
            raw['check_prior'][0] = 0.
            with self.assertRaisesRegex(ValueError, 'APP/check'):
                check_observed_branch_inputs(raw, .5)

    def test_original_observation_hash_includes_dtype_and_shape(self):
        observed = dict(y=np.array([1+2j, 3+4j], np.complex128),
                        pilot=np.array([0., 1.], np.float64), sigma2=np.array(.5))
        parts = []
        for name in ('y', 'pilot', 'sigma2'):
            value = observed[name]
            source_contract = (str(value.dtype).encode() +
                               json.dumps(value.shape).encode() +
                               np.ascontiguousarray(value).tobytes())
            parts.append(hashlib.sha256(source_contract).hexdigest())
        expected = hashlib.sha256('|'.join(parts).encode()).hexdigest()
        self.assertEqual(observation_hash(observed), expected)
        changed = dict(observed, pilot=observed['pilot'].astype(np.float32))
        self.assertNotEqual(observation_hash(changed), expected)


if __name__ == '__main__':
    unittest.main()
