#!/usr/bin/env python
"""Gates UB1-UB4 and OP of the upper-bound screen (spec research/ub-screen-20261015.md section 7).  Writes out/ub_screen/gates/gates.json + GATES.md.

  UB1 toy:        UB = J + n log2(1 + a / sigma2) - f  >=  MI - err_MI - 1e-12 in all 27 deterministic quadrature cases of the screen's U4 set (f, J recomputed with ib_screen_toy; = stored to 1e-12).
  UB2 identity:   direct N-side log2 det(I + Cbar / sigma2), Cbar = rho sum_l D_l(pt) R_l D_l(pt)^H + a diag(c)  ==  J + Cst  (relative 1e-9), 3 gate frames x MODEL/PHYS/RAY x L in {8, 32} x 5 conditions;
                  RAY: K-side f also equals the direct N-side log2 det(I + C_s / sigma2) (relative 1e-9) (MODEL / PHYS reported as well).
  UB3 mean cov:   L = 8, one gate frame, 6.5 dB rho .2, 2000 i.i.d. QPSK draws: ||mean C_s - Cbar||_F <= 4 sqrt(mean ||C_s - M||_F^2 / 2000), running sums only.
  UB4 RAY law:    stage 'locate' of the OLD screen: ray_params(C.rng_for('locate', L, frame, 'rays'), L) rebuilt with C.draw_rays' formula == C.draw_rays (np.array_equal), diag R_l = 1/L to 1e-12.
  OP:             a smoke run of ub_screen_run writes config / results json carrying _argv and _config (flags, seed domain, frame counts, L sets, code md5); this file's json carries them too.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import sys
import time
import traceback

import numpy as np

import ib_screen_core as C
import ib_screen_toy as T
import ub_screen_core as U
import ub_screen_run as R

HERE = Path(__file__).resolve().parent
GATE_OUT = U.OUT / 'gates'
N = C.N


def md5_file(path):
    return hashlib.md5(Path(path).read_bytes()).hexdigest()


# ------------------------------------------------------------------------------------------------------------------ helpers
class TapCov:
    """The L explicit N x N tap covariances R_l (MODEL/PHYS: one shared matrix; RAY: R_l = F_l F_l^H built on demand), c_n = sum_l R_l[n, n]."""

    def __init__(self, ref, L, Fs=None):
        self.ref, self.L, self.Fs = ref, int(L), Fs
        if ref.name != 'RAY':
            F = ref.factor(L)
            self.shared = F @ F.T

    def get(self, l):
        if self.ref.name == 'RAY':
            F = self.Fs[l]
            return F @ F.conj().T
        return self.shared

    def c(self):
        if self.ref.name == 'RAY':
            return sum(np.real(np.diag(self.get(l))) for l in range(self.L))
        return self.L * np.real(np.diag(self.shared))

    def cs(self, Us):
        """C_s = sum_l diag(u_l) R_l diag(u_l)^H, N-side Hadamard form from the explicit R_l."""
        out = np.zeros((N, N), complex)
        for l in range(self.L):
            u = Us[:, l]
            out += self.get(l) * (u[:, None] * u.conj()[None, :])
        return out


def logdet_pd(M):
    M = (M + M.conj().T) / 2.
    return C.logdet2_chol(M)[0]


def frame_objects(consts, ref, stage, L, frame):
    """delays, q and (RAY) the factors of the frame's drawn counts / angles."""
    delays, q = U.draw_common(stage, L, frame)
    Fs = None
    if ref.name == 'RAY':
        counts, thetas, _z = U.ray_params(U.rng_for(stage, L, frame, 'rays'), L)
        Fs = U.ray_factors(thetas, counts, L)
    return delays, q, Fs


# ------------------------------------------------------------------------------------------------------------------- UB1
def gate_UB1():
    stored = json.loads((C.OUT / 'gates' / 'gates.json').read_text())['gates']['U4']['cases']
    cases = [c for c in stored if c['n'] in (1, 2)]  # the 27 deterministic quadrature cases (N = 4 Monte Carlo lives under another key)
    out, worst_fj = [], 0.
    for c in cases:
        t = T.toy_setup(c['n'], c['cov'], c['rho'], c['sigma2'])
        f, J = T.toy_f_J(t)
        d_fj = max(abs(f - c['f']), abs(J - c['J']))
        worst_fj = max(worst_fj, d_fj)
        a = 1. - c['rho']
        cs = float(U.cst_arr(np.diag(t['R']).real, a, c['sigma2'])[0])  # diag R = 1 (flat and rank1)
        ub = float(U.ub_score(f, J, cs))
        margin = ub - (c['MI'] - c['err_MI'])
        out.append(dict(n=c['n'], cov=c['cov'], rho=c['rho'], sigma2=c['sigma2'], f=f, J=J, cst=cs, UB=ub, MI=c['MI'], err_MI=c['err_MI'], margin=margin, d_fJ_vs_stored=d_fj,
                        ok=bool(margin >= -1e-12 and d_fj <= 1e-12)))
    return dict(passed=bool(len(out) == 27 and all(x['ok'] for x in out)), n_cases=len(out), n_ok=int(sum(x['ok'] for x in out)), min_margin=min(x['margin'] for x in out),
                max_d_fJ_vs_stored=worst_fj, cases=out,
                criterion='UB = J + n log2(1 + a / sigma2) - f >= MI - err_MI - 1e-12 in 27/27; f, J recomputed equal stored to 1e-12 (margin ~0 expected in the 3 cases N = 1, rho = 0)')


# ------------------------------------------------------------------------------------------------------------------- UB2
def gate_UB2(consts, refs):
    s2, rho, a = C.cond_arrays(U.CONDS)
    rows, worst_id, worst_f = [], 0., 0.
    worst_f_by_ref = {}
    for ref in refs:
        for L in (8, 32):
            for frame in range(3):
                delays, q, Fs = frame_objects(consts, ref, 'gate', L, frame)
                if ref.name == 'RAY':
                    f, J, _k = U.ray_f_and_j(consts, delays, q, Fs)
                else:
                    f, J, _side = C.f_and_j(consts, ref, L, delays, q)
                cs = U.cst(ref, L)
                tc = TapCov(ref, L, Fs)
                Up, Ux = consts.u(consts.ptil, delays), consts.u(consts.idaft(q), delays)
                Cp = tc.cs(Up)
                c = tc.c()  # c_n = sum_l R_l[n, n]
                for ci in range(len(U.CONDS)):
                    Cbar = rho[ci] * Cp + a[ci] * np.diag(c)
                    M = np.eye(N) + Cbar / s2[ci]
                    direct = logdet_pd(M)
                    mine = float(J[ci] + cs[ci])
                    rel = abs(direct - mine) / abs(direct)
                    Cs = tc.cs(math.sqrt(rho[ci]) * Up + math.sqrt(a[ci]) * Ux)
                    f_direct = logdet_pd(np.eye(N) + Cs / s2[ci])
                    rel_f = abs(f_direct - f[ci]) / abs(f_direct)
                    worst_id = max(worst_id, rel)
                    worst_f_by_ref[ref.name] = max(worst_f_by_ref.get(ref.name, 0.), rel_f)
                    if ref.name == 'RAY':
                        worst_f = max(worst_f, rel_f)
                    rows.append(dict(ref=ref.name, L=L, frame=frame, cond=list(U.CONDS[ci]), direct=direct, J_plus_cst=mine, rel_identity=rel, f_Kside=float(f[ci]), f_direct=f_direct, rel_f=rel_f))
    return dict(passed=bool(worst_id <= 1e-9 and worst_f <= 1e-9), max_rel_identity=worst_id, max_rel_f_RAY=worst_f, max_rel_f_by_ref=worst_f_by_ref, n_checks=len(rows), rows=rows,
                criterion='|direct N-side log2 det(I + Cbar/s2) - (J + Cst)| <= 1e-9 |direct| for all refs; RAY K-side f vs direct N-side relative 1e-9 (MODEL/PHYS f check reported only)')


# ------------------------------------------------------------------------------------------------------------------- UB3
def gate_UB3(consts, refs, n_draws=2000, ci=0):
    L, frame = 8, 0
    s2, rho, a = C.cond_arrays(U.CONDS)
    s2, rho, a = s2[ci], rho[ci], a[ci]
    out = []
    for ref in refs:
        delays, _q, Fs = frame_objects(consts, ref, 'gate', L, frame)
        tc = TapCov(ref, L, Fs)
        Up = consts.u(consts.ptil, delays)
        Cbar = rho * tc.cs(Up) + a * np.diag(tc.c())
        if ref.name == 'RAY':
            def draw_Cs(Ux):
                Us = math.sqrt(rho) * Up + math.sqrt(a) * Ux
                Bs = np.hstack([Us[:, l, None] * F for l, F in enumerate(Fs)])
                return Bs @ Bs.conj().T
        else:
            R0 = tc.shared

            def draw_Cs(Ux):
                Us = math.sqrt(rho) * Up + math.sqrt(a) * Ux
                return R0 * (Us @ Us.conj().T)
        rng = U.rng_for('gate', L, 9999, 'data')
        S1, S2f = np.zeros((N, N), complex), 0.
        for i in range(n_draws):
            bits = rng.integers(0, 2, size=(N, 2))
            q = ((2 * bits[:, 0] - 1) + 1j * (2 * bits[:, 1] - 1)) / math.sqrt(2.)
            Cs = draw_Cs(consts.u(consts.idaft(q), delays))
            S1 += Cs
            S2f += float(np.vdot(Cs, Cs).real)
        M = S1 / n_draws
        var_f = max(S2f / n_draws - float(np.vdot(M, M).real), 0.)
        se = math.sqrt(var_f / n_draws)
        err = float(np.linalg.norm(M - Cbar))
        out.append(dict(ref=ref.name, L=L, cond=list(U.CONDS[ci]), n_draws=n_draws, err_fro=err, se_fro=se, err_over_se=err / se, rel_err=err / float(np.linalg.norm(Cbar)), ok=bool(err <= 4. * se)))
    return dict(passed=bool(all(x['ok'] for x in out)), detail=out, criterion='||M - Cbar||_F <= 4 sqrt(mean ||C_s - M||_F^2 / 2000) (M = mean of C_s over 2000 QPSK draws)')


# ------------------------------------------------------------------------------------------------------------------- UB4
def gate_UB4():
    rows, k = [], np.arange(N)
    for L in (8, 32):
        for frame in range(3):
            counts, thetas, zs = U.ray_params(C.rng_for('locate', L, frame, 'rays'), L)
            a = np.empty((N, L), complex)
            for t in range(L):  # identical formula to C.draw_rays
                r = int(counts[t])
                a[:, t] = np.exp(2j * np.pi * np.outer(k, 2. * np.cos(thetas[t])) / N) @ (np.sqrt(1. / (L * r)) * zs[t])
            ref = C.draw_rays('locate', L, frame)
            eq = bool(np.array_equal(a, ref))
            Fs = U.ray_factors(thetas, counts, L)
            dev = max(float(np.max(np.abs(np.sum(np.abs(F) ** 2, axis=1) - 1. / L))) for F in Fs)
            dev_R = max(float(np.max(np.abs(np.real(np.diag(F @ F.conj().T)) - 1. / L))) for F in Fs)
            rows.append(dict(L=L, frame=frame, bitwise_equal=eq, max_diag_dev=max(dev, dev_R), ok=bool(eq and dev <= 1e-12 and dev_R <= 1e-12)))
    return dict(passed=bool(all(x['ok'] for x in rows)), detail=rows,
                criterion="ray_params(C.rng_for('locate', L, frame, 'rays'), L) + C.draw_rays' formula == C.draw_rays (np.array_equal); diag R_l = 1/L to 1e-12; frames 0..2, L in {8, 32}")


# --------------------------------------------------------------------------------------------------------------------- OP
def gate_OP():
    scratch = Path('/data/guoyikun/tmp') / f'ub_screen_op_{os.getpid()}'
    scratch.mkdir(parents=True, exist_ok=False)
    try:
        R.main(['--stage', 'timing', '--Ls', '8', '--frames', '1', '--refs', 'MODEL,PHYS,RAY', '--out', str(scratch)])
        need_cfg = {'stage', 'Ls', 'frames', 'refs', 'conds', 'with_9p5', 'seed_root', 'seed_domain', 'stage_id', 'code_md5', 'consts_md5', 'nshard', 'delta_endpoint'}
        detail = {}
        ok = True
        for name in ('config_shard000.json', 'results_shard000.json'):
            d = json.loads((scratch / name).read_text())
            has = bool('_argv' in d and '_config' in d and need_cfg <= set(d['_config']) and {'ub_screen_core.py', 'ub_screen_run.py'} <= set(d['_config']['code_md5']))
            detail[name] = dict(has_argv=bool('_argv' in d), has_config=bool('_config' in d), missing=sorted(need_cfg - set(d.get('_config', {}))), ok=has)
            ok &= has
        rows = [json.loads(x) for x in (scratch / 'rows_shard000.jsonl').read_text().splitlines()]
        row_ok = bool(len(rows) == 3 and all(set(r) >= {'stage', 'L', 'frame', 'ref', 'f', 'J', 'u', 'sec'} for r in rows) and any('rank' in r for r in rows if r['ref'] == 'RAY'))
        # u = J + Cst - f recomputed from the stored row
        cs_tab = {r.name: U.cst(r, 8) for r in (C.ModelRef(), C.PhysRef(), U.RayRef())}
        row_ok &= all(np.max(np.abs(np.array(r['u']) - (np.array(r['J']) + cs_tab[r['ref']] - np.array(r['f'])))) < 1e-9 for r in rows)
        return dict(passed=bool(ok and row_ok), detail=detail, rows_ok=bool(row_ok), criterion='runner config / results json carry _argv and _config (flags, seed domain, frames, Ls, code md5); rows carry stage, L, frame, ref, f, J, u, sec, rank')
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


# --------------------------------------------------------------------------------------------------------------- reporting
def md_report(res):
    g = res['gates']
    L = ['# Upper-bound screen: gates', '', f"Run {res['_config']['date']} on deinlab; spec `.trellis/tasks/10-08-doppler-cluster/research/ub-screen-20261015.md` (FROZEN 2026-10-15).", '',
         '| gate | result | decisive number |', '|---|---|---|']
    if 'UB1' in g and 'min_margin' in g['UB1']:
        u = g['UB1']
        L.append(f"| UB1 toy | {'PASS' if u['passed'] else 'FAIL'} | {u['n_ok']}/{u['n_cases']} cases; min (UB - (MI - err)) = {u['min_margin']:.3e}; max |f, J - stored| = {u['max_d_fJ_vs_stored']:.1e} |")
    if 'UB2' in g and 'max_rel_identity' in g['UB2']:
        u = g['UB2']
        L.append(f"| UB2 identity | {'PASS' if u['passed'] else 'FAIL'} | max relative |direct - (J + Cst)| = {u['max_rel_identity']:.2e} ({u['n_checks']} checks); RAY K-side f vs N-side: {u['max_rel_f_RAY']:.2e}; "
                 f"by ref {', '.join(f'{k}: {v:.1e}' for k, v in u['max_rel_f_by_ref'].items())} |")
    if 'UB3' in g and 'detail' in g['UB3']:
        u = g['UB3']
        L.append(f"| UB3 mean covariance | {'PASS' if u['passed'] else 'FAIL'} | ||M - Cbar||_F / SE: " + ', '.join(f"{d['ref']} {d['err_over_se']:.2f} (rel err {d['rel_err']:.1e})" for d in u['detail']) + ' (bar 4) |')
    if 'UB4' in g and 'detail' in g['UB4']:
        u = g['UB4']
        L.append(f"| UB4 RAY law | {'PASS' if u['passed'] else 'FAIL'} | {sum(d['bitwise_equal'] for d in u['detail'])}/{len(u['detail'])} bitwise equal; max |diag R_l - 1/L| = {max(d['max_diag_dev'] for d in u['detail']):.1e} |")
    if 'OP' in g and 'detail' in g['OP']:
        u = g['OP']
        L.append(f"| OP fingerprint | {'PASS' if u['passed'] else 'FAIL'} | config / results json carry _argv and _config: {all(d['ok'] for d in u['detail'].values())}; row fields ok: {u['rows_ok']} |")
    L += ['', f"**Overall: {'ALL PASS' if res['all_passed'] else 'FAIL'}**", '', '## Detail', '', '```json', json.dumps(g, indent=1, default=float)[:60000], '```']
    return '\n'.join(L) + '\n'


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument('--only', default='')
    ap.add_argument('--commit', default='unknown')
    args = ap.parse_args()
    GATE_OUT.mkdir(parents=True, exist_ok=True)
    only = [x for x in args.only.split(',') if x]
    consts = C.Consts()
    refs = [C.ModelRef(), C.PhysRef(), U.RayRef()]
    gates = {}
    for name, fn in (('UB1', gate_UB1), ('UB2', lambda: gate_UB2(consts, refs)), ('UB3', lambda: gate_UB3(consts, refs)), ('UB4', gate_UB4), ('OP', gate_OP)):
        if only and name not in only:
            continue
        t0 = time.perf_counter()
        try:
            gates[name] = fn()
        except Exception as error:
            gates[name] = dict(passed=False, error=repr(error), trace=traceback.format_exc()[-2000:])
        gates[name]['seconds'] = time.perf_counter() - t0
        print(name, 'PASS' if gates[name]['passed'] else 'FAIL', f"{gates[name]['seconds']:.1f}s", flush=True)
    cfg = dict(date=time.strftime('%Y-%m-%d'), commit=args.commit, only=only, seed_root=U.SEED_ROOT, seed_domain=U.SEED_DOMAIN, stage_ids=U.STAGE_ID, comp_ids=U.COMP, gate_frames=[0, 1, 2],
               gate_Ls=[8, 32], ub3_draws=2000, conds=[list(c) for c in U.CONDS], k_switch=U.K_SWITCH, consts_md5=md5_file(C.OUT / 'consts.json'),
               code_md5={n: md5_file(HERE / n) for n in ('ub_screen_core.py', 'ub_screen_run.py', 'ub_screen_gates.py', 'ib_screen_core.py', 'ib_screen_toy.py')})
    res = dict(_argv=sys.argv, _config=cfg, gates=gates, all_passed=bool(all(g['passed'] for g in gates.values())))
    suffix = '' if not only else '_' + '_'.join(only)
    (GATE_OUT / f'gates{suffix}.json').write_text(json.dumps(res, indent=1, default=float, allow_nan=False) + '\n')
    if not only:
        (GATE_OUT / 'GATES.md').write_text(md_report(res))
    print('ALL_PASSED' if res['all_passed'] else 'SOME_FAILED')


if __name__ == '__main__':
    main()
