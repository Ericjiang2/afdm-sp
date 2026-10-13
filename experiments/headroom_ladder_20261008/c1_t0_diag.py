#!/usr/bin/env python
"""T0 follow-up diagnostics D1-D3 on EXISTING C1 rows (read-only; no new simulation; research/c1-scalar-closure.md A3 'diagnostics from
stored rows').  Reuses c1_t0_screen.load / helpers (c1_t0_screen.py is not modified).
usage: c1_t0_diag.py --boot-dir D --map-dir D --t1-json F --t1-frames F --out-dir D [--boot-md5 F --map-md5 F]

D1  Round-1 detector LLR calibration.  Per cell and arm (A3, SPg_flat; other SP arms in json): mean r1_ll_in (logloss, bits/coded bit, LLR
    clipped +-20) vs mean r1_mabs_in (mean |LLR|, clipped).  Consistent-Gaussian reference: LLR | bit ~ N(sigma^2/2, sigma^2), clipped
    +-20 (numerical tables, 8001-point Gaussian grid); implied logloss = ll_cg(mean|LLR|) obtained by inverting mean|LLR|(sigma).
    observed/implied > 1 = observed logloss larger than a consistent Gaussian with the same mean |LLR| (over-confident).  Frame-level:
    implied(mabs_f) per frame; cell value = mean_f ll_f / mean_f implied_f (and median_f ll_f/implied_f).  A3 is the true-H baseline
    (QPSK on a fading channel is NOT a single-sigma Gaussian, so A3 itself has ratio > 1; compare SP with A3).
D2  Decoder closure in MI space.  I_in = 1 - r1_ll_in per frame; P(r1 correct = r1_cerr == 0 | I_in) in 0.02 bins, pooled over cells per
    dataset (and per dataset/SNR/rho pooling L) for SPg_flat and A3.  AWGN reference: (a) t1_transfer.json columns.coded (J_chan, 1 - FER)
    mean-level; (b) T1 per-frame (frames.npz: 1 - ll_chan, coded_err == 0) in the same bins.  I50 = I_in at P(correct) = .5: linear
    interpolation between the first bin pair crossing .5 (bins with n >= 20) and logistic fit P = sigmoid(a + b I) (I50 = -a/b).
D3  Inner map: per cell eps_det1/eps_ce1 (median [q25, q75] of per-frame ratio; ratio of medians), vs K and K/K*; Spearman(E_real,
    eps_det1/E_real), Spearman(E_real, eps_ce1/E_real), Spearman(E_real, eps_det1/eps_ce1).
"""
from __future__ import annotations

import argparse
import collections
import json
import math
from pathlib import Path
import sys
import time

import numpy as np

import c1_t0_screen as T

T.FIELDS = T.FIELDS + ('r1_mabs_in',)
BIN_W = 0.02
MIN_N = 20
ARMS_D1 = ('A3', 'SPg_flat', 'SPg_slep', 'SPg_flat03')
MABS_EDGES = np.array([0., 1., 2., 3., 4., 5., 6., 8., 10., 15., 20.0001])


# ------------------------------------------------------------------------------------------------ consistent Gaussian
def cg_tables():
    Z = np.linspace(-10., 10., 8001)
    w = np.exp(-Z**2 / 2.)
    w /= w.sum()
    sig = np.geomspace(0.02, 80., 3000)
    mabs, ll = np.empty(len(sig)), np.empty(len(sig))
    for i, s in enumerate(sig):
        L = np.clip(s * s / 2. + s * Z, -20., 20.)
        mabs[i] = w @ np.abs(L)
        ll[i] = w @ (np.logaddexp(0., -L) / math.log(2.))
    return sig, np.maximum.accumulate(mabs), ll


SIG, CG_MABS, CG_LL = cg_tables()


def implied_ll(mabs):
    return np.interp(mabs, CG_MABS, CG_LL)


# ------------------------------------------------------------------------------------------------ D1
def d1_stats(ll, mabs):
    imp = implied_ll(mabs)
    return dict(n=int(len(ll)), mean_mabs=float(mabs.mean()), mean_ll_in=float(ll.mean()), mean_I_in=float(1 - ll.mean()),
                mean_implied_ll=float(imp.mean()), ratio_obs_over_implied=float(ll.mean() / imp.mean()),
                median_frame_ratio=float(np.median(ll / np.maximum(imp, 1e-12))),
                implied_ll_at_mean_mabs=float(implied_ll(np.array([mabs.mean()]))[0]),
                ratio_obs_over_implied_at_mean=float(ll.mean() / implied_ll(np.array([mabs.mean()]))[0]))


def d1_bins(ll, mabs, nb=8):
    edges = np.unique(np.quantile(mabs, np.linspace(0, 1, nb + 1)))
    idx = np.clip(np.searchsorted(edges, mabs, side='right') - 1, 0, len(edges) - 2)
    out = []
    for b in range(len(edges) - 1):
        m = idx == b
        out.append(d1_stats(ll[m], mabs[m]) if m.sum() else None)
    return out


def d1_fixed_bins(ll, mabs):
    idx = np.clip(np.searchsorted(MABS_EDGES, mabs, side='right') - 1, 0, len(MABS_EDGES) - 2)
    return [dict(lo=float(MABS_EDGES[b]), hi=float(MABS_EDGES[b + 1]), **(d1_stats(ll[idx == b], mabs[idx == b]) if (idx == b).sum() else dict(n=0)))
            for b in range(len(MABS_EDGES) - 1)]


# ------------------------------------------------------------------------------------------------ D2
def curve(I, ok):
    lo = math.floor(min(I.min(), 0.) / BIN_W) * BIN_W
    edges = np.arange(lo, 1.0 + 2 * BIN_W, BIN_W)
    idx = np.clip(np.searchsorted(edges, I, side='right') - 1, 0, len(edges) - 2)
    rows = []
    for b in range(len(edges) - 1):
        m = idx == b
        n = int(m.sum())
        rows.append(dict(lo=float(edges[b]), center=float(edges[b] + BIN_W / 2), n=n, p=(float(ok[m].mean()) if n else None)))
    return rows


def cross_bins(rows, level=.5, min_n=MIN_N):
    pts = [(r['center'], r['p']) for r in rows if r['n'] >= min_n]
    for (x0, p0), (x1, p1) in zip(pts[:-1], pts[1:]):
        if p0 < level <= p1:
            return float(x0 + (level - p0) / (p1 - p0) * (x1 - x0))
    return None


def logistic(I, ok, iters=60):
    """P(correct) = sigmoid(a + b x), x = I standardised; Newton/IRLS with tiny ridge.  Returns (I50, slope per unit I, converged)."""
    m, s = I.mean(), I.std()
    if s == 0 or ok.min() == ok.max():
        return None, None, False
    x = (I - m) / s
    X = np.stack([np.ones_like(x), x], 1)
    y = ok.astype(float)
    beta = np.zeros(2)
    for _ in range(iters):
        p = 1. / (1. + np.exp(-np.clip(X @ beta, -30, 30)))
        W = np.maximum(p * (1 - p), 1e-9)
        step = np.linalg.solve(X.T @ (X * W[:, None]) + 1e-6 * np.eye(2), X.T @ (y - p) - 1e-6 * beta)
        beta += step
        if np.max(np.abs(step)) < 1e-9:
            break
    a, b = beta
    if abs(b) < 1e-9:
        return None, None, False
    return float(m + s * (-a / b)), float(b / s), bool(np.max(np.abs(step)) < 1e-6)


def d2_summary(I, ok):
    rows = curve(I, ok)
    i50, slope, conv = logistic(I, ok)
    return dict(n=int(len(I)), p_correct=float(ok.mean()), I50_bins=cross_bins(rows), I50_logistic=i50, logistic_slope=slope, logistic_converged=conv,
                mean_I_in=float(I.mean()), bins=rows)


def awgn_columns(t1):
    c = t1['columns']['coded']
    J, P = np.array(c['J_chan']), 1. - np.array(c['FER'])
    cross = None
    for i in range(len(J) - 1):
        if P[i] < .5 <= P[i + 1] or P[i] > .5 >= P[i + 1]:
            cross = float(J[i] + (0.5 - P[i]) / (P[i + 1] - P[i]) * (J[i + 1] - J[i]))
            break
    return dict(q_db=c['q_db'], J_chan=c['J_chan'], FER=c['FER'], I50_mean_level=cross)


def awgn_frames(path):
    z = np.load(path)
    keys = sorted(k for k in z.files if k.startswith('coded_') and k.endswith('_ll_chan'))
    I = np.concatenate([1. - z[k] for k in keys])
    ok = np.concatenate([z[k[:-len('ll_chan')] + 'coded_err'] == 0 for k in keys])
    return I, ok, len(keys)


# ------------------------------------------------------------------------------------------------ D3
def d3_cell(d, rec):
    e, c1, d1 = d['e_real'], d['eps_ce1'], d['eps_det1']
    r = d1 / c1
    return dict(snr_db=rec['snr_db'], rho=rec['rho'], L=rec['L'], K=rec['K'], K_over_kstar=rec['K_over_kstar'], near_cliff=rec['near_cliff'],
                n=int(len(e)), ratio_med=float(np.median(r)), ratio_q25=float(np.percentile(r, 25)), ratio_q75=float(np.percentile(r, 75)),
                ratio_of_medians=float(np.median(d1) / np.median(c1)), med_ce1=float(np.median(c1)), med_det1=float(np.median(d1)),
                spearman_E_det1_over_E=T.spearman(e, d1 / e), spearman_E_ce1_over_E=T.spearman(e, c1 / e), spearman_E_ratio=T.spearman(e, r),
                spearman_E_det1=T.spearman(e, d1), spearman_E_ce1=T.spearman(e, c1))


# ------------------------------------------------------------------------------------------------ main
def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument('--boot-dir', type=Path, required=True)
    ap.add_argument('--map-dir', type=Path, required=True)
    ap.add_argument('--t1-json', type=Path, required=True)
    ap.add_argument('--t1-frames', type=Path, required=True)
    ap.add_argument('--out-dir', type=Path, required=True)
    ap.add_argument('--boot-md5', type=Path, default=None)
    ap.add_argument('--map-md5', type=Path, default=None)
    ap.add_argument('--no-plots', action='store_true')
    args = ap.parse_args(argv)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    t1 = json.load(open(args.t1_json))
    res = dict(_argv=sys.argv, _config=dict(boot_dir=str(args.boot_dir), map_dir=str(args.map_dir), t1_json=str(args.t1_json),
                                            t1_frames=str(args.t1_frames), out_dir=str(args.out_dir), boot_md5=str(args.boot_md5),
                                            map_md5=str(args.map_md5), bin_w=BIN_W, min_n_bin=MIN_N, mabs_fixed_edges=MABS_EDGES.tolist(),
                                            clip=20.0, cg_sigma_grid=[float(SIG[0]), float(SIG[-1]), len(SIG)], cliff_band=T.CLIFF_BAND, N=T.N,
                                            g_old=T.G_OLD, fields=T.FIELDS))
    cells_by_ds, d1, d2, d3, md5s = {}, {}, {}, {}, {}
    for name, dirp, m5 in (('c1_boot', args.boot_dir, args.boot_md5), ('c1_map', args.map_dir, args.map_md5)):
        md5s[name] = T.verify_md5(dirp, m5)
        print(f'[{name}] md5 {md5s[name]}', flush=True)
        cells, st = T.load(dirp)
        print(f'[{name}] {st} ({time.time() - t0:.0f}s)', flush=True)
        cells_by_ds[name] = cells
        d1[name], d3[name] = [], []
        for (arm, snr, rho_pm, L), d in sorted(cells.items()):
            rho, s2, K = rho_pm / 1000., 10 ** (-snr / 1000.), 8 * L
            ks = T.kstar(T.G_OLD, rho, s2)
            ratio = (K / ks if ks > 0 else math.inf) if math.isfinite(ks) else 0.
            head = dict(snr_db=snr / 100., rho=rho, L=int(L), K=int(K), K_over_kstar=ratio,
                        near_cliff=bool(T.CLIFF_BAND[0] <= ratio <= T.CLIFF_BAND[1]), arm=arm)
            ll, mabs = d['r1_ll_in'], d['r1_mabs_in']
            rec = dict(head, **d1_stats(ll, mabs), frame_bins_mabs8=d1_bins(ll, mabs))
            if arm != 'A3':
                a3 = cells.get(('A3', snr, rho_pm, L))
                _, i_sp, i_a3 = np.intersect1d(d['frame'], a3['frame'], return_indices=True)
                rec['mean_dI_sp_minus_a3_paired'] = float(np.mean((1 - ll[i_sp]) - (1 - a3['r1_ll_in'][i_a3])))
            d1[name].append(rec)
            if arm == 'SPg_flat':
                d3[name].append(d3_cell(d, head))
    # D1 pooled fixed bins over near-cliff cells (per dataset, arm)
    d1_pool = {}
    for name, cells in cells_by_ds.items():
        for arm in ARMS_D1:
            ll_l, mabs_l = [], []
            for rec in d1[name]:
                if rec['arm'] == arm and rec['near_cliff']:
                    d = cells[(arm, int(round(rec['snr_db'] * 100)), int(round(rec['rho'] * 1000)), rec['L'])]
                    ll_l.append(d['r1_ll_in'])
                    mabs_l.append(d['r1_mabs_in'])
            if ll_l:
                ll, mabs = np.concatenate(ll_l), np.concatenate(mabs_l)
                d1_pool[f'{name}|{arm}'] = dict(overall=d1_stats(ll, mabs), fixed_bins=d1_fixed_bins(ll, mabs))
    # D2
    d2['awgn_columns'] = awgn_columns(t1)
    Ia, oka, nq = awgn_frames(args.t1_frames)
    d2['awgn_frames'] = dict(n_q_points=nq, **d2_summary(Ia, oka))
    for name, cells in cells_by_ds.items():
        for arm in ARMS_D1:
            keys = [k for k in cells if k[0] == arm]
            if not keys:
                continue
            I = np.concatenate([1. - cells[k]['r1_ll_in'] for k in keys])
            ok = np.concatenate([cells[k]['r1_cerr'] == 0 for k in keys])
            d2[f'{name}|{arm}'] = d2_summary(I, ok)
            groups = collections.defaultdict(list)
            for k in keys:
                groups[(k[1], k[2])].append(k)
            for (snr, rho_pm), ks_ in sorted(groups.items()):
                I = np.concatenate([1. - cells[k]['r1_ll_in'] for k in ks_])
                ok = np.concatenate([cells[k]['r1_cerr'] == 0 for k in ks_])
                d2[f'{name}|{arm}|{snr / 100:g}|{rho_pm / 1000:g}'] = d2_summary(I, ok)
    res.update(md5=md5s, d1_cells=d1, d1_pooled_near_cliff=d1_pool, d2=d2, d3=d3)
    (args.out_dir / 'diag.json').write_text(json.dumps(T.clean(res), indent=1))
    write_md(args.out_dir / 'DIAG.md', md5s, d1, d1_pool, d2, d3)
    if not args.no_plots:
        plots(args.out_dir, d2, d3)
    print(f'done ({time.time() - t0:.0f}s)', flush=True)


# ------------------------------------------------------------------------------------------------ report
def write_md(path, md5s, d1, d1_pool, d2, d3):
    f = T.fmt
    md = ['# T0 follow-up diagnostics D1-D3 (existing rows, read-only; descriptive)\n',
          f'MD5: {md5s}. Definitions: script docstring. SPg_flat = primary SP arm; near cliff = K/K* in {T.CLIFF_BAND}. Full per-cell/frame-bin '
          'records and other SP arms: diag.json.\n']
    # ---- D1
    md.append('## D1 round-1 detector LLR calibration (observed logloss / logloss implied by mean |LLR| of a consistent Gaussian; > 1 = over-confident)\n')
    md.append('Per-cell table, near-cliff cells. ll = mean r1_ll_in, mabs = mean r1_mabs_in, imp = mean_f implied logloss, R = ll/imp. '
              'dI = mean over paired frames of (I_in(SP) - I_in(A3)).\n')
    for name in d1:
        by = collections.defaultdict(dict)
        for r in d1[name]:
            by[(r['snr_db'], r['rho'], r['L'])][r['arm']] = r
        rows = []
        for (snr, rho, L), arms in sorted(by.items()):
            sp, a3 = arms.get('SPg_flat'), arms.get('A3')
            if not sp or not sp['near_cliff']:
                continue
            rows.append([f(snr), f(rho), L, f(sp['K_over_kstar'], 2), f(sp['mean_mabs'], 3), f(sp['mean_ll_in'], 4), f(sp['mean_implied_ll'], 4),
                         f(sp['ratio_obs_over_implied'], 3), f(a3['mean_mabs'], 3), f(a3['mean_ll_in'], 4), f(a3['mean_implied_ll'], 4),
                         f(a3['ratio_obs_over_implied'], 3), f(1 - sp['mean_ll_in'], 3), f(1 - a3['mean_ll_in'], 3), f(sp['mean_dI_sp_minus_a3_paired'], 3)])
        md.append(f'### {name}\n')
        md.append(T.tab(['SNR', 'rho', 'L', 'K/K*', 'SP mabs', 'SP ll', 'SP imp', 'SP R', 'A3 mabs', 'A3 ll', 'A3 imp', 'A3 R', 'SP I_in', 'A3 I_in', 'dI'], rows) + '\n')
    md.append('### Frame-level, pooled over near-cliff cells (fixed mean-|LLR| bins; n, mean mabs, mean ll, mean implied, R)\n')
    for key, v in d1_pool.items():
        if key.split('|')[1] not in ('A3', 'SPg_flat'):
            continue
        rows = [[f"{b['lo']:g}-{b['hi']:.0f}", b['n'], f(b.get('mean_mabs'), 3), f(b.get('mean_ll_in'), 4), f(b.get('mean_implied_ll'), 4),
                 f(b.get('ratio_obs_over_implied'), 3)] for b in v['fixed_bins'] if b['n'] >= 5]
        o = v['overall']
        md.append(f"**{key}** pooled n {o['n']}: mean mabs {f(o['mean_mabs'], 3)}, ll {f(o['mean_ll_in'], 4)}, implied {f(o['mean_implied_ll'], 4)}, R {f(o['ratio_obs_over_implied'], 3)}\n")
        md.append(T.tab(['mabs bin', 'n', 'mabs', 'll', 'implied', 'R'], rows) + '\n')
    # ---- D2
    md.append('## D2 decoder closure in MI space: P(round-1 decode correct | I_in = 1 - r1_ll_in)\n')
    aw, awf = d2['awgn_columns'], d2['awgn_frames']
    md.append(f"AWGN reference: mean-level (t1_transfer.json columns.coded, P = 1 - FER vs J_chan) I50 = {f(aw['I50_mean_level'], 4)}; frame-level (frames.npz, "
              f"{awf['n']} frames, {awf['n_q_points']} q points) I50 bins {f(awf['I50_bins'], 4)}, logistic {f(awf['I50_logistic'], 4)}.\n")
    rows = []
    for key in sorted(k for k in d2 if k.count('|') == 1):
        v = d2[key]
        rows.append([key, v['n'], f(v['mean_I_in'], 3), f(v['p_correct'], 3), f(v['I50_bins'], 4), f(v['I50_logistic'], 4), f(v['logistic_slope'], 3)])
    rows.append(['AWGN (frame-level)', awf['n'], f(awf['mean_I_in'], 3), f(awf['p_correct'], 3), f(awf['I50_bins'], 4), f(awf['I50_logistic'], 4), f(awf['logistic_slope'], 3)])
    md.append(T.tab(['pool (dataset|arm)', 'n frames', 'mean I_in', 'P(correct)', 'I50 bins', 'I50 logistic', 'slope dlogit/dI'], rows) + '\n')
    md.append('Per (dataset, arm, SNR, rho), pooled over L (SPg_flat and A3):\n')
    rows = []
    for key in sorted(k for k in d2 if k.count('|') == 3 and ('|SPg_flat|' in k or '|A3|' in k)):
        v = d2[key]
        rows.append([key, v['n'], f(v['mean_I_in'], 3), f(v['p_correct'], 3), f(v['I50_bins'], 4), f(v['I50_logistic'], 4), f(v['logistic_slope'], 3)])
    md.append(T.tab(['pool', 'n', 'mean I_in', 'P(correct)', 'I50 bins', 'I50 logistic', 'slope'], rows) + '\n')
    md.append('Overlay: P(correct) per 0.02 I_in bin (n in parentheses; "-" = n < 20).\n')
    series = [('SP boot', d2['c1_boot|SPg_flat']), ('SP map', d2['c1_map|SPg_flat']), ('A3 boot', d2['c1_boot|A3']), ('A3 map', d2['c1_map|A3']),
              ('AWGN frames', awf)]
    rows = []
    for lo in np.round(np.arange(0.30, 0.9001, BIN_W), 2):
        row = [f'{lo:.2f}']
        for _, s in series:
            b = next((b for b in s['bins'] if abs(b['lo'] - lo) < 1e-6), None)
            row.append('-' if b is None or b['n'] < MIN_N else f"{b['p']:.3f} ({b['n']})")
        rows.append(row)
    md.append(T.tab(['I_in bin lo'] + [n for n, _ in series], rows) + '\n')
    # ---- D3
    md.append('## D3 inner map eps_det1/eps_ce1 (SPg_flat; per-frame ratio, median [q25, q75]; all cells, * = near cliff)\n')
    for name, recs in d3.items():
        rows = []
        for r in sorted(recs, key=lambda r: (r['snr_db'], r['rho'], r['K'])):
            rows.append([f(r['snr_db']), f(r['rho']), r['L'], r['K'], f"{f(r['K_over_kstar'], 2)}{'*' if r['near_cliff'] else ''}",
                         f"{f(r['ratio_med'], 3)} [{f(r['ratio_q25'], 3)}, {f(r['ratio_q75'], 3)}]", f(r['ratio_of_medians'], 3), f(r['med_ce1'], 3), f(r['med_det1'], 3),
                         f(r['spearman_E_det1_over_E'], 2), f(r['spearman_E_ce1_over_E'], 2), f(r['spearman_E_ratio'], 2)])
        md.append(f'### {name}\n')
        md.append(T.tab(['SNR', 'rho', 'L', 'K', 'K/K*', 'det1/ce1 med [q25,q75]', 'med(det1)/med(ce1)', 'med ce1', 'med det1', 'rho_S(E, det1/E)',
                         'rho_S(E, ce1/E)', 'rho_S(E, det1/ce1)'], rows) + '\n')
    path.write_text('\n'.join(md))


def plots(out, d2, d3):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(1, 2, figsize=(12, 4.2))
    for lab, key, st in (('SPg_flat boot', 'c1_boot|SPg_flat', 'o-'), ('SPg_flat map', 'c1_map|SPg_flat', 's-'), ('A3 boot', 'c1_boot|A3', '^--'),
                         ('A3 map', 'c1_map|A3', 'v--'), ('AWGN frames', 'awgn_frames', 'k-')):
        b = [x for x in d2[key]['bins'] if x['n'] >= MIN_N]
        ax[0].plot([x['center'] for x in b], [x['p'] for x in b], st, ms=3, label=lab)
    ax[0].axhline(.5, color='gray', lw=.5)
    ax[0].set_xlim(.3, 1)
    ax[0].set_xlabel('I_in = 1 - r1_ll_in (per frame)')
    ax[0].set_ylabel('P(round-1 decode correct)')
    ax[0].legend(fontsize=7)
    ax[0].set_title('D2: decoder closure in MI space', fontsize=9)
    cm = plt.get_cmap('tab10')
    for i, (name, recs) in enumerate(d3.items()):
        for j, (snr, rho) in enumerate(sorted({(r['snr_db'], r['rho']) for r in recs})):
            rs = sorted([r for r in recs if r['snr_db'] == snr and r['rho'] == rho], key=lambda r: r['K'])
            ax[1].plot([r['K_over_kstar'] for r in rs], [r['ratio_med'] for r in rs], 'o-', ms=3, lw=.9, label=f'{name} {snr:g} dB rho {rho:g}',
                       color=cm((i * 6 + j) % 10))
    ax[1].set_xlabel('K / K*(1.37)')
    ax[1].set_ylabel('median eps_det1 / eps_ce1')
    ax[1].set_xscale('log')
    ax[1].legend(fontsize=6)
    ax[1].set_title('D3: inner map ratio', fontsize=9)
    fig.tight_layout()
    fig.savefig(out / 'diag.png', dpi=110)
    plt.close(fig)


if __name__ == '__main__':
    main()
