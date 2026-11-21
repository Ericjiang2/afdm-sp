#!/usr/bin/env python
"""E-2 unit gates (numpy/scipy only; no receiver context, no data).  Synthetic parts of the design.md gates:

  T0   source diff     geometry_validation_guard.py == E-1 variant + codelay_guard additions only
  T1   predicates      codelay_guard: vectorised conflict_matrix / hits_group vs brute force; |D_N| limit and value
  G1   (synthetic)     codelay_guard='off' bitwise equal to the E-1 variant (5 configurations x 64 states, incl. gamma diag/full)
  G2   (synthetic)     guard invariants in compact AND direct paths (all / neardup, full and diag), compact == direct masks,
                       local Doppler refinement cannot drift a legal pair into |D_N| >= .5 (dedicated co-delay states), A2g != A2
  G3   (synthetic)     every guarded/unguarded geometry configuration run twice -> bitwise equal
  CG0  copy == frozen  draw_cluster_geometry / cluster_paths equal the frozen headroom functions when domain = CLUS (20 frames)
  CG1  power           ||H||_F^2/N = 1 within 1e-9 on 50 E2CJ frames after the numeric renormalisation
  CG2  operator        physical.Channel.apply == D T D^-1 (independent dense time-domain matrix) to 1e-9 on 20 E2CJ frames
  CG3  (descriptive)   fraction of J4 taps with >= 2 rays over the 1000 main frames; the pipeline-level CG3 (rest of the P1 frame is
                       channel-independent) and the context-level CG1/CG2 (physical_channel_matrix) run in e2_driver.py --mode cgate.
Usage: python test_e2.py [--out DIR] [--states 64]
"""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import sys
import time

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import e2_lib  # noqa: E402

e2_lib.prepare_paths()
import codelay_guard as cg  # noqa: E402
import e2_channels as ch  # noqa: E402
import geometry_reopen_variant as e1_reopen  # noqa: E402  (E-1 variant, frozen)
import geometry_validation_variant as e1_val  # noqa: E402  (E-1 variant, frozen)
import geometry_validation_guard as e2_val  # noqa: E402
import test_variant as e1t  # noqa: E402  (E-1 synthetic state generator, frozen)
from physical import Channel, daft  # noqa: E402

EXPERIMENTS = HERE.parent
N1024, C1, C2 = 1024, 0.004395, 1.98e-07
# (name, gamma_mode, max_edits, local_passes, strategy, guard)
GUARD_CONFIGS = {
    'A1': ('full', 2, 2, 'compact', 'off'), 'A2': ('diag', 2, 2, 'compact', 'off'), 'A3': ('full', 0, 2, 'compact', 'off'),
    'A1g': ('full', 2, 2, 'compact', 'all'), 'A2g': ('diag', 2, 2, 'compact', 'all'), 'A2n': ('diag', 2, 2, 'compact', 'neardup')}


def run_e2(state, gamma, edits, passes, strategy, guard, **kw):
    a, k = e1t.kwargs(state, e2_val, edits, passes, strategy=strategy, gamma_mode=gamma, codelay_guard=guard, **kw)
    return e2_val.reopen_geometry(*a, **k)


def run_e1(state, gamma, edits, passes, strategy):
    a, k = e1t.kwargs(state, e1_val, edits, passes, strategy=strategy, gamma_mode=gamma)
    return e1_val.reopen_geometry(*a, **k)


def codelay_pairs(result, n):
    """(delay, |D_N|) of every same-delay pair in the final geometry."""
    out = []
    p = result.paths
    for i in range(len(p)):
        for j in range(i + 1, len(p)):
            if p[i].delay == p[j].delay:
                out.append((p[i].delay, float(cg.abs_dn(p[i].doppler - p[j].doppler, n))))
    return out


def guard_satisfied(result, n, guard):
    pairs = codelay_pairs(result, n)
    if guard == 'all':
        return not pairs
    if guard == 'neardup':
        return all(d < cg.NEARDUP_THRESHOLD for _, d in pairs)
    return True


# ----------------------------------------------------------------------------- tests
def t0_source_diff():
    e1 = EXPERIMENTS / 'tf_cstate_e1_20261017' / 'geometry_validation_variant.py'
    e2 = HERE / 'geometry_validation_guard.py'
    problems = e2_lib.guard_diff_problems(e1, e2)
    assert not problems, f'T0: {problems}'
    return dict(e1_variant_md5=e2_lib.md5_file(e1), e2_guard_md5=e2_lib.md5_file(e2), problems=problems)


def t1_predicates():
    rng = np.random.default_rng(7)
    assert cg.abs_dn(np.array([0.]), 1024)[0] == 1.0
    x = .5
    assert abs(cg.abs_dn(np.array([x]), 1024)[0] - abs(np.sin(np.pi * x) / (1024 * np.sin(np.pi * x / 1024)))) < 1e-15
    # |D_N(x)| >= .5  <=>  |x| <~ 0.6 (monotone on [0, 1]); pin the bracket
    assert cg.abs_dn(np.array([.55]), 1024)[0] >= .5 > cg.abs_dn(np.array([.65]), 1024)[0]
    bad = 0
    n_checks = 0
    for mode in ('off', 'all', 'neardup'):
        for _ in range(200):
            P, C = int(rng.integers(1, 9)), int(rng.integers(1, 60))
            cd = rng.integers(0, 6, P)
            cn = rng.uniform(-3, 3, P)
            ld = rng.integers(0, 6, C)
            ln = rng.uniform(-3, 3, C)
            got = cg.conflict_matrix(cd, cn, ld, ln, 1024, mode)
            ref = np.zeros((P, C), bool)
            if mode != 'off':
                for i in range(P):
                    for j in range(C):
                        if cd[i] == ld[j]:
                            ref[i, j] = True if mode == 'all' else cg.abs_dn(np.array([ln[j] - cn[i]]), 1024)[0] >= cg.NEARDUP_THRESHOLD
            bad += int(not np.array_equal(got, ref))
            # hits_group == any over others
            paths = [e1_reopen.Path(int(d), float(v)) for d, v in zip(cd, cn)]
            group = [e1_reopen.Path(int(d), float(v)) for d, v in zip(ld, ln)]
            bad += int(not np.array_equal(cg.hits_group(group, paths, 1024, mode), ref.any(axis=0)))
            n_checks += 1
    assert bad == 0, 'T1: vectorised guard predicates differ from the brute-force definition'
    for mode in ('off', 'all', 'neardup'):
        assert not cg.hits_group([], [], 1024, mode).size
    try:
        cg.conflict_matrix([1], [0.], [1], [0.], 1024, 'bogus')
        raise AssertionError('T1: bogus mode accepted')
    except ValueError:
        pass
    return dict(random_cases_per_mode=200, modes=3, mismatches=bad)


def t2_g1(states):
    cfgs = {'A1': ('full', 2, 2, 'compact'), 'A2': ('diag', 2, 2, 'compact'), 'A3': ('full', 0, 2, 'compact'),
            'compact_e0_l0': ('full', 0, 0, 'compact'), 'direct_e2_l2': ('full', 2, 2, 'direct')}
    out = {}
    for name, (gm, me, lp, strat) in cfgs.items():
        ok, bad = 0, []
        for i, s in enumerate(states):
            ref = run_e1(s, gm, me, lp, strat)
            got = run_e2(s, gm, me, lp, strat, 'off')
            a, k = e1t.kwargs(s, e2_val, me, lp, strategy=strat, gamma_mode=gm)  # codelay_guard omitted: default must be 'off'
            default = e2_val.reopen_geometry(*a, **k)
            diff = e2_lib.deep_equal(ref, got) + e2_lib.deep_equal(ref, default)
            ok += int(not diff)
            if diff:
                bad.append((i, diff[:3]))
        out[name] = dict(states=len(states), identical=ok, mismatches=bad[:3])
        assert ok == len(states), f'G1 FAILED ({name}): {bad[:2]}'
    return out


def synth_codelay(seed, n=e1t.N, max_delay=e1t.MAX_DELAY, snr_db=18.0):
    """State whose TRUE channel has a same-delay pair (delay 5: nu 0 and .3); start has that pair legal under neardup (dnu = 1.0)."""
    rng = np.random.default_rng(seed)
    c1, c2 = 7.0 / (2 * n), 1.0 / (16 * n)
    delays = np.array([5, 5, 14, 22, 29])
    dopp = np.array([0.0, 0.3, rng.uniform(-2, 2), rng.uniform(-2, 2), rng.uniform(-2, 2)])
    gains = (rng.normal(size=5) + 1j * rng.normal(size=5)) / np.sqrt(10)
    chan = Channel(n, c1, c2, delays, dopp, gains)
    x_true = (rng.choice([-1., 1.], n) + 1j * rng.choice([-1., 1.], n)) / 2
    clean = chan.apply(x_true)
    sigma2 = float(np.mean(abs(clean) ** 2) / 10 ** (snr_db / 10))
    y = clean + np.sqrt(sigma2 / 2) * (rng.normal(size=n) + 1j * rng.normal(size=n))
    v = .02 + .02 * rng.random(n)
    x_mean = x_true * (1 - 2 * v)
    init_d = [5, 5, 14, 22, 29]
    init_nu = [-.5, .5, float(dopp[2] + rng.normal(0, .1)), float(dopp[3] + rng.normal(0, .1)), float(dopp[4] + rng.normal(0, .1))]
    return dict(Y=daft(y, c1, c2, True), x=x_mean, v=v, delays=init_d, dopplers=init_nu, c1=c1, c2=c2, ridge=sigma2)


def t3_g2(states):
    n = e1t.N
    out = dict(states=len(states), invariants_checked=0, violations=0, compact_direct_agree=0, a2g_differs_from_a2=0,
               guard_changes_decision_a1=0, local_refinement=dict(), off_violates_somewhere=False)
    for i, s in enumerate(states):
        for gm in ('full', 'diag'):
            for guard in ('all', 'neardup'):
                comp = run_e2(s, gm, 2, 2, 'compact', guard)
                dire = run_e2(s, gm, 2, 2, 'direct', guard)
                for res in (comp, dire):
                    out['invariants_checked'] += 1
                    out['violations'] += int(not guard_satisfied(res, n, guard))
                same = (e1t.top1(comp) == e1t.top1(dire) and e1t.edit_sig(comp) == e1t.edit_sig(dire)
                        and comp.global_trace[0]['scores'].shape == dire.global_trace[0]['scores'].shape)
                if same:
                    a, b = comp.global_trace[0], dire.global_trace[0]
                    both = a['valid'] & b['valid']
                    same = bool(np.array_equal(a['valid'], b['valid'])
                                and np.max(abs(a['scores'][both] - b['scores'][both]) / (1 + abs(b['scores'][both]))) < 1e-8)
                out['compact_direct_agree'] += int(same)
        a2 = run_e2(s, 'diag', 2, 2, 'compact', 'off')
        a2g = run_e2(s, 'diag', 2, 2, 'compact', 'all')
        out['a2g_differs_from_a2'] += int(e1t.delay_set(a2) != e1t.delay_set(a2g) or e1t.edit_sig(a2) != e1t.edit_sig(a2g) or e1t.top1(a2) != e1t.top1(a2g))
        a1 = run_e2(s, 'full', 2, 2, 'compact', 'off')
        a1g = run_e2(s, 'full', 2, 2, 'compact', 'all')
        out['guard_changes_decision_a1'] += int(e1t.delay_set(a1) != e1t.delay_set(a1g) or e1t.edit_sig(a1) != e1t.edit_sig(a1g))
    n_cmp = 4 * len(states)
    # dedicated co-delay states: true same-delay pair; local refinement must not drift the legal pair into |D_N| >= .5 under 'neardup'
    drift_off = drift_nd = checks = 0
    pairs_off, pairs_nd = [], []
    for seed in range(16):
        s = synth_codelay(seed)   # the start already holds a legal-under-neardup pair, so 'all' (which forbids it) is not exercised here
        for guard, store in (('off', pairs_off), ('neardup', pairs_nd)):
            res = run_e2(s, 'full', 0, 2, 'compact', guard)   # local Doppler refinement only
            store.append(codelay_pairs(res, n))
            checks += 1
            if guard == 'neardup':
                drift_nd += int(not guard_satisfied(res, n, 'neardup'))
            if guard == 'off':
                drift_off += int(not guard_satisfied(res, n, 'neardup'))
    out['local_refinement'] = dict(states=16, off_final_pair_has_abs_dn_ge_half=drift_off, neardup_final_pair_has_abs_dn_ge_half=drift_nd,
                                   mean_abs_dn_off=float(np.mean([p[1] for ps in pairs_off for p in ps] or [0.])),
                                   mean_abs_dn_neardup=float(np.mean([p[1] for ps in pairs_nd for p in ps] or [0.])))
    out['off_violates_somewhere'] = bool(drift_off > 0)
    assert out['violations'] == 0, f"G2: guard invariant violated {out['violations']} times"
    assert out['compact_direct_agree'] == n_cmp, f"G2: compact and direct disagree in guard mode ({out['compact_direct_agree']}/{n_cmp})"
    need = 8 if len(states) >= 32 else 1
    assert out['a2g_differs_from_a2'] >= need, f"G2: A2g differs from A2 on only {out['a2g_differs_from_a2']} states"
    assert drift_nd == 0, 'G2: neardup guard let local refinement push a legal pair into |D_N| >= .5'
    assert drift_off > 0, 'G2 (sanity): without the guard the local refinement never closed a legal pair; the dedicated test is vacuous'
    return out


def t4_g3(states):
    out = {}
    for arm, (gm, me, lp, strat, guard) in GUARD_CONFIGS.items():
        ok, bad = 0, []
        for i, s in enumerate(states):
            r1 = run_e2(s, gm, me, lp, strat, guard)
            r2 = run_e2(s, gm, me, lp, strat, guard)
            diff = e2_lib.deep_equal(r1, r2)
            ok += int(not diff)
            if diff:
                bad.append((i, diff[:2]))
        out[arm] = dict(states=len(states), identical=ok, mismatches=bad[:3])
        assert ok == len(states), f'G3 FAILED ({arm}): {bad[:2]}'
    return out


def load_frozen_driver():
    spec = importlib.util.spec_from_file_location('headroom_driver_frozen', EXPERIMENTS / 'headroom_ladder_20261008' / 'driver.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def cg0_copy_equals_frozen(frames=20):
    drv = load_frozen_driver()
    entropy = ch.E2CJ_ENTROPY
    bad = []
    for f in range(frames):
        a = ch.draw_cluster_geometry(entropy, ch.CLUS_DOMAIN, f)
        b = drv.draw_cluster_geometry(entropy, f)
        d = e2_lib.deep_equal(a, b)
        pa, pb = ch.cluster_paths(a), drv.cluster_paths(b, 'J4')
        d += e2_lib.deep_equal({k: v for k, v in pa.items() if k != 'tap_of'}, pb)
        if d:
            bad.append((f, d[:2]))
    assert not bad, f'CG0 FAILED: {bad[:2]}'
    # the E2CJ domain really gives different draws
    assert not np.array_equal(ch.draw_cluster_geometry(entropy, ch.E2CJ_DOMAIN, 0)['delays'], ch.draw_cluster_geometry(entropy, ch.CLUS_DOMAIN, 0)['delays']) \
        or not np.array_equal(ch.draw_cluster_geometry(entropy, ch.E2CJ_DOMAIN, 1)['delays'], ch.draw_cluster_geometry(entropy, ch.CLUS_DOMAIN, 1)['delays'])
    return dict(frames=frames, identical=frames - len(bad), frozen_driver_md5=e2_lib.md5_file(EXPERIMENTS / 'headroom_ladder_20261008' / 'driver.py'))


def cg1_power(frames=50):
    worst, before = 0., []
    for f in range(frames):
        paths = ch.cluster_paths(ch.draw_cluster_geometry(ch.E2CJ_ENTROPY, ch.E2CJ_DOMAIN, f))
        g, p0 = ch.unit_power_gains(N1024, C1, paths)
        p1 = ch.power_per_dim(N1024, C1, paths['l_i'], paths['k_real'], g)
        worst = max(worst, abs(p1 - 1.))
        before.append(p0)
    assert worst < 1e-9, f'CG1 FAILED: |power-1| = {worst}'
    return dict(frames=frames, worst_abs_deviation=worst, power_before_renorm=dict(min=float(min(before)), mean=float(np.mean(before)), max=float(max(before))))


def cg2_operator(frames=20):
    rng = np.random.default_rng(3)
    worst = 0.
    for f in range(frames):
        paths = ch.cluster_paths(ch.draw_cluster_geometry(ch.E2CJ_ENTROPY, ch.E2CJ_DOMAIN, f))
        g, _ = ch.unit_power_gains(N1024, C1, paths)
        x = rng.normal(size=N1024) + 1j * rng.normal(size=N1024)
        channel = Channel(N1024, C1, C2, paths['l_i'], paths['k_real'], g)
        t = ch.time_domain_matrix(N1024, C1, paths['l_i'], paths['k_real'], g)
        ref = daft(t @ daft(x, C1, C2, True), C1, C2)
        got = channel.apply(x)
        worst = max(worst, float(np.linalg.norm(got - ref) / np.linalg.norm(ref)))
    assert worst < 1e-9, f'CG2 FAILED: relative error {worst}'
    return dict(frames=frames, worst_relative_error=worst)


def cg3_taps(frames=1000):
    multi, taps, total_rays, max_rays = 0, 0, 0, 0
    for f in range(*ch.MAIN_FRAMES):
        geom = ch.draw_cluster_geometry(ch.E2CJ_ENTROPY, ch.E2CJ_DOMAIN, f)
        rays = ch.cluster_paths(geom)['rays_per_tap']
        multi += sum(1 for r in rays if r >= 2)
        taps += len(rays)
        total_rays += sum(rays)
        max_rays = max(max_rays, max(rays))
    return dict(main_frames=ch.MAIN_FRAMES[1] - ch.MAIN_FRAMES[0], taps=taps, taps_with_ge2_rays=multi, frac_taps_with_ge2_rays=multi / taps,
                mean_rays_per_frame=total_rays / (ch.MAIN_FRAMES[1] - ch.MAIN_FRAMES[0]), max_rays_in_a_tap=max_rays)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument('--out', type=Path, default=HERE / 'out' / 'unit')
    p.add_argument('--states', type=int, default=64)
    a = p.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    t0 = time.perf_counter()
    states = [e1t.synth(1000 + i, snr_db=4.0 + (i % 5) * 1.5) for i in range(a.states)]
    result = dict(n_synthetic_states=a.states, note='synthetic states; real-P1-state G1-G5 and the context-level CG1-CG3 are in e2_driver.py')
    for name, fn, arg in (('T0_source_diff', t0_source_diff, None), ('T1_predicates', t1_predicates, None), ('G1_off_equals_e1', t2_g1, states),
                          ('G2_guard_invariants', t3_g2, states), ('G3_determinism', t4_g3, states), ('CG0_copy_equals_frozen', cg0_copy_equals_frozen, None),
                          ('CG1_unit_power', cg1_power, None), ('CG2_operator', cg2_operator, None), ('CG3_descriptive_taps', cg3_taps, None)):
        s = time.perf_counter()
        result[name] = fn() if arg is None else fn(arg)
        result[name]['seconds'] = time.perf_counter() - s
        print(f'{name}: PASS ({result[name]["seconds"]:.1f}s)', flush=True)
    result['all_pass'] = True
    result['total_seconds'] = time.perf_counter() - t0
    (a.out / 'test_e2.json').write_text(json.dumps(result, indent=1, default=str) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k in ('G2_guard_invariants', 'CG1_unit_power', 'CG3_descriptive_taps')}, indent=1, default=str))
    print('ALL PASS')


if __name__ == '__main__':
    main()
