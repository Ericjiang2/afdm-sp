#!/usr/bin/env python
"""E-1 unit gates on synthetic states (numpy/scipy only; no receiver context, no data):

  T0  source diff    variant == frozen + gamma_mode additions only (both files)
  T1  C1 assertion   diag(projected_variance) == sum(v) (to 1e-10 rel) for every path set; diag _gamma_cross == 0;
                     diag _system gamma == (sum v) I; full _gamma_cross / _system bitwise equal to frozen
  T2  G1 (synthetic) variant gamma_mode='full' bitwise equal to frozen reopen_geometry on 64 synthetic states, 5 configurations
  T3  G2 (synthetic) diag mode: off-diagonals zero, diagonal == sum(v) on the returned diagnostics; full vs diag differ;
                     compact vs direct strategy agree in diag mode (top-1 candidate, edits, scores within 1e-8 rel)
  T4  G3             every geometry arm configuration run twice -> bitwise equal
The real-P1-state versions of G1-G4 run in e1_driver.py --mode gate (they need the receiver context, available on deinlab only).
Usage: python test_variant.py [--out DIR] [--states 64]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import e1_lib  # noqa: E402

e1_lib.prepare_paths()
import geometry_reopen as old_reopen  # noqa: E402  (frozen)
import geometry_validation as old_val  # noqa: E402  (frozen)
import geometry_reopen_variant as new_reopen  # noqa: E402
import geometry_validation_variant as new_val  # noqa: E402
from physical import Channel, daft, projected_variance  # noqa: E402

EXPERIMENTS = HERE.parent
N, P_PATHS, MAX_DELAY = 128, 6, 31

# geometry configurations of arms A1-A4, A6 (A5 has no geometry call)
CONFIGS = {'A1': ('full', 2, 2), 'A2': ('diag', 2, 2), 'A3': ('full', 0, 2), 'A4': ('diag', 0, 2), 'A6': ('full', 0, 0)}


def synth(seed, n=N, P=P_PATHS, snr_db=6.0, max_delay=MAX_DELAY):
    """Synthetic F0-like state: structured per-symbol variance v, a wrong-delay path, perturbed Dopplers."""
    rng = np.random.default_rng(seed)
    c1, c2 = 7.0 / (2 * n), 1.0 / (16 * n)
    delays = np.sort(rng.choice(max_delay + 1, P, replace=False))
    dopp = rng.uniform(-2, 2, P)
    gains = (rng.normal(size=P) + 1j * rng.normal(size=P)) / np.sqrt(2 * P)
    chan = Channel(n, c1, c2, delays, dopp, gains)
    x_true = (rng.choice([-1., 1.], n) + 1j * rng.choice([-1., 1.], n)) / 2
    clean = chan.apply(x_true)
    sigma2 = float(np.mean(abs(clean) ** 2) / 10 ** (snr_db / 10))
    y = clean + np.sqrt(sigma2 / 2) * (rng.normal(size=n) + 1j * rng.normal(size=n))
    v = .05 + .4 * (rng.random(n) < .25)
    x_mean = x_true * (1 - 2 * v)
    init_delays = delays.copy()
    pool = np.setdiff1d(np.arange(max_delay + 1), delays)
    init_delays[rng.integers(P)] = rng.choice(pool)
    init_dopp = np.clip(dopp + rng.normal(0, .25, P), -3, 3)
    return dict(Y=daft(y, c1, c2, True), x=x_mean, v=v, delays=[int(d) for d in init_delays],
                dopplers=[float(d) for d in init_dopp], c1=c1, c2=c2, ridge=sigma2)


def kwargs(state, mod, max_edits, local_passes, **extra):
    paths = [mod.Path(d, nu) for d, nu in zip(state['delays'], state['dopplers'])]
    return (state['Y'], state['x'], state['v'], paths), dict(
        c1=state['c1'], c2=state['c2'], ridge=state['ridge'], max_delay=MAX_DELAY, doppler_min=-3., doppler_max=3.,
        grid_step=.25, max_edits=max_edits, chunk_size=64, local_passes=local_passes, local_halfwidth=.75,
        local_max_evals=16, duplicate_tolerance=1e-6, top_k=20, **extra)


def run_val(mod, state, max_edits, local_passes, **extra):
    a, k = kwargs(state, mod, max_edits, local_passes, **extra)
    return mod.reopen_geometry(*a, **k)


def run_reopen(mod, state, max_edits, local_passes, **extra):
    a, k = kwargs(state, mod, max_edits, local_passes, **extra)
    return mod.reopen_geometry(*a, **k)


def delay_set(result):
    return sorted(p.delay for p in result.paths)


def edit_sig(result):
    return [(e['step'], e['slot'], e['new']['delay'], e['new']['doppler']) for e in result.edits]


def top1(result):
    return None if not result.global_trace else (result.global_trace[0]['selected']['slot'],
                                                  result.global_trace[0]['selected']['replacement']['delay'],
                                                  result.global_trace[0]['selected']['replacement']['doppler'])


# ----------------------------------------------------------------------------- tests
def t0_source_diff():
    pairs = {'geometry_reopen_variant.py': EXPERIMENTS / 'tf_geometry_reopen_20260922' / 'geometry_reopen.py',
             'geometry_validation_variant.py': EXPERIMENTS / 'tf_cstate_validation_20260922' / 'geometry_validation.py'}
    out = {}
    for variant, frozen in pairs.items():
        problems = e1_lib.variant_diff_problems(frozen, HERE / variant)
        out[variant] = dict(frozen_md5=e1_lib.md5_file(frozen), variant_md5=e1_lib.md5_file(HERE / variant), problems=problems)
        assert not problems, f'T0 {variant}: {problems}'
    return out


def t1_c1_assertion(states):
    rng = np.random.default_rng(12345)
    worst_rel, n_checked, bitwise_cross, bitwise_system = 0., 0, 0, 0
    for i, s in enumerate(states):
        v = s['v']
        # (a) C1 on random path sets (including same-delay doublets and large P)
        for _ in range(4):
            p = int(rng.integers(1, 9))
            delays = rng.integers(0, MAX_DELAY + 1, p)
            dopp = rng.uniform(-3, 3, p)
            g = projected_variance(v, delays, dopp, s['c1'])
            d = np.diag(g)
            assert np.all(d.imag == 0), 'T1: projected_variance diagonal not real'
            rel = float(np.max(abs(d.real - v.sum()) / v.sum()))
            worst_rel = max(worst_rel, rel)
            n_checked += 1
            assert rel < 1e-10, f'T1 C1 FAILED: diag(projected_variance) != sum(v), rel {rel}'
        # (b) _gamma_cross: diag -> zeros; full -> bitwise frozen
        cur = [new_reopen.Path(d, nu) for d, nu in zip(s['delays'], s['dopplers'])]
        cand = [new_reopen.Path(int(d), float(nu)) for d, nu in zip(rng.integers(0, MAX_DELAY + 1, 40), rng.uniform(-3, 3, 40))]
        cur_old = [old_reopen.Path(p.delay, p.doppler) for p in cur]
        cand_old = [old_reopen.Path(p.delay, p.doppler) for p in cand]
        vf = np.fft.fft(v)
        z = new_reopen._gamma_cross(cur, cand, vf, s['c1'], gamma_mode='diag')
        assert z.shape == (len(cur), len(cand)) and not z.any(), 'T1: diag _gamma_cross not zero'
        f_new = new_reopen._gamma_cross(cur, cand, vf, s['c1'])
        f_old = old_reopen._gamma_cross(cur_old, cand_old, vf, s['c1'])
        assert f_new.tobytes() == f_old.tobytes(), 'T1: full _gamma_cross differs from frozen'
        bitwise_cross += 1
        # (c) _system
        xt = daft(s['x'], s['c1'], s['c2'], inverse=True)
        a_old = old_reopen._system(s['Y'], xt, v, cur_old, s['c1'], s['c2'], s['ridge'])
        a_new = new_reopen._system(s['Y'], xt, v, cur, s['c1'], s['c2'], s['ridge'])
        assert not e1_lib.deep_equal(list(a_old), list(a_new)), 'T1: full _system differs from frozen'
        bitwise_system += 1
        a_diag = new_reopen._system(s['Y'], xt, v, cur, s['c1'], s['c2'], s['ridge'], gamma_mode='diag')
        gam = a_diag[5]
        assert np.array_equal(gam - np.diag(np.diag(gam)), np.zeros_like(gam)), 'T1: diag gamma has off-diagonals'
        assert np.allclose(np.diag(gam).real, v.sum(), rtol=1e-10, atol=0), 'T1: diag gamma != sum(v)'
        full_g = a_new[5]
        assert np.allclose(np.diag(gam), np.diag(full_g), rtol=1e-12, atol=0), 'T1: diag gamma != diagonal of full gamma'
    return dict(c1_worst_relative_error=worst_rel, c1_path_sets_checked=n_checked, gamma_cross_full_bitwise_states=bitwise_cross,
                system_full_bitwise_states=bitwise_system)


def t2_g1(states):
    cfgs = {'compact_e2_l2': ('val', 'compact', 2, 2), 'compact_e0_l2': ('val', 'compact', 0, 2),
            'compact_e0_l0': ('val', 'compact', 0, 0), 'direct_e2_l2': ('val', 'direct', 2, 2),
            'old_kernel_e2_l2': ('old', None, 2, 2)}
    out = {}
    for name, (which, strategy, me, lp) in cfgs.items():
        n_ok, bad = 0, []
        for i, s in enumerate(states):
            if which == 'val':
                ref = run_val(old_val, s, me, lp, strategy=strategy)
                got = run_val(new_val, s, me, lp, strategy=strategy, gamma_mode='full')
                got_default = run_val(new_val, s, me, lp, strategy=strategy)
            else:
                ref = run_reopen(old_reopen, s, me, lp)
                got = run_reopen(new_reopen, s, me, lp, gamma_mode='full')
                got_default = run_reopen(new_reopen, s, me, lp)
            diff = e1_lib.deep_equal(ref, got) + e1_lib.deep_equal(ref, got_default)
            if diff:
                bad.append((i, diff[:3]))
            else:
                n_ok += 1
        out[name] = dict(states=len(states), identical=n_ok, mismatches=bad[:3])
        assert n_ok == len(states), f'T2 G1 FAILED ({name}): {bad[:2]}'
    return out


def t3_g2(states):
    out = dict(states=len(states), gains_differ=0, support_differs=0, edits_differ=0, top1_differs=0, any_decision_differs=0,
               diag_gamma_offdiag_max=0., diag_gamma_diag_rel_err=0., compact_direct_agree=0, accepted_edits_full=0, accepted_edits_diag=0,
               nonidentical_compact_vs_direct=[])
    for i, s in enumerate(states):
        full = run_val(new_val, s, 2, 2, strategy='compact', gamma_mode='full')
        diag = run_val(new_val, s, 2, 2, strategy='compact', gamma_mode='diag')
        g = diag.diagnostics['gamma']
        out['diag_gamma_offdiag_max'] = max(out['diag_gamma_offdiag_max'], float(np.max(abs(g - np.diag(np.diag(g))))))
        out['diag_gamma_diag_rel_err'] = max(out['diag_gamma_diag_rel_err'],
                                             float(np.max(abs(np.diag(g).real - s['v'].sum()) / s['v'].sum())))
        out['gains_differ'] += int(full.gains.tobytes() != diag.gains.tobytes())
        out['support_differs'] += int(delay_set(full) != delay_set(diag))
        out['edits_differ'] += int(edit_sig(full) != edit_sig(diag))
        out['top1_differs'] += int(top1(full) != top1(diag))
        out['any_decision_differs'] += int(delay_set(full) != delay_set(diag) or edit_sig(full) != edit_sig(diag)
                                           or top1(full) != top1(diag))
        out['accepted_edits_full'] += len(full.edits)
        out['accepted_edits_diag'] += len(diag.edits)
        # compact vs direct consistency in diag mode (step-1 score grids)
        dd = run_val(new_val, s, 2, 2, strategy='direct', gamma_mode='diag')
        a, b = diag.global_trace[0], dd.global_trace[0]
        rel = float(np.max(abs(a['scores'] - b['scores']) / (1 + abs(b['scores']))))
        same = top1(diag) == top1(dd) and edit_sig(diag) == edit_sig(dd)
        out['compact_direct_agree'] += int(same and rel < 1e-8)
        if not (same and rel < 1e-8):
            out['nonidentical_compact_vs_direct'].append((i, rel, top1(diag), top1(dd)))
    out['nonidentical_compact_vs_direct'] = out['nonidentical_compact_vs_direct'][:5]
    assert out['diag_gamma_offdiag_max'] == 0., 'T3: diag gamma has off-diagonals'
    assert out['diag_gamma_diag_rel_err'] < 1e-10, 'T3: diag gamma diagonal != sum(v)'
    assert out['gains_differ'] == len(states), 'T3: diag gains identical to full on some synthetic states'
    need = 8 if len(states) >= 32 else 1
    assert out['any_decision_differs'] >= need, f"T3: diag differs from full on only {out['any_decision_differs']} decisions"
    assert out['compact_direct_agree'] == len(states), f"T3: compact vs direct disagree in diag mode {out['nonidentical_compact_vs_direct']}"
    return out


def t4_g3(states):
    out = {}
    for arm, (gm, me, lp) in CONFIGS.items():
        n_ok, bad = 0, []
        for i, s in enumerate(states):
            r1 = run_val(new_val, s, me, lp, strategy='compact', gamma_mode=gm)
            r2 = run_val(new_val, s, me, lp, strategy='compact', gamma_mode=gm)
            diff = e1_lib.deep_equal(r1, r2)
            n_ok += int(not diff)
            if diff:
                bad.append((i, diff[:2]))
        out[arm] = dict(states=len(states), identical=n_ok, mismatches=bad[:3])
        assert n_ok == len(states), f'T4 G3 FAILED ({arm}): {bad[:2]}'
    return out


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument('--out', type=Path, default=HERE / 'out' / 'unit')
    p.add_argument('--states', type=int, default=64)
    a = p.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    t0 = time.perf_counter()
    states = [synth(1000 + i, snr_db=4.0 + (i % 5) * 1.5) for i in range(a.states)]
    result = dict(n_synthetic_states=a.states, n=N, paths=P_PATHS, max_delay=MAX_DELAY,
                  note='synthetic states; real-P1-state G1-G4 are in e1_driver.py --mode gate')
    for name, fn, arg in (('T0_source_diff', t0_source_diff, None), ('T1_c1_assertion', t1_c1_assertion, states),
                          ('T2_G1_full_bitwise_frozen', t2_g1, states), ('T3_G2_diag', t3_g2, states), ('T4_G3_determinism', t4_g3, states)):
        s = time.perf_counter()
        result[name] = fn() if arg is None else fn(arg)
        result[name]['seconds'] = time.perf_counter() - s
        print(f'{name}: PASS ({result[name]["seconds"]:.1f}s)', flush=True)
    result['all_pass'] = True
    result['total_seconds'] = time.perf_counter() - t0
    (a.out / 'test_variant.json').write_text(json.dumps(result, indent=1, default=str) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k.startswith('T3')}, indent=1, default=str))
    print('ALL PASS')


if __name__ == '__main__':
    main()
