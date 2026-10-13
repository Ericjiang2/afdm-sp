"""H-01 unit fixtures. Toy N is not 256-block mechanism evidence."""
from __future__ import annotations

import hashlib
import json
import tempfile
import time
import unittest
from .test_supplement_development_analysis import MANIFEST
from pathlib import Path
from types import MappingProxyType, SimpleNamespace
from unittest.mock import patch

import numpy as np

from afdm_sp_joint_unrolled import supplement_h01 as h01
from afdm_sp_joint_unrolled.direction_data import CampaignFrame
from afdm_sp_joint_unrolled.direction_factorial import residual_ledger
from afdm_sp_joint_unrolled.e1_ldpc import build_code, encode, qpsk_map

def resolve_d1_freeze(here=None):
    here = Path(here).resolve() if here is not None else Path(__file__).resolve()
    candidates = (
        here.parents[1] / '.mission/20260909_09-01-15-afdm-comprehensive-supplement/evidence/D1_FREEZE.json',
        here.parents[2] / 'inputs/D1_FREEZE.json',
        Path.cwd() / 'inputs/D1_FREEZE.json',
    )
    for path in candidates:
        if path.is_file():
            return path
    raise FileNotFoundError('D1_FREEZE.json not found in vault evidence or snapshot inputs')


D1_PATH = resolve_d1_freeze()
CONST = np.array([.5 + .5j, .5 - .5j, -.5 + .5j, -.5 - .5j])


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def toy_frame(code, *, block=0, snr=8, protocol_sha256='p' * 64):
    n = code['n'] // 2
    info = np.zeros(code['k'], dtype=np.uint8)
    coded = encode(code, info)
    data = qpsk_map(coded, scale=np.sqrt(.5))
    Htrue = np.eye(n, dtype=complex)
    pilot = np.full(n, .5 + .5j)
    noise = np.zeros(n, complex)
    sigma2 = np.array(.05)
    y = Htrue @ (pilot + data)
    observed = MappingProxyType(dict(
        y=y, pilot=pilot, sigma2=sigma2, constellation=CONST.copy()))
    truth = dict(H=Htrue, info=info, coded=coded, data=data, noise=noise, params=None)
    hashes = {k: h01.array_hash(v) for k, v in
              (('y', y), ('pilot', pilot), ('H', Htrue), ('info', info),
               ('coded', coded), ('data', data), ('noise', noise))}
    meta = dict(campaign_id=h01.CAMPAIGN_ID, split='mechanism', block=block,
                snr_db=snr, protocol_sha256=protocol_sha256, input_hashes=hashes,
                channel_seed=0, data_seed=0, code_id='toy', interleaver_id='identity',
                rng_words={'noise': [0]}, scenario='G0')
    return CampaignFrame(observed, meta, truth)


def toy_result(frame):
    n = len(frame.observed['y'])
    Hhat = .8 * np.asarray(frame._truth['H'])
    coded = np.asarray(frame._truth['coded'])
    info = np.asarray(frame._truth['info'])
    return dict(H=Hhat, sigma2=float(frame.observed['sigma2']),
                sigma2_terminal=.1, mu=np.zeros(n, complex), var=np.ones(n),
                llr=np.zeros(2 * n), decoded=coded.copy(), info_hat=info.copy(),
                x_hard=np.zeros(n, complex), x_soft=np.zeros(n, complex),
                gains=np.ones(1, complex), support=[0], decode_ok=True, seconds=.01,
                graphs=[], initial_estimator={'support': [0]}, capacity_trace=[],
                support_trace=[], terminal_scale=.5)


class H01ContractTests(unittest.TestCase):
    def test_d1_resolver_reads_snapshot_inputs_layout(self):
        with tempfile.TemporaryDirectory() as tmp:
            snap = Path(tmp) / 'source-h01-v2'
            fake = snap / 'source' / 'afdm_sp_joint_unrolled' / 'test_supplement_h01.py'
            fake.parent.mkdir(parents=True)
            fake.write_text('# fixture path only\n')
            dest = snap / 'inputs' / 'D1_FREEZE.json'
            dest.parent.mkdir()
            dest.write_bytes(D1_PATH.read_bytes())
            found = resolve_d1_freeze(fake)
            self.assertEqual(found.resolve(), dest.resolve())
            self.assertEqual(sha(found), h01.FROZEN_D1_SHA256)

    def test_real_d1_freeze_binds_bp_and_selected_not_ep10(self):
        self.assertTrue(D1_PATH.is_file())
        self.assertEqual(sha(D1_PATH), h01.FROZEN_D1_SHA256)
        d1, digest = h01.load_d1_freeze(D1_PATH)
        self.assertEqual(digest, h01.FROZEN_D1_SHA256)
        detectors = h01.detectors_from_d1(d1)
        self.assertEqual(detectors, ('BP', d1['selected']))
        self.assertEqual(len(set(detectors)), 2)
        self.assertNotIn('EP10', detectors)
        self.assertNotEqual(d1['selected'], 'BP')
        self.assertTrue(d1['h01_may_start'])
        self.assertFalse(d1['rerun_16T'])
        self.assertEqual(d1['status'], 'development_selected_frozen_reference')
        self.assertIn('optimal detector', d1['not_claims'])

    def test_d1_rejects_hash_ep10_and_blocked_start(self):
        raw = json.loads(D1_PATH.read_text())
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'd1.json'
            path.write_text(json.dumps(raw))
            with self.assertRaises(ValueError):
                h01.load_d1_freeze(path, expected_sha256='0' * 64)
            raw['selected'] = 'EP10'
            path.write_text(json.dumps(raw))
            with self.assertRaises(ValueError):
                h01.load_d1_freeze(path, expected_sha256=sha(path))
            raw = json.loads(D1_PATH.read_text())
            raw['h01_may_start'] = False
            path.write_text(json.dumps(raw))
            with self.assertRaises(ValueError):
                h01.load_d1_freeze(path, expected_sha256=sha(path))
            raw = json.loads(D1_PATH.read_text())
            raw['rerun_16T'] = True
            path.write_text(json.dumps(raw))
            with self.assertRaises(ValueError):
                h01.load_d1_freeze(path, expected_sha256=sha(path))

    def test_recipe_is_base_primary_not_a02_alias(self):
        self.assertEqual(h01.RECIPE_ID, 'B0-p2-s0.5')
        self.assertEqual(h01.recipe_by_id(h01.RECIPE_ID)['id'], 'B0-p2-s0.5')
        self.assertNotEqual(h01.RECIPE_ID, 'A02-Bstar')


class H01SnapshotTests(unittest.TestCase):
    def test_snapshot_residual_and_true_h_is_not_true_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            code = build_code(n=24, d_v=3, d_c=6, cache_dir=tmp)
            frame = toy_frame(code)
            result = toy_result(frame)
            snap = h01.factorial_snapshot(frame, result)
            residual_ledger(snap, snap['Hhat'], snap['Hhat'])
            cancel_true = residual_ledger(snap, snap['Htrue'], snap['Hhat'])
            data_true = residual_ledger(snap, snap['Hhat'], snap['Htrue'])
            self.assertLess(cancel_true['energies']['pilot_channel_error'], 1e-18)
            self.assertGreater(data_true['energies']['pilot_channel_error'], 1e-18)
            self.assertLess(data_true['energies']['data_channel_error'], 1e-18)
            self.assertGreater(cancel_true['energies']['data_channel_error'], 1e-18)
            self.assertNotEqual(h01.array_hash(snap['Hhat']), h01.array_hash(snap['Htrue']))
            with self.assertRaises(AssertionError):
                residual_ledger(dict(snap, y=snap['y'] + 1.), snap['Hhat'], snap['Hhat'])


class H01ReservationTests(unittest.TestCase):
    def args(self, out, **changes):
        value = dict(out=out, protocol=Path('p.json'), checkpoint=Path('ckpt'),
                     d1=D1_PATH, d1_sha256=h01.FROZEN_D1_SHA256, split='mechanism',
                     start=0, stop=1, snrs=[8], device='cpu',
                     deadline_unix=int(time.time()) + 60, max_full_calls=1,
                     max_terminal_calls=8, max_output_bytes=1024 ** 3)
        value.update(changes)
        return SimpleNamespace(**value)

    def test_only_mechanism_768f_6144t_and_snr_domain(self):
        a = self.args(Path('out'))
        self.assertEqual(h01.validate_args(a)['n_full'], 1)
        for changes in (dict(split='design'), dict(stop=257), dict(snrs=[6]),
                        dict(max_full_calls=2), dict(max_terminal_calls=7),
                        dict(deadline_unix=time.time() + 60), dict(snrs=[8, 8])):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                h01.validate_args(self.args(Path('out'), **changes))
        ok = self.args(Path('out'), start=250, stop=256, snrs=[7, 8, 9],
                       max_full_calls=18, max_terminal_calls=144)
        self.assertEqual(h01.validate_args(ok)['n_full'], 18)
        self.assertEqual(h01.validate_args(ok)['n_terminal'], 144)

    def test_shared_ledger_rejects_overlap_and_fills_768(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            contract = dict(max_full_calls=512, max_terminal_calls=4096,
                            config_sha256='a' * 64, start=0, stop=256, snrs=[7, 8],
                            source_sha256={}, checkpoint_sha256='c',
                            protocol_sha256='p', d1_sha256=h01.FROZEN_D1_SHA256)
            h01.reserve_h01(root / 'first', contract)
            with self.assertRaisesRegex(ValueError, 'already reserved'):
                h01.reserve_h01(root / 'dup', dict(contract, max_full_calls=1,
                    max_terminal_calls=8, start=0, stop=1, snrs=[7],
                    config_sha256='b' * 64))
            h01.reserve_h01(root / 'last', dict(contract, max_full_calls=256,
                max_terminal_calls=2048, start=0, stop=256, snrs=[9],
                config_sha256='d' * 64))
            with self.assertRaisesRegex(ValueError, 'already reserved'):
                h01.reserve_h01(root / 'over', dict(contract, max_full_calls=1,
                    max_terminal_calls=8, start=0, stop=1, snrs=[9],
                    config_sha256='e' * 64))


class H01RunBlockTests(unittest.TestCase):
    def test_cpu_block_runs_real_factorial_bp_and_d1(self):
        d1, _ = h01.load_d1_freeze(D1_PATH)
        detectors = h01.detectors_from_d1(d1)
        with tempfile.TemporaryDirectory() as tmp:
            code = build_code(n=24, d_v=3, d_c=6, cache_dir=tmp)
            frame = toy_frame(code, block=3, snr=7)
            out = Path(tmp) / 'batch'
            out.mkdir()
            attempts = []
            row = h01.run_block(frame, toy_result(frame), code, detectors, out,
                                before_full=lambda meta: attempts.append(('F', meta)),
                                before_cell=lambda meta: attempts.append(('T', meta)))
            self.assertEqual(row['recipe_id'], 'B0-p2-s0.5')
            self.assertEqual(row['detectors'], list(detectors))
            self.assertEqual(len(row['cells']), 8)
            self.assertEqual([k for k, _ in attempts], ['F'] + ['T'] * 8)
            self.assertTrue(all(c['cell_id'].endswith(detectors[0]) or
                                c['cell_id'].endswith(detectors[1]) for c in row['cells']))
            self.assertFalse(any('EP10' in c['cell_id'] for c in row['cells']))
            self.assertEqual(sum(c['detector'] == detectors[1] for c in row['cells']), 4)
            est = next(c for c in row['cells']
                       if c['cell_id'] == f'cancel_estimated__data_estimated__{detectors[0]}')
            cancel = next(c for c in row['cells']
                          if c['cell_id'] == f'cancel_true__data_estimated__{detectors[0]}')
            data = next(c for c in row['cells']
                        if c['cell_id'] == f'cancel_estimated__data_true__{detectors[0]}')
            self.assertNotEqual(est['z_hash'], cancel['z_hash'])
            self.assertEqual(est['z_hash'], data['z_hash'])
            self.assertNotEqual(est['H_data_source']['sha256'], data['H_data_source']['sha256'])
            self.assertTrue(cancel['truth_access_level'] == 'CSI_oracle')
            self.assertFalse(est['candidate_eligible'])
            self.assertTrue((out / f'normal-full-7-000003.json').is_file())
            self.assertEqual(len(list(out.glob('cell-7-000003-*.json'))), 8)

    def test_execute_mocked_receiver_uses_real_factorial(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            code_dir = root / 'code'
            code_dir.mkdir()
            code = build_code(n=24, d_v=3, d_c=6, cache_dir=code_dir)
            protocol = root / 'protocol.json'
            protocol.write_text('{}')
            checkpoint = root / 'ckpt'
            checkpoint.write_bytes(b'ckpt')
            out = root / 'batch'
            frame = toy_frame(code, protocol_sha256=sha(protocol))
            result = toy_result(frame)
            seen = []

            class FakeReceiver:
                def __init__(self, model, code_arg, identifier, **kwargs):
                    self.identifier = identifier

                def run(self, observed, **kwargs):
                    seen.append(self.identifier)
                    self_outer.assertIs(observed, frame.observed)
                    return result

            self_outer = self
            args = SimpleNamespace(
                out=out, protocol=protocol, checkpoint=checkpoint, d1=D1_PATH,
                d1_sha256=h01.FROZEN_D1_SHA256, split='mechanism', start=0, stop=1,
                snrs=[8], device='cpu', deadline_unix=int(time.time()) + 120,
                max_full_calls=1, max_terminal_calls=8, max_output_bytes=1024 ** 3)
            with patch.object(h01, 'CHECKPOINT_HASH', sha(checkpoint)), \
                 patch.object(h01, 'sources', return_value={'fixture': '1'}), \
                 patch.object(h01, 'build_code', return_value=code), \
                 patch.object(h01, 'SupplementData') as data, \
                 patch.object(h01, '_make_config_a'), \
                 patch.object(h01, 'build_receiver'), \
                 patch.object(h01, 'BaselineReceiver', FakeReceiver):
                data.return_value.make_frame.return_value = frame
                self.assertEqual(h01.execute(args), 0)
            self.assertEqual(seen, ['B0-p2-s0.5'])
            summary = json.loads((out / 'summary.json').read_text())
            self.assertEqual(summary['status'], 'complete')
            self.assertEqual((summary['calls_attempted']['F'],
                              summary['calls_attempted']['T']), (1, 8))
            self.assertEqual(summary['calls_completed']['F'], 1)
            self.assertEqual(summary['calls_completed']['T'], 8)
            self.assertNotIn('EP10', json.dumps(summary))
            contract = json.loads((out / 'contract.json').read_text())
            self.assertEqual(contract['recipe_id'], 'B0-p2-s0.5')
            self.assertEqual(contract['split'], 'mechanism')
            self.assertEqual(contract['detectors'][0], 'BP')
            self.assertNotIn('EP10', contract['detectors'])


class H01ContrastTests(unittest.TestCase):
    def test_c_d_detector_signs_from_paired_fer(self):
        d1, _ = h01.load_d1_freeze(D1_PATH)
        detectors = h01.detectors_from_d1(d1)
        n = 8
        zeros = [0] * n
        ones = [1] * n
        table = {}
        for snr in (7, 8, 9):
            for cancel in ('estimated', 'true'):
                for data in ('estimated', 'true'):
                    for det in detectors:
                        key = (snr, f'cancel_{cancel}__data_{data}__{det}')
                        if cancel == 'estimated' and data == 'estimated' and det == 'BP':
                            table[key] = ones
                        else:
                            table[key] = zeros
        rows = h01.development_contrasts(table, detectors, blocks=list(range(n)), manifest=MANIFEST)
        c_bp = next(r for r in rows if r['id'] == 'BP:C|D0@nominal:8' and r['snr'] == 8)
        self.assertGreater(c_bp['delta'], 0)
        self.assertEqual(c_bp['n'], n)
        det0 = next(r for r in rows if r['id'] == 'det:C0D0@nominal:8' and r['snr'] == 8)
        self.assertGreater(det0['delta'], 0)
        self.assertFalse(any('EP10' in json.dumps(r) for r in rows))
        ids = [r['id'] for r in rows if r['snr'] == 8]
        self.assertEqual(len(ids), 21)
        self.assertEqual(len(set(ids)), 21)


class H01HarvestTests(unittest.TestCase):
    def _batch(self, root, start, stop, detectors):
        out = root / f'batch-{start:03d}-{stop:03d}'
        out.mkdir()
        n = (stop - start) * 3
        (out / 'summary.json').write_text(json.dumps(dict(
            status='complete', exitcode=0, failures=[],
            calls_attempted={'F': n, 'T': 8 * n},
            calls_completed={'F': n, 'T': 8 * n})))
        (out / 'contract.json').write_text(json.dumps(dict(
            d1_sha256=h01.FROZEN_D1_SHA256, recipe_id='B0-p2-s0.5',
            detectors=list(detectors))))
        np.savez(out / 'snapshot-8-000000.npz', y=np.zeros(2), Hhat=np.eye(2))
        for block in range(start, stop):
            for snr in (7, 8, 9):
                for cancel in ('estimated', 'true'):
                    for data in ('estimated', 'true'):
                        for det in detectors:
                            cell = f'cancel_{cancel}__data_{data}__{det}'
                            fer = 1 if cancel == 'estimated' and data == 'estimated' and det == 'BP' else 0
                            (out / f'cell-{snr}-{block:06d}-{cell}.json').write_text(json.dumps(dict(
                                FER=fer, SNR=snr, cell_id=cell, block_id=block,
                                candidate_eligible=False, deployable=False)))
        return out

    def test_incomplete_run_is_not_768f_6144t(self):
        d1, _ = h01.load_d1_freeze(D1_PATH)
        detectors = h01.detectors_from_d1(d1)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._batch(root, 0, 16, detectors)
            with self.assertRaisesRegex(ValueError, '16 complete batches'):
                h01.harvest_run(root, contrast_manifest=MANIFEST)

    def test_harvest_reads_shipped_cells_and_support_gap(self):
        d1, _ = h01.load_d1_freeze(D1_PATH)
        detectors = h01.detectors_from_d1(d1)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for start in range(0, 256, 16):
                self._batch(root, start, start + 16, detectors)
            result = h01.harvest_run(root, contrast_manifest=MANIFEST)
            self.assertEqual(result['calls'], {'F': 768, 'T': 6144})
            self.assertFalse(result['snapshot_has_support'])
            self.assertFalse(result['m01_can_reuse_h01_snapshots'])
            self.assertNotIn('EP10', result['detectors'])
            self.assertEqual(result['fer_by_cell'][8][f'cancel_estimated__data_estimated__{detectors[0]}'], 1.0)
            self.assertEqual(result['fer_by_cell'][8][f'cancel_true__data_estimated__{detectors[0]}'], 0.0)
            self.assertTrue(all(r['scope'].startswith('H-01 development') for r in result['contrasts']))

    def test_extra_block_cannot_be_silently_discarded(self):
        detectors = ('BP', 'BP80')
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for start in range(0, 256, 16):
                self._batch(root, start, start + 16, detectors)
            batch = root / 'batch-000-016'
            record = json.loads(next(batch.glob('cell-*.json')).read_text())
            record['block_id'] = 999
            (batch / 'cell-extra.json').write_text(json.dumps(record))
            with self.assertRaisesRegex(ValueError, 'identity grid'):
                h01.harvest_run(root, contrast_manifest=MANIFEST)


if __name__ == '__main__':
    unittest.main()
