#!/usr/bin/env python
"""DDST zero-simulation screen (task 10-08-doppler-cluster; research/ddst-zero-sim-screen-20261014.md, frozen).

mode geometry : eigen-spectrum of the data -> pilot-correlator interference matrix
                M = (1/K) sum_j T_j^H A A^H T_j   (SPg_flat column set of driver_c1.py, frozen ZC pilot and chirp constants)
                -> out/ddst_screen/geometry.json.  Needs the frozen context (deinlab, AFDM env).  No frames, no receiver.
mode law      : round-1 law (c1r1_model.LoopLaw, H_w, LMMSE link) with DDST bounds U and R -> out/ddst_screen/law.json
                + RESULTS.md and the frozen decision.  Needs only geometry.json and the stored T1/T2 files.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import numpy as np

HERE = Path(__file__).resolve().parent
OUT = HERE / 'out' / 'ddst_screen'
N = 1024
D_COEF, W_FULL = 8, 2.5
LS = (4, 8, 12, 16, 20, 24, 28, 32, 40, 48)
DRAWS = 4
SEED_DOMAIN = 0x44445354  # "DDST"
R_GRID = tuple(range(0, N // 2 + 1, 8))
GROUPS = (('c1_boot', 8., .2), ('c1_boot', 8., .3), ('c1_boot', 8., .5),
          ('c1_boot', 11., .2), ('c1_boot', 11., .3), ('c1_boot', 11., .5), ('c1_map', 6.5, .3))
K_GRID = tuple(range(16, N + 1, 4))
GATE_RATIO, GATE_COUNT = 1.15, 5


# ------------------------------------------------------------------------------------------------ geometry
def geometry(args):
    import driver_c1
    import dpss_rx
    import tapchannel
    ns = SimpleNamespace(project=HERE.parents[1], native_dir=args.native_dir, baseline_dir=args.baseline_dir)
    ctx = driver_c1.load_context(ns)
    from physical import daft
    s = ctx.system
    pilot = np.asarray(s._zc_seq, complex)  # unit-power ZC; the rho scale cancels in f(r)
    pt = daft(pilot, s.c1, s.c2, True)
    v, _lam = dpss_rx.tap_columns(N, 0., W_FULL, D_COEF)  # (N, D) = sqrt(N) v_d
    k = np.arange(N)
    rows = []
    for L in LS:
        for draw in range(DRAWS):
            rng = np.random.default_rng(np.random.SeedSequence([20261014, SEED_DOMAIN, L, draw]))
            delays = np.sort(rng.choice(101, size=L, replace=False)).astype(int)
            cp = tapchannel._cp(N, s.c1, delays)  # (N, L)
            phase = (cp[:, :, None] * v[:, None, :]).reshape(N, L * D_COEF)  # column j = (tap, d)
            lj = np.repeat(delays, D_COEF)
            K = L * D_COEF
            A = np.stack([phase[:, j] * pt[(k - lj[j]) % N] for j in range(K)], axis=1)  # (N, K) pilot regressors
            M = np.zeros((N, N), complex)
            for j in range(K):
                # (T_j^H u)[m] = conj(phase_j[m + l_j]) u[m + l_j]
                C = np.roll(phase[:, j].conj()[:, None] * A, -lj[j], axis=0)
                M += C @ C.conj().T
            M /= K
            lam = np.clip(np.linalg.eigvalsh(M)[::-1], 0., None)
            tail = np.concatenate([np.cumsum(lam[::-1])[::-1], [0.]]) / lam.sum()  # tail[r] = f(r)
            f = lambda r: float(tail[r])
            rmin = lambda thr: int(np.argmax(tail <= thr))
            rows.append(dict(L=L, K=K, draw=draw, delays=delays.tolist(), trace=float(lam.sum()),
                             r90=rmin(.10), r99=rmin(.01), r999=rmin(.001),
                             f_at_K=f(min(K, N)), f_at_N4=f(N // 4), f_at_N2=f(N // 2),
                             f_grid=[f(r) for r in R_GRID],
                             lam_quantiles={q: float(np.quantile(lam, q)) for q in (.5, .9, .99)},
                             numerical_rank_1e9=int(np.sum(lam > 1e-9 * lam[0]))))
            print(L, draw, 'r90', rows[-1]['r90'], 'r99', rows[-1]['r99'], 'f(K)', round(rows[-1]['f_at_K'], 4),
                  'f(N/2)', round(rows[-1]['f_at_N2'], 4), flush=True)
    summary = {}
    for L in LS:
        sub = [r for r in rows if r['L'] == L]
        summary[str(L)] = dict(K=L * D_COEF, r90_median=float(np.median([r['r90'] for r in sub])),
                               r99_median=float(np.median([r['r99'] for r in sub])),
                               f_grid_median=np.median(np.array([r['f_grid'] for r in sub]), axis=0).tolist())
    cfg = dict(N=N, D=D_COEF, W=W_FULL, centre=0., Ls=LS, draws=DRAWS, seed=[20261014, SEED_DOMAIN, 'L', 'draw'],
               delays='uniform without replacement from {0..100} (C1 law)', r_grid=R_GRID, prior='flat I/K',
               native_dir=args.native_dir, baseline_dir=args.baseline_dir, c1=float(s.c1), c2=float(s.c2),
               source_sha256=ctx.sources)
    return dict(_argv=sys.argv, _config=cfg, rows=rows, summary=summary)


# ----------------------------------------------------------------------------------------------------- law
def law(args):
    import c1_t2_predict as P
    from c1r1_model import LoopLaw, crossing, i_star
    geo = json.loads((OUT / 'geometry.json').read_text())
    gK = np.array([geo['summary'][str(L)]['K'] for L in LS], float)
    gF = np.array([geo['summary'][str(L)]['f_grid_median'] for L in LS])  # (len LS, len R_GRID)
    rg = np.array(R_GRID, float)

    def phi(r_idx, K):
        f = float(np.interp(K, gK, gF[:, r_idx]))  # clamped outside [32, 384]
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
                val = fp['I1'] if r == 0 else min(fp['I1'], float(gauss))  # amendment 1: r = 0 is the baseline exactly
                if val > best:
                    best, best_r = val, r
            R_I.append(best)
            R_r.append(best_r)
        kb, ku, kr = (crossing(list(K_GRID), y, istar) for y in (base_I, U_I, R_I))
        g = None if (kb is None or kr is None) else kr / kb
        rb = None if kb is None else int(R_r[int(np.argmin(abs(np.array(K_GRID) - kb)))])
        groups.append(dict(dataset=ds, snr_db=snr, rho=rho, Kc_base=kb, Kc_U=ku, Kc_R=kr, g_R=g,
                           g_U=None if (kb is None or ku is None) else ku / kb, r_opt_at_Kc_base=rb,
                           eta_K_range=[pts[0][0], pts[-1][0]],
                           I1_base=base_I, I1_U=U_I, I1_R=R_I, r_opt=R_r))
        print(ds, snr, rho, 'Kc base', kb, 'U', ku, 'R', kr, 'g_R', g, flush=True)
    n_pass = sum(1 for gr in groups if gr['g_R'] is not None and gr['g_R'] >= GATE_RATIO)
    decision = 'PASS-to-design' if n_pass >= GATE_COUNT else 'KILL'
    geo_flag = {}
    for gr in groups:
        if gr['Kc_base'] is not None:
            r90 = float(np.interp(gr['Kc_base'], gK, [geo['summary'][str(L)]['r90_median'] for L in LS]))
            geo_flag[f"{gr['snr_db']:g}|{gr['rho']:g}"] = dict(Kc_base=gr['Kc_base'], r90=r90, r90_over_N=r90 / N)
    cfg = dict(model='H_w|L1 (c1r1_model.LoopLaw)', I_star=istar, K_grid=[K_GRID[0], K_GRID[-1], 4], r_grid=[0, N // 2, 8],
               U='r = N/2, no dimension cost', R='min(J_unc(q), (1-r/N) log2(1+qN/(N-r))/2), r optimised',
               phi='f(r) N/(N-r), per-L median, linear in K, clamped', gate=f'g_R >= {GATE_RATIO} in >= {GATE_COUNT}/7',
               eta='out/c1_t2/predictions.json, linear in K, clamped', geometry_sha=_sha(OUT / 'geometry.json'))
    return dict(_argv=sys.argv, _config=cfg, groups=groups, n_pass=n_pass, decision=decision, geometry_flag=geo_flag)


def _sha(path):
    import hashlib
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_md(geo, res):
    f0 = lambda x: '-' if x is None else f'{x:.0f}'
    f2 = lambda x: '-' if x is None else f'{x:.3f}'
    L = ['# DDST zero-simulation screen: results', '',
         'Protocol: `.trellis/tasks/10-08-doppler-cluster/research/ddst-zero-sim-screen-20261014.md` (frozen before this run).', '',
         '## Interference geometry (median over 4 delay draws)', '',
         '| L | K | r_90 | r_99 | f(K) | f(N/4) | f(N/2) |', '|---|---|---|---|---|---|---|']
    for Ls in LS:
        sub = [r for r in geo['rows'] if r['L'] == Ls]
        med = lambda key: float(np.median([r[key] for r in sub]))
        L.append(f"| {Ls} | {Ls * D_COEF} | {med('r90'):.0f} | {med('r99'):.0f} | {med('f_at_K'):.3f} | {med('f_at_N4'):.3f} | {med('f_at_N2'):.3f} |")
    L += ['', '## Round-1 cliff Kc_R1 (law H_w, LMMSE link)', '',
          '| group | Kc base | Kc U (no dim. cost) | Kc R (dim. cost) | g_U | g_R | r_opt at Kc base |',
          '|---|---|---|---|---|---|---|']
    for g in res['groups']:
        L.append(f"| {g['dataset']} {g['snr_db']:g} dB rho {g['rho']:g} | {f0(g['Kc_base'])} | {f0(g['Kc_U'])} | {f0(g['Kc_R'])} | "
                 f"{f2(g['g_U'])} | {f2(g['g_R'])} | {g['r_opt_at_Kc_base']} |")
    L += ['', f"Gate: g_R >= {GATE_RATIO} in >= {GATE_COUNT}/7 groups. Passing groups: {res['n_pass']}/7. "
          f"**Decision: {res['decision']}.**", '', '## Geometry flag at the baseline cliff', '']
    L += [f"- {k}: Kc {v['Kc_base']:.0f}, r_90 {v['r90']:.0f} ({v['r90_over_N']:.2f} N)" for k, v in res['geometry_flag'].items()]
    (OUT / 'RESULTS.md').write_text('\n'.join(L) + '\n')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument('mode', choices=('geometry', 'law'))
    ap.add_argument('--native-dir', default='sp_afdm_native_joint_reviewed_20260921')
    ap.add_argument('--baseline-dir', default='sp_afdm_frozen_reviewed_20260921')
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    if args.mode == 'geometry':
        res = geometry(args)
        (OUT / 'geometry.json').write_text(json.dumps(res, indent=1, default=float))
    else:
        res = law(args)
        (OUT / 'law.json').write_text(json.dumps(res, indent=1, default=float))
        write_md(json.loads((OUT / 'geometry.json').read_text()), res)
        print((OUT / 'RESULTS.md').read_text())


if __name__ == '__main__':
    main()
