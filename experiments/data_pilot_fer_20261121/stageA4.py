"""Stage A4 (STAGEA4_PROTOCOL.md): round-0 Doppler Cramer-Rao bounds given the true delays.

Model (raw units, exact to 1e-12 against raw['noiseless']): y = F T F^H (p + d) + w, F = DAFT (unitary),
T = sum_i g_i diag(c_i) P_{l_i}, c_i[k] = cp_i[k] exp(2j pi k nu_i / n), (P_l x)[k] = x[(k - l) % n].
Unknowns theta = (nu_1..nu_P, Re g, Im g); delays known.  Bounds on nu (nuisance gains included):
  pilot_white  data treated as white noise:            2 Re(mu_i^H mu_j) / (sigma2 + v_d tr(TT^H)/n), mu = T p_t
  pilot        data as interference with exact C:      2 Re(mu_i^H C^-1 mu_j),  C = v_d T T^H + sigma2 I
  semiblind    Gaussian data, Slepian-Bangs:           pilot + tr(C^-1 C_i C^-1 C_j),  C_k = v_d (T_k T^H + T T_k^H)
  known        all data known:                          2 Re(J^H J) / sigma2, J = d(T (p_t + d_t)) / d theta
Metric (stage A3's): sum |g_i|^2 min(sqrt(2/pi) sqrt(CRB_i), CAP) / sum |g_i|^2.

  python stageA4.py gate --out out/stageA4_gate.json
  python stageA4.py run  --out out/stageA4
  python stageA4.py read --out out/stageA4
"""
import argparse, gzip, json, os, resource, sys, time
from multiprocessing import get_context
from pathlib import Path
import numpy as np

import stageA
from stageA import SCENARIOS, setup
from physical import daft, regressors, Channel

FRAMES = range(41000, 41100)
RHOS = (100, 150, 200)
SNRS = (300, 400, 500)
BOUNDS = ('pilot_white', 'pilot', 'semiblind', 'known')
CAP, TARGET, LOOSE, DECIDE_SNR, DECIDE_RHOS = 0.375, 0.04, 0.08, 400, (100, 150)
WORKERS, BOOT, SEED = 32, 2000, 20261121


def model(truth, n, c1):
    """Dense T and, per parameter, the single nonzero per row of T_k: (cols, vals)."""
    k = np.arange(n); l = np.asarray(truth['l_i'], int); nu = np.asarray(truth['k_real'], float)
    g = np.asarray(truth['g_i'], complex); T = np.zeros((n, n), complex); parts = [[], [], []]
    for li, ni, gi in zip(l, nu, g):
        cols = (k - li) % n
        c = np.where(k < li, np.exp(2j * np.pi * c1 * (n * n + 2 * n * (k - li))), 1.) * np.exp(2j * np.pi * k * ni / n)
        T[k, cols] += gi * c
        parts[0].append((cols, gi * c * 2j * np.pi * k / n)); parts[1].append((cols, c)); parts[2].append((cols, 1j * c))
    return T, parts[0] + parts[1] + parts[2]


def dense(cols, vals, n):
    M = np.zeros((n, n), complex); M[np.arange(n), cols] = vals
    return M


def prepare(truth, n, c1):
    """Everything that depends on the channel only (not on rho, SNR, pilot or data)."""
    T, ops = model(truth, n, c1)
    lam, U = np.linalg.eigh(T @ T.conj().T)
    A = T.conj().T @ U
    X = np.empty((len(ops), n * n), complex)
    for j, (cols, vals) in enumerate(ops):
        B = np.zeros((n, n), complex); B[cols] = vals.conj()[:, None] * U          # B = T_k^H U
        D = B.conj().T @ A; X[j] = (D + D.conj().T).ravel()                         # U^H (T_k T^H + T T_k^H) U
    return dict(T=T, ops=ops, lam=np.maximum(lam, 0.), U=U, X=X, trTT=float(np.real(np.trace(T @ T.conj().T))))


def fims(P, p, d, sigma2, n, c1, c2):
    """Fisher matrices of the four bounds for one (rho, SNR); p, d in raw DAFT units."""
    ops = P['ops']; pt = daft(p, c1, c2, True); st = daft(p + d, c1, c2, True); vd = float(np.mean(np.abs(d) ** 2))
    Jp = np.stack([v * pt[c] for c, v in ops], 1); Js = np.stack([v * st[c] for c, v in ops], 1)
    w = 1. / (vd * P['lam'] + sigma2); M = P['U'].conj().T @ Jp
    pilot = 2 * np.real(M.conj().T @ (w[:, None] * M))
    q = vd * w; X = P['X']
    cov = np.real((X * np.outer(q, q).ravel()) @ X.conj().T)
    return dict(pilot_white=2 * np.real(Jp.conj().T @ Jp) / (sigma2 + vd * P['trTT'] / n), pilot=pilot,
                semiblind=pilot + cov, known=2 * np.real(Js.conj().T @ Js) / sigma2)


def crb_nu(F, n_paths):
    ev = np.linalg.eigvalsh(F)
    if ev.min() <= 1e-12 * ev.max():
        return np.full(n_paths, np.inf)
    return np.diag(np.linalg.inv(F))[:n_paths].real


def metric(crb, g):
    pw = np.abs(np.asarray(g)) ** 2
    return float(np.sum(pw * np.minimum(np.sqrt(2 / np.pi) * np.sqrt(np.maximum(crb, 0)), CAP)) / pw.sum())


def keys_for(C, frame, s_):
    st, ctx = C['stage3'], C['ctx']; ref = None
    for rho in RHOS:
        base = st.inputs(ctx, frame, s_, rho)
        for snr in SNRS:
            raw, obs, truth = st.observed(ctx, base, rho, snr)
            t = (tuple(truth['l_i']), tuple(truth['k_real']), tuple(truth['g_i']))
            if ref is None:
                ref = t
            elif t != ref:
                raise ValueError(f'channel differs across rho/SNR at {frame} {s_}')
            yield rho, snr, raw, truth


def draw_job(job):
    frame, s_ = job
    C = setup(); c1, c2 = C['ctx'].system.c1, C['ctx'].system.c2
    rows, P = [], None
    for rho, snr, raw, truth in keys_for(C, frame, s_):
        n = len(raw['y'])
        if P is None:
            P = prepare(truth, n, c1)
        F = fims(P, np.asarray(raw['pilot']), np.asarray(raw['data']), float(raw['sigma2']), n, c1, c2)
        g = np.asarray(truth['g_i']); crbs = {b: crb_nu(F[b], len(g)) for b in BOUNDS}
        rows.append(dict(frame=frame, scenario=s_, rho=rho, snr=snr, power=(np.abs(g) ** 2).tolist(),
                         crb={b: v.tolist() for b, v in crbs.items()}, metric={b: metric(v, g) for b, v in crbs.items()}))
    return rows


def gate(out):
    """G1 reconstruction; G2 derivatives; G3 known-data ML Monte Carlo vs CRB; G4 fast trace term vs dense."""
    from scipy.optimize import least_squares
    C = setup(); st, ctx = C['stage3'], C['ctx']; c1, c2 = ctx.system.c1, ctx.system.c2
    res = dict(G1=[], G2=[], G3=None, G4=None)
    for s_, rho, snr, frame in (('U', 100, 400, 41000), ('G', 150, 300, 41001), ('U', 200, 500, 41002), ('G', 100, 400, 41003)):
        raw, obs, truth = st.observed(ctx, st.inputs(ctx, frame, s_, rho), rho, snr)
        p, d, y0 = (np.asarray(raw[k]) for k in ('pilot', 'data', 'noiseless')); n = len(y0)
        T, ops = model(truth, n, c1)
        rec = daft(T @ daft(p + d, c1, c2, True), c1, c2)
        res['G1'].append(float(np.linalg.norm(rec - y0) / np.linalg.norm(y0)))
        l, nu, g = (np.asarray(truth[k]) for k in ('l_i', 'k_real', 'g_i')); errs = []
        for i in range(len(l)):
            h = 1e-5; tp = dict(truth, k_real=nu + h * (np.arange(len(l)) == i)); tm = dict(truth, k_real=nu - h * (np.arange(len(l)) == i))
            fd = (model(tp, n, c1)[0] - model(tm, n, c1)[0]) / (2 * h); an = dense(*ops[i], n)
            errs.append(float(np.linalg.norm(fd - an) / np.linalg.norm(an)))
            ch = Channel(n, c1, c2, l, nu, g).regressors(p + d, derivative=True)[:, i] * g[i]
            mine = daft(an @ daft(p + d, c1, c2, True), c1, c2)
            errs.append(float(np.linalg.norm(ch - mine) / np.linalg.norm(mine)))
        res['G2'].append(max(errs))
    # G3: known-data ML at 20 dB from the true start, 300 noise draws
    raw, obs, truth = st.observed(ctx, st.inputs(ctx, 41000, 'U', 100), 100, 2000)
    p, d, y0 = (np.asarray(raw[k]) for k in ('pilot', 'data', 'noiseless')); n = len(y0); s2 = float(raw['sigma2'])
    l, nu, g = (np.asarray(truth[k]) for k in ('l_i', 'k_real', 'g_i')); x = p + d
    crb = crb_nu(fims(prepare(truth, n, c1), p, d, s2, n, c1, c2)['known'], len(l))
    rng = np.random.default_rng(SEED); est = []
    for _ in range(300):
        y = y0 + np.sqrt(s2 / 2) * (rng.standard_normal(n) + 1j * rng.standard_normal(n))

        def resid(v):
            A = regressors(x, l, v, c1, c2); r = y - A @ np.linalg.lstsq(A, y, rcond=None)[0]
            return np.concatenate([r.real, r.imag])
        est.append(least_squares(resid, nu.copy(), x_scale=np.sqrt(crb), xtol=1e-12, ftol=1e-12).x)
    ratio = np.var(np.array(est) - nu, axis=0) / crb
    res['G3'] = dict(crb_std=np.sqrt(crb).tolist(), ratio=ratio.tolist(), median=float(np.median(ratio)))
    # G4: eigen-basis trace term against a dense computation for a few entries
    raw, obs, truth = st.observed(ctx, st.inputs(ctx, 41001, 'G', 100), 100, 400)
    p, d = np.asarray(raw['pilot']), np.asarray(raw['data']); n = len(p); s2 = float(raw['sigma2']); vd = float(np.mean(np.abs(d) ** 2))
    P = prepare(truth, n, c1); F = fims(P, p, d, s2, n, c1, c2); T = P['T']
    Ci = np.linalg.inv(vd * T @ T.conj().T + s2 * np.eye(n)); errs = []
    for i, j in ((0, 0), (0, 3), (2, 9), (5, 20), (12, 17)):
        Di, Dj = (vd * (dense(*P['ops'][k], n) @ T.conj().T + T @ dense(*P['ops'][k], n).conj().T) for k in (i, j))
        ref = float(np.real(np.trace(Ci @ Di @ Ci @ Dj)))
        errs.append(abs((F['semiblind'] - F['pilot'])[i, j] - ref) / abs(ref))
    res['G4'] = float(max(errs))
    t = time.process_time(); draw_job((41099, 'G')); per_draw = time.process_time() - t
    out_ = dict(G1=bool(max(res['G1']) < 1e-10), G2=bool(max(res['G2']) < 1e-5), G3=bool(0.8 <= res['G3']['median'] <= 1.25),
                G4=bool(res['G4'] < 1e-8),
                detail=res, cpu_seconds_per_draw=per_draw,
                projected_core_hours=per_draw * len(FRAMES) * len(SCENARIOS) / 3600 * 1.3)
    Path(out).write_text(json.dumps(out_, indent=1)); print(json.dumps(out_, indent=1))


def run(out):
    out = Path(out); out.mkdir(parents=True, exist_ok=False)
    jobs = [(f, s_) for f in FRAMES for s_ in SCENARIOS]
    (out / 'RUN_CONFIG.json').write_text(json.dumps(dict(_argv=sys.argv, frames=[FRAMES.start, FRAMES.stop - 1],
        scenarios=SCENARIOS, rhos=RHOS, snrs=SNRS, bounds=BOUNDS, cap=CAP, workers=WORKERS), indent=1))
    t0 = time.time(); n = 0
    with gzip.open(out / 'rows.jsonl.gz', 'wt') as fh, get_context('spawn').Pool(WORKERS) as pool:
        for rows in pool.imap_unordered(draw_job, jobs):
            for r in rows:
                print(json.dumps(r), file=fh); n += 1
    ch = resource.getrusage(resource.RUSAGE_CHILDREN); hours = (ch.ru_utime + ch.ru_stime) / 3600
    want = len(jobs) * len(RHOS) * len(SNRS)
    (out / 'STATUS').write_text((f'DONE {n} {hours:.4f}' if n == want else f'STOPPED {n}/{want} {hours:.4f}') + '\n')
    print((out / 'STATUS').read_text(), 'wall', round(time.time() - t0))


def read(out):
    out = Path(out); status = (out / 'STATUS').read_text().split()
    if status[0] != 'DONE':
        raise ValueError(status)
    rows = [json.loads(x) for x in gzip.open(out / 'rows.jsonl.gz', 'rt')]
    draws = sorted({(r['frame'], r['scenario']) for r in rows}); di = {k: i for i, k in enumerate(draws)}
    V = np.full((len(BOUNDS), len(RHOS), len(SNRS), len(draws)), np.nan)
    for r in rows:
        for b, bound in enumerate(BOUNDS):
            V[b, RHOS.index(r['rho']), SNRS.index(r['snr']), di[(r['frame'], r['scenario'])]] = r['metric'][bound]
    if np.isnan(V).any():
        raise ValueError('incomplete grid')
    rng = np.random.default_rng(SEED)
    idx = rng.integers(0, len(draws), (BOOT, len(draws)))
    table = {}
    for b, bound in enumerate(BOUNDS):
        table[bound] = {}
        for i, rho in enumerate(RHOS):
            for j, snr in enumerate(SNRS):
                v = V[b, i, j]; boots = v[idx].mean(axis=1)
                table[bound][f'{rho}_{snr}'] = dict(mean=float(v.mean()), median=float(np.median(v)),
                                                    ci=[float(x) for x in np.percentile(boots, [2.5, 97.5])])
    j = SNRS.index(DECIDE_SNR); label, why = 'CLOSED', 'known'
    for bound, name in (('pilot', 'PILOT-ENOUGH'), ('semiblind', 'SB-REACHABLE'), ('known', 'ALPHABET-ONLY')):
        best = min(DECIDE_RHOS, key=lambda r: table[bound][f'{r}_{DECIDE_SNR}']['mean'])
        if table[bound][f'{best}_{DECIDE_SNR}']['mean'] <= TARGET:
            label, why = name, bound
            break
    best = min(DECIDE_RHOS, key=lambda r: table[why][f'{r}_{DECIDE_SNR}']['mean']); lo, hi = table[why][f'{best}_{DECIDE_SNR}']['ci']
    verdict = label + (' (borderline)' if lo <= TARGET <= hi else '')
    a3 = json.loads((out.parent / 'stageA3' / 'results.json').read_text())['r0_doppler_err_snr4_5']['delay']
    eff = {str(r): dict(actual_pilot_r0_err_snr4_5=a3[str(r)],
                        pilot_white_bound_snr4_5=float(np.mean([table['pilot_white'][f'{r}_{s}']['mean'] for s in (400, 500)])))
           for r in RHOS}
    res = dict(_argv=sys.argv, protocol='STAGEA4_PROTOCOL.md', table=table, verdict=verdict, deciding_bound=why,
               deciding_rho=best, target=TARGET, loose=LOOSE, efficiency=eff, status=status)
    (out / 'results.json').write_text(json.dumps(res, indent=1)); print(json.dumps(res, indent=1))


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('mode', choices=('gate', 'run', 'read')); ap.add_argument('--out', required=True)
    a = ap.parse_args()
    dict(gate=gate, run=run, read=read)[a.mode](a.out)
