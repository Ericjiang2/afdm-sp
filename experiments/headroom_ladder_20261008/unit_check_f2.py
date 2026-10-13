#!/usr/bin/env python
"""Unit checks for the F2 oracle ladder (orders.py) and arm wiring (run on deinlab, single thread, CPU).

U1  misfit identity: tap-sequence misfit == explicit ||H_true - H_D||_F^2/||H_true||_F^2 from physical_channel_matrix
    (D in 1,2,3,5; several frames of N4b/J4/N4a); ||H_true||_F^2 == sum_l ||a_l||^2.
U2  single-ray taps (config D1): O1 misfit == 0 and Channel(O1).apply == Channel(true).apply.
U3  large-D / identity: LS on the exact true Doppler set reproduces the tap (misfit ~ 0) and Channel.apply(truth);
    spacing-1 D=63 grid misfit is small (Dirichlet-leakage limit) and decreasing in D (info).
U4  the 1-bin grid is exactly orthogonal (Gram = N I) and Channel(O_D).apply == physical H_D @ x (D = 5).
U5  arm wiring on real frames: O1 == A3 bit-for-bit on D1 frames (Channel identical up to LS rounding); PS runs on
    N4b/J4/D1 frames (slot cap, multi-slot per delay, stop reason) and returns finite scores.
usage: unit_check_f2.py <out.json>
"""
import json
from pathlib import Path
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import driver  # noqa: E402
import driver_f2 as f2  # noqa: E402
import orders  # noqa: E402

ENTROPY = '129abc3bec7243c1dd584ffab5b2a3989f2e81da01ee8397de783e8f52357812'


def frame_paths(frame, config):
    return driver.cluster_paths(driver.draw_cluster_geometry(ENTROPY, frame), config)


def main():
    out = Path(sys.argv[1])
    args = f2.parse_args(['--mode', 'generate', '--out', str(out.parent), '--frames', '1',
                          '--entropy-hex', ENTROPY, '--snr-list', '8'])
    ctx = f2.load_context(args)
    s = ctx.system
    n, prefix = int(s.N_total), int(s.l_max_cap)
    rng = np.random.default_rng(7)
    rep = {}

    # ---- U1 ----
    worst, rows = 0., []
    for config, frames in (('N4b', range(0, 6)), ('J4', range(6, 12)), ('N4a', range(12, 16))):
        for f in frames:
            pa = frame_paths(f, config)
            l, nu, g = pa['l_i'], pa['k_real'], pa['g_i']
            ht = ctx.physical_channel_matrix(n, s.c1, s.c2, l, nu, g, prefix_length=prefix)
            den_formula = sum(float(np.vdot(a, a).real) for a in
                              (orders.tap_sequence(v[0], v[1], n) for v in orders.tap_groups(l, nu, g).values()))
            den_err = abs(np.linalg.norm(ht) ** 2 - den_formula) / den_formula
            for D in (1, 2, 3, 5):
                ls, nus, gs, mis = orders.oracle_paths(l, nu, g, D, n)
                hd = ctx.physical_channel_matrix(n, s.c1, s.c2, ls, nus, gs, prefix_length=prefix)
                mm = float(np.linalg.norm(ht - hd) ** 2 / np.linalg.norm(ht) ** 2)
                worst = max(worst, abs(mm - mis), den_err)
                rows.append(dict(config=config, frame=f, D=D, misfit_tap=mis, misfit_matrix=mm, fro_den_rel_err=den_err))
    rep['U1_max_abs_diff_misfit_or_energy'] = worst
    rep['U1_rows'] = rows
    assert worst < 1e-10, worst
    print('U1 ok', worst, flush=True)

    # ---- U2 ----
    x = rng.standard_normal(n) + 1j * rng.standard_normal(n)
    u2 = []
    for f in range(8):
        pa = frame_paths(f, 'D1')
        l, nu, g = pa['l_i'], pa['k_real'], pa['g_i']
        ls, nus, gs, mis = orders.oracle_paths(l, nu, g, 1, n)
        ct = ctx.Channel(n, s.c1, s.c2, l, nu, g)
        co = ctx.Channel(n, s.c1, s.c2, ls, nus, gs)
        rel = float(np.linalg.norm(ct.apply(x) - co.apply(x)) / np.linalg.norm(ct.apply(x)))
        u2.append(dict(frame=f, misfit=mis, apply_rel_diff=rel, max_nu_diff=float(np.max(np.abs(nus - nu))),
                       max_g_diff=float(np.max(np.abs(gs - g)))))
        assert mis < 1e-24 and rel < 1e-12, u2[-1]
    rep['U2_D1_single_ray'] = u2
    print('U2 ok', flush=True)

    # ---- U3 ----
    u3 = []
    for config, f in (('J4', 3), ('N4b', 5), ('N4a', 9)):
        pa = frame_paths(f, config)
        l, nu, g = pa['l_i'], pa['k_real'], pa['g_i']
        grp = orders.tap_groups(l, nu, g)
        ls, nus, gs, mis = orders.misfit_with_nus(l, nu, g, {d: v[0] for d, v in grp.items()}, n)
        ct = ctx.Channel(n, s.c1, s.c2, l, nu, g)
        co = ctx.Channel(n, s.c1, s.c2, ls, nus, gs)
        rel = float(np.linalg.norm(ct.apply(x) - co.apply(x)) / np.linalg.norm(ct.apply(x)))
        by_d = {D: orders.oracle_paths(l, nu, g, D, n)[3] for D in (1, 2, 3, 5, 9, 17, 33, 63)}
        u3.append(dict(config=config, frame=f, misfit_exact_nus=mis, apply_rel_diff_exact_nus=rel, misfit_by_D=by_d,
                       max_rays_per_tap=max(pa['rays_per_tap']), max_spread=max(pa['tap_spread'])))
        assert mis < 1e-20 and rel < 1e-9, u3[-1]
    rep['U3_large_D'] = u3
    print('U3 ok', flush=True)

    # ---- U4 ----
    pa = frame_paths(5, 'N4b')
    l, nu, g = pa['l_i'], pa['k_real'], pa['g_i']
    ls, nus, gs, mis = orders.oracle_paths(l, nu, g, 5, n)
    k = np.arange(n)
    gram = []
    for d, (nv, gv) in orders.tap_groups(l, nu, g).items():
        grid = orders.subpath_grid(orders.centroid(nv, gv), 5)
        E = np.exp(2j * np.pi * np.outer(k, grid) / n)
        gram.append(float(np.max(np.abs(E.conj().T @ E / n - np.eye(5)))))
    hd = ctx.physical_channel_matrix(n, s.c1, s.c2, ls, nus, gs, prefix_length=prefix)
    co = ctx.Channel(n, s.c1, s.c2, ls, nus, gs)
    rel = float(np.linalg.norm(co.apply(x) - hd @ x) / np.linalg.norm(hd @ x))
    rep['U4'] = dict(max_gram_dev=max(gram), channel_apply_vs_physical_H_rel=rel)
    assert max(gram) < 1e-12 and rel < 1e-10, rep['U4']
    print('U4 ok', flush=True)

    # ---- U5 ----
    msg_cache, u5 = {}, []
    for config, frames, snr in (('D1', range(0, 4), 7.0), ('N4b', range(0, 3), 8.0), ('J4', range(0, 3), 8.0)):
        for f in frames:
            msg = msg_cache.setdefault(f, driver.cluster_message(ctx, ENTROPY, f))
            raw_base, diag = driver.cluster_base(ctx, msg, driver.draw_cluster_geometry(ENTROPY, f), config)
            raw = driver.cluster_at_snr(raw_base, snr)
            obs = driver.observe(raw, .5, snr)
            truth = driver.truth_from_raw(raw, diag)
            rows = f2.run_cell_f2(ctx, ['A0', 'A3', 'PS', 'O1', 'O2', 'O3', 'O5'], obs, truth, int(round(snr * 100)), f, True)
            by = {r['arm']: r for r in rows}
            rec = dict(config=config, frame=f, snr=snr, status={a: r['status'] for a, r in by.items()},
                       info_errors={a: r.get('info_errors') for a, r in by.items()},
                       logloss={a: r.get('logloss_bits') for a, r in by.items()},
                       seconds={a: r.get('seconds') for a, r in by.items()})
            if 'PS' in by and by['PS']['status'] == 'ok':
                rec['ps'] = {k2: by['PS'][k2] for k2 in by['PS'] if k2.startswith('ps_') or k2 in ('fit_delays', 'triggered')}
                assert rec['ps']['ps_n_slots'] <= 8
            for a in ('O1', 'O2', 'O3', 'O5'):
                if by[a]['status'] == 'ok':
                    rec.setdefault('misfit', {})[a] = by[a]['misfit']
                    rec.setdefault('misfit_matrix_abs_diff', {})[a] = by[a].get('misfit_matrix_abs_diff')
            if config == 'D1':  # O1 must reproduce A3 (identical Channel up to LS rounding)
                assert by['O1']['info_errors'] == by['A3']['info_errors']
                assert abs(by['O1']['logloss_bits'] - by['A3']['logloss_bits']) < 1e-9, (by['O1']['logloss_bits'], by['A3']['logloss_bits'])
            u5.append(rec)
            print('U5', config, f, rec['info_errors'], flush=True)
    rep['U5'] = u5
    rep['status'] = 'pass'
    out.write_text(json.dumps(rep, indent=1, default=driver.to_jsonable, allow_nan=False) + '\n')
    print('all pass', flush=True)


if __name__ == '__main__':
    main()
