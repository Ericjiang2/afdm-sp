"""S-01 unit fixtures. Not 192-block counterexample evidence."""
from __future__ import annotations

import hashlib
import json
import tempfile
import time
import unittest
from pathlib import Path
from types import MappingProxyType, SimpleNamespace
from unittest.mock import patch

import numpy as np
import torch

from afdm_sp_joint_unrolled import supplement_s01 as s01
from afdm_sp_joint_unrolled import direction_receiver
from afdm_sp_joint_unrolled.direction_receiver import data_constellation
from afdm_sp_joint_unrolled.direction_data import CampaignFrame
from afdm_sp_joint_unrolled.e1_ldpc import build_code, encode, qpsk_map

CONST = np.array([.5 + .5j, .5 - .5j, -.5 + .5j, -.5 - .5j])


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def toy_frame(code, *, block=0, snr=8, protocol_sha256='p' * 64, scenario='integer'):
    n = code['n'] // 2
    info = np.zeros(code['k'], dtype=np.uint8)
    coded = encode(code, info)
    data = qpsk_map(coded, scale=np.sqrt(.5))
    Htrue = np.eye(n, dtype=complex)
    pilot = np.full(n, .5 + .5j)
    y = Htrue @ (pilot + data)
    observed = MappingProxyType(dict(y=y, pilot=pilot, sigma2=np.array(.05), constellation=CONST.copy()))
    truth = dict(H=Htrue, info=info, coded=coded, data=data, noise=np.zeros(n, complex),
                 params={'P_actual': 8})
    meta = dict(split='counterexample', block=block, snr_db=snr, scenario=scenario,
                protocol_sha256=protocol_sha256, input_hashes={'y': 'y', 'pilot': 'p'})
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


def protocol_body(code_hash):
    g0 = dict(N_total=1024, P_paths=8, rho=.5, k_max_cap=2, l_max_cap=102, k_leak=2,
              frac_prune_rel_thres=.01, use_frac_doppler=True,
              gen_h_daft_convention='python', v_mean=2., tau_spread=.01, fs=16000.)
    def scene(sid, **updates):
        system = dict(g0)
        extra = {}
        if 'delay_collision' in updates:
            extra['delay_collision'] = updates.pop('delay_collision')
        if 'admitted' in updates:
            extra['admitted'] = updates.pop('admitted')
        system.update(updates)
        return dict(id=sid, generator='truncated_daft', admitted=extra.get('admitted', True),
                    **{k: v for k, v in extra.items() if k != 'admitted'}, system=system)
    return dict(
        campaign_id=s01.CAMPAIGN_ID,
        rng={'namespace_words': [20260909, 90115, 419173],
             'components': {'channel': 1, 'data': 2, 'noise': 3, 'code': 4,
                            'interleaver': 5, 'pilot-design': 6, 'order': 7}},
        splits={'engineering': 1, 'design': 2, 'mechanism': 3, 'confirm': 4,
                'counterexample': 5, 'timing': 6},
        scenarios={
            'G0': dict(id=0, generator='truncated_daft', system=g0),
            'integer': scene(1, use_frac_doppler=False),
            'overlap': scene(2, delay_collision='neighbor'),
            'P4': scene(3, P_paths=4),
            'P12': scene(4, P_paths=12),
            'rho25': scene(5, rho=.25),
            'rho75': scene(6, rho=.75),
            'G1': scene(7, frac_prune_rel_thres=0., admitted=False),
        },
        system={'ldpc': {'G_sha256': code_hash}, 'interleaver': 'identity'})


class S01Tests(unittest.TestCase):
    def test_real_receiver_entry_validates_rho_before_model_forward(self):
        class ForwardReached(RuntimeError):
            pass

        class InstrumentedModel:
            use_soft_decisions = True

            def __init__(self, rho):
                self.cfg = SimpleNamespace(
                    N=1024, l_max=102, k_max=2, rho=rho, n_paths=40,
                    n_outer_iter=10, pic_iter=20, early_stop=False,
                    dtype=torch.complex64, rdtype=torch.float32,
                    mp_mode='bp', update_sigma2=True, device='cpu')

            def __call__(self, y, pilot, sigma2, constellation, **kwargs):
                np.testing.assert_allclose(
                    constellation.numpy(), data_constellation(self.cfg.rho), rtol=1e-6)
                raise ForwardReached('real receiver entry reached model forward')

        # Instrument only the model and code identity; run the actual input boundary.
        with patch.object(direction_receiver, 'validate_code'):
            for rho in (.25, .5, .75):
                with self.subTest(rho=rho):
                    receiver = direction_receiver.ObservedReceiver(InstrumentedModel(rho), {})
                    observed = dict(y=np.zeros(1024, complex), pilot=np.zeros(1024, complex),
                                    sigma2=.1, constellation=data_constellation(rho))
                    with self.assertRaises(ForwardReached):
                        receiver.run(observed)
                    observed['constellation'] = data_constellation(.75 if rho != .75 else .25)
                    with self.assertRaisesRegex(ValueError, 'constellation differs'):
                        receiver.run(observed)

    def test_registered_rho_constellation_keeps_g0_and_rejects_unknown(self):
        g0 = np.sqrt(.5) * np.array([1 + 1j, 1 - 1j, -1 + 1j, -1 - 1j]) / np.sqrt(2)
        np.testing.assert_allclose(data_constellation(.5), g0)
        self.assertFalse(np.allclose(data_constellation(.25), g0))
        self.assertFalse(np.allclose(data_constellation(.75), g0))
        with self.assertRaises(ValueError):
            data_constellation(.4)

    def test_ready_units_exclude_g1_and_reserve_3456f(self):
        self.assertEqual(s01.UNIT_IDS, ('integer', 'overlap', 'P4', 'P12', 'rho25', 'rho75'))
        self.assertEqual(s01.TOTAL_F, 3456)
        self.assertNotIn('G1', s01.UNIT_IDS)
        a = SimpleNamespace(split='counterexample', start=0, stop=1, snrs=[8],
                            max_full_calls=6, deadline_unix=int(time.time()) + 60,
                            max_output_bytes=1024 ** 3, checkpoint=Path('x'),
                            resume_failed_batch=None)
        self.assertEqual(s01.validate_args(a)['n_full'], 6)
        with self.assertRaises(ValueError):
            s01.validate_args(SimpleNamespace(**dict(vars(a), split='design')))
        with self.assertRaises(ValueError):
            s01.validate_args(SimpleNamespace(**dict(vars(a), max_full_calls=5)))
        with self.assertRaises(ValueError):
            s01._identities(0, 1, [8], units=('G1',))

    def test_g1_has_explicit_576f_set_and_no_legacy_retry_authority(self):
        args = SimpleNamespace(split='counterexample', unit_set=s01.G1_SET,
            start=0, stop=192, snrs=[7, 8, 9], max_full_calls=576,
            deadline_unix=int(time.time()) + 60, max_output_bytes=40 * 1024**3,
            resume_failed_batch=None)
        parsed = s01.validate_args(args)
        self.assertEqual(parsed['n_full'], 576)
        self.assertEqual({key[2] for key in parsed['identities']}, {'G1'})
        with self.assertRaisesRegex(ValueError, 'retry allowance'):
            s01.validate_args(SimpleNamespace(**dict(vars(args), resume_failed_batch=Path('old'))))
        with self.assertRaisesRegex(ValueError, 'frozen ready set'):
            s01._identities(0, 1, [8], ('G1', 'integer'), unit_set=s01.G1_SET)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            contract = dict(campaign_id=s01.CAMPAIGN_ID, stage=s01.STAGE, start=0, stop=192,
                snrs=[7, 8, 9], unit_set=s01.G1_SET, max_full_calls=576)
            s01.reserve_s01(root / 'first', contract)
            with self.assertRaisesRegex(ValueError, 'already reserved'):
                s01.reserve_s01(root / 'second', contract)
            with self.assertRaisesRegex(ValueError, 'no automatic retry'):
                s01.reserve_s01(root / 'third', dict(contract, recovery={'fake': True}))

    def test_g1_batch_reader_rejects_missing_raw_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'contract.json').write_text(json.dumps(dict(recipe_id=s01.RECIPE_ID,
                units=['G1'], unit_set=s01.G1_SET, split=s01.SPLIT,
                g1_executed=True, protocol_sha256='p', start=0, stop=1, snrs=[8])))
            (root / 'summary.json').write_text(json.dumps(dict(status='complete', exitcode=0,
                failures=[], calls_attempted=1, calls_completed=1)))
            (root / 'frame-G1-8-000.json').write_text(json.dumps(dict(FER=0, unit='G1',
                scenario='G1', SNR=8, block_id=0, frame_protocol_sha256='wrong')))
            with self.assertRaisesRegex(ValueError, 'protocol changed'):
                s01._read_batch(root, unit_set=s01.G1_SET)
            with self.assertRaisesRegex(ValueError, 'binding mismatch'):
                s01._read_batch(root)

    def test_execute_runs_six_units_and_never_g1(self):
        self._run_fixture()

    def _run_fixture(self, *, recover=False, corrupt=False, recovery_chain=False):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            protocol = root / 'p.json'
            checkpoint = root / 'ckpt'
            checkpoint.write_bytes(b'ckpt')
            out = root / 'batch-000-001'
            (root / 'code').mkdir()
            code = build_code(n=24, d_v=3, d_c=6, cache_dir=root / 'code')
            from afdm_sp_joint_unrolled.direction_data import CODE_HASH
            protocol.write_text(json.dumps(protocol_body(CODE_HASH)))
            seen = []
            models = []
            failed_rhos = {.25, .75} if recover else set()
            cfg_failure = []

            class FakeReceiver:
                def __init__(self, *a, **k):
                    self.system = k.get('system')

                def run(self, observed, **kwargs):
                    seen.append(getattr(self.system, 'rho', None))
                    if self.system.rho in failed_rhos:
                        if cfg_failure:
                            raise UnboundLocalError("local variable 'cfg' referenced before assignment")
                        raise ValueError('constellation differs from frozen data power/order')
                    return toy_result(toy_frame(code))

            args = SimpleNamespace(
                out=out, protocol=protocol, checkpoint=checkpoint, split='counterexample',
                start=0, stop=1, snrs=[8], device='cpu',
                deadline_unix=int(time.time()) + 120, max_full_calls=6,
                max_output_bytes=1024 ** 3, resume_failed_batch=None)
            with patch.object(s01, 'CHECKPOINT_HASH', sha(checkpoint)), \
                 patch.object(s01, 'sources', return_value={'fixture': '1'}), \
                 patch.object(s01, 'build_code', return_value=code), \
                 patch.object(s01, 'SupplementData') as data, \
                 patch.object(s01, '_make_config_a',
                              side_effect=lambda *a, **k: SimpleNamespace(
                                  P_paths=8, rho=.5, use_frac_doppler=True,
                                  delay_collision=None, k_leak=2, frac_prune_rel_thres=.01)), \
                 patch.object(s01, 'build_receiver', side_effect=lambda *a, **k: models.append(a[1].rho) or object()), \
                 patch.object(s01, 'BaselineReceiver', FakeReceiver):
                proto = json.loads(protocol.read_text())
                data.return_value.protocol = proto
                data.return_value.make_frame.side_effect = (
                    lambda system, split, block, snr, scenario='G0':
                    toy_frame(code, block=block, snr=snr, protocol_sha256=sha(protocol),
                              scenario=scenario))
                # system_for overwrites P_paths from spec after _make_config_a
                def fake_system(spec):
                    return SimpleNamespace(
                        P_paths=int(spec['system']['P_paths']),
                        rho=float(spec['system']['rho']),
                        use_frac_doppler=bool(spec['system']['use_frac_doppler']),
                        delay_collision=spec.get('delay_collision'),
                        k_leak=2, frac_prune_rel_thres=.01)
                with patch.object(s01, 'system_for', side_effect=fake_system):
                    self.assertEqual(s01.execute(args), 1 if recover else 0)
                    if recover:
                        before = {p.name: p.read_bytes() for p in out.glob('*.json')}
                        failed_rhos.clear()
                        seen.clear()
                        resumed = SimpleNamespace(**dict(
                            vars(args), out=root / 'batch-000-001-recovery-v2',
                            max_full_calls=2, resume_failed_batch=out))
                        if corrupt:
                            path = next(out.glob('frame-*.json'))
                            row = json.loads(path.read_text())
                            row['FER'] = 1 - row['FER']
                            path.write_text(json.dumps(row))
                            with self.assertRaisesRegex(ValueError, 'recovery'):
                                s01.execute(resumed)
                            self.assertEqual(seen, [])
                            return
                        prior_attempts, prior_failures = 6, 2
                        if recovery_chain:
                            failed_rhos.update((.25, .75))
                            cfg_failure.append(True)
                            self.assertEqual(s01.execute(resumed), 1)
                            failed_rhos.clear()
                            seen.clear()
                            second = resumed.out
                            second_before = {p.name: p.read_bytes() for p in second.glob('*.json')}
                            resumed = SimpleNamespace(**dict(
                                vars(resumed), out=root / 'batch-000-001-recovery-v3',
                                resume_failed_batch=second))
                            prior_attempts, prior_failures = 8, 4
                        self.assertEqual(s01.execute(resumed), 0)
                        self.assertEqual(sorted(seen), [.25, .75])
                        summary = json.loads((resumed.out / 'summary.json').read_text())
                        self.assertEqual((summary['calls_attempted'], summary['calls_completed'],
                                          summary['calls_reused']), (2, 2, 4))
                        self.assertEqual(len(list(resumed.out.glob('frame-*.json'))), 6)
                        self.assertEqual(before, {p.name: p.read_bytes() for p in out.glob('*.json')})
                        if recovery_chain:
                            self.assertEqual(second_before, {
                                p.name: p.read_bytes() for p in second.glob('*.json')})
                        with patch.object(s01, 'N_BATCHES', 1), patch.object(s01, 'N_BLOCKS', 1), \
                             patch.object(s01, 'SNRS', (8,)), patch.object(s01, 'TOTAL_F', 6):
                            harvested = s01.harvest_run(root)
                        self.assertEqual(harvested['calls'], {'F': 6})
                        self.assertEqual(harvested['execution_accounting'], {
                            'attempted_F': prior_attempts + 2, 'failed_F': prior_failures, 'reused_F': 4,
                            'new_completed_F': 2, 'unique_completed_F': 6})
                        replay = SimpleNamespace(**dict(vars(resumed), out=root / 'duplicate'))
                        with self.assertRaisesRegex(ValueError, 'already reserved'):
                            s01.execute(replay)
                        if recovery_chain:
                            ancestor = next(out.glob('frame-*.json'))
                            ancestor.write_bytes(ancestor.read_bytes() + b'\n')
                            with self.assertRaisesRegex(ValueError, 'source changed'):
                                s01._read_batch(resumed.out)
                        return
            self.assertEqual(len(seen), 6)
            self.assertEqual(sorted(models), [.25, .5, .75])
            self.assertIn(.25, seen)
            self.assertIn(.75, seen)
            names = {p.name for p in out.glob('frame-*.json')}
            self.assertTrue(any(name.startswith('frame-integer-') for name in names))
            self.assertFalse(any('G1' in name for name in names))
            summary = json.loads((out / 'summary.json').read_text())
            self.assertEqual((summary['calls_attempted'], summary['calls_completed']), (6, 6))
            self.assertFalse(summary['g1_executed'])

    def test_recovery_reuses_successes_and_rejects_duplicate_retry(self):
        self._run_fixture(recover=True)

    def test_recovery_rejects_changed_successful_record(self):
        self._run_fixture(recover=True, corrupt=True)

    def test_recovery_retains_both_failed_sources_and_counts_every_attempt(self):
        self._run_fixture(recover=True, recovery_chain=True)

    def test_harvest_run_reads_toy_batches(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 's01-counterexample-v1'
            root.mkdir()
            for b in range(12):
                batch = root / f'batch-{16 * b:03d}-{16 * (b + 1):03d}'
                batch.mkdir()
                (batch / 'summary.json').write_text(json.dumps(dict(
                    status='complete', exitcode=0, failures=[],
                    calls_attempted=288, calls_completed=288)))
                (batch / 'contract.json').write_text(json.dumps(dict(
                    recipe_id=s01.RECIPE_ID, units=list(s01.UNIT_IDS),
                    split='counterexample', g1_executed=False,
                    start=16*b, stop=16*(b+1), snrs=list(s01.SNRS))))
                for snr in s01.SNRS:
                    for local in range(16):
                        block = 16 * b + local
                        for unit in s01.UNIT_IDS:
                            fer = int(unit == 'P12' and snr == 8)
                            (batch / f'frame-{unit}-{snr}-{block:03d}.json').write_text(
                                json.dumps(dict(
                                    schema='supplement-s01-frame-v1', SNR=snr,
                                    block_id=block, unit=unit, scenario=unit, FER=fer,
                                    candidate_eligible=False, deployable=False,
                                    true_P_to_receiver=False)))
            harvested = s01.harvest_run(root)
            self.assertEqual(harvested['calls'], {'F': 3456})
            self.assertEqual(harvested['fer_by_cell'][8]['P12'], 1.0)
            self.assertEqual(harvested['fer_by_cell'][8]['P4'], 0.0)
            self.assertFalse(harvested['g1_executed'])
            self.assertFalse(harvested['rerun_16T'])
            contrast = next(c for c in harvested['contrasts']
                            if c['id'] == 'P12-P4' and c['snr'] == 8)
            self.assertGreater(contrast['delta'], 0)


if __name__ == '__main__':
    unittest.main()
