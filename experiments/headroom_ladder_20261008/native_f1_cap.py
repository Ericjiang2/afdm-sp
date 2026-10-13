"""PB16 comparator entry (task 10-08-doppler-cluster): COPY of cstate_necessity_stageA_20260928/native_f1.py receive_f1 with
PhysicalF1 -> PhysicalF1Cap(cap) (f1_cap.py) and time_refine_keep_slots(max_paths=8) -> max_paths=cap.  Everything else is identical
(2 coded rounds, TF20 joint, LDPC50, same state hand-over).  `keep_slots.time_refine_keep_slots` is imported UNCHANGED (its cap is
the max_paths argument).  Comparator only, cap 16, no stopping rule.
"""
from __future__ import annotations

import time

import numpy as np

from f1_cap import PhysicalF1Cap
from keep_slots import time_refine_keep_slots
from messages import moments
from receiver import decoder_messages
from twofft import scalar_joint

def receive_f1_cap(observation, system, code, *, cap=16, checkpoint_sink=None, record_states=False):
    if set(observation) != {'y', 'pilot', 'sigma2'}:
        raise ValueError('F1 accepts only the three observed input fields')
    if len(observation['y']) != 1024 or system.rho != .5 or system.l_max_cap != 102:
        raise ValueError('frozen F1 interface requires N=1024, rho=.5, delay cap 102')
    if checkpoint_sink is not None and not callable(checkpoint_sink):
        raise TypeError('checkpoint_sink must be callable')
    start = time.perf_counter()
    initial = PhysicalF1Cap(1024, system.c1, system.c2, 102, cap).acquire(
        observation['y'], observation['pilot'], float(observation['sigma2']))
    acquisition_end = time.perf_counter()
    state = {'delays': initial['delays'], 'dopplers': initial['dopplers'],
             'gains': initial['gains'], 'mu': np.zeros(1024, complex),
             'v': np.full(1024, .5), 'prior': np.zeros(2048)}
    arrays = {}
    events = []
    for round_index in range(2):
        begin = time.perf_counter()
        channel, detail = time_refine_keep_slots(
            observation['y'], observation['pilot'], state['mu'], state['v'],
            state['delays'], state['dopplers'], state['gains'], system.c1, system.c2,
            observation['sigma2'], mode='soft', max_paths=cap, rounds=2)
        if not np.array_equal(channel.delays, state['delays']) or channel.p != len(state['delays']):
            raise AssertionError('F1 physical slots changed before TF')
        refit_end = time.perf_counter()
        detector = scalar_joint(observation['y'], observation['pilot'], channel,
            observation['sigma2'], pd=.5, prior=state['prior'], iterations=20,
            damping=.3, gain_mode='joint', record_states=record_states)
        tf_end = time.perf_counter()
        decoder = decoder_messages(code, np.clip(detector['extrinsic'], -20, 20), maxiter=50)
        decoder_end = time.perf_counter()
        state['prior'] = np.clip(decoder['raw_check_extrinsic'], -20, 20)
        state['mu'], state['v'], _ = moments(np.clip(decoder['raw_app'], -20, 20), .5)
        state['delays'] = channel.delays
        state['dopplers'] = channel.dopplers
        state['gains'] = detector['gains']
        event = dict(round=round_index, ce=refit_end-begin, inference=tf_end-refit_end,
                     decoder=decoder_end-tf_end, ready=decoder_end-start,
                     decoder_iterations=int(decoder['iterations']), inference_iterations=20,
                     ce_evaluations=detail['evaluations'], inference_fft_count=detector['fft_count'],
                     ce_fft_count=detail['fft_count'])
        events.append(event)
        snapshot = {'decoded': decoder['decoded'], 'input_llr': decoder['incoming_llr'],
                    'app': decoder['raw_app'], 'check': decoder['raw_check_extrinsic'],
                    'delays': channel.delays, 'dopplers': channel.dopplers,
                    'gains': detector['gains'], 'gain_variance': detector['gain_variance'],
                    'ce_gains': channel.gains, 'mu': detector['mu'],
                    'variance': detector['variance'], 'ce_history': np.array(detail['history']),
                    'ce_gamma': detail['gamma'], 'inference_trace': detector['trace']}
        if record_states:
            snapshot['inference_states'] = detector['states']
        arrays.update({f'r{round_index}_{key}': value for key, value in snapshot.items()})
        if checkpoint_sink is not None:
            checkpoint_sink(dict(event, snapshot=snapshot), decoder['decoded'].copy())
    return decoder, arrays, dict(seconds=time.perf_counter()-start,
        pilot_seconds=acquisition_end-start, events=events, acquisition=initial,
        initial_geometry={'delays': initial['delays'], 'dopplers': initial['dopplers'],
                          'gains': initial['gains']},
        entering_geometry={'delays': arrays['r1_delays'], 'dopplers': arrays['r1_dopplers'],
                           'gains': arrays['r1_gains']})
