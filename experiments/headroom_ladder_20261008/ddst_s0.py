#!/usr/bin/env python
"""DDST Stage 0 (protocol research/ddst-small-run-protocol-20261014.md section 2): transmitter without delay feedback, zero-simulation.

M_prior(L) = mean over 32 delay sets (C1 law: L distinct delays uniform on {0..100}) of the interference matrix M (ddst_core.interference_matrix).
The transmitter removes the top-r eigenvectors of M_prior(L); a real frame (true delays, M_true) then keeps the residual
    f_prior(r) = tr((I - P_prior,r) M_true) / tr(M_true)          (mean over 32 FRESH true-delay draws, disjoint from the averaging draws)
and phi_prior(r) = f_prior(r) N / (N - r).  The ddst_screen law (variants U and R, same 7 groups, same K grid, r optimised) is then re-run with phi_prior.
Gate (section 2): g_R(prior) >= 1.05 in >= 5/7 groups -> Stage 1 includes DDST-A-blind.

modes   geometry --L <L>  one L: M_prior(L), Uprior_L<LL>.npz (top 512 eigenvectors), part_L<LL>.json
        combine           part files -> geometry_prior.json
        law               law with phi_prior -> law_prior.json, RESULTS.md (also re-runs the verbatim law copy on the SCREEN geometry and
                          asserts it reproduces out/ddst_screen/law.json, so that the copy is shown to equal ddst_screen.law)
Seed streams (own domains, distinct from the screen's 0x44445354):  averaging  SeedSequence([20261014, 0x50525052, L, draw]) ("PRPR"),
fresh true delays  SeedSequence([20261014, 0x50525452, L, draw]) ("PRTR").  L grid = ddst_screen.LS (law) + L = 36 (geometry only, for the Stage-1 replication cell).
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import numpy as np

HERE = Path(__file__).resolve().parent
OUT = HERE / 'out' / 'ddst_s0'
SCREEN = HERE / 'out' / 'ddst_screen'
N = 1024
D_COEF = 8
LS = (4, 8, 12, 16, 20, 24, 28, 32, 40, 48)  # ddst_screen.LS
L_EXTRA = (36,)
DRAWS_AVG = DRAWS_TRUE = 32
DOM_AVG, DOM_TRUE = 0x50525052, 0x50525452
R_GRID = tuple(range(0, N // 2 + 1, 8))
GROUPS = (('c1_boot', 8., .2), ('c1_boot', 8., .3), ('c1_boot', 8., .5),
          ('c1_boot', 11., .2), ('c1_boot', 11., .3), ('c1_boot', 11., .5), ('c1_map', 6.5, .3))
K_GRID = tuple(range(16, N + 1, 4))
GATE_RATIO_BLIND, GATE_COUNT = 1.05, 5
U_COLS = N // 2


def delays_of(domain, L, draw):
    rng = np.random.default_rng(np.random.SeedSequence([20261014, domain, L, draw]))
    return np.sort(rng.choice(101, size=L, replace=False)).astype(int)


def md5(path):
    h = hashlib.md5()
    with open(path, 'rb') as stream:
        for block in iter(lambda: stream.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def tail_fraction(lam):
    """tail[r] = f(r) of a spectrum (screen convention: clipped at 0)."""
    lam = np.clip(lam, 0., None)
    return np.concatenate([np.cumsum(lam[::-1])[::-1], [0.]]) / lam.sum()


# ------------------------------------------------------------------------------------------------ geometry
def geometry_L(args):
    import ddst_core as core
    import driver_c1
    ns = SimpleNamespace(project=HERE.parents[1], native_dir=args.native_dir, baseline_dir=args.baseline_dir)
    ctx = driver_c1.load_context(ns)
    s = ctx.system
    pt = core.pilot_time(ctx)
    L = args.L
    OUT.mkdir(parents=True, exist_ok=True)
    avg_delays, Msum = [], np.zeros((N, N), complex)
    for draw in range(DRAWS_AVG):
        d = delays_of(DOM_AVG, L, draw)
        avg_delays.append(d.tolist())
        Msum += core.interference_matrix(d, s.c1, pt)
    Mp = Msum / DRAWS_AVG
    lam_p, V_p = core.spectrum(Mp)
    U = np.ascontiguousarray(V_p[:, :U_COLS])
    np.savez(OUT / f'Uprior_L{L:02d}.npz', U=U, lam=lam_p)
    tail_p = tail_fraction(lam_p)
    rows = []
    for draw in range(DRAWS_TRUE):
        d = delays_of(DOM_TRUE, L, draw)
        M = core.interference_matrix(d, s.c1, pt)
        trM = float(np.trace(M).real)
        diag = np.einsum('ij,ij->j', U.conj(), M @ U).real  # u_i^H M u_i
        captured = np.concatenate([[0.], np.cumsum(diag)])  # captured[r] = sum_{i<r}
        f_prior = [(trM - float(captured[r])) / trM for r in R_GRID]
        lam_t, _ = core.spectrum(M)
        tail_t = tail_fraction(lam_t)
        rows.append(dict(draw=draw, delays=d.tolist(), trace=trM, f_prior_grid=f_prior, f_genie_grid=[float(tail_t[r]) for r in R_GRID]))
        print(L, draw, 'f_prior(K)', round(f_prior[R_GRID.index(min(8 * L, U_COLS))], 4), 'f_genie(K)', round(rows[-1]['f_genie_grid'][R_GRID.index(min(8 * L, U_COLS))], 4), flush=True)
    part = dict(L=L, K=D_COEF * L, avg_delays=avg_delays, rows=rows, r90_own=int(np.argmax(tail_p <= .10)), r99_own=int(np.argmax(tail_p <= .01)),
                f_own_grid=[float(tail_p[r]) for r in R_GRID], trace_Mprior=float(lam_p.sum()),
                Uprior_md5=md5(OUT / f'Uprior_L{L:02d}.npz'), Uprior_cols=U_COLS)
    (OUT / f'part_L{L:02d}.json').write_text(json.dumps(part, indent=1))


def combine(args):
    parts = {}
    for L in LS + L_EXTRA:
        parts[L] = json.loads((OUT / f'part_L{L:02d}.json').read_text())
    summary, rows = {}, []
    for L, p in parts.items():
        fp = np.array([r['f_prior_grid'] for r in p['rows']])
        fg = np.array([r['f_genie_grid'] for r in p['rows']])
        summary[str(L)] = dict(K=p['K'], r90_median=float(p['r90_own']), r99=float(p['r99_own']),
                               f_grid_mean=fp.mean(axis=0).tolist(), f_grid_median=np.median(fp, axis=0).tolist(),
                               f_grid_std=fp.std(axis=0, ddof=1).tolist(), f_genie_grid_mean=fg.mean(axis=0).tolist(),
                               in_law_grid=L in LS, Uprior_md5=p['Uprior_md5'])
        for r in p['rows']:
            rows.append(dict(L=L, draw=r['draw'], delays=r['delays'], trace=r['trace']))
    cfg = dict(N=N, D=D_COEF, Ls=LS, L_extra_geometry_only=L_EXTRA, draws_avg=DRAWS_AVG, draws_true=DRAWS_TRUE,
               seed_avg=[20261014, DOM_AVG, 'L', 'draw'], seed_true=[20261014, DOM_TRUE, 'L', 'draw'], r_grid=R_GRID,
               delays='uniform without replacement from {0..100} (C1 law)', Uprior_cols=U_COLS,
               definition='f_prior(r) = tr((I - U_r U_r^H) M_true)/tr(M_true), U_r = top-r eigenvectors of M_prior(L) = mean of 32 averaging draws; mean over 32 fresh true draws',
               code_md5={n: md5(HERE / n) for n in ('ddst_core.py', 'ddst_s0.py', 'ddst_screen.py')},
               Uprior_files_md5={f'Uprior_L{L:02d}.npz': parts[L]['Uprior_md5'] for L in parts})
    (OUT / 'geometry_prior.json').write_text(json.dumps(dict(_argv=sys.argv, _config=cfg, rows=rows, summary=summary), indent=1))


# ------------------------------------------------------------------------------------------------------ law
def law_core(geo, fkey, label):
    """VERBATIM copy of ddst_screen.law (same classes, grids, groups, crossing), with the geometry object and the f-grid key as parameters."""
    import c1_t2_predict as P
    from c1r1_model import LoopLaw, crossing, i_star
    gK = np.array([geo['summary'][str(L)]['K'] for L in LS], float)
    gF = np.array([geo['summary'][str(L)][fkey] for L in LS])
    rg = np.array(R_GRID, float)

    def phi(r_idx, K):
        f = float(np.interp(K, gK, gF[:, r_idx]))
        return f * N / (N - rg[r_idx])

    class DdstLaw(LoopLaw):
        def __init__(self, *a, phi_val=1., **kw):
            super().__init__(*a, **kw)
            self.phi = float(phi_val)

        def parts(self, e):
            q = self.q(e)
            v = float(self.cu('M_unc', q))
            s = (self.n + self.a * v * self.phi) / ((self.rho + self.a * (1. - v)) * 1024)
            beta = 1. / (1. + self.K * s)
            d = q * v
            w = self.a * (1. - v) / (self.rho + self.a * (1. - v))
            kappa = {'ind': 0., 'H_w': w, 'coh': 1.}[self.mode]
            c = kappa * beta * d
            return dict(q=q, v=v, s=s, beta=beta, d=d, w=w, c=c, e_ind=self.K * s / (1. + self.K * s))

        def pilot_only(self):
            s = (self.n + self.a * self.phi) / (self.rho * 1024)
            return self.K * s / (1. + self.K * s)

    cu, _ = P.load_curves(HERE / 'out/c1_t1/t1_transfer.json')
    istar = i_star()
    eta_tab = json.loads((HERE / 'out/c1_t2/predictions.json').read_text())['cells']
    groups = []
    for ds, snr, rho in GROUPS:
        pts = sorted((c['K'], c['eta']) for c in eta_tab if c['dataset'] == ds and c['snr_db'] == snr and c['rho'] == rho)
        eta_of = lambda K: float(np.interp(K, [p[0] for p in pts], [p[1] for p in pts]))
        base_I, U_I, R_I, R_r = [], [], [], []
        for K in K_GRID:
            et = eta_of(K)
            base_I.append(LoopLaw(cu, rho, snr, K, et, 'H_w', True).fixed_point()['I1'])
            fpU = DdstLaw(cu, rho, snr, K, et, 'H_w', True, phi_val=phi(len(R_GRID) - 1, K)).fixed_point()
            U_I.append(fpU['I1'])
            best, best_r = -1., 0
            for i, r in enumerate(R_GRID):
                fp = DdstLaw(cu, rho, snr, K, et, 'H_w', True, phi_val=phi(i, K)).fixed_point()
                gauss = (1. - r / N) * np.log2(1. + fp['q'] * N / (N - r)) / 2.
                val = fp['I1'] if r == 0 else min(fp['I1'], float(gauss))
                if val > best:
                    best, best_r = val, r
            R_I.append(best)
            R_r.append(best_r)
        kb, ku, kr = (crossing(list(K_GRID), y, istar) for y in (base_I, U_I, R_I))
        g = None if (kb is None or kr is None) else kr / kb
        rb = None if kb is None else int(R_r[int(np.argmin(abs(np.array(K_GRID) - kb)))])
        groups.append(dict(dataset=ds, snr_db=snr, rho=rho, Kc_base=kb, Kc_U=ku, Kc_R=kr, g_R=g,
                           g_U=None if (kb is None or ku is None) else ku / kb, r_opt_at_Kc_base=rb,
                           eta_K_range=[pts[0][0], pts[-1][0]], I1_base=base_I, I1_U=U_I, I1_R=R_I, r_opt=R_r))
        print(label, ds, snr, rho, 'Kc base', kb, 'U', ku, 'R', kr, 'g_R', g, flush=True)
    return groups, istar


def same(a, b):
    if isinstance(a, dict):
        return a.keys() == b.keys() and all(same(a[k], b[k]) for k in a)
    if isinstance(a, (list, tuple)):
        return len(a) == len(b) and all(same(x, y) for x, y in zip(a, b))
    return a == b


def law(args):
    geo_screen = json.loads((SCREEN / 'geometry.json').read_text())
    stored = json.loads((SCREEN / 'law.json').read_text())
    grp_chk, _ = law_core(geo_screen, 'f_grid_median', 'check')
    keys = ('dataset', 'snr_db', 'rho', 'Kc_base', 'Kc_U', 'Kc_R', 'g_R', 'g_U', 'r_opt_at_Kc_base', 'I1_base', 'I1_U', 'I1_R', 'r_opt')
    copy_ok = all(same({k: a[k] for k in keys}, {k: b[k] for k in keys}) for a, b in zip(grp_chk, stored['groups']))
    print('verbatim copy reproduces out/ddst_screen/law.json:', copy_ok, flush=True)
    geo = json.loads((OUT / 'geometry_prior.json').read_text())
    groups, istar = law_core(geo, 'f_grid_mean', 'prior')
    n_pass = sum(1 for g in groups if g['g_R'] is not None and g['g_R'] >= GATE_RATIO_BLIND)
    decision = 'DDST-A-blind RUN' if n_pass >= GATE_COUNT else 'DDST-A-blind NOT RUN (any Stage-1 result: requires delay-support feedback)'
    cfg = dict(model='H_w|L1 (c1r1_model.LoopLaw), verbatim copy of ddst_screen.law (checked against out/ddst_screen/law.json)', I_star=istar,
               phi='f_prior(r) N/(N-r); f_prior = mean over 32 fresh true-delay draws of tr((I-P_prior,r)M_true)/tr(M_true); per-L, linear in K, clamped',
               gate=f'g_R(prior) >= {GATE_RATIO_BLIND} in >= {GATE_COUNT}/7', geometry_prior_md5=md5(OUT / 'geometry_prior.json'),
               copy_reproduces_screen_law=bool(copy_ok), code_md5={n: md5(HERE / n) for n in ('ddst_s0.py', 'ddst_core.py', 'ddst_screen.py')})
    res = dict(_argv=sys.argv, _config=cfg, groups=groups, n_pass=n_pass, decision=decision, copy_reproduces_screen_law=bool(copy_ok))
    (OUT / 'law_prior.json').write_text(json.dumps(res, indent=1, default=float))
    write_md(geo, res, stored)
    print((OUT / 'RESULTS.md').read_text())


def write_md(geo, res, stored):
    f0 = lambda x: '-' if x is None else f'{x:.0f}'
    f2 = lambda x: '-' if x is None else f'{x:.3f}'
    L = ['# DDST Stage 0: transmitter without delay feedback (zero-simulation)', '',
         'Protocol: `.trellis/tasks/10-08-doppler-cluster/research/ddst-small-run-protocol-20261014.md` section 2 (frozen).',
         'M_prior(L) = mean of M over 32 delay sets; f_prior(r) = tr((I - P_prior,r) M_true)/tr(M_true) averaged over 32 fresh true-delay draws; '
         'genie f(r) of the same draws shown for comparison.', '',
         '## Geometry of M_prior and the residual seen by real frames', '',
         '| L | K | r_90 of M_prior | r_99 of M_prior | f_prior(K) | f_genie(K) | f_prior(N/4) | f_genie(N/4) | f_prior(N/2) | f_genie(N/2) |', '|---|---|---|---|---|---|---|---|---|---|']
    for Ls in LS + L_EXTRA:
        sm = geo['summary'][str(Ls)]
        K = sm['K']
        idx = lambda r: R_GRID.index(r)
        fp, fg = sm['f_grid_mean'], sm['f_genie_grid_mean']
        L.append(f"| {Ls}{'*' if Ls in L_EXTRA else ''} | {K} | {sm['r90_median']:.0f} | {sm['r99']:.0f} | {fp[idx(K)]:.3f} | {fg[idx(K)]:.3f} | "
                 f"{fp[idx(256)]:.3f} | {fg[idx(256)]:.3f} | {fp[idx(512)]:.3f} | {fg[idx(512)]:.3f} |")
    L += ['', '(* L = 36 is geometry only, for the Stage-1 replication cell; it is not part of the law grid.)', '',
          '## Round-1 cliff Kc_R1 with phi_prior (law H_w, LMMSE link)', '',
          '| group | Kc base | Kc U | Kc R (prior) | g_U (prior) | g_R (prior) | g_R (genie, screen) | r_opt at Kc base (prior) |', '|---|---|---|---|---|---|---|---|']
    for g, gs in zip(res['groups'], stored['groups']):
        L.append(f"| {g['dataset']} {g['snr_db']:g} dB rho {g['rho']:g} | {f0(g['Kc_base'])} | {f0(g['Kc_U'])} | {f0(g['Kc_R'])} | "
                 f"{f2(g['g_U'])} | {f2(g['g_R'])} | {f2(gs['g_R'])} | {g['r_opt_at_Kc_base']} |")
    L += ['', f"Gate: g_R(prior) >= {GATE_RATIO_BLIND} in >= {GATE_COUNT}/7 groups. Passing groups: {res['n_pass']}/7. **Decision: {res['decision']}.**", '',
          f"Verbatim law copy reproduces out/ddst_screen/law.json exactly: {res['copy_reproduces_screen_law']}."]
    (OUT / 'RESULTS.md').write_text('\n'.join(L) + '\n')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument('mode', choices=('geometry', 'combine', 'law'))
    ap.add_argument('--L', type=int, default=None)
    ap.add_argument('--native-dir', default='sp_afdm_native_joint_reviewed_20260921')
    ap.add_argument('--baseline-dir', default='sp_afdm_frozen_reviewed_20260921')
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    {'geometry': geometry_L, 'combine': combine, 'law': law}[args.mode](args)


if __name__ == '__main__':
    main()
