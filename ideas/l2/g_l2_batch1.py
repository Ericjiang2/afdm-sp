#!/usr/bin/env python3
"""Runner g L2 Batch 1 driver (2026-11-22, gemini-4-carbon) for cards:
  g03  I-20261122-g03: 1-bit receiver strong direct-path zero-crossing duality & blind Probit score
  g01  I-20261122-g01: short-CP SP-OFDM ISAC cross-block pilot ghost vs block phase coding vs continuous template
  g05  I-20261122-g05: SIMO (M=2) banded Woodbury trace-corrected EM vs c16 pilot VarPro & equal-budget short TDM

Pre-registered criteria & forecasts: ideas/l2/PREDICTIONS_g_batch1.md
No frozen receiver source files are modified.
Usage:
  python g_l2_batch1.py smoke|g03|g01|g05|all|read --out out_g1
"""
import argparse, gzip, json, os, resource, sys, time
from multiprocessing import get_context
from pathlib import Path
import numpy as np
from scipy.linalg import cho_factor, cho_solve
from scipy.optimize import minimize_scalar
from scipy.special import erfcx, ndtr

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from l2_batch3 import setup, scale_of  # noqa: E402

SEED = 20261122
WORKERS = 12

CFG = dict(
    g03=dict(
        calib_seeds=[10000, 10400],
        null_check_seeds=[10400, 10600],
        eval_seeds=[20000, 20300],
        cnrs_db=[15.0, 20.0, 25.0, 30.0, 35.0],
        wsrs_db=[-18.0, -22.0, -26.0, -30.0, -34.0],
        n4096_cnr=30.0,
        n4096_wsrs_db=[-26.0, -30.0, -34.0, -38.0],
        ell_range=[4, 65],
        nu_grid_step=0.25,
        nu_max=3.0,
        pilot_syms_sb=41,
        pfa=0.01,
    ),
    g01=dict(
        calib_seeds=[30000, 30500],
        eval_seeds=[31000, 31400],
        fs=16000.0,
        M=16,
        K=64,
        C=16,
        snr_strong_db=4.5,
        rhos=[0.20, 0.30, 0.40],
        delay_modes=['d_clean', 'd_gen'],
        f_bands=[31.25, 45.0],
        wsrs_db=[-14.0, -16.0, -18.0, -20.0],
        pfa=0.01,
    ),
    g05=dict(
        smoke_frame=48999,
        frames=[49000, 49150],
        scenario='G',
        partA_snr=400,
        partA_rhos=[30, 50, 100],
        partA_corrs=[0.0, 0.5, 0.85],
        partA_totmatch=dict(rho=50, snr=100, corr=0.0),
        partB_rho=50,
        partB_high_rho=250,
        partB_corr=0.0,
        partB_snrs=[200, 300, 400],
        em_iters=5,
        turbo_rounds=10,
        dec_iters=50,
    ),
)


# ===========================================================================
# Shared transforms & numerical primitives
# ===========================================================================
def daft(x, c1, c2, inverse=False):
    x = np.asarray(x, complex)
    n = x.shape[0]
    k = np.arange(n)
    shape = (n,) + (1,) * (x.ndim - 1)
    a = np.exp(2j * np.pi * c1 * k * k).reshape(shape)
    b = np.exp(2j * np.pi * c2 * k * k).reshape(shape)
    if inverse:
        return a.conj() * np.fft.ifft(b.conj() * x, axis=0) * np.sqrt(n)
    return b * np.fft.fft(a * x, axis=0) / np.sqrt(n)


def dkernel(t, n):
    t = (np.asarray(t, dtype=float) + n / 2.0) % n - n / 2.0
    return np.exp(1j * np.pi * (n - 1) * t / n) * np.sinc(t) / np.sinc(t / n)


def inv_mills(z):
    """Exact overflow/underflow-safe phi(z) / Phi(z) on (-inf, +inf)."""
    z = np.asarray(z, dtype=float)
    out = np.empty_like(z)
    pos = z >= 0.0
    if np.any(pos):
        zp = z[pos]
        out[pos] = (np.exp(-0.5 * zp * zp) / np.sqrt(2.0 * np.pi)) / ndtr(zp)
    if np.any(~pos):
        zn = z[~pos]
        out[~pos] = np.sqrt(2.0 / np.pi) / erfcx(-zn / np.sqrt(2.0))
    return out


# ===========================================================================
# 1. Card g03: 1-bit strong direct-path PAPR duality & blind Probit score
# ===========================================================================
def blind_newton_eta0(r, x, max_iter=12):
    """Estimate eta_0 = g_0 / sigma_0 in C from 1-bit r = sign(Re y) + j sign(Im y) and known x."""
    sr = np.real(r)
    si = np.imag(r)
    xr = np.real(x)
    xi = np.imag(x)
    s = np.concatenate([sr, si])
    X = np.column_stack([np.concatenate([xr, xi]), np.concatenate([-xi, xr])])
    ang0 = np.angle(np.vdot(x, r))
    theta = np.array([4.0 * np.cos(ang0), 4.0 * np.sin(ang0)], dtype=float)
    for _ in range(max_iter):
        u = X @ theta
        su = s * u
        lam = inv_mills(su)
        grad = X.T @ (s * lam) - 1e-5 * theta
        w = np.maximum(lam * (lam + su), 0.0)
        H = -(X.T * w[None, :]) @ X - 1e-5 * np.eye(2)
        step = np.linalg.solve(-H, grad)
        nrm_step = np.linalg.norm(step)
        if nrm_step > 15.0:
            step *= 15.0 / nrm_step
        theta = theta + step
        nrm = np.linalg.norm(theta)
        if nrm > 120.0:
            theta *= 120.0 / nrm
            break
        if nrm_step < 1e-4:
            break
    return complex(theta[0], theta[1])


def g03_score_vec(r, x, mode):
    if mode == 'bussgang':
        alpha = np.vdot(x, r) / max(np.vdot(x, x).real, 1e-12)
        return r - alpha * x
    eta0 = blind_newton_eta0(r, x)
    u = eta0 * x
    sr, si = np.real(r), np.imag(r)
    ur, ui = np.real(u), np.imag(u)
    if mode == 'cmean':
        return (sr - (2.0 * ndtr(ur) - 1.0)) + 1j * (si - (2.0 * ndtr(ui) - 1.0))
    # mode == 'probit'
    return sr * inv_mills(sr * ur) + 1j * si * inv_mills(si * ui)


def g03_map_search(score_v, x, ell_lo, ell_hi, nu_grid):
    """Self-normalized 2D delay-Doppler map max and argmax via batched FFT cross-correlation."""
    n = len(x)
    denom = float(np.vdot(score_v, score_v).real)
    if denom < 1e-24:
        return 0.0, ell_lo, 0.0
    idx = np.arange(n)
    Xf_conj = np.conj(np.fft.fft(x))
    mod = score_v[None, :] * np.exp(-2j * np.pi * np.outer(nu_grid, idx) / n)
    corr = np.fft.ifft(np.fft.fft(mod, axis=1) * Xf_conj[None, :], axis=1)
    sub = (np.abs(corr[:, ell_lo:ell_hi]) ** 2) * n / denom
    flat_idx = int(np.argmax(sub))
    iu, il = divmod(flat_idx, ell_hi - ell_lo)
    return float(sub[iu, il]), int(ell_lo + il), float(nu_grid[iu])


def frac_delay_doppler(x, tau, nu):
    n = len(x)
    k = np.fft.fftfreq(n, 1.0 / n)
    phase = np.exp(-2j * np.pi * k * tau / n)
    if n % 2 == 0:
        phase[n // 2] = np.cos(np.pi * tau)
    delayed = np.fft.ifft(np.fft.fft(x) * phase)
    return delayed * np.exp(2j * np.pi * nu * np.arange(n) / n)


def g03_waveforms(C, seed, n):
    rng = np.random.default_rng([SEED, 3, seed, n])
    ctx = C['ctx']
    c1, c2 = float(ctx.system.c1) * (1024.0 / n), float(ctx.system.c2)
    if n == 1024:
        raw, _, _ = C['stage3'].observed(ctx, C['stage3'].inputs(ctx, 40000 + (seed % 5000), 'U', 100), 100, 400)
        b = np.asarray(raw['coded']).astype(int)
    else:
        b = rng.integers(0, 2, size=2 * n)
    s_qpsk = ((1 - 2 * b[:n]) + 1j * (1 - 2 * b[n:])) / np.sqrt(2.0)
    psi = rng.uniform(0.0, 2.0 * np.pi, size=n)
    x_sc_qpsk = s_qpsk.copy()
    x_sc_cphase = np.exp(1j * psi) * s_qpsk
    x_afdm = daft(s_qpsk, c1, c2, inverse=True)
    return dict(b=b, s_qpsk=s_qpsk, c1=c1, c2=c2,
                sc_qpsk=x_sc_qpsk, sc_cphase=x_sc_cphase, afdm=x_afdm)


def g03_semiblind_reconstruct(C, r, wf, npilot):
    ctx = C['ctx']
    c1, c2 = wf['c1'], wf['c2']
    s_true = wf['s_qpsk']
    r_d = daft(r, c1, c2, inverse=False)
    sp = s_true[:npilot]
    rp = r_d[:npilot]
    alpha = np.vdot(sp, rp) / np.vdot(sp, sp)
    if abs(alpha) < 1e-4:
        return wf['afdm'] * 0.0, False
    eta = max(float(np.mean(np.abs(rp - alpha * sp) ** 2)) / (abs(alpha) ** 2), 0.15)
    z = r_d / alpha
    a = 1.0 / np.sqrt(2.0)
    llr = np.concatenate([4.0 * a * z.real / eta, 4.0 * a * z.imag / eta])
    b_true = wf['b']
    n = len(s_true)
    llr[:npilot] = (1 - 2 * b_true[:npilot]) * 20.0
    llr[n:n + npilot] = (1 - 2 * b_true[n:n + npilot]) * 20.0
    dec = ctx.native.decoder_messages(ctx.code, np.clip(llr, -20.0, 20.0), maxiter=50)
    bh = np.asarray(dec['decoded'], int)
    sh = ((1 - 2 * bh[:n]) + 1j * (1 - 2 * bh[n:])) / np.sqrt(2.0)
    sh[:npilot] = sp
    dec_ok = bool(np.array_equal(bh, b_true))
    return daft(sh, c1, c2, inverse=True), dec_ok


def g03_null_worker(args):
    seed, n, cnrs_db = args
    C = setup()
    cfg = CFG['g03']
    nu_grid = np.arange(-cfg['nu_max'], cfg['nu_max'] + 1e-9, cfg['nu_grid_step'])
    ell_lo, ell_hi = cfg['ell_range']
    wf = g03_waveforms(C, seed, n)
    rng = np.random.default_rng([SEED, 30, seed, n])
    phi0 = rng.uniform(0.0, 2.0 * np.pi)
    g0 = np.exp(1j * phi0)
    w0 = (rng.standard_normal(n) + 1j * rng.standard_normal(n)) / np.sqrt(2.0)
    arms = ('sc_qpsk_probit', 'sc_cphase_probit', 'afdm_bussgang', 'afdm_cmean', 'afdm_probit') + (
        ('afdm_semiblind_probit',) if n == 1024 else ())
    out = {}
    for cnr in cnrs_db:
        sig = 10.0 ** (-cnr / 20.0)
        out[str(cnr)] = {}
        for arm in arms:
            x = wf['sc_qpsk'] if arm == 'sc_qpsk_probit' else (wf['sc_cphase'] if arm == 'sc_cphase_probit' else wf['afdm'])
            y = g0 * x + sig * w0
            r = np.where(y.real >= 0, 1.0, -1.0) + 1j * np.where(y.imag >= 0, 1.0, -1.0)
            xref = x
            if arm == 'afdm_semiblind_probit':
                xref, _ = g03_semiblind_reconstruct(C, r, wf, cfg['pilot_syms_sb'])
            mode = 'bussgang' if arm == 'afdm_bussgang' else ('cmean' if arm == 'afdm_cmean' else 'probit')
            sv = g03_score_vec(r, xref, mode)
            pk, _, _ = g03_map_search(sv, xref, ell_lo, ell_hi, nu_grid)
            out[str(cnr)][arm] = pk
    return dict(seed=seed, n=n, peaks=out)


def g03_eval_worker(args):
    seed, n, cnrs_db, wsrs_db, thresh = args
    C = setup()
    cfg = CFG['g03']
    nu_grid = np.arange(-cfg['nu_max'], cfg['nu_max'] + 1e-9, cfg['nu_grid_step'])
    ell_lo, ell_hi = cfg['ell_range']
    wf = g03_waveforms(C, seed, n)
    rng = np.random.default_rng([SEED, 31, seed, n])
    phi0 = rng.uniform(0.0, 2.0 * np.pi)
    phiw = rng.uniform(0.0, 2.0 * np.pi)
    tau_w = rng.uniform(8.0, 60.0)
    sgn_nu = -1.0 if rng.random() < 0.5 else 1.0
    nu_w = sgn_nu * rng.uniform(0.6, 2.5)
    g0 = np.exp(1j * phi0)
    w0 = (rng.standard_normal(n) + 1j * rng.standard_normal(n)) / np.sqrt(2.0)
    echo = {k: frac_delay_doppler(wf[k], tau_w, nu_w) for k in ('sc_qpsk', 'sc_cphase', 'afdm')}
    arms = ('sc_qpsk_probit', 'sc_cphase_probit', 'afdm_bussgang', 'afdm_cmean', 'afdm_probit') + (
        ('afdm_semiblind_probit',) if n == 1024 else ())
    cells = {}
    for cnr in cnrs_db:
        sig = 10.0 ** (-cnr / 20.0)
        for wsr in wsrs_db:
            gw = (10.0 ** (wsr / 20.0)) * np.exp(1j * phiw)
            key = f'{cnr}|{wsr}'
            cells[key] = {}
            for arm in arms:
                wk = 'sc_qpsk' if arm == 'sc_qpsk_probit' else ('sc_cphase' if arm == 'sc_cphase_probit' else 'afdm')
                x = wf[wk]
                y = g0 * x + gw * echo[wk] + sig * w0
                r = np.where(y.real >= 0, 1.0, -1.0) + 1j * np.where(y.imag >= 0, 1.0, -1.0)
                xref = x
                dec_ok = True
                if arm == 'afdm_semiblind_probit':
                    xref, dec_ok = g03_semiblind_reconstruct(C, r, wf, cfg['pilot_syms_sb'])
                mode = 'bussgang' if arm == 'afdm_bussgang' else ('cmean' if arm == 'afdm_cmean' else 'probit')
                sv = g03_score_vec(r, xref, mode)
                pk, lhat, nuhat = g03_map_search(sv, xref, ell_lo, ell_hi, nu_grid)
                th = thresh[str(n)][str(cnr)][arm]
                hit = int(pk > th and abs(lhat - tau_w) <= 1.0 and abs(nuhat - nu_w) <= 0.5)
                cells[key][arm] = dict(hit=hit, fa_ex=int(pk > th), pk=round(pk, 4), dec_ok=int(dec_ok))
    return dict(seed=seed, n=n, tau_w=tau_w, nu_w=nu_w, cells=cells)


def run_g03(out):
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    cfg = CFG['g03']
    t0 = time.time()
    c_seeds = list(range(*cfg['calib_seeds']))
    nc_seeds = list(range(*cfg['null_check_seeds']))
    e_seeds = list(range(*cfg['eval_seeds']))
    thresh = {'1024': {}, '4096': {}}
    null_gate = {}
    with get_context('spawn').Pool(WORKERS) as pool:
        cal_1024 = list(pool.imap_unordered(g03_null_worker, [(s, 1024, cfg['cnrs_db']) for s in c_seeds]))
        cal_4096 = list(pool.imap_unordered(g03_null_worker, [(s, 4096, [cfg['n4096_cnr']]) for s in c_seeds]))
        for n_str, rows, cnrs in (('1024', cal_1024, cfg['cnrs_db']), ('4096', cal_4096, [cfg['n4096_cnr']])):
            for cnr in cnrs:
                cs = str(cnr); thresh[n_str][cs] = {}
                for arm in rows[0]['peaks'][cs]:
                    vals = [r['peaks'][cs][arm] for r in rows]
                    thresh[n_str][cs][arm] = float(np.quantile(vals, 1.0 - cfg['pfa']))
        chk_1024 = list(pool.imap_unordered(g03_null_worker, [(s, 1024, [25.0]) for s in nc_seeds]))
        for arm in ('afdm_probit', 'afdm_bussgang'):
            th = thresh['1024']['25.0'][arm]
            null_gate[arm] = float(np.mean([r['peaks']['25.0'][arm] > th for r in chk_1024]))
        ev_1024 = list(pool.imap_unordered(
            g03_eval_worker, [(s, 1024, cfg['cnrs_db'], cfg['wsrs_db'], thresh) for s in e_seeds]))
        ev_4096 = list(pool.imap_unordered(
            g03_eval_worker, [(s, 4096, [cfg['n4096_cnr']], cfg['n4096_wsrs_db'], thresh) for s in e_seeds]))
    with gzip.open(out / 'g03_rows.jsonl.gz', 'wt') as fh:
        for r in sorted(ev_1024, key=lambda x: x['seed']) + sorted(ev_4096, key=lambda x: x['seed']):
            print(json.dumps(r), file=fh)
    ch = resource.getrusage(resource.RUSAGE_CHILDREN)
    meta = dict(_argv=sys.argv, _config=cfg, seed=SEED, workers=WORKERS, thresholds=thresh, null_gate_25db=null_gate,
                core_hours=(ch.ru_utime + ch.ru_stime) / 3600.0, wall_seconds=time.time() - t0)
    (out / 'g03_run.json').write_text(json.dumps(meta, indent=1))
    print('g03 done wall=', round(meta['wall_seconds'], 1), 'null_gate=', null_gate)


# ===========================================================================
# 2. Card g01: short-CP SP-OFDM ISAC ghost vs block phase coding vs lin-template
# ===========================================================================
def g01_pilot_block(K):
    n = np.arange(K)
    return np.exp(1j * np.pi * (n ** 2) / K)


def g01_stream_from_blocks(blocks, C):
    """Concatenate M blocks with length-C cyclic prefix; prepend block -1 for steady-state."""
    with_cp = [np.concatenate([b[-C:], b]) for b in blocks]
    return np.concatenate(with_cp)


def g01_extract_active(stream, M, K, C):
    L = K + C
    # block 0 is guard block -1; active blocks are m = 1..M
    out = np.empty((M, K), dtype=complex)
    for m in range(M):
        st = (m + 1) * L + C
        out[m] = stream[st:st + K]
    return out


def g01_lin_template(p, q_seq, M, K, C, ell, f_hz, fs):
    """Exact active-window samples (M, K) produced by a unit-gain path at delay ell and Doppler f_hz."""
    L = K + C
    blocks = [q_seq[m] * p for m in range(M + 1)]
    stream = g01_stream_from_blocks(blocks, C)
    tot = len(stream)
    delayed = np.zeros(tot, dtype=complex)
    if ell == 0:
        delayed[:] = stream
    else:
        delayed[ell:] = stream[:-ell]
    t = np.arange(tot) / fs
    rx = delayed * np.exp(2j * np.pi * f_hz * t)
    return g01_extract_active(rx, M, K, C)


def g01_cyclic_map(Y_act, p, q_act, ell_cands, f_grid, K, C, fs):
    """Self-normalized cyclic-pilot slow-time Doppler map on intra-CP candidates ell_cands."""
    M = Y_act.shape[0]
    L = K + C
    Y_deq = Y_act * np.conj(q_act)[:, None]
    Pf_conj = np.conj(np.fft.fft(p))
    # Per-block circular correlation with pilot p: shape (M, K)
    corr_blk = np.fft.ifft(np.fft.fft(Y_deq, axis=1) * Pf_conj[None, :], axis=1)
    # Slow-time phase + intra-block phase approximation
    m_idx = np.arange(M)
    n_idx = np.arange(K)
    denom = max(float(np.vdot(Y_deq, Y_deq).real), 1e-24)
    best_val, best_l, best_f = 0.0, int(ell_cands[0]), 0.0
    # Vectorized over f_grid and ell_cands
    # Exact intra-CP template inner product: for ell <= C, block m active samples are q_m * p[(n-ell)%K] * exp(j 2pi f ((m+1)L + C + n)/fs)
    t_mat = ((m_idx[:, None] + 1) * L + C + n_idx[None, :]) / fs
    for f in f_grid:
        Y_derot = Y_deq * np.exp(-2j * np.pi * f * t_mat)
        c_m = np.fft.ifft(np.fft.fft(Y_derot, axis=1) * Pf_conj[None, :], axis=1)
        scores = np.abs(np.sum(c_m[:, ell_cands], axis=0)) ** 2 / (denom * M / K)
        j = int(np.argmax(scores))
        if scores[j] > best_val:
            best_val = float(scores[j])
            best_l = int(ell_cands[j])
            best_f = float(f)
    return best_val, best_l, best_f


def g01_est_strong_lin(Y_act, p, q_seq, M, K, C, fs):
    """Estimate strong path (ell_s in 1..36, f_s in [-35, 35] Hz) using exact cross-block pilot template."""
    f_coarse = np.linspace(-35.0, 35.0, 29)
    best_v, best_l, best_f = -1.0, 1, 0.0
    for ell in range(1, 37):
        # Base template at f = 0
        blocks = [q_seq[m] * p for m in range(M + 1)]
        stream = g01_stream_from_blocks(blocks, C)
        delayed = np.zeros_like(stream)
        delayed[ell:] = stream[:-ell]
        B0 = g01_extract_active(delayed, M, K, C)
        L = K + C
        t_mat = ((np.arange(M)[:, None] + 1) * L + C + np.arange(K)[None, :]) / fs
        # Inner products across f_coarse
        ips = np.sum(np.conj(B0)[None, :, :] * Y_act[None, :, :] * np.exp(-2j * np.pi * f_coarse[:, None, None] * t_mat[None, :, :]), axis=(1, 2))
        nrm2 = float(np.vdot(B0, B0).real)
        vals = (np.abs(ips) ** 2) / max(nrm2, 1e-12)
        j = int(np.argmax(vals))
        if vals[j] > best_v:
            best_v, best_l, best_f = float(vals[j]), ell, float(f_coarse[j])
    # Fine 1D refinement in f around best_f
    blocks = [q_seq[m] * p for m in range(M + 1)]
    stream = g01_stream_from_blocks(blocks, C)
    delayed = np.zeros_like(stream); delayed[best_l:] = stream[:-best_l]
    B0 = g01_extract_active(delayed, M, K, C)
    nrm2 = float(np.vdot(B0, B0).real)
    t_mat = ((np.arange(M)[:, None] + 1) * (K + C) + C + np.arange(K)[None, :]) / fs

    def neg_obj(f):
        ip = np.sum(np.conj(B0) * Y_act * np.exp(-2j * np.pi * f * t_mat))
        return -float((abs(ip) ** 2) / nrm2)

    res = minimize_scalar(neg_obj, bounds=(best_f - 3.0, best_f + 3.0), method='bounded', options={'xatol': 0.05})
    f_hat = float(res.x)
    T_s = B0 * np.exp(2j * np.pi * f_hat * t_mat)
    h_hat = np.vdot(T_s, Y_act) / nrm2
    return best_l, f_hat, h_hat, T_s


def g01_joint_lin_map(Y_act, T_s, p, q_seq, ell_cands, f_grid, M, K, C, fs):
    """Sol's baseline: project out estimated strong-path continuous pilot subspace T_s, score intra-CP candidates."""
    u_s = T_s / max(np.linalg.norm(T_s), 1e-12)
    Y_proj = Y_act - np.vdot(u_s, Y_act) * u_s
    denom = max(float(np.vdot(Y_proj, Y_proj).real), 1e-24)
    L = K + C
    t_mat = ((np.arange(M)[:, None] + 1) * L + C + np.arange(K)[None, :]) / fs
    q_act = q_seq[1:]
    Pf_conj = np.conj(np.fft.fft(p))
    best_val, best_l, best_f = 0.0, int(ell_cands[0]), 0.0
    # Note: for ell in 1..C, exact intra-CP template is orthogonalized against u_s!
    # Prebuild base templates for ell_cands at f=0: shape (len(ell_cands), M, K)
    B_list = []
    for ell in ell_cands:
        p_sh = np.roll(p, ell)
        B_list.append(q_act[:, None] * p_sh[None, :])
    B_arr = np.asarray(B_list)  # (E, M, K)
    for f in f_grid:
        rot = np.exp(2j * np.pi * f * t_mat)
        T_cands = B_arr * rot[None, :, :]  # (E, M, K)
        # Project each candidate orthogonal to u_s for exact 2-path VarPro gain!
        ov = np.sum(np.conj(u_s)[None, :, :] * T_cands, axis=(1, 2))  # (E,)
        T_perp = T_cands - ov[:, None, None] * u_s[None, :, :]
        nrms = np.maximum(np.real(np.sum(np.conj(T_perp) * T_perp, axis=(1, 2))), 1e-12)
        ips = np.sum(np.conj(T_perp) * Y_proj[None, :, :], axis=(1, 2))
        scores = (np.abs(ips) ** 2) / (nrms * denom / (M * K))
        j = int(np.argmax(scores))
        if scores[j] > best_val:
            best_val, best_l, best_f = float(scores[j]), int(ell_cands[j]), float(f)
    return best_val, best_l, best_f


def g01_sim_one(seed, rho, dmode, f_band, wsr_db, thresh=None):
    cfg = CFG['g01']
    M, K, C, fs = cfg['M'], cfg['K'], cfg['C'], cfg['fs']
    p = g01_pilot_block(K)
    rng = np.random.default_rng([SEED, 11, seed, int(round(rho * 100)), 0 if dmode == 'd_clean' else 1, int(round(f_band))])
    u_blocks = [(rng.choice([-1.0, 1.0], K) + 1j * rng.choice([-1.0, 1.0], K)) / np.sqrt(2.0) for _ in range(M + 1)]
    if dmode == 'd_clean':
        ell_s = 28
        f_s = rng.uniform(-15.0, 15.0)
    else:
        ell_s = int(rng.choice([21, 22, 23, 25, 26, 27, 29, 30, 31]))
        f_s = rng.uniform(-20.0, 20.0)
    phi_s = rng.uniform(0.0, 2.0 * np.pi)
    h_s = np.exp(1j * phi_s)
    sig = 10.0 ** (-cfg['snr_strong_db'] / 20.0)
    tot = (M + 1) * (K + C)
    noise = sig * (rng.standard_normal(tot) + 1j * rng.standard_normal(tot)) / np.sqrt(2.0)

    d_ghost = ell_s - C
    if wsr_db is not None:
        if seed % 2 == 0 and 4 <= d_ghost <= 15:
            ell_w = d_ghost
        else:
            ell_w = int(rng.integers(4, 16))
        f_w = rng.uniform(-f_band + 2.0, f_band - 2.0)
        h_w = (10.0 ** (wsr_db / 20.0)) * np.exp(1j * rng.uniform(0.0, 2.0 * np.pi))
    else:
        ell_w, f_w, h_w = 8, 0.0, 0.0j

    ell_cands = np.arange(4, C + 1)
    f_grid = np.linspace(-f_band, f_band, 25)
    t_tot = np.arange(tot) / fs

    # Build TX streams for repeated (q=1) and phase-coded q_m = (-1)^(m(m+1)//2)
    q_rep = np.ones(M + 1, dtype=complex)
    m_arr = np.arange(-1, M)
    q_cod = np.array([(-1.0) ** ((m * (m + 1)) // 2) for m in m_arr], dtype=complex)

    def rx_active(q_seq):
        blks = [q_seq[m] * (np.sqrt(rho) * p + np.sqrt(1.0 - rho) * u_blocks[m]) for m in range(M + 1)]
        s_tx = g01_stream_from_blocks(blks, C)
        ds = np.zeros(tot, complex); ds[ell_s:] = s_tx[:-ell_s]
        rx = h_s * ds * np.exp(2j * np.pi * f_s * t_tot) + noise
        if wsr_db is not None:
            dw = np.zeros(tot, complex); dw[ell_w:] = s_tx[:-ell_w]
            rx = rx + h_w * dw * np.exp(2j * np.pi * f_w * t_tot)
        return g01_extract_active(rx, M, K, C)

    Y_rep = rx_active(q_rep)
    Y_cod = rx_active(q_cod)

    v_naive, l_naive, fn_naive = g01_cyclic_map(Y_rep, p, q_rep[1:], ell_cands, f_grid, K, C, fs)
    _, _, h_hat_s, T_s = g01_est_strong_lin(Y_rep, np.sqrt(rho) * p, q_rep, M, K, C, fs)
    Y_1sic = Y_rep - h_hat_s * T_s
    v_1sic, l_1sic, fn_1sic = g01_cyclic_map(Y_1sic, p, q_rep[1:], ell_cands, f_grid, K, C, fs)
    v_jlin, l_jlin, fn_jlin = g01_joint_lin_map(Y_rep, T_s, p, q_rep, ell_cands, f_grid, M, K, C, fs)
    v_pcod, l_pcod, fn_pcod = g01_cyclic_map(Y_cod, p, q_cod[1:], ell_cands, f_grid, K, C, fs)

    raw_res = dict(
        rep_naive=(v_naive, l_naive, fn_naive),
        rep_1sic=(v_1sic, l_1sic, fn_1sic),
        rep_joint_lin=(v_jlin, l_jlin, fn_jlin),
        phase_code=(v_pcod, l_pcod, fn_pcod),
    )
    if thresh is None:
        return {k: v[0] for k, v in raw_res.items()}
    df_tol = max(2.0 * f_band / 24.0 * 1.5, 4.5)
    out = {}
    for arm, (val, lh, fh) in raw_res.items():
        th = thresh[arm]
        hit = int(val > th and lh == ell_w and abs(fh - f_w) <= df_tol)
        out[arm] = dict(hit=hit, fa_ex=int(val > th), pk=round(val, 4))
    return dict(ell_w=ell_w, d_ghost=d_ghost, arms=out)


def g01_calib_worker(seed):
    cfg = CFG['g01']
    res = {}
    for rho in cfg['rhos']:
        for dmode in cfg['delay_modes']:
            for fb in cfg['f_bands']:
                res[f'{rho}|{dmode}|{fb}'] = g01_sim_one(seed, rho, dmode, fb, None, None)
    return res


def g01_eval_worker(args):
    seed, thresh = args
    cfg = CFG['g01']
    cells = {}
    for rho in cfg['rhos']:
        for dmode in cfg['delay_modes']:
            for fb in cfg['f_bands']:
                tk = f'{rho}|{dmode}|{fb}'
                for wsr in cfg['wsrs_db']:
                    cells[f'{tk}|{wsr}'] = g01_sim_one(seed, rho, dmode, fb, wsr, thresh[tk])
    return dict(seed=seed, cells=cells)


def g01_noiseless_gate():
    """Verify noiseless ghost amplitude ratio = 12/64 = 0.1875 for rep_naive and 0 for phase_code."""
    M, K, C, fs = 16, 64, 16, 16000.0
    p = g01_pilot_block(K)
    q_rep = np.ones(M + 1, complex)
    q_cod = np.array([(-1.0) ** ((m * (m + 1)) // 2) for m in range(-1, M)], complex)
    Y_rep = g01_lin_template(p, q_rep, M, K, C, 28, 0.0, fs)
    Y_cod = g01_lin_template(p, q_cod, M, K, C, 28, 0.0, fs)
    Pf_conj = np.conj(np.fft.fft(p))
    c_rep = np.mean(np.fft.ifft(np.fft.fft(Y_rep, axis=1) * Pf_conj[None, :], axis=1), axis=0) / K
    c_cod = np.mean(np.fft.ifft(np.fft.fft(Y_cod * np.conj(q_cod[1:])[:, None], axis=1) * Pf_conj[None, :], axis=1), axis=0) / K
    return dict(rep_ghost_12=float(abs(c_rep[12])), rep_main_28=float(abs(c_rep[28])),
                cod_ghost_12=float(abs(c_cod[12])), cod_main_28=float(abs(c_cod[28])))


def run_g01(out):
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    cfg = CFG['g01']; t0 = time.time()
    gate = g01_noiseless_gate()
    if abs(gate['rep_ghost_12'] - 0.1875) > 1e-3 or gate['cod_ghost_12'] > 1e-10:
        raise AssertionError(f'g01 noiseless gate failed: {gate}')
    c_seeds = list(range(*cfg['calib_seeds']))
    e_seeds = list(range(*cfg['eval_seeds']))
    thresh = {}
    with get_context('spawn').Pool(WORKERS) as pool:
        c_rows = list(pool.imap_unordered(g01_calib_worker, c_seeds))
        for tk in c_rows[0]:
            thresh[tk] = {}
            for arm in c_rows[0][tk]:
                thresh[tk][arm] = float(np.quantile([r[tk][arm] for r in c_rows], 1.0 - cfg['pfa']))
        e_rows = list(pool.imap_unordered(g01_eval_worker, [(s, thresh) for s in e_seeds]))
    with gzip.open(out / 'g01_rows.jsonl.gz', 'wt') as fh:
        for r in sorted(e_rows, key=lambda x: x['seed']):
            print(json.dumps(r), file=fh)
    ch = resource.getrusage(resource.RUSAGE_CHILDREN)
    meta = dict(_argv=sys.argv, _config=cfg, seed=SEED, workers=WORKERS, noiseless_gate=gate, thresholds=thresh,
                core_hours=(ch.ru_utime + ch.ru_stime) / 3600.0, wall_seconds=time.time() - t0)
    (out / 'g01_run.json').write_text(json.dumps(meta, indent=1))
    print('g01 done wall=', round(meta['wall_seconds'], 1), 'gate=', gate)


# ===========================================================================
# 3. Card g05: SIMO (M=2) Woodbury-EM vs c16 pilot VarPro & short TDM
# ===========================================================================
def time_channel_apply(xt, c1, delays, dopplers, gains):
    """O(P N) exact action H_time @ xt."""
    return time_regressors(xt, delays, dopplers, c1) @ np.asarray(gains, complex)


def time_channel_adj_apply(yt, c1, delays, dopplers, gains):
    """O(P N) exact adjoint action H_time^H @ yt."""
    n = len(yt); idx = np.arange(n)
    out = np.zeros(n, dtype=complex)
    for l, nu, g in zip(delays, dopplers, gains):
        l = int(l)
        col = (idx - l) % n
        cp = np.where(idx < l, np.exp(2j * np.pi * c1 * (n * n + 2 * n * (idx - l))), 1.0)
        term = np.conj(g) * np.conj(cp) * np.exp(-2j * np.pi * idx * float(nu) / n) * yt
        out[col] += term
    return out


def time_channel_gram_sum(n, c1, delays, dopplers, G):
    """O(P^2 N) exact sum_{m=1}^M H_m^H H_m matching dense matmul to machine precision."""
    idx = np.arange(n); P = len(delays)
    S = np.zeros((n, n), dtype=complex)
    l_arr = [int(x) for x in delays]
    nu_arr = [float(x) for x in dopplers]
    cp_list = [np.where(idx < lp, np.exp(2j * np.pi * c1 * (n * n + 2 * n * (idx - lp))), 1.0) for lp in l_arr]
    GG = G @ G.conj().T  # (P, P) = sum_m g_{m,p} conj(g_{m,q}); note (H^H H) uses sum_m conj(g_{m,p}) g_{m,q} = conj(GG[p,q])
    for p in range(P):
        lp = l_arr[p]; r_idx = (idx - lp) % n
        S[r_idx, r_idx] += np.real(GG[p, p])
        for q in range(p + 1, P):
            lq = l_arr[q]; c_idx = (idx - lq) % n
            w = np.conj(GG[p, q]) * np.conj(cp_list[p]) * cp_list[q] * np.exp(2j * np.pi * (nu_arr[q] - nu_arr[p]) * idx / n)
            S[r_idx, c_idx] += w
            S[c_idx, r_idx] += np.conj(w)
    return S


def time_regressors(xt, delays, dopplers, c1):
    n = len(xt); idx = np.arange(n)
    l = np.asarray(delays, int); nu = np.asarray(dopplers, float)
    d_idx = idx[:, None] - l[None, :]
    cp = np.where(d_idx < 0, np.exp(2j * np.pi * c1 * (n * n + 2 * n * d_idx)), 1.0)
    return xt[d_idx % n] * cp * np.exp(2j * np.pi * idx[:, None] * nu[None, :] / n)


def doppler_pw_mae(delays_hat, dopplers_hat, truth):
    l_true = np.asarray(truth['l_i'], int)
    nu_true = np.asarray(truth['k_real'], float)
    pw = np.abs(np.asarray(truth['g_i'], complex)) ** 2
    errs = []
    l_hat = np.asarray(delays_hat, int); nu_hat = np.asarray(dopplers_hat, float)
    for lt, nut in zip(l_true, nu_true):
        m = np.flatnonzero(l_hat == lt)
        if len(m) > 0:
            errs.append(float(np.min(np.abs(nu_hat[m] - nut))))
        else:
            errs.append(1.5)
    return float(np.sum(pw * np.array(errs)) / np.sum(pw))


def simo_pilot_support_and_init(Yt, pt, c1, l_cap=102, P=8, fixed_delays=None):
    """Simultaneous M-hydrophone Orthogonal Matching Pursuit (S-OMP) over (delay, Doppler) grid."""
    n = len(pt)
    k_grid = np.arange(-2.25, 2.251, 0.25)
    idx = np.arange(n)
    if fixed_delays is not None:
        rot = np.exp(-2j * np.pi * np.outer(k_grid, idx) / n)
        cand_ls = np.asarray(fixed_delays, int)
        best_k = np.empty(len(cand_ls))
        for i, l in enumerate(cand_ls):
            d_idx = idx - int(l)
            cp = np.where(d_idx < 0, np.exp(2j * np.pi * c1 * (n * n + 2 * n * d_idx)), 1.0)
            base = pt[d_idx % n] * cp
            ips = rot @ (np.conj(base)[:, None] * Yt)
            best_k[i] = float(k_grid[int(np.argmax(np.sum(np.abs(ips) ** 2, axis=1)))])
        return cand_ls, best_k

    # Unknown delays: build dictionary (n, (l_cap+1)*K) and run P-step S-OMP
    ls_all = np.repeat(np.arange(l_cap + 1), len(k_grid))
    ks_all = np.tile(k_grid, l_cap + 1)
    Phi = time_regressors(pt, ls_all, ks_all, c1)
    nrms = np.maximum(np.linalg.norm(Phi, axis=0, keepdims=True), 1e-12)
    Phi_u = Phi / nrms
    R = Yt.copy()
    Q_list = []
    sel_l = []
    sel_k = []
    active_mask = np.ones(len(ls_all), dtype=bool)
    for _ in range(P):
        scores = np.sum(np.abs(Phi_u.conj().T @ R) ** 2, axis=1)
        scores[~active_mask] = -1.0
        j = int(np.argmax(scores))
        lj = int(ls_all[j]); kj = float(ks_all[j])
        sel_l.append(lj); sel_k.append(kj)
        active_mask[ls_all == lj] = False
        q = Phi_u[:, j].copy()
        for u in Q_list:
            q = q - np.vdot(u, q) * u
        qn = np.linalg.norm(q)
        if qn > 1e-12:
            q = q / qn
            Q_list.append(q)
            R = R - np.outer(q, np.conj(q) @ R)
    order = np.argsort(sel_l)
    return np.asarray(sel_l, int)[order], np.asarray(sel_k, float)[order]


def simo_varpro_step(Yt, xt, delays, nus_init, c1, Sigma_cov_fft=None, diag_ridge=1e-6, rounds=2):
    """Joint M-channel Variable Projection over continuous Dopplers with exact cyclic-diagonal covariance."""
    n = len(xt); P = len(delays); idx = np.arange(n)
    l = np.asarray(delays, int); nus = np.asarray(nus_init, float).copy()
    d_idx = idx[:, None] - l[None, :]
    cp_mat = np.where(d_idx < 0, np.exp(2j * np.pi * c1 * (n * n + 2 * n * d_idx)), 1.0)
    base = xt[d_idx % n] * cp_mat  # (n, P)
    tot_y = float(np.real(np.vdot(Yt, Yt)))

    def eval_nu(nu_vec):
        A = base * np.exp(2j * np.pi * idx[:, None] * nu_vec[None, :] / n)  # (n, P)
        Q = A.conj().T @ A + diag_ridge * np.eye(P)
        if Sigma_cov_fft is not None:
            # Sigma_cov_fft[(p, q)] holds the length-n vector c_{pq}[k] such that
            # [Sigma_post]_{p,q} = sum_k c_{pq}[k] * exp(j 2pi (nu_q - nu_p) k / n)
            Gam = np.zeros((P, P), dtype=complex)
            for p in range(P):
                Gam[p, p] = Sigma_cov_fft[(p, p)]
                for q in range(p + 1, P):
                    ph = np.exp(2j * np.pi * (nu_vec[q] - nu_vec[p]) * idx / n)
                    val = complex(np.dot(Sigma_cov_fft[(p, q)], ph))
                    Gam[p, q] = val
                    Gam[q, p] = np.conj(val)
            Q = Q + 0.5 * (Gam + Gam.conj().T)
        B = A.conj().T @ Yt  # (P, M)
        G = np.linalg.solve(Q, B)  # (P, M)
        obj = tot_y - float(np.real(np.sum(np.conj(B) * G)))
        return obj, G

    val, G = eval_nu(nus)
    bounds = [(max(-2.6, c - 0.65), min(2.6, c + 0.65)) for c in nus]
    for _ in range(rounds):
        for j, (lo, hi) in enumerate(bounds):
            def sc_fn(t):
                q = nus.copy(); q[j] = t
                return eval_nu(q)[0]
            opt = minimize_scalar(sc_fn, bounds=(lo, hi), method='bounded', options={'xatol': 0.002, 'maxiter': 15})
            if opt.fun < val:
                nus[j] = float(opt.x)
                val, G = eval_nu(nus)
    return nus, G, val


def build_woodbury_cov_dict(S_inv, sigma2, delays, c1):
    """Extract the 1 + P(P-1)/2 cyclic diagonals of sigma2 * S^{-1} for exact M-step trace correction."""
    n = S_inv.shape[0]; P = len(delays); idx = np.arange(n)
    l = np.asarray(delays, int)
    tr_val = complex(sigma2 * np.real(np.trace(S_inv)))
    cov_dict = {}
    cp_cols = []
    for p in range(P):
        cov_dict[(p, p)] = tr_val
        lp = int(l[p])
        cp_cols.append(np.where(idx < lp, np.exp(2j * np.pi * c1 * (n * n + 2 * n * (idx - lp))), 1.0))
    for p in range(P):
        lp = int(l[p])
        for q in range(p + 1, P):
            lq = int(l[q])
            # [U_p^H U_q S^{-1}] trace = sum_k conj(cp_p[k]) * cp_q[k] * exp(j 2pi (nu_q - nu_p) k / n) * S_inv[(k-lq)%n, (k-lp)%n]
            r_idx = (idx - lq) % n
            c_idx = (idx - lp) % n
            cov_dict[(p, q)] = sigma2 * np.conj(cp_cols[p]) * cp_cols[q] * S_inv[r_idx, c_idx]
    return cov_dict


def run_woodbury_em(Yt, pt, sigma2, vd, c1, fixed_delays=None, em_iters=5, use_trace=True):
    """SIMO Time-Domain Woodbury EM (use_trace=False gives the naive alternating negative control)."""
    n = len(pt); M = Yt.shape[1]
    delays, nus0 = simo_pilot_support_and_init(Yt, pt, c1, fixed_delays=fixed_delays)
    # Round-0 c16 unbiased pilot-only Variable Projection (d_hat = 0 => E[d y^H] != 0, so LS on known pilot pt is unbiased!)
    nus, G, _ = simo_varpro_step(Yt, pt, delays, nus0, c1, Sigma_cov_fft=None, diag_ridge=sigma2 * 1e-3, rounds=2)
    if em_iters == 0:
        return delays, nus, G

    for it in range(em_iters):
        S = (sigma2 / vd) * np.eye(n, dtype=complex) + time_channel_gram_sum(n, c1, delays, nus, G)
        rhs = np.zeros(n, dtype=complex)
        for m in range(M):
            res_m = Yt[:, m] - time_channel_apply(pt, c1, delays, nus, G[:, m])
            rhs += time_channel_adj_apply(res_m, c1, delays, nus, G[:, m])
        cf = cho_factor(S, lower=True, check_finite=False)
        d_hat = cho_solve(cf, rhs, check_finite=False)
        # Re-check coarse Doppler jumps (or unknown delays) using full reconstructed signal pt + d_hat!
        if it in (0, 2):
            delays_new, nus_coarse = simo_pilot_support_and_init(
                Yt, pt + d_hat, c1, fixed_delays=(delays if fixed_delays is not None else None))
            delays = delays_new
            # Keep previous continuous nu if within 0.35 bin of new full-signal coarse peak, else jump to coarse peak
            nus = np.where(np.abs(nus - nus_coarse) <= 0.35, nus, nus_coarse)
        if use_trace:
            S_inv = cho_solve(cf, np.eye(n, dtype=complex), check_finite=False)
            cov_dict = build_woodbury_cov_dict(S_inv, sigma2, delays, c1)
        else:
            cov_dict = None
        nus, G, _ = simo_varpro_step(Yt, pt + d_hat, delays, nus, c1,
                                     Sigma_cov_fft=cov_dict, diag_ridge=sigma2 * 1e-3, rounds=1)
    return delays, nus, G


def simo_short_tdm(dt_true, G_true, delays_true, nus_true, w_time, sigma2, vd, rho, c1, fixed_delays=None):
    """Sol's baseline: equal total frame energy, pilot placed in 2 time-domain TDM bursts at 0 and N/2."""
    n = len(dt_true); M = G_true.shape[1]
    p_tot = vd / (1.0 - rho)
    L_b = max(8, int(round(rho * n / 2.0)))
    slots = np.r_[np.arange(0, L_b), np.arange(n // 2, n // 2 + L_b)]
    p_tdm = np.zeros(n, dtype=complex)
    zc = np.exp(1j * np.pi * (np.arange(L_b) ** 2) / L_b) * np.sqrt(p_tot)
    p_tdm[:L_b] = zc
    p_tdm[n // 2:n // 2 + L_b] = zc
    mask_d = np.ones(n, dtype=float)
    mask_d[slots] = 0.0
    scale_d = np.sqrt((1.0 - rho) * n * p_tot / max(np.sum(mask_d) * vd, 1e-9))
    dt_tx = dt_true * mask_d * scale_d
    xt_tx = p_tdm + dt_tx
    Yt = np.column_stack([time_channel_apply(xt_tx, c1, delays_true, nus_true, G_true[:, m]) + w_time[:, m]
                          for m in range(M)])
    # Unbiased joint M-channel VarPro using known TDM bursts p_tdm
    delays, nus0 = simo_pilot_support_and_init(Yt, p_tdm, c1, fixed_delays=fixed_delays)
    nus, G, _ = simo_varpro_step(Yt, p_tdm, delays, nus0, c1, Sigma_cov_fft=None, diag_ridge=sigma2 * 1e-3, rounds=2)
    return delays, nus, G, Yt, p_tdm, mask_d * scale_d


def simo_turbo_decode(C, Yt, pt, delays, nus, G, sigma2, c1, truth, d_scale_vec=None, rounds=10, dec_iters=50):
    """Exact M-hydrophone LMMSE-LDPC turbo loop via O(N log N) FFT conjugation + N x N Hermitian Cholesky."""
    from messages import moments
    ctx = C['ctx']; dec_fn = ctx.native.decoder_messages; gd = C['stage3'].e1.gd
    n = len(pt); M = Yt.shape[1]; vd = 0.5; a = np.sqrt(vd / 2.0); c2 = float(ctx.system.c2)
    # Build K_time = sum_m H_eff_m^H H_eff_m in O(P^2 N), then conjugate K_daft = A K_time A^H via 2D FFTs in O(N^2 log N)!
    K_time = time_channel_gram_sum(n, c1, delays, nus, G)
    if d_scale_vec is not None:
        K_time = (K_time * d_scale_vec[:, None]) * d_scale_vec[None, :]
    # K_daft = A @ K_time @ A^H = daft(daft(K_time, inv=False)^H, inv=False)^H
    K = daft(daft(K_time, c1, c2, inverse=False).conj().T, c1, c2, inverse=False).conj().T
    K = 0.5 * (K + K.conj().T)
    yt_nopilot = [Yt[:, m] - time_channel_apply(pt, c1, delays, nus, G[:, m]) for m in range(M)]
    prior = np.zeros(2 * n); err = 1; used = 0
    for r in range(rounds):
        mu, v, _ = moments(np.clip(prior, -20.0, 20.0), vd)
        v_safe = np.maximum(v, 1e-8)
        sq = np.sqrt(v_safe)
        used = r + 1
        B_mat = (K * sq[:, None]) * sq[None, :] + sigma2 * np.eye(n)
        cf = cho_factor(B_mat, lower=True, check_finite=False)
        B_inv = cho_solve(cf, np.eye(n, dtype=complex), check_finite=False)
        diag_Binv = np.real(np.diag(B_inv))
        s = np.maximum((1.0 - sigma2 * diag_Binv) / v_safe, 1e-9)
        mu_t = daft(mu, c1, c2, inverse=True)
        if d_scale_vec is not None:
            mu_t = mu_t * d_scale_vec
        rhs_t = np.zeros(n, dtype=complex)
        for m in range(M):
            res_m = yt_nopilot[m] - time_channel_apply(mu_t, c1, delays, nus, G[:, m])
            rhs_t += time_channel_adj_apply(res_m, c1, delays, nus, G[:, m])
        if d_scale_vec is not None:
            rhs_t = rhs_t * d_scale_vec
        rhs = daft(rhs_t, c1, c2, inverse=False)
        filt = (cho_solve(cf, sq * rhs, check_finite=False)) / sq
        z = mu + filt / s
        eta = np.maximum(1.0 / s - v_safe, 1e-9)
        llr = np.concatenate([4.0 * a * z.real / eta, 4.0 * a * z.imag / eta])
        dec = dec_fn(ctx.code, np.clip(llr, -20.0, 20.0), maxiter=dec_iters)
        err = int(gd.score(ctx, dec['decoded'], truth) > 0)
        if bool(dec['decode_ok']):
            break
        prior = np.asarray(dec['raw_check_extrinsic'], float)
    return err, used


def g05_make_simo_frame(C, frame, rho_int, snr_int, corr):
    stage3, ctx = C['stage3'], C['ctx']
    c1, c2 = float(ctx.system.c1), float(ctx.system.c2)
    raw, obs, truth = stage3.observed(ctx, stage3.inputs(ctx, frame, CFG['g05']['scenario'], rho_int), rho_int, snr_int)
    n = len(obs['y']); sc = scale_of(raw, obs)
    p_daft = np.asarray(obs['pilot'], complex)
    d_daft = np.asarray(raw['data'], complex) / sc
    s2 = float(obs['sigma2'])
    l_true = np.asarray(truth['l_i'], int)
    nu_true = np.asarray(truth['k_real'], float)
    g1 = np.asarray(truth['g_i'], complex)
    rng = np.random.default_rng([SEED, 50, frame, int(round(corr * 100))])
    z_perp = (rng.standard_normal(len(g1)) + 1j * rng.standard_normal(len(g1))) / np.sqrt(2.0) * np.abs(g1)
    g2 = corr * g1 + np.sqrt(max(1.0 - corr ** 2, 0.0)) * z_perp
    g2 = g2 * (np.linalg.norm(g1) / max(np.linalg.norm(g2), 1e-12))
    G_true = np.column_stack([g1, g2])
    pt = daft(p_daft, c1, c2, inverse=True)
    dt = daft(d_daft, c1, c2, inverse=True)
    w1 = daft(np.sqrt(s2) * np.asarray(raw['noise'], complex), c1, c2, inverse=True)
    rng_w = np.random.default_rng([SEED, 51, frame, snr_int, rho_int])
    w2 = np.sqrt(s2) * (rng_w.standard_normal(n) + 1j * rng_w.standard_normal(n)) / np.sqrt(2.0)
    w_time = np.column_stack([w1, w2])
    Yt = np.column_stack([
        time_channel_apply(pt + dt, c1, l_true, nu_true, G_true[:, 0]) + w1,
        time_channel_apply(pt + dt, c1, l_true, nu_true, G_true[:, 1]) + w2,
    ])
    y1_daft_chk = daft(Yt[:, 0] - w1, c1, c2, inverse=False) + np.sqrt(s2) * np.asarray(raw['noise'], complex)
    gate_rel = float(np.linalg.norm(y1_daft_chk - obs['y']) / np.linalg.norm(obs['y']))
    return dict(Yt=Yt, pt=pt, dt=dt, w_time=w_time, s2=s2, truth=truth, G_true=G_true,
                c1=c1, c2=c2, gate_rel=gate_rel)


def g05_worker(frame):
    C = setup(); cfg = CFG['g05']; vd = 0.5
    rec = dict(frame=frame, partA={}, partB={})
    # Part A: known delays Doppler MAE across (rho, corr) + total-power-matched check
    cells_A = [(r, cfg['partA_snr'], c, f'{r}|{cfg["partA_snr"]}|{c}')
               for r in cfg['partA_rhos'] for c in cfg['partA_corrs']]
    tm = cfg['partA_totmatch']
    cells_A.append((tm['rho'], tm['snr'], tm['corr'], f'{tm["rho"]}|{tm["snr"]}|{tm["corr"]}|totmatch'))
    for rho_i, snr_i, corr, tag in cells_A:
        D = g05_make_simo_frame(C, frame, rho_i, snr_i, corr)
        if tag == '50|400|0.0':
            rec['gate_rel'] = D['gate_rel']
        lt = D['truth']['l_i']
        _, nu_c16, _ = run_woodbury_em(D['Yt'], D['pt'], D['s2'], vd, D['c1'], fixed_delays=lt, em_iters=0)
        _, nu_nt, _ = run_woodbury_em(D['Yt'], D['pt'], D['s2'], vd, D['c1'], fixed_delays=lt, em_iters=cfg['em_iters'], use_trace=False)
        _, nu_em, _ = run_woodbury_em(D['Yt'], D['pt'], D['s2'], vd, D['c1'], fixed_delays=lt, em_iters=cfg['em_iters'], use_trace=True)
        _, nu_tdm, _, _, _, _ = simo_short_tdm(
            D['dt'], D['G_true'], lt, D['truth']['k_real'], D['w_time'], D['s2'], vd, rho_i / 1000.0, D['c1'], fixed_delays=lt)
        rec['partA'][tag] = dict(
            c16_pilot_varpro=doppler_pw_mae(lt, nu_c16, D['truth']),
            short_tdm_joint=doppler_pw_mae(lt, nu_tdm, D['truth']),
            alt_notrace=doppler_pw_mae(lt, nu_nt, D['truth']),
            woodbury_em=doppler_pw_mae(lt, nu_em, D['truth']),
        )

    # Part B: unknown-delay blind capture + SIMO LMMSE-LDPC coded FER
    for snr_i in cfg['partB_snrs']:
        D5 = g05_make_simo_frame(C, frame, cfg['partB_rho'], snr_i, cfg['partB_corr'])
        D25 = g05_make_simo_frame(C, frame, cfg['partB_high_rho'], snr_i, cfg['partB_corr'])
        lt = D5['truth']['l_i']; nut = D5['truth']['k_real']
        # 1. true_H (rho=0.05)
        e_true, _ = simo_turbo_decode(C, D5['Yt'], D5['pt'], lt, nut, D5['G_true'], D5['s2'], D5['c1'],
                                      D5['truth'], rounds=cfg['turbo_rounds'], dec_iters=cfg['dec_iters'])
        # 2. c16_pilot_varpro at rho=0.05 (unknown delays)
        l_c5, nu_c5, G_c5 = run_woodbury_em(D5['Yt'], D5['pt'], D5['s2'], vd, D5['c1'], fixed_delays=None, em_iters=0)
        e_c5, _ = simo_turbo_decode(C, D5['Yt'], D5['pt'], l_c5, nu_c5, G_c5, D5['s2'], D5['c1'],
                                    D5['truth'], rounds=cfg['turbo_rounds'], dec_iters=cfg['dec_iters'])
        # 3. c16_pilot_varpro at rho=0.25 (conventional high-pilot reference!)
        l_c25, nu_c25, G_c25 = run_woodbury_em(D25['Yt'], D25['pt'], D25['s2'], vd, D25['c1'], fixed_delays=None, em_iters=0)
        e_c25, _ = simo_turbo_decode(C, D25['Yt'], D25['pt'], l_c25, nu_c25, G_c25, D25['s2'], D25['c1'],
                                     D25['truth'], rounds=cfg['turbo_rounds'], dec_iters=cfg['dec_iters'])
        # 4. short_tdm_joint at rho=0.05 (unknown delays)
        l_tdm, nu_tdm, G_tdm, Y_tdm, p_tdm, d_sc = simo_short_tdm(
            D5['dt'], D5['G_true'], lt, nut, D5['w_time'], D5['s2'], vd, cfg['partB_rho'] / 1000.0, D5['c1'], fixed_delays=None)
        e_tdm, _ = simo_turbo_decode(C, Y_tdm, p_tdm, l_tdm, nu_tdm, G_tdm, D5['s2'], D5['c1'],
                                     D5['truth'], d_scale_vec=d_sc, rounds=cfg['turbo_rounds'], dec_iters=cfg['dec_iters'])
        # 5. woodbury_em at rho=0.05 (unknown delays + 1 blind support refresh)
        l_em, nu_em, G_em = run_woodbury_em(D5['Yt'], D5['pt'], D5['s2'], vd, D5['c1'],
                                            fixed_delays=None, em_iters=cfg['em_iters'], use_trace=True)
        e_em, _ = simo_turbo_decode(C, D5['Yt'], D5['pt'], l_em, nu_em, G_em, D5['s2'], D5['c1'],
                                    D5['truth'], rounds=cfg['turbo_rounds'], dec_iters=cfg['dec_iters'])
        rec['partB'][str(snr_i)] = dict(
            true_H=e_true, c16_rho05=e_c5, c16_rho25=e_c25, short_tdm_rho05=e_tdm, woodbury_em_rho05=e_em,
            found_c16_05=int(len(set(int(x) for x in lt) & set(int(x) for x in l_c5))),
            found_em_05=int(len(set(int(x) for x in lt) & set(int(x) for x in l_em))),
            mae_unk_em_05=doppler_pw_mae(l_em, nu_em, D5['truth']),
        )
    return rec


def run_g05(out):
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    cfg = CFG['g05']; t0 = time.time()
    frames = list(range(*cfg['frames']))
    with get_context('spawn').Pool(WORKERS) as pool:
        rows = list(pool.imap_unordered(g05_worker, frames))
    rows.sort(key=lambda x: x['frame'])
    with gzip.open(out / 'g05_rows.jsonl.gz', 'wt') as fh:
        for r in rows:
            print(json.dumps(r), file=fh)
    ch = resource.getrusage(resource.RUSAGE_CHILDREN)
    meta = dict(_argv=sys.argv, _config=cfg, seed=SEED, workers=WORKERS, rows=len(rows),
                max_gate_rel=max(r['gate_rel'] for r in rows),
                core_hours=(ch.ru_utime + ch.ru_stime) / 3600.0, wall_seconds=time.time() - t0)
    (out / 'g05_run.json').write_text(json.dumps(meta, indent=1))
    print('g05 done wall=', round(meta['wall_seconds'], 1), 'core_hours=', round(meta['core_hours'], 3))


# ===========================================================================
# Smoke gate & summary reader
# ===========================================================================
def smoke(out):
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    t0 = time.process_time()
    C = setup()
    g1_gate = g01_noiseless_gate()
    if abs(g1_gate['rep_ghost_12'] - 0.1875) > 1e-3 or g1_gate['cod_ghost_12'] > 1e-10:
        raise AssertionError(f'g01 gate failed: {g1_gate}')
    D = g05_make_simo_frame(C, CFG['g05']['smoke_frame'], 50, 400, 0.0)
    if not D['gate_rel'] < 1e-12:
        raise AssertionError(f'g05 operator gate failed: {D["gate_rel"]}')
    # Verify M=1 Hermitian Cholesky turbo matches direct solve
    r_g5 = g05_worker(CFG['g05']['smoke_frame'])
    n_s = g03_null_worker((9999, 1024, [25.0]))
    t_cpu = time.process_time() - t0
    res = dict(g01_gate=g1_gate, g05_gate_rel=D['gate_rel'], g05_sample_partA=r_g5['partA']['50|400|0.0'],
               g05_sample_partB=r_g5['partB'], g03_null_sample=n_s['peaks']['25.0'], smoke_cpu_sec=t_cpu)
    (out / 'smoke.json').write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1))


def boot_ci(vals, rng, n_boot=2000):
    vals = np.asarray(vals, float)
    n = len(vals)
    pt = float(np.mean(vals))
    bs = [float(np.mean(vals[rng.integers(0, n, n)])) for _ in range(n_boot)]
    return dict(point=pt, ci95=[float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))])


def interp_mdr50(wsrs, hits):
    """Interpolated WSR (dB) at 50% hit rate (wsrs sorted descending e.g. -18, -22, ...)."""
    for i in range(len(wsrs) - 1):
        if hits[i] >= 0.5 and hits[i + 1] < 0.5:
            frac = (hits[i] - 0.5) / max(hits[i] - hits[i + 1], 1e-9)
            return float(wsrs[i] + frac * (wsrs[i + 1] - wsrs[i]))
    if hits[-1] >= 0.5:
        return float(wsrs[-1])
    return float(wsrs[0] + 4.0)


def read_summary(out):
    out = Path(out)
    rng = np.random.default_rng(SEED + 99)
    summary = dict(_argv=sys.argv, _config=CFG)

    # --- Read g03 ---
    if (out / 'g03_rows.jsonl.gz').exists():
        rows = [json.loads(x) for x in gzip.open(out / 'g03_rows.jsonl.gz', 'rt')]
        r1024 = [r for r in rows if r['n'] == 1024]
        r4096 = [r for r in rows if r['n'] == 4096]
        cfg3 = CFG['g03']
        arms3 = ('sc_qpsk_probit', 'sc_cphase_probit', 'afdm_bussgang', 'afdm_cmean', 'afdm_probit', 'afdm_semiblind_probit')
        grid = {}
        mdr50 = {}
        for cnr in cfg3['cnrs_db']:
            mdr50[str(cnr)] = {}
            for arm in arms3:
                hs = []
                for wsr in cfg3['wsrs_db']:
                    k = f'{cnr}|{wsr}'
                    grid.setdefault(k, {})[arm] = float(np.mean([r['cells'][k][arm]['hit'] for r in r1024]))
                    hs.append(grid[k][arm])
                mdr50[str(cnr)][arm] = interp_mdr50(cfg3['wsrs_db'], hs)
        # Core pooled (CNR in 20,25,30 x WSR in -22,-26,-30)
        core_keys = [f'{c}|{w}' for c in (20.0, 25.0, 30.0) for w in (-22.0, -26.0, -30.0)]
        per_seed = {arm: np.array([np.mean([r['cells'][k][arm]['hit'] for k in core_keys]) for r in r1024]) for arm in arms3}
        sb_dec_25 = float(np.mean([r['cells']['25.0|-26.0']['afdm_semiblind_probit']['dec_ok'] for r in r1024]))
        grid4096 = {f'30.0|{w}': {a: float(np.mean([r['cells'][f'30.0|{w}'][a]['hit'] for r in r4096]))
                                  for a in r4096[0]['cells'][f'30.0|{w}']} for w in cfg3['n4096_wsrs_db']}
        d_buss = boot_ci(100.0 * (per_seed['afdm_probit'] - per_seed['afdm_bussgang']), rng)
        d_cph = boot_ci(100.0 * (per_seed['afdm_probit'] - per_seed['sc_cphase_probit']), rng)
        d_cm = boot_ci(100.0 * (per_seed['afdm_probit'] - per_seed['afdm_cmean']), rng)
        mdr_gain_30 = mdr50['30.0']['afdm_bussgang'] - mdr50['30.0']['afdm_probit']
        sb_ratio = float(np.mean(per_seed['afdm_semiblind_probit']) / max(np.mean(per_seed['afdm_probit']), 1e-9))
        meta3 = json.loads((out / 'g03_run.json').read_text())
        v3 = ('PASS' if d_buss['point'] >= 25.0 and d_buss['ci95'][0] > 20.0 and mdr_gain_30 >= 4.0 and sb_ratio >= 0.90
              else 'KILL' if d_buss['point'] < 15.0 or mdr_gain_30 < 3.0 or sb_dec_25 < 0.80 else 'UNDETERMINED')
        summary['g03'] = dict(verdict=v3, null_gate_25db=meta3['null_gate_25db'], sb_decode_rate_25db=sb_dec_25,
                              pooled_hit={a: float(np.mean(per_seed[a])) for a in arms3},
                              diff_probit_minus_bussgang_pp=d_buss,
                              diff_probit_minus_sc_cphase_pp=d_cph,
                              diff_probit_minus_cmean_pp=d_cm,
                              mdr50_db=mdr50, mdr50_gain_30db=mdr_gain_30, sb_hit_ratio=sb_ratio,
                              grid_1024=grid, grid_4096=grid4096, core_hours=meta3['core_hours'])

    # --- Read g01 ---
    if (out / 'g01_rows.jsonl.gz').exists():
        rows1 = [json.loads(x) for x in gzip.open(out / 'g01_rows.jsonl.gz', 'rt')]
        arms1 = ('rep_naive', 'rep_1sic', 'rep_joint_lin', 'phase_code')
        prim_keys = [f'{rho}|{dm}|31.25|{wsr}' for rho in (0.2, 0.3) for dm in ('d_clean', 'd_gen') for wsr in (-16.0, -18.0)]
        ps1 = {a: np.array([np.mean([r['cells'][k]['arms'][a]['hit'] for k in prim_keys]) for r in rows1]) for a in arms1}
        # Also ghost-colocated subset (even seeds where ell_w == d_ghost)
        coloc_rows = [r for r in rows1 if r['seed'] % 2 == 0]
        ps1_coloc = {a: np.array([np.mean([r['cells'][k]['arms'][a]['hit'] for k in prim_keys]) for r in coloc_rows]) for a in arms1}
        d_vs_1sic = boot_ci(100.0 * (ps1['phase_code'] - ps1['rep_1sic']), rng)
        d_vs_jlin = boot_ci(100.0 * (ps1['phase_code'] - ps1['rep_joint_lin']), rng)
        d_vs_naive = boot_ci(100.0 * (ps1['phase_code'] - ps1['rep_naive']), rng)
        d_coloc_jlin = boot_ci(100.0 * (ps1_coloc['phase_code'] - ps1_coloc['rep_joint_lin']), rng)
        wide_keys = [f'{rho}|{dm}|45.0|{wsr}' for rho in (0.2, 0.3) for dm in ('d_clean', 'd_gen') for wsr in (-16.0, -18.0)]
        wide_hits = {a: float(np.mean([[r['cells'][k]['arms'][a]['hit'] for k in wide_keys] for r in rows1])) for a in arms1}
        best_rx_diff = d_vs_jlin if np.mean(ps1['rep_joint_lin']) >= np.mean(ps1['rep_1sic']) else d_vs_1sic
        v1 = ('PASS' if best_rx_diff['ci95'][1] >= 10.0 and best_rx_diff['ci95'][0] > 3.0
              else 'KILL' if best_rx_diff['ci95'][1] < 10.0 else 'UNDETERMINED')
        meta1 = json.loads((out / 'g01_run.json').read_text())
        summary['g01'] = dict(verdict=v1, noiseless_gate=meta1['noiseless_gate'],
                              primary_hit={a: float(np.mean(ps1[a])) for a in arms1},
                              coloc_hit={a: float(np.mean(ps1_coloc[a])) for a in arms1},
                              wide45_hit=wide_hits,
                              diff_pcode_minus_naive_pp=d_vs_naive,
                              diff_pcode_minus_1sic_pp=d_vs_1sic,
                              diff_pcode_minus_joint_lin_pp=d_vs_jlin,
                              diff_coloc_pcode_minus_joint_lin_pp=d_coloc_jlin,
                              core_hours=meta1['core_hours'])

    # --- Read g05 ---
    if (out / 'g05_rows.jsonl.gz').exists():
        rows5 = [json.loads(x) for x in gzip.open(out / 'g05_rows.jsonl.gz', 'rt')]
        partA_summary = {}
        for tag in rows5[0]['partA']:
            partA_summary[tag] = {
                arm: boot_ci([r['partA'][tag][arm] for r in rows5], rng)
                for arm in rows5[0]['partA'][tag]
            }
        snrs_B = [str(s) for s in CFG['g05']['partB_snrs']]
        arms_B = ('true_H', 'c16_rho05', 'c16_rho25', 'short_tdm_rho05', 'woodbury_em_rho05')
        per_snr_B = {
            s: {a: int(sum(r['partB'][s][a] for r in rows5)) for a in arms_B}
            for s in snrs_B
        }
        for s in snrs_B:
            per_snr_B[s]['mean_found_c16_05'] = float(np.mean([r['partB'][s]['found_c16_05'] for r in rows5]))
            per_snr_B[s]['mean_found_em_05'] = float(np.mean([r['partB'][s]['found_em_05'] for r in rows5]))
            per_snr_B[s]['mean_mae_unk_em_05'] = float(np.mean([r['partB'][s]['mae_unk_em_05'] for r in rows5]))
        tot_err = {a: np.array([sum(r['partB'][s][a] for s in snrs_B) for r in rows5], float) for a in arms_B}
        n_f = len(rows5)
        diff_c05 = boot_ci((tot_err['c16_rho05'] - tot_err['woodbury_em_rho05']) * n_f, rng)
        diff_tdm = boot_ci((tot_err['short_tdm_rho05'] - tot_err['woodbury_em_rho05']) * n_f, rng)
        diff_c25 = boot_ci((tot_err['c16_rho25'] - tot_err['woodbury_em_rho05']) * n_f, rng)
        mae_00 = partA_summary['50|400|0.0']['woodbury_em']
        mae_05 = partA_summary['50|400|0.5']['woodbury_em']
        c16_00 = partA_summary['50|400|0.0']['c16_pilot_varpro']['point']
        tdm_00 = partA_summary['50|400|0.0']['short_tdm_joint']['point']
        pass_A = (mae_00['point'] <= 0.040 and mae_00['ci95'][1] <= 0.045
                  and mae_05['point'] <= 0.040 and mae_05['ci95'][1] <= 0.045
                  and c16_00 / max(mae_00['point'], 1e-6) >= 2.0
                  and tdm_00 / max(mae_00['point'], 1e-6) >= 2.0)
        pass_B = (diff_c05['ci95'][0] > 0.0 and diff_tdm['ci95'][0] > 0.0 and diff_c25['ci95'][0] > 10.0)
        v5 = ('PASS' if pass_A and pass_B
              else 'KILL' if mae_00['point'] > 0.045 or diff_tdm['point'] <= 0 or diff_c25['point'] <= 0
              else 'UNDETERMINED')
        meta5 = json.loads((out / 'g05_run.json').read_text())
        summary['g05'] = dict(verdict=v5, frames=n_f, max_gate_rel=meta5['max_gate_rel'],
                              partA_mae=partA_summary, partB_errors_per_150=per_snr_B,
                              paired_excess_errors_c16_05_minus_em=diff_c05,
                              paired_excess_errors_tdm_05_minus_em=diff_tdm,
                              paired_excess_errors_c16_25_minus_em=diff_c25,
                              core_hours=meta5['core_hours'])

    (out / 'summary.json').write_text(json.dumps(summary, indent=1))
    print(json.dumps(summary, indent=1))


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('mode', choices=('smoke', 'g03', 'g01', 'g05', 'all', 'read'))
    ap.add_argument('--out', required=True)
    args = ap.parse_args()
    if args.mode == 'smoke':
        smoke(args.out)
    elif args.mode == 'all':
        run_g03(args.out)
        run_g01(args.out)
        run_g05(args.out)
        read_summary(args.out)
    elif args.mode == 'read':
        read_summary(args.out)
    else:
        dict(g03=run_g03, g01=run_g01, g05=run_g05)[args.mode](args.out)
