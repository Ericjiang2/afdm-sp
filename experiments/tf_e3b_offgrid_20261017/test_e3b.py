#!/usr/bin/env python
"""E-3b unit gates (numpy / scipy only; no receiver context, no data).

  G2  refinement correctness
        a  one path with a fractional Doppler, v = 0, Y built independently with Channel.apply: the refined Doppler error is < 1e-3 (6 Doppler values)
        b  every refinement keeps the value monotone non-increasing, <= 16 evaluations per coordinate, Dopplers in [-3, 3] and inside the +-.5 window
        c  v = 0: _system's gamma is exactly 0 in both gamma modes; v > 0: 'diag' keeps only the diagonal (= sum v), 'full' differs
        d  strict decrease: a flat objective (Y = 0) accepts nothing and moves nothing
  G3  determinism: refine() twice on the same input -> bitwise identical (arrays, floats); the real-key two-run check is in e3b_driver.py gate
  K   key sets: 2400 main keys, 20 gate keys, 16 smoke keys on frames >= 8300 (>= 2 per SNR), contiguous exact shard partition
  C   cost-check projection
Usage: python test_e3b.py [--out DIR]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import e3b_lib as lib  # noqa: E402

import offgrid_refine as ref  # noqa: E402
from geometry_reopen_variant import Path as GPath, _system  # noqa: E402
from physical import Channel, daft  # noqa: E402


def system_like(n):
    return 7.0 / (2 * n), 1.0 / (16 * n)


def synth(n, delays, dopplers, gains, seed, noise=0.):
    """(Y, xt, x) with Y = daft(Channel.apply(x), inverse) built independently of the _responses used by the objective."""
    c1, c2 = system_like(n)
    rng = np.random.default_rng(seed)
    pilot = np.exp(2j * np.pi * rng.random(n)) * .5
    data = (rng.choice([-1., 1.], n) + 1j * rng.choice([-1., 1.], n)) * .5
    x = pilot + data
    ch = Channel(n, c1, c2, delays, dopplers, gains)
    y = ch.apply(x)
    if noise:
        y = y + noise * (rng.normal(size=n) + 1j * rng.normal(size=n)) / np.sqrt(2)
    return daft(y, c1, c2, True), daft(x, c1, c2, True), x


def nearest_grid(x, step=.25):
    return float(np.round(x / step) * step)


# ----------------------------------------------------------------------------- G2
def g2_single_path():
    n = 256
    c1, c2 = system_like(n)
    errs, accepted = [], []
    for k, nu0 in enumerate((.37, -1.13, 2.61, 0.11, -2.9, 1.5 + .0625)):
        Y, xt, _ = synth(n, [5], [nu0], [.8 + .3j], seed=100 + k)
        r = ref.refine(Y, xt, np.zeros(n), [5], [nearest_grid(nu0)], c1, c2, ridge=1e-6, gamma_mode='full')
        errs.append(abs(float(r['dopplers'][0]) - nu0))
        accepted.append(r['n_accept'])
        assert r['monotone'] and r['max_evals_coord'] <= ref.MAX_EVALS and r['in_bounds'] and r['in_window']
    worst = max(errs)
    assert worst < 1e-3, f'G2a: worst Doppler error {worst}'
    # the same with weak noise (information only, not a gate)
    noisy = []
    for k, nu0 in enumerate((.37, -1.13, 2.61)):
        Y, xt, _ = synth(n, [5], [nu0], [.8 + .3j], seed=200 + k, noise=.02)
        r = ref.refine(Y, xt, np.zeros(n), [5], [nearest_grid(nu0)], c1, c2, ridge=4e-4, gamma_mode='full')
        noisy.append(abs(float(r['dopplers'][0]) - nu0))
    return dict(errors=errs, worst_error=worst, accepted_coordinates=accepted, noisy_errors_info_only=noisy, tolerance=1e-3)


def g2_multi_and_codelay():
    n = 256
    c1, c2 = system_like(n)
    delays = [3, 3, 9, 20]
    nus = [.37, 1.81, -1.13, 2.61]
    Y, xt, _ = synth(n, delays, nus, [.9, .5j, -.6, .4 + .2j], seed=7)
    start = [nearest_grid(x) for x in nus]
    r = ref.refine(Y, xt, np.zeros(n), delays, start, c1, c2, ridge=1e-6, gamma_mode='full')
    assert r['monotone'] and r['value_recheck_equal'] and r['max_evals_coord'] <= ref.MAX_EVALS and r['in_bounds'] and r['in_window']
    assert r['value_after'] < r['value_before']
    err = float(np.max(np.abs(r['dopplers'] - np.asarray(nus))))
    # noisy data with v > 0 in both gamma modes, co-delay atoms starting close together (no guard: they may approach)
    rng = np.random.default_rng(3)
    v = .1 + .2 * rng.random(n)
    Yn, xtn, _ = synth(n, delays, nus, [.9, .5j, -.6, .4 + .2j], seed=8, noise=.05)
    out = dict(error_noise_free=err, value_before=r['value_before'], value_after=r['value_after'], n_accept=r['n_accept'], evals=r['evals'], variants={})
    for gm in ('diag', 'full'):
        rn = ref.refine(Yn, xtn, v, [3, 3, 9, 20], [.25, .5, -1.25, 2.5], c1, c2, ridge=2.5e-3, gamma_mode=gm)
        assert rn['monotone'] and rn['max_evals_coord'] <= ref.MAX_EVALS and rn['in_bounds'] and rn['in_window'] and np.isfinite(rn['gains']).all()
        out['variants'][gm] = dict(value_before=rn['value_before'], value_after=rn['value_after'], n_accept=rn['n_accept'], dopplers=[float(x) for x in rn['dopplers']],
                                   gamma_offdiag_abs_max=rn['gamma_offdiag_abs_max'], gamma_diag_rel_err=rn['gamma_diag_rel_err'], cond_Q=rn['cond_Q'])
    assert out['variants']['diag']['gamma_offdiag_abs_max'] == 0.0 and out['variants']['full']['gamma_offdiag_abs_max'] > 0
    assert out['variants']['diag']['gamma_diag_rel_err'] < 1e-12 and out['variants']['full']['gamma_diag_rel_err'] < 1e-12
    # near-coincident same-delay atoms (1e-7 apart) with a small ridge: _system must not raise (the ridge keeps Q positive definite)
    rc = ref.refine(Yn, xtn, v, [3, 3], [.37, .37 + 1e-7], c1, c2, ridge=2.5e-3, gamma_mode='full')
    assert rc['monotone'] and np.isfinite(rc['gains']).all()
    out['near_coincident'] = dict(dopplers=[float(x) for x in rc['dopplers']], cond_Q=rc['cond_Q'])
    return out


def g2_gamma_zero():
    n = 256
    c1, c2 = system_like(n)
    Y, xt, _ = synth(n, [3, 3, 9], [.37, 1.81, -1.13], [.9, .5j, -.6], seed=9)
    paths = [GPath(3, .4), GPath(3, 1.7), GPath(9, -1.0), GPath(9, -1.0 + 1e-6)]
    worst = 0.
    for gm in ('diag', 'full'):
        gamma = _system(Y, xt, np.zeros(n), paths, c1, c2, 1e-3, gm)[5]
        assert np.all(gamma == 0), f'G2c: gamma not exactly zero ({gm})'
        worst = max(worst, float(np.max(np.abs(gamma))))
    v = .1 + .05 * np.arange(n) / n
    gd_, gf_ = (_system(Y, xt, v, paths, c1, c2, 1e-3, gm)[5] for gm in ('diag', 'full'))
    assert np.max(np.abs(gd_ - np.diag(np.diag(gd_)))) == 0 and np.max(np.abs(gf_ - np.diag(np.diag(gf_)))) > 0
    assert np.allclose(np.diag(gd_).real, v.sum(), rtol=1e-12) and np.allclose(np.diag(gf_).real, v.sum(), rtol=1e-12)
    return dict(zero_v_gamma_abs_max=worst, diag_equals_sum_v=True, full_has_offdiagonal=True)


def g2_strict_decrease():
    n = 256
    c1, c2 = system_like(n)
    _, xt, _ = synth(n, [3], [.4], [1.], seed=11)
    r = ref.refine(np.zeros(n, complex), xt, np.zeros(n), [3, 8], [.25, -1.], c1, c2, ridge=1e-3, gamma_mode='full')
    assert r['n_accept'] == 0 and list(r['dopplers']) == [.25, -1.] and r['value_before'] == r['value_after'] == 0.0 and r['monotone']
    # window at the Doppler boundary stays inside [-3, 3] and inside +-.5 of the start
    Y, xtb, _ = synth(n, [4], [2.93], [.7], seed=12)
    rb = ref.refine(Y, xtb, np.zeros(n), [4], [3.0], c1, c2, ridge=1e-6, gamma_mode='full')
    assert rb['in_bounds'] and rb['in_window'] and rb['dopplers'][0] <= 3.0 and abs(rb['dopplers'][0] - 2.93) < 1e-3
    return dict(flat_objective_accepts=r['n_accept'], boundary_final_doppler=float(rb['dopplers'][0]))


# ----------------------------------------------------------------------------- G3
def g3_determinism():
    n = 256
    c1, c2 = system_like(n)
    delays = [3, 3, 9, 20]
    Y, xt, _ = synth(n, delays, [.37, 1.81, -1.13, 2.61], [.9, .5j, -.6, .4 + .2j], seed=13, noise=.05)
    v = .1 + .2 * np.random.default_rng(5).random(n)
    results = []
    for gm in ('diag', 'full'):
        a = ref.refine(Y, xt, v, delays, [.25, 1.75, -1.25, 2.5], c1, c2, 2.5e-3, gm)
        b = ref.refine(Y, xt, v, delays, [.25, 1.75, -1.25, 2.5], c1, c2, 2.5e-3, gm)
        diff = lib.deep_equal(a, b)
        assert not diff, diff
        results.append(gm)
    return dict(identical_modes=results)


# ----------------------------------------------------------------------------- K, C
def keys_and_blocks():
    main = lib.main_keys()
    assert len(main) == 2400 == lib.N_KEYS and len(set(main)) == 2400
    assert {k[0] for k in main} == {'U', 'G'} and {k[1] for k in main} == {300} and {k[2] for k in main} == set(range(600, 1101, 100))
    assert min(k[3] for k in main) == 4000 and max(k[3] for k in main) == 4199
    gate = lib.gate_keys()
    assert len(gate) == 20 and len(set(gate)) == 20 and set(gate) <= set(main) and gate == lib.gate_keys()
    smoke = lib.smoke_keys()
    assert len(smoke) == 16 and len(set(smoke)) == 16 and min(k[3] for k in smoke) >= 8300 and not set(smoke) & set(main)
    for snr in lib.SNRS:
        assert sum(k[2] == snr for k in smoke) >= 2 and {k[0] for k in smoke if k[2] == snr} == {'U', 'G'}
    for nshard in (16, 20, 23, 24):
        blocks = [lib.shard_block(main, s, nshard) for s in range(nshard)]
        assert sum(blocks, []) == main and max(map(len, blocks)) - min(map(len, blocks)) <= 1
    assert [len(lib.shard_block(main, s, 24)) for s in range(24)] == [100] * 24
    return dict(main=len(main), gate=len(gate), smoke=len(smoke), smoke_snr_counts={s: sum(k[2] == s for k in smoke) for s in lib.SNRS},
                gate_keys=[list(k) for k in gate])


def cost_check_projection():
    import e3b_driver as drv
    rows = [dict(variants={}, seconds=dict(total=20.), gen_seconds=.2) for _ in range(5)] + [dict(status='error')]
    proj = drv.projected_core_hours(rows, 2400)
    assert abs(proj - 20.2 * 2400 / 3600) < 1e-12 and drv.projected_core_hours([dict(status='error')], 2400) is None
    assert 13.4 < proj < 13.5
    return dict(projected=proj)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--out', type=Path, default=None)
    a = p.parse_args()
    res = {}
    for name, fn in (('G2a_single_path', g2_single_path), ('G2b_multi_codelay', g2_multi_and_codelay), ('G2c_gamma', g2_gamma_zero),
                     ('G2d_strict_window', g2_strict_decrease), ('G3_determinism', g3_determinism), ('K_keys', keys_and_blocks), ('C_cost_check', cost_check_projection)):
        res[name] = fn()
        print(f'{name}: ok')
    res['G2'] = dict(pass_=True, single_path_worst_error=res['G2a_single_path']['worst_error'], tolerance=1e-3,
                     zero_v_gamma_abs_max=res['G2c_gamma']['zero_v_gamma_abs_max'], monotone_checked=True, evals_cap_checked=True)
    res['G3'] = dict(pass_=True, identical_modes=res['G3_determinism']['identical_modes'])
    if a.out:
        a.out.mkdir(parents=True, exist_ok=True)
        (a.out / 'test_e3b.json').write_text(json.dumps(res, indent=1) + '\n')
    print(json.dumps({k: res[k] for k in ('G2', 'G3')}, indent=1))


if __name__ == '__main__':
    main()
