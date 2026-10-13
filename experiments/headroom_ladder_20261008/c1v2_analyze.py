#!/usr/bin/env python
"""Analysis of the C1 V2 mechanism probe (driver_c1v2.py).  Reads rows only.
    python -B c1v2_analyze.py [<c1v2_dir>] [--out <dir>] [--frame-table] [--t1 <t1_transfer.json>] [--preds <c1_t2 predictions.json>]
Default <c1v2_dir> = out/c1v2; outputs <out> = <c1v2_dir>/analysis/{v2.json, v2.md}.

Aggregation (research/c1-round1-loop-theory.md, V2 amendment): every P2 quantity is a per-frame value reduced to a per-cell median; P2a, P2b, P2d pass
if they hold in >= 5 of 6 cells (generic: ceil(5/6 * n_cells)); P2c must hold in every cell; "rises as rho falls" = monotone in rho at each L.
Per-frame quantities (physical units, N = 1024, a = 1 - rho, n = 10^(-SNR/10), s(v) = (n + a v)/((rho + a (1 - v)) N), e_ind(v) = K s/(1 + K s)):
  P2a  ln(e_indep / e_ind(vmeas_indep))                          pass: |cell median| <= .20
  P2b  e_soft / e_indep   vs  (1 - c_hat)^-2                     pass: |median(ratio) / median((1 - c_hat)^-2) - 1| <= .25
  P2c  kappa_hat = c_hat / (beta_hat d_hat)                      pass: cell median in [0, 1]
  P2d  median kappa_hat vs median w_hat                          pass: |median kappa_hat / median w_hat - 1| <= .25 in >= 5/6 cells AND
                                                                        median kappa_hat non-increasing in rho at each L (both sub-tests reported)
Report-only: amendment 2 (e_indep_mse; e_soft/e_indep_mse, e*/e_indep_mse and kappa_eff = (1 - ratio^-1/2)/(beta_hat d_hat) next to w_hat),
R1 (alpha-calibration loss), R2 (pilot-Gram absorption / retention vs equal-Gram), R3 (link geometry at h* and I_1 under the LMMSE,
T2 and geometric links with the cell's eta and J_unc of the T1 curves).  No verdict is attached to R1-R3.
"""
import argparse
import glob
import json
import math
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
N = 1024
A_TOL, B_TOL, D_TOL = .20, .25, .25


def e_ind(v, rho, snr_db, K):
    a, n = 1. - rho, 10 ** (-snr_db / 10)
    s = (n + a * v) / ((rho + a * (1. - v)) * N)
    return K * s / (1. + K * s)


def e_ind_adj(v, rho, snr_db, K, E):
    """Report-only: flat-prior linear estimator error for realised channel energy E (E = 1 gives e_ind)."""
    a, n = 1. - rho, 10 ** (-snr_db / 10)
    s = (n + a * v) / ((rho + a * (1. - v)) * N)
    beta = 1. / (1. + K * s)
    return (1. - beta) ** 2 * E + K * beta ** 2 * s


def clean(x):
    if isinstance(x, dict):
        return {str(k): clean(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [clean(v) for v in x]
    if isinstance(x, (np.floating, float)):
        return float(x) if math.isfinite(x) else None
    if isinstance(x, (np.integer,)):
        return int(x)
    if isinstance(x, (np.bool_,)):
        return bool(x)
    return x


def med(x):
    return float(np.median(np.asarray(x, float)))


def load(dirp):
    return [json.loads(x) for f in sorted(glob.glob(str(dirp / 'rows_shard*.jsonl'))) for x in open(f) if x.strip()]


def load_links(t1, preds):
    """(J_unc curve, eta table) or (None, None) when the T1 / T2 calibration files are not available."""
    try:
        import c1_t2_predict as P
        cu, _ = P.load_curves(t1)
        eta = {(c['dataset'], c['snr_db'], c['rho'], c['L']): c['eta'] for c in json.loads(Path(preds).read_text())['cells']}
        return cu, eta
    except (FileNotFoundError, ImportError, KeyError):
        return None, None


def cell_stats(rs, cu, eta_tab):
    f = lambda k: np.array([r[k] for r in rs], float)  # noqa: E731
    rho, snr, L = rs[0]['rho'], rs[0]['snr_db'], rs[0]['L']
    K = rs[0]['n_cols']
    E, estar = f('e_real'), f('e_star')
    d, w, beta, c = f('d_hat'), f('w_hat'), f('beta_hat'), f('c_hat')
    vmi = f('vmeas_indep')
    ind = np.array([e_ind(v, rho, snr, K) for v in vmi])
    ind_adj = np.array([e_ind_adj(v, rho, snr, K, e) for v, e in zip(vmi, E)])
    ln_a = np.log(f('e_indep') / ind)
    ratio_b = f('e_soft') / f('e_indep')
    with np.errstate(divide='ignore', invalid='ignore'):
        pred_b = np.where(c < 1., (1. - c) ** -2, np.inf)
    kappa = c / (beta * d)
    out = dict(rho=rho, snr_db=snr, L=L, K=K, n=len(rs),
               med=dict(e_star=med(estar), e_ce1=med(f('e_ce1')), e_soft=med(f('e_soft')), e_true=med(f('e_true')), e_indep=med(f('e_indep')),
                        e_0=med(f('e_0')), e_ind_pred=med(ind), e_ind_adj_pred=med(ind_adj), e_real=med(E),
                        vmeas_star=med(f('vmeas_star')), vrep_star=med(f('vrep_star')), vmeas_indep=med(vmi), vrep_indep=med(f('vrep_indep')),
                        indep_snr_db=med(f('indep_snr_db')), d_hat=med(d), d_fixed0=med(f('d_fixed0')), w_hat=med(w), beta_hat=med(beta),
                        c_hat=med(c), c_plus=med(f('c_plus')), c_minus=med(f('c_minus')), c_sd=med(f('c_sd')), beta_d=med(beta * d),
                        kappa_hat=med(kappa), mu0_nmse=med(f('mu0_nmse')), h0_vs_soft=med(f('h0_vs_soft'))),
               P2a=dict(ln_med=med(ln_a), ln_med_adj=med(np.log(f('e_indep') / ind_adj)), ln_of_medians=float(np.log(med(f('e_indep')) / med(ind))),
                        ok=bool(abs(med(ln_a)) <= A_TOL)),
               P2b=dict(ratio_obs_med=med(ratio_b), ratio_pred_med=med(pred_b), ratio_pred_at_med_c=(float((1. - med(c)) ** -2) if med(c) < 1. else None),
                        rel_dev=float(med(ratio_b) / med(pred_b) - 1.) if math.isfinite(med(pred_b)) else None,
                        ok=bool(math.isfinite(med(pred_b)) and abs(med(ratio_b) / med(pred_b) - 1.) <= B_TOL)),
               P2c=dict(kappa_med=med(kappa), c_med=med(c), beta_d_med=med(beta * d), frac_frames_in_bracket=float(np.mean((c >= 0.) & (c <= beta * d))),
                        ok=bool(0. <= med(kappa) <= 1.)),
               P2d=dict(kappa_med=med(kappa), w_med=med(w), rel_dev=float(med(kappa) / med(w) - 1.), ok_level=bool(abs(med(kappa) / med(w) - 1.) <= D_TOL)),
               R1=dict(calib_loss=med(f('r1_calib_loss')), alpha_best=med(f('r1_alpha_best')), mi=med(f('r1_mi')), mi_best=med(f('r1_mi_best'))),
               R2=dict(dp_over_n=med(f('r2_dp_over_n')), dp_eq=med(f('r2_dp_eq')), trq2_over_n=med(f('r2_trq2_over_n')),
                       retention=med(f('r2_retention')), retention_eq=med(f('r2_retention_eq')), beta_hat_pilot=med(f('beta_hat_pilot')),
                       beta_eq=med(f('r2_beta_eq'))))
    # amendment 2 (report-only): e_indep_mse (independent soft symbols with the true MSE of mu*, refit weights of mu*) and effective kappa
    if 'e_indep_mse' in rs[0]:
        eim = f('e_indep_mse')
        r_soft, r_star = f('e_soft') / eim, estar / eim
        with np.errstate(invalid='ignore', divide='ignore'):
            k_soft, k_star = (1. - r_soft ** -.5) / (beta * d), (1. - r_star ** -.5) / (beta * d)
        out['A2'] = dict(e_indep_mse=med(eim), ratio_soft=med(r_soft), ratio_star=med(r_star), kappa_eff_soft=med(k_soft), kappa_eff_star=med(k_star),
                         w_hat=med(w), kappa_hat=med(kappa), vmeas_indep_mse=med(f('vmeas_indep_mse')), vmeas_star=med(f('vmeas_star')),
                         indep_mse_snr_db=med(f('indep_mse_snr_db')), n_status_not_ok=int(sum(r['indep_mse_status'] != 'ok' for r in rs)))
    # R3: link geometry at h* and I_1 under three links
    alpha, U, hn = f('r3_alpha'), f('r3_U'), f('r3_hnorm2')
    out['R3'] = dict(alpha=med(alpha), U_over_E=med(U / E), lmmse_over_E=med((E - estar) / E), hnorm2_over_E=med(hn / E), I_obs_med=med(1. - f('r1_ll_in')))
    eta = None if eta_tab is None else eta_tab.get(('c1_boot', snr, rho, L))
    if cu is not None and eta is not None:
        a, n = 1. - rho, 10 ** (-snr / 10)
        q = {'lmmse': eta * a * (E - estar) / (n + estar), 't2': eta * a * E / (n + estar), 'geom': eta * a * U / (n + E - U)}
        iobs = 1. - f('r1_ll_in')
        out['R3'].update(eta=eta)
        for k, qq in q.items():
            ip = cu('J_unc', np.maximum(qq, 1e-300))
            out['R3'][f'I_pred_{k}'] = med(ip)
            out['R3'][f'abs_err_{k}'] = med(np.abs(ip - iobs))
            out['R3'][f'bias_{k}'] = med(ip - iobs)
    return out


def verdicts(cells):
    n = len(cells)
    need = int(np.ceil(5. / 6. * n - 1e-9))
    key = lambda c: (c['snr_db'], c['L'], c['rho'])  # noqa: E731
    cs = sorted(cells, key=key)
    v = {'n_cells': n, 'need': need}
    for k in ('P2a', 'P2b'):
        v[k] = dict(n_pass=int(sum(c[k]['ok'] for c in cs)), ok=bool(sum(c[k]['ok'] for c in cs) >= need))
    v['P2c'] = dict(n_pass=int(sum(c['P2c']['ok'] for c in cs)), ok=bool(all(c['P2c']['ok'] for c in cs)))
    mono = {}
    for (snr, L) in sorted({(c['snr_db'], c['L']) for c in cs}):
        ks = [c['P2d']['kappa_med'] for c in cs if c['snr_db'] == snr and c['L'] == L]  # ascending rho
        mono[f'{snr:g}|L{L}'] = bool(all(a >= b for a, b in zip(ks, ks[1:])))
    v['P2d'] = dict(n_level_pass=int(sum(c['P2d']['ok_level'] for c in cs)), level_ok=bool(sum(c['P2d']['ok_level'] for c in cs) >= need),
                    monotone_in_rho=mono, monotone_ok=bool(all(mono.values())))
    v['P2d']['ok'] = bool(v['P2d']['level_ok'] and v['P2d']['monotone_ok'])
    a, b, c_, d = v['P2a']['ok'], v['P2b']['ok'], v['P2c']['ok'], v['P2d']['ok']
    if not a:
        branch = 'P2a fails: the independent-error refit law is wrong (spec branch).'
    elif not b:
        branch = 'P2b fails: the deficit is not linear self-absorption; look at soft-symbol quality; framework rejected (spec branch).'
    elif a and b and c_ and not d:
        branch = 'P2a-c pass, P2d fails: keep the law with kappa measured as one operator constant, drop H_w (spec branch).'
    elif a and b and c_ and d:
        branch = 'P2a-d pass: H_w retained for V3.'
    else:
        branch = 'P2a, P2b pass, P2c fails: not covered by the spec branches (bracket 0 <= c <= beta d violated).'
    v['branch'] = branch
    return v


def fm(x, nd=3):
    return '-' if x is None else (f'{x:.{nd}f}')


def write_md(res, frame_rows):
    cs, v = res['cells'], res['verdicts']
    L = [f"# C1 V2 mechanism probe (8 dB; per-cell medians over frames)", '',
         f"rows {res['n_rows']} (error rows {res['n_error_rows']}); cells {v['n_cells']}; frames per cell: "
         + ', '.join(sorted({str(c['n']) for c in cs})) + (' (indicative only: fewer than 40 frames)' if any(c['n'] < 40 for c in cs) else ''), '',
         '## Verdicts', '', '| test | cells passing | need | verdict |', '|---|---|---|---|']
    L.append(f"| P2a e_indep vs e_ind(vmeas_indep), abs ln <= {A_TOL} | {v['P2a']['n_pass']} | {v['need']} | {'PASS' if v['P2a']['ok'] else 'FAIL'} |")
    L.append(f"| P2b e_soft/e_indep vs (1-c_hat)^-2, within {int(B_TOL * 100)}% | {v['P2b']['n_pass']} | {v['need']} | {'PASS' if v['P2b']['ok'] else 'FAIL'} |")
    L.append(f"| P2c 0 <= c_hat <= beta_hat d_hat (median kappa_hat in [0,1]) | {v['P2c']['n_pass']} | {v['n_cells']} | {'PASS' if v['P2c']['ok'] else 'FAIL'} |")
    L.append(f"| P2d kappa_hat within {int(D_TOL * 100)}% of w_hat | {v['P2d']['n_level_pass']} | {v['need']} | {'PASS' if v['P2d']['level_ok'] else 'FAIL'} |")
    L.append(f"| P2d kappa_hat monotone in rho at each L ({', '.join(f'{k}: {m}' for k, m in v['P2d']['monotone_in_rho'].items())}) | - | - | "
             f"{'PASS' if v['P2d']['monotone_ok'] else 'FAIL'} |")
    L += ['', f"Branch: {v['branch']}", '', '## Per cell (medians)', '',
          '| SNR | rho | L | n | e* | e_soft | e_indep | e_true | e_ind(vmeas) | lnA | e_soft/e_indep | (1-c)^-2 | c_hat | beta d | kappa | w_hat | d_hat | d_fixed0 | beta_hat |',
          '|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|']
    for c in cs:
        m = c['med']
        L.append(f"| {c['snr_db']:g} | {c['rho']:g} | {c['L']} | {c['n']} | {fm(m['e_star'], 4)} | {fm(m['e_soft'], 4)} | {fm(m['e_indep'], 4)} | {fm(m['e_true'], 4)} | "
                 f"{fm(m['e_ind_pred'], 4)} | {fm(c['P2a']['ln_med'], 3)} | {fm(c['P2b']['ratio_obs_med'], 3)} | {fm(c['P2b']['ratio_pred_med'], 3)} | "
                 f"{fm(m['c_hat'])} | {fm(m['beta_d'])} | {fm(m['kappa_hat'])} | {fm(m['w_hat'])} | {fm(m['d_hat'])} | {fm(m['d_fixed0'])} | {fm(m['beta_hat'])} |")
    L += ['', 'Soft-symbol quality and probe controls (medians): reported vs true normalised MSE of mu*, matched independent symbols, delta = 0 control.', '',
          '| rho | L | vrep(v*) | vmeas(mu*) | vmeas_indep | indep SINR dB | e_0 | h0_vs_soft | mu0_nmse | c_plus | c_minus | c_sd (4 dirs) |', '|---|---|---|---|---|---|---|---|---|---|---|---|']
    for c in cs:
        m = c['med']
        L.append(f"| {c['rho']:g} | {c['L']} | {fm(m['vrep_star'])} | {fm(m['vmeas_star'])} | {fm(m['vmeas_indep'])} | {fm(m['indep_snr_db'], 2)} | {fm(m['e_0'], 4)} | "
                 f"{fm(m['h0_vs_soft'])} | {fm(m['mu0_nmse'])} | {fm(m['c_plus'])} | {fm(m['c_minus'])} | {fm(m['c_sd'])} |")
    if all('A2' in c for c in cs):
        L += ['', '## Amendment 2 (report-only): e_indep_mse and effective kappa  (kappa_eff = (1 - ratio^-1/2)/(beta_hat d_hat), per frame then median)', '',
              '| rho | L | e_indep_mse | e_soft/e_indep_mse | e*/e_indep_mse | kappa_eff (e_soft) | kappa_eff (e*) | w_hat | kappa_hat (probe) | vmeas_indep_mse (target vmeas*) | SINR dB | not ok |',
              '|---|---|---|---|---|---|---|---|---|---|---|---|']
        for c in cs:
            a2 = c['A2']
            L.append(f"| {c['rho']:g} | {c['L']} | {fm(a2['e_indep_mse'], 4)} | {fm(a2['ratio_soft'])} | {fm(a2['ratio_star'])} | {fm(a2['kappa_eff_soft'])} | "
                     f"{fm(a2['kappa_eff_star'])} | {fm(a2['w_hat'])} | {fm(a2['kappa_hat'])} | {fm(a2['vmeas_indep_mse'])} ({fm(a2['vmeas_star'])}) | "
                     f"{fm(a2['indep_mse_snr_db'], 2)} | {a2['n_status_not_ok']} |")
    L += ['', '## R1 (report-only): calibration loss of the round-1 decoder-input LLR', '',
          '| rho | L | MI(L) | best-alpha MI | loss | alpha* |', '|---|---|---|---|---|---|']
    for c in cs:
        r = c['R1']
        L.append(f"| {c['rho']:g} | {c['L']} | {fm(r['mi'])} | {fm(r['mi_best'])} | {fm(r['calib_loss'], 4)} | {fm(r['alpha_best'], 2)} |")
    L += ['', '## R2 (report-only): pilot-regression absorption and data-signal retention (exact pilot Gram vs equal-Gram)', '',
          '| rho | L | d_p/N | k beta (eq) | tr Q_p^2/N | retention | 1-k beta(2-beta) (eq) | beta_pilot (exact) | beta (eq) |', '|---|---|---|---|---|---|---|---|---|']
    for c in cs:
        r = c['R2']
        L.append(f"| {c['rho']:g} | {c['L']} | {fm(r['dp_over_n'], 4)} | {fm(r['dp_eq'], 4)} | {fm(r['trq2_over_n'], 4)} | {fm(r['retention'], 4)} | {fm(r['retention_eq'], 4)} | "
                 f"{fm(r['beta_hat_pilot'])} | {fm(r['beta_eq'])} |")
    L += ['', '## R3 (report-only): link geometry at h* and I_1 under three links (eta from out/c1_t2/predictions.json, c1_boot dataset; J_unc from T1)', '',
          'I_pred: LMMSE q = eta a (E_real - e*)/(n + e*); T2 q = eta a E_real/(n + e*); geometric q = eta a U/(n + E_real - U).  abs err = per-frame median |I_pred - I_obs|.', '',
          '| rho | L | eta | alpha | U/E_real | (E_real-e*)/E_real | \\|h*\\|^2/E_real | I_obs | I LMMSE | I T2 | I geom | abs err LMMSE | abs err T2 | abs err geom |',
          '|---|---|---|---|---|---|---|---|---|---|---|---|---|---|']
    for c in cs:
        r = c['R3']
        L.append(f"| {c['rho']:g} | {c['L']} | {fm(r.get('eta'))} | {fm(r['alpha'], 4)} | {fm(r['U_over_E'], 4)} | {fm(r['lmmse_over_E'], 4)} | {fm(r['hnorm2_over_E'], 4)} | "
                 f"{fm(r['I_obs_med'])} | {fm(r.get('I_pred_lmmse'))} | {fm(r.get('I_pred_t2'))} | {fm(r.get('I_pred_geom'))} | "
                 f"{fm(r.get('abs_err_lmmse'))} | {fm(r.get('abs_err_t2'))} | {fm(r.get('abs_err_geom'))} |")
    if frame_rows:
        L += ['', '## Per frame', '',
              '| cell | frame | e* | e_soft | e_true | e_indep | e_indep_mse | c_hat | d_hat | w_hat | beta_hat | R1 loss | R2 dp/N (eq) | R2 retention (eq) |', '|---|---|---|---|---|---|---|---|---|---|---|---|---|---|']
        for r in frame_rows:
            L.append(f"| {r['config']} rho {r['rho']:g} | {r['frame']} | {r['e_star']:.4f} | {r['e_soft']:.4f} | {r['e_true']:.4f} | {r['e_indep']:.4f} | {r.get('e_indep_mse', float('nan')):.4f} | {r['c_hat']:.3f} | "
                     f"{r['d_hat']:.3f} | {r['w_hat']:.3f} | {r['beta_hat']:.3f} | {r['r1_calib_loss']:.4f} | {r['r2_dp_over_n']:.4f} ({r['r2_dp_eq']:.4f}) | "
                     f"{r['r2_retention']:.4f} ({r['r2_retention_eq']:.4f}) |")
    return '\n'.join(L) + '\n'


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument('dir', nargs='?', type=Path, default=HERE / 'out' / 'c1v2')
    ap.add_argument('--out', type=Path, default=None)
    ap.add_argument('--frame-table', action='store_true')
    ap.add_argument('--t1', type=Path, default=HERE / 'out' / 'c1_t1' / 't1_transfer.json')
    ap.add_argument('--preds', type=Path, default=HERE / 'out' / 'c1_t2' / 'predictions.json')
    args = ap.parse_args()
    out = args.out or args.dir / 'analysis'
    out.mkdir(parents=True, exist_ok=True)
    rows = load(args.dir)
    ok = [r for r in rows if r['status'] == 'ok']
    cu, eta_tab = load_links(args.t1, args.preds)
    groups = {}
    for r in ok:
        groups.setdefault((r['snr_db'], r['rho'], r['L']), []).append(r)
    cells = [cell_stats(sorted(rs, key=lambda r: r['frame']), cu, eta_tab) for _, rs in sorted(groups.items())]
    res = dict(n_rows=len(rows), n_error_rows=len(rows) - len(ok), links_available=cu is not None and eta_tab is not None, cells=cells,
               verdicts=verdicts(cells))
    (out / 'v2.json').write_text(json.dumps(clean(res), indent=1, allow_nan=False) + '\n')
    frame_rows = sorted(ok, key=lambda r: (r['L'], r['rho'], r['frame'])) if args.frame_table else None
    md = write_md(res, frame_rows)
    (out / 'v2.md').write_text(md)
    print(md)


if __name__ == '__main__':
    main()
