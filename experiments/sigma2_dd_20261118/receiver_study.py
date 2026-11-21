"""Paired B and fixed-true-channel A3 paths on one supplied P1 observation."""

import importlib
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
CAP = 8
RHO = .3
SCENARIO = 'G'
ARMS = ('known', 'SF', 'DD')


def load(frozen_slot):
    sys.path.insert(0, str(frozen_slot))
    q = importlib.import_module('qualify_v2')
    ctx, variant, _, closed, source_parity = q.load()
    dd = importlib.import_module('native_dd')
    return q, ctx, variant, dd, closed, source_parity


def evaluate_b(study, method, actual, truth):
    q, ctx, variant, dd, closed, _ = study
    sm = q.sm
    obs, noise = q.observe_only(actual, method != 'known')
    if method == 'DD':
        dec, arrays, timing = dd.receive(obs, ctx.system, ctx.code, max_paths=CAP)
        update = timing['noise_update']
        noise = dict(update, first_round=noise)
        obs = dict(obs, sigma2=update['estimate'])
        syndrome = int(ctx.hd.syndrome_weight(ctx, dec['decoded']))
    else:
        dec, arrays, syndrome, _ = sm.f0_state(ctx, variant, obs, CAP)

    delays = arrays['r1_delays'].tolist()
    f0 = dict(syndrome=syndrome, info_errors=sm.gd.score(ctx, dec['decoded'], truth),
              slot_count=len(delays), slot_count_r0=len(arrays['r0_delays']),
              r1_delays=delays, r1_dopplers=arrays['r1_dopplers'].tolist())
    a1c = None
    if syndrome:
        continuation = sm.e1d.run_branch(ctx, closed, obs, arrays, 'A1')
        result = continuation['result']
        support = delays.copy()
        true_delays = set(truth['l_i'])
        edits = []
        for edit in result.edits:
            slot, old, new = int(edit['slot']), edit['old'], edit['new']
            if support[slot] != old['delay']:
                raise ValueError('Edit does not match its entering slot')
            phantom = new['delay'] in support[:slot] + support[slot + 1:]
            edits.append(dict(step=int(edit['step']), slot=slot, old=old, new=new,
                              phantom=phantom, dropped_true=old['delay'] in true_delays))
            support[slot] = new['delay']
        a1c = dict(edits=edits,
                   final_delays=[int(p.delay) for p in result.paths],
                   final_dopplers=[float(p.doppler) for p in result.paths],
                   info_errors=sm.gd.score(ctx, continuation['decoder']['decoded'], truth))
        if a1c['final_delays'] != support:
            raise ValueError('Edits do not reproduce final support')
    if noise is not None:
        noise['ratio'] = obs['sigma2'] / float(actual['sigma2'])
    return dict(f0=f0, a1c=a1c, info_errors=(a1c or f0)['info_errors'], noise=noise,
                round1_delays=arrays['r0_delays'].tolist(),
                round1_dopplers=arrays['r0_dopplers'].tolist()), obs, arrays


def evaluate_a3(study, obs, truth):
    q, ctx = study[:2]
    row = q.sm.p1ctx.p1_driver.compute_arms(ctx, obs, truth, ['A3'])['A3']
    if row['status'] != 'ok':
        raise RuntimeError(row)
    return row
