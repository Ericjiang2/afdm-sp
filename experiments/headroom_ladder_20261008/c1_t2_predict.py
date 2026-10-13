#!/usr/bin/env python
"""Freeze C1 T2 predictions (research/c1-scalar-closure.md).  Reads ONLY non-SP calibration:
  out/c1_t1/t1_transfer.json            fixed-code AWGN curves
  out/c1_t0/t0_screen.json  a3.mean_r1_ll_in (true-H, eta rule); for variant B also SP eps_det1 median (pre-decoding state).
No SP outcome field (fer, outcomes, eps_ce2, eps_det2, strata) is read.  Writes out/c1_t2/predictions.json + PREDICTIONS.md.
Curve-domain rules (frozen here): below -1 dB FER = 1, M_app = v_app_wrong = M_unc(q), M_ext = v_ext_wrong linear in dB from
the -1 dB value to 1 at -10 dB; above 4 dB clamp; conditional columns missing where no frames fall in that class are filled
from the nearest measured point.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys

import numpy as np

import c1_t2_model as m

HERE = Path(__file__).resolve().parent
OUT = HERE / 'out' / 'c1_t2'
ROUNDS = (1, 2, 4)


def _fill(x):
    x = np.array([np.nan if v is None else v for v in x], float)
    idx = np.nonzero(~np.isnan(x))[0]
    return np.interp(np.arange(x.size), idx, x[idx])


def load_curves(path):
    cols = json.loads(Path(path).read_text())['columns']
    u, c = cols['uncoded'], cols['coded']
    cu = m.Curves(np.array(u['q_db']), M_unc=np.array(u['M_unc']), J_unc=np.array(u['J_unc']))
    q = np.array(c['q_db'])
    lo = np.arange(-10., q.min() - 1e-9, 0.2)
    m_unc_lo = cu('M_unc', 10 ** (lo / 10))
    chk_lo = np.interp(lo, [-10., q.min()], [1., c['M_chk'][int(np.argmin(q))]])
    chk_w = _fill(c['v_chk_wrong'])
    chk_lo_w = np.interp(lo, [-10., q.min()], [1., chk_w[int(np.argmin(q))]])
    cat = lambda a, b: np.concatenate([a, b])
    cc = m.Curves(cat(lo, q),
                  FER=cat(np.ones_like(lo), c['FER']),
                  M_app=cat(m_unc_lo, c['M_app']), M_ext=cat(chk_lo, c['M_chk']),
                  v_app_wrong=cat(m_unc_lo, _fill(c['v_wrong'])), v_ext_wrong=cat(chk_lo_w, chk_w),
                  v_app_correct=cat(np.full_like(lo, np.nan), _fill(c['v_correct'])))
    cc.cols['v_app_correct'] = _fill(list(cc.cols['v_app_correct']))
    return cu, cc


def median_of(qdict):
    for key in ('q50', 'p50', '50', 'median'):
        if key in qdict:
            return float(qdict[key])
    raise KeyError(f'no median key in {list(qdict)}')


def cell_inputs(t0):
    """Whitelisted per-cell inputs (SPg_flat cells)."""
    out = []
    for name, ds in t0['datasets'].items():
        for c in ds['cells']:
            if c['arm'] != 'SPg_flat':
                continue
            out.append(dict(dataset=name, snr_db=float(c['snr_db']), rho=float(c['rho']), L=int(c['L']), K=int(c['K']),
                            a3_r1_ll_in=float(c['a3']['mean_r1_ll_in']),
                            obs_eps_det1_median=median_of(c['quantiles']['eps_det1']['overall'])))
    return out


def predict_cell(cu, cc, ci, eta, e_det1_override=None):
    sm = m.ScalarMap(cu, cc, ci['rho'], ci['snr_db'], ci['K'], eta)
    e_ce1, e_det1 = sm.pilot_only()
    if e_det1_override is not None:
        e_det1 = float(e_det1_override)
    q1 = sm.q(e_det1)
    res = dict(e_ce1=e_ce1, e_det1=e_det1, q1_db=float(10 * np.log10(q1)), fer_r1=float(np.clip(cc('FER', q1), 0, 1)),
               eps_ce2_given_r1_fail=float(sm.refit(cc('v_app_wrong', q1))),
               eps_ce2_given_r1_correct=float(sm.refit(cc('v_app_correct', q1))))
    # two-branch failure path from the (possibly overridden) e_det1
    p_fail, e_det, path = 1., e_det1, []
    for r in range(1, max(ROUNDS) + 1):
        q = sm.q(e_det)
        fer = float(np.clip(cc('FER', q), 0., 1.))
        p_fail *= fer
        path.append(dict(r=r, e_det=e_det, q_db=float(10 * np.log10(q)), fer=fer))
        if r in ROUNDS:
            res[f'p_fail_R{r}'] = p_fail
        e_det = sm.inner(float(sm.refit(cc('v_app_wrong', q))), sm.q_prior(cc('v_ext_wrong', q)))
    res['fail_path'] = path
    return res


def structure(cu, cc, snr_db, rho, eta, K_grid):
    """Mean-field fixed points of G over K; K_flip(mean field) = first K with FER_T1(q(final e_det)) > .5 after 50 rounds."""
    rows, k_flip = [], None
    for K in K_grid:
        sm = m.ScalarMap(cu, cc, rho, snr_db, K, eta)
        fps = sm.fixed_points(300)
        fin = sm.mean_field_run(50)[-1]['e_det']
        bad = bool(cc('FER', sm.q(fin)) > .5)
        if bad and k_flip is None:
            k_flip = int(K)
        rows.append(dict(K=int(K), n_stable=sum(f['stable'] for f in fps), fps=fps, final_e_det=fin, bad=bad))
    windows = [r['K'] for r in rows if r['n_stable'] >= 2]
    return dict(K_flip_mean_field=k_flip, bistable_K=[min(windows), max(windows)] if windows else None, scan=rows)


def crossing(Ks, ys, level=.5):
    Ks, ys = np.asarray(Ks, float), np.asarray(ys, float)
    for i in range(len(Ks) - 1):
        if (ys[i] - level) * (ys[i + 1] - level) <= 0 and ys[i] != ys[i + 1]:
            return float(Ks[i] + (level - ys[i]) * (Ks[i + 1] - Ks[i]) / (ys[i + 1] - ys[i]))
    return None


def main():
    t1_path, t0_path = HERE / 'out/c1_t1/t1_transfer.json', HERE / 'out/c1_t0/t0_screen.json'
    cu, cc = load_curves(t1_path)
    cells = cell_inputs(json.loads(t0_path.read_text()))
    preds, groups = [], {}
    for ci in cells:
        eta = m.eta_rule(cu, ci['a3_r1_ll_in'], ci['rho'], ci['snr_db'])
        rec = dict(ci, eta=eta, A=predict_cell(cu, cc, ci, eta),
                   B=predict_cell(cu, cc, ci, eta, e_det1_override=ci['obs_eps_det1_median']))
        preds.append(rec)
        groups.setdefault((ci['dataset'], ci['snr_db'], ci['rho']), []).append(rec)
    summary = []
    for (ds, snr, rho), recs in sorted(groups.items()):
        recs.sort(key=lambda r: r['K'])
        Ks = [r['K'] for r in recs]
        eta_med = float(np.median([r['eta'] for r in recs]))
        st = structure(cu, cc, snr, rho, eta_med, np.arange(16, 513, 16))
        summary.append(dict(dataset=ds, snr_db=snr, rho=rho, eta_median=eta_med,
                            Kc_pred_A_R2=crossing(Ks, [r['A']['p_fail_R2'] for r in recs]),
                            Kc_pred_B_R2=crossing(Ks, [r['B']['p_fail_R2'] for r in recs]),
                            Kc_pred_A_R1=crossing(Ks, [r['A']['fer_r1'] for r in recs]),
                            K_flip_mean_field=st['K_flip_mean_field'], bistable_K_mean_field=st['bistable_K'],
                            structure_scan=st['scan']))
    OUT.mkdir(parents=True, exist_ok=True)
    blob = dict(_argv=sys.argv, _config=dict(t1=str(t1_path.relative_to(HERE)), t0=str(t0_path.relative_to(HERE)),
                rounds=ROUNDS, inputs_whitelist=['a3.mean_r1_ll_in', 'quantiles.eps_det1.overall median (variant B only)']),
                cells=preds, groups=summary)
    (OUT / 'predictions.json').write_text(json.dumps(blob, indent=1, default=float))
    lines = ['# C1 T2 frozen predictions (no SP outcome read)', '',
             '| dataset | SNR | rho | eta med | Kc A (R2) | Kc B (R2) | Kc A (R1) | K_flip MF | bistable K (MF) |', '|---|---|---|---|---|---|---|---|---|']
    fmt = lambda x: 'none' if x is None else (f'{x:.0f}' if not isinstance(x, list) else f'{x[0]}-{x[1]}')
    for g in summary:
        lines.append(f"| {g['dataset']} | {g['snr_db']:g} | {g['rho']:g} | {g['eta_median']:.3f} | {fmt(g['Kc_pred_A_R2'])} | "
                     f"{fmt(g['Kc_pred_B_R2'])} | {fmt(g['Kc_pred_A_R1'])} | {fmt(g['K_flip_mean_field'])} | {fmt(g['bistable_K_mean_field'])} |")
    lines += ['', '## Per cell (A = zero-SP, B = observed eps_det1 median)', '',
              '| dataset | SNR | rho | L | K | eta | e_det1 A | q1 A dB | FER_r1 A | Pfail R2 A | Pfail R2 B | e_ce2|fail A | e_ce2|fail B |', '|---|' * 13]
    for r in preds:
        a, b = r['A'], r['B']
        lines.append(f"| {r['dataset']} | {r['snr_db']:g} | {r['rho']:g} | {r['L']} | {r['K']} | {r['eta']:.3f} | {a['e_det1']:.4f} | "
                     f"{a['q1_db']:.2f} | {a['fer_r1']:.3f} | {a['p_fail_R2']:.3f} | {b['p_fail_R2']:.3f} | "
                     f"{a['eps_ce2_given_r1_fail']:.4f} | {b['eps_ce2_given_r1_fail']:.4f} |")
    (OUT / 'PREDICTIONS.md').write_text('\n'.join(lines) + '\n')
    print('\n'.join(lines[:4 + len(summary)]))


if __name__ == '__main__':
    main()
