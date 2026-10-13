#!/usr/bin/env python
"""F3 analysis: FER curves (Wilson CI), high-SNR log-log slope d log10(FER)/d(SNR_dB/10) with frame-bootstrap CI,
mean P_eff per config, ordering check against P_eff.
usage: f3_analyze.py <rows_dir> <out_dir> [--lo 1e-3 --hi 1e-1 --boot 4000 --seed 20261008]
Reads rows_shard*.jsonl (A3 rows only); writes analysis.json, F3_TABLE.md, rows_compact.csv, fer_curves.png (if matplotlib).
Slope convention: slope = d log10(FER) / d(SNR_dB/10)  (negative; harvested diversity d = -slope).
Fit: OLS of log10(FER) on SNR_dB/10 over SNR cells whose point FER is in [lo, hi] (fixed set, also used in every
bootstrap replicate; replicate points with 0 errors are dropped).  Sensitivity: error-count-weighted OLS, wider range.
Bootstrap: frames resampled with replacement, SAME resampled frame set for every SNR cell and every config (frames
share message/noise streams across configs, so pairing is preserved in differences).
"""
import argparse
import csv
import glob
import json
from pathlib import Path

import numpy as np

CONFIG_ORDER = ['D1', 'N4a', 'N4b', 'J4', 'J8', 'S16']
PRED_ORDER = ['S16', 'J8', 'J4', 'N4b', 'N4a', 'D1']  # task-stated prediction (">~" between S16, J8)


def wilson(k, n, z=1.959964):
    if n == 0:
        return (np.nan, np.nan)
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (max(0., c - h), min(1., c + h))


def load(rows_dir):
    rows, dup, err = {}, 0, 0
    eigs = {}
    for f in sorted(glob.glob(str(Path(rows_dir) / 'rows_shard*.jsonl'))):
        for line in open(f):
            r = json.loads(line)
            if r['arm'] != 'A3':
                continue
            if r['status'] != 'ok':
                err += 1
                continue
            k = (r['config'], r['snr_centi_db'], r['frame'])
            dup += k in rows
            rows[k] = r
            if 'peff_eigs' in r:
                eigs.setdefault(k[0], []).append(np.concatenate([np.asarray(t, float) for t in r['peff_eigs']]))
    return rows, dup, err, eigs


def fit(x, y, w=None):
    if len(x) < 2:
        return np.nan
    if w is None:
        return float(np.polyfit(x, y, 1)[0])
    return float(np.polyfit(x, y, 1, w=np.sqrt(w))[0])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('rows_dir')
    ap.add_argument('out_dir')
    ap.add_argument('--lo', type=float, default=1e-3)
    ap.add_argument('--hi', type=float, default=1e-1)
    ap.add_argument('--boot', type=int, default=4000)
    ap.add_argument('--seed', type=int, default=20261008)
    a = ap.parse_args()
    out = Path(a.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    rows, dup, err, eigs = load(a.rows_dir)
    configs = [c for c in CONFIG_ORDER if any(k[0] == c for k in rows)]
    snrs = sorted({k[1] for k in rows})
    frames = sorted({k[2] for k in rows})
    nf = len(frames)
    # complete (config, snr, frame) grid required
    missing = [(c, s, f) for c in configs for s in snrs for f in frames if (c, s, f) not in rows]
    if missing:
        print(f'WARNING: {len(missing)} missing cells, e.g. {missing[:3]}')
    E = {c: np.full((nf, len(snrs)), np.nan) for c in configs}
    PE = {c: np.full((nf, len(snrs)), np.nan) for c in configs}
    EN = {c: np.full((nf, len(snrs)), np.nan) for c in configs}
    SG = {c: np.full((nf, len(snrs)), np.nan) for c in configs}
    fidx = {f: i for i, f in enumerate(frames)}
    sidx = {s: i for i, s in enumerate(snrs)}
    with open(out / 'rows_compact.csv', 'w', newline='') as fh:
        wr = csv.writer(fh)
        wr.writerow(['config', 'snr_db', 'frame', 'info_errors', 'decode_ok', 'peff', 'cl_energy_per_dim', 'cl_sum_g2',
                     'logloss_bits'])
        for (c, s, f), r in sorted(rows.items()):
            i, j = fidx[f], sidx[s]
            E[c][i, j] = r['info_errors'] > 0
            PE[c][i, j] = r['peff']
            EN[c][i, j] = r['cl_energy_per_dim']
            SG[c][i, j] = r['cl_sum_g2']
            wr.writerow([c, s / 100, f, r['info_errors'], int(r['decode_ok']), r['peff'],
                         f"{r['cl_energy_per_dim']:.6g}", f"{r['cl_sum_g2']:.6g}", f"{r['logloss_bits']:.5g}"])
    x = np.array([s / 100 / 10 for s in snrs])
    rng = np.random.default_rng(a.seed)
    counts = rng.multinomial(nf, np.full(nf, 1. / nf), size=a.boot).astype(float)  # (B, nf), shared by all configs

    res = dict(rows_dir=str(a.rows_dir), n_frames=nf, snr_db=[s / 100 for s in snrs], configs=configs,
               dup_rows_overwritten=dup, error_rows=err, missing_cells=len(missing), boot=a.boot, seed=a.seed,
               fit_range=[a.lo, a.hi], per_config={})
    slope_boot = {}
    for c in configs:
        k = np.nansum(E[c], axis=0)
        n = np.sum(~np.isnan(E[c]), axis=0)
        fer = k / n
        wil = [wilson(int(kk), int(nn)) for kk, nn in zip(k, n)]
        sel = (fer >= a.lo) & (fer <= a.hi)
        xs, ys = x[sel], np.log10(fer[sel])
        slope = fit(xs, ys)
        slope_w = fit(xs, ys, k[sel])
        sel_w = (fer >= a.lo) & (fer <= 0.3)
        slope_wide = fit(x[sel_w], np.log10(fer[sel_w]))
        # bootstrap (fixed point set)
        bk = counts @ np.nan_to_num(E[c])  # (B, S) errors in replicate
        bfer = bk / nf
        bs = np.full(a.boot, np.nan)
        idx = np.where(sel)[0]
        for b in range(a.boot):
            ok = idx[bk[b, idx] > 0]
            if len(ok) >= 2:
                bs[b] = np.polyfit(x[ok], np.log10(bfer[b, ok]), 1)[0]
        slope_boot[c] = bs
        ci = [float(np.nanpercentile(bs, 2.5)), float(np.nanpercentile(bs, 97.5))] if np.isfinite(bs).any() else [np.nan] * 2
        pe = np.nanmean(PE[c], axis=0)
        res['per_config'][c] = dict(
            n=[int(v) for v in n], errors=[int(v) for v in k], fer=[float(v) for v in fer],
            wilson=[[float(a_), float(b_)] for a_, b_ in wil], mean_peff=[float(v) for v in pe],
            mean_energy_per_dim=[float(v) for v in np.nanmean(EN[c], axis=0)],
            p05_energy_per_dim=[float(v) for v in np.nanpercentile(EN[c], 5, axis=0)],
            mean_sum_g2=[float(v) for v in np.nanmean(SG[c], axis=0)],
            fit_snr_db=[float(v * 10) for v in xs], fit_fer=[float(v) for v in fer[sel]],
            slope=slope, slope_ci95=ci, slope_boot_valid=int(np.isfinite(bs).sum()),
            slope_weighted=slope_w, slope_wide_range=slope_wide, wide_fit_snr_db=[float(v * 10) for v in x[sel_w]],
            diversity_from_slope=-slope, diversity_ci95=[-ci[1], -ci[0]])

    # sensitivity: common SNR window (same cells for every config) and P_eff threshold
    cw = [snrs.index(v) for v in (800, 900, 1000) if v in snrs]
    for c in configs:
        r = res['per_config'][c]
        fer = np.array(r['fer'])
        if len(cw) >= 2 and np.all(fer[cw] > 0):
            r['slope_common_8_10'] = fit(x[cw], np.log10(fer[cw]))
            bk = counts @ np.nan_to_num(E[c])
            bs = np.array([np.polyfit(x[cw], np.log10(bk[b, cw] / nf), 1)[0] if np.all(bk[b, cw] > 0) else np.nan
                           for b in range(a.boot)])
            r['slope_common_8_10_ci95'] = [float(np.nanpercentile(bs, 2.5)), float(np.nanpercentile(bs, 97.5))]
        else:
            r['slope_common_8_10'] = np.nan
            r['slope_common_8_10_ci95'] = [np.nan, np.nan]
    thr = {}
    for c in configs:
        thr[c] = {}
        for snr_db in (10, 14):
            s2 = 10 ** (-snr_db / 10)
            thr[c][str(snr_db)] = {str(T): float(np.mean([np.count_nonzero(e / s2 > T) for e in eigs[c]]))
                                   for T in (1, 10, 100)} if c in eigs else None
    res['peff_threshold_sensitivity_mean'] = thr
    # ordering check
    def at(c, snr_db, key):
        return res['per_config'][c][key][snrs.index(int(round(snr_db * 100)))]
    snr_lo, snr_hi = (10, 14) if (1000 in snrs and 1400 in snrs) else (snrs[len(snrs) // 2] / 100, snrs[-1] / 100)
    peff10 = {c: at(c, snr_lo, 'mean_peff') for c in configs}
    peff14 = {c: at(c, snr_hi, 'mean_peff') for c in configs}
    by_peff = sorted(configs, key=lambda c: -peff10[c])
    by_slope = sorted(configs, key=lambda c: res['per_config'][c]['slope'])  # most negative first
    pairs = []
    for i in range(len(PRED_ORDER) - 1):
        A, B = PRED_ORDER[i], PRED_ORDER[i + 1]
        if A in slope_boot and B in slope_boot:
            diff = slope_boot[B] - slope_boot[A]  # >0 <=> |slope_A| > |slope_B| (A steeper)
            ok = np.isfinite(diff)
            pairs.append(dict(steeper_predicted=A, shallower_predicted=B, n_valid=int(ok.sum()),
                              frac_boot_A_steeper=float(np.mean(diff[ok] > 0)) if ok.any() else None,
                              diff_ci95=[float(np.percentile(diff[ok], 2.5)), float(np.percentile(diff[ok], 97.5))] if ok.any() else None))
    # rank correlation (Spearman) between P_eff and |slope|
    pe = np.array([peff10[c] for c in configs])
    dd = np.array([-res['per_config'][c]['slope'] for c in configs])
    okc = np.isfinite(dd)
    if okc.sum() >= 3:
        r1 = np.argsort(np.argsort(pe[okc])); r2 = np.argsort(np.argsort(dd[okc]))
        spearman = float(np.corrcoef(r1, r2)[0, 1])
    else:
        spearman = None
    res['ordering'] = dict(snr_lo=snr_lo, snr_hi=snr_hi, peff_lo=peff10, peff_hi=peff14, order_by_peff_lo=by_peff,
                           order_by_steepness=by_slope, predicted_order=PRED_ORDER, spearman_peff_vs_diversity=spearman,
                           adjacent_pairs_in_predicted_order=pairs)
    (out / 'analysis.json').write_text(json.dumps(res, indent=1) + '\n')

    # markdown
    L = []
    L.append(f'# F3 diversity-slope analysis (A3 true-H, expected-power clustered law)\n')
    L.append(f'rows: {a.rows_dir} | frames={nf} per cell | SNR={res["snr_db"]} | boot={a.boot} seed={a.seed} | '
             f'dup={dup} err_rows={err} missing={len(missing)}\n')
    L.append(f'slope = d log10(FER)/d(SNR_dB/10) (negative; diversity d = -slope); OLS on cells with FER in '
             f'[{a.lo:g},{a.hi:g}], CI = 95% frame bootstrap over the fixed point set.\n')
    L.append(f'| config | mean P_eff({snr_lo:g}dB) | mean P_eff({snr_hi:g}dB) | slope [95% CI] | d=-slope | fit pts (dB) | '
             f'FER@{snr_lo:g} [Wilson] | FER@{snr_hi:g} [Wilson] |')
    L.append('|---|---|---|---|---|---|---|---|')
    for c in configs:
        r = res['per_config'][c]
        j10, j14 = snrs.index(int(round(snr_lo * 100))), snrs.index(int(round(snr_hi * 100)))
        fmt = lambda j: f"{r['fer'][j]:.4g} [{r['wilson'][j][0]:.2g},{r['wilson'][j][1]:.2g}] ({r['errors'][j]}/{r['n'][j]})"  # noqa: E731
        L.append(f"| {c} | {peff10[c]:.2f} | {peff14[c]:.2f} | {r['slope']:.2f} [{r['slope_ci95'][0]:.2f}, {r['slope_ci95'][1]:.2f}] | "
                 f"{-r['slope']:.2f} | {','.join(f'{v:g}' for v in r['fit_snr_db'])} ({len(r['fit_snr_db'])}) | {fmt(j10)} | {fmt(j14)} |")
    L.append('\nSensitivity (slope):\n')
    L.append('| config | OLS [lo,hi] | error-weighted [lo,hi] | OLS FER in [lo,0.3] | pts (wide) | valid boot |')
    L.append('|---|---|---|---|---|---|')
    for c in configs:
        r = res['per_config'][c]
        L.append(f"| {c} | {r['slope']:.2f} | {r['slope_weighted']:.2f} | {r['slope_wide_range']:.2f} | "
                 f"{','.join(f'{v:g}' for v in r['wide_fit_snr_db'])} | {r['slope_boot_valid']}/{a.boot} |")
    L.append('\nCommon-window slope (cells 8,9,10 dB for every config; 95% frame bootstrap):\n')
    for c in configs:
        r = res['per_config'][c]
        L.append(f"- {c}: {r['slope_common_8_10']:.2f} [{r['slope_common_8_10_ci95'][0]:.2f}, {r['slope_common_8_10_ci95'][1]:.2f}]")
    L.append('\nMean P_eff vs threshold T (count gamma_k = lambda_k/sigma2 > T), T=1/10/100:\n')
    L.append('| config | 10 dB | 14 dB |')
    L.append('|---|---|---|')
    for c in configs:
        t = res['peff_threshold_sensitivity_mean'][c]
        if t:
            L.append(f"| {c} | " + ' / '.join(f"{v:.2f}" for v in t['10'].values()) + ' | ' + ' / '.join(f"{v:.2f}" for v in t['14'].values()) + ' |')
    L.append('\nFER by SNR (errors/n):\n')
    L.append('| config | ' + ' | '.join(f'{s / 100:g}' for s in snrs) + ' |')
    L.append('|---|' + '---|' * len(snrs))
    for c in configs:
        r = res['per_config'][c]
        L.append(f'| {c} | ' + ' | '.join(f"{r['fer'][j]:.4g} ({r['errors'][j]})" for j in range(len(snrs))) + ' |')
    L.append('\nMean P_eff by SNR:\n')
    L.append('| config | ' + ' | '.join(f'{s / 100:g}' for s in snrs) + ' |')
    L.append('|---|' + '---|' * len(snrs))
    for c in configs:
        L.append(f'| {c} | ' + ' | '.join(f"{v:.2f}" for v in res['per_config'][c]['mean_peff']) + ' |')
    L.append('\nChannel energy per dim (||H||_F^2/N): mean / p05 at lowest SNR cell:\n')
    for c in configs:
        r = res['per_config'][c]
        L.append(f"- {c}: mean {r['mean_energy_per_dim'][0]:.3f}, p05 {r['p05_energy_per_dim'][0]:.3f}, mean sum|g|^2 {r['mean_sum_g2'][0]:.3f}")
    L.append(f"\nOrdering: by mean P_eff({snr_lo:g}dB) = {' > '.join(by_peff)}; by steepness (-slope) = {' > '.join(by_slope)}; "
             f"predicted = {' >~ '.join(PRED_ORDER)}; Spearman(P_eff, d) = {spearman}\n")
    L.append('| predicted steeper | predicted shallower | P(boot: steeper really steeper) | CI of slope_B - slope_A |')
    L.append('|---|---|---|---|')
    for p in pairs:
        L.append(f"| {p['steeper_predicted']} | {p['shallower_predicted']} | {p['frac_boot_A_steeper']} | {p['diff_ci95']} |")
    (out / 'F3_TABLE.md').write_text('\n'.join(L) + '\n')
    print('\n'.join(L))

    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(1, 2, figsize=(12, 4.5))
        for c in configs:
            r = res['per_config'][c]
            fer = np.array(r['fer']); lo = np.array([w[0] for w in r['wilson']]); hi = np.array([w[1] for w in r['wilson']])
            m = fer > 0
            xs_db = np.array(res['snr_db'])
            ax[0].errorbar(xs_db[m], fer[m], yerr=[fer[m] - lo[m], hi[m] - fer[m]], marker='o', ms=3, capsize=2,
                           label=f"{c} (P_eff10={peff10[c]:.1f}, slope {r['slope']:.2f})")
        ax[0].set_yscale('log'); ax[0].set_xlabel('SNR (dB)'); ax[0].set_ylabel('FER (A3, true H)')
        ax[0].axhspan(a.lo, a.hi, color='0.9', zorder=0); ax[0].legend(fontsize=7); ax[0].grid(alpha=.3)
        for c in configs:
            r = res['per_config'][c]
            dl, dh = r['diversity_ci95']
            ax[1].errorbar(peff10[c], r['diversity_from_slope'], yerr=[[max(0., r['diversity_from_slope'] - dl)],
                           [max(0., dh - r['diversity_from_slope'])]], marker='o', capsize=2)
            ax[1].annotate(c, (peff10[c], -r['slope']))
        ax[1].set_xlabel(f'mean P_eff({snr_lo:g} dB) from truth'); ax[1].set_ylabel('fitted diversity d = -slope'); ax[1].grid(alpha=.3)
        fig.tight_layout(); fig.savefig(out / 'fer_curves.png', dpi=130)
    except Exception as e:  # plotting is optional
        print('plot skipped:', repr(e))


if __name__ == '__main__':
    main()
