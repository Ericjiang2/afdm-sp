#!/usr/bin/env python
"""Gates of the information-budget screen (research/info-budget-screen-20261014.md section 7 and 2.2).  Plain numpy except the optional frozen-context operator check.

  G0  J_QPSK table vs direct QUADPACK; limits; monotone
  U1  T2 and T3 forms agree: N-side Hadamard form == K-side factor form == independent dense / textbook K x K form (MODEL: log2 det(I_K + A^H A / (K sigma2))), 1e-8
  U2  A(h) with G_h = identity == N J_QPSK(a / sigma2) exactly; A invariant under unitary left factors; G_h = Ht W (FFT assembly) == dense product;
      U >= E_d[f] in expectation (MC with its confidence interval)
  U3  the J0 covariance == empirical covariance of generator rays (driver_c1.draw_c1_paths + orders.tap_sequence), Doppler unit = cycles per frame
  U4  toy exact falsification by deterministic quadrature, N in {1, 2}, flat and rank-1 covariance, SNR {0, 6.5, 15} dB, rho {0, .2, .5}; reproduces the reference values of
      codex-info-budget-skillcheck (N = L = 1, rho .5, sigma2 = 10, 1, .1); N = 4 Monte Carlo report-only.  Any LB > MI - error stops the screen.
  OP  (frozen context, --frozen-check) the screen's operator sum_l diag(cp_l a_l) S_l (IDAFT x) equals ctx.propagate_cpp of the generator for the same paths.
Writes out/ib_screen/gates/{gates.json, GATES.md}.
"""
from __future__ import annotations

import argparse
import copy
import json
import math
from pathlib import Path
import sys
import time
import traceback

import numpy as np
import scipy.linalg as sla

import ib_screen_core as C
import ib_screen_toy as T

HERE = Path(__file__).resolve().parent
OUT = HERE / 'out' / 'ib_screen' / 'gates'


def md5_file(path):
    import hashlib
    h = hashlib.md5()
    with open(path, 'rb') as s:
        for b in iter(lambda: s.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


# ------------------------------------------------------------------------------------------------------------------------ G0
def gate_G0(tab):
    rng = np.random.default_rng(3)
    g = np.exp(rng.uniform(math.log(1e-8), math.log(200.), 400))
    direct = np.array([C.bpsk_mi(x)[0] for x in g])
    err = float(np.max(np.abs(direct - tab.bpsk(g))))
    mono = bool(np.all(np.diff(tab.bpsk(np.exp(np.linspace(-18, 5.3, 5000)))) >= -1e-14))
    lim = dict(zero=float(tab(np.array([0.]))[0]), big=float(tab(np.array([1e7]))[0]), tiny=float(tab(np.array([1e-12]))[0]) / 1e-12)
    ok = bool(err < 1e-10 and mono and lim['zero'] == 0. and lim['big'] == 2. and abs(lim['tiny'] - 1. / math.log(2.)) < 1e-6)
    return dict(passed=ok, interp_max_err_vs_direct=err, node_quad_err_max=tab.node_err_max, monotone=mono, limits=lim, bpsk_at_1=float(tab.bpsk(np.array([1.]))[0]),
                criterion='|table - direct| < 1e-10 at 400 random gamma, monotone, J(0)=0, J(inf)=2, slope 1/ln2 per QPSK symbol at 0')


# ------------------------------------------------------------------------------------------------------------------------ U1
def dense_reference(consts, ref_name, ref, L, delays, q, conds):
    """independent dense evaluation (no factors): C_s, C_p as N x N sums with the dense tap covariance; MODEL also the textbook K x K form."""
    s2, rho, a = C.cond_arrays(conds)
    if ref_name == 'PHYS':
        n = np.arange(C.N)
        from scipy.special import j0
        Rd = j0(4. * np.pi * (n[:, None] - n[None, :]) / C.N) / L
    else:
        Rd = ref.M @ ref.M.T / (C.D_COEF * L)
    cdiag = L * np.diag(Rd)
    xtil = consts.idaft(q)
    out_f, out_J, out_K = [], [], []
    for c in range(len(conds)):
        s = math.sqrt(rho[c]) * consts.ptil + math.sqrt(a[c]) * xtil
        Cs = np.zeros((C.N, C.N), complex)
        Cp = np.zeros((C.N, C.N), complex)
        U_s = consts.u(s, delays)
        U_p = math.sqrt(rho[c]) * consts.u(consts.ptil, delays)
        for i in range(len(delays)):
            Cs += U_s[:, i][:, None] * Rd * U_s[:, i].conj()[None, :]
            Cp += U_p[:, i][:, None] * Rd * U_p[:, i].conj()[None, :]
        out_f.append(np.linalg.slogdet(np.eye(C.N) + Cs / s2[c])[1] / math.log(2.))
        Q = s2[c] + a[c] * cdiag
        out_J.append((np.linalg.slogdet(np.diag(Q) + Cp)[1] - np.sum(np.log(Q))) / math.log(2.))
        if ref_name == 'MODEL':
            K = C.D_COEF * L
            Amat = np.concatenate([U_s[:, i][:, None] * ref.M for i in range(len(delays))], axis=1)  # (N, K) unnormalised
            out_K.append(np.linalg.slogdet(np.eye(K) + Amat.conj().T @ Amat / (K * s2[c]))[1] / math.log(2.))
    return np.array(out_f), np.array(out_J), (np.array(out_K) if out_K else None)


def gate_U1(consts, model, phys):
    detail, ok = [], True
    for name, ref, Ls in (('MODEL', model, (4, 8, 24)), ('PHYS', phys, (4, 8, 24, 40))):
        for L in Ls:
            for frame in (0, 1):
                delays, q = C.draw_common('test', L, frame)
                fN, JN, _ = C.f_and_j(consts, ref, L, delays, q, side='N')
                fK, JK, _ = C.f_and_j(consts, ref, L, delays, q, side='K')
                fD, JD, fT = dense_reference(consts, name, ref, L, delays, q, C.CONDS)
                e = dict(ref=name, L=L, frame=frame, f_N_vs_K=float(np.max(np.abs(fN - fK))), J_N_vs_K=float(np.max(np.abs(JN - JK))),
                         f_N_vs_dense=float(np.max(np.abs(fN - fD))), J_N_vs_dense=float(np.max(np.abs(JN - JD))),
                         f_vs_textbookK=None if fT is None else float(np.max(np.abs(fN - fT))))
                vals = [v for k, v in e.items() if k.startswith(('f_', 'J_')) and v is not None]
                e['max'] = max(vals)
                e['passed'] = bool(e['max'] < 1e-8)
                ok &= e['passed']
                detail.append(e)
    return dict(passed=bool(ok), detail=detail, max_over_all=max(d['max'] for d in detail),
                criterion='N-side == K-side == dense slogdet == (MODEL) textbook log2 det(I_K + A^H A/(K s2)) to 1e-8 absolute, f and J, all 5 conditions')


# ------------------------------------------------------------------------------------------------------------------------ U2
def gate_U2(consts, tab, phys):
    detail = {}
    ok = True
    s2, rho, a = C.cond_arrays()
    # (a) G = identity: A = N J_QPSK(a/s2) exactly
    A_id, d = C.a_from_G(np.eye(C.N, dtype=complex), tab)
    want = C.N * tab(a / s2)
    detail['identity'] = dict(max_abs_diff=float(np.max(np.abs(A_id - want))), diag_min=float(d.min()), diag_max=float(d.max()), A=A_id.tolist(), want=want.tolist())
    ok &= bool(np.max(np.abs(A_id - want)) <= 1e-12)
    # (b) unitary left factor leaves A unchanged; random unitary G -> A = same as QR of itself (sanity)
    rng = np.random.default_rng(5)
    X = rng.standard_normal((C.N, C.N)) + 1j * rng.standard_normal((C.N, C.N))
    Qu, _ = np.linalg.qr(rng.standard_normal((C.N, C.N)) + 1j * rng.standard_normal((C.N, C.N)))
    A1, _ = C.a_from_G(X.copy(), tab)
    A2, _ = C.a_from_G(Qu @ X, tab)
    detail['left_unitary'] = dict(max_abs_diff=float(np.max(np.abs(A1 - A2))))
    ok &= bool(np.max(np.abs(A1 - A2)) < 1e-8)
    # (c) FFT assembly of G_h = Ht W equals the dense product
    L = 6
    delays, q = C.draw_common('test', L, 0)
    a_seq = (rng.standard_normal((C.N, L)) + 1j * rng.standard_normal((C.N, L))) / math.sqrt(2. * L)
    coef = consts.cp(delays) * a_seq
    rows = np.arange(C.N)
    Ht = np.zeros((C.N, C.N), complex)
    for i, l in enumerate(delays):
        Ht[rows, (rows - l) % C.N] = coef[:, i]
    W = np.stack([consts.idaft(e) for e in np.eye(C.N, dtype=complex)], axis=1)  # columns idaft(e_m)
    M1 = np.zeros((C.N, C.N), complex)
    for i, l in enumerate(delays):
        M1[rows, (rows - l) % C.N] = coef[:, i]
    M1 *= consts.cl1[None, :]
    G = np.fft.ifft(M1, axis=1) * (consts.cl2 * math.sqrt(C.N))[None, :]
    xcheck = rng.standard_normal(C.N) + 1j * rng.standard_normal(C.N)
    detail['G_assembly'] = dict(rel_err_dense=float(np.linalg.norm(G - Ht @ W) / np.linalg.norm(G)),
                                rel_err_apply=float(np.linalg.norm(G @ xcheck - Ht @ consts.idaft(xcheck)) / np.linalg.norm(G @ xcheck)))
    ok &= bool(detail['G_assembly']['rel_err_dense'] < 1e-12 and detail['G_assembly']['rel_err_apply'] < 1e-12)
    # (d) U >= E_d f(d) in expectation, per delay set (MC over d with its confidence interval); PHYS covariance, condition 0..4
    rows_u = []
    for L in (8, 16, 32):
        delays, _q = C.draw_common('test', L, 100 + L)
        U = C.u_bound(consts, phys, L, delays)
        fs = []
        for k in range(40):
            _, qk = C.draw_common('test', L, 200 + k + 1000 * L)
            f, _J, _ = C.f_and_j(consts, phys, L, delays, qk, side='auto')
            fs.append(f)
        fs = np.array(fs)
        m, se = fs.mean(axis=0), fs.std(axis=0, ddof=1) / math.sqrt(len(fs))
        z = (U - m) / se
        rows_u.append(dict(L=L, U=U.tolist(), mean_f=m.tolist(), se=se.tolist(), margin_over_se=z.tolist(), ok=bool(np.all(U >= m - 3. * se))))
        ok &= rows_u[-1]['ok']
    detail['U_vs_Ef'] = rows_u
    return dict(passed=bool(ok), detail=detail,
                criterion='identity: exactly N J_QPSK(a/s2); unitary-invariance < 1e-8; G assembly < 1e-12; U >= mean f - 3 SE (40 data draws per delay set, PHYS)')


# ------------------------------------------------------------------------------------------------------------------------ U3
def gate_U3():
    import driver_c1 as c1
    import orders
    import hashlib
    entropy = hashlib.sha256(b'ib_screen_u3').hexdigest()
    lags = [0, 1, 2, 4, 8, 16, 32, 64, 128, 256]
    ref = np.array([float(__import__('scipy.special', fromlist=['j0']).j0(4. * np.pi * t / C.N)) for t in lags])
    res = {}
    nrays_target = {'1e5': 100_000, '1e6': 1_000_000}
    acc = np.zeros(len(lags))
    ntaps = 0
    nrays = 0
    f = 0
    Lgen = 16
    snaps = {}
    frames_for_unit = []
    while nrays < nrays_target['1e6']:
        paths = c1.draw_c1_paths(entropy, f, Lgen)
        for d, (nu, g) in orders.tap_groups(paths['l_i'], paths['k_real'], paths['g_i']).items():
            a = orders.tap_sequence(nu, g, C.N) * math.sqrt(Lgen)  # unit-variance tap sequence
            nrays += len(nu)
            ntaps += 1
            n = len(a)
            F = np.fft.fft(a, 2 * n)
            ac = np.fft.ifft(np.abs(F) ** 2)[:n]  # sum_n a[n+tau] conj(a[n])
            acc += np.array([ac[t].real / (n - t) for t in lags])
        f += 1
        for key, tgt in nrays_target.items():
            if key not in snaps and nrays >= tgt:
                snaps[key] = dict(nrays=nrays, ntaps=ntaps, emp=(acc / ntaps).tolist())
    for key, s in snaps.items():
        emp = np.array(s['emp'])
        res[key] = dict(nrays=s['nrays'], ntaps=s['ntaps'], max_abs_dev=float(np.max(np.abs(emp - ref))), emp=emp.tolist())
    # wrong-unit alternatives are far away (power of the test)
    from scipy.special import j0
    alt = {name: float(np.max(np.abs(np.array(res['1e6']['emp']) - np.array([j0(x * t / C.N) for t in lags])))) for name, x in (('2pi*2 (cycles/frame, used)', 4. * np.pi), ('2pi*1', 2. * np.pi), ('2pi*4', 8. * np.pi))}
    ok = bool(res['1e6']['max_abs_dev'] < 1e-2 and res['1e5']['max_abs_dev'] < 1e-2 * 1.5)
    return dict(passed=ok, lags=lags, J0_ref=ref.tolist(), runs=res, power_of_test=alt,
                doppler_unit='nu = 2 cos(theta) enters a_l[n] = sum g exp(2 pi i nu n / N): nu in cycles per frame (driver_c1.draw_c1_paths: nu = 2 cos theta; orders.tap_sequence: exp(2j pi nu k / n))',
                criterion='max over lags <= 256 of |empirical (unit-variance) tap autocovariance - J0(4 pi lag / N)| < 1e-2 (10^6 rays); the 10^5-ray run is held to 1.5e-2 (statistical noise ~ .004)')


# ------------------------------------------------------------------------------------------------------------------------ U4
CODEX_REF = {10.: (.00142, .00298), 1.: (.01812, .08711), .1: (-.67701, .28870)}


def conservative(lb, mi):
    """the reference values are LB rounded down and MI rounded up at 5 decimals."""
    return math.floor(lb * 1e5) / 1e5, math.ceil(mi * 1e5) / 1e5


def gate_U4(tab):
    cases, ok = [], True
    for n in (1, 2):
        for cov in (('flat',) if n == 1 else ('flat', 'rank1')):
            for snr in (0., 6.5, 15.):
                for rho in (0., .2, .5):
                    t0 = time.perf_counter()
                    r = T.toy_case(n, cov, rho, snr_db=snr, tab=tab)
                    r['sec'] = time.perf_counter() - t0
                    r['mass'] = T.mixture_mass(T.toy_setup(n, cov, rho, 10. ** (-snr / 10.)))
                    cases.append(r)
                    ok &= bool(r['ok'] and abs(r['mass'] - 1.) < 1e-9)
                    print('U4', n, cov, snr, rho, 'LB %.5f MI %.5f margin %.2e' % (r['LB'], r['MI'], r['margin']), flush=True)
    refs = []
    for s2, (lb_ref, mi_ref) in CODEX_REF.items():
        r = T.toy_case(1, 'flat', .5, s2=s2, tab=tab)
        lb_c, mi_c = conservative(r['LB'], r['MI'])
        e = dict(sigma2=s2, LB=r['LB'], MI=r['MI'], LB_ref=lb_ref, MI_ref=mi_ref, LB_diff=r['LB'] - lb_ref, MI_diff=r['MI'] - mi_ref, quad_err=r['err'],
                 LB_floor5=lb_c, MI_ceil5=mi_c, reproduced=bool(abs(lb_c - lb_ref) < 1e-9 and abs(mi_c - mi_ref) < 1e-9 and abs(r['LB'] - lb_ref) < 1e-5 and abs(r['MI'] - mi_ref) < 1e-5),
                 LB_le_MI=bool(r['LB'] <= r['MI'] - r['err']))
        # independent N=1 checks: E A by direct (table-free) quadrature, MI by the KL form
        t = T.toy_setup(1, 'flat', .5, s2)
        EA_direct = float(__import__('scipy.integrate', fromlist=['quad']).quad(lambda x: math.exp(-x) * 2. * C.bpsk_mi(t['a'] * x / s2)[0], 0., 80., epsabs=1e-12, epsrel=1e-11, limit=400)[0])
        e['EA_table_vs_direct'] = abs(EA_direct - r['EA'])
        e['MI_KL_form'] = T.n1_mi_kl(t)
        e['MI_KL_diff'] = abs(e['MI_KL_form'] - r['MI'])
        ok &= bool(e['reproduced'] and e['LB_le_MI'] and e['EA_table_vs_direct'] < 1e-9 and e['MI_KL_diff'] < 1e-9)
        refs.append(e)
    # closed-form A vs pivoted-QR A (N = 2): the screen's QR routine on the toy
    rng = np.random.default_rng(9)
    qr_chk = []
    for cov in ('flat', 'rank1'):
        t = T.toy_setup(2, cov, .2, .2239)
        dif = []
        for _ in range(200):
            h = (rng.standard_normal(2) + 1j * rng.standard_normal(2)) / math.sqrt(2.)
            if cov == 'rank1':
                h = np.full(2, h[0])
            dif.append(abs(T.A_qr(h, t, tab) - T.A_closed(h, t, tab)))
        qr_chk.append(dict(cov=cov, max_diff=float(max(dif))))
    ok &= bool(all(c['max_diff'] < 1e-10 for c in qr_chk))
    mc = [T.toy_mc_n4(cov, rho, snr, tab) for cov, rho, snr in (('flat', .2, 6.5), ('rank1', .2, 6.5), ('flat', .5, 15.), ('rank1', .5, 0.))]
    worst = min(c['margin'] for c in cases)
    return dict(passed=bool(ok), cases=cases, codex_reference=refs, qr_vs_closed_form=qr_chk, n4_monte_carlo_report_only=mc, min_margin=worst,
                criterion='in every case LB <= MI - (err_LB + err_MI) with quadrature normalisation |mass - 1| < 1e-9 at the fine level; the three reference pairs reproduced (LB rounded down / MI rounded up at 5 decimals, abs diff < 1e-5)')


# ------------------------------------------------------------------------------------------------------------------------ OP (frozen ctx)
def gate_OP():
    from types import SimpleNamespace
    import driver_c1 as c1
    import orders
    import hashlib
    ns = SimpleNamespace(project=HERE.parents[1], native_dir='sp_afdm_native_joint_reviewed_20260921', baseline_dir='sp_afdm_frozen_reviewed_20260921')
    ctx = c1.load_context(ns)
    s = ctx.system
    consts = C.Consts()
    entropy = hashlib.sha256(b'ib_screen_op').hexdigest()
    errs = []
    for L in (4, 12):
        paths = c1.draw_c1_paths(entropy, 0, L)
        rng = np.random.default_rng(1)
        q = ((2 * rng.integers(0, 2, C.N) - 1) + 1j * (2 * rng.integers(0, 2, C.N) - 1)) / math.sqrt(2.)
        x = .6 * consts.zc + .4 * q
        wave = ctx.transform(x, s.c1, s.c2, inverse=True)
        y_gen = ctx.propagate_cpp(wave, s.c1, paths['l_i'], paths['k_real'], paths['g_i'], prefix_length=int(s.l_max_cap))
        delays = np.array(sorted(set(int(v) for v in paths['l_i'])))
        a_seq = np.stack([orders.tap_sequence(nu, g, C.N) for d, (nu, g) in sorted(orders.tap_groups(paths['l_i'], paths['k_real'], paths['g_i']).items())], axis=1)
        mine = (consts.u(wave, delays) * a_seq).sum(axis=1)
        errs.append(dict(L=L, max_abs=float(np.max(np.abs(mine - y_gen))), rel=float(np.linalg.norm(mine - y_gen) / np.linalg.norm(y_gen)),
                         c1_equal=bool(abs(consts.c1 - s.c1) == 0 and abs(consts.c2 - s.c2) == 0), wave_vs_idaft=float(np.max(np.abs(wave - consts.idaft(x))))))
    return dict(passed=bool(all(e['rel'] < 1e-12 and e['c1_equal'] and e['wave_vs_idaft'] < 1e-12 for e in errs)), detail=errs,
                criterion='screen operator sum_l diag(cp_l a_l) S_l (IDAFT x) == ctx.propagate_cpp(IDAFT x) of the generator (rel < 1e-12), same c1/c2, same IDAFT')


def md_report(res):
    g = res['gates']
    L = ['# Information-budget screen: gates', '',
         f"Run {res['_config']['date']} on deinlab, code commit `{res['_config']['commit']}`; spec `.trellis/tasks/10-08-doppler-cluster/research/info-budget-screen-20261014.md` (frozen a34777b6).", '',
         '| gate | result | decisive number |', '|---|---|---|']

    def line(name, key, txt):
        if key in g:
            L.append(f"| {name} | {'PASS' if g[key]['passed'] else 'FAIL'} | {txt} |")
    if 'G0' in g and 'interp_max_err_vs_direct' in g['G0']:
        line('G0 J_QPSK table', 'G0', f"max |table - direct quad| {g['G0']['interp_max_err_vs_direct']:.1e} (node quad err {g['G0']['node_quad_err_max']:.1e}); I_BPSK(1) = {g['G0']['bpsk_at_1']:.6f}")
    if 'U1' in g and 'max_over_all' in g['U1']:
        line('U1 T2/T3 forms', 'U1', f"max abs diff over N-side/K-side/dense/textbook-K x K: {g['U1']['max_over_all']:.1e} (bar 1e-8)")
    if 'U2' in g and 'detail' in g['U2']:
        d = g['U2']['detail']
        line('U2 A(h), U', 'U2', f"G=I: A - N J_QPSK = {d['identity']['max_abs_diff']:.1e} (exact); unitary invariance {d['left_unitary']['max_abs_diff']:.1e}; G assembly {d['G_assembly']['rel_err_dense']:.1e}; "
                              f"U >= E f: min margin/SE {min(min(x['margin_over_se']) for x in d['U_vs_Ef']):.1f}")
    if 'U3' in g and 'runs' in g['U3']:
        r = g['U3']['runs']
        line('U3 J0 covariance', 'U3', f"max dev {r['1e6']['max_abs_dev']:.4f} (10^6 rays), {r['1e5']['max_abs_dev']:.4f} (10^5 rays); wrong-unit alternatives {', '.join(f'{k}: {v:.2f}' for k, v in g['U3']['power_of_test'].items())}")
    if 'U4' in g and 'cases' in g['U4']:
        u = g['U4']
        refs = '; '.join(f"s2={e['sigma2']:g}: LB {e['LB']:.5f} (ref {e['LB_ref']:.5f}), MI {e['MI']:.5f} (ref {e['MI_ref']:.5f})" for e in u['codex_reference'])
        line('U4 toy exact', 'U4', f"{len(u['cases'])} cases, min (MI - LB - err) = {u['min_margin']:.2e}; Codex refs: {refs}")
    if 'OP' in g and 'detail' in g['OP']:
        line('OP operator vs generator', 'OP', f"rel err {max(e['rel'] for e in g['OP']['detail']):.1e}")
    L += ['', f"**Overall: {'ALL PASS' if res['all_passed'] else 'FAIL'}**", '', '## Detail', '', '```json', json.dumps(g, indent=1, default=float)[:60000], '```']
    return '\n'.join(L) + '\n'


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument('--commit', default='unknown')
    ap.add_argument('--only', default='')
    ap.add_argument('--frozen-check', action='store_true', help='run the OP gate (needs the frozen context: source env_single.sh; conda activate AFDM)')
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    only = [x for x in args.only.split(',') if x]
    gates = {}
    if args.frozen_check:
        gates['OP'] = gate_OP()
        print('OP', 'PASS' if gates['OP']['passed'] else 'FAIL')
        name = OUT / 'gates_OP.json'
        name.write_text(json.dumps(dict(_argv=sys.argv, _config=dict(date=time.strftime('%Y-%m-%d'), commit=args.commit), gates=gates), indent=1, default=float))
        return
    tab = C.QpskMI()
    consts, model, phys = C.Consts(), C.ModelRef(), C.PhysRef()
    for name, fn in (('G0', lambda: gate_G0(tab)), ('U1', lambda: gate_U1(consts, model, phys)), ('U2', lambda: gate_U2(consts, tab, phys)),
                     ('U3', lambda: gate_U3()), ('U4', lambda: gate_U4(tab))):
        if only and name not in only:
            continue
        t0 = time.perf_counter()
        try:
            gates[name] = fn()
        except Exception as error:
            gates[name] = dict(passed=False, error=repr(error), trace=traceback.format_exc()[-2000:])
        gates[name]['seconds'] = time.perf_counter() - t0
        print(name, 'PASS' if gates[name]['passed'] else 'FAIL', f"{gates[name]['seconds']:.1f}s", flush=True)
    op_path = OUT / 'gates_OP.json'
    if op_path.exists():
        gates['OP'] = json.loads(op_path.read_text())['gates']['OP']
    cfg = dict(date=time.strftime('%Y-%m-%d'), commit=args.commit, only=only, code_md5={n: md5_file(HERE / n) for n in ('ib_screen_core.py', 'ib_screen_toy.py', 'ib_screen_gates.py')},
               consts_md5=md5_file(C.OUT / 'consts.json'), phys_rank=phys.r, phys_trunc_err=phys.trunc_err)
    res = dict(_argv=sys.argv, _config=cfg, gates=gates, all_passed=bool(all(g['passed'] for g in gates.values())))
    suffix = '' if not only else '_' + '_'.join(only)
    (OUT / f'gates{suffix}.json').write_text(json.dumps(res, indent=1, default=float, allow_nan=False) + '\n')
    if not only:
        (OUT / 'GATES.md').write_text(md_report(res))
    print('ALL_PASSED' if res['all_passed'] else 'SOME_FAILED')


if __name__ == '__main__':
    main()
