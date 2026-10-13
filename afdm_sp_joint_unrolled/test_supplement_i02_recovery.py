"""Small numerical/lineage contracts; these fixtures are not campaign evidence."""
import copy
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np

from . import supplement_i02_cache as cache
from .budgeted_support_diagnostics import array_hash
from .direction_cancel_receiver import CancellationTransform
from .e1_ldpc import build_code, encode, qpsk_map
from .supplement_i02_diagnostics import cancellation_diagnostics
from .supplement_i02_replay import replay_state, build_recovery_code
from .supplement_i02_entry import compare_arrays
from .supplement_profile import score_errors


def fixture(directory):
    code = build_code(n=24, d_v=3, d_c=6, cache_dir=directory)
    n = code['n'] // 2
    rng = np.random.default_rng(702)
    info = np.zeros(code['k'], np.uint8)
    coded = encode(code, info)
    data = qpsk_map(coded, scale=np.sqrt(.5))
    pilot = np.full(n, .5 + .5j)
    noise = rng.normal(size=n) + 1j * rng.normal(size=n)
    htrue = np.eye(n, dtype=complex)
    y = htrue @ (pilot + data) + np.sqrt(.05) * noise
    snapshot = dict(H=.8 * htrue, y=y, pilot=pilot, x_soft=data * .9,
        gains=np.array([.8 + 0j]), support=np.array([0]), sigma2=np.array(.2),
        sigma2_terminal=np.array(.1), sigma2_thermal=np.array(.05),
        constellation=np.array([.5+.5j, .5-.5j, -.5+.5j, -.5-.5j]),
        mu=data.copy(), var=np.ones(n), llr=np.ones(2*n), x_hard=data.copy(),
        decoded=coded.copy(), info_hat=info.copy(), info=info, coded=coded)
    truth = dict(H=htrue, info=info, coded=coded, data=data, noise=noise)
    inputs = {**truth, 'pilot': pilot, 'y': y}
    hashes = {k: array_hash(v) for k, v in inputs.items()}
    frame = SimpleNamespace(_truth=truth,
        observed={k: snapshot[k] for k in ('y', 'pilot', 'constellation')} |
                 {'sigma2': snapshot['sigma2_thermal']},
        metadata={'input_hashes': dict(hashes)})
    record = dict(identity=[0, 8, 'I0'], baseline_recipe='B0-p2-s0.5',
        truth_access_level='none', decoder_checkpoint_records=[],
        diagnostic_consumption_records=[], input_hashes=hashes,
        **score_errors(snapshot, truth))
    system = SimpleNamespace(N_total=n, c1=1/(2*n), c2=.001,
                             l_max_cap=1, k_max_cap=0)
    old = {}
    for mode in (None, 'scalar', 'diagonal', 'lowrank'):
        arm = 'I02-' + (mode or 'baseline')
        transformed = None if mode is None else CancellationTransform(system, mode)(
            **{k: snapshot[k] for k in ('y', 'pilot', 'H', 'x_soft', 'support')},
            sigma_base=float(snapshot['sigma2_terminal']))
        old[arm] = dict(arm_id=arm, block_id=0, SNR=8, mode=mode,
            truth_access_level='none', recipe_id='B0-p2-s0.5',
            cancellation=None if transformed is None else transformed['diagnostics'],
            **score_errors(snapshot, truth))
    return snapshot, record, old, frame, system, code


class LineageTests(unittest.TestCase):
    def test_real_code_initialization_creates_cache_under_fresh_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            hashes = dict(H='44cd76d564cbbe045ddb1b511deb1889ebf707b5f4a4553de18e131081b84178',
                          G='6066e7e1b33f251662ca741072098d73f14f64fd383333c944dd12bc85b71755')
            code = build_recovery_code(Path(tmp), hashes)
            self.assertEqual(code['n'], 2048)
            self.assertTrue(list((Path(tmp) / 'code-cache').glob('*.npz')))

    def test_real_entry_comparison_keeps_bitwise_and_numeric_results_distinct(self):
        row = compare_arrays(np.array([1.], np.float32), np.array([1.], np.float64))
        self.assertTrue(row['accepted'])
        self.assertFalse(row['bitwise_equal'])
        row = compare_arrays(np.array([0], np.uint8), np.array([1], np.uint8))
        self.assertFalse(row['accepted'])
        self.assertEqual(row['max_absolute_error'], 1.)

    def test_checks_inputs_without_estimator_or_decoder_calls(self):
        with tempfile.TemporaryDirectory() as tmp:
            args = fixture(tmp)
            with patch('afdm_sp_joint_unrolled.direction_cancel.working_factor',
                       side_effect=AssertionError('unexpected estimator')):
                proof = cache.validate_lineage(*args)
            self.assertTrue(proof['exogenous_hashes_match'])
            self.assertEqual(proof['matched_cancellation_modes'], 3)
            self.assertEqual(proof['calls'], dict(F=0, E=0, T=0))

    def test_rejects_wrong_exogenous_hash_and_wrong_transform_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            args = fixture(tmp)
            broken = copy.deepcopy(args)
            broken[1]['input_hashes']['noise'] = '0' * 64
            with self.assertRaisesRegex(ValueError, 'exogenous'):
                cache.validate_lineage(*broken)
            broken = copy.deepcopy(args)
            broken[2]['I02-lowrank']['cancellation']['A_sha256'] = '0' * 64
            with self.assertRaisesRegex(ValueError, 'A_sha256'):
                cache.validate_lineage(*broken)
            broken = copy.deepcopy(args)
            broken[2]['I02-baseline']['raw_bit_errors'] += 1
            with self.assertRaisesRegex(ValueError, 'baseline'):
                cache.validate_lineage(*broken)

    def test_file_tamper_and_duplicate_identity_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'record.json'
            path.write_text('{}')
            binding = cache.file_binding(path)
            path.write_text('{"changed":true}')
            with self.assertRaisesRegex(ValueError, 'hash'):
                cache.checked_path(binding)
        rows = [dict(block=b, snr=s) for b in range(192) for s in (7, 8, 9)]
        cache.validate_identities(rows)
        with self.assertRaisesRegex(ValueError, 'identity'):
            cache.validate_identities(rows + [rows[0]])
        with self.assertRaisesRegex(ValueError, 'identity'):
            cache.validate_identities(rows[:-1])


class CancellationDiagnosticsTests(unittest.TestCase):
    def test_whitening_and_cross_terms_match_independent_dense_calculation(self):
        with tempfile.TemporaryDirectory() as tmp:
            s, _, _, frame, system, _ = fixture(tmp)
            s = dict(s, Htrue=frame._truth['H'], data=frame._truth['data'],
                     noise=frame._truth['noise'])
            for mode in ('scalar', 'diagonal', 'lowrank'):
                transformed = CancellationTransform(system, mode)(
                    **{k: s[k] for k in ('y', 'pilot', 'H', 'x_soft', 'support')},
                    sigma_base=float(s['sigma2_terminal']))
                result, arrays = cancellation_diagnostics(s, transformed, mode)
                sigma = float(s['sigma2_terminal'])
                B = transformed['B']
                covariance = sigma*np.eye(len(s['y'])) + B @ B.conj().T
                if mode == 'lowrank':
                    eig, vectors = np.linalg.eigh(covariance)
                    W = (vectors * np.sqrt(sigma / eig)) @ vectors.conj().T
                    np.testing.assert_allclose(transformed['H'], W @ s['H'], atol=1e-12)
                    self.assertLess(result['working_covariance']['whitening_relative_error'], 1e-12)
                residual = transformed['z'] - transformed['H'] @ s['data']
                np.testing.assert_allclose(arrays['residual'], residual, atol=1e-12)
                ledger = result['residual']
                self.assertAlmostEqual(ledger['residual_mean_square'],
                    sum(ledger['energies'].values()) + sum(ledger['cross_terms'].values()))
                self.assertEqual(len(ledger['cross_terms']), 3)
                self.assertGreater(result['working_covariance']['minimum_eigenvalue'], 0)

    def test_cached_replay_reuses_baseline_and_charges_each_real_transform_and_terminal(self):
        with tempfile.TemporaryDirectory() as tmp:
            s, _, _, frame, system, code = fixture(tmp)
            s = dict(s, Htrue=frame._truth['H'], data=frame._truth['data'],
                     noise=frame._truth['noise'])
            calls = []
            cells = list(replay_state(s, system, code, device='cpu',
                                      before_call=lambda kind, arm: calls.append((kind, arm))))
            self.assertEqual(len(cells), 4)
            self.assertEqual([c[0] for c in calls], ['E', 'T'] * 3)
            self.assertTrue(cells[0]['reused_terminal'])
            for row in cells:
                self.assertEqual(row['diagnostics']['truth_access'], 'offline_only')
                self.assertTrue(np.isfinite(row['terminal']['llr']).all())

    def test_failed_terminal_keeps_completed_estimator_and_attempted_terminal(self):
        with tempfile.TemporaryDirectory() as tmp:
            s, _, _, frame, system, code = fixture(tmp)
            s = dict(s, Htrue=frame._truth['H'], data=frame._truth['data'],
                     noise=frame._truth['noise'])
            attempted, completed = [], []
            with patch('afdm_sp_joint_unrolled.supplement_i02_replay.terminal_decode',
                       side_effect=RuntimeError('fixture terminal failure')):
                with self.assertRaisesRegex(RuntimeError, 'fixture terminal'):
                    list(replay_state(s, system, code, device='cpu',
                        before_call=lambda kind, arm: attempted.append(kind),
                        after_call=lambda kind, arm: completed.append(kind)))
            self.assertEqual(attempted, ['E', 'T'])
            self.assertEqual(completed, ['E'])


if __name__ == '__main__':
    unittest.main()
