#!/usr/bin/env python
"""V1 (link check) and V3 (blind test on new cells) of the round-1 loop law (research/c1-round1-loop-theory.md, section 7).
Reads rows and JSON only; imports the frozen c1r1_model.py (LoopLaw, crossing, i_star), c1_t2_predict.py (load_curves, median_of) and
c1_t2_model.py (eta_rule) without editing them.
    python -B c1r1_verify.py v1 [--boot-dir out/c1_boot] [--map-dir out/c1_map] [--pred out/c1_t2/predictions.json] [--t1 ...] [--out out/c1r1/verify]
    python -B c1r1_verify.py v3 [--v3-dirs out/c1v3_s95r3 out/c1v3_s8r4 out/c1v3_s65r2] [--fresh out/c1r1/predictions_fresh.json] [--allow-partial]
Outputs <out>/v1.json, v1.md or v3.json, v3.md (with _argv, _config, md5 of inputs).

V1  Per frame (SPg_flat rows of c1_boot + c1_map, status ok; e = eps_det1, E = e_real, both physical units ||.||_F^2 / N, E = 1 expected;
    a = 1 - rho, n = 10^(-snr/10)):   LMMSE link q = eta a (E - e) / (n + e) (clipped at 0),  T2 link q = eta a E / (n + e);
    I_pred = J_unc(q);  I_obs = 1 - r1_ll_in.  eta per cell = out/c1_t2/predictions.json (dataset, snr_db, rho, L).
    Pass: per-cell median |I_pred - I_obs| <= .03 under LMMSE in >= 80% of cells AND LMMSE closer than T2 in >= 75% of cells, where
    closer = per-cell median over frames of (|err_LMMSE| - |err_T2|) < 0.  Report-only: per-cell median signed errors vs K/N.
V3  Cells from the new runs (A3 + SPg_flat, 200 frames, offset 3000).  eta per cell = frozen T2 rule on the cell's own A3 rows:
    eta = c1_t2_model.eta_rule(J_unc, mean(A3 r1_ll_in over frames, sorted by frame), rho, snr_db)  (the path of c1_t2_predict.main /
    c1_t0_screen.analyse_a3); the path is first checked to reproduce the stored eta of existing cells.  Model LoopLaw(..., link=True),
    modes H_w (primary), ind, coh.  Obs: I_1 = frame mean of 1 - r1_ll_in (SPg_flat), median eps_det1, FER_r1 = mean(r1_cerr > 0).
    P3a |I_1 pred - obs| <= .05 in >= 80% of cells; P3b |ln(e*_H_w / median eps_det1)| <= .30 in >= 75%; P3c |ln(Kc_R1 pred / obs)| <=
    .25 in every group whose observed I_1(K) crosses I* inside the grid; P3d e*_ind <= median eps_det1 <= e*_coh in >= 95% of cells.
    Frozen reference numbers (interpolated eta) from out/c1r1/predictions_fresh.json are shown beside the primary ones.
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import math
from pathlib import Path
import sys

import numpy as np

import c1_t2_model as M
import c1_t2_predict as PR
import c1r1_model as R1

HERE = Path(__file__).resolve().parent
N, D_COEF = 1024, 8
V1_ERR_BAR, V1_ERR_FRAC, V1_CLOSER_FRAC = 0.03, 0.80, 0.75
P3A_BAR, P3A_FRAC, P3B_BAR, P3B_FRAC, P3C_BAR, P3D_FRAC = 0.05, 0.80, 0.30, 0.75, 0.25, 0.95
ETA_CHECK_TOL = 1e-9
MODES = ('H_w', 'ind', 'coh')

ap = argparse.ArgumentParser()
ap.add_argument('mode', choices=('v1', 'v3'))
ap.add_argument('--boot-dir', default='out/c1_boot')
ap.add_argument('--map-dir', default='out/c1_map')
ap.add_argument('--v3-dirs', nargs='+', default=['out/c1v3_s95r3', 'out/c1v3_s8r4', 'out/c1v3_s65r2'])
ap.add_argument('--pred', default='out/c1_t2/predictions.json')
ap.add_argument('--fresh', default='out/c1r1/predictions_fresh.json')
ap.add_argument('--t1', default='out/c1_t1/t1_transfer.json')
ap.add_argument('--out', default='out/c1r1/verify')
ap.add_argument('--allow-partial', action='store_true', help='smoke runs only: do not require finished/merged inputs')
args = ap.parse_args()
P = lambda s: (HERE / s) if not Path(s).is_absolute() else Path(s)


def md5(path):
    return hashlib.md5(Path(path).read_bytes()).hexdigest()


def dir_fp(d):
    fs = sorted(glob.glob(str(P(d) / 'rows_shard*.jsonl')))
    return dict(n_files=len(fs), md5_of_shard_md5s=hashlib.md5(''.join(md5(f) for f in fs).encode()).hexdigest())


def scan(d, arms, fields):
    """Stream rows of dir d; keep status-ok rows of the given arms (substring prefilter), dedup by (arm, snr, rho, L, frame)."""
    keep, seen = [], set()
    st = dict(n_lines=0, n_not_ok=0, n_dup=0, n_kept=0)
    pats = [f'"arm": "{a}"' for a in arms]
    for f in sorted(glob.glob(str(P(d) / 'rows_shard*.jsonl'))):
        with open(f) as fh:
            for line in fh:
                if not line.strip():
                    continue
                st['n_lines'] += 1
                if '"status": "ok"' not in line:
                    st['n_not_ok'] += 1
                    continue
                if not any(p in line for p in pats):
                    continue
                r = json.loads(line)
                key = (r['arm'], r['snr_centi_db'], r['rho_permille'], r['L'], r['frame'])
                if key in seen:
                    st['n_dup'] += 1
                    continue
                seen.add(key)
                keep.append({k: r.get(k) for k in ('arm', 'snr_centi_db', 'rho_permille', 'L', 'frame') + fields})
                st['n_kept'] += 1
    return keep, st


def run_state(d, n_expected):
    lc = P(d) / 'logs' / 'lifecycle.txt'
    lines = [x.strip() for x in lc.read_text().splitlines()] if lc.exists() else []
    n = sum(1 for f in glob.glob(str(P(d) / 'rows_shard*.jsonl')) for x in open(f) if x.strip())
    return dict(results_json=(P(d) / 'results.json').exists(), merge_ok='merge ok' in lines, done='done' in lines, n_rows=n, n_expected=n_expected)


def gate(states):
    problems = []
    for d, st in states.items():
        if not (st['results_json'] and st['merge_ok'] and st['done']):
            problems.append(f"{d}: results.json={st['results_json']} merge_ok={st['merge_ok']} done={st['done']}")
        if st['n_rows'] != st['n_expected']:
            problems.append(f"{d}: {st['n_rows']} rows, expected {st['n_expected']}")
    if problems:
        msg = 'INPUT NOT COMPLETE: ' + ' | '.join(problems)
        if not args.allow_partial:
            sys.exit('FAIL: ' + msg + '  (use --allow-partial for a smoke run)')
        print('WARNING (--allow-partial): ' + msg, file=sys.stderr)
    return problems


def _j(o):
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, np.floating):
        return float(o)
    if isinstance(o, np.bool_):
        return bool(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, (set, tuple)):
        return list(o)
    raise TypeError(type(o))


def f(x, d=3, sign=False):
    if x is None:
        return '-'
    return format(x, f'{"+" if sign else ""}.{d}f')


cu, _ = PR.load_curves(P(args.t1))
I_STAR = float(json.loads(P(args.t1).read_text())['exit']['I_in_at_crossings']['FER0.5_linear']['I_in'])
assert abs(I_STAR - R1.i_star()) < 1e-15, 'I* differs from c1r1_model.i_star()'
CFG = dict(mode=args.mode, I_star=I_STAR, N=N, allow_partial=bool(args.allow_partial),
           md5=dict(t1=md5(P(args.t1)), pred=md5(P(args.pred)), c1r1_model=md5(HERE / 'c1r1_model.py'), c1_t2_model=md5(HERE / 'c1_t2_model.py'),
                    c1_t2_predict=md5(HERE / 'c1_t2_predict.py'), c1r1_verify=md5(HERE / 'c1r1_verify.py')))
OUT = P(args.out)
OUT.mkdir(parents=True, exist_ok=True)


# ================================================================================================ V1
def run_v1():
    CFG.update(dirs=dict(boot=args.boot_dir, map=args.map_dir), bars=dict(err=V1_ERR_BAR, err_frac=V1_ERR_FRAC, closer_frac=V1_CLOSER_FRAC))
    states = {args.boot_dir: run_state(args.boot_dir, 144000), args.map_dir: run_state(args.map_dir, 40000)}
    problems = gate(states)
    CFG['row_fingerprint'] = {d: dir_fp(d) for d in (args.boot_dir, args.map_dir)}
    preds = json.loads(P(args.pred).read_text())
    eta_tab = {(c['dataset'], round(c['snr_db'], 2), round(c['rho'], 3), c['L']): c['eta'] for c in preds['cells']}
    cells, stats = {}, {}
    for ds, d in (('c1_boot', args.boot_dir), ('c1_map', args.map_dir)):
        rows, st = scan(d, ('SPg_flat',), ('eps_det1', 'r1_ll_in', 'e_real'))
        stats[ds] = st
        for r in rows:
            cells.setdefault((ds, r['snr_centi_db'], r['rho_permille'], r['L']), []).append(r)
    recs, no_eta, groups = [], [], {}
    n_nonfinite = 0
    for (ds, sc, rp, L), rows in sorted(cells.items()):
        snr, rho = sc / 100., rp / 1000.
        rows.sort(key=lambda r: r['frame'])
        arr = np.array([[r['eps_det1'] if r['eps_det1'] is not None else np.nan, r['r1_ll_in'] if r['r1_ll_in'] is not None else np.nan,
                         r['e_real'] if r['e_real'] is not None else np.nan] for r in rows], float)
        ok = np.isfinite(arr).all(axis=1)
        n_nonfinite += int((~ok).sum())
        e, ll, E = arr[ok, 0], arr[ok, 1], arr[ok, 2]
        eta = eta_tab.get((ds, round(snr, 2), round(rho, 3), L))
        if eta is None:
            no_eta.append(dict(dataset=ds, snr_db=snr, rho=rho, L=L, n=int(ok.sum())))
            continue
        a, n = 1. - rho, 10 ** (-snr / 10)
        qL = eta * a * np.maximum(E - e, 0.) / (n + e)
        qT = eta * a * E / (n + e)
        I_obs = 1. - ll
        errL, errT = cu('J_unc', qL) - I_obs, cu('J_unc', qT) - I_obs
        rec = dict(dataset=ds, snr_db=snr, rho=rho, L=L, K=D_COEF * L, K_over_N=D_COEF * L / N, n=int(ok.sum()), n_nonfinite=int((~ok).sum()), eta=eta,
                   med_E_real=float(np.median(E)), med_eps_det1=float(np.median(e)), mean_I_obs=float(I_obs.mean()),
                   n_E_le_e=int((E <= e).sum()), n_eps_gt_E=int((e > E).sum()),
                   med_abs_L=float(np.median(abs(errL))), med_abs_T=float(np.median(abs(errT))),
                   med_signed_L=float(np.median(errL)), med_signed_T=float(np.median(errT)),
                   paired_med=float(np.median(abs(errL) - abs(errT))), frac_frames_L_closer=float(np.mean(abs(errL) < abs(errT))),
                   mean_signed_L=float(errL.mean()), mean_signed_T=float(errT.mean()))
        rec['err_ok'] = bool(rec['med_abs_L'] <= V1_ERR_BAR)
        rec['closer'] = bool(rec['paired_med'] < 0)
        recs.append(rec)
        groups.setdefault((ds, snr, rho), []).append(rec)
    nc = len(recs)
    frac_err = float(np.mean([r['err_ok'] for r in recs]))
    frac_cl = float(np.mean([r['closer'] for r in recs]))
    a_pass, b_pass = bool(frac_err >= V1_ERR_FRAC), bool(frac_cl >= V1_CLOSER_FRAC)
    allp = bool(a_pass and b_pass)
    worst = sorted(recs, key=lambda r: -r['med_abs_L'])[:5]
    verdicts = [
        f"V1 {'PASS' if allp else 'FAIL'}: median |I_pred - I_obs| <= {V1_ERR_BAR} under LMMSE in {sum(r['err_ok'] for r in recs)}/{nc} cells = {frac_err:.3f} "
        f"(need >= {V1_ERR_FRAC}) -> {'ok' if a_pass else 'NO'}; LMMSE closer than T2 in {sum(r['closer'] for r in recs)}/{nc} cells = {frac_cl:.3f} "
        f"(need >= {V1_CLOSER_FRAC}) -> {'ok' if b_pass else 'NO'}",
        f"V1 over all cells: median of cell median |err| LMMSE {np.median([r['med_abs_L'] for r in recs]):.4f}, T2 {np.median([r['med_abs_T'] for r in recs]):.4f}; "
        f"median of cell median signed err LMMSE {np.median([r['med_signed_L'] for r in recs]):+.4f}, T2 {np.median([r['med_signed_T'] for r in recs]):+.4f}",
        'V1 worst LMMSE cells (median |err|): ' + '; '.join(f"{r['dataset'][3:]} {r['snr_db']:g} dB rho {r['rho']:g} L{r['L']} {r['med_abs_L']:.3f}" for r in worst)]
    res = dict(_argv=sys.argv, _config=CFG, run_state=states, partial_problems=problems, scan_stats=stats, n_cells=nc, cells_without_eta=no_eta,
               n_nonfinite_frames_dropped=n_nonfinite, frac_err_ok=frac_err, frac_closer=frac_cl, pass_err=a_pass, pass_closer=b_pass, verdict=allp,
               verdicts=verdicts, cells=recs)
    md = ['# V1 link check (SPg_flat rows of c1_boot + c1_map; per-frame q from eps_det1 and E_real)', '',
          f'I* = {I_STAR:.4f}.  q_LMMSE = eta a (E_real - eps_det1)/(n + eps_det1) (clipped at 0), q_T2 = eta a E_real/(n + eps_det1); I_pred = J_unc(q); I_obs = 1 - r1_ll_in.', '',
          '## Verdicts', ''] + ['- ' + v for v in verdicts] + ['']
    if problems:
        md += ['**PARTIAL INPUT (smoke run): ' + ' | '.join(problems) + '**', '']
    md += ['Rows: ' + '; '.join(f"{k} {v['n_lines']} lines, {v['n_not_ok']} not ok, {v['n_dup']} dup, {v['n_kept']} SPg_flat kept" for k, v in stats.items())
           + f"; non-finite frames dropped {n_nonfinite}; cells evaluated {nc}; cells without eta: "
           + ('none' if not no_eta else '; '.join(f"{r['dataset']} {r['snr_db']:g} dB rho {r['rho']:g} L{r['L']}" for r in no_eta)), '',
           '## Per cell, grouped by (dataset, SNR, rho); errors = I_pred - I_obs (median over frames)', '']
    for (ds, snr, rho), rs in sorted(groups.items()):
        rs.sort(key=lambda r: r['L'])
        md += [f'### {ds} {snr:g} dB rho {rho:g}', '',
               '| L | K/N | n | eta | med E_real | med eps_det1 | mean I_obs | med abs err LMMSE | med abs err T2 | med err LMMSE | med err T2 | paired med (|L|-|T2|) | frames LMMSE closer | err ok | closer |',
               '|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|']
        for r in rs:
            md.append(f"| {r['L']} | {r['K_over_N']:.3f} | {r['n']} | {r['eta']:.3f} | {r['med_E_real']:.3f} | {r['med_eps_det1']:.4f} | {r['mean_I_obs']:.3f} | "
                      f"{r['med_abs_L']:.4f} | {r['med_abs_T']:.4f} | {r['med_signed_L']:+.4f} | {r['med_signed_T']:+.4f} | {r['paired_med']:+.4f} | "
                      f"{r['frac_frames_L_closer']:.2f} | {'Y' if r['err_ok'] else 'N'} | {'Y' if r['closer'] else 'N'} |")
        md.append('')
    md += ['## Unit diagnostics', '',
           f"cells with median E_real outside [0.8, 1.2]: {sum(1 for r in recs if not 0.8 <= r['med_E_real'] <= 1.2)}; frames with E_real <= eps_det1 (LMMSE q clipped to 0): "
           f"{sum(r['n_E_le_e'] for r in recs)} of {sum(r['n'] for r in recs)}", '']
    (OUT / 'v1.json').write_text(json.dumps(res, indent=1, default=_j) + '\n')
    (OUT / 'v1.md').write_text('\n'.join(md) + '\n')
    print('\n'.join(md))


# ================================================================================================ V3
V3_EXPECT = {'c1v3_s95r3': 2800, 'c1v3_s8r4': 2800, 'c1v3_s65r2': 2400}


def eta_from_a3(ll_by_frame, rho, snr_db):
    """Frozen T2 eta rule exactly as c1_t2_predict.main reads it: a3_r1_ll_in = np.mean(A3 r1_ll_in sorted by frame) (c1_t0_screen.analyse_a3)."""
    ll = np.array([ll_by_frame[k] for k in sorted(ll_by_frame)], float)
    m = float(np.mean(ll))
    return float(M.eta_rule(cu, m, rho, snr_db)), m


def eta_check():
    preds = json.loads(P(args.pred).read_text())
    tab = {(c['dataset'], round(c['snr_db'], 2), round(c['rho'], 3), c['L']): c for c in preds['cells']}
    targets = [('c1_boot', 8.0, .2, 4), ('c1_boot', 8.0, .3, 24), ('c1_boot', 11.0, .5, 32), ('c1_map', 6.5, .3, 16), ('c1_map', 5.0, .3, 8)]
    dirs = {'c1_boot': args.boot_dir, 'c1_map': args.map_dir}
    a3 = {ds: scan(dirs[ds], ('A3',), ('r1_ll_in',))[0] for ds in sorted({t[0] for t in targets})}
    out = []
    for ds, snr, rho, L in targets:
        ll = {r['frame']: float(r['r1_ll_in']) for r in a3[ds] if r['snr_centi_db'] == round(snr * 100) and r['rho_permille'] == round(rho * 1000) and r['L'] == L}
        eta, m = eta_from_a3(ll, rho_permille_to_rho(round(rho * 1000)), round(snr * 100) / 100.)
        c = tab[(ds, snr, rho, L)]
        out.append(dict(dataset=ds, snr_db=snr, rho=rho, L=L, n_frames=len(ll), eta_new=eta, eta_stored=c['eta'], rel_diff_eta=abs(eta - c['eta']) / c['eta'],
                        mean_ll_new=m, mean_ll_stored=c['a3_r1_ll_in'], abs_diff_ll=abs(m - c['a3_r1_ll_in'])))
    return out


rho_permille_to_rho = lambda rp: rp / 1000.


def run_v3():
    dirs = args.v3_dirs
    CFG.update(dirs=dict(v3=dirs, boot=args.boot_dir, map=args.map_dir, fresh=args.fresh), md5_fresh=md5(P(args.fresh)),
               bars=dict(p3a=P3A_BAR, p3a_frac=P3A_FRAC, p3b=P3B_BAR, p3b_frac=P3B_FRAC, p3c=P3C_BAR, p3d_frac=P3D_FRAC, eta_check_tol=ETA_CHECK_TOL))
    states = {d: run_state(d, V3_EXPECT.get(Path(d).name)) for d in dirs}
    problems = gate({d: s for d, s in states.items() if s['n_expected'] is not None})
    CFG['row_fingerprint'] = {d: dir_fp(d) for d in dirs}
    chk = eta_check()
    eta_ok = all(c['rel_diff_eta'] <= ETA_CHECK_TOL for c in chk)
    if not eta_ok:
        print('WARNING: eta path does not reproduce stored eta: ' + str(chk), file=sys.stderr)
    fresh = json.loads(P(args.fresh).read_text())
    ref_cell = {(round(c['snr_db'], 2), round(c['rho'], 3), c['L']): c for c in fresh['cells']}
    cells, stats = {}, {}
    for d in dirs:
        rows, st = scan(d, ('A3', 'SPg_flat'), ('r1_ll_in', 'eps_det1', 'e_real', 'r1_cerr'))
        stats[d] = st
        for r in rows:
            c = cells.setdefault((r['snr_centi_db'], r['rho_permille'], r['L']), dict(A3={}, SP={}))
            if r['arm'] == 'A3':
                c['A3'][r['frame']] = r
            else:
                c['SP'][r['frame']] = r
    recs, skipped, groups = [], [], {}
    for (sc, rp, L), c in sorted(cells.items()):
        snr, rho = sc / 100., rp / 1000.
        sp = [c['SP'][k] for k in sorted(c['SP'])
              if all(c['SP'][k][x] is not None and math.isfinite(c['SP'][k][x]) for x in ('r1_ll_in', 'eps_det1', 'r1_cerr'))]
        a3l = {k: float(r['r1_ll_in']) for k, r in c['A3'].items() if r['r1_ll_in'] is not None and math.isfinite(r['r1_ll_in'])}
        if not sp or not a3l:
            skipped.append(dict(snr_db=snr, rho=rho, L=L, n_sp=len(sp), n_a3=len(a3l)))
            continue
        eta, a3m = eta_from_a3(a3l, rho, snr)
        K = D_COEF * L
        fp = {m: R1.LoopLaw(cu, rho, snr, K, eta, m, True).fixed_point() for m in MODES}
        ref = ref_cell.get((round(snr, 2), round(rho, 3), L))
        I_obs = float(np.mean([1. - r['r1_ll_in'] for r in sp]))
        eps_med = float(np.median([r['eps_det1'] for r in sp]))
        fer = float(np.mean([r['r1_cerr'] > 0 for r in sp]))
        rec = dict(snr_db=snr, rho=rho, L=L, K=K, K_over_N=K / N, n_sp=len(sp), n_a3=len(a3l), frames_match=bool(set(c['A3']) == set(c['SP'])),
                   frame_range=[min(c['SP']), max(c['SP'])], a3_mean_r1_ll_in=a3m, eta=eta, eta_reference=None if ref is None else ref['eta_reference'],
                   I1_obs=I_obs, eps_det1_median=eps_med, fer_r1_obs=fer,
                   pred={m: dict(e=fp[m]['e'], I1=fp[m]['I1'], slope=fp[m]['slope'], c=fp[m]['c'], d=fp[m]['d'], w=fp[m]['w']) for m in MODES},
                   ref=None if ref is None else {m: dict(e=ref[m]['e'], I1=ref[m]['I1']) for m in MODES},
                   pilot_only_pred=R1.LoopLaw(cu, rho, snr, K, eta).pilot_only())
        rec['eta_ratio'] = None if ref is None else eta / ref['eta_reference']
        rec['err_I1'] = rec['pred']['H_w']['I1'] - I_obs
        rec['ln_e_over_eps'] = math.log(rec['pred']['H_w']['e'] / eps_med)
        rec['p3a_ok'] = bool(abs(rec['err_I1']) <= P3A_BAR)
        rec['p3b_ok'] = bool(abs(rec['ln_e_over_eps']) <= P3B_BAR)
        rec['p3d_ok'] = bool(rec['pred']['ind']['e'] <= eps_med <= rec['pred']['coh']['e'])
        if ref is not None:
            rec['err_I1_ref'] = ref['H_w']['I1'] - I_obs
            rec['ln_e_over_eps_ref'] = math.log(ref['H_w']['e'] / eps_med)
            rec['p3a_ok_ref'] = bool(abs(rec['err_I1_ref']) <= P3A_BAR)
            rec['p3b_ok_ref'] = bool(abs(rec['ln_e_over_eps_ref']) <= P3B_BAR)
            rec['p3d_ok_ref'] = bool(ref['ind']['e'] <= eps_med <= ref['coh']['e'])
        recs.append(rec)
        groups.setdefault((snr, rho), []).append(rec)
    nc = len(recs)
    frac = lambda key: float(np.mean([r[key] for r in recs])) if recs else float('nan')
    fa, fb, fd = frac('p3a_ok'), frac('p3b_ok'), frac('p3d_ok')
    refrecs = [r for r in recs if r['ref'] is not None]
    fr = lambda key: float(np.mean([r[key] for r in refrecs])) if refrecs else float('nan')
    # Kc per group
    gk = {}
    for (snr, rho), rs in sorted(groups.items()):
        rs.sort(key=lambda r: r['L'])
        Ks = [r['K'] for r in rs]
        kc = dict(snr_db=snr, rho=rho, Ls=[r['L'] for r in rs], K=Ks,
                  obs_I1=R1.crossing(Ks, [r['I1_obs'] for r in rs], I_STAR), obs_fer=R1.crossing(Ks, [r['fer_r1_obs'] for r in rs], .5),
                  pred_H_w=R1.crossing(Ks, [r['pred']['H_w']['I1'] for r in rs], I_STAR),
                  pred_ind=R1.crossing(Ks, [r['pred']['ind']['I1'] for r in rs], I_STAR),
                  pred_coh=R1.crossing(Ks, [r['pred']['coh']['I1'] for r in rs], I_STAR),
                  ref_H_w=None if any(r['ref'] is None for r in rs) else R1.crossing(Ks, [r['ref']['H_w']['I1'] for r in rs], I_STAR),
                  ref_H_w_stored=fresh['kc_r1_reference'].get(f'{snr:g}|{rho:g}'))
        lnr = lambda p, o: None if (p is None or o is None) else math.log(p / o)
        kc['ln_pred_over_obs_I1'] = lnr(kc['pred_H_w'], kc['obs_I1'])
        kc['ln_pred_over_obs_fer'] = lnr(kc['pred_H_w'], kc['obs_fer'])
        kc['ln_ref_over_obs_I1'] = lnr(kc['ref_H_w'], kc['obs_I1'])
        kc['evaluated'] = kc['obs_I1'] is not None  # group crosses I* inside the grid (observed I_1)
        kc['p3c_ok'] = None if not kc['evaluated'] else bool(kc['ln_pred_over_obs_I1'] is not None and abs(kc['ln_pred_over_obs_I1']) <= P3C_BAR)
        kc['evaluated_fer'] = kc['obs_fer'] is not None
        kc['p3c_ok_fer'] = None if not kc['evaluated_fer'] else bool(kc['ln_pred_over_obs_fer'] is not None and abs(kc['ln_pred_over_obs_fer']) <= P3C_BAR)
        kc['pred_only_crossing'] = bool(kc['obs_I1'] is None and kc['pred_H_w'] is not None)
        gk[f'{snr:g}|{rho:g}'] = kc
    ev = [k for k in gk.values() if k['evaluated']]
    p3c = None if not ev else bool(all(k['p3c_ok'] for k in ev))
    ev_f = [k for k in gk.values() if k['evaluated_fer']]
    p3c_f = None if not ev_f else bool(all(k['p3c_ok_fer'] for k in ev_f))
    p3a, p3b, p3d = bool(fa >= P3A_FRAC), bool(fb >= P3B_FRAC), bool(fd >= P3D_FRAC)
    vt = lambda b: 'n/a' if b is None else ('PASS' if b else 'FAIL')
    kc_s = lambda k, key: '-' if k[key] is None else f'{k[key]:.1f}'
    verdicts = [
        f"V3 eta path check: {'reproduces' if eta_ok else 'DOES NOT reproduce'} the stored eta in {len(chk)} existing cells (max rel diff {max(c['rel_diff_eta'] for c in chk):.2e})",
        f"P3a |I_1 pred - obs| <= {P3A_BAR}: {sum(r['p3a_ok'] for r in recs)}/{nc} = {fa:.3f} (need >= {P3A_FRAC}) -> {vt(p3a)}; max |err| {max(abs(r['err_I1']) for r in recs):.3f}; "
        f"frozen-reference eta: {sum(r['p3a_ok_ref'] for r in refrecs)}/{len(refrecs)} = {fr('p3a_ok_ref'):.3f}",
        f"P3b |ln(e*_H_w / median eps_det1)| <= {P3B_BAR}: {sum(r['p3b_ok'] for r in recs)}/{nc} = {fb:.3f} (need >= {P3B_FRAC}) -> {vt(p3b)}; median ln {np.median([r['ln_e_over_eps'] for r in recs]):+.3f}; "
        f"frozen-reference eta: {sum(r['p3b_ok_ref'] for r in refrecs)}/{len(refrecs)} = {fr('p3b_ok_ref'):.3f}",
        f"P3c |ln(Kc_R1 pred/obs)| <= {P3C_BAR} in every group whose observed I_1 crosses I* (primary: obs = I_1(K) crossing I*): {vt(p3c)}; "
        + '; '.join(f"{k['snr_db']:g} dB rho {k['rho']:g}: obs {kc_s(k, 'obs_I1')} pred {kc_s(k, 'pred_H_w')} ln "
                    + ('-' if k['ln_pred_over_obs_I1'] is None else f"{k['ln_pred_over_obs_I1']:+.3f}") + f" ({vt(k['p3c_ok'])})" for k in gk.values())
        + f"; [report-only: obs = FER_r1 .5 crossing -> {vt(p3c_f)}: " + '; '.join(
            f"{k['snr_db']:g}/{k['rho']:g} obs {kc_s(k, 'obs_fer')} ln " + ('-' if k['ln_pred_over_obs_fer'] is None else f"{k['ln_pred_over_obs_fer']:+.3f}") for k in gk.values()) + ']',
        f"P3d e*_ind <= median eps_det1 <= e*_coh: {sum(r['p3d_ok'] for r in recs)}/{nc} = {fd:.3f} (need >= {P3D_FRAC}) -> {vt(p3d)}; "
        f"frozen-reference eta: {sum(r['p3d_ok_ref'] for r in refrecs)}/{len(refrecs)} = {fr('p3d_ok_ref'):.3f}",
        'eta realised / eta_reference: ' + ', '.join(f"{k['snr_db']:g}/{k['rho']:g}: median {np.median([r['eta_ratio'] for r in rs if r['eta_ratio'] is not None]):.3f} "
                                                      f"(range {min(r['eta_ratio'] for r in rs if r['eta_ratio'] is not None):.3f}-{max(r['eta_ratio'] for r in rs if r['eta_ratio'] is not None):.3f})"
                                                      for k, rs in ((v, groups[(v['snr_db'], v['rho'])]) for v in gk.values()))]
    res = dict(_argv=sys.argv, _config=CFG, run_state=states, partial_problems=problems, scan_stats=stats, eta_check=chk, eta_check_ok=eta_ok,
               n_cells=nc, skipped_cells=skipped, P3a=dict(frac=fa, ok=p3a), P3b=dict(frac=fb, ok=p3b), P3c=dict(ok=p3c, ok_fer_variant=p3c_f), P3d=dict(frac=fd, ok=p3d),
               reference_fracs=dict(P3a=fr('p3a_ok_ref'), P3b=fr('p3b_ok_ref'), P3d=fr('p3d_ok_ref')), groups=gk, verdicts=verdicts, cells=recs)
    md = ['# V3 blind test on new cells (A3 + SPg_flat, 200 frames, offset 3000; model H_w, LMMSE link, own-cell eta)', '',
          f'I* = {I_STAR:.4f}.  eta = frozen T2 rule on the cell A3 rows.  Frozen reference = out/c1r1/predictions_fresh.json (eta interpolated from existing A3 cells).', '',
          '## Verdicts', ''] + ['- ' + v for v in verdicts] + ['']
    md += ['P3c group set: evaluated = observed I_1(K) crosses I* inside the grid ('
           + (', '.join(f"{k['snr_db']:g}/{k['rho']:g}" for k in ev) or 'none') + '); groups where only the H_w prediction crosses: '
           + (', '.join(f"{k['snr_db']:g}/{k['rho']:g}" for k in gk.values() if k['pred_only_crossing']) or 'none')
           + '; groups without an observed I_1 crossing: ' + (', '.join(f"{k['snr_db']:g}/{k['rho']:g}" for k in gk.values() if not k['evaluated']) or 'none'), '']
    if problems:
        md += ['**PARTIAL INPUT (smoke run): ' + ' | '.join(problems) + '**', '']
    md += ['## eta path check against stored eta (existing cells)', '', '| dataset | SNR | rho | L | frames | eta new | eta stored | rel diff | mean A3 r1_ll_in new | stored | abs diff |', '|---|---|---|---|---|---|---|---|---|---|---|']
    for c in chk:
        md.append(f"| {c['dataset']} | {c['snr_db']:g} | {c['rho']:g} | {c['L']} | {c['n_frames']} | {c['eta_new']:.12f} | {c['eta_stored']:.12f} | {c['rel_diff_eta']:.2e} | "
                  f"{c['mean_ll_new']:.12f} | {c['mean_ll_stored']:.12f} | {c['abs_diff_ll']:.2e} |")
    md += ['', 'Rows: ' + '; '.join(f"{Path(d).name} {v['n_lines']} lines, {v['n_not_ok']} not ok, {v['n_dup']} dup, {v['n_kept']} kept" for d, v in stats.items())
           + f"; cells {nc}; skipped cells {skipped or 'none'}; cells whose A3 and SPg_flat frame sets differ: "
           + (', '.join(f"{r['snr_db']:g}/{r['rho']:g}/L{r['L']}" for r in recs if not r['frames_match']) or 'none'), '']
    for (snr, rho), rs in sorted(groups.items()):
        md += [f'## Group {snr:g} dB, rho {rho:g}', '',
               '| L | K | eta | eta ref | ratio | I_1 obs | I_1 H_w | err | I_1 H_w ref | median eps_det1 | e* ind | e* H_w | e* coh | e* H_w ref | ln(e*/eps) | ln ref | P3a | P3b | P3d |',
               '|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|']
        for r in rs:
            rf = r['ref']
            md.append(f"| {r['L']} | {r['K']} | {r['eta']:.4f} | {f(r['eta_reference'], 4)} | {f(r['eta_ratio'], 3)} | {r['I1_obs']:.4f} | {r['pred']['H_w']['I1']:.4f} | "
                      f"{r['err_I1']:+.4f} | {f(None if rf is None else rf['H_w']['I1'], 4)} | {r['eps_det1_median']:.4f} | {r['pred']['ind']['e']:.4f} | "
                      f"{r['pred']['H_w']['e']:.4f} | {r['pred']['coh']['e']:.4f} | {f(None if rf is None else rf['H_w']['e'], 4)} | {r['ln_e_over_eps']:+.3f} | "
                      f"{f(r.get('ln_e_over_eps_ref'), 3, True)} | {'Y' if r['p3a_ok'] else 'N'} | {'Y' if r['p3b_ok'] else 'N'} | {'Y' if r['p3d_ok'] else 'N'} |")
        k = gk[f'{snr:g}|{rho:g}']
        md += ['', f"Kc_R1: observed I_1 crossing I* {kc_s(k, 'obs_I1')}; observed FER_r1 = .5 crossing {kc_s(k, 'obs_fer')}; predicted H_w (own eta) {kc_s(k, 'pred_H_w')}, "
                   f"ind {kc_s(k, 'pred_ind')}, coh {kc_s(k, 'pred_coh')}; frozen reference H_w {kc_s(k, 'ref_H_w_stored')} (recomputed from reference cells {kc_s(k, 'ref_H_w')}); "
                   f"ln(pred/obs I_1) {f(k['ln_pred_over_obs_I1'], 3, True)}, ln(pred/obs FER) {f(k['ln_pred_over_obs_fer'], 3, True)}, ln(ref/obs I_1) {f(k['ln_ref_over_obs_I1'], 3, True)}; "
                   f"max fixed-point slope H_w {max(r['pred']['H_w']['slope'] for r in rs):.3f}", '']
    (OUT / 'v3.json').write_text(json.dumps(res, indent=1, default=_j) + '\n')
    (OUT / 'v3.md').write_text('\n'.join(md) + '\n')
    print('\n'.join(md))

if args.mode == 'v1':
    run_v1()
else:
    run_v3()
