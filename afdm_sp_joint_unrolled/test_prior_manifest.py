"""Fixed prior identities retain full truth and never resample failed frames."""
import json
import copy
import fcntl
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
import torch

from afdm_sp_joint_unrolled.budgeted_support_diagnostics import dev_rng
from afdm_sp_joint_unrolled.decision_harvest import (
    harvest_frame, run_harvest, validate_prior_manifest, validate_complete_prior,
)
from afdm_sp_joint_unrolled.loop9_cache_features import _merged_dictionary_coefficients


def manifest(n):
    return dict(schema='afdm-prior-frames-v1', root_seed=20260905, frames=[
        dict(split=2, replicate=40, frame_index=i, stream=9,
             seed=int(dev_rng(40, i, 9, split=2).integers(0, 2**31))) for i in range(n)])


class PriorManifestTests(unittest.TestCase):
    def test_existing_lock_rejects_duplicate_before_computation(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)/'out'
            out.mkdir()
            with (out/'.harvest.lock').open('a') as lock:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                with self.assertRaisesRegex(RuntimeError, 'already running'):
                    run_harvest(out, 8, 2, 64, 2, 8, 10, 4, 2, 64, 0,
                                nomination_cap=40, frame_manifest=Path(tmp)/'not_read.json')

    def test_exact_manifest_identity_and_seed(self):
        m = manifest(3)
        self.assertEqual(validate_prior_manifest(m, 3), m['frames'])
        for key, value in [('seed', 0), ('frame_index', 1), ('split', 3)]:
            changed = manifest(3)
            changed['frames'][0][key] = value
            with self.assertRaises(ValueError):
                validate_prior_manifest(changed, 3)

    def test_complex_merge_keeps_cancelled_entry_in_full_labels(self):
        params = dict(l_exp=[0, 0, 1], k_exp=[0, 0, 0], chan_coef_exp=[1+2j, -1-2j, .4+.3j])
        columns, gains = _merged_dictionary_coefficients(params, 1, 3)
        np.testing.assert_array_equal(columns, [1, 4])
        np.testing.assert_array_equal(gains, [0, .4+.3j])

    def test_frame_full_truth_is_not_nomination_or_candidate_limited(self):
        params = dict(l_exp=[0,0,1], k_exp=[0,0,0], chan_coef_exp=[1+2j,-1-2j,.4+.3j],
                      l_i=[0,1], k_real=[0.,0.], g_i=[1.,.4], k_leak=2, P_actual=3, taps=2)
        system = SimpleNamespace(_P_actual=3, P_paths=2, k_max_cap=1, l_max_cap=1,
                                 _zc_seq=np.ones(8, dtype=complex),
                                 generate_channel_matrix=lambda: (np.eye(8), None, params),
                                 gen_h_daft=lambda g,l,k: np.eye(8, dtype=complex)*sum(g))
        Phi = np.eye(8, dtype=complex)[:, :6]
        result = harvest_frame(system, 8, .1, Phi, np.ones(6), 3, 2, 123, .5,
                               nomination_cap=1, complete_truth=True)
        truth = result['frame_record']['truth']
        np.testing.assert_array_equal(truth['columns'], [1,4])
        np.testing.assert_array_equal(truth['active_columns'], [4])
        self.assertEqual(truth['zero_threshold'], 0.)
        self.assertEqual(len(result['frame_record']['input_hashes']), 5)
        self.assertEqual(result['frame_record']['receiver_nomination'], 1)

    def test_failed_fixed_frame_is_recorded_without_replacement(self):
        system = SimpleNamespace(rho=.5, _zc_seq=np.ones(8), k_max_cap=1, l_max_cap=20,
                                 c1=.02, c2=.001, v_mean=2, P_paths=8, fs=8000)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'manifest.json'
            path.write_text(json.dumps(manifest(2)))
            out = Path(tmp)/'output'
            with patch('afdm_sp_joint_unrolled.decision_harvest._make_config_a', return_value=system), \
                 patch('afdm_sp_joint_unrolled.decision_harvest.harvest_frame', return_value=None) as harvest:
                with self.assertRaisesRegex(ValueError, 'fixed prior frame'):
                    run_harvest(out, 8, 2, 8, 2, 8, 10, 4, 2, 64, 0,
                                nomination_cap=40, frame_manifest=path)
            self.assertEqual(harvest.call_count, 1)
            failure = json.loads((out/'failure.json').read_text())
            self.assertEqual(failure['frame']['frame_index'], 0)
            self.assertFalse((out/'cache_snr8.pt').exists())

    def test_complete_cache_validates_and_detects_corruption(self):
        N = 64
        params = dict(l_exp=[0,0,1], k_exp=[0,0,0], chan_coef_exp=[1+2j,-1-2j,.4+.3j],
                      l_i=[0,1,0,0,0,0,0,0], k_real=[0.]*8, g_i=[1.,.4,0,0,0,0,0,0],
                      k_leak=2, P_actual=3, taps=8, fro_scale=1.)
        system = SimpleNamespace(rho=.5, _zc_seq=np.ones(N, dtype=complex),
                                 k_max_cap=1, l_max_cap=20, c1=.02, c2=.001,
                                 v_mean=2, P_paths=8, fs=8000, _P_actual=3,
                                 generate_channel_matrix=lambda: (np.eye(N), None, params),
                                 gen_h_daft=lambda g,l,k: np.eye(N, dtype=complex)*sum(g))
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'manifest.json'
            path.write_text(json.dumps(manifest(2)))
            out = Path(tmp)/'output'
            with patch('afdm_sp_joint_unrolled.decision_harvest._make_config_a', return_value=system):
                run_harvest(out, 8, 2, N, 2, 8, 10, 4, 2, 64, 0,
                            nomination_cap=40, frame_manifest=path)
            cache = torch.load(out/'cache_snr8.pt', weights_only=False)
            validate_complete_prior(cache, 2)
            self.assertEqual(len(list(out.glob('frame-*.pt'))), 2)
            bad = copy.deepcopy(cache)
            bad['frame_records'][0]['truth']['coefficients'][0] = 1.
            with self.assertRaisesRegex(ValueError, 'merge'):
                validate_complete_prior(bad, 2)
            bad = copy.deepcopy(cache)
            bad['y'][0,0] = 1-bad['y'][0,0]
            with self.assertRaisesRegex(ValueError, 'labels'):
                validate_complete_prior(bad, 2)
            bad = copy.deepcopy(cache)
            bad['config']['p_paths'] = 99
            with self.assertRaisesRegex(ValueError, 'hash'):
                validate_complete_prior(bad, 2)
            # Simulate interrupted final aggregation: committed frame files survive.
            (out/'cache_snr8.pt').unlink()
            with patch('afdm_sp_joint_unrolled.decision_harvest._make_config_a', return_value=system), \
                 patch('afdm_sp_joint_unrolled.decision_harvest.harvest_frame', side_effect=AssertionError('completed frame recomputed')):
                run_harvest(out, 8, 2, N, 2, 8, 10, 4, 2, 64, 0,
                            nomination_cap=40, frame_manifest=path, resume=True)
            validate_complete_prior(torch.load(out/'cache_snr8.pt', weights_only=False), 2)
            (out/'cache_snr8.pt').unlink()
            with patch('afdm_sp_joint_unrolled.decision_harvest._make_config_a', return_value=system):
                with self.assertRaisesRegex(ValueError, 'provenance mismatch'):
                    run_harvest(out, 8, 2, N, 2, 8, 10, 4, 3, 64, 0,
                                nomination_cap=40, frame_manifest=path, resume=True)
            first_hash = (out/'frame-0000.pt').read_bytes()
            (out/'frame-0001.pt').unlink()
            with patch('afdm_sp_joint_unrolled.decision_harvest._make_config_a', return_value=system), \
                 patch('afdm_sp_joint_unrolled.decision_harvest.harvest_frame', wraps=harvest_frame) as call:
                run_harvest(out, 8, 2, N, 2, 8, 10, 4, 2, 64, 0,
                            nomination_cap=40, frame_manifest=path, resume=True)
            self.assertEqual(call.call_count, 1)
            self.assertEqual(call.call_args.args[7], manifest(2)['frames'][1]['seed'])
            self.assertEqual((out/'frame-0000.pt').read_bytes(), first_hash)
            with self.assertRaises(FileExistsError):
                run_harvest(out, 8, 2, N, 2, 8, 10, 4, 2, 64, 0,
                            nomination_cap=40, frame_manifest=path)


if __name__ == '__main__':
    unittest.main()
