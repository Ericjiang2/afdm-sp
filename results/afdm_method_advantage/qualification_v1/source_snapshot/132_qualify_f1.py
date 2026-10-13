"""Write synthetic F1 numerical residuals; never calls a receiver or decoder."""
from __future__ import annotations

import argparse
import hashlib
import inspect
import json
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
from unittest import mock

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SOURCE = Path(os.environ.get('STAGE_A_SOURCE',
    ROOT / 'experiments/sp_afdm_native_joint_20260921'))
BASELINE = Path(os.environ.get('STAGE_A_BASELINE',
    ROOT / 'experiments/sp_afdm_frozen_20260920'))
sys.path[:0] = [str(SOURCE / 'src'), str(BASELINE / 'src'), str(HERE)]
from physical import Channel, daft  # noqa: E402
from twofft import time_refine  # noqa: E402
import physical  # noqa: E402
import twofft  # noqa: E402
import evidence  # noqa: E402
from f1 import PhysicalF1, refit, response, score_derivatives  # noqa: E402
from keep_slots import _valid_slots, time_refine_keep_slots  # noqa: E402
import native_f1  # noqa: E402


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def qualify(scratch_root):
    executed_sources = {'physical.py': Path(physical.__file__).resolve(),
                        'twofft.py': Path(twofft.__file__).resolve(),
                        'evidence.py': Path(evidence.__file__).resolve()}
    if (executed_sources['physical.py'] != (BASELINE/'src/physical.py').resolve()
            or executed_sources['evidence.py'] != (BASELINE/'src/evidence.py').resolve()
            or executed_sources['twofft.py'] != (SOURCE/'src/twofft.py').resolve()):
        raise ValueError('synthetic qualification imported an unbound source alias')
    n = 63
    c1, c2 = 5/(2*n), (np.sqrt(2)-1)/(2*n*n)
    rng = np.random.default_rng(928)
    pilot = rng.normal(size=n) + 1j*rng.normal(size=n)
    time_pilot = daft(pilot, c1, c2, True)
    response_errors = []
    for delay, nu in ((0, -2.1), (5, .37), (62, 2.81)):
        direct = response(time_pilot, delay, nu, c1)
        source = Channel(n, c1, c2, [delay], [nu], [1]).apply(pilot)
        response_errors.append(float(np.max(abs(daft(direct, c1, c2)-source))))
    residual = rng.normal(size=n) + 1j*rng.normal(size=n)
    energy, noise, nu = float(np.vdot(time_pilot, time_pilot).real), .21, .43

    def value(x):
        b = response(time_pilot, 7, x, c1)
        return score_derivatives(b, residual, energy, noise)[0]

    _, slope, curvature = score_derivatives(response(time_pilot, 7, nu, c1),
                                             residual, energy, noise)
    first = abs(slope-(value(nu+1e-5)-value(nu-1e-5))/(2e-5))
    second = abs(curvature-(value(nu+1e-4)-2*value(nu)+value(nu-1e-4))/1e-8)
    z = (1+.3j)*response(time_pilot, 3, .4, c1)
    f1 = PhysicalF1(n, c1, c2, 14).acquire(daft(z, c1, c2), pilot, .05)
    history = f1['objective_history']
    p = len(f1['delays'])
    gain, _, _, _ = refit(z, time_pilot, [2, 2, 7], [-1.4, .7, .5], c1, .13)
    B = np.column_stack([response(time_pilot, delay, doppler, c1)
                         for delay, doppler in zip([2, 2, 7], [-1.4, .7, .5])])
    expected = np.linalg.solve(B.conj().T@B+.13*np.eye(3), B.conj().T@z)
    y = rng.normal(size=n) + 1j*rng.normal(size=n)
    mu = .1*(rng.normal(size=n) + 1j*rng.normal(size=n))
    v = rng.uniform(.05, .5, size=n)
    ls, ks, gs = [2, 9], [-.7, 1.25], [1+.1j, .4j]
    old, old_detail = time_refine(y, pilot, mu, v, ls, ks, gs, c1, c2, .2)
    new, new_detail = time_refine_keep_slots(y, pilot, mu, v, ls, ks, gs, c1, c2, .2)
    metrics = dict(response_max_abs=max(response_errors), first_derivative_abs=float(first),
        second_derivative_abs=float(second), max_joint_objective_increase=float(
            max(0., np.max(np.diff(history)))), ridge_gain_max_abs=float(np.max(abs(gain-expected))),
        all_distinct_doppler_max_abs=float(np.max(abs(new.dopplers-old.dopplers))),
        all_distinct_gain_max_abs=float(np.max(abs(new.gains-old.gains))),
        all_distinct_gamma_max_abs=float(np.max(abs(new_detail['gamma']-old_detail['gamma']))),
        selected_paths=p, coordinate_visits=f1['counters']['coordinate_visits'],
        required_coordinate_visits=p*(p+2))
    if (metrics['response_max_abs'] > 3e-13 or metrics['first_derivative_abs'] > 2e-7
            or metrics['second_derivative_abs'] > 3e-5
            or metrics['max_joint_objective_increase'] > 1e-8
            or metrics['ridge_gain_max_abs'] > 3e-14
            or any(metrics[name] > 2e-10 for name in (
                'all_distinct_doppler_max_abs', 'all_distinct_gain_max_abs',
                'all_distinct_gamma_max_abs'))
            or metrics['coordinate_visits'] != metrics['required_coordinate_visits']):
        raise AssertionError('F1 synthetic numerical qualification failed')
    checks = {'A_response_cpp': True, 'B_first_second_derivatives': True,
              'C_objective_nonincrease': True, 'D_joint_ridge': True,
              'distinct_delay_handoff': True, 'G_eight_slot_budget': p <= 8}

    # E/F: source-matched observed-pilot acquisition and two retained slots.
    same_delay = response(time_pilot, 4, -1.5, c1) + .8*response(time_pilot, 4, 1.5, c1)
    pair = PhysicalF1(n, c1, c2, 4).acquire(daft(same_delay, c1, c2), pilot, .04)
    pair_channel, _ = time_refine_keep_slots(daft(same_delay, c1, c2), pilot,
        np.zeros(n, complex), np.full(n, .5), [4, 4], [-1.5, 1.5],
        [1, .8], c1, c2, .04)
    if (len(pair['delays']) < 2 or len(set(pair['delays'])) == len(pair['delays'])
            or pair_channel.delays.tolist() != [4, 4]
            or _valid_slots(np.array([4, 4]), np.array([.5, .5+5e-7]))
            or not _valid_slots(np.array([4, 4]), np.array([.5, .5+2e-6]))):
        raise AssertionError('same-delay multiplicity/duplicate boundary failed')
    checks['E_multiplicity'] = checks['F_duplicate_boundary'] = True
    if (set(inspect.signature(PhysicalF1.acquire).parameters) !=
            {'self', 'y', 'pilot', 'sigma2'}):
        raise AssertionError('F1 observed-only call interface differs')
    try:
        PhysicalF1(n, c1, c2, 4).acquire(daft(same_delay, c1, c2),
                                          pilot, .04, truth_delays=[4])
    except TypeError:
        checks['H_no_truth_interface'] = True
    else:
        raise AssertionError('F1 accepted a truth keyword')

    # Actual evidence serializer, all successful arm shapes, and fail-closed metadata.
    with tempfile.TemporaryDirectory(dir=scratch_root) as directory:
        directory = Path(directory)
        identity = dict(schema='cstate-necessity-stage-a/1',
                        observation_id='s650_f0000', arm='A', input_sha256='0'*64)
        for arm in 'ABCDE':
            identity['arm'] = arm
            payload = dict(final_decoded=np.zeros(2048, np.uint8),
                final_info=np.zeros(1024, np.uint8),
                baseline_arrays=dict(r0_delays=np.array([4, 4]),
                    r1_gains=np.array([1+.1j, .5-.2j]),
                    r1_inference_trace=[dict(iteration=0, variance=.5)]),
                acquisition=None if arm in 'AB' else dict(
                    counters={'bank_scans': 2}, last_coordinate_gain=1+.2j),
                branch_detector=None if arm in 'AC' else dict(
                    extrinsic=np.zeros(2048), trace=[dict(iteration=0)]))
            path = directory / f'{arm}.npz'
            evidence.save_artifact(path, payload, identity.copy())
            loaded, restored_identity = evidence.load_artifact(path)
            if (restored_identity['arm'] != arm or
                    not np.array_equal(loaded['baseline_arrays']['r1_gains'],
                                       payload['baseline_arrays']['r1_gains']) or
                    not np.array_equal(loaded['final_decoded'], payload['final_decoded'])):
                raise AssertionError('real evidence serializer round-trip failed')
        try:
            evidence.save_artifact(directory/'bad.npz', {'groups': {4: 1}}, identity)
        except TypeError:
            pass
        else:
            raise AssertionError('non-string metadata key was accepted')
    checks['real_serializer_and_failure_boundary'] = True

    # Two-round interface timing/slot chain with explicit stubs: no scalar TF or
    # decoder implementation is executed in this engineering qualification.
    full_n = 1024
    full_channel = Channel(full_n, 5/2048,
        (np.sqrt(2)-1)/(2*full_n**2), [4, 4], [-.8, .9], [1+.1j, .4-.2j])
    seen = []

    def fake_acquire(self, y, known_pilot, sigma2):
        return dict(channel=full_channel, delays=full_channel.delays.copy(),
            dopplers=full_channel.dopplers.copy(), gains=full_channel.gains.copy())

    def fake_refine(y, known_pilot, mu, v, delays, dopplers, gains, c1, c2, noise, **kwargs):
        seen.append((np.asarray(delays).copy(), np.asarray(dopplers).copy()))
        return full_channel, dict(evaluations=2, fft_count=3,
                                  history=[1.], gamma=np.eye(2))

    def fake_joint(y, known_pilot, c, noise, **kwargs):
        if c.delays.tolist() != [4, 4]:
            raise AssertionError('TF input regrouped same-delay slots')
        return dict(extrinsic=np.zeros(2048), app=np.zeros(2048),
            mu=np.zeros(1024, complex), variance=np.full(1024, .5),
            gains=full_channel.gains.copy(), gain_variance=np.full(2, .5),
            trace=[dict(iteration=0)], fft_count=41)

    def fake_decode(code, llr, maxiter):
        if maxiter != 50:
            raise AssertionError('decoder schedule differs')
        return dict(decoded=np.zeros(2048, np.uint8), incoming_llr=llr,
            raw_app=np.zeros(2048), raw_check_extrinsic=np.zeros(2048), iterations=1)

    with mock.patch.object(native_f1.PhysicalF1, 'acquire', fake_acquire), \
         mock.patch.object(native_f1, 'time_refine_keep_slots', fake_refine), \
         mock.patch.object(native_f1, 'scalar_joint', fake_joint), \
         mock.patch.object(native_f1, 'decoder_messages', fake_decode), \
         mock.patch.object(native_f1, 'moments', lambda prior, pd: (
             np.zeros(1024, complex), np.full(1024, .5), None)):
        obs = dict(y=np.zeros(1024, complex), pilot=np.ones(1024, complex), sigma2=.2)
        system = SimpleNamespace(rho=.5, l_max_cap=102,
                                 c1=full_channel.c1, c2=full_channel.c2)
        _, arrays, timing = native_f1.receive_f1(obs, system, {},
            checkpoint_sink=lambda event, decoded: None)
    if (len(seen) != 2 or arrays['r1_delays'].tolist() != [4, 4]
            or timing['entering_geometry']['delays'].tolist() != [4, 4]
            or any(delays.tolist() != [4, 4] for delays, _ in seen)):
        raise AssertionError('two-round F1 physical slot handoff differs')
    checks['two_round_TF_handoff_stub'] = True
    if not all(checks.values()):
        raise AssertionError('one or more F1 synthetic qualification checks failed')
    return dict(status='pass', synthetic_only=True, seed=928, n=n,
        production_receiver_calls=0, decoder_calls=0, new_observations=0,
        checks=checks, metrics=metrics,
        executed_source_paths={k: str(v) for k,v in executed_sources.items()},
        executed_source_hashes={k: sha(v) for k,v in executed_sources.items()},
        source_hashes={name: sha(HERE/name) for name in
            ('f1.py', 'keep_slots.py', 'native_f1.py', 'run_stage_a.py',
             'test_f1.py', 'test_stage_a.py', 'qualify_f1.py')})


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise FileExistsError(args.out)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(qualify(args.out.parent), indent=2, allow_nan=False)+'\n')
