"""Synthetic producer contracts; no production receiver or decoder calls."""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import os
import sys

import numpy as np
import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SOURCE = Path(os.environ.get('STAGE_A_SOURCE',
    ROOT / 'experiments/sp_afdm_native_joint_20260921'))
BASELINE = Path(os.environ.get('STAGE_A_BASELINE',
    ROOT / 'experiments/sp_afdm_frozen_20260920'))
sys.path[:0] = [str(SOURCE / 'src'), str(BASELINE / 'src'), str(HERE)]

import evidence  # noqa: E402
from physical import Channel  # noqa: E402
import native_f1  # noqa: E402
from run_stage_a import _compare_saved, schedule, update_c_trigger, write_json_exclusive  # noqa: E402


def test_balanced_primary_order_and_no_extra_arm():
    assert [schedule(i) for i in range(4)] == [
        ('A', 'B', 'C', 'D'), ('B', 'C', 'D', 'A'),
        ('C', 'D', 'A', 'B'), ('D', 'A', 'B', 'C')]
    assert [sum(arm == schedule(i)[slot] for i in range(1024))
            for arm in 'ABCD' for slot in range(4)] == [256] * 16
    for index in range(4):
        active = False
        for arm in schedule(index):
            active = update_c_trigger(active, arm, 1 if arm == 'C' else 0)
        assert active  # E is appended after all four rotations on every C trigger.


def test_actual_serializer_successful_four_arm_shapes(tmp_path):
    source_arrays = dict(r0_decoded=np.zeros(2048, np.uint8),
        r1_decoded=np.zeros(2048, np.uint8), r0_delays=np.array([4, 4]),
        r1_delays=np.array([4, 4]), r1_dopplers=np.array([-.5, .5]),
        r1_gains=np.array([1+.2j, .3-.1j]),
        r1_inference_trace=[dict(iteration=0, gain_variance=.1)])
    for arm in ('A', 'B', 'C', 'D', 'E'):
        branched = arm in ('B', 'D', 'E')
        payload = dict(observation_id='s650_f0000', arm=arm,
            input_sha256='0'*64, baseline_arrays=source_arrays,
            native_decoder=dict(decoded=np.zeros(2048, np.uint8),
                incoming_llr=np.zeros(2048)),
            acquisition=None if arm in ('A', 'B') else dict(
                delays=np.array([4, 4]), dopplers=np.array([-.5, .5]),
                objective_history=np.array([3., 2.]),
                counters=dict(bank_scans=2, joint_solves=4)),
            branch_inputs=None if not branched else dict(
                app_input=np.zeros(2048), check_prior=np.zeros(2048)),
            branch_detector=None if not branched else dict(
                extrinsic=np.zeros(2048), trace=[dict(iteration=0)]),
            branch_decoder=None if not branched else dict(
                decoded=np.zeros(2048, np.uint8), incoming_llr=np.zeros(2048)),
            final_decoded=np.zeros(2048, np.uint8), final_info=np.zeros(1024, np.uint8))
        path = tmp_path / f'{arm}.npz'
        digest = evidence.save_artifact(path, payload, dict(
            schema='cstate-necessity-stage-a/1', observation_id='s650_f0000',
            arm=arm, input_sha256='0'*64))
        loaded, identity = evidence.load_artifact(path)
        assert digest and identity['arm'] == arm
        assert np.array_equal(loaded['final_decoded'], payload['final_decoded'])
        assert np.array_equal(loaded['baseline_arrays']['r1_gains'],
                              source_arrays['r1_gains'])
        assert (loaded['branch_detector'] is None) == (not branched)


def test_serializer_and_decision_failure_boundaries(tmp_path):
    identity = dict(schema='cstate-necessity-stage-a/1', observation_id='s650_f0000',
                    arm='A', input_sha256='0'*64)
    with pytest.raises(TypeError, match='keys must be strings'):
        evidence.save_artifact(tmp_path/'bad-key.npz', {'groups': {4: 1}}, identity)
    with pytest.raises(ValueError, match='nonfinite metadata'):
        evidence.save_artifact(tmp_path/'nonfinite.npz', {'timing': float('nan')}, identity)
    path = tmp_path/'decision.json'
    write_json_exclusive(path, {'status': 'ok'})
    with pytest.raises(FileExistsError):
        write_json_exclusive(path, {'status': 'replacement'})


def test_historical_prefix_parity_and_bit_exactness():
    array = {'r0_decoded': np.zeros(2048, np.uint8),
             'r1_gains': np.array([1+.1j, .3-.1j])}
    second = {'r0_decoded': array['r0_decoded'].copy(),
              'r1_gains': array['r1_gains'] + 1e-10}
    assert _compare_saved(array, second) <= 2e-10
    second['r1_gains'][0] += 2e-10
    with pytest.raises(ValueError):
        _compare_saved(array, second)
    second['r1_gains'] = array['r1_gains'].copy()
    second['r0_decoded'][0] = 1
    with pytest.raises(ValueError):
        _compare_saved(array, second)


def test_two_round_f1_slot_handoff_with_synthetic_stubs(monkeypatch):
    path_delays = np.array([4, 4])
    path_nus = np.array([-.8, .9])
    path_gains = np.array([1+.1j, .4-.2j])
    channel = Channel(1024, 5/2048, (np.sqrt(2)-1)/(2*1024**2),
                      path_delays, path_nus, path_gains)
    seen = []

    def fake_acquire(self, y, pilot, sigma2):
        return {'channel': channel, 'delays': path_delays.copy(),
                'dopplers': path_nus.copy(), 'gains': path_gains.copy(),
                'objective_history': np.array([3., 2.]), 'counters': {'bank_scans': 1}}

    def fake_refine(y, pilot, mu, v, ls, ks, gs, c1, c2, noise, **kwargs):
        seen.append((np.asarray(ls).copy(), np.asarray(ks).copy(), np.asarray(mu).copy()))
        return channel, {'evaluations': 2, 'fft_count': 3, 'history': [1.],
                         'gamma': np.eye(2)}

    def fake_joint(y, pilot, c, noise, **kwargs):
        assert c.delays.tolist() == [4, 4]
        return dict(extrinsic=np.zeros(2048), app=np.zeros(2048),
            mu=np.zeros(1024, complex), variance=np.full(1024, .5),
            gains=path_gains.copy(), gain_variance=np.full(2, .5),
            trace=[dict(iteration=0)], fft_count=41)

    def fake_decode(code, llr, maxiter):
        assert maxiter == 50
        return dict(decoded=np.zeros(2048, np.uint8), incoming_llr=llr,
            raw_app=np.zeros(2048), raw_check_extrinsic=np.zeros(2048), iterations=1)

    monkeypatch.setattr(native_f1.PhysicalF1, 'acquire', fake_acquire)
    monkeypatch.setattr(native_f1, 'time_refine_keep_slots', fake_refine)
    monkeypatch.setattr(native_f1, 'scalar_joint', fake_joint)
    monkeypatch.setattr(native_f1, 'decoder_messages', fake_decode)
    monkeypatch.setattr(native_f1, 'moments', lambda prior, pd: (
        np.zeros(1024, complex), np.full(1024, .5), None))
    events = []
    obs = dict(y=np.zeros(1024, complex), pilot=np.ones(1024, complex), sigma2=.2)
    system = SimpleNamespace(rho=.5, l_max_cap=102, c1=channel.c1, c2=channel.c2)
    _, arrays, timing = native_f1.receive_f1(obs, system, {},
        checkpoint_sink=lambda event, decoded: events.append(event))
    assert len(seen) == len(events) == 2
    assert all(delays.tolist() == [4, 4] for delays, _, _ in seen)
    assert all(np.array_equal(nus, path_nus) for _, nus, _ in seen)
    assert arrays['r1_delays'].tolist() == [4, 4]
    assert timing['entering_geometry']['delays'].tolist() == [4, 4]
