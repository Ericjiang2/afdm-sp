#!/usr/bin/env python
"""Analysis of the C1 J12 run (driver_c1j12.py).  Reads rows only.
    python -B c1j12_analyze.py [<c1j12_dir>] [--out <dir>] [--boot <c1_boot>] [--map <c1_map>] [--jfp <c1jfp dir>] [--frame-table]
Default <c1j12_dir> = out/c1j12; outputs <out> = <c1j12_dir>/analysis/{j12.json, j12.md}.

Section 8 of research/c1-joint-fp-theory.md.  Per frame: z = P_perp(h_I - h_o), u = P_perp(h_S - h_I), w = P_perp(h_T - h_S) (P_perp = I - h_o h_o^H/|h_o|^2;
h_T kernel round-1 gains, h_S plain soft refit on (m_T, v_T), h_I matched-true-MSE independent refit, h_o truth on the DPSS basis).  Cell statistics are sums over frames:
  R_X   = sum |P_perp(h_X - h_o)|^2 / sum |z|^2,  X = S, T
  D_reg = R_S - 1 = [sum 2Re z^H u + sum |u|^2] / sum |z|^2                                  (own vs independent symbols, same plain refit)
  D_alg = R_T - R_S = [sum 2Re z^H w + sum |w|^2 + sum 2Re u^H w] / sum |z|^2                (joint algorithm vs plain refit)
Decision rule: |D_alg| > |D_reg| in >= 7/10 cells -> mainly algorithmic; |D_reg| > |D_alg| in >= 7/10 -> mainly the structure of the receiver's own symbol errors;
otherwise mixed (left to the user).  The J-run statistic (median |P_perp(h_T-h_o)|^2 / median |z|^2) is reported next to R_T for continuity.
Report-only: rho-trend signs of D_reg and D_alg (8 dB, L8 / L24), e_perp(T)/e_perp(20) for T = 10/40/80, share of |P_perp d_dyn| in |P_perp(h_T-h_o)| and the four
J7 terms, expectation check (e_soft/e_indep_mse > e*/e_indep_mse from medians of total errors).
Checks: S1 bit-exact vs stored rows (--boot / --map), recursion == kernel (max dLLR <= 1e-8, max dh <= 1e-10), J12 identity residual <= 1e-10 per frame, J8/J6/J3 residuals,
S2 e_soft / e_indep_mse / e_star equal the J-run rows of the same cell and frame (--jfp, when available).
"""
import argparse
import glob
import json
import math
from pathlib import Path

import numpy as np

import c1jfp_analyze as JA
import c1v2_analyze as A

HERE = Path(__file__).resolve().parent
fm = A.fm
med = A.med
TOL_ID = 1e-10


def cell_stats(rs):
    f = lambda k: np.array([r[k] for r in rs], float)  # noqa: E731
    rho, snr, L = rs[0]['rho'], rs[0]['snr_db'], rs[0]['L']
    S = lambda k: float(np.sum(f(k)))  # noqa: E731
    sz = S('z2')
    R_S, R_T = S('eperp_S') / sz, S('eperp_T') / sz
    terms = {k: S(k) / sz for k in ('zu2', 'u2', 'zw2', 'w2', 'uw2')}
    out = dict(rho=rho, snr_db=snr, L=L, n=len(rs), R_S=R_S, R_T=R_T, D_reg=R_S - 1., D_alg=R_T - R_S, terms=terms,
               D_reg_sum_check=terms['zu2'] + terms['u2'] - (R_S - 1.), D_alg_sum_check=terms['zw2'] + terms['w2'] + terms['uw2'] - (R_T - R_S),
               J_ratio=med(f('eperp_T')) / med(f('eperp_I')), J_ratio_S=med(f('eperp_S')) / med(f('eperp_I')),
               med_ratio_perframe_T=med(f('eperp_T') / f('z2')),
               tot=dict(e_star=med(f('e_star')), e_soft=med(f('e_soft')), e_indep_mse=med(f('e_indep_mse')),
                        soft_over_ind=med(f('e_soft')) / med(f('e_indep_mse')), star_over_ind=med(f('e_star')) / med(f('e_indep_mse'))))
    out['expectation_soft_gt_star'] = bool(out['tot']['soft_over_ind'] > out['tot']['star_over_ind'])
    # T dependence (sums over frames, relative to the T = 20 recursion output = kernel output)
    out['T_ratio'] = {str(T): S(f'eperp_T{T}') / S('eperp_T20') for T in (10, 40, 80)}
    out['T_ratio_median'] = {str(T): med(f(f'eperp_T{T}') / f('eperp_T20')) for T in (10, 40, 80)}
    out['T_total_ratio'] = {str(T): S(f'e_T{T}') / S('e_T20') for T in (10, 40, 80)}
    # dynamic term
    ep = S('eperp_T')
    j7 = np.array([r['j7_perp'] for r in rs], float)
    out['dyn'] = dict(share_ddyn=math.sqrt(float(np.sum(f('ddyn_perp') ** 2)) / ep), share_ddyn_median=med(f('ddyn_perp') / np.sqrt(f('eperp_T'))),
                      share_dh=math.sqrt(float(np.sum(f('dh_perp') ** 2)) / ep), share_qf=math.sqrt(float(np.sum(f('qf_perp') ** 2)) / ep),
                      share_j7=[math.sqrt(float(np.sum(j7[:, i] ** 2)) / ep) for i in range(4)],
                      med_ddyn_perp=med(f('ddyn_perp')), med_j7_perp=[med(j7[:, i]) for i in range(4)])
    out['checks'] = dict(max_j12_resid=float(np.max(f('j12_resid'))), max_j8_resid=float(np.max(f('j8_resid'))), max_j6_resid=float(np.max(f('j6_resid'))),
                         max_j3_resid=float(np.max(f('j3_resid'))), max_q0_dllr=float(np.max(f('q0_dllr'))), max_q0_dh=float(np.max(f('q0_dh'))),
                         max_q0_dm=float(np.max(f('q0_dm'))), max_q0_dh0=float(np.max(f('q0_dh0'))))
    return out


def decision(cells):
    n = len(cells)
    alg = int(sum(abs(c['D_alg']) > abs(c['D_reg']) for c in cells))
    reg = int(sum(abs(c['D_reg']) > abs(c['D_alg']) for c in cells))
    need = int(math.ceil(.7 * n - 1e-9))
    if alg >= need:
        verdict = 'ALGORITHMIC: |D_alg| > |D_reg| in >= 7/10 cells; stop the search for a scalar-kappa mechanism, keep the calibrated kappa = w law.'
    elif reg >= need:
        verdict = "STRUCTURE: |D_reg| > |D_alg| in >= 7/10 cells; the excess is mainly the structure of the receiver's own symbol errors; round 2 models D_reg (J24 / J14 path)."
    else:
        verdict = 'MIXED: neither term dominates in >= 7/10 cells; report and leave the call to the user.'
    return dict(n_cells=n, n_alg_dominates=alg, n_reg_dominates=reg, need=need, verdict=verdict)


def rho_trends(cells):
    out = {}
    for L in sorted({c['L'] for c in cells if c['snr_db'] == 8.}):
        by = {c['rho']: c for c in cells if c['snr_db'] == 8. and c['L'] == L}
        if .2 in by and .5 in by:
            d = lambda k: by[.5][k] - by[.2][k]  # noqa: E731
            dreg, dalg, dRT = d('D_reg'), d('D_alg'), d('R_T')
            out[f'L{L}'] = dict(dD_reg=dreg, dD_alg=dalg, dR_T=dRT, sign_D_reg=float(np.sign(dreg)), sign_D_alg=float(np.sign(dalg)), sign_R_T=float(np.sign(dRT)),
                                carrier='D_reg' if abs(dreg) > abs(dalg) else 'D_alg',
                                values={f'{r:g}': dict(R_T=by[r]['R_T'], D_reg=by[r]['D_reg'], D_alg=by[r]['D_alg']) for r in sorted(by)})
    return out


def check_s2(rows_ok, jfp_dir):
    if not jfp_dir or not Path(jfp_dir).is_dir():
        return dict(available=False)
    jrows = {}
    for fn in sorted(glob.glob(str(Path(jfp_dir) / 'rows_shard*.jsonl'))):
        for x in open(fn):
            if x.strip():
                r = json.loads(x)
                if r.get('status') == 'ok':
                    jrows[(r['config'], r['rho_permille'], r['snr_centi_db'], r['frame'])] = r
    worst = dict(e_soft=0., e_indep_mse=0., e_star=0., eperp_T_vs_e_perp=0., eperp_I_vs_e_ind_perp=0.)
    n_cmp, missing = 0, 0
    for r in rows_ok:
        j = jrows.get((r['config'], r['rho_permille'], r['snr_centi_db'], r['frame']))
        if j is None:
            missing += 1
            continue
        n_cmp += 1
        worst['e_soft'] = max(worst['e_soft'], abs(r['e_soft'] - j['e_soft']))
        worst['e_indep_mse'] = max(worst['e_indep_mse'], abs(r['e_indep_mse'] - j['e_indep_mse']))
        worst['e_star'] = max(worst['e_star'], abs(r['e_star'] - j['e_star']))
        worst['eperp_T_vs_e_perp'] = max(worst['eperp_T_vs_e_perp'], abs(r['eperp_T'] - j['e_perp']))
        worst['eperp_I_vs_e_ind_perp'] = max(worst['eperp_I_vs_e_ind_perp'], abs(r['eperp_I'] - j['e_ind_perp']))
    return dict(available=True, n_compared=n_cmp, n_missing=missing, max_abs_diff=worst, ok=bool(n_cmp > 0 and missing == 0 and max(worst.values()) < 1e-12))


def write_md(res, frame_rows):
    cs, dec, chk = res['cells'], res['decision'], res['checks']
    L = ['# C1 J12 run: finite-time decomposition of the round-1 error ratio (frames 640-679; sums over frames per cell)', '',
         f"rows {res['n_rows']} (error rows {res['n_error_rows']}); cells {dec['n_cells']}; frames per cell: " + ', '.join(sorted({str(c['n']) for c in cs})) +
         (' (indicative only: fewer than 40 frames)' if any(c['n'] < 40 for c in cs) else ''), '', '## Decision rule', '',
         f"|D_alg| > |D_reg| in {dec['n_alg_dominates']}/{dec['n_cells']} cells; |D_reg| > |D_alg| in {dec['n_reg_dominates']}/{dec['n_cells']} (need {dec['need']}).", '',
         f"**{dec['verdict']}**", '',
         f"Expectation stated before the run (medians of total errors: e_soft/e_indep_mse > e*/e_indep_mse in 9/10 cells): "
         f"{res['expectation']['n_true']}/{dec['n_cells']} cells.", '', '## Per cell', '',
         'R_S, R_T are sums over frames of |P_perp(h_X - h_o)|^2 over sum |z|^2; the six J12 terms are divided by sum |z|^2; J-run = median |P(h_T-h_o)|^2 / median |z|^2.', '',
         '| SNR | rho | L | n | R_S | R_T | J-run ratio | D_reg | D_alg | 2Re z^H u | \\|u\\|^2 | 2Re z^H w | \\|w\\|^2 | 2Re u^H w | dominant |',
         '|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|']
    for c in cs:
        t = c['terms']
        L.append(f"| {c['snr_db']:g} | {c['rho']:g} | {c['L']} | {c['n']} | {fm(c['R_S'])} | {fm(c['R_T'])} | {fm(c['J_ratio'])} | {fm(c['D_reg'])} | {fm(c['D_alg'])} | "
                 f"{fm(t['zu2'])} | {fm(t['u2'])} | {fm(t['zw2'])} | {fm(t['w2'])} | {fm(t['uw2'])} | {'alg' if abs(c['D_alg']) > abs(c['D_reg']) else 'reg'} |")
    L += ['', '## Report-only: rho trend at 8 dB', '']
    for k, v in res['rho_trends'].items():
        L.append(f"- {k}: R_T {v['sign_R_T']:+.0f} ({v['dR_T']:+.3f}), D_reg {v['sign_D_reg']:+.0f} ({v['dD_reg']:+.3f}), D_alg {v['sign_D_alg']:+.0f} ({v['dD_alg']:+.3f}); "
                 f"larger change in |.|: {v['carrier']}; values " + '; '.join(f"rho {r}: R_T {fm(x['R_T'])} D_reg {fm(x['D_reg'])} D_alg {fm(x['D_alg'])}" for r, x in v['values'].items()))
    L += ['', '## Report-only: total errors (medians) and the expectation check', '',
          '| SNR | rho | L | e* | e_soft | e_indep_mse | e_soft/e_indep_mse | e*/e_indep_mse | soft > star |', '|---|---|---|---|---|---|---|---|---|']
    for c in cs:
        t = c['tot']
        L.append(f"| {c['snr_db']:g} | {c['rho']:g} | {c['L']} | {fm(t['e_star'], 4)} | {fm(t['e_soft'], 4)} | {fm(t['e_indep_mse'], 4)} | {fm(t['soft_over_ind'])} | "
                 f"{fm(t['star_over_ind'])} | {c['expectation_soft_gt_star']} |")
    L += ['', '## Report-only: e_perp(T)/e_perp(20) from the verified recursion (sum over frames; median of per-frame ratios in brackets); total-error ratio e(T)/e(20)', '',
          '| SNR | rho | L | T=10 | T=40 | T=80 | total T=10 | T=40 | T=80 |', '|---|---|---|---|---|---|---|---|---|']
    for c in cs:
        r, m, tt = c['T_ratio'], c['T_ratio_median'], c['T_total_ratio']
        L.append(f"| {c['snr_db']:g} | {c['rho']:g} | {c['L']} | " + ' | '.join(f"{fm(r[T])} ({fm(m[T])})" for T in ('10', '40', '80')) + ' | ' +
                 ' | '.join(fm(tt[T]) for T in ('10', '40', '80')) + ' |')
    L += ['', '## Report-only: dynamic term at the 20th update (share = sqrt(sum |P_perp x|^2 / sum |P_perp(h_T-h_o)|^2))', '',
          'J7 terms in order: (1) symbol damping difference, (2) gain update, (3) gain damping difference, (4) residual update; each mapped through Q^-1.  d_dyn = dh - Q^-1 f.', '',
          '| SNR | rho | L | d_dyn share | median per frame | dh share | Q^-1 f share | J7(1) | J7(2) | J7(3) | J7(4) |', '|---|---|---|---|---|---|---|---|---|---|---|']
    for c in cs:
        d = c['dyn']
        L.append(f"| {c['snr_db']:g} | {c['rho']:g} | {c['L']} | {fm(d['share_ddyn'])} | {fm(d['share_ddyn_median'])} | {fm(d['share_dh'])} | {fm(d['share_qf'])} | " +
                 ' | '.join(fm(x) for x in d['share_j7']) + ' |')
    L += ['', '## Checks', '']
    s1 = res['S1']
    L.append('- S1 (stored c1_boot / c1_map rows): ' + (f"compared {s1['n_compared']}, missing {s1['n_missing']}, max abs diff {json.dumps(s1['max_abs_diff'])} -> {'PASS' if s1['ok'] else 'FAIL'}"
                                                     if s1.get('available') else 'stored directories not available here (not checked)'))
    L.append(f"- recursion (T = 20) == kernel: max dLLR {chk['max_q0_dllr']:.1e} (<= 1e-8), max dh {chk['max_q0_dh']:.1e} (<= 1e-10), max dm {chk['max_q0_dm']:.1e}, "
             f"max dh0 {chk['max_q0_dh0']:.1e} -> {'PASS' if chk['recursion_ok'] else 'FAIL'}")
    L.append(f"- J12 identity residual: max {chk['max_j12_resid']:.1e} (<= {TOL_ID:g}) -> {'PASS' if chk['j12_ok'] else 'FAIL'}")
    L.append(f"- J8 residual max {chk['max_j8_resid']:.1e}, J6 residual max {chk['max_j6_resid']:.1e}, J3 residual max {chk['max_j3_resid']:.1e} -> {'PASS' if chk['j8_ok'] else 'FAIL'} (<= {TOL_ID:g})")
    L.append(f"- decomposition sums: max |D_reg - (terms)| {chk['max_dreg_sum']:.1e}, max |D_alg - (terms)| {chk['max_dalg_sum']:.1e}")
    s2 = res['S2']
    L.append('- S2 (J12 e_soft / e_indep_mse / e_star equal the J-run rows): ' + (f"compared {s2['n_compared']}, missing {s2['n_missing']}, max abs diff {json.dumps(s2['max_abs_diff'])} -> "
                                                                          f"{'PASS' if s2['ok'] else 'FAIL'}" if s2.get('available') else 'J-run rows not available here (not checked)'))
    if frame_rows:
        L += ['', '## Per frame', '', '| cell | frame | e_perp I | S | T | R_S | R_T | 2Re z^H u | \\|u\\|^2 | 2Re z^H w | \\|w\\|^2 | 2Re u^H w | j12 resid | j8 resid |',
              '|---|---|---|---|---|---|---|---|---|---|---|---|---|---|']
        for r in frame_rows:
            L.append(f"| {r['snr_db']:g} rho {r['rho']:g} {r['config']} | {r['frame']} | {r['eperp_I']:.4f} | {r['eperp_S']:.4f} | {r['eperp_T']:.4f} | {r['eperp_S'] / r['z2']:.3f} | "
                     f"{r['eperp_T'] / r['z2']:.3f} | {r['zu2'] / r['z2']:.3f} | {r['u2'] / r['z2']:.3f} | {r['zw2'] / r['z2']:.3f} | {r['w2'] / r['z2']:.3f} | {r['uw2'] / r['z2']:.3f} | "
                     f"{r['j12_resid']:.1e} | {r['j8_resid']:.1e} |")
    return '\n'.join(L) + '\n'


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument('dir', nargs='?', type=Path, default=HERE / 'out' / 'c1j12')
    ap.add_argument('--out', type=Path, default=None)
    ap.add_argument('--boot', type=Path, default=HERE / 'out' / 'c1_boot')
    ap.add_argument('--map', type=Path, default=HERE / 'out' / 'c1_map')
    ap.add_argument('--jfp', type=Path, default=HERE / 'out' / 'c1jfp')
    ap.add_argument('--frame-table', action='store_true')
    args = ap.parse_args()
    out = args.out or args.dir / 'analysis'
    out.mkdir(parents=True, exist_ok=True)
    rows = A.load(args.dir)
    ok = [r for r in rows if r['status'] == 'ok']
    groups = {}
    for r in ok:
        groups.setdefault((r['snr_db'], r['rho'], r['L']), []).append(r)
    cells = [cell_stats(sorted(rs, key=lambda r: r['frame'])) for _, rs in sorted(groups.items())]
    allc = [c['checks'] for c in cells]
    mx = lambda k: max(c[k] for c in allc)  # noqa: E731
    chk = dict(max_j12_resid=mx('max_j12_resid'), max_j8_resid=mx('max_j8_resid'), max_j6_resid=mx('max_j6_resid'), max_j3_resid=mx('max_j3_resid'),
               max_q0_dllr=mx('max_q0_dllr'), max_q0_dh=mx('max_q0_dh'), max_q0_dm=mx('max_q0_dm'), max_q0_dh0=mx('max_q0_dh0'),
               max_dreg_sum=max(abs(c['D_reg_sum_check']) for c in cells), max_dalg_sum=max(abs(c['D_alg_sum_check']) for c in cells))
    chk['recursion_ok'] = bool(chk['max_q0_dllr'] <= 1e-8 and chk['max_q0_dh'] <= 1e-10)
    chk['j12_ok'] = bool(chk['max_j12_resid'] <= TOL_ID)
    chk['j8_ok'] = bool(max(chk['max_j8_resid'], chk['max_j6_resid'], chk['max_j3_resid']) <= TOL_ID)
    res = dict(n_rows=len(rows), n_error_rows=len(rows) - len(ok), cells=cells, decision=decision(cells), rho_trends=rho_trends(cells), checks=chk,
               expectation=dict(n_true=int(sum(c['expectation_soft_gt_star'] for c in cells))), S1=JA.check_s1(ok, args.boot, args.map), S2=check_s2(ok, args.jfp))
    (out / 'j12.json').write_text(json.dumps(A.clean(res), indent=1, allow_nan=False) + '\n')
    md = write_md(res, sorted(ok, key=lambda r: (r['snr_db'], r['rho'], r['L'], r['frame'])) if args.frame_table else None)
    (out / 'j12.md').write_text(md)
    print(md)


if __name__ == '__main__':
    main()
