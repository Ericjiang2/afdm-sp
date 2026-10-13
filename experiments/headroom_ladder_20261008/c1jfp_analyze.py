#!/usr/bin/env python
"""Analysis of the C1 J run (driver_c1jfp.py).  Reads rows only.
    python -B c1jfp_analyze.py [<c1jfp_dir>] [--out <dir>] [--boot <c1_boot dir>] [--map <c1_map dir>] [--frame-table]
Default <c1jfp_dir> = out/c1jfp; outputs <out> = <c1jfp_dir>/analysis/{jfp.json, jfp.md}.  --boot / --map (default out/c1_boot, out/c1_map when present)
give the stored SPg_flat rows for check S1 (eps_det1, r1_ll_in, r1_cerr, r1_syn must equal the stored row of the same L, rho, SNR, frame).

Q0-Q7 exactly as in research/c1-joint-fp-theory.md section 4 (cell statistics = medians over frames):
  obs        = median e_perp / median e_ind,perp                                  (e_ind,perp: matched-true-MSE independent refit with reported variance v*)
  inputs     = n0 physical = 10^(-SNR/10), v = median vmeas_star x (1 - rho), q = median E_real, beta = median beta_hat, c = median c_perp, d = c / beta
  A_B(d)     = [(1 - d)^2 n0 + (1 - d) q v]/(n0 + q v);   A_AMP(d) = (1 - d)^2
  Q0  max |dLLR| <= 1e-8 and max |dh| <= 1e-10 over all rows (Codex eqs 12-20 vs the kernel)
  Q1  median |h_ridge(lamJ) - h*|/|h*| <= .02 in every cell
  Q2  median d_span / (median c_perp / median beta_hat) in [.85, 1.15] in >= 80% of cells
  Q3  |ln(A_B(d)/(1 - c)^2 / obs)| <= .20 in >= 80% of cells
  Q4  ln(A_AMP(d)/(1 - c)^2 / obs) < -.25 in >= 80% of cells
  Q5  median c_par_scale < c/2 and median c_par_phase < c/2 (signed; |c_par| also reported) in >= 80% of cells
  Q6  |ln(A_B(d_hat)/(1 - beta d_hat)^2 / obs)| <= .20 in >= 70% of cells (d_hat = median reported Stein divergence)
  Q7  sign of the rho trend (rho .5 vs .2, 8 dB) of the Q3 prediction equals that of obs, at L8 and at L24 (both required)
Report-only: d_abs vs d_span, joint-ridge (lamJ) versions of c and e_ind, implied kappa_eff, e* vs e_par + e_perp (+ misfit), FP variants, S1.
"""
import argparse
import glob
import json
import math
from pathlib import Path

import numpy as np

import c1v2_analyze as A

HERE = Path(__file__).resolve().parent
ln = lambda x: math.log(x) if x is not None and x > 0 and math.isfinite(x) else float('nan')  # noqa: E731
med = A.med
fm = A.fm


def A_B(d, n0, q, v):
    return ((1. - d) ** 2 * n0 + (1. - d) * q * v) / (n0 + q * v)


def A_AMP(d):
    return (1. - d) ** 2


def cell_stats(rs):
    f = lambda k: np.array([r[k] for r in rs], float)  # noqa: E731
    rho, snr, L = rs[0]['rho'], rs[0]['snr_db'], rs[0]['L']
    n0p, a = 10 ** (-snr / 10), 1. - rho
    m = dict((k, med(f(k))) for k in (
        'e_star', 'e_par', 'e_perp', 'e_ind_par', 'e_ind_perp', 'e_ind_par_ridge', 'e_ind_perp_ridge', 'e_soft', 'e_soft_perp', 'e_ridge', 'e_ridge_par',
        'e_ridge_perp', 'fp_rel_xbar', 'eps_proj', 'hstar2', 'htrue2', 'c_perp', 'c_perp_ridge', 'c_par_scale', 'c_par_phase', 'c_par_scale_ridge', 'c_par_phase_ridge',
        'd_span', 'd_span_sd', 'd_abs', 'd_abs_sd', 'beta_hat', 'd_hat', 'vmeas_star', 'vrep_star', 'e_real', 'fp_rel', 'fpd_rel', 'fp_ridge_vs_soft',
        'lamJ', 'lamJ_damped', 'lam_soft', 'rec_v', 'rec_V', 'rec_u', 'e_indep_mse', 'p_re', 'p_im', 'e_split_resid'))
    m['p_abs'] = med(np.hypot(f('p_re'), f('p_im')))
    obs = m['e_perp'] / m['e_ind_perp']
    v, q, beta, c = m['vmeas_star'] * a, m['e_real'], m['beta_hat'], m['c_perp']
    d = c / beta
    dh = m['d_hat']
    pred_B = A_B(d, n0p, q, v) / (1. - c) ** 2 if c < 1. else float('nan')
    pred_AMP = A_AMP(d) / (1. - c) ** 2 if c < 1. else float('nan')
    pred_6 = A_B(dh, n0p, q, v) / (1. - beta * dh) ** 2
    out = dict(rho=rho, snr_db=snr, L=L, K=int(rs[0]['n_cols']), n=len(rs), med=m, obs=obs, n0=n0p, v=v, q=q, d=d,
               pred_B=pred_B, pred_AMP=pred_AMP, pred_6=pred_6, A_B_d=A_B(d, n0p, q, v), A_B_dhat=A_B(dh, n0p, q, v))
    out['Q2'] = dict(ratio=m['d_span'] / d, ok=bool(.85 <= m['d_span'] / d <= 1.15))
    out['Q3'] = dict(ln=ln(pred_B / obs), ok=bool(abs(ln(pred_B / obs)) <= .20))
    out['Q4'] = dict(ln=ln(pred_AMP / obs), ok=bool(ln(pred_AMP / obs) < -.25))
    out['Q5'] = dict(scale=m['c_par_scale'], phase=m['c_par_phase'], half_c=c / 2., ok=bool(m['c_par_scale'] < c / 2. and m['c_par_phase'] < c / 2.),
                     abs_ok=bool(abs(m['c_par_scale']) < c / 2. and abs(m['c_par_phase']) < c / 2.))
    out['Q6'] = dict(ln=ln(pred_6 / obs), ok=bool(abs(ln(pred_6 / obs)) <= .20))
    out['Q1'] = dict(fp_rel=m['fp_rel'], ok=bool(m['fp_rel'] <= .02))
    out['kappa'] = dict(obs=(1. - obs ** -.5) / c if obs > 0 else None,
                        pred=(1. - (1. - c) / math.sqrt(A_B(d, n0p, q, v))) / c if A_B(d, n0p, q, v) > 0 else None)
    return out


def verdicts(cells, rows_ok):
    n = len(cells)
    frac = lambda key: float(np.mean([c[key]['ok'] for c in cells]))  # noqa: E731
    v = dict(n_cells=n)
    v['Q0'] = dict(max_dllr=max(r['q0_dllr'] for r in rows_ok), max_dh=max(r['q0_dh'] for r in rows_ok), max_dm=max(r['q0_dm'] for r in rows_ok),
                   max_dh0=max(r['q0_dh0'] for r in rows_ok), max_trace_rel=max(r['q0_trace_rel'] for r in rows_ok),
                   max_b_builder=max(r['b_builder_diff'] for r in rows_ok))
    v['Q0']['ok'] = bool(v['Q0']['max_dllr'] <= 1e-8 and v['Q0']['max_dh'] <= 1e-10)
    v['Q1'] = dict(n_pass=int(sum(c['Q1']['ok'] for c in cells)), ok=bool(all(c['Q1']['ok'] for c in cells)))
    for k, need in (('Q2', .8), ('Q3', .8), ('Q4', .8), ('Q5', .8), ('Q6', .7)):
        v[k] = dict(n_pass=int(sum(c[k]['ok'] for c in cells)), frac=frac(k), need=need, ok=bool(frac(k) >= need - 1e-12))
    # Q7: rho trend at 8 dB for each L
    q7, ok7 = {}, True
    for L in sorted({c['L'] for c in cells if c['snr_db'] == 8.}):
        by = {c['rho']: c for c in cells if c['snr_db'] == 8. and c['L'] == L}
        if .2 in by and .5 in by:
            so, sp = np.sign(by[.5]['obs'] - by[.2]['obs']), np.sign(by[.5]['pred_B'] - by[.2]['pred_B'])
            q7[f'L{L}'] = dict(obs_trend=float(so), pred_trend=float(sp), obs=[by[r]['obs'] for r in (.2, .3, .5) if r in by],
                               pred=[by[r]['pred_B'] for r in (.2, .3, .5) if r in by], ok=bool(so == sp))
            ok7 = ok7 and bool(so == sp)
        else:
            ok7 = False
    v['Q7'] = dict(per_L=q7, ok=bool(ok7 and len(q7) == 2))
    ok = {k: v[k]['ok'] for k in v if k.startswith('Q')}
    br = []
    if not ok['Q1']:
        br.append('Q1 fails: the 20-step output is not at the fixed point; spec section 1 applies only approximately.')
    if not ok['Q2'] and ok['Q3']:
        br.append('Q2 fails with Q3 passing: the image and the noise see different absorption; two parameters are needed.')
    if not ok['Q3']:
        br.append('Q3 fails: the two-term structure is wrong.')
    if ok['Q3'] and not ok['Q6']:
        br.append('Q6 fails with Q3 passing: d_span is not the Stein divergence; a model for d_span becomes round 2.' if ok['Q2'] else
                  'Q6 fails with Q3 passing (and Q2 failing).')
    if not br:
        br.append('Q1-Q3 and Q6 pass.')
    v['branch'] = br
    return v


# ---------------------------------------------------------------------------------------------------------------------------- S1
def stored_index(dirp, nshard, snr_centi):
    cache = {}

    def get(r):
        if r['snr_centi_db'] != snr_centi:
            return None
        fn = Path(dirp) / f"rows_shard{r['frame'] % nshard:03d}.jsonl"
        if fn not in cache:
            cache[fn] = {}
            if fn.exists():
                for x in open(fn):
                    s = json.loads(x)
                    if s['arm'] == 'SPg_flat':
                        cache[fn][(s['config'], s['rho_permille'], s['snr_centi_db'], s['frame'])] = s
        return cache[fn].get((r['config'], r['rho_permille'], r['snr_centi_db'], r['frame']))
    return get


def check_s1(rows_ok, boot, mapd):
    getters = []
    if boot and Path(boot).is_dir():
        getters.append(('c1_boot', stored_index(boot, 100, 800), stored_index(boot, 100, 1100)))
    if mapd and Path(mapd).is_dir():
        getters.append(('c1_map', stored_index(mapd, 56, 650)))
    if not getters:
        return dict(available=False)
    worst = dict(eps_det1=0., r1_ll_in=0., r1_cerr=0, r1_syn=0)
    n_cmp, missing = 0, []
    for r in rows_ok:
        st = None
        for g in getters:
            for fn in g[1:]:
                st = st or fn(r)
        if st is None:
            missing.append(f"{r['config']} rho{r['rho']} snr{r['snr_db']:g} f{r['frame']}")
            continue
        n_cmp += 1
        for k in worst:
            worst[k] = max(worst[k], abs(r[k] - st[k]))
    return dict(available=True, n_compared=n_cmp, n_missing=len(missing), missing=missing[:12], max_abs_diff=worst,
                ok=bool(n_cmp == len(rows_ok) and max(worst.values()) < 1e-10))


# -------------------------------------------------------------------------------------------------------------------------- markdown
def write_md(res, frame_rows):
    cs, v = res['cells'], res['verdicts']
    L = ['# C1 J run: round-1 joint fixed point (frames 640-679; per-cell medians)', '',
         f"rows {res['n_rows']} (error rows {res['n_error_rows']}); cells {v['n_cells']}; frames per cell: " + ', '.join(sorted({str(c['n']) for c in cs})) +
         (' (indicative only: fewer than 40 frames)' if any(c['n'] < 40 for c in cs) else ''), '', '## Verdicts', '',
         '| test | result | verdict |', '|---|---|---|']
    q0 = v['Q0']
    L.append(f"| Q0 Codex eqs 12-20 vs kernel: max abs dLLR {q0['max_dllr']:.1e} (<=1e-8), max abs dh {q0['max_dh']:.1e} (<=1e-10) | "
             f"dm {q0['max_dm']:.1e}, dh0 {q0['max_dh0']:.1e}, trace rel {q0['max_trace_rel']:.1e}, B-builder {q0['max_b_builder']:.1e} | {'PASS' if q0['ok'] else 'FAIL'} |")
    L.append(f"| Q1 median |h_ridge(lamJ) - h*|/|h*| <= .02 in every cell | {v['Q1']['n_pass']}/{v['n_cells']} cells | {'PASS' if v['Q1']['ok'] else 'FAIL'} |")
    desc = {'Q2': 'd_span/(c_perp/beta_hat) in [.85, 1.15]', 'Q3': 'abs ln(A_B(d)/(1-c)^2 / obs) <= .20', 'Q4': 'ln(A_AMP version / obs) < -.25',
            'Q5': 'c_par (scale and phase) < c_perp/2', 'Q6': 'abs ln(A_B(d_hat)/(1-beta d_hat)^2 / obs) <= .20'}
    for k in ('Q2', 'Q3', 'Q4', 'Q5', 'Q6'):
        L.append(f"| {k} {desc[k]} | {v[k]['n_pass']}/{v['n_cells']} cells (need {v[k]['need']:.0%}) | {'PASS' if v[k]['ok'] else 'FAIL'} |")
    L.append(f"| Q7 rho-trend sign of Q3 prediction vs obs (8 dB): " + '; '.join(
        f"{k}: obs {d['obs_trend']:+.0f} pred {d['pred_trend']:+.0f}" for k, d in v['Q7']['per_L'].items()) + f" | | {'PASS' if v['Q7']['ok'] else 'FAIL'} (expected to fail) |")
    L += ['', 'Branch: ' + ' '.join(v['branch']), '']
    s1 = res['S1']
    if s1.get('available'):
        L += [f"S1 (stored c1_boot / c1_map rows): compared {s1['n_compared']}, missing {s1['n_missing']}, max abs diff {json.dumps(s1['max_abs_diff'])} -> "
              f"{'PASS' if s1['ok'] else 'FAIL'}", '']
    else:
        L += ['S1: stored row directories not available here (not checked).', '']
    L += ['## Q-statistics per cell', '',
          '| SNR | rho | L | n | obs e_perp/e_ind,perp | d=c/beta | c_perp | beta_hat | d_span | d_span/d | pred A_B | ln Q3 | pred A_AMP | ln Q4 | d_hat | pred Q6 | ln Q6 | fp_rel | c_par scale | c_par phase |',
          '|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|']
    for c in cs:
        m = c['med']
        L.append(f"| {c['snr_db']:g} | {c['rho']:g} | {c['L']} | {c['n']} | {fm(c['obs'])} | {fm(c['d'])} | {fm(m['c_perp'])} | {fm(m['beta_hat'])} | {fm(m['d_span'])} | "
                 f"{fm(c['Q2']['ratio'])} | {fm(c['pred_B'])} | {fm(c['Q3']['ln'])} | {fm(c['pred_AMP'])} | {fm(c['Q4']['ln'])} | {fm(m['d_hat'])} | {fm(c['pred_6'])} | "
                 f"{fm(c['Q6']['ln'])} | {fm(m['fp_rel'], 4)} | {fm(m['c_par_scale'])} | {fm(m['c_par_phase'])} |")
    L += ['', '## Report-only: error split and totals (medians)', '',
          '| SNR | rho | L | e* | e_par | e_perp | misfit eps_proj | e*/(e_par+e_perp+misfit) | e_ind,par | e_ind,perp | e_indep_mse | e_soft | |p| | |h*|^2 | |h|^2 | E_real |',
          '|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|']
    for c in cs:
        m = c['med']
        L.append(f"| {c['snr_db']:g} | {c['rho']:g} | {c['L']} | {fm(m['e_star'], 4)} | {fm(m['e_par'], 4)} | {fm(m['e_perp'], 4)} | {fm(m['eps_proj'], 5)} | "
                 f"{fm(1. + m['e_split_resid'] / max(m['e_star'], 1e-300), 4)} | {fm(m['e_ind_par'], 4)} | {fm(m['e_ind_perp'], 4)} | {fm(m['e_indep_mse'], 4)} | "
                 f"{fm(m['e_soft'], 4)} | {fm(m['p_abs'])} | {fm(m['hstar2'])} | {fm(m['htrue2'])} | {fm(m['e_real'])} |")
    L += ['', '## Report-only: absorption (d_abs vs d_span) and joint-ridge (lamJ) versions', '',
          '| SNR | rho | L | d_span (sd over draws) | d_abs (sd) | d_abs/d_span | c_perp | c_perp ridge | c_par scale ridge | c_par phase ridge | e_ind,perp | e_ind,perp ridge | e_perp (h* itself) | e_ridge,perp |',
          '|---|---|---|---|---|---|---|---|---|---|---|---|---|---|']
    for c in cs:
        m = c['med']
        L.append(f"| {c['snr_db']:g} | {c['rho']:g} | {c['L']} | {fm(m['d_span'])} ({fm(m['d_span_sd'])}) | {fm(m['d_abs'])} ({fm(m['d_abs_sd'])}) | {fm(m['d_abs'] / m['d_span'])} | "
                 f"{fm(m['c_perp'])} | {fm(m['c_perp_ridge'])} | {fm(m['c_par_scale_ridge'])} | {fm(m['c_par_phase_ridge'])} | {fm(m['e_ind_perp'], 4)} | "
                 f"{fm(m['e_ind_perp_ridge'], 4)} | {fm(m['e_perp'], 4)} | {fm(m['e_ridge_perp'], 4)} |")
    L += ['', '## Report-only: FP identity detail and implied kappa_eff', '',
          'kappa_eff (obs) = (1 - obs^-1/2)/c_perp; kappa_eff (pred) = (1 - (1 - c_perp)/sqrt(A_B(d)))/c_perp.  lamJ = (n0 + V v)(K + u N v) from the Codex final state (internal units).', '',
          '| SNR | rho | L | fp_rel (x = p+m*) | fp_rel (xbar, lamJ) | fp_rel (xbar, lamJ damped) | h_ridge vs h_soft | lamJ | lamJ damped | lam_soft (refit) | e_ridge | e* | kappa_eff obs | kappa_eff pred |',
          '|---|---|---|---|---|---|---|---|---|---|---|---|---|---|']
    for c in cs:
        m = c['med']
        L.append(f"| {c['snr_db']:g} | {c['rho']:g} | {c['L']} | {fm(m['fp_rel'], 4)} | {fm(m['fp_rel_xbar'], 4)} | {fm(m['fpd_rel'], 4)} | {fm(m['fp_ridge_vs_soft'], 4)} | {fm(m['lamJ'], 2)} | "
                 f"{fm(m['lamJ_damped'], 2)} | {fm(m['lam_soft'], 2)} | {fm(m['e_ridge'], 4)} | {fm(m['e_star'], 4)} | {fm(c['kappa']['obs'])} | {fm(c['kappa']['pred'])} |")
    if frame_rows:
        L += ['', '## Per frame', '',
              '| cell | frame | e* | e_par | e_perp | e_ind,perp | c_perp | c_par s/p | d_span | d_abs | beta | d_hat | fp_rel | q0 dLLR | q0 dh |', '|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|']
        for r in frame_rows:
            L.append(f"| {r['snr_db']:g} rho {r['rho']:g} {r['config']} | {r['frame']} | {r['e_star']:.4f} | {r['e_par']:.4f} | {r['e_perp']:.4f} | {r['e_ind_perp']:.4f} | "
                     f"{r['c_perp']:.3f} | {r['c_par_scale']:.3f}/{r['c_par_phase']:.3f} | {r['d_span']:.3f} | {r['d_abs']:.3f} | {r['beta_hat']:.3f} | {r['d_hat']:.3f} | "
                     f"{r['fp_rel']:.4f} | {r['q0_dllr']:.1e} | {r['q0_dh']:.1e} |")
    return '\n'.join(L) + '\n'


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument('dir', nargs='?', type=Path, default=HERE / 'out' / 'c1jfp')
    ap.add_argument('--out', type=Path, default=None)
    ap.add_argument('--boot', type=Path, default=HERE / 'out' / 'c1_boot')
    ap.add_argument('--map', type=Path, default=HERE / 'out' / 'c1_map')
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
    res = dict(n_rows=len(rows), n_error_rows=len(rows) - len(ok), cells=cells, verdicts=verdicts(cells, ok), S1=check_s1(ok, args.boot, args.map))
    (out / 'jfp.json').write_text(json.dumps(A.clean(res), indent=1, allow_nan=False) + '\n')
    md = write_md(res, sorted(ok, key=lambda r: (r['snr_db'], r['rho'], r['L'], r['frame'])) if args.frame_table else None)
    (out / 'jfp.md').write_text(md)
    print(md)


if __name__ == '__main__':
    main()
