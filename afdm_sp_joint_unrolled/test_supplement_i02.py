"""I-02 unit fixtures. Not 192-block cancellation evidence."""
from __future__ import annotations

import hashlib
import json
import tempfile
import time
import unittest
from .test_supplement_development_analysis import MANIFEST
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np

from afdm_sp_joint_unrolled import supplement_i02 as i02
from types import MappingProxyType

from afdm_sp_joint_unrolled.direction_data import CampaignFrame
from afdm_sp_joint_unrolled.e1_ldpc import build_code, encode, qpsk_map

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
    y = Htrue @ (pilot + data)
    observed = MappingProxyType(dict(y=y, pilot=pilot, sigma2=np.array(.05), constellation=CONST.copy()))
    truth = dict(H=Htrue, info=info, coded=coded, data=data, noise=np.zeros(n, complex), params=None)
    meta = dict(split='design', block=block, snr_db=snr, protocol_sha256=protocol_sha256,
                input_hashes={'y': 'y', 'pilot': 'p'})
    return CampaignFrame(observed, meta, truth)


def toy_result(frame):
    n = len(frame.observed['y'])
    coded = np.asarray(frame._truth['coded'])
    info = np.asarray(frame._truth['info'])
    return dict(H=.8 * np.asarray(frame._truth['H']), sigma2=float(frame.observed['sigma2']),
                sigma2_terminal=.1, mu=np.zeros(n, complex), var=np.ones(n),
                llr=np.zeros(2 * n), decoded=coded.copy(), info_hat=info.copy(),
                x_hard=np.zeros(n, complex), x_soft=np.zeros(n, complex),
                gains=np.ones(1, complex), support=[0], decode_ok=True, seconds=.01)


class I02Tests(unittest.TestCase):
    def test_four_arms_and_design_2304f(self):
        self.assertEqual(i02.ARM_IDS, ('I02-baseline', 'I02-scalar', 'I02-diagonal', 'I02-lowrank'))
        self.assertEqual(i02.TOTAL_F, 2304)
        self.assertIsNone(i02.transform_for(SimpleNamespace(), i02.ARMS[0]))
        a = SimpleNamespace(split='design', start=0, stop=1, snrs=[8],
                            max_full_calls=4, deadline_unix=int(time.time()) + 60,
                            max_output_bytes=1024 ** 3, checkpoint=Path('x'))
        self.assertEqual(i02.validate_args(a)['n_full'], 4)
        with self.assertRaises(ValueError):
            i02.validate_args(SimpleNamespace(**dict(vars(a), split='mechanism')))
        with self.assertRaises(ValueError):
            i02.validate_args(SimpleNamespace(**dict(vars(a), max_full_calls=3)))

    def test_execute_runs_all_four_arms_and_keeps_baseline_untransformed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            protocol = root / 'p.json'
            protocol.write_text('{}')
            checkpoint = root / 'ckpt'
            checkpoint.write_bytes(b'ckpt')
            out = root / 'batch'
            (root / 'code').mkdir()
            code = build_code(n=24, d_v=3, d_c=6, cache_dir=root / 'code')
            frame = toy_frame(code, protocol_sha256=sha(protocol))
            result = toy_result(frame)
            seen = []

            class FakeReceiver:
                def __init__(self, *a, **k):
                    pass

                def run(self, observed, **kwargs):
                    seen.append(kwargs.get('terminal_transform'))
                    out_result = dict(result)
                    if kwargs.get('terminal_transform') is not None:
                        out_result['cancellation_transform'] = {
                            'z': observed['y'], 'H': result['H'],
                            'sigma_out': result['sigma2_terminal'],
                            'diagnostics': {'truth_access': 'none', 'mode': 'fixture'},
                            'B': np.zeros((2, 0), complex)}
                    return out_result

            args = SimpleNamespace(
                out=out, protocol=protocol, checkpoint=checkpoint, split='design',
                start=0, stop=1, snrs=[8], device='cpu',
                deadline_unix=int(time.time()) + 120, max_full_calls=4,
                max_output_bytes=1024 ** 3)
            with patch.object(i02, 'CHECKPOINT_HASH', sha(checkpoint)), \
                 patch.object(i02, 'sources', return_value={'fixture': '1'}), \
                 patch.object(i02, 'build_code', return_value=code), \
                 patch.object(i02, 'SupplementData') as data, \
                 patch.object(i02, '_make_config_a'), \
                 patch.object(i02, 'build_receiver'), \
                 patch.object(i02, 'BaselineReceiver', FakeReceiver), \
                 patch.object(i02, 'transform_for',
                              side_effect=lambda system, arm: None if arm['mode'] is None else object()):
                data.return_value.make_frame.return_value = frame
                self.assertEqual(i02.execute(args), 0)
            self.assertEqual(len(seen), 4)
            self.assertEqual(sum(t is None for t in seen), 1)
            summary = json.loads((out / 'summary.json').read_text())
            self.assertEqual((summary['calls_attempted'], summary['calls_completed']), (4, 4))
            baseline = json.loads(next(out.glob('frame-*-I02-baseline.json')).read_text())
            self.assertIsNone(baseline['mode'])
            self.assertIsNone(baseline['cancellation'])

    def test_harvest_run_reads_toy_batches(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'i02-design-v1'
            root.mkdir()
            for b in range(12):
                batch = root / f'batch-{16 * b:03d}-{16 * (b + 1):03d}'
                batch.mkdir()
                (batch / 'summary.json').write_text(json.dumps(dict(
                    status='complete', exitcode=0, failures=[],
                    calls_attempted=192, calls_completed=192)))
                (batch / 'contract.json').write_text(json.dumps(dict(
                    recipe_id=i02.RECIPE_ID, arms=list(i02.ARM_IDS), split='design')))
                for snr in i02.SNRS:
                    for local in range(16):
                        block = 16 * b + local
                        for arm in i02.ARM_IDS:
                            fer = int(arm == 'I02-scalar' and snr == 8)
                            (batch / f'frame-{snr}-{block:03d}-{arm}.json').write_text(
                                json.dumps(dict(
                                    schema='supplement-i02-frame-v1', SNR=snr,
                                    block_id=block, arm_id=arm, FER=fer,
                                    candidate_eligible=False, deployable=False,
                                    truth_access_level='none')))
            harvested = i02.harvest_run(root, contrast_manifest=MANIFEST)
            self.assertEqual(harvested['calls'], {'F': 2304})
            self.assertEqual(harvested['fer_by_cell'][8]['I02-scalar'], 1.0)
            self.assertEqual(harvested['fer_by_cell'][8]['I02-baseline'], 0.0)
            self.assertEqual(harvested['status'], 'complete_development_not_confirmation')
            self.assertFalse(harvested['rerun_16T'])
            contrast = next(c for c in harvested['contrasts']
                            if c['id'] == 'cov:scalar_base-scalar_calibrated@nominal:8' and c['snr'] == 8)
            self.assertLess(contrast['delta'], 0)


if __name__ == '__main__':
    unittest.main()
