"""M-01 unit fixtures. Not 256-block structure evidence."""
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

from afdm_sp_joint_unrolled import supplement_h01 as h01
from afdm_sp_joint_unrolled import supplement_m01 as m01
from afdm_sp_joint_unrolled.direction_structure import fit
from afdm_sp_joint_unrolled.e1_ldpc import build_code
from afdm_sp_joint_unrolled.test_supplement_h01 import D1_PATH, sha, toy_frame, toy_result


class M01ContractTests(unittest.TestCase):
    def test_missing_support_is_not_reusable_h01_v2_snapshot(self):
        with self.assertRaisesRegex(ValueError, 'omit'):
            m01.require_support({'y': np.zeros(2)})

    def test_support_must_be_unique_ids(self):
        with self.assertRaises(ValueError):
            m01.require_support({'support': np.array([1, 1])})
        ids = m01.require_support({'support': np.array([3, 7, 11])})
        self.assertEqual(ids.tolist(), [3, 7, 11])

    def test_snapshot_from_result_keeps_support(self):
        with tempfile.TemporaryDirectory() as tmp:
            code = build_code(n=24, d_v=3, d_c=6, cache_dir=tmp)
            frame = toy_frame(code)
            snap = m01.snapshot_from_result(frame, toy_result(frame))
            self.assertEqual(snap['support'].tolist(), [0])
            self.assertNotIn('EP10', m01.ARMS)

    def test_d1_binding_rejects_ep10(self):
        d1, digest = h01.load_d1_freeze(D1_PATH)
        self.assertEqual(digest, sha(D1_PATH))
        detectors = h01.detectors_from_d1(d1)
        self.assertNotIn('EP10', detectors)
        with self.assertRaises(ValueError):
            m01.detect_arm({'snapshot': {'sigma2_terminal': .1, 'constellation': np.ones(4, complex),
                                         'info': np.zeros(1, np.uint8), 'support': np.array([1])},
                            'I': np.array([1])},
                           {'H': np.eye(1), 'z': np.zeros(1, complex),
                            'residual': {}, 'fitted': {'coefficients': np.ones(1)}},
                           {'n': 2}, 'free', 'EP10', device='cpu',
                           before_call=lambda *a: None)

    def test_fit_still_rejects_true_gains(self):
        y = np.array([1, .5j])
        A = np.eye(2, dtype=complex)
        L = np.eye(2, dtype=complex)
        with self.assertRaises(TypeError):
            fit(y, A, [0, 1], 'link', basis=L, sigma_terminal=.1, true_gains=np.ones(2))

    def test_reservation_is_768f_3072e_6144t(self):
        a = SimpleNamespace(split='mechanism', start=0, stop=1, snrs=[8],
                            max_full_calls=1, max_ce_calls=4, max_terminal_calls=8,
                            deadline_unix=int(time.time()) + 60, max_output_bytes=1024 ** 3,
                            d1=D1_PATH, d1_sha256=h01.FROZEN_D1_SHA256)
        parsed = m01.validate_args(a)
        self.assertEqual((parsed['n_full'], parsed['n_ce'], parsed['n_terminal']), (1, 4, 8))
        with self.assertRaises(ValueError):
            m01.validate_args(SimpleNamespace(**dict(vars(a), max_ce_calls=3)))

    def test_execute_charges_one_f_four_e_eight_t(self):
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
            prepared = dict(I=np.array([0], dtype=int), snapshot=m01.snapshot_from_result(frame, result),
                            basis=np.ones((1, 1), complex), Phi_I=np.ones((12, 1), complex),
                            truth_support=[0], pairing_verified=True,
                            input_hashes=frame.metadata['input_hashes'])
            fitted = dict(fitted={'coefficients': np.ones(1, complex), 'atom_ids': [0]},
                          H=np.eye(12, dtype=complex), z=np.zeros(12, complex),
                          residual={'relative_vector_closure': 0.})

            class FakeReceiver:
                def __init__(self, *a, **k):
                    pass

                def run(self, observed, **k):
                    return result

            def fake_detect(prepared_arg, fitted_arg, code_arg, arm, detector, *, device, before_call):
                before_call('terminal', arm, detector)
                return dict(FER=0, info_errors=0, truth_access_level='geometry_oracle',
                            info_hat=frame._truth['info'])

            args = SimpleNamespace(
                out=out, protocol=protocol, checkpoint=checkpoint, d1=D1_PATH,
                d1_sha256=h01.FROZEN_D1_SHA256, split='mechanism', start=0, stop=1,
                snrs=[8], device='cpu', deadline_unix=int(time.time()) + 120,
                max_full_calls=1, max_ce_calls=4, max_terminal_calls=8,
                max_output_bytes=1024 ** 3)
            with patch.object(m01, 'CHECKPOINT_HASH', sha(checkpoint)), \
                 patch.object(m01, 'sources', return_value={'fixture': '1'}), \
                 patch.object(m01, 'build_code', return_value=code), \
                 patch.object(m01, 'SupplementData') as data, \
                 patch.object(m01, '_make_config_a'), \
                 patch.object(m01, 'build_receiver'), \
                 patch.object(m01, 'BaselineReceiver', FakeReceiver), \
                 patch.object(m01, 'prepare_from_frame', return_value=prepared), \
                 patch.object(m01, 'fit_arm', return_value=fitted), \
                 patch.object(m01, 'detect_arm', side_effect=fake_detect):
                data.return_value.make_frame.return_value = frame
                self.assertEqual(m01.execute(args), 0)
            summary = json.loads((out / 'summary.json').read_text())
            self.assertEqual(summary['calls_completed'], {'F': 1, 'E': 4, 'T': 8})
            self.assertNotIn('EP10', json.dumps(summary))
            self.assertTrue((out / 'snapshot-8-000000.npz').is_file())
            with np.load(out / 'snapshot-8-000000.npz') as arrays:
                self.assertIn('support', arrays.files)

    def test_harvest_run_reads_toy_batches_and_rejects_missing_support(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'm01-mechanism-v2'
            root.mkdir()
            detectors = ('BP', 'BP80')
            for b in range(16):
                batch = root / f'batch-{16 * b:03d}-{16 * (b + 1):03d}'
                batch.mkdir()
                (batch / 'summary.json').write_text(json.dumps(dict(
                    status='complete', exitcode=0, failures=[],
                    calls_attempted={'F': 48, 'E': 192, 'T': 384},
                    calls_completed={'F': 48, 'E': 192, 'T': 384})))
                (batch / 'contract.json').write_text(json.dumps(dict(
                    d1_sha256=h01.FROZEN_D1_SHA256, recipe_id=m01.RECIPE_ID,
                    arms=list(m01.ARMS), detectors=list(detectors))))
                np.savez(batch / 'snapshot-8-000000.npz', support=np.array([0]), y=np.zeros(2))
                for snr in m01.SNRS:
                    for local in range(16):
                        block = 16 * b + local
                        for arm in m01.ARMS:
                            for det in detectors:
                                fer = int(arm == 'free' and det == 'BP' and snr == 8)
                                (batch / f'cell-{snr}-{block:06d}-{arm}-{det}.json').write_text(
                                    json.dumps(dict(
                                        schema='supplement-m01-cell-v1', SNR=snr,
                                        block_id=block, arm=arm, detector=det, FER=fer,
                                        candidate_eligible=False, deployable=False,
                                        truth_access_level='geometry_oracle')))
            harvested = m01.harvest_run(root, contrast_manifest=MANIFEST)
            self.assertEqual(harvested['calls'], {'F': 768, 'E': 3072, 'T': 6144})
            self.assertTrue(harvested['snapshot_has_support'])
            self.assertFalse(harvested['a01_can_reuse_m01_snapshots'])
            self.assertEqual(harvested['fer_by_cell'][8]['free__BP'], 1.0)
            self.assertEqual(harvested['fer_by_cell'][8]['link__BP'], 0.0)
            self.assertEqual(harvested['status'], 'complete_development_not_confirmation')
            self.assertFalse(harvested['rerun_16T'])
            link_free = next(c for c in harvested['contrasts']
                             if c['id'] == 'BP:free-link@nominal:8' and c['snr'] == 8)
            self.assertGreater(link_free['delta'], 0)
            broken = root / 'batch-000-016' / 'snapshot-8-000000.npz'
            np.savez(broken, y=np.zeros(2))
            with self.assertRaisesRegex(ValueError, 'support'):
                m01.harvest_run(root, contrast_manifest=MANIFEST)


if __name__ == '__main__':
    unittest.main()
