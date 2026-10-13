#!/usr/bin/env python
"""Part B analysis (3GPP TDL realism).  Two modes:
  pick :  c1_tdl_analyze.py --mode pick --dev DIR --out-dir DIR [--write-theta FILE]
          dev rows (frames 1000..1099, arms SPcb_t<theta>, SPg_flat): mean logloss per theta (mean over conditions of per-condition mean),
          argmin -> frozen theta JSON.  Conditions = profile x scale x SNR x rho (24).
  report: c1_tdl_analyze.py --mode report --test DIR --out-dir DIR [--dev DIR]
          per (profile, scale, SNR, rho): taps, K = 8T, K*(g), FER (Wilson) per arm, paired McNemar tests, cliff flags, SPcb acquisition diagnostics.
K*(g) = b/((1-b)s), s = (s2+1-rho)/(rho N), b = (1-rho)/g - s2, g = c1_boot SPg_flat level-0.5 shrinkage fit (read from analysis.json).  The flat-prior
first-pass error eps = K s/(1+K s) does not depend on the tap-power distribution (sum of prior variances 1 = sum of true variances 1), so K*(g)
applies to non-uniform TDL powers with K = 8 x (number of columns' taps).
past-cliff flags: predicted = K/K* >= 1;  cliff = FER >= 0.5;  degraded = FER_SP - FER_A3 >= 0.05 and paired McNemar p < .01;
sinr_lt_g = mean over frames of 1{(1-rho)/(sigma2 + eps_ce1) < g} (first-pass SINR below the threshold g).
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

import analyze
import c1_analyze as ca
from c1_map_analyze import kstar_g, mcnemar_gt, tab, clean, md5

N = 1024
FIELDS = ('info_errors', 'logloss_bits', 'eps_ce1', 'e_real', 'cb_n_cand', 'cb_n_kept', 'cb_hit', 'cb_false', 'cb_cand_hit', 'cb_missed_energy',
          'n_cols', 'n_taps_kept', 'b_missed_energy', 'b_n_fit_distinct', 'triggered', 'seconds')


def load(d):
    files = sorted(Path(d).glob('rows_shard*.jsonl'))
    rows, seen, n_err, dup = [], set(), 0, 0
    for f in files:
        for line in open(f):
            if not line.strip():
                continue
            r = json.loads(line)
            if r['status'] != 'ok':
                n_err += 1
                continue
            key = (r['arm'], r['config'], r['rho_permille'], r['snr_centi_db'], r['frame'])
            if key in seen:
                dup += 1
                continue
            seen.add(key)
            rows.append(r)
    return files, rows, n_err, dup


def conditions(rows):
    return sorted({(r['config'], r['snr_centi_db'], r['rho_permille']) for r in rows})


# ----------------------------------------------------------------------------------------------- pick
def pick(a):
    files, rows, n_err, dup = load(a.dev)
    arms = sorted({r['arm'] for r in rows})
    thetas = sorted(float(x[len('SPcb_t'):]) for x in arms if x.startswith('SPcb_t'))
    conds = conditions(rows)
    ll = collections.defaultdict(list)
    fe = collections.defaultdict(list)
    frames = sorted({r['frame'] for r in rows})
    for r in rows:
        ll[(r['arm'], r['config'], r['snr_centi_db'], r['rho_permille'])].append(r['logloss_bits'])
        fe[(r['arm'], r['config'], r['snr_centi_db'], r['rho_permille'])].append(r['info_errors'] > 0)
    tab_rows, summary = [], {}
    for arm in [f'SPcb_t{t:g}' for t in thetas] + (['SPg_flat'] if 'SPg_flat' in arms else []):
        per = [float(np.mean(ll[(arm,) + c])) for c in conds]
        pf = [float(np.mean(fe[(arm,) + c])) for c in conds]
        summary[arm] = dict(mean_logloss=float(np.mean(per)), mean_fer=float(np.mean(pf)), per_condition_logloss=per, per_condition_fer=pf)
    best = min((summary[f'SPcb_t{t:g}']['mean_logloss'], t) for t in thetas)[1]
    md = ['# Dev tuning of the SPcb acquisition threshold theta (dev frames %d..%d, %d frames, %d conditions)\n' % (frames[0], frames[-1], len(frames), len(conds)),
          'criterion: mean over the 24 conditions of the per-condition mean logloss_bits of the SPcb arm (lower is better).  SPg_flat (genie delays) shown for reference only.\n',
          tab(['arm', 'mean logloss', 'mean FER'], [[k, f'{v["mean_logloss"]:.4f}', f'{v["mean_fer"]:.3f}'] for k, v in summary.items()]) + '\n',
          f'**selected theta = {best:g}**\n',
          '## per-condition logloss\n',
          tab(['config', 'snr', 'rho'] + list(summary), [[c[0], c[1] / 100, c[2] / 1000] + [f'{summary[k]["per_condition_logloss"][i]:.3f}' for k in summary] for i, c in enumerate(conds)]) + '\n']
    a.out_dir.mkdir(parents=True, exist_ok=True)
    (a.out_dir / 'DEV_THETA.md').write_text('\n'.join(md) + '\n')
    spec = dict(theta=best, criterion='min mean over conditions of per-condition mean logloss_bits (SPcb), dev frames %d..%d' % (frames[0], frames[-1]),
                grid=thetas, summary={k: dict(mean_logloss=v['mean_logloss'], mean_fer=v['mean_fer']) for k, v in summary.items()},
                dev_rows_md5={str(f): md5(f) for f in files}, n_rows=len(rows), n_error_rows=n_err)
    if a.write_theta:
        Path(a.write_theta).write_text(json.dumps(clean(spec), indent=1) + '\n')
    print('\n'.join(md))


# ---------------------------------------------------------------------------------------------- report
def report(a):
    files, rows, n_err, dup = load(a.test)
    boot = json.loads(a.boot_analysis.read_text())
    g = float(boot['fitq']['SPg_flat|0.5']['gamma_shr'])
    arms = [x for x in ('A3', 'SPg_flat', 'SPcb', 'B') if any(r['arm'] == x for r in rows)]
    conds = conditions(rows)
    frames = None
    by = collections.defaultdict(dict)
    for r in rows:
        by[(r['config'], r['snr_centi_db'], r['rho_permille'], r['arm'])][r['frame']] = r
    for c in conds:
        for ar in arms:
            fs = set(by[c + (ar,)])
            frames = fs if frames is None else frames & fs
    frames = sorted(frames)
    nF = len(frames)
    R = dict(_argv=sys.argv, inputs={str(f): md5(f) for f in files}, n_rows=len(rows), n_error_rows=n_err, duplicates=dup, frames=nF, g_used=g,
             g_source=f'{a.boot_analysis} fitq[SPg_flat|0.5].gamma_shr', arms=arms, cells={})
    theta = None
    if a.dev:
        pass
    md = ['# C1-TDL report (Part B)\n', f'rows {len(rows)} (error rows {n_err}, duplicates {dup}); frames per cell {nF}; arms {arms}; g for K*(g) = {g:.2f} '
          f'(c1_boot SPg_flat level-0.5 shrinkage fit).\n']
    # --------------------------------------------------------------- main table
    out_rows = []
    for c in conds:
        cfg, snr, rho_pm = c
        rho, s2 = rho_pm / 1000, ca.sig2(snr)
        F = {ar: np.array([by[c + (ar,)][f]['info_errors'] > 0 for f in frames]) for ar in arms}
        r0 = by[c + ('A3',)][frames[0]]
        T, K = r0['n_taps'], r0['K']
        ks = kstar_g(g, rho, s2)
        cell = dict(config=cfg, snr=snr / 100, rho=rho, n_tdl_taps=r0['n_tdl_taps'], T=T, K=K, kstar=ks, k_over_kstar=K / ks if ks > 0 else math.inf,
                    fer={}, ci={}, ll={})
        for ar in arms:
            k = int(F[ar].sum())
            lo, hi = analyze.wilson(k, nF)
            cell['fer'][ar] = k / nF
            cell['ci'][ar] = (lo, hi)
            cell['ll'][ar] = float(np.mean([by[c + (ar,)][f]['logloss_bits'] for f in frames]))
        # paired tests
        def mc(x, y):  # x fails only / y fails only, two-sided exact
            b = int(np.sum(F[x] & ~F[y]))
            cc = int(np.sum(~F[x] & F[y]))
            return b, cc, analyze.mcnemar(b, cc)
        cell['sp_vs_a3'] = {ar: mc(ar, 'A3') for ar in ('SPg_flat', 'SPcb') if ar in arms}
        if 'SPcb' in arms and 'SPg_flat' in arms:
            cell['cb_vs_genie'] = mc('SPcb', 'SPg_flat')
        if 'SPcb' in arms and 'B' in arms:
            cell['cb_vs_b'] = mc('SPcb', 'B')
        # SPcb diagnostics + SINR
        for ar in ('SPg_flat', 'SPcb'):
            if ar not in arms:
                continue
            e1 = np.array([by[c + (ar,)][f]['eps_ce1'] for f in frames])
            sinr = (1 - rho) / (s2 + e1)
            cell.setdefault('sinr_lt_g', {})[ar] = float(np.mean(sinr < g))
            cell.setdefault('eps1', {})[ar] = float(np.mean(e1))
            cell.setdefault('sinr_mean', {})[ar] = float(np.mean(sinr))
        if 'SPcb' in arms:
            d = {k: float(np.mean([by[c + ('SPcb',)][f][k] for f in frames])) for k in ('cb_n_cand', 'cb_n_kept', 'cb_hit', 'cb_false', 'cb_missed_energy', 'n_cols')}
            cell['cb'] = d
            cell['K_cb'] = d['n_cols']
            cell['k_cb_over_kstar'] = d['n_cols'] / ks if ks > 0 else math.inf
        if 'B' in arms:
            cell['b_missed_energy'] = float(np.mean([by[c + ('B',)][f]['b_missed_energy'] for f in frames]))
            cell['b_triggered'] = float(np.mean([bool(by[c + ('B',)][f].get('triggered')) for f in frames]))
        for ar in ('SPg_flat', 'SPcb'):
            if ar not in arms:
                continue
            b_, c_, p_ = cell['sp_vs_a3'][ar]
            cell.setdefault('flags', {})[ar] = dict(
                predicted_past=bool((K if ar == 'SPg_flat' else cell['K_cb']) >= ks), cliff=bool(cell['fer'][ar] >= .5),
                degraded=bool(cell['fer'][ar] - cell['fer']['A3'] >= .05 and p_ < .01 and b_ > c_))
        R['cells'][f'{cfg}|{snr / 100:g}|{rho:g}'] = cell
        out_rows.append(cell)
    # main FER table
    def f3(cell, ar):
        lo, hi = cell['ci'][ar]
        return f'{cell["fer"][ar]:.3f} [{lo:.3f},{hi:.3f}]'
    md.append('## 1. FER per condition (Wilson 95% CI); K = 8 x merged taps; K* = K*(g)\n')
    md.append(tab(['config', 'SNR', 'rho', 'TDL taps', 'T', 'K', 'K*(g)', 'K/K*'] + arms,
                  [[x['config'], f'{x["snr"]:g}', f'{x["rho"]:g}', x['n_tdl_taps'], x['T'], x['K'], f'{x["kstar"]:.0f}', f'{x["k_over_kstar"]:.2f}'] + [f3(x, ar) for ar in arms]
                   for x in out_rows]) + '\n')
    if 'SPcb' in arms:
        md.append('## 2. SPcb acquisition (means over frames)\n')
        md.append(tab(['config', 'SNR', 'rho', 'T true', 'cand delays', 'kept', 'kept true', 'kept false', 'missed energy', 'K_cb', 'K_cb/K*'],
                      [[x['config'], f'{x["snr"]:g}', f'{x["rho"]:g}', x['T'], f'{x["cb"]["cb_n_cand"]:.1f}', f'{x["cb"]["cb_n_kept"]:.1f}', f'{x["cb"]["cb_hit"]:.1f}',
                        f'{x["cb"]["cb_false"]:.1f}', f'{x["cb"]["cb_missed_energy"]:.3f}', f'{x["K_cb"]:.0f}', f'{x["k_cb_over_kstar"]:.2f}'] for x in out_rows]) + '\n')
    md.append('## 3. Past the cliff?  (pred = K_arm >= K*(g); cliff = FER >= .5; degr = FER_SP - FER_A3 >= .05 with paired McNemar p<.01; P(SINR<g) = first-pass SINR_spec below g)\n')
    rows3 = []
    for x in out_rows:
        row = [x['config'], f'{x["snr"]:g}', f'{x["rho"]:g}', f'{x["K"]}/{x["kstar"]:.0f}']
        for ar in ('SPg_flat', 'SPcb'):
            if ar in arms:
                fl = x['flags'][ar]
                b_, c_, p_ = x['sp_vs_a3'][ar]
                row += [f'{"Y" if fl["predicted_past"] else "n"}/{"Y" if fl["cliff"] else "n"}/{"Y" if fl["degraded"] else "n"}', f'{x["sinr_lt_g"][ar]:.2f}', f'{b_}/{c_} p={p_:.1e}']
        rows3.append(row)
    heads = ['config', 'SNR', 'rho', 'K/K*']
    for ar in ('SPg_flat', 'SPcb'):
        if ar in arms:
            heads += [f'{ar} pred/cliff/degr', f'{ar} P(SINR<g)', f'{ar} vs A3 b/c']
    md.append(tab(heads, rows3) + '\n')
    if 'SPcb' in arms and 'SPg_flat' in arms:
        md.append('## 4. Paired: SPcb vs SPg_flat, SPcb vs B  (b = first fails only, c = second fails only; exact two-sided p)\n')
        rows4 = []
        for x in out_rows:
            r_ = [x['config'], f'{x["snr"]:g}', f'{x["rho"]:g}', '%d/%d p=%.1e' % x['cb_vs_genie']]
            if 'cb_vs_b' in x:
                r_.append('%d/%d p=%.1e' % x['cb_vs_b'])
            rows4.append(r_)
        md.append(tab(['config', 'SNR', 'rho', 'SPcb vs SPg_flat'] + (['SPcb vs B'] if 'B' in arms else []), rows4) + '\n')
    (a.out_dir / 'TDL_REPORT.md').write_text('\n'.join(md) + '\n')
    (a.out_dir / 'tdl_report.json').write_text(json.dumps(clean(R), indent=1) + '\n')
    print('\n'.join(md))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument('--mode', choices=('pick', 'report'), required=True)
    ap.add_argument('--dev', type=Path)
    ap.add_argument('--test', type=Path)
    ap.add_argument('--out-dir', type=Path, required=True)
    ap.add_argument('--write-theta', type=Path)
    ap.add_argument('--boot-analysis', type=Path, default=Path(__file__).resolve().parent / 'out' / 'c1_boot' / 'analysis' / 'analysis.json')
    a = ap.parse_args(argv)
    a.out_dir.mkdir(parents=True, exist_ok=True)
    (pick if a.mode == 'pick' else report)(a)


if __name__ == '__main__':
    main()
