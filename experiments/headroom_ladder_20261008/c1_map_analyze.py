#!/usr/bin/env python
"""Part A analysis (diversity-vs-bootstrapping trade-off map).  Input: out/c1_map rows (driver_c1.py, arms A3 + SPg_flat, rho .3, genie
delays, L in 2..32).  Output: <out-dir>/MAP_ANALYSIS.md, map_analysis.json, c1_map_fer.png.
usage: c1_map_analyze.py --out-dir DIR [--B 4000] [--boot-analysis .../c1_boot/analysis/analysis.json] <run dir>

K*(g) = b / ((1 - b) s),  s = (s2 + 1 - rho)/(rho N),  b = (1 - rho)/g - s2   (= c1_analyze.kstar_shr(g, rho, s2, P = 1); cross-checked below).
g = gamma_shr of SPg_flat at level 0.5 read from c1_boot analysis.json (fitq['SPg_flat|0.5']['gamma_shr']).
FER = info_errors > 0; Wilson 95% CI (analyze.wilson).  Frames are paired across L (message/noise shared), SNR and arm.
Non-monotone SP test: (a) naive  L_min = last argmin of FER over L; one-sided exact McNemar FER(L_edge) > FER(L_min) for both edges;
(b) split-sample  L_min chosen on even frames, tested on odd frames (removes the argmin selection bias).
Cliff: K_c(level) = K = 8L where FER first rises through `level` after its (last) minimum, linear interpolation in K; 95% CI by frame bootstrap.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import math
from pathlib import Path
import sys

import numpy as np
from scipy import stats

import analyze
import c1_analyze as ca

N = 1024
RHO = 0.3


def md5(path):
    h = hashlib.md5()
    with open(path, 'rb') as s:
        for b in iter(lambda: s.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def kstar_g(g, rho, s2):
    s = (s2 + 1 - rho) / (rho * N)
    b = (1 - rho) / g - s2
    if b <= 0:
        return 0.
    if b >= 1:
        return math.inf
    return b / ((1 - b) * s)


def crossing_K(fer, Ks, level):
    fer = np.asarray(fer, float)
    i0 = int(np.flatnonzero(fer == fer.min())[-1])
    if fer[i0] >= level:
        return -math.inf
    for j in range(i0 + 1, len(Ks)):
        if fer[j] >= level:
            a, b = fer[j - 1], fer[j]
            return float(Ks[j - 1] + (level - a) / (b - a) * (Ks[j] - Ks[j - 1]))
    return math.inf


def mcnemar_gt(fail_a, fail_b):
    """one-sided exact p for P(a fails & b ok) > P(a ok & b fails); returns (b, c, p)."""
    b = int(np.sum(fail_a & ~fail_b))
    c = int(np.sum(~fail_a & fail_b))
    n = b + c
    return b, c, (1.0 if n == 0 else float(stats.binom.sf(b - 1, n, .5)))


def fk(x):
    return '>256' if x == math.inf else '<16' if x == -math.inf else f'{x:.0f}'


def tab(head, rows):
    return '\n'.join(['| ' + ' | '.join(head) + ' |', '|' + '|'.join(['---'] * len(head)) + '|'] + ['| ' + ' | '.join(str(x) for x in r) + ' |' for r in rows])


def clean(o):
    if isinstance(o, dict):
        return {str(k): clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [clean(v) for v in o]
    if isinstance(o, np.ndarray):
        return clean(o.tolist())
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    if isinstance(o, (float, np.floating)):
        o = float(o)
        return None if math.isnan(o) else ('+inf' if o == math.inf else '-inf' if o == -math.inf else o)
    return o


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument('dir')
    ap.add_argument('--out-dir', type=Path, required=True)
    ap.add_argument('--B', type=int, default=4000)
    ap.add_argument('--seed', type=int, default=20261009)
    ap.add_argument('--boot-analysis', type=Path, default=Path(__file__).resolve().parent / 'out' / 'c1_boot' / 'analysis' / 'analysis.json')
    ap.add_argument('--no-plots', action='store_true')
    a = ap.parse_args(argv)
    a.out_dir.mkdir(parents=True, exist_ok=True)
    files = sorted(Path(a.dir).glob('rows_shard*.jsonl'))
    cols, seen, n_rows, n_err, dup = collections.defaultdict(list), set(), 0, 0, 0
    for f in files:
        for line in open(f):
            if not line.strip():
                continue
            r = json.loads(line)
            n_rows += 1
            if r['status'] != 'ok':
                n_err += 1
                continue
            key = (r['arm'], r['snr_centi_db'], r['rho_permille'], r['L'], r['frame'])
            if key in seen:
                dup += 1
                continue
            seen.add(key)
            for k in ('arm', 'snr_centi_db', 'rho_permille', 'L', 'frame', 'info_errors', 'logloss_bits', 'eps_ce1', 'e_real'):
                cols[k].append(r.get(k, np.nan))
    c = {k: np.array(v) for k, v in cols.items()}
    snrs = sorted(set(c['snr_centi_db'].tolist()))
    Ls = sorted(set(c['L'].tolist()))
    Ks = np.array([8 * L for L in Ls], float)
    arms = ['A3', 'SPg_flat']
    frames = None
    for s in snrs:
        for L in Ls:
            for ar in arms:
                m = (c['arm'] == ar) & (c['snr_centi_db'] == s) & (c['L'] == L)
                fs = set(c['frame'][m].tolist())
                frames = fs if frames is None else frames & fs
    frames = sorted(frames)
    nF, nL = len(frames), len(Ls)
    pos = {f: i for i, f in enumerate(frames)}
    fail = {}
    for s in snrs:
        for ar in arms:
            F = np.zeros((nL, nF), bool)
            for i, L in enumerate(Ls):
                m = (c['arm'] == ar) & (c['snr_centi_db'] == s) & (c['L'] == L)
                idx = np.array([pos.get(f, -1) for f in c['frame'][m]])
                ok = idx >= 0
                F[i, idx[ok]] = c['info_errors'][m][ok] > 0
            fail[(ar, s)] = F
    rho = RHO
    # g from c1_boot
    boot = json.loads(a.boot_analysis.read_text())
    g_used = float(boot['fitq']['SPg_flat|0.5']['gamma_shr'])
    g_rms = float(boot['fitq']['SPg_flat|0.5']['rms_shr'])
    chk = max(abs(kstar_g(g_used, rho, ca.sig2(s)) - ca.kstar_shr(g_used, rho, ca.sig2(s), 1.)) / kstar_g(g_used, rho, ca.sig2(s)) for s in snrs)
    R = dict(_argv=sys.argv, inputs={str(f): md5(f) for f in files}, n_rows=n_rows, n_error_rows=n_err, duplicates=dup, frames=nF, snr_db=[s / 100 for s in snrs],
             rho=rho, L=Ls, K=Ks.tolist(), g_used=g_used, g_source=f'{a.boot_analysis} fitq[SPg_flat|0.5].gamma_shr (rms log err {g_rms:.3f})',
             kstar_formula_crosscheck_max_rel_diff=float(chk), B=a.B, seed=a.seed)
    md = ['# C1 trade-off map (Part A)\n',
          f'rows {n_rows} (error rows {n_err}, duplicates {dup}); frames per cell {nF}; rho {rho}; SNR {R["snr_db"]} dB; L {Ls} (K = 8L = {[int(k) for k in Ks]}); '
          f'arms {arms}; genie delays; bootstrap B={a.B} frames (joint over L/SNR/arm), seed {a.seed}.\n',
          f'**g used for K*(g): {g_used:.2f}** (c1_boot, SPg_flat, level 0.5, shrinkage-corrected fit, rms log err {g_rms:.3f}; K* = b/((1-b)s) == c1_analyze.kstar_shr(P=1), '
          f'max rel diff {chk:.1e}).\n']
    rng = np.random.default_rng(a.seed)
    boot_idx = rng.integers(0, nF, (a.B, nF))
    bfer = {k: np.stack([F[:, boot_idx[b0:b0 + 500]].mean(-1) for b0 in range(0, a.B, 500)], axis=1).reshape(nL, a.B) for k, F in fail.items()}
    fer = {k: F.mean(1) for k, F in fail.items()}
    kf = {k: F.sum(1).astype(int) for k, F in fail.items()}
    # ------------------------------------------------------------------ 1 tables
    md.append('## 1. FER vs L (Wilson 95% CI)\n')
    R['fer'] = {}
    for s in snrs:
        s2 = ca.sig2(s)
        ks = kstar_g(g_used, rho, s2)
        rows = []
        for ar in arms:
            cells = []
            for i in range(nL):
                lo, hi = analyze.wilson(int(kf[(ar, s)][i]), nF)
                cells.append(f'{fer[(ar, s)][i]:.3f} [{lo:.3f},{hi:.3f}]')
            rows.append([ar] + cells)
            R['fer'][f'{ar}|{s / 100:g}'] = dict(fer=fer[(ar, s)].tolist(), k=kf[(ar, s)].tolist(), n=nF)
        md.append(f'### SNR {s / 100:g} dB (sigma2 {s2:.4f}); K*(g={g_used:.2f}) = {ks:.0f}, L* = {ks / 8:.1f}\n')
        md.append(tab(['arm'] + [f'L={L}' for L in Ls], rows) + '\n')
    # ------------------------------------------------------------------ 2 A3 monotone
    md.append('## 2. A3 (true H) FER vs L\n')
    R['a3'] = {}
    for s in snrs:
        f3 = fer[('A3', s)]
        F3 = fail[('A3', s)]
        inc, sig = [], []
        for i in range(nL - 1):
            b, cc, p = mcnemar_gt(F3[i + 1], F3[i])
            if kf[('A3', s)][i + 1] > kf[('A3', s)][i]:
                inc.append(f'{Ls[i]}->{Ls[i + 1]} ({kf[("A3", s)][i]}->{kf[("A3", s)][i + 1]})')
            if p < 0.01:
                sig.append(f'{Ls[i]}->{Ls[i + 1]} (p={p:.1e})')
        rs = stats.spearmanr(np.arange(nL), f3)
        b, cc, p_end = mcnemar_gt(F3[0], F3[-1])
        # trend over blocks: Cochran-Armitage-like via Spearman on L vs FER (point) and McNemar L=2 vs L=32 (one-sided: FER(2) > FER(32))
        R['a3'][f'{s / 100:g}'] = dict(fer=f3.tolist(), point_increases=inc, significant_increases=sig, spearman=float(rs.statistic),
                                       fer_L2_gt_L32=dict(b=b, c=cc, p=p_end))
        md.append(f'- SNR {s / 100:g} dB: A3 FER {" ".join(f"{x:.3f}" for x in f3)}; Spearman(L, FER) {rs.statistic:.2f}; point-estimate increases {inc or "none"}; '
                  f'significant adjacent increases (paired McNemar p<.01) {sig or "none"}; FER(L=2) > FER(L=32): {b}/{cc}, p={p_end:.1e}\n')
    # ------------------------------------------------------------------ 3 SP non-monotone
    md.append('## 3. SP (SPg_flat) FER vs L: interior minimum?\n')
    md.append('naive: L_min = last argmin of FER over L; p_left = one-sided exact McNemar FER(L=2) > FER(L_min); p_right = FER(L=32) > FER(L_min).  split-sample: L_min chosen on even-index frames, '
              'test on odd-index frames (selection-bias free).  P(L_min interior) = bootstrap probability that the argmin (last) lies strictly inside the grid; '
              'P(L_min > 2) = bootstrap probability that it is not the smallest L.\n')
    R['sp_min'] = {}
    rows = []
    for s in snrs:
        F = fail[('SPg_flat', s)]
        f = fer[('SPg_flat', s)]
        i0 = int(np.flatnonzero(f == f.min())[-1])
        bl, cl, pl = mcnemar_gt(F[0], F[i0])
        br, cr, pr = mcnemar_gt(F[-1], F[i0])
        ev, od = F[:, 0::2], F[:, 1::2]
        i_ev = int(np.flatnonzero(ev.mean(1) == ev.mean(1).min())[-1])
        sb, sc, sp = mcnemar_gt(od[0], od[i_ev])
        # bootstrap argmin
        am = np.array([int(np.flatnonzero(bfer[('SPg_flat', s)][:, b] == bfer[('SPg_flat', s)][:, b].min())[-1]) for b in range(a.B)])
        p_int = float(np.mean((am > 0) & (am < nL - 1)))
        p_gt2 = float(np.mean(am > 0))
        gap = fer[('SPg_flat', s)][0] - f.min()
        gap_boot = bfer[('SPg_flat', s)][0] - bfer[('SPg_flat', s)].min(0)
        R['sp_min'][f'{s / 100:g}'] = dict(L_min=Ls[i0], fer_min=float(f.min()), fer_L2=float(f[0]), fer_L32=float(f[-1]), p_left=pl, p_right=pr, b_left=(bl, cl),
                                          split_L_min_even=Ls[i_ev], split_p_odd=sp, split_bc=(sb, sc), p_boot_interior=p_int, p_boot_gt2=p_gt2,
                                          gap_L2_minus_min=float(gap), gap_ci=[float(np.percentile(gap_boot, 2.5)), float(np.percentile(gap_boot, 97.5))])
        rows.append([f'{s / 100:g}', f'{Ls[i0]}', f'{f.min():.3f}', f'{f[0]:.3f}', f'{gap:.3f} [{np.percentile(gap_boot, 2.5):.3f},{np.percentile(gap_boot, 97.5):.3f}]',
                     f'{bl}/{cl} p={pl:.2g}', f'{br}/{cr} p={pr:.1e}', f'L={Ls[i_ev]}: {sb}/{sc} p={sp:.2g}', f'{p_int:.3f}', f'{p_gt2:.3f}'])
    md.append(tab(['SNR', 'L_min', 'FER_min', 'FER(L=2)', 'FER(2) - FER_min [95% CI]', 'naive left b/c', 'naive right b/c', 'split-sample (odd frames)', 'P(L_min interior)', 'P(L_min>2)'], rows) + '\n')
    # ------------------------------------------------------------------ 4 SP vs A3 gap
    md.append('## 4. SP - A3 gap per L (paired McNemar, b = SP fails only, c = A3 fails only; * p<.01)\n')
    rows = []
    for s in snrs:
        cell = []
        for i in range(nL):
            b = int(np.sum(fail[('SPg_flat', s)][i] & ~fail[('A3', s)][i]))
            cc = int(np.sum(~fail[('SPg_flat', s)][i] & fail[('A3', s)][i]))
            p = analyze.mcnemar(b, cc)
            cell.append(f'{b}/{cc}' + ('*' if p < .01 else ''))
        rows.append([f'{s / 100:g}'] + cell)
    md.append(tab(['SNR'] + [f'L={L}' for L in Ls], rows) + '\n')
    # ------------------------------------------------------------------ 5 cliff
    md.append('## 5. Cliff location vs K*(g)\n')
    md.append(f'K*(g={g_used:.2f}); K_c(level) with 95% bootstrap CI; g_impl = (1-rho)/(s2 + K_c s/(1+K_c s)) = SINR threshold implied by K_c; K*(g) also shown for g = 1.3 / 1.4.  '
              f'"within CI" = K*(g) inside the K_c bootstrap interval.\n')
    R['cliff'] = {}
    rows = []
    for s in snrs:
        s2 = ca.sig2(s)
        sc_ = (s2 + 1 - rho) / (rho * N)
        for lev in (0.1, 0.5):
            kc = crossing_K(fer[('SPg_flat', s)], Ks, lev)
            bs = np.array([crossing_K(bfer[('SPg_flat', s)][:, b], Ks, lev) for b in range(a.B)])
            lo, hi = float(np.percentile(bs, 2.5, method='nearest')), float(np.percentile(bs, 97.5, method='nearest'))
            ks = kstar_g(g_used, rho, s2)
            gi = (1 - rho) / (s2 + kc * sc_ / (1 + kc * sc_)) if np.isfinite(kc) and kc > 0 else float('nan')
            R['cliff'][f'{s / 100:g}|{lev}'] = dict(kc=kc, ci=[lo, hi], kstar=ks, kstar_13=kstar_g(1.3, rho, s2), kstar_14=kstar_g(1.4, rho, s2), g_impl=gi,
                                                   within_ci=bool(lo <= ks <= hi), log_ratio=float(math.log(ks / kc)) if np.isfinite(kc) and kc > 0 else None)
            rows.append([f'{s / 100:g}', lev, fk(kc), f'[{fk(lo)},{fk(hi)}]', f'{ks:.0f} (L* {ks / 8:.1f})', f'{kstar_g(1.3, rho, s2):.0f} / {kstar_g(1.4, rho, s2):.0f}',
                         'n/a' if not np.isfinite(gi) else f'{gi:.2f}', 'yes' if lo <= ks <= hi else 'no',
                         'n/a' if not (np.isfinite(kc) and kc > 0) else f'{math.log(ks / kc):+.2f}'])
    md.append(tab(['SNR', 'level', 'K_c', 'K_c 95% CI', 'K*(g)', 'K*(1.3) / K*(1.4)', 'g_impl', 'K* in CI', 'ln(K*/K_c)'], rows) + '\n')
    # ------------------------------------------------------------------ 5b floor-robust cliff definitions
    md.append('### 5b. Decoder-waterfall-robust cliff definitions\n')
    md.append('The level-0.5 crossing of the raw SP FER is confounded by the decoder waterfall (SP FER is already ~.44 at L=2..4 at 5 dB).  Two floor-robust variants: '
              '(cond) SP-specific failure rate P(SP fails | A3 decodes), level 0.5 (removes frames lost to channel diversity / the code itself); '
              '(rel) raw SP FER crossing the midpoint (1 + FER_min)/2 above its own minimum.  K_c by linear interpolation in K, 95% bootstrap CI over frames.\n')
    rows = []
    for s in snrs:
        s2 = ca.sig2(s)
        Fs, Fa = fail[('SPg_flat', s)], fail[('A3', s)]
        cf, okm = (Fs & ~Fa), ~Fa
        rate = cf.sum(1) / okm.sum(1)
        brate = np.stack([cf[:, boot_idx[b]].sum(-1) / okm[:, boot_idx[b]].sum(-1) for b in range(a.B)], axis=1)
        kc_c = crossing_K(rate, Ks, 0.5)
        bs_c = np.array([crossing_K(brate[:, b], Ks, 0.5) for b in range(a.B)])
        f = fer[('SPg_flat', s)]
        kc_r = crossing_K(f, Ks, (1 + f.min()) / 2)
        bf = bfer[('SPg_flat', s)]
        bs_r = np.array([crossing_K(bf[:, b], Ks, (1 + bf[:, b].min()) / 2) for b in range(a.B)])
        ks = kstar_g(g_used, rho, s2)
        sc_ = (s2 + 1 - rho) / (rho * N)
        for name, kc, bs, extra in (('cond (level .5)', kc_c, bs_c, ' '.join(f'{x:.3f}' for x in rate)), (f'rel (level {(1 + f.min()) / 2:.3f})', kc_r, bs_r, '')):
            lo, hi = float(np.percentile(bs, 2.5, method='nearest')), float(np.percentile(bs, 97.5, method='nearest'))
            gi = (1 - rho) / (s2 + kc * sc_ / (1 + kc * sc_)) if np.isfinite(kc) and kc > 0 else float('nan')
            R['cliff'][f'{s / 100:g}|{name.split()[0]}'] = dict(kc=kc, ci=[lo, hi], kstar=ks, g_impl=gi, within_ci=bool(lo <= ks <= hi),
                                                              log_ratio=float(math.log(ks / kc)) if np.isfinite(kc) and kc > 0 else None, rate=rate.tolist() if name.startswith('cond') else None)
            rows.append([f'{s / 100:g}', name, fk(kc), f'[{fk(lo)},{fk(hi)}]', f'{ks:.0f} (L* {ks / 8:.1f})', 'n/a' if not np.isfinite(gi) else f'{gi:.2f}', 'yes' if lo <= ks <= hi else 'no',
                         'n/a' if not (np.isfinite(kc) and kc > 0) else f'{math.log(ks / kc):+.2f}', extra])
    md.append(tab(['SNR', 'definition', 'K_c', 'K_c 95% CI', 'K*(g)', 'g_impl', 'K* in CI', 'ln(K*/K_c)', 'cond. rate at L=' + ','.join(map(str, Ls))], rows) + '\n')
    # ------------------------------------------------------------------ 6 first-pass eps
    md.append('## 6. First-pass error eps1 (SPg_flat) vs shrinkage-corrected prediction eps = Ks/(1+Ks)\n')
    rows = []
    R['eps'] = {}
    for s in snrs:
        s2 = ca.sig2(s)
        sc_ = (s2 + 1 - rho) / (rho * N)
        obs, pred = [], []
        for L in Ls:
            m = (c['arm'] == 'SPg_flat') & (c['snr_centi_db'] == s) & (c['L'] == L)
            obs.append(float(np.mean(c['eps_ce1'][m])))
            pred.append(8 * L * sc_ / (1 + 8 * L * sc_))
        R['eps'][f'{s / 100:g}'] = dict(obs=obs, pred=pred)
        rows.append([f'{s / 100:g}', 'obs'] + [f'{x:.3f}' for x in obs])
        rows.append([f'{s / 100:g}', 'pred'] + [f'{x:.3f}' for x in pred])
        rows.append([f'{s / 100:g}', 'obs/pred'] + [f'{o / p:.2f}' for o, p in zip(obs, pred)])
    md.append(tab(['SNR', 'row'] + [f'L={L}' for L in Ls], rows) + '\n')
    (a.out_dir / 'MAP_ANALYSIS.md').write_text('\n'.join(md) + '\n')
    (a.out_dir / 'map_analysis.json').write_text(json.dumps(clean(R), indent=1) + '\n')
    if not a.no_plots:
        try:
            import matplotlib
            matplotlib.use('Agg')
            import matplotlib.pyplot as plt
            fig, axs = plt.subplots(1, len(snrs), figsize=(5.2 * len(snrs), 3.8), sharey=True)
            for ax, s in zip(np.atleast_1d(axs), snrs):
                for ar, col in (('A3', 'tab:blue'), ('SPg_flat', 'tab:red')):
                    lo_hi = np.array([analyze.wilson(int(k), nF) for k in kf[(ar, s)]])
                    ax.errorbar(Ls, fer[(ar, s)], yerr=[np.clip(fer[(ar, s)] - lo_hi[:, 0], 0, None), np.clip(lo_hi[:, 1] - fer[(ar, s)], 0, None)], color=col, marker='o', ms=3, capsize=2, label=ar)
                ks = kstar_g(g_used, rho, ca.sig2(s))
                ax.axvline(ks / 8, color='k', ls='--', lw=.8, label=f'K*(g={g_used:.2f})/8')
                ax.set_yscale('symlog', linthresh=0.01)
                ax.set_title(f'SNR {s / 100:g} dB, rho {rho}')
                ax.set_xlabel('L (K = 8L)')
                ax.grid(alpha=.3)
            np.atleast_1d(axs)[0].set_ylabel('FER')
            np.atleast_1d(axs)[0].legend(fontsize=8)
            fig.tight_layout()
            fig.savefig(a.out_dir / 'c1_map_fer.png', dpi=140)
        except Exception as e:  # plots are optional
            print('plot skipped:', repr(e))
    print('\n'.join(md))


if __name__ == '__main__':
    main()
