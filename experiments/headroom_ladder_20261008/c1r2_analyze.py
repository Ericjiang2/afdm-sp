#!/usr/bin/env python
"""Analysis of the C1 R2 run (driver_c1r2.py).  Reads rows only.
    python -B c1r2_analyze.py [<c1r2_dir>] [--out <dir>] [--boot <c1_boot>] [--map <c1_map>] [--frame-table]
Default <c1r2_dir> = out/c1r2; outputs <out> = <c1r2_dir>/analysis/{r2.json, r2.md}.

research/c1-round2-own-symbol-theory.md section 6 (amended) is the primary analysis; the frozen section-4 statistics are kept as "frozen version (circular)".
All vectors are P_perp-projected w.r.t. h_o; sums over the frames of a cell are divided by sum |z|^2 (z = P_perp(h_I - h_o)).  D_reg = R_S - 1, D_alg = R_T - R_S (J12).

AMENDED (counterfactual split g_S = g_0 + g_img + g_det through R_S H_o; fixed-gain detector m_F):
  P1  |D_reg| > |D_alg| in >= 7/10 cells (unchanged).
  P2' alpha_0 = -Re<g_0, n_S>/|n_S|^2 (per frame; cell median) within +-20% of the median d_span in >= 8/10; control alpha_I = -Re<g_I, n_I>/|n_I|^2, |median| <= .05 in >= 8/10.
  P3' gamma' = Re<g_img, Delta_T>/|Delta_T|^2 (cell median) within +-30% of the median of beta_hat d_span in >= 7/10; the share of |g_img|^2 not along Delta_T is reported.
  P4' sum |g_0 + alpha_0 n_S|^2 / sum |g_I|^2 within +-25% of 1 - median d_hat in >= 7/10.
  P5' D_pred from measured n, b, m (S and I) and measured g_I, g_det; g_0 = -d_span n_S + r (|r|^2 = (1 - d_hat)|g_I|^2, r orthogonal to everything), g_img = beta_hat d_span Delta_T:
      per frame |s_pred|^2 + (1 - d_hat)|g_I|^2 - |z_vec|^2, s_pred = (1 - d_span) n_S + beta_hat d_span Delta_T + g_det + b_S + m_S, summed over frames; pass if
      |ln((1 + D_pred)/(1 + D_reg))| <= .15 in >= 8/10.  The size of g_det is reported.
  P6' exact additive attribution of D_reg (measured components): S - I = c_abs + c_int + c_img + c_det + c_des with c_abs = -alpha_0 n_S, c_int = (g_0 + alpha_0 n_S) - g_I, c_img = g_img,
      c_det = g_det, c_des = (n_S - n_I) + (b_S - b_I) + (m_S - m_I) (design / Gram difference of J11); with I = z_vec the contribution of c_k is 2Re<I, c_k> + Re<c_k, S - I>, so
      the five contributions add up exactly to sum(|S|^2 - |I|^2).  Reported: change of each contribution from rho .2 to .5 at 8 dB, L8 and L24 (the model says c_img;
      pass if D_reg falls and c_img carries more than half of the fall); the same attribution with the predicted components is shown next to it.
  Accounting: the exact contributions close to the measured D_reg to <= 1e-10; |g_0 + g_img + g_det - g_S| / |g_S| <= 1e-10 per frame.
  A1 (|Q_S - Q_I|_F/|Q_I|_F <= .05) is falsified in the smoke; reported, with the design contribution c_des.
"""
import argparse
import json
import math
from pathlib import Path

import numpy as np

import c1jfp_analyze as JA
import c1v2_analyze as A

HERE = Path(__file__).resolve().parent
fm = A.fm
med = A.med
TERMS = ('abs', 'img', 'bias_img', 'intr', 'ab_bias')
COMPS = ('abs', 'int', 'img', 'det', 'des')


def vec(r, name):
    return np.array(r[f'vec_{name}_re'], float) + 1j * np.array(r[f'vec_{name}_im'], float)


def ip(a, b):
    return float(np.vdot(a, b).real)


# ====================================================================================== frozen version (circular): least squares of g_S on [n_S, Delta_T]
def frame_terms(r):
    n, b, D, gI = vec(r, 'nS'), vec(r, 'bS'), vec(r, 'dT'), vec(r, 'gI')
    nI, bI, mI, mS, gS = vec(r, 'nI'), vec(r, 'bI'), vec(r, 'mI'), vec(r, 'mS'), vec(r, 'gS')
    a, g = r['alpha'], r['gamma']
    rS = gS + a * n - g * D
    nn, DD, gg = ip(n, n), ip(D, D), ip(gI, gI)
    nD, nb, bD = ip(n, D), ip(n, b), ip(b, D)

    def terms(al, ga, intr):
        return dict(abs=(al * al - 2. * al) * nn, img=ga * ga * DD + 2. * ga * (1. - al) * nD, bias_img=2. * ga * bD, intr=intr, ab_bias=-2. * al * nb)

    fit = terms(a, g, ip(rS, rS) - gg)
    ap, gp = r['d_span'], r['beta_hat'] * r['d_span']
    pred = terms(ap, gp, -r['d_hat'] * gg)
    s0 = (1. - a) * n + g * D + rS + b
    q0 = n + b + gI
    zv = nI + gI + bI + mI
    X1 = 2. * (1. - a) * ip(n, rS) + 2. * ip(b, rS) + 2. * g * ip(D, rS)
    X2 = -2. * ip(n + b, gI)
    X3 = ip(mS, mS) + 2. * ip(s0, mS) + ip(q0, q0) - ip(zv, zv)
    return dict(fit=fit, pred=pred, X1=X1, X2=X2, X3=X3, num_meas=r['eperp_S'] - r['z2'], z2=r['z2'], z2_vec=ip(zv, zv), rS2_check=abs(ip(rS, rS) - r['rS2']),
                s0q0_check=ip(s0, s0) - ip(q0, q0) - (sum(fit.values()) + X1 + X2))


def frozen_cell(rs, base):
    f = lambda k: np.array([r[k] for r in rs], float)  # noqa: E731
    ft = [frame_terms(r) for r in rs]
    sz = base['sz']
    S = lambda fn: float(np.sum([fn(t) for t in ft]))  # noqa: E731
    fit = {k: S(lambda t: t['fit'][k]) / sz for k in TERMS}
    pred = {k: S(lambda t: t['pred'][k]) / sz for k in TERMS}
    drop = dict(X1=S(lambda t: t['X1']) / sz, X2=S(lambda t: t['X2']) / sz, X3=S(lambda t: t['X3']) / sz)
    rebuilt = sum(fit.values()) + sum(drop.values())
    D_reg, D_pred = base['D_reg'], sum(pred.values())
    rS2, gI2 = float(np.sum(f('rS2'))), float(np.sum(f('gI2')))
    d_med = med(f('d_hat'))
    out = dict(D_fit=sum(fit.values()), D_pred=D_pred, fit=fit, pred=pred, drop=drop, rebuilt=rebuilt, closure=abs(rebuilt - D_reg),
               alg_check=max(abs(t['s0q0_check']) for t in ft) / max(sz / len(ft), 1e-300), rS2_fit_check=max(t['rS2_check'] for t in ft))
    out['P2'] = dict(alpha=med(f('alpha')), d_span=med(f('d_span')), rel=med(f('alpha')) / med(f('d_span')) - 1., alpha_I=med(f('alpha_I')),
                     ok=bool(abs(med(f('alpha')) / med(f('d_span')) - 1.) <= .20), ok_ctrl=bool(abs(med(f('alpha_I'))) <= .05))
    bd = med(f('beta_hat') * f('d_span'))
    out['P3'] = dict(gamma=med(f('gamma')), beta_d=bd, rel=med(f('gamma')) / bd - 1., gamma_I=med(f('gamma_I')), ok=bool(abs(med(f('gamma')) / bd - 1.) <= .30))
    out['P4'] = dict(ratio=rS2 / gI2, target=1. - d_med, rel=(rS2 / gI2) / (1. - d_med) - 1., rI2_over_gI2=float(np.sum(f('rI2'))) / gI2,
                     ok=bool(abs((rS2 / gI2) / (1. - d_med) - 1.) <= .25))
    lnr = math.log((1. + D_pred) / (1. + D_reg)) if (1. + D_pred) > 0 and (1. + D_reg) > 0 else float('nan')
    out['P5'] = dict(ln=lnr, ok=bool(abs(lnr) <= .15))
    return out


def frozen_p6(cells):
    out = {}
    for L in sorted({c['L'] for c in cells if c['snr_db'] == 8.}):
        by = {c['rho']: c for c in cells if c['snr_db'] == 8. and c['L'] == L}
        if not (.2 in by and .5 in by):
            continue
        dD = by[.5]['D_reg'] - by[.2]['D_reg']
        res = dict(dD_reg=dD)
        for tag in ('fit', 'pred'):
            ch = {k: by[.5]['fz'][tag][k] - by[.2]['fz'][tag][k] for k in TERMS}
            ch.update({k: by[.5]['fz']['drop'][k] - by[.2]['fz']['drop'][k] for k in ('X1', 'X2', 'X3')})
            res[tag] = dict(changes=ch, image_share=(ch['img'] / dD) if dD != 0 else float('nan'), argmin=min(ch, key=ch.get))
        res['ok'] = bool(dD < 0 and res['fit']['image_share'] > .5)
        out[f'L{L}'] = res
    return out


def frozen_verdicts(cells):
    n = len(cells)
    cnt = lambda fn: int(sum(fn(c['fz']) for c in cells))  # noqa: E731
    v = dict(n_cells=n)
    v['P2'] = dict(n_pass=cnt(lambda c: c['P2']['ok']), n_pass_ctrl=cnt(lambda c: c['P2']['ok_ctrl']), need=8)
    v['P3'] = dict(n_pass=cnt(lambda c: c['P3']['ok']), need=7)
    v['P4'] = dict(n_pass=cnt(lambda c: c['P4']['ok']), need=7)
    v['P5'] = dict(n_pass=cnt(lambda c: c['P5']['ok']), need=8)
    for k in ('P3', 'P4', 'P5'):
        v[k]['ok'] = bool(v[k]['n_pass'] >= v[k]['need'])
    v['P2']['ok'] = bool(v['P2']['n_pass'] >= 8 and v['P2']['n_pass_ctrl'] >= 8)
    pp = frozen_p6(cells)
    v['P6'] = dict(per_L={k: dict(ok=x['ok'], dD_reg=x['dD_reg'], image_share=x['fit']['image_share'], argmin=x['fit']['argmin']) for k, x in pp.items()},
                   ok=bool(len(pp) == 2 and all(x['ok'] for x in pp.values())))
    return v, pp


# ====================================================================================== amended analysis
def amend_frame(r):
    n, nI, b, bI, mS, mI = (vec(r, k) for k in ('nS', 'nI', 'bS', 'bI', 'mS', 'mI'))
    gI, g0, gimg, gdet, gS, D = (vec(r, k) for k in ('gI', 'g0', 'gimg', 'gdet', 'gS', 'dT'))
    nn, nnI, DD = ip(n, n), ip(nI, nI), ip(D, D)
    a0 = -ip(g0, n) / nn
    aI = -ip(gI, nI) / nnI
    gam = ip(gimg, D) / DD
    r0 = g0 + a0 * n
    I = nI + gI + bI + mI
    # exact additive attribution with measured components
    comps = dict(abs=-a0 * n, int=r0 - gI, img=gimg, det=gdet, des=(n - nI) + (b - bI) + (mS - mI))
    delta = sum(comps.values())
    S = n + g0 + gimg + gdet + b + mS
    contrib = {k: 2. * ip(I, c) + ip(c, delta) for k, c in comps.items()}
    exact = dict(contrib=contrib, num_exact=ip(S, S) - ip(I, I), delta_check=float(np.linalg.norm(S - I - delta)) / max(float(np.linalg.norm(S - I)), 1e-300),
                 num_meas=r['eperp_S'] - r['z2'], z2=r['z2'], z2_vec=ip(I, I), gsum=float(np.linalg.norm(g0 + gimg + gdet - gS) / np.linalg.norm(gS)))
    # prediction: augmented vectors carry the orthogonal r in an extra real coordinate
    ds, bd, dh = r['d_span'], r['beta_hat'] * r['d_span'], r['d_hat']
    rr = math.sqrt(max(1. - dh, 0.) * ip(gI, gI))
    aug = lambda v, x=0.: np.concatenate([v, [x]])  # noqa: E731
    Ia = aug(I)
    pc = dict(abs=aug(-ds * n), int=aug(-gI, rr), img=aug(bd * D), det=aug(gdet), des=aug(comps['des']))
    pdelta = sum(pc.values())
    pred_contrib = {k: 2. * ip(Ia, c) + ip(c, pdelta) for k, c in pc.items()}
    s_pred = (1. - ds) * n + bd * D + gdet + b + mS
    num_pred = ip(s_pred, s_pred) + (1. - dh) * ip(gI, gI) - ip(I, I)
    return dict(a0=a0, aI=aI, gam=gam, r02=ip(r0, r0), gI2=ip(gI, gI), gimg2=ip(gimg, gimg), gam2DD=gam * gam * DD, DD=DD, gdet2=ip(gdet, gdet), g02=ip(g0, g0),
                gS2=ip(gS, gS), nn=nn, exact=exact, pred_contrib=pred_contrib, num_pred=num_pred, pred_sum_check=sum(pred_contrib.values()) - num_pred, a0_nn=a0 * a0 * nn)


def amend_cell(rs, base):
    f = lambda k: np.array([r[k] for r in rs], float)  # noqa: E731
    af = [amend_frame(r) for r in rs]
    sz = base['sz']
    Sm = lambda fn: float(np.sum([fn(t) for t in af]))  # noqa: E731
    D_reg = base['D_reg']
    contrib = {k: Sm(lambda t: t['exact']['contrib'][k]) / sz for k in COMPS}
    pcontrib = {k: Sm(lambda t: t['pred_contrib'][k]) / sz for k in COMPS}
    rebuilt = sum(contrib.values())
    D_pred = Sm(lambda t: t['num_pred']) / sz
    gI2 = Sm(lambda t: t['gI2'])
    d_med = med(f('d_hat'))
    bd = med(f('beta_hat') * f('d_span'))
    a0, aI, gam = np.array([t['a0'] for t in af]), np.array([t['aI'] for t in af]), np.array([t['gam'] for t in af])
    out = dict(contrib=contrib, pred_contrib=pcontrib, rebuilt=rebuilt, closure=abs(rebuilt - D_reg), D_pred=D_pred,
               closure_frames=max(abs(t['exact']['num_exact'] - t['exact']['num_meas']) for t in af) / max(sz / len(af), 1e-300),
               pred_sum_check=max(abs(t['pred_sum_check']) for t in af), gsum_max=max(t['exact']['gsum'] for t in af), delta_check=max(t['exact']['delta_check'] for t in af),
               z2_vec_diff=max(abs(t['exact']['z2_vec'] - t['exact']['z2']) / t['exact']['z2'] for t in af))
    out['P2'] = dict(alpha0=med(a0), d_span=med(f('d_span')), rel=med(a0) / med(f('d_span')) - 1., alphaI=med(aI), alphaI_absmed=med(np.abs(aI)),
                     ok=bool(abs(med(a0) / med(f('d_span')) - 1.) <= .20), ok_ctrl=bool(abs(med(aI)) <= .05))
    out['P3'] = dict(gamma=med(gam), beta_d=bd, rel=med(gam) / bd - 1., off_axis=1. - Sm(lambda t: t['gam2DD']) / Sm(lambda t: t['gimg2']), ok=bool(abs(med(gam) / bd - 1.) <= .30))
    r4 = Sm(lambda t: t['r02']) / gI2
    out['P4'] = dict(ratio=r4, target=1. - d_med, d_hat=d_med, rel=r4 / (1. - d_med) - 1., ok=bool(abs(r4 / (1. - d_med) - 1.) <= .25))
    lnr = math.log((1. + D_pred) / (1. + D_reg)) if (1. + D_pred) > 0 and (1. + D_reg) > 0 else float('nan')
    out['P5'] = dict(D_reg=D_reg, D_pred=D_pred, ln=lnr, ok=bool(abs(lnr) <= .15), gdet_over_z2=Sm(lambda t: t['gdet2']) / sz, gdet_over_gS=Sm(lambda t: t['gdet2']) / Sm(lambda t: t['gS2']))
    out['sizes'] = dict(g0_over_gI=Sm(lambda t: t['g02']) / gI2, gimg_over_z2=Sm(lambda t: t['gimg2']) / sz, gdet_over_z2=Sm(lambda t: t['gdet2']) / sz,
                        DT_over_z2=Sm(lambda t: t['DD']) / sz, gS_over_gI=Sm(lambda t: t['gS2']) / gI2, absorbed_over_gI=Sm(lambda t: t['a0_nn']) / gI2,
                        mF_o_nmse=med(f('mF_o_nmse')), mF_T_nmse=med(f('mF_T_nmse')), mT_nmse=med(f('mT_nmse')), dm_img_nmse=med(f('dm_img_nmse')), dm_det_nmse=med(f('dm_det_nmse')))
    return out


def amend_p6(cells):
    out = {}
    for L in sorted({c['L'] for c in cells if c['snr_db'] == 8.}):
        by = {c['rho']: c for c in cells if c['snr_db'] == 8. and c['L'] == L}
        if not (.2 in by and .5 in by):
            continue
        dD = by[.5]['D_reg'] - by[.2]['D_reg']
        res = dict(dD_reg=dD, D_reg={f'{r:g}': by[r]['D_reg'] for r in sorted(by)})
        for tag, key in (('meas', 'contrib'), ('pred', 'pred_contrib')):
            ch = {k: by[.5]['am'][key][k] - by[.2]['am'][key][k] for k in COMPS}
            res[tag] = dict(changes=ch, img_share=(ch['img'] / dD) if dD != 0 else float('nan'), argmin=min(ch, key=ch.get),
                            values={f'{r:g}': by[r]['am'][key] for r in sorted(by)})
        res['ok'] = bool(dD < 0 and res['meas']['img_share'] > .5)
        res['ok_pred'] = bool(dD < 0 and res['pred']['img_share'] > .5)
        out[f'L{L}'] = res
    return out


def amend_verdicts(cells):
    n = len(cells)
    cnt = lambda fn: int(sum(fn(c) for c in cells))  # noqa: E731
    v = dict(n_cells=n)
    v['P1'] = dict(n_pass=cnt(lambda c: abs(c['D_reg']) > abs(c['D_alg'])), need=7)
    v['P2'] = dict(n_pass=cnt(lambda c: c['am']['P2']['ok']), n_pass_ctrl=cnt(lambda c: c['am']['P2']['ok_ctrl']), need=8)
    v['P3'] = dict(n_pass=cnt(lambda c: c['am']['P3']['ok']), need=7)
    v['P4'] = dict(n_pass=cnt(lambda c: c['am']['P4']['ok']), need=7)
    v['P5'] = dict(n_pass=cnt(lambda c: c['am']['P5']['ok']), need=8)
    v['A1'] = dict(n_pass=cnt(lambda c: c['gram_rel'] <= .05), need=n, median_gram=float(np.median([c['gram_rel'] for c in cells])))
    for k in ('P1', 'P3', 'P4', 'P5', 'A1'):
        v[k]['ok'] = bool(v[k]['n_pass'] >= v[k]['need'])
    v['P2']['ok'] = bool(v['P2']['n_pass'] >= 8 and v['P2']['n_pass_ctrl'] >= 8)
    pp = amend_p6(cells)
    v['P6'] = dict(per_L={k: dict(ok=x['ok'], ok_pred=x['ok_pred'], dD_reg=x['dD_reg'], img_share=x['meas']['img_share'], img_share_pred=x['pred']['img_share'],
                                 argmin=x['meas']['argmin'], argmin_pred=x['pred']['argmin']) for k, x in pp.items()}, ok=bool(len(pp) == 2 and all(x['ok'] for x in pp.values())))
    ok = {k: v[k]['ok'] for k in ('P1', 'P2', 'P3', 'P4', 'P5', 'P6')}
    br = []
    if ok['P2'] and ok['P4'] and not ok['P3']:
        br.append("P2' and P4' hold but P3' fails: the image path needs the adjoint and precision terms (Codex B); that is round 3.")
    if not ok['P5'] and ok['P2'] and ok['P3'] and ok['P4']:
        br.append("P5' fails while P2'-P4' hold: the dropped cross terms matter; see the exact attribution.")
    if not ok['P2']:
        br.append("P2' fails: the absorption of g_0 is not the span divergence; J24 needs the full direction weights (J14).")
    if not br:
        br.append('No pre-registered branch condition triggered beyond the individual verdicts above.')
    v['branch'] = br
    return v, pp


# ====================================================================================== cells and report
def cell_stats(rs):
    f = lambda k: np.array([r[k] for r in rs], float)  # noqa: E731
    rho, snr, L = rs[0]['rho'], rs[0]['snr_db'], rs[0]['L']
    sz = float(np.sum(f('z2')))
    R_S, R_T = float(np.sum(f('eperp_S'))) / sz, float(np.sum(f('eperp_T'))) / sz
    base = dict(sz=sz, D_reg=R_S - 1.)
    out = dict(rho=rho, snr_db=snr, L=L, n=len(rs), D_reg=R_S - 1., D_alg=R_T - R_S, R_S=R_S, R_T=R_T, gram_rel=med(f('gram_rel')),
               med=dict(beta_hat=med(f('beta_hat')), d_hat=med(f('d_hat')), d_abs=med(f('d_abs')), d_span=med(f('d_span'))))
    out['fz'] = frozen_cell(rs, base)
    out['am'] = amend_cell(rs, base)
    out['checks'] = dict(max_rec_err=float(np.max(f('rec_err'))), max_noise_diff=float(np.max(f('noise_regen_diff'))), max_split_S=float(np.max(f('split_resid_S'))),
                         max_split_I=float(np.max(f('split_resid_I'))), max_j12=float(np.max(f('j12_resid'))), mis_energy_med=med(f('mis_energy')),
                         max_gsum_stored=float(np.max(f('gsum_resid'))))
    return out


def write_md(res, frame_rows):
    cs, v, pp, fv, fpp = res['cells'], res['verdicts'], res['p6'], res['frozen_verdicts'], res['frozen_p6']
    yn = lambda b: 'PASS' if b else 'FAIL'  # noqa: E731
    L = ['# C1 R2 run (amended, section 6): the receiver\'s own symbol errors in the plain refit (frames 680-719; sums over frames per cell)', '',
         f"rows {res['n_rows']} (error rows {res['n_error_rows']}); cells {v['n_cells']}; frames per cell: " + ', '.join(sorted({str(c['n']) for c in cs})) +
         (' (indicative only: fewer than 40 frames)' if any(c['n'] < 40 for c in cs) else ''), '', "## Verdicts (amended: P2'-P6' on the counterfactual split g_S = g_0 + g_img + g_det)", '',
         '| test | cells passing | need | verdict |', '|---|---|---|---|',
         f"| P1 \\|D_reg\\| > \\|D_alg\\| | {v['P1']['n_pass']} | {v['P1']['need']} | {yn(v['P1']['ok'])} |",
         f"| P2' alpha_0 within 20% of median d_span (control \\|median alpha_I\\| <= .05: {v['P2']['n_pass_ctrl']}) | {v['P2']['n_pass']} | 8 | {yn(v['P2']['ok'])} |",
         f"| P3' gamma' within 30% of median(beta_hat d_span) | {v['P3']['n_pass']} | {v['P3']['need']} | {yn(v['P3']['ok'])} |",
         f"| P4' sum\\|g_0 + alpha_0 n_S\\|^2/sum\\|g_I\\|^2 within 25% of 1 - median d_hat | {v['P4']['n_pass']} | {v['P4']['need']} | {yn(v['P4']['ok'])} |",
         f"| P5' \\|ln((1+D_pred)/(1+D_reg))\\| <= .15 (measured n, b, m, g_I, g_det) | {v['P5']['n_pass']} | {v['P5']['need']} | {yn(v['P5']['ok'])} |",
         "| P6' c_img carries > half of the fall of D_reg with rho (8 dB): " + '; '.join(
             f"{k}: dD_reg {x['dD_reg']:+.3f}, c_img share {x['img_share']:.2f} (predicted components {x['img_share_pred']:.2f}), largest fall: {x['argmin']}" for k, x in v['P6']['per_L'].items()) +
         f" | | | {yn(v['P6']['ok'])} |",
         f"| A1 median \\|Q_S - Q_I\\|_F/\\|Q_I\\|_F <= .05 (falsified as an assumption; median {v['A1']['median_gram']:.3f}) | {v['A1']['n_pass']} | {v['A1']['need']} | {yn(v['A1']['ok'])} |", '',
         'Branch: ' + ' '.join(v['branch']), '']
    ck = res['checks']
    L += ['## Checks', '',
          "- S1 (stored c1_boot / c1_map rows): " + (f"compared {res['S1']['n_compared']}, missing {res['S1']['n_missing']}, max abs diff {json.dumps(res['S1']['max_abs_diff'])} -> {yn(res['S1']['ok'])}"
                                                     if res['S1'].get('available') else 'stored directories not available here (not checked)'),
          f"- noise reconstruction: max |regenerated - generator draw| {ck['max_noise_diff']:.1e}; max |Y - B(x) h_o - w - r_mis|/max|Y| {ck['max_rec_err']:.1e} -> {yn(ck['rec_ok'])} (<= 1e-10); "
          f"median misfit energy |r_mis|^2/N {ck['mis_energy_med']:.1e}",
          f"- exact refit split P_perp(h_X - h_o) = n + g + b + m: max relative residual S {ck['max_split_S']:.1e}, I {ck['max_split_I']:.1e} -> {yn(ck['split_ok'])}",
          f"- J12 identity residual max {ck['max_j12']:.1e} -> {yn(ck['j12_ok'])}",
          f"- g_0 + g_img + g_det = g_S: max relative residual {ck['max_gsum']:.1e} (driver {ck['max_gsum_stored']:.1e}) -> {yn(ck['gsum_ok'])} (<= 1e-10)",
          f"- accounting closure (exact attribution, measured components): max |sum of contributions - D_reg measured| = {ck['max_closure']:.1e}; per-frame numerator {ck['max_closure_frames']:.1e}; "
          f"|S - I - sum c_k| {ck['max_delta_check']:.1e}; |z_vec|^2/|z|^2 - 1 {ck['max_z2_vec']:.1e} -> {yn(ck['closure_ok'])} (<= 1e-10)", '',
          '## Per cell: D_reg, assembly and the counterfactual components (medians for coefficients; sums for D and energies)', '',
          "| SNR | rho | L | n | D_reg | D_alg | D_pred (P5') | ln (1+Dp)/(1+D) | med alpha_0 | med d_span | med alpha_I | med gamma' | med beta d_span | off-axis share of g_img | sum\\|r_0\\|^2/\\|g_I\\|^2 | 1-d_hat | gram_rel |",
          '|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|']
    for c in cs:
        a = c['am']
        L.append(f"| {c['snr_db']:g} | {c['rho']:g} | {c['L']} | {c['n']} | {fm(c['D_reg'])} | {fm(c['D_alg'])} | {fm(a['D_pred'])} | {fm(a['P5']['ln'])} | {fm(a['P2']['alpha0'])} | "
                 f"{fm(a['P2']['d_span'])} | {fm(a['P2']['alphaI'])} | {fm(a['P3']['gamma'])} | {fm(a['P3']['beta_d'])} | {fm(a['P3']['off_axis'])} | {fm(a['P4']['ratio'])} | "
                 f"{fm(a['P4']['target'])} | {fm(c['gram_rel'])} |")
    L += ['', '## Exact attribution of D_reg to the five components (divided by sum |z|^2); sum = D_reg measured', '',
          'c_abs = -alpha_0 n_S, c_int = (g_0 + alpha_0 n_S) - g_I, c_img = g_img, c_det = g_det, c_des = (n_S - n_I) + (b_S - b_I) + (m_S - m_I); contribution = 2Re<I, c> + Re<c, S - I>.', '',
          '| SNR | rho | L | abs | int | img | det | des | sum | D_reg measured | closure |', '|---|---|---|---|---|---|---|---|---|---|---|']
    for c in cs:
        t = c['am']['contrib']
        L.append(f"| {c['snr_db']:g} | {c['rho']:g} | {c['L']} | " + ' | '.join(fm(t[k]) for k in COMPS) + f" | {fm(c['am']['rebuilt'])} | {fm(c['D_reg'])} | {c['am']['closure']:.1e} |")
    L += ['', "## The same attribution with the predicted components (alpha = d_span, g_img = beta_hat d_span Delta_T, |r|^2 = (1 - d_hat)|g_I|^2 orthogonal; sum = D_pred)", '',
          '| SNR | rho | L | abs | int | img | det | des | D_pred | D_reg measured |', '|---|---|---|---|---|---|---|---|---|---|']
    for c in cs:
        t = c['am']['pred_contrib']
        L.append(f"| {c['snr_db']:g} | {c['rho']:g} | {c['L']} | " + ' | '.join(fm(t[k]) for k in COMPS) + f" | {fm(c['am']['D_pred'])} | {fm(c['D_reg'])} |")
    L += ['', "## P6': change of each component's contribution from rho .2 to .5 at 8 dB (measured; predicted-component share in the first line)", '']
    for k, x in pp.items():
        L.append(f"- {k}: D_reg {x['D_reg']} (change {x['dD_reg']:+.3f}); measured changes: " + ', '.join(f"{t} {x['meas']['changes'][t]:+.3f}" for t in COMPS) +
                 f"; c_img share {x['meas']['img_share']:.2f}; predicted-component changes: " + ', '.join(f"{t} {x['pred']['changes'][t]:+.3f}" for t in COMPS) + f" (share {x['pred']['img_share']:.2f})")
    L += ['', '## Sizes and detector quantities (sums for energies, medians for nmse)', '',
          '| SNR | rho | L | \\|g_0\\|^2/\\|g_I\\|^2 | absorbed alpha_0^2\\|n\\|^2/\\|g_I\\|^2 | \\|g_img\\|^2/\\|z\\|^2 | \\|g_det\\|^2/\\|z\\|^2 | \\|g_det\\|^2/\\|g_S\\|^2 | \\|g_S\\|^2/\\|g_I\\|^2 | \\|Delta_T\\|^2/\\|z\\|^2 | nmse m_F(h_o) | m_F(h_T) | m_T | nmse(m_F(h_o)-m_F(h_T)) | nmse(m_F(h_T)-m_T) | beta_hat | d_hat | d_span | d_abs |',
          '|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|']
    for c in cs:
        s, m = c['am']['sizes'], c['med']
        L.append(f"| {c['snr_db']:g} | {c['rho']:g} | {c['L']} | {fm(s['g0_over_gI'])} | {fm(s['absorbed_over_gI'])} | {fm(s['gimg_over_z2'])} | {fm(s['gdet_over_z2'])} | "
                 f"{fm(c['am']['P5']['gdet_over_gS'])} | {fm(s['gS_over_gI'])} | {fm(s['DT_over_z2'])} | {fm(s['mF_o_nmse'])} | {fm(s['mF_T_nmse'])} | {fm(s['mT_nmse'])} | "
                 f"{fm(s['dm_img_nmse'])} | {fm(s['dm_det_nmse'])} | {fm(m['beta_hat'])} | {fm(m['d_hat'])} | {fm(m['d_span'])} | {fm(m['d_abs'])} |")
    # ---------------------------------------------------------------- frozen version (circular)
    L += ['', '# Frozen version (circular): least squares of g_S on [n_S, Delta_T] (section 4 as frozen; retained for the record)', '',
          '| test | cells passing | need | verdict |', '|---|---|---|---|',
          f"| P2 median alpha within 20% of median d_span (control: {fv['P2']['n_pass_ctrl']}) | {fv['P2']['n_pass']} | 8 | {yn(fv['P2']['ok'])} |",
          f"| P3 median gamma within 30% of median(beta_hat d_span) | {fv['P3']['n_pass']} | {fv['P3']['need']} | {yn(fv['P3']['ok'])} |",
          f"| P4 sum\\|r_S\\|^2/sum\\|g_I\\|^2 within 25% of 1 - median d_hat | {fv['P4']['n_pass']} | {fv['P4']['need']} | {yn(fv['P4']['ok'])} |",
          f"| P5 \\|ln((1+D_pred)/(1+D_reg))\\| <= .15 | {fv['P5']['n_pass']} | {fv['P5']['need']} | {yn(fv['P5']['ok'])} |",
          "| P6 image term carries > half of the fall of D_reg: " + '; '.join(f"{k}: dD_reg {x['dD_reg']:+.3f}, share {x['image_share']:.2f}, largest fall {x['argmin']}" for k, x in fv['P6']['per_L'].items()) +
          f" | | | {yn(fv['P6']['ok'])} |", '',
          '| SNR | rho | L | D_reg | D_pred | ln | med alpha | med gamma | med beta d_span | sum r_S^2/g_I^2 | closure (model terms + X1-X3) |', '|---|---|---|---|---|---|---|---|---|---|---|']
    for c in cs:
        z = c['fz']
        L.append(f"| {c['snr_db']:g} | {c['rho']:g} | {c['L']} | {fm(c['D_reg'])} | {fm(z['D_pred'])} | {fm(z['P5']['ln'])} | {fm(z['P2']['alpha'])} | {fm(z['P3']['gamma'])} | "
                 f"{fm(z['P3']['beta_d'])} | {fm(z['P4']['ratio'])} | {z['closure']:.1e} |")
    L += ['']
    for k, x in fpp.items():
        L.append(f"- frozen P6 {k}: D_reg change {x['dD_reg']:+.3f}; image share {x['fit']['image_share']:.2f}; changes: " +
                 ', '.join(f"{t} {x['fit']['changes'][t]:+.3f}" for t in list(TERMS) + ['X1', 'X2', 'X3']))
    if frame_rows:
        L += ['', '## Per frame', '', '| cell | frame | R_S | R_T | alpha_0 | d_span | gamma\' | beta d_span | |g_det|^2/|z|^2 | gsum | gram | rec_err |', '|---|---|---|---|---|---|---|---|---|---|---|---|']
        for r in frame_rows:
            t = amend_frame(r)
            L.append(f"| {r['snr_db']:g} rho {r['rho']:g} {r['config']} | {r['frame']} | {r['eperp_S'] / r['z2']:.3f} | {r['eperp_T'] / r['z2']:.3f} | {t['a0']:.3f} | {r['d_span']:.3f} | "
                     f"{t['gam']:.3f} | {r['beta_hat'] * r['d_span']:.3f} | {t['gdet2'] / r['z2']:.3f} | {r['gsum_resid']:.1e} | {r['gram_rel']:.3f} | {r['rec_err']:.1e} |")
    return '\n'.join(L) + '\n'


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument('dir', nargs='?', type=Path, default=HERE / 'out' / 'c1r2')
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
    ver, pp = amend_verdicts(cells)
    fver, fpp = frozen_verdicts(cells)
    allc = [c['checks'] for c in cells]
    ck = dict(max_rec_err=max(c['max_rec_err'] for c in allc), max_noise_diff=max(c['max_noise_diff'] for c in allc), max_split_S=max(c['max_split_S'] for c in allc),
              max_split_I=max(c['max_split_I'] for c in allc), max_j12=max(c['max_j12'] for c in allc), mis_energy_med=float(np.median([c['mis_energy_med'] for c in allc])),
              max_gsum_stored=max(c['max_gsum_stored'] for c in allc), max_gsum=max(c['am']['gsum_max'] for c in cells), max_closure=max(c['am']['closure'] for c in cells),
              max_closure_frames=max(c['am']['closure_frames'] for c in cells), max_delta_check=max(c['am']['delta_check'] for c in cells), max_z2_vec=max(c['am']['z2_vec_diff'] for c in cells),
              max_frozen_closure=max(c['fz']['closure'] for c in cells))
    ck['rec_ok'] = bool(ck['max_rec_err'] <= 1e-10 and ck['max_noise_diff'] == 0.)
    ck['split_ok'] = bool(max(ck['max_split_S'], ck['max_split_I']) <= 1e-10)
    ck['j12_ok'] = bool(ck['max_j12'] <= 1e-10)
    ck['gsum_ok'] = bool(max(ck['max_gsum'], ck['max_gsum_stored']) <= 1e-10)
    ck['closure_ok'] = bool(max(ck['max_closure'], ck['max_closure_frames'], ck['max_delta_check']) <= 1e-10)
    res = dict(n_rows=len(rows), n_error_rows=len(rows) - len(ok), cells=cells, verdicts=ver, p6=pp, frozen_verdicts=fver, frozen_p6=fpp, checks=ck, S1=JA.check_s1(ok, args.boot, args.map))
    (out / 'r2.json').write_text(json.dumps(A.clean(res), indent=1, allow_nan=False) + '\n')
    md = write_md(res, sorted(ok, key=lambda r: (r['snr_db'], r['rho'], r['L'], r['frame'])) if args.frame_table else None)
    (out / 'r2.md').write_text(md)
    print(md)


if __name__ == '__main__':
    main()
