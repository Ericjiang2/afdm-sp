#!/usr/bin/env python3
"""Idea-funnel local round 3, L2 check for card I-20261121-l14 (2026-11-22, runner l, claude-fable-5.2).
Equal-peak-power comparison of SP-AFDM and SP-SC-CP with perfect channel knowledge and the finite-length LDPC turbo loop.
Source: ideas/l2/l2_l09_coded.py (turbo imported; job pattern copied because that job has no transmit chain, no pilot and
its noise level comes from the frame, not from a peak-power budget) and ideas/l2/l2_l09_cluster.py (h_time and the 4-ray
same-delay cluster construction copied: importing that module runs its argv handling).  Transmit chain: l2_r3_peak_chain.py.
Pre-registered criteria: ideas/l2/PREDICTIONS_r3_batch4.md.
  python l2_r3_peak.py smoke|run|read --out out_r3b4
"""
import argparse, gzip, json, os, resource, sys, time
from multiprocessing import get_context
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import l2_l09_coded as l09  # noqa: E402
from l2_l09_coded import setup, SEED, scale_of, turbo  # noqa: E402
import l2_r3_peak_chain as ch  # noqa: E402

WORKERS = 12
CFG = dict(frames=[49000, 49120], scenario='U', rho_frame=100, rho=0.25, pd=0.5, thr_db=1.5, calib_frames=400,
           gamma_lo_db=5.0, gamma_step_db=0.25, gamma_points=25, rays=4, nu_max=2.0, zc_root=7)
ARMS = [('p1', 'sc', False), ('p1', 'afdm', False), ('cluster', 'sc', False), ('cluster', 'afdm', False), ('cluster', 'afdm', True)]
_CAL = {}


def h_time(n, c1, l, nu, g):                    # copied from l2_l09_cluster.py
    H = np.zeros((n, n), complex); idx = np.arange(n)
    for li, ni, gi in zip(l, nu, g):
        cp = np.where(idx < li, np.exp(2j * np.pi * c1 * (n * n + 2 * n * (idx - li))), 1.0)
        H[idx, (idx - li) % n] += gi * cp * np.exp(2j * np.pi * idx * ni / n)
    return H


def afdm_matrix(n, c1, c2):
    idx = np.arange(n); F = np.fft.fft(np.eye(n), axis=0) / np.sqrt(n)
    return np.exp(2j * np.pi * c2 * idx ** 2)[:, None] * F * np.exp(2j * np.pi * c1 * idx ** 2)[None, :]


def pilot(n):
    pp = CFG['pd'] * CFG['rho'] / (1 - CFG['rho']); k = np.arange(n)
    return np.sqrt(pp) * np.exp(-1j * np.pi * CFG['zc_root'] * k ** 2 / n)


def calibration(n, A):
    """Per-waveform constants from independent random QPSK blocks (not the evaluation frames)."""
    if not _CAL:
        rng = np.random.default_rng([SEED, 1414]); F = CFG['calib_frames']; a = np.sqrt(CFG['pd'] / 2); p = pilot(n)
        d = a * (rng.choice([-1, 1], (F, n)) + 1j * rng.choice([-1, 1], (F, n)))
        blocks = dict(sc=p[None, :] + d, afdm=(p[None, :] + d) @ A.conj())          # rows: A^H (p + d)
        for wf, t in blocks.items():
            c = ch.calibrate(t, CFG['thr_db']); p0 = float(np.mean(np.abs(t) ** 2))
            _CAL[wf] = dict(alpha=c['alpha'], sigma_e2=c['sigma_e2'] * p0, p_peak=c['p_peak'] * p0, sdr_db=c['sdr_db'],
                            papr999_db=float(10 * np.log10(c['p_peak'] / c['p_avg_tx'])), e_kurtosis=c['e_kurtosis'])
    return _CAL


def turbo_rec(C, H, y, s2, truth, recon):
    """l09's turbo with one addition: before each round after the first, rebuild the clipping distortion from the soft
    symbols and subtract its image.  recon = dict(alpha, sigma_e2, chpow, to_time, to_sym, p)."""
    from messages import moments
    ctx = C['ctx']; dec_fn = ctx.native.decoder_messages; gd = C['stage3'].e1.gd; n = H.shape[1]; pd = CFG['pd']; a = np.sqrt(pd / 2)
    prior = np.zeros(2 * n); err = None; used = 0; al = recon['alpha']; Hc = H / al
    for r in range(l09.CFG['rounds']):
        mu, v, _ = moments(np.clip(prior, -20, 20), pd); used = r + 1
        if r == 0:
            yy, s2r = y, s2 + recon['sigma_e2'] * recon['chpow']
        else:
            t_hat = recon['to_time'](recon['p'] + mu)
            e_hat = ch.matched(ch.icf(t_hat, CFG['thr_db'])) - al * t_hat
            yy = y - Hc @ recon['to_sym'](e_hat); s2r = s2 + recon['sigma_e2'] * recon['chpow'] * float(np.mean(v)) / pd
        Fm = np.linalg.solve((H * v[None, :]) @ H.conj().T + s2r * np.eye(n), H)
        s = np.real(np.sum(H.conj() * Fm, axis=0)); z = mu + (Fm.conj().T @ (yy - H @ mu)) / s; eta = np.maximum(1 / s - v, 1e-9)
        llr = np.concatenate([4 * a * z.real / eta, 4 * a * z.imag / eta])
        dec = dec_fn(ctx.code, np.clip(llr, -20, 20), maxiter=l09.CFG['dec_iters']); err = int(gd.score(ctx, dec['decoded'], truth))
        if bool(dec['decode_ok']):
            break
        prior = np.asarray(dec['raw_check_extrinsic'], float)
    return err, used


def job(frame, grid=None):
    C = setup(); stage3, ctx = C['stage3'], C['ctx']
    base = stage3.inputs(ctx, frame, CFG['scenario'], CFG['rho_frame'])
    raw, obs, truth = stage3.observed(ctx, base, CFG['rho_frame'], 500)
    Hd = np.asarray(raw['H'], complex); n = Hd.shape[0]; c1, c2 = float(ctx.system.c1), float(ctx.system.c2)
    A = afdm_matrix(n, c1, c2); cal = calibration(n, A); p = pilot(n)
    d = np.asarray(raw['data'], complex) / scale_of(raw, obs); w0 = np.asarray(raw['noise'], complex)
    l = np.asarray(truth['l_i'], int); nu = np.asarray(truth['k_real'], float); g = np.asarray(truth['g_i'], complex)
    Ht = {'p1': h_time(n, c1, l, nu, g)}
    gate = float(np.linalg.norm(A @ Ht['p1'] @ A.conj().T - Hd) / np.linalg.norm(Hd))
    rng = np.random.default_rng([SEED, frame, 91]); l2, nu2, g2 = [], [], []          # 4-ray same-delay cluster, as in l2_l09_cluster.py
    for li, gi in zip(l, g):
        ph = rng.uniform(0, 2 * np.pi, CFG['rays']); th = rng.uniform(0, 2 * np.pi, CFG['rays'])
        l2 += [li] * CFG['rays']; nu2 += list(CFG['nu_max'] * np.cos(th)); g2 += list(abs(gi) / np.sqrt(CFG['rays']) * np.exp(1j * ph))
    Ht['cluster'] = h_time(n, c1, l2, nu2, g2)
    gam = CFG['gamma_lo_db'] + CFG['gamma_step_db'] * np.arange(CFG['gamma_points']) if grid is None else np.asarray(grid, float)
    rec = dict(frame=frame, gate_h=gate, d_power=float(np.mean(np.abs(d) ** 2)), w_power=float(np.mean(np.abs(w0) ** 2)), thr_idx={}, runs={})
    for chan, wf, rc in ARMS:
        al, se2, ppk = cal[wf]['alpha'], cal[wf]['sigma_e2'], cal[wf]['p_peak']
        if wf == 'sc':
            t = p + d; to_time = lambda x: x; to_sym = lambda x: x; Hs = Ht[chan]
        else:
            t = A.conj().T @ (p + d); to_time = lambda x: A.conj().T @ x; to_sym = lambda x: A @ x; Hs = A @ Ht[chan] @ A.conj().T
        r = ch.matched(ch.icf(t, CFG['thr_db']))
        x_clean = to_sym(Ht[chan] @ r) - al * (Hs @ p)                 # receiver knows the channel, alpha and the pilot
        chpow = float(np.linalg.norm(Ht[chan]) ** 2 / n); H_eff = al * Hs
        recon = dict(alpha=al, sigma_e2=se2, chpow=chpow, to_time=to_time, to_sym=to_sym, p=p)
        def ok(i):
            s2 = ppk / 10 ** (gam[i] / 10); y = x_clean + np.sqrt(s2) * to_sym(w0)
            e, _ = (turbo_rec(C, H_eff, y, s2, truth, recon) if rc else turbo(C, H_eff, y, s2 + se2 * chpow, truth))
            return e == 0
        lo, hi, nrun = -1, len(gam), 0                                 # bisection: smallest grid index that decodes (monotone assumed)
        while hi - lo > 1:
            mid = (lo + hi) // 2; nrun += 1
            if ok(mid): hi = mid
            else: lo = mid
        key = f'{chan}|{wf}|{"rec" if rc else "plain"}'; rec['thr_idx'][key] = hi; rec['runs'][key] = nrun
    return [rec]


def run(out):
    out.mkdir(parents=True, exist_ok=True); path = out / 'peak_rows.jsonl'
    if path.exists() or Path(str(path) + '.gz').exists():
        raise FileExistsError(path)
    t0 = time.time(); nrow = 0
    with get_context('spawn').Pool(WORKERS) as pool, open(path, 'x') as fh:
        for rows in pool.imap_unordered(job, list(range(*CFG['frames']))):
            for r in rows:
                print(json.dumps(r), file=fh); nrow += 1
    chd = resource.getrusage(resource.RUSAGE_CHILDREN)
    (out / 'peak_run.json').write_text(json.dumps(dict(_argv=sys.argv, _config=dict(CFG, seed=SEED, workers=WORKERS, arms=ARMS, turbo=l09.CFG),
        rows=nrow, core_hours=(chd.ru_utime + chd.ru_stime) / 3600, wall_seconds=time.time() - t0), indent=1))
    os.system(f'gzip -n {path}'); print('rows', nrow, 'core-hours', round((chd.ru_utime + chd.ru_stime) / 3600, 3))


def read(out):
    rows = sorted([json.loads(x) for x in gzip.open(out / 'peak_rows.jsonl.gz', 'rt')], key=lambda r: r['frame'])
    n = len(rows); rng = np.random.default_rng(SEED + 4); step = CFG['gamma_step_db']; npt = CFG['gamma_points']
    thr = {k: np.array([r['thr_idx'][k] for r in rows], float) for k in rows[0]['thr_idx']}
    db = {k: CFG['gamma_lo_db'] + step * v for k, v in thr.items()}                  # index npt (never decoded) maps to top + step
    def boot(fn):
        pt = fn(np.arange(n)); bs = [fn(rng.integers(0, n, n)) for _ in range(4000)]
        return dict(point=float(pt), ci95=[float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))])
    def cross(k, fer, ii):                                                          # gamma where the empirical FER curve crosses fer
        v = np.sort(db[k][ii]); return float(np.quantile(v, 1 - fer))
    pairs = dict(p1_afdm_minus_sc=('p1|afdm|plain', 'p1|sc|plain'), cluster_afdm_minus_sc=('cluster|afdm|plain', 'cluster|sc|plain'),
                 cluster_afdmrec_minus_sc=('cluster|afdm|rec', 'cluster|sc|plain'), cluster_afdmrec_minus_afdm=('cluster|afdm|rec', 'cluster|afdm|plain'),
                 sc_cluster_minus_p1=('cluster|sc|plain', 'p1|sc|plain'), afdm_cluster_minus_p1=('cluster|afdm|plain', 'p1|afdm|plain'))
    res = dict(frames=n, gate_h_max=max(r['gate_h'] for r in rows), d_power=float(np.mean([r['d_power'] for r in rows])),
               w_power=float(np.mean([r['w_power'] for r in rows])),
               censored={k: dict(below=int((v == 0).sum()), above=int((v == npt).sum())) for k, v in thr.items()},
               mean_runs={k: float(np.mean([r['runs'][k] for r in rows])) for k in thr},
               median_threshold_db={k: float(np.median(v)) for k, v in db.items()},
               fer_cross_db={k: {f'{int(f * 100)}%': cross(k, f, np.arange(n)) for f in (0.5, 0.1)} for k in db},
               paired_mean_shift_db={name: boot(lambda ii, a=a, b=b: (db[a][ii] - db[b][ii]).mean()) for name, (a, b) in pairs.items()},
               shift_at_fer10_db={name: boot(lambda ii, a=a, b=b: cross(a, 0.1, ii) - cross(b, 0.1, ii)) for name, (a, b) in pairs.items()})
    i1 = res['paired_mean_shift_db']['p1_afdm_minus_sc']; i2 = res['paired_mean_shift_db']['cluster_afdmrec_minus_sc']
    res['criterion_i_sc_ahead_on_p1_by_0p8'] = bool(i1['point'] >= 0.8)
    res['criterion_ii_afdm_rec_within_0p5_on_cluster'] = bool(i2['point'] <= 0.5)
    (out / 'peak_summary.json').write_text(json.dumps(res, indent=1)); print(json.dumps(res, indent=1))


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('mode', choices=('smoke', 'run', 'read')); ap.add_argument('--out', default='out_r3b4'); a = ap.parse_args()
    o = HERE / a.out
    if a.mode == 'smoke':
        t0 = time.process_time(); r = job(49000, grid=np.arange(2.0, 16.01, 1.0))[0]; t = time.process_time() - t0
        g = np.arange(2.0, 16.01, 1.0)
        print(json.dumps(dict(cal={k: {kk: (abs(vv) if isinstance(vv, complex) else vv) for kk, vv in v.items()} for k, v in _CAL.items()},
                              gate_h=r['gate_h'], d_power=r['d_power'], w_power=r['w_power'],
                              first_ok_gamma_db={k: (float(g[i]) if i < len(g) else None) for k, i in r['thr_idx'].items()}, runs=r['runs'], cpu=t), indent=1))
    else:
        dict(run=run, read=read)[a.mode](o)
