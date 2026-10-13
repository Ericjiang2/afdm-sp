#!/usr/bin/env python
"""Unit checks for driver_f3 (run on deinlab, single thread, CPU).

U1  realized mode is bit-identical to driver.cluster_paths (l_i, k_real, g_i, rays_per_tap, tap_spread, norm_factor)
    for D1,N4a,N4b,J4,J8 over --frames frames of the F1 entropy.
U2  expected mode: gains == realized gains * realized norm factor (to 1 ulp-level rtol 1e-15), norm_factor == 1,
    ray/Doppler/delay arrays identical to realized mode; expected-power sums: mean sum|g|^2 -> 1 (within 4 SE).
U3  S16: 16 distinct sorted delays starting at 0, max <= 100, 1 ray/tap, sum tap_power = 1, channel_seed equals the
    F1 channel_seed of the same frame; redraw statistics.
U4  tap_eigenvalues: sum lambda = N tap_power; equals the nonzero spectrum of the explicit N x N V P V^H (3 frames);
    R=1 gives lambda = N tap_power.
U5  ctx: cluster_base_f3 closure (matrix == direct CPP propagation) for every config in both modes (asserted inside),
    mean ||H||_F^2/N over frames (expected mode) ~ 1 for D1; realized energy equals expected-mode energy / factor^2.
U6  P_eff staircase from truth: mean P_eff per config at 6/10/14 dB.
"""
import argparse
import json
from pathlib import Path
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import driver as base  # noqa: E402
import driver_f3 as f3  # noqa: E402

ENTROPY = '129abc3bec7243c1dd584ffab5b2a3989f2e81da01ee8397de783e8f52357812'  # F1 / F2 entropy
N = 1024


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--frames', type=int, default=2000)
    p.add_argument('--ctx-frames', type=int, default=40)
    a = p.parse_args()
    report = {}
    old = ('D1', 'N4a', 'N4b', 'J4', 'J8')

    # U1 / U2
    bad1, bad2, sg2 = 0, 0, {c: [] for c in f3.F3_CONFIGS}
    for f in range(a.frames):
        geom = base.draw_cluster_geometry(ENTROPY, f)
        for c in old:
            ref = base.cluster_paths(geom, c)
            r = f3.paths_f3(geom, c, 'realized')
            same = (np.array_equal(ref['l_i'], r['l_i']) and np.array_equal(ref['k_real'], r['k_real'])
                    and np.array_equal(ref['g_i'], r['g_i']) and ref['rays_per_tap'] == r['rays_per_tap']
                    and ref['tap_spread'] == r['tap_spread'] and ref['norm_factor'] == r['norm_factor']
                    and ref['tap_delays'] == r['tap_delays'])
            bad1 += not same
            e = f3.paths_f3(geom, c, 'expected')
            ok2 = (e['norm_factor'] == 1.0 and np.array_equal(e['l_i'], r['l_i'])
                   and np.array_equal(e['k_real'], r['k_real'])
                   and np.array_equal(e['g_i'] / np.sqrt(np.sum(np.abs(e['g_i'])**2)), r['g_i'])
                   and np.allclose(e['g_i'], r['g_i'] * r['norm_factor'], rtol=1e-14, atol=0))
            bad2 += not ok2
            sg2[c].append(e['sum_g2'])
    report['U1_realized_mismatch'] = bad1
    report['U2_expected_inconsistent'] = bad2
    report['U2_mean_sum_g2'] = {c: [float(np.mean(v)), float(np.std(v) / np.sqrt(len(v)))] for c, v in sg2.items() if v}
    print('U1/U2', bad1, bad2, report['U2_mean_sum_g2'], flush=True)
    assert bad1 == 0 and bad2 == 0
    for c, (m, se) in report['U2_mean_sum_g2'].items():
        assert abs(m - 1) < 4 * se + 1e-12, (c, m, se)

    # U3
    redraws, bad3, cs_bad = [], 0, 0
    s16_sg2 = []
    for f in range(a.frames):
        geom = f3.draw_s16_geometry(ENTROPY, f)
        pa = f3.paths_f3(geom, 'S16', 'expected')
        l = pa['l_i']
        ok = (len(l) == 16 and l[0] == 0 and np.all(np.diff(l) >= 1) and l.max() <= base.CLUSTER_PARAMS['delay_cap']
              and pa['rays_per_tap'] == [1] * 16 and abs(pa['tap_power'].sum() - 1) < 1e-12
              and np.all(np.abs(pa['k_real']) <= 2 + 1e-12))
        bad3 += not ok
        cs_bad += geom['channel_seed'] != base.draw_cluster_geometry(ENTROPY, f)['channel_seed']
        redraws.append(geom['delay_redraws'])
        s16_sg2.append(pa['sum_g2'])
    report['U3_S16_malformed'] = bad3
    report['U3_S16_channel_seed_mismatch_vs_F1'] = cs_bad
    report['U3_S16_redraws_mean_max'] = [float(np.mean(redraws)), int(np.max(redraws))]
    report['U3_S16_mean_sum_g2'] = [float(np.mean(s16_sg2)), float(np.std(s16_sg2) / np.sqrt(len(s16_sg2)))]
    print('U3', report['U3_S16_malformed'], cs_bad, report['U3_S16_redraws_mean_max'], flush=True)
    assert bad3 == 0 and cs_bad == 0

    # U4
    worst_sum = 0.
    for f in range(200):
        for c in old:
            pa = f3.paths_f3(base.draw_cluster_geometry(ENTROPY, f), c, 'expected')
            eigs = f3.tap_eigenvalues(pa, N)
            for t, l in enumerate(eigs):
                worst_sum = max(worst_sum, abs(l.sum() / (N * pa['tap_power'][t]) - 1))
                if pa['rays_per_tap'][t] == 1:
                    assert abs(l[0] / (N * pa['tap_power'][t]) - 1) < 1e-10
    report['U4_max_rel_sum_err'] = worst_sum
    assert worst_sum < 1e-9
    explicit = []
    for f in (0, 1, 2):
        pa = f3.paths_f3(base.draw_cluster_geometry(ENTROPY, f), 'J4', 'expected')
        eigs = f3.tap_eigenvalues(pa, N)
        for t in range(4):
            nu = pa['k_real'][pa['tap_of'] == t]
            v = np.exp(2j * np.pi * np.outer(np.arange(N), nu) / N)
            m = (v * (pa['tap_power'][t] / len(nu))) @ v.conj().T
            w = np.linalg.eigvalsh((m + m.conj().T) / 2)[::-1][:len(nu)]
            explicit.append(float(np.max(np.abs(w - eigs[t]) / max(w[0], 1e-300))))
    report['U4_explicit_max_rel_diff'] = max(explicit)
    print('U4', worst_sum, max(explicit), flush=True)
    assert max(explicit) < 1e-9

    # U6 (no ctx needed)
    stair = {}
    for c in f3.F3_CONFIGS:
        acc = {6: [], 10: [], 14: []}
        for f in range(a.frames):
            geom = f3.geometry(ENTROPY, f, c)
            eigs = f3.tap_eigenvalues(f3.paths_f3(geom, c, 'expected'), N)
            for snr in acc:
                acc[snr].append(f3.peff_count(eigs, 10 ** (-snr / 10))[0])
        stair[c] = {str(k): [float(np.mean(v)), float(np.std(v))] for k, v in acc.items()}
    report['U6_peff_mean_std'] = stair
    print('U6', json.dumps(stair), flush=True)

    # U5 (needs frozen context)
    args = f3.parse_args(['--mode', 'generate', '--out', str(a.out.parent), '--frames', '1',
                          '--entropy-hex', ENTROPY, '--power-norm', 'expected'])
    ctx = f3.load_context(args)
    e_energy = {c: [] for c in f3.F3_CONFIGS}
    rel = 0.
    for f in range(a.ctx_frames):
        msg = base.cluster_message(ctx, ENTROPY, f)
        for c in f3.F3_CONFIGS:
            geom = f3.geometry(ENTROPY, f, c)
            raw_e, _ = f3.cluster_base_f3(ctx, msg, geom, c, 'expected')  # closure asserted inside
            e_energy[c].append(raw_e['cluster']['energy_per_dim'])
            if c in old:
                raw_r, _ = f3.cluster_base_f3(ctx, msg, geom, c, 'realized')
                fac = raw_r['cluster']['norm_factor']
                rel = max(rel, abs(raw_e['cluster']['energy_per_dim'] / fac**2 / raw_r['cluster']['energy_per_dim'] - 1))
    report['U5_energy_per_dim_mean_se'] = {c: [float(np.mean(v)), float(np.std(v) / np.sqrt(len(v)))]
                                           for c, v in e_energy.items()}
    report['U5_expected_over_factor2_vs_realized_max_rel'] = rel
    print('U5', report['U5_energy_per_dim_mean_se'], rel, flush=True)
    assert rel < 1e-9
    a.out.write_text(json.dumps(report, indent=1) + '\n')
    print('all checks passed', flush=True)


if __name__ == '__main__':
    main()
