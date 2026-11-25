"""Stage A5 (STAGEA5_PROTOCOL.md): semi-blind Gaussian ML round-0 Doppler proxy check (true delays).

Reuses stageA.setup() and stageA4.{model, prepare, fims, crb_nu, metric} without editing frozen files.
Estimators (all given true delays l_i; gains are nuisance, never peeking at truth g_i or nu_i):
  PW = pilot-only (data treated as white noise): single-path MF init + 2 sweeps coordinate search
  SB = semi-blind Gaussian ML: start from PW, exact-gradient joint L-BFGS-B minimizing logdet C + e^H C^-1 e over (nu, Re g, Im g)
  KD = known data (sanity ceiling): full-signal MF init + 2 sweeps coordinate search
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import multiprocessing
from multiprocessing.connection import wait
import os
from pathlib import Path
import platform
import re
import resource
import shutil
import subprocess
import sys
import time
from typing import Any

import numpy as np
from scipy.linalg import LinAlgError, cho_factor, cho_solve, lapack
from scipy.optimize import minimize, minimize_scalar

HERE = Path(__file__).resolve().parent
EXP = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(EXP / 'huang_steelman_20261124'))

import hs_arms as ar  # noqa: E402

FRAMES = tuple(range(41000, 41100))
SCENARIOS = ('U', 'G')
RHOS = (100, 150, 200)
ALL_SNRS = (300, 400, 500)
DECIDE_SNR = 400
DECIDE_RHOS = (100, 150)
CAP = 0.375
PASS_THRESH = 0.08
OUTLIER_THRESH = 0.25
BOOT_DRAWS = 2000
BOOT_SEED = 20261125
WORKERS = 24
BUDGET_CAP_HOURS = 6.0
BUDGET_CAP_SEC = BUDGET_CAP_HOURS * 3600.0
COST_MARGIN = 1.3
OVERHEAD_HOURS = 0.10
BUDGET_EXIT_CODE = 124
NU_MIN, NU_MAX = -3.0, 3.0
CLK_TCK = os.sysconf(os.sysconf_names['SC_CLK_TCK']) if hasattr(os, 'sysconf') else 100

OWN_FILES = ('STAGEA5_PROTOCOL.md', 'stageA5.py', 'test_stageA5.py', 'stageA5_launch.sh')
STAGEA_PY_MD5 = '17be1c3e75e07fb9a4dec1b3774c54aa'
STAGEA4_PY_MD5 = '38790432341fc7dc68dfe3153405c48b'
STAGEA4_ROWS_MD5 = 'a662fa94be8f76a960a3f43413c95973'


def own_md5() -> dict[str, str]:
    return {name: ar.md5_file(HERE / name) for name in OWN_FILES}


def verify_pinned_deps() -> dict[str, str]:
    a_md5 = ar.md5_file(HERE / 'stageA.py')
    a4_md5 = ar.md5_file(HERE / 'stageA4.py')
    if a_md5 != STAGEA_PY_MD5:
        raise RuntimeError(f'stageA.py MD5 mismatch: {a_md5} != {STAGEA_PY_MD5}')
    if a4_md5 != STAGEA4_PY_MD5:
        raise RuntimeError(f'stageA4.py MD5 mismatch: {a4_md5} != {STAGEA4_PY_MD5}')
    return {'stageA.py': a_md5, 'stageA4.py': a4_md5}


def verify_freeze_commit_if_git(freeze_commit: str) -> bool:
    """Verify freeze commit exists and matches live OWN_FILES blobs when running inside a git checkout."""
    repo_root = HERE.parent.parent
    if not (repo_root / '.git').exists():
        return False
    chk = subprocess.run(
        ['git', '-C', str(repo_root), 'cat-file', '-e', f'{freeze_commit}^{{commit}}'],
        capture_output=True, text=True, check=False,
    )
    if chk.returncode != 0:
        raise RuntimeError(f'freeze_commit {freeze_commit} not found in git repo: {chk.stderr.strip()}')
    for name in OWN_FILES:
        rel = f'experiments/data_pilot_fer_20261121/{name}'
        blob = subprocess.run(
            ['git', '-C', str(repo_root), 'show', f'{freeze_commit}:{rel}'],
            capture_output=True, check=False,
        )
        if blob.returncode != 0:
            raise RuntimeError(f'{rel} missing from freeze_commit {freeze_commit}')
        if hashlib.md5(blob.stdout).hexdigest() != ar.md5_file(HERE / name):
            raise RuntimeError(f'{rel} working copy differs from freeze_commit {freeze_commit}')
    return True


def _used_cpu_seconds() -> float:
    ch = resource.getrusage(resource.RUSAGE_CHILDREN)
    return time.process_time() + ch.ru_utime + ch.ru_stime


def _active_pids_cpu(pids: list[int]) -> float:
    total = 0.0
    for pid in pids:
        try:
            raw = Path(f'/proc/{pid}/stat').read_text(encoding='utf-8')
            after = raw[raw.rfind(')') + 2:].split()
            total += (int(after[11]) + int(after[12])) / float(CLK_TCK)
        except OSError:
            pass
    return total


# --------------------------------------------------------------------------- Core math & estimators
def precompute_delay_geometry(delays: np.ndarray, n: int, c1: float) -> dict[str, Any]:
    """Precompute delay-dependent chirp phase cp_i[k] and shifted column indices matching stageA4.model."""
    k = np.arange(n, dtype=np.int64)
    l_arr = np.asarray(delays, dtype=np.int64)
    p = len(l_arr)
    cols = np.empty((p, n), dtype=np.int64)
    cp = np.empty((p, n), dtype=np.complex128)
    for i, li in enumerate(l_arr):
        cols[i] = (k - li) % n
        cp[i] = np.where(k < li, np.exp(2j * np.pi * c1 * (n * n + 2 * n * (k - li))), 1.0 + 0j)
    # Cross-index shift for T @ T^H: entry (k, (k - l_i + l_j) % n)
    cross_col = np.empty((p, p, n), dtype=np.int64)
    for i in range(p):
        for j in range(p):
            cross_col[i, j] = (k - l_arr[i] + l_arr[j]) % n
    return dict(n=n, p=p, k=k, k_norm=2j * np.pi * k / float(n), delays=l_arr, cols=cols, cp=cp, cross_col=cross_col)


def doppler_vectors(geom: dict[str, Any], nu: np.ndarray) -> np.ndarray:
    """Return c[p, n] where c[i, k] = cp_i[k] * exp(2j*pi*k*nu_i/n), exact match to stageA4.model."""
    nu_arr = np.asarray(nu, dtype=np.float64)
    return geom['cp'] * np.exp(nu_arr[:, None] * geom['k_norm'][None, :])


def build_basis_matrix(geom: dict[str, Any], c_mat: np.ndarray, x_t: np.ndarray) -> np.ndarray:
    """Build A[n, P] with column i = c_i(nu_i) * x_t[(k - l_i) % n]."""
    shifted = x_t[geom['cols']]  # [P, n]
    return (c_mat * shifted).T   # [n, P]


def build_covariance_fast(
    geom: dict[str, Any],
    c_mat: np.ndarray,
    g: np.ndarray,
    vd: float,
    sigma2: float,
) -> np.ndarray:
    """Build dense C = vd * T @ T^H + sigma2 * I using exact P^2 sparse diagonals (exact to ~1e-15)."""
    n, p = geom['n'], geom['p']
    k = geom['k']
    cross_col = geom['cross_col']
    C = np.zeros((n, n), dtype=np.complex128)
    diag_val = float(sigma2) + float(vd) * float(np.sum(np.abs(g) ** 2))
    C[k, k] = diag_val
    for i in range(p):
        gi_ci = (float(vd) * g[i]) * c_mat[i]
        for j in range(p):
            if i == j:
                continue
            m = cross_col[i, j]
            C[k, m] += gi_ci * np.conj(g[j] * c_mat[j, m])
    return C


def sb_nll_and_grad(
    theta: np.ndarray,
    geom: dict[str, Any],
    shifted_pt: np.ndarray,
    r: np.ndarray,
    vd: float,
    sigma2: float,
) -> tuple[float, np.ndarray]:
    """Exact Gaussian NLL = logdet C + e^H C^-1 e and analytic gradient over theta = (nu, Re g, Im g)."""
    p = geom['p']
    n = geom['n']
    k = geom['k']
    cross_col = geom['cross_col']
    nu = theta[:p]
    g = theta[p:2 * p] + 1j * theta[2 * p:3 * p]
    c_mat = doppler_vectors(geom, nu)
    C = build_covariance_fast(geom, c_mat, g, vd, sigma2)
    try:
        L, _ = cho_factor(C, lower=True, overwrite_a=True, check_finite=False)
    except LinAlgError:
        return 1e30, np.zeros(3 * p, dtype=np.float64)
    diag_L = np.diag(L).real
    if np.any(diag_L <= 0.0) or not np.isfinite(diag_L).all():
        return 1e30, np.zeros(3 * p, dtype=np.float64)
    logdet = 2.0 * float(np.sum(np.log(diag_L)))
    mu = np.sum((g[:, None] * c_mat) * shifted_pt, axis=0)
    e = r - mu
    alpha = cho_solve((L, True), e, check_finite=False)
    nll = logdet + float(np.vdot(e, alpha).real)
    if not np.isfinite(nll):
        return 1e30, np.zeros(3 * p, dtype=np.float64)

    Cinv, info = lapack.zpotri(L, lower=1, overwrite_c=0)
    if info != 0:
        return 1e30, np.zeros(3 * p, dtype=np.float64)
    Cinv = np.tril(Cinv) + np.tril(Cinv, -1).conj().T
    W = Cinv - np.outer(alpha, alpha.conj())

    grad = np.empty(3 * p, dtype=np.float64)
    for i in range(p):
        qi = np.zeros(n, dtype=np.complex128)
        for j in range(p):
            m = cross_col[i, j]
            qi += np.conj(g[j] * c_mat[j, m]) * W[m, k]
        s_i = (2.0 * float(vd)) * qi
        v_nu = g[i] * c_mat[i] * geom['k_norm']
        v_rg = c_mat[i]
        v_ig = 1j * c_mat[i]
        grad[i] = float(np.real(np.sum(s_i * v_nu)) - 2.0 * np.real(np.vdot(alpha, v_nu * shifted_pt[i])))
        grad[p + i] = float(np.real(np.sum(s_i * v_rg)) - 2.0 * np.real(np.vdot(alpha, v_rg * shifted_pt[i])))
        grad[2 * p + i] = float(np.real(np.sum(s_i * v_ig)) - 2.0 * np.real(np.vdot(alpha, v_ig * shifted_pt[i])))
    if not np.isfinite(grad).all():
        return 1e30, np.zeros(3 * p, dtype=np.float64)
    return nll, grad


def _mf_init(geom: dict[str, Any], x_t: np.ndarray, r: np.ndarray, step: float = 0.05) -> np.ndarray:
    """Single-path matched filter initialization over [-3, 3] with given grid step."""
    n_grid = int(round((NU_MAX - NU_MIN) / step)) + 1
    grid = np.linspace(NU_MIN, NU_MAX, n_grid)
    E = np.exp(np.outer(grid, geom['k_norm']))  # [G, n]
    nu_init = np.empty(geom['p'], dtype=np.float64)
    for i in range(geom['p']):
        base = geom['cp'][i] * x_t[geom['cols'][i]]
        # a_i(nu)^H r = sum_k conj(base[k]) * exp(-2j*pi*k*nu/n) * r[k] = conj(E) @ (conj(base) * r)
        corr = np.conj(E) @ (np.conj(base) * r)
        nu_init[i] = float(grid[int(np.argmax(np.abs(corr) ** 2))])
    return nu_init


def _ls_coordinate_search(
    geom: dict[str, Any],
    x_t: np.ndarray,
    r: np.ndarray,
    nu_start: np.ndarray,
    *,
    half_win: float = 0.5,
    grid_step: float = 0.05,
    xatol: float = 0.005,
    sweeps: int = 2,
) -> tuple[np.ndarray, np.ndarray]:
    """Coordinate search minimizing ||r - A(nu) g_LS||^2 (used by PW and KD)."""
    nu = np.asarray(nu_start, dtype=np.float64).copy()
    c_mat = doppler_vectors(geom, nu)
    A = build_basis_matrix(geom, c_mat, x_t)
    g, _, _, _ = np.linalg.lstsq(A, r, rcond=None)
    shifted = x_t[geom['cols']]  # [P, n]
    r_norm2 = float(np.vdot(r, r).real)

    for _ in range(sweeps):
        order = np.argsort(-np.abs(g))
        for idx in order:
            p_idx = int(idx)
            lo = max(NU_MIN, nu[p_idx] - half_win)
            hi = min(NU_MAX, nu[p_idx] + half_win)
            n_pts = max(3, int(round((hi - lo) / grid_step)) + 1)
            grid = np.linspace(lo, hi, n_pts)

            # Orthonormal basis Q_other for all other columns -> fast exact projection residual!
            other = [j for j in range(geom['p']) if j != p_idx]
            if other:
                Q_o, _ = np.linalg.qr(A[:, other], mode='reduced')
                r_perp = r - Q_o @ (Q_o.conj().T @ r)
                r_perp_norm2 = float(np.vdot(r_perp, r_perp).real)
            else:
                Q_o = None
                r_perp = r
                r_perp_norm2 = r_norm2

            base_p = geom['cp'][p_idx] * shifted[p_idx]

            def obj(val: float) -> float:
                col = base_p * np.exp(float(val) * geom['k_norm'])
                if Q_o is not None:
                    u = col - Q_o @ (Q_o.conj().T @ col)
                else:
                    u = col
                u_n2 = float(np.vdot(u, u).real)
                if u_n2 <= 1e-18:
                    return r_perp_norm2
                proj = abs(np.vdot(u, r_perp)) ** 2 / u_n2
                return max(0.0, r_perp_norm2 - proj)

            # Vectorized coarse grid evaluation
            cols_grid = base_p[:, None] * np.exp(np.outer(geom['k_norm'], grid))  # [n, G]
            if Q_o is not None:
                U_grid = cols_grid - Q_o @ (Q_o.conj().T @ cols_grid)
            else:
                U_grid = cols_grid
            u_n2_vec = np.sum(np.abs(U_grid) ** 2, axis=0)
            num_vec = np.abs(U_grid.conj().T @ r_perp) ** 2
            scores = np.where(u_n2_vec > 1e-18, np.maximum(0.0, r_perp_norm2 - num_vec / np.maximum(u_n2_vec, 1e-30)), r_perp_norm2)
            best_g = float(grid[int(np.argmin(scores))])

            b_lo = max(lo, best_g - grid_step)
            b_hi = min(hi, best_g + grid_step)
            res = minimize_scalar(obj, bounds=(b_lo, b_hi), method='bounded', options={'xatol': xatol})
            cand = float(res.x)
            nu[p_idx] = cand if obj(cand) <= obj(best_g) else best_g
            c_mat[p_idx] = geom['cp'][p_idx] * np.exp(nu[p_idx] * geom['k_norm'])
            A[:, p_idx] = c_mat[p_idx] * shifted[p_idx]
        g, _, _, _ = np.linalg.lstsq(A, r, rcond=None)
    if not (np.isfinite(nu).all() and np.isfinite(g).all()):
        raise FloatingPointError('Nonfinite output in LS coordinate search')
    return nu, g


def estimate_pw(geom: dict[str, Any], p_t: np.ndarray, r: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """PW: pilot-only estimator treating data as white noise."""
    nu0 = _mf_init(geom, p_t, r, step=0.05)
    return _ls_coordinate_search(geom, p_t, r, nu0, half_win=0.5, grid_step=0.05, xatol=0.005, sweeps=2)


def estimate_kd(
    geom: dict[str, Any],
    x_t: np.ndarray,
    r: np.ndarray,
    *,
    nu_init: np.ndarray | None = None,
    sweeps: int = 2,
    xatol: float = 1e-4,
) -> tuple[np.ndarray, np.ndarray]:
    """KD: known-data sanity ceiling."""
    nu0 = _mf_init(geom, x_t, r, step=0.05) if nu_init is None else np.asarray(nu_init, dtype=np.float64)
    return _ls_coordinate_search(geom, x_t, r, nu0, half_win=0.5, grid_step=0.05, xatol=xatol, sweeps=sweeps)


def estimate_sb(
    geom: dict[str, Any],
    p_t: np.ndarray,
    r: np.ndarray,
    vd: float,
    sigma2: float,
    nu_pw: np.ndarray,
    g_pw: np.ndarray,
    *,
    maxiter: int = 80,
    ftol: float = 1e-10,
) -> tuple[np.ndarray, np.ndarray]:
    """SB: semi-blind Gaussian ML minimizing logdet C + e^H C^-1 e jointly over (nu, Re g, Im g) via L-BFGS-B."""
    p = geom['p']
    nu0 = np.clip(np.asarray(nu_pw, dtype=np.float64), NU_MIN, NU_MAX)
    g0 = np.asarray(g_pw, dtype=np.complex128)
    theta0 = np.concatenate([nu0, g0.real, g0.imag])
    shifted_pt = p_t[geom['cols']]
    bounds = [(NU_MIN, NU_MAX)] * p + [(-10.0, 10.0)] * (2 * p)
    res = minimize(
        sb_nll_and_grad,
        theta0,
        args=(geom, shifted_pt, r, float(vd), float(sigma2)),
        method='L-BFGS-B',
        jac=True,
        bounds=bounds,
        options={'maxiter': maxiter, 'ftol': ftol, 'gtol': 1e-6},
    )
    nu = np.asarray(res.x[:p], dtype=np.float64)
    g = np.asarray(res.x[p:2 * p] + 1j * res.x[2 * p:3 * p], dtype=np.complex128)
    if not (np.isfinite(nu).all() and np.isfinite(g).all()):
        raise FloatingPointError('Nonfinite output in SB estimator')
    return nu, g


def doppler_metric(nu_hat: np.ndarray, nu_true: np.ndarray, g_true: np.ndarray) -> tuple[float, float, list[float]]:
    """A3/A4 power-weighted capped MAE + outlier (>0.25 bin) path fraction."""
    abs_err = np.abs(np.asarray(nu_hat, dtype=np.float64) - np.asarray(nu_true, dtype=np.float64))
    pw = np.abs(np.asarray(g_true, dtype=np.complex128)) ** 2
    val = float(np.sum(pw * np.minimum(abs_err, CAP)) / np.sum(pw))
    out_frac = float(np.mean(abs_err > OUTLIER_THRESH))
    return val, out_frac, abs_err.tolist()


# --------------------------------------------------------------------------- File-IPC worker helper
def _spawn_map(worker_fn, items: list[Any], max_workers: int, ipc_dir: Path, tag: str) -> list[Any]:
    n_workers = min(max_workers, max(1, len(items)))
    buckets = [items[i::n_workers] for i in range(n_workers)]
    mp_ctx = multiprocessing.get_context('spawn')
    out_files = []
    procs = []
    for wi, bucket in enumerate(buckets):
        in_f = ipc_dir / f'{tag}_in_{wi:02d}.json'
        out_f = ipc_dir / f'{tag}_out_{wi:02d}.json'
        in_f.write_text(json.dumps(bucket), encoding='utf-8')
        p = mp_ctx.Process(target=worker_fn, args=(str(in_f), str(out_f)))
        p.start()
        procs.append((wi, p))
        out_files.append(out_f)
    for wi, p in procs:
        p.join()
        code = p.exitcode
        p.close()
        if code != 0:
            raise RuntimeError(f'Worker {tag}/{wi} exited with code {code}')
    merged: list[tuple[int, Any]] = []
    for wi, out_f in enumerate(out_files):
        chunk = json.loads(out_f.read_text(encoding='utf-8'))
        for pos, val in enumerate(chunk):
            merged.append((wi + pos * n_workers, val))
    merged.sort(key=lambda x: x[0])
    return [v for _, v in merged]


def _load_runtime():
    ar.verify_frozen_extra_md5()
    import stageA  # noqa: E402
    import stageA4  # noqa: E402
    from physical import daft  # noqa: E402

    C = stageA.setup()
    return C, stageA4, daft


# --------------------------------------------------------------------------- Gates G1-G4
def _g3_worker(in_path: str, out_path: str):
    C, stageA4, daft = _load_runtime()
    st, ctx = C['stage3'], C['ctx']
    c1, c2 = ctx.system.c1, ctx.system.c2
    jobs = json.loads(Path(in_path).read_text(encoding='utf-8'))
    out = []
    for frame, s in jobs:
        raw, _, truth = st.observed(ctx, st.inputs(ctx, frame, s, 300), 300, 1200)
        y = np.asarray(raw['y'], dtype=np.complex128)
        p = np.asarray(raw['pilot'], dtype=np.complex128)
        d = np.asarray(raw['data'], dtype=np.complex128)
        sigma2 = float(raw['sigma2'])
        vd = float(np.mean(np.abs(d) ** 2))
        n = len(y)
        r = daft(y, c1, c2, True)
        p_t = daft(p, c1, c2, True)
        geom = precompute_delay_geometry(truth['l_i'], n, c1)
        nu_pw, g_pw = estimate_pw(geom, p_t, r)
        nu_sb, _ = estimate_sb(geom, p_t, r, vd, sigma2, nu_pw, g_pw)
        m_sb, out_sb, _ = doppler_metric(nu_sb, truth['k_real'], truth['g_i'])
        m_pw, _, _ = doppler_metric(nu_pw, truth['k_real'], truth['g_i'])
        P = stageA4.prepare(truth, n, c1)
        F = stageA4.fims(P, p, d, sigma2, n, c1, c2)
        crb_sb = stageA4.crb_nu(F['semiblind'], len(truth['l_i']))
        m_crb_sb = stageA4.metric(crb_sb, truth['g_i'])
        out.append(dict(frame=frame, scenario=s, sb=m_sb, pw=m_pw, sb_crb=m_crb_sb, outlier_sb=out_sb))
    ar.atomic_write_text(Path(out_path), json.dumps(out))


def _g4_worker(in_path: str, out_path: str):
    C, _, daft = _load_runtime()
    st, ctx = C['stage3'], C['ctx']
    c1, c2 = ctx.system.c1, ctx.system.c2
    jobs = json.loads(Path(in_path).read_text(encoding='utf-8'))
    out = []
    for frame, s, rho, snr in jobs:
        t0 = time.process_time()
        raw, _, truth = st.observed(ctx, st.inputs(ctx, frame, s, rho), rho, snr)
        y = np.asarray(raw['y'], dtype=np.complex128)
        p = np.asarray(raw['pilot'], dtype=np.complex128)
        d = np.asarray(raw['data'], dtype=np.complex128)
        sigma2 = float(raw['sigma2'])
        vd = float(np.mean(np.abs(d) ** 2))
        n = len(y)
        r = daft(y, c1, c2, True)
        p_t = daft(p, c1, c2, True)
        x_t = daft(p + d, c1, c2, True)
        geom = precompute_delay_geometry(truth['l_i'], n, c1)
        t_pw0 = time.process_time()
        nu_pw, g_pw = estimate_pw(geom, p_t, r)
        t_pw = time.process_time() - t_pw0
        t_sb0 = time.process_time()
        nu_sb, _ = estimate_sb(geom, p_t, r, vd, sigma2, nu_pw, g_pw)
        t_sb = time.process_time() - t_sb0
        t_kd0 = time.process_time()
        nu_kd, _ = estimate_kd(geom, x_t, r)
        t_kd = time.process_time() - t_kd0
        tot = time.process_time() - t0
        out.append(dict(key=[frame, s, rho, snr], total_cpu=tot, pw_cpu=t_pw, sb_cpu=t_sb, kd_cpu=t_kd))
    ar.atomic_write_text(Path(out_path), json.dumps(out))


def cmd_gate(args):
    print(sys.executable, flush=True)
    if platform.system() == 'Linux' and sys.executable != '/home/guoyikun/.conda/envs/AFDM/bin/python':
        raise RuntimeError(f'Wrong python interpreter: {sys.executable}')
    thread_env = ar.check_thread_env()
    started = time.monotonic()

    gate_path = args.out.resolve()
    gate_path.parent.mkdir(parents=True, exist_ok=True)
    if gate_path.exists():
        gate_path.unlink()

    C, stageA4, daft = _load_runtime()
    st, ctx = C['stage3'], C['ctx']
    c1, c2 = ctx.system.c1, ctx.system.c2

    # Verify pinned frozen dependencies and stageA4 rows archive
    deps_md5 = verify_pinned_deps()
    a4_rows_path = HERE / 'out' / 'stageA4' / 'rows.jsonl.gz'
    if ar.md5_file(a4_rows_path) != STAGEA4_ROWS_MD5:
        raise RuntimeError(f'stageA4 rows.jsonl.gz MD5 mismatch: {ar.md5_file(a4_rows_path)}')

    # G1: noiseless KD from truth + 0.1 bin on 4 keys + fast covariance exactness check
    g1_keys = (('U', 100, 400, 41200), ('G', 150, 400, 41201), ('U', 200, 400, 41202), ('G', 100, 400, 41203))
    g1_rows = []
    for s, rho, snr, frame in g1_keys:
        raw, _, truth = st.observed(ctx, st.inputs(ctx, frame, s, rho), rho, snr)
        p = np.asarray(raw['pilot'], dtype=np.complex128)
        d = np.asarray(raw['data'], dtype=np.complex128)
        y0 = np.asarray(raw['noiseless'], dtype=np.complex128)
        n = len(y0)
        r0 = daft(y0, c1, c2, True)
        x_t = daft(p + d, c1, c2, True)
        geom = precompute_delay_geometry(truth['l_i'], n, c1)
        nu_true = np.asarray(truth['k_real'], dtype=np.float64)
        nu_hat, _ = estimate_kd(geom, x_t, r0, nu_init=nu_true + 0.1, sweeps=2, xatol=1e-4)
        max_err = float(np.max(np.abs(nu_hat - nu_true)))

        # Verify fast covariance vs dense stageA4.model
        T_ref, _ = stageA4.model(truth, n, c1)
        vd = float(np.mean(np.abs(d) ** 2))
        s2 = float(raw['sigma2'])
        C_ref = vd * (T_ref @ T_ref.conj().T) + s2 * np.eye(n, dtype=np.complex128)
        c_mat = doppler_vectors(geom, nu_true)
        C_fast = build_covariance_fast(geom, c_mat, np.asarray(truth['g_i'], dtype=np.complex128), vd, s2)
        cov_err = float(np.linalg.norm(C_fast - C_ref) / np.linalg.norm(C_ref))
        g1_rows.append(dict(key=[s, rho, snr, frame], max_nu_err=max_err, cov_rel_err=cov_err))
    g1_pass = bool(all(x['max_nu_err'] < 1e-3 and x['cov_rel_err'] < 1e-13 for x in g1_rows))
    print(f'G1 {"PASS" if g1_pass else "FAIL"} max_nu_err={max(x["max_nu_err"] for x in g1_rows):.2e} cov_err={max(x["cov_rel_err"] for x in g1_rows):.2e}', flush=True)

    # G2: KD Monte Carlo at 12 dB, 100 noise draws on one key -> median var / CRB_known in [0.7, 1.5]
    raw_g2, _, truth_g2 = st.observed(ctx, st.inputs(ctx, 41200, 'U', 100), 100, 1200)
    p_g2 = np.asarray(raw_g2['pilot'], dtype=np.complex128)
    d_g2 = np.asarray(raw_g2['data'], dtype=np.complex128)
    y0_g2 = np.asarray(raw_g2['noiseless'], dtype=np.complex128)
    s2_g2 = float(raw_g2['sigma2'])
    n_g2 = len(y0_g2)
    r0_g2 = daft(y0_g2, c1, c2, True)
    xt_g2 = daft(p_g2 + d_g2, c1, c2, True)
    geom_g2 = precompute_delay_geometry(truth_g2['l_i'], n_g2, c1)
    nu_true_g2 = np.asarray(truth_g2['k_real'], dtype=np.float64)
    P_g2 = stageA4.prepare(truth_g2, n_g2, c1)
    F_g2 = stageA4.fims(P_g2, p_g2, d_g2, s2_g2, n_g2, c1, c2)
    crb_kd = stageA4.crb_nu(F_g2['known'], len(nu_true_g2))
    rng_g2 = np.random.default_rng(BOOT_SEED)
    errs_g2 = np.empty((100, len(nu_true_g2)), dtype=np.float64)
    for di in range(100):
        w = np.sqrt(s2_g2 / 2.0) * (rng_g2.standard_normal(n_g2) + 1j * rng_g2.standard_normal(n_g2))
        nu_h, _ = estimate_kd(geom_g2, xt_g2, r0_g2 + w, sweeps=2, xatol=1e-4)
        errs_g2[di] = nu_h - nu_true_g2
    var_ratio = np.var(errs_g2, axis=0, ddof=1) / crb_kd
    med_ratio = float(np.median(var_ratio))
    g2_pass = bool(0.7 <= med_ratio <= 1.5)
    print(f'G2 {"PASS" if g2_pass else "FAIL"} median var/CRB_known={med_ratio:.3f} per_path={[round(float(v), 3) for v in var_ratio]}', flush=True)

    # G3 (20 benign draws: frames 41200..41209 x U/G at rho=.30, 12 dB) & G4 (6 cost keys at 4 dB)
    tmp_root = Path(os.environ.get('TMPDIR', '/data/guoyikun/tmp'))
    ipc_dir = tmp_root / f'stageA5_gates_ipc_{os.getpid()}'
    ipc_dir.mkdir(parents=True, exist_ok=True)
    try:
        g3_jobs = [[f, s] for f in range(41200, 41210) for s in SCENARIOS]
        print('Running G3 (20 benign draws: rho=0.30, 12 dB)...', flush=True)
        g3_rows = _spawn_map(_g3_worker, g3_jobs, min(args.workers, 20), ipc_dir, 'g3')
        mean_sb = float(np.mean([x['sb'] for x in g3_rows]))
        mean_sb_crb = float(np.mean([x['sb_crb'] for x in g3_rows]))
        mean_pw = float(np.mean([x['pw'] for x in g3_rows]))
        sb_ratio = mean_sb / mean_sb_crb
        g3_pass = bool(sb_ratio <= 1.5)
        print(f'G3 {"PASS" if g3_pass else "FAIL"} mean_sb={mean_sb:.5f} mean_sb_crb={mean_sb_crb:.5f} ratio={sb_ratio:.3f} (mean_pw={mean_pw:.5f})', flush=True)

        g4_jobs = [[41220, 'U', rho, 400] for rho in RHOS] + [[41221, 'G', rho, 400] for rho in RHOS]
        print('Running G4 cost benchmark (6 keys at 4 dB)...', flush=True)
        g4_rows = _spawn_map(_g4_worker, g4_jobs, min(args.workers, 6), ipc_dir, 'g4')
    finally:
        shutil.rmtree(ipc_dir, ignore_errors=True)

    mean_key_cpu = float(np.mean([x['total_cpu'] for x in g4_rows]))
    candidates = []
    for snrs in ((300, 400, 500), (400,)):
        n_keys = len(FRAMES) * len(SCENARIOS) * len(RHOS) * len(snrs)
        raw_h = mean_key_cpu * n_keys / 3600.0 + OVERHEAD_HOURS
        marg_h = raw_h * COST_MARGIN
        candidates.append(dict(
            snrs=list(snrs),
            n_keys=n_keys,
            mean_cpu_sec_per_key=mean_key_cpu,
            raw_hours=raw_h,
            projected_hours_with_margin=marg_h,
            within_budget=bool(marg_h <= BUDGET_CAP_HOURS),
        ))
    selected = next((c for c in candidates if c['within_budget']), None)
    g4_pass = selected is not None
    all_passed = bool(g1_pass and g2_pass and g3_pass and g4_pass)
    gate_cpu_h = _used_cpu_seconds() / 3600.0

    payload = dict(
        _argv=sys.argv,
        _config=dict(
            python_executable=sys.executable,
            threads=thread_env,
            workers=args.workers,
            own_md5=own_md5(),
            stageA_py_md5=deps_md5['stageA.py'],
            stageA4_py_md5=deps_md5['stageA4.py'],
            stageA4_rows_md5=STAGEA4_ROWS_MD5,
        ),
        all_passed=all_passed,
        selected=selected,
        G1=dict(passed=g1_pass, rows=g1_rows),
        G2=dict(passed=g2_pass, draws=100, median_var_over_crb=med_ratio, per_path_var_over_crb=var_ratio.tolist()),
        G3=dict(passed=g3_pass, draws=len(g3_rows), mean_sb=mean_sb, mean_sb_crb=mean_sb_crb, ratio=sb_ratio, mean_pw=mean_pw, rows=g3_rows),
        G4=dict(passed=g4_pass, budget_cap_core_hours=BUDGET_CAP_HOURS, margin=COST_MARGIN, candidates=candidates, samples=g4_rows),
        gate_cpu_hours=gate_cpu_h,
        gate_wall_seconds=time.monotonic() - started,
    )
    ar.atomic_write_text(gate_path, json.dumps(payload, indent=2, allow_nan=False) + '\n')
    print(f'GATE_STATUS={"PASS" if all_passed else "FAIL"} selected={selected} cpu_hours={gate_cpu_h:.4f}', flush=True)
    sys.exit(0 if all_passed else 1)


# --------------------------------------------------------------------------- Main run & readout
def _run_shard_worker(shard_idx: int, draws: list[tuple[int, str]], snrs: tuple[int, ...], raw_dir: Path):
    C, _, daft = _load_runtime()
    st, ctx = C['stage3'], C['ctx']
    c1, c2 = ctx.system.c1, ctx.system.c2
    lines: list[str] = []
    for frame, s in draws:
        for rho in RHOS:
            base = st.inputs(ctx, frame, s, rho)
            for snr in snrs:
                raw, _, truth = st.observed(ctx, base, rho, snr)
                y = np.asarray(raw['y'], dtype=np.complex128)
                p = np.asarray(raw['pilot'], dtype=np.complex128)
                d = np.asarray(raw['data'], dtype=np.complex128)
                sigma2 = float(raw['sigma2'])
                vd = float(np.mean(np.abs(d) ** 2))
                n = len(y)
                r = daft(y, c1, c2, True)
                p_t = daft(p, c1, c2, True)
                x_t = daft(p + d, c1, c2, True)
                geom = precompute_delay_geometry(truth['l_i'], n, c1)

                nu_pw, g_pw = estimate_pw(geom, p_t, r)
                nu_sb, _ = estimate_sb(geom, p_t, r, vd, sigma2, nu_pw, g_pw)
                nu_kd, _ = estimate_kd(geom, x_t, r)

                m_pw, o_pw, e_pw = doppler_metric(nu_pw, truth['k_real'], truth['g_i'])
                m_sb, o_sb, e_sb = doppler_metric(nu_sb, truth['k_real'], truth['g_i'])
                m_kd, o_kd, e_kd = doppler_metric(nu_kd, truth['k_real'], truth['g_i'])

                lines.append(json.dumps(dict(
                    frame=frame, scenario=s, rho=rho, snr=snr,
                    metric=dict(PW=m_pw, SB=m_sb, KD=m_kd),
                    outlier_frac=dict(PW=o_pw, SB=o_sb, KD=o_kd),
                    abs_err=dict(PW=e_pw, SB=e_sb, KD=e_kd),
                ), allow_nan=False) + '\n')

    final_path = raw_dir / f'rows_shard{shard_idx:03d}.jsonl.gz'
    part_path = final_path.with_suffix(final_path.suffix + f'.{os.getpid()}.part')
    with part_path.open('wb') as raw_fh:
        with gzip.GzipFile(filename='', mode='wb', fileobj=raw_fh, mtime=0) as gz:
            for ln in lines:
                gz.write(ln.encode('utf-8'))
        raw_fh.flush()
        os.fsync(raw_fh.fileno())
    os.replace(part_path, final_path)
    print(f'Shard {shard_idx:03d} done ({len(lines)} keys)', flush=True)


def verdict_a5(ci_lo: float, ci_hi: float) -> str:
    if ci_hi <= PASS_THRESH:
        return 'PASS'
    if ci_lo > PASS_THRESH:
        return 'FAIL'
    return 'BORDERLINE'


def analyze_stageA5(
    rows: list[dict[str, Any]],
    a4_rows: list[dict[str, Any]],
    snrs: tuple[int, ...],
    a3_actual_pilot: dict[str, float],
    *,
    boot_draws: int = BOOT_DRAWS,
    boot_seed: int = BOOT_SEED,
) -> dict[str, Any]:
    """Frozen Stage A5 readout with paired frame-cluster bootstrap over physical frames (binding U/G and all rhos)."""
    frames = sorted({int(r['frame']) for r in rows})
    fi = {f: i for i, f in enumerate(frames)}
    si_scen = {s: i for i, s in enumerate(SCENARIOS)}
    n_frames = len(frames)
    n_scen = len(SCENARIOS)
    n_draws = n_frames * n_scen
    ests = ('PW', 'SB', 'KD')

    M = np.full((len(ests), len(RHOS), len(snrs), n_frames, n_scen), np.nan, dtype=np.float64)
    O = np.full((len(ests), len(RHOS), len(snrs), n_frames, n_scen), np.nan, dtype=np.float64)
    for r in rows:
        ri = RHOS.index(int(r['rho']))
        si = snrs.index(int(r['snr']))
        f_idx = fi[int(r['frame'])]
        sc_idx = si_scen[r['scenario']]
        for ei, e in enumerate(ests):
            M[ei, ri, si, f_idx, sc_idx] = float(r['metric'][e])
            O[ei, ri, si, f_idx, sc_idx] = float(r['outlier_frac'][e])
    if np.isnan(M).any():
        raise RuntimeError('Incomplete Stage A5 metric grid')

    # Pair with Stage A4 CRB metrics on the exact same frames x scenarios
    a4_bounds = ('pilot_white', 'pilot', 'semiblind', 'known')
    B = np.full((len(a4_bounds), len(RHOS), len(snrs), n_frames, n_scen), np.nan, dtype=np.float64)
    for r in a4_rows:
        snr = int(r['snr'])
        if snr not in snrs:
            continue
        f_val = int(r['frame'])
        if f_val not in fi or r['scenario'] not in si_scen:
            continue
        ri = RHOS.index(int(r['rho']))
        si = snrs.index(snr)
        f_idx = fi[f_val]
        sc_idx = si_scen[r['scenario']]
        for bi, bname in enumerate(a4_bounds):
            B[bi, ri, si, f_idx, sc_idx] = float(r['metric'][bname])
    if np.isnan(B).any():
        raise RuntimeError('Incomplete Stage A4 paired CRB grid')

    # Paired bootstrap over physical frames (each frame binds U and G jointly across all rhos)
    rng = np.random.default_rng(boot_seed)
    boot_fidx = rng.integers(0, n_frames, size=(boot_draws, n_frames))
    M_frame = M.mean(axis=-1)  # (ests, rhos, snrs, n_frames); mean over frames equals mean over all draws

    # Primary E = min_{rho in {100,150}} mean(SB at 4 dB)
    si_400 = snrs.index(DECIDE_SNR)
    ei_sb = ests.index('SB')
    ri_100, ri_150 = RHOS.index(100), RHOS.index(150)
    sb_100_f = M_frame[ei_sb, ri_100, si_400]
    sb_150_f = M_frame[ei_sb, ri_150, si_400]
    mean_100 = float(sb_100_f.mean())
    mean_150 = float(sb_150_f.mean())
    E_pt = min(mean_100, mean_150)
    E_rho = 100 if mean_100 <= mean_150 else 150
    b_100 = sb_100_f[boot_fidx].mean(axis=1)
    b_150 = sb_150_f[boot_fidx].mean(axis=1)
    E_boot = np.minimum(b_100, b_150)
    E_lo, E_hi = (float(x) for x in np.percentile(E_boot, [2.5, 97.5]))
    verdict = verdict_a5(E_lo, E_hi)

    table: dict[str, dict[str, Any]] = {}
    for ei, e in enumerate(ests):
        table[e] = {}
        for ri, rho in enumerate(RHOS):
            for si, snr in enumerate(snrs):
                v_all = M[ei, ri, si].reshape(-1)
                v_f = M_frame[ei, ri, si]
                bm = v_f[boot_fidx].mean(axis=1)
                ci = [float(x) for x in np.percentile(bm, [2.5, 97.5])]
                table[e][f'{rho}_{snr}'] = dict(
                    mean=float(v_all.mean()),
                    median=float(np.median(v_all)),
                    ci95=ci,
                    outlier_gt_0p25_frac=float(O[ei, ri, si].mean()),
                )

    crb_table: dict[str, dict[str, float]] = {}
    for bi, bname in enumerate(a4_bounds):
        crb_table[bname] = {
            f'{rho}_{snr}': float(B[bi, ri, si].mean())
            for ri, rho in enumerate(RHOS) for si, snr in enumerate(snrs)
        }

    efficiency: dict[str, Any] = {}
    for ri, rho in enumerate(RHOS):
        key4 = f'{rho}_{DECIDE_SNR}'
        sb_m = table['SB'][key4]['mean']
        sb_c = crb_table['semiblind'][key4]
        pw_m = table['PW'][key4]['mean']
        pw_c = crb_table['pilot_white'][key4]
        kd_m = table['KD'][key4]['mean']
        kd_c = crb_table['known'][key4]
        efficiency[str(rho)] = dict(
            sb_over_sb_crb=float(sb_m / sb_c),
            pw_over_pilot_white_crb=float(pw_m / pw_c),
            kd_over_known_crb=float(kd_m / kd_c),
            pw_4db_mean=pw_m,
            stageA_actual_pilot_4_5db=float(a3_actual_pilot[str(rho)]),
            pw_over_stageA_actual=float(pw_m / float(a3_actual_pilot[str(rho)])),
        )

    return dict(
        frames=n_frames,
        draws=n_draws,
        snrs=list(snrs),
        boot_unit='physical_frame_cluster',
        boot_draws=boot_draws,
        boot_seed=boot_seed,
        primary=dict(
            E_point=E_pt,
            E_ci95=[E_lo, E_hi],
            best_rho=E_rho,
            threshold=PASS_THRESH,
            verdict=verdict,
        ),
        table=table,
        crb_mean=crb_table,
        efficiency_4db=efficiency,
    )


def render_results_md(res: dict[str, Any]) -> str:
    a = res['analysis']
    p = a['primary']
    lines = [
        '# Stage A5 Results: Semi-Blind Round-0 Doppler Proxy Check',
        '',
        f'- Freeze commit: `{res["_config"]["freeze_commit"]}`',
        f'- Draws: **{a["draws"]}** (frames `41000–41099` × U/G), SNRs: `{a["snrs"]}`',
        f'- Runtime: **{res["runtime"]["total_core_hours"]:.4f} core-hours** (cap 6.0 h, wall {res["runtime"]["wall_seconds"]:.1f} s)',
        '',
        '## Primary Verdict (Pre-Registered, SNR = 4 dB)',
        '',
        f'- `E = min_{{ρ ∈ {{0.10, 0.15}}}} mean(SB)` = **{p["E_point"]:.4f} bin** (at ρ={p["best_rho"]/1000:.2f}), '
        f'95% CI **[{p["E_ci95"][0]:.4f}, {p["E_ci95"][1]:.4f}] bin** → **{p["verdict"]}** (threshold `0.08` bin)',
        '',
        '## 4 dB Summary Table (Power-Weighted Capped MAE, bin; 200 Draws)',
        '',
        '| ρ | PW mean [med] | SB mean [med] (95% CI) | KD mean [med] | SB-CRB | PW-CRB | SB Eff | PW Eff | SB Outlier >0.25 | Stage A Actual (4–5 dB) |',
        '|---:|---|---|---|---:|---:|---:|---:|---:|---:|',
    ]
    for rho in RHOS:
        k4 = f'{rho}_400'
        pw = a['table']['PW'][k4]
        sb = a['table']['SB'][k4]
        kd = a['table']['KD'][k4]
        eff = a['efficiency_4db'][str(rho)]
        lines.append(
            f'| {rho/1000:.2f} | {pw["mean"]:.4f} [{pw["median"]:.4f}] | '
            f'**{sb["mean"]:.4f}** [{sb["median"]:.4f}] ([{sb["ci95"][0]:.4f}, {sb["ci95"][1]:.4f}]) | '
            f'{kd["mean"]:.4f} [{kd["median"]:.4f}] | '
            f'{a["crb_mean"]["semiblind"][k4]:.4f} | {a["crb_mean"]["pilot_white"][k4]:.4f} | '
            f'{eff["sb_over_sb_crb"]:.2f}× | {eff["pw_over_pilot_white_crb"]:.2f}× | '
            f'{100*sb["outlier_gt_0p25_frac"]:.2f}% | {eff["stageA_actual_pilot_4_5db"]:.4f} |'
        )
    return '\n'.join(lines) + '\n'


def cmd_run(args):
    print(sys.executable, flush=True)
    if platform.system() == 'Linux' and sys.executable != '/home/guoyikun/.conda/envs/AFDM/bin/python':
        raise RuntimeError(f'Wrong python interpreter: {sys.executable}')
    ar.check_thread_env()
    if not re.fullmatch(r'[0-9a-f]{40}', args.freeze_commit):
        raise ValueError(f'freeze-commit must be 40-char hex SHA, got {args.freeze_commit!r}')
    if not 1 <= args.workers <= 32:
        raise ValueError('workers must be in 1..32')
    deps_md5 = verify_pinned_deps()
    freeze_git_ok = verify_freeze_commit_if_git(args.freeze_commit)

    gate_path = args.gate.resolve()
    gate_bytes = gate_path.read_bytes()
    gate_md5 = hashlib.md5(gate_bytes).hexdigest()
    gate = json.loads(gate_bytes.decode('utf-8'))
    if not gate.get('all_passed') or not gate.get('selected'):
        raise RuntimeError('Refusing to run without passing stageA5_gate.json')
    live_own = own_md5()
    if gate['_config']['own_md5'] != live_own:
        raise RuntimeError('gate.json own_md5 mismatch; re-run gates')
    if gate['_config']['stageA_py_md5'] != deps_md5['stageA.py'] or gate['_config']['stageA4_py_md5'] != deps_md5['stageA4.py']:
        raise RuntimeError('Reused stageA/stageA4 MD5 mismatch vs gate.json')

    snrs = tuple(int(s) for s in gate['selected']['snrs'])
    out_dir = args.out.resolve()
    raw_dir = out_dir / 'raw'
    raw_dir.mkdir(parents=True, exist_ok=True)
    if list(raw_dir.glob('rows_shard*.jsonl*')):
        raise RuntimeError(f'Refusing to overwrite existing shards in {raw_dir}')

    a4_rows_path = HERE / 'out' / 'stageA4' / 'rows.jsonl.gz'
    if ar.md5_file(a4_rows_path) != STAGEA4_ROWS_MD5:
        raise RuntimeError('stageA4 rows.jsonl.gz MD5 mismatch')

    wall_start = time.monotonic()
    all_draws = [(f, s) for f in FRAMES for s in SCENARIOS]
    n_shards = args.workers
    mp_ctx = multiprocessing.get_context('spawn')
    running = {}
    budget_hit = False
    print(f'Launching Stage A5: {len(all_draws)} draws x {len(RHOS)} rhos x {len(snrs)} SNRs ({snrs}) on {n_shards} workers...', flush=True)
    try:
        for idx in range(n_shards):
            sub_draws = all_draws[idx::n_shards]
            p = mp_ctx.Process(target=_run_shard_worker, args=(idx, sub_draws, snrs, raw_dir))
            p.start()
            running[p.sentinel] = (idx, p)
        while running:
            ready = wait(running, timeout=5.0)
            for r in ready:
                idx, p = running.pop(r)
                p.join()
                code = p.exitcode
                p.close()
                if code != 0:
                    raise RuntimeError(f'Shard {idx:03d} failed with exit code {code}')
            live_cpu = _used_cpu_seconds() + _active_pids_cpu([p.pid for _, p in running.values() if p.pid])
            if live_cpu >= BUDGET_CAP_SEC - 360.0:
                budget_hit = True
                break
    finally:
        for _, p in running.values():
            p.terminate()
        for _, p in running.values():
            p.join()
            p.close()
    if budget_hit or _used_cpu_seconds() >= BUDGET_CAP_SEC:
        print(f'STOPPED_BUDGET ({_used_cpu_seconds()/3600:.3f} core-hours)', flush=True)
        sys.exit(BUDGET_EXIT_CODE)

    # Merge shard MD5s and load all rows
    raw_md5 = {}
    rows = []
    for idx in range(n_shards):
        sp = raw_dir / f'rows_shard{idx:03d}.jsonl.gz'
        raw_md5[sp.name] = ar.md5_file(sp)
        with gzip.open(sp, 'rt', encoding='utf-8') as fh:
            for line in fh:
                rows.append(json.loads(line))
    ar.atomic_write_text(
        out_dir / 'REMOTE_ROWS_MD5.txt',
        ''.join(f'{d}  {n}\n' for n, d in sorted(raw_md5.items())),
    )

    a4_rows = [json.loads(ln) for ln in gzip.open(a4_rows_path, 'rt', encoding='utf-8')]
    a3_actual = json.loads((HERE / 'out' / 'stageA3' / 'results.json').read_text(encoding='utf-8'))['r0_doppler_err_snr4_5']['delay']
    analysis = analyze_stageA5(rows, a4_rows, snrs, a3_actual)

    total_cpu_h = _used_cpu_seconds() / 3600.0
    if total_cpu_h >= BUDGET_CAP_HOURS:
        print(f'STOPPED_BUDGET after analysis ({total_cpu_h:.4f} core-hours)', flush=True)
        sys.exit(BUDGET_EXIT_CODE)

    results = dict(
        _argv=sys.argv,
        _config=dict(
            freeze_commit=args.freeze_commit,
            freeze_commit_git_verified=freeze_git_ok,
            python_executable=sys.executable,
            own_md5=live_own,
            stageA_py_md5=deps_md5['stageA.py'],
            stageA4_py_md5=deps_md5['stageA4.py'],
            gate_md5=gate_md5,
            snrs=list(snrs),
            rhos=list(RHOS),
            frames=[FRAMES[0], FRAMES[-1]],
            draws=len(all_draws),
            raw_output_dir=str(raw_dir),
            raw_rows_md5=raw_md5,
            stageA4_rows_md5=STAGEA4_ROWS_MD5,
        ),
        gates=dict(
            all_passed=gate['all_passed'],
            selected=gate['selected'],
            G2_median_var_over_crb=gate['G2']['median_var_over_crb'],
            G3_sb_over_crb_ratio=gate['G3']['ratio'],
        ),
        runtime=dict(
            total_core_hours=total_cpu_h,
            wall_seconds=time.monotonic() - wall_start,
            cpu_cap_core_hours=BUDGET_CAP_HOURS,
        ),
        analysis=analysis,
    )
    ar.atomic_write_text(out_dir / 'results.json', json.dumps(results, indent=2, allow_nan=False) + '\n')
    ar.atomic_write_text(out_dir / 'RESULTS.md', render_results_md(results))
    p = analysis['primary']
    print(
        f'STAGEA5_DONE verdict={p["verdict"]} E={p["E_point"]:.4f} '
        f'ci=[{p["E_ci95"][0]:.4f}, {p["E_ci95"][1]:.4f}] rho={p["best_rho"]} '
        f'cpu_hours={total_cpu_h:.4f}',
        flush=True,
    )


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest='mode', required=True)
    g = sub.add_parser('gate')
    g.add_argument('--out', type=Path, required=True)
    g.add_argument('--workers', type=int, default=16)

    r = sub.add_parser('run')
    r.add_argument('--gate', type=Path, required=True)
    r.add_argument('--out', type=Path, required=True)
    r.add_argument('--freeze-commit', required=True)
    r.add_argument('--workers', type=int, default=WORKERS)

    args = ap.parse_args()
    dict(gate=cmd_gate, run=cmd_run)[args.mode](args)


if __name__ == '__main__':
    main()
