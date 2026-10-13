"""A-01 unit fixtures. Not 256-block attribution evidence."""
from __future__ import annotations

import json
import tempfile
import time
import unittest
from .test_supplement_development_analysis import MANIFEST
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np

from afdm_sp_joint_unrolled import supplement_a01 as a01
from afdm_sp_joint_unrolled import supplement_h01 as h01
from afdm_sp_joint_unrolled.e1_ldpc import build_code
from afdm_sp_joint_unrolled.test_supplement_h01 import D1_PATH, sha, toy_frame, toy_result


class A01ContractTests(unittest.TestCase):
    def test_bridge_reuses_original_bounded_physical_search_not_self_fitted_ls(self):
        from .direction_physical import fit_physical_observed
        from .direction_physical_receiver import PhysicalChannelRefit
        class PublicSystem:
            N_total, c1, c2 = 1024, 5 / 2048, 1e-7
            l_max_cap, k_max_cap, k_guard, k_leak = 102, 2, 0, 2
            frac_prune_rel_thres, gen_h_daft_convention = .01, 'python'
            @property
            def P_paths(self):
                raise AssertionError('legal bridge read true physical path count')
        system = PublicSystem()
        A = np.array([[1, .2j, .4], [.2, 1, 1j], [1j, .3, 2]], complex)
        y = np.array([1+1j, 2, -.5j])
        ids, gains = np.array([1, 2, 3]), np.ones(3, complex)
        snapshot = dict(support=ids, gains=gains, pilot=np.ones(3, complex),
                        x_soft=np.zeros(3, complex), y=y, sigma2_terminal=.04)
        geometry = PhysicalChannelRefit(system, 'm-param-budget').geometry
        expected = {constraint: fit_physical_observed(geometry, y, A, ids, gains, .04, arm)
                    for constraint, arm in (('hard', 'm-param-budget'), ('soft', 'm-soft'))}
        with patch.object(a01, '_sensing', return_value=A):
            legal = a01.prepare_legal_bridge(snapshot, system)
        for constraint in ('soft', 'hard'):
            actual, _ = a01._constrained(A, y, legal['basis'], constraint)
            np.testing.assert_allclose(actual, expected[constraint]['coefficients'], atol=1e-12)
        self.assertGreater(np.linalg.norm(expected['soft']['coefficients'] -
                                          expected['hard']['coefficients']), .01)
        self.assertEqual(legal['diagnostics']['query_count'], expected['hard']['diagnostics']['query_count'])
        self.assertLessEqual(legal['diagnostics']['query_count'], 73)

    def test_sixteen_arms_and_s0_only_legal_flow(self):
        self.assertEqual(len(a01.ARMS), 16)
        self.assertEqual(len(a01.CORE_ARMS), 12)
        self.assertEqual(a01.TOTAL_E, 16 * a01.TOTAL_F)
        self.assertEqual(a01.TOTAL_T, 32 * a01.TOTAL_F)
        legal = [arm for arm in a01.ARMS if a01._arm_spec(arm)['legal_flow_comparable']]
        self.assertEqual(legal, ['S0-soft', 'S0-hard'])

    def test_snapshot_requires_x_soft(self):
        with tempfile.TemporaryDirectory() as tmp:
            code = build_code(n=24, d_v=3, d_c=6, cache_dir=tmp)
            frame = toy_frame(code)
            result = toy_result(frame)
            result.pop('x_soft')
            with self.assertRaisesRegex(ValueError, 'x_soft'):
                a01.snapshot_from_result(frame, result)
            result = toy_result(frame)
            snap = a01.snapshot_from_result(frame, result)
            self.assertIn('x_soft', snap)
            self.assertIn('support', snap)

    def test_reservation_includes_two_shared_preparation_passes(self):
        a = SimpleNamespace(split='mechanism', start=0, stop=1, snrs=[8],
                            max_full_calls=1, max_ce_calls=18, max_terminal_calls=32,
                            deadline_unix=int(time.time()) + 60, max_output_bytes=1024 ** 3,
                            d1=D1_PATH, d1_sha256=h01.FROZEN_D1_SHA256)
        parsed = a01.validate_args(a)
        self.assertEqual((parsed['n_full'], parsed['n_ce'], parsed['n_terminal']), (1, 18, 32))
        with self.assertRaises(ValueError):
            a01.validate_args(SimpleNamespace(**dict(vars(a), max_ce_calls=16)))

    def test_replay_reserves_no_full_receiver_and_counts_all_preparation(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'batch'
            out.mkdir()
            contract = dict(start=0, stop=1, snrs=[8], max_full_calls=0,
                            max_ce_calls=18, max_terminal_calls=32,
                            replay_manifest_sha256='a' * 64)
            ledger = Path(a01.reserve_a01(out, contract))
            reservation = json.loads(next(ledger.glob('reservation-*.json')).read_text())
            self.assertEqual(reservation['calls_reserved'], {'F': 0, 'E': 18, 'T': 32})
            self.assertEqual(reservation['replay_manifest_sha256'], 'a' * 64)
            with self.assertRaisesRegex(ValueError, 'already reserved'):
                a01.reserve_a01(out, contract)

    def test_execute_charges_one_f_eighteen_e_thirtytwo_t(self):
        self._exercise_execute(replay=False)

    def test_cached_execution_never_builds_or_calls_full_receiver(self):
        self._exercise_execute(replay=True)

    def _exercise_execute(self, *, replay):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            protocol = root / 'p.json'
            protocol.write_text('{}')
            checkpoint = root / 'ckpt'
            checkpoint.write_bytes(b'ckpt')
            out = root / 'batch'
            code_dir = root / 'code'
            code_dir.mkdir()
            code = build_code(n=24, d_v=3, d_c=6, cache_dir=code_dir)
            frame = toy_frame(code, protocol_sha256=sha(protocol))
            result = toy_result(frame)
            snap = a01.snapshot_from_result(frame, result)
            prepared = dict(
                snapshot=snap, I=np.array([0], dtype=int), S0=np.array([0], dtype=int),
                W_true=np.ones((1, 1), complex), W_est=np.ones((1, 1), complex),
                W_s0=np.ones((1, 1), complex), geometry={}, truth_support=[0],
                pairing_verified=True, geometry_frozen_before_data=True,
                reference_coefficients=np.ones(1, complex),
                preparation_solver_calls={'core_reference': 1, 'legal_search': 1},
                bridge_definition='fixture', legal_geometry={})
            fitted = dict(coefficients=np.ones(1, complex), atom_ids=np.array([0]),
                          H=np.eye(12, dtype=complex), residual={'relative_vector_closure': 0.},
                          diagnostics={}, basis=np.ones((1, 1)),
                          spec=a01._arm_spec('est-none-xsoft'),
                          truth_access_level='geometry_oracle+true_groups')

            class FakeReceiver:
                def __init__(self, *a, **k):
                    pass

                def run(self, observed, **k):
                    return result

            def fake_detect(prepared_arg, fitted_arg, code_arg, arm, detector, *, device, before_call):
                before_call('terminal', arm, detector)
                spec = a01._arm_spec(arm)
                return dict(FER=0, info_errors=0, truth_access_level='none',
                            legal_flow_comparable=spec['legal_flow_comparable'],
                            info_hat=frame._truth['info'], decoded=frame._truth['coded'],
                            llr=1. - 2. * frame._truth['coded'])

            args = SimpleNamespace(
                out=out, protocol=protocol, checkpoint=checkpoint, d1=D1_PATH,
                d1_sha256=h01.FROZEN_D1_SHA256, split='mechanism', start=0, stop=1,
                snrs=[8], device='cpu', deadline_unix=int(time.time()) + 120,
                max_full_calls=0 if replay else 1, max_ce_calls=18, max_terminal_calls=32,
                replay_manifest=protocol if replay else None,
                max_output_bytes=1024 ** 3)
            def prepare(*args, before_call, after_call):
                for phase in ('core_reference', 'legal_search'):
                    before_call(phase)
                    after_call(phase)
                return prepared

            with patch.object(a01, 'CHECKPOINT_HASH', sha(checkpoint)), \
                 patch.object(a01, 'sources', return_value={'fixture': '1'}), \
                 patch.object(a01, 'build_code', return_value=code), \
                 patch.object(a01, 'SupplementData') as data, \
                 patch.object(a01, '_make_config_a'), \
                 patch.object(a01, 'build_receiver') as build, \
                 patch.object(a01, 'load_manifest', return_value={'frames': [{'block': 0, 'snr': 8}]}), \
                 patch.object(a01, 'read_state', return_value=(snap, {'fixture': True}, {})), \
                 patch.object(a01, 'BaselineReceiver', FakeReceiver), \
                 patch.object(a01, 'prepare_from_frame', side_effect=prepare), \
                 patch.object(a01, 'fit_arm', return_value=fitted), \
                 patch.object(a01, 'fit_diagnostics', return_value=({}, {'gains': fitted['coefficients']})), \
                 patch.object(a01, 'detect_arm', side_effect=fake_detect):
                data.return_value.make_frame.return_value = frame
                self.assertEqual(a01.execute(args), 0)
                self.assertEqual(build.call_count, 0 if replay else 1)
            summary = json.loads((out / 'summary.json').read_text())
            self.assertEqual(summary['calls_completed'], {'F': 0 if replay else 1, 'E': 18, 'T': 32})
            self.assertEqual(summary['calls_completed'], summary['calls_attempted'])
            self.assertEqual(len(summary['arms']), 16)
            if replay:
                self.assertTrue((out / 'cached-state-8-000000.json').is_file())
                self.assertFalse(list(out.glob('snapshot-*.npz')))
                self.assertFalse(list(out.glob('started-F-*')))
            else:
                self.assertTrue((out / 'snapshot-8-000000.npz').is_file())
                with np.load(out / 'snapshot-8-000000.npz') as arrays:
                    self.assertIn('x_soft', arrays.files)
            cells = list(out.glob('cell-*.json'))
            self.assertEqual(len(cells), 32)
            s0 = json.loads(next(out.glob('cell-*-S0-soft-BP.json')).read_text())
            self.assertTrue(s0['legal_flow_comparable'])
            core = json.loads(next(out.glob('cell-*-est-none-xsoft-BP.json')).read_text())
            self.assertFalse(core['legal_flow_comparable'])
            self.assertFalse(core['deployable'])

    def test_harvest_run_reads_toy_batches(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'a01-mechanism-v1'
            root.mkdir()
            detectors = ('BP', 'BP80')
            for b in range(16):
                batch = root / f'batch-{16 * b:03d}-{16 * (b + 1):03d}'
                batch.mkdir()
                (batch / 'summary.json').write_text(json.dumps(dict(
                    status='complete', exitcode=0, failures=[],
                    calls_attempted={'F': 48, 'E': 768, 'T': 1536},
                    calls_completed={'F': 48, 'E': 768, 'T': 1536})))
                (batch / 'contract.json').write_text(json.dumps(dict(
                    d1_sha256=h01.FROZEN_D1_SHA256, recipe_id=a01.RECIPE_ID,
                    arms=list(a01.ARMS), detectors=list(detectors))))
                np.savez(batch / 'snapshot-8-000000.npz',
                         support=np.array([0]), x_soft=np.zeros(2), y=np.zeros(2))
                for snr in a01.SNRS:
                    for local in range(16):
                        block = 16 * b + local
                        for arm in a01.ARMS:
                            for det in detectors:
                                fer = int(arm == 'est-none-xsoft' and det == 'BP' and snr == 8)
                                (batch / f'cell-{snr}-{block:06d}-{arm}-{det}.json').write_text(
                                    json.dumps(dict(
                                        schema='supplement-a01-cell-v1', SNR=snr,
                                        block_id=block, arm=arm, detector=det, FER=fer,
                                        candidate_eligible=False, deployable=False,
                                        legal_flow_comparable=arm in ('S0-soft', 'S0-hard'),
                                        truth_access_level='none')))
            harvested = a01.harvest_run(root, contrast_manifest=MANIFEST)
            self.assertEqual(harvested['calls'], {'F': 768, 'E': 12288, 'T': 24576})
            self.assertTrue(harvested['snapshot_has_x_soft'])
            self.assertEqual(harvested['fer_by_cell'][8]['est-none-xsoft__BP'], 1.0)
            self.assertEqual(harvested['fer_by_cell'][8]['S0-soft__BP'], 0.0)
            self.assertFalse(harvested['rerun_16T'])
            geom = next(c for c in harvested['contrasts']
                        if c['arms'] == ['BP:core:g0c0d0', 'BP:core:g1c0d0'] and c['snr'] == 8)
            self.assertGreater(geom['delta'], 0)


if __name__ == '__main__':
    unittest.main()
