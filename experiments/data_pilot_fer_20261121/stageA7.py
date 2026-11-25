"""Stage A7 (STAGEA7_PROTOCOL.md): decisive diagnosis of round-0 semi-blind Doppler sidelobe lock.

Compares (a) SEARCH vs (b) MODEL vs (c) INFO vs UNCLEAR on the 38 unseen Stage A6 4.5-5.0 dB
SBdop final failures (strictly gated on 4.0 dB dev keys prior to freeze).
Also exposes exact cyclic-banded block-Takahashi NLL/gradient (`prepare_fast_geom`,
`sb_nll_only_fast`, `sb_nll_and_grad_fast`) and truth-free global semi-blind estimator
(`estimate_sb_global`) over the identical domain [-3, 3]^P x [-10, 10]^{2P} as Stage A5.
"""
from __future__ import annotations

import argparse
from collections import Counter
import fnmatch
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
from scipy.linalg import cho_factor, cho_solve, cholesky_banded, solve_triangular
from scipy.linalg.lapack import ztbtrs
from scipy.optimize import minimize, minimize_scalar

HERE = Path(__file__).resolve().parent
EXP = HERE.parent
HUANG_DIR = EXP / 'huang_steelman_20261124'
SAMEFRAME_HG_DIR = EXP / 'sameframe_hg_20261124'

sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HUANG_DIR))
sys.path.insert(0, str(SAMEFRAME_HG_DIR))

import hs_arms as ar  # noqa: E402

DEV_SNR = 400
CONF_SNRS = (450, 500)
EXPECTED_CONF_N = 38
NU_MIN, NU_MAX = -3.0, 3.0
GAIN_MIN, GAIN_MAX = -10.0, 10.0
BOX_HALF = 0.25
OUTLIER_THRESH = 0.25

BOOT_DRAWS = 2000
BOOT_SEED = 20261125

WORKERS = 28
STAGE_BUDGET_HOURS = 1.0
STAGE_BUDGET_SEC = STAGE_BUDGET_HOURS * 3600.0
COST_MARGIN = 1.3
OVERHEAD_HOURS = 0.05
BUDGET_EXIT_CODE = 124
CLK_TCK = os.sysconf(os.sysconf_names['SC_CLK_TCK']) if hasattr(os, 'sysconf') else 100

OWN_FILES = ('STAGEA7_PROTOCOL.md', 'stageA7.py', 'test_stageA7.py', 'stageA7_launch.sh')
PINNED_CODE_MD5 = {
    'data_pilot_fer_20261121/stageA.py': '17be1c3e75e07fb9a4dec1b3774c54aa',
    'data_pilot_fer_20261121/stageA2.py': '01a72e6942ec39de99c0e788b3b5b0a9',
    'data_pilot_fer_20261121/stageA3.py': '305645c21bf13b1bc35ec300aa1bcbb2',
    'data_pilot_fer_20261121/stageA5.py': '073b76973298fbd58ecb0ef38953c97d',
    'data_pilot_fer_20261121/stageA6.py': 'e7e42f0f941613d997c4f71b01b09777',
    'sameframe_hg_20261124/sameframe.py': '01197778b2ec3cf7f37719ca3b192152',
    'huang_steelman_20261124/hs_arms.py': 'a43f2934c085bde1b69f929fddf06bf6',
    'huang_steelman_20261124/hs_analysis.py': '864b8b7510872c33dc60fc725c57a45d',
}
ARCHIVE_SPECS = {
    'stageA2': (
        HERE / 'out' / 'stageA2' / 'REMOTE_ROWS_MD5.txt',
        HERE / 'out' / 'stageA2',
        '5c2544bcf9f1ba794cff107fcf7c4e282dec5d9b09be34f438c213ceda797354',
        'rows_shard*.jsonl.gz',
    ),
    'stageA6': (
        HERE / 'out' / 'stageA6' / 'REMOTE_ROWS_MD5.txt',
        HERE / 'out' / 'stageA6' / 'raw',
        'ab0c564400ea009a948824a392449686cb3ccd38dd7fa1f4a8f758be3a2b9f4b',
        'rows_shard*.jsonl.gz',
    ),
}


def own_md5() -> dict[str, str]:
    return {name: ar.md5_file(HERE / name) for name in OWN_FILES}


def verify_pinned_code() -> dict[str, str]:
    out: dict[str, str] = {}
    for rel, expected in PINNED_CODE_MD5.items():
        actual = ar.md5_file(EXP / rel)
        if actual != expected:
            raise RuntimeError(f'Pinned dependency MD5 mismatch for {rel}: {actual} != {expected}')
        out[rel] = actual
    return out


def verify_archive(name: str) -> dict[str, str]:
    manifest_path, shard_dir, exp_sha, glob_pat = ARCHIVE_SPECS[name]
    got_sha = ar.sha256_file(manifest_path)
    if got_sha != exp_sha:
        raise RuntimeError(f'{name} manifest SHA-256 mismatch: {got_sha} != {exp_sha}')
    expected: dict[str, str] = {}
    for line in manifest_path.read_text(encoding='utf-8').splitlines():
        if not line.strip():
            continue
        digest, fname = line.split()
        p = shard_dir / fname
        if not p.is_file():
            raise FileNotFoundError(f'Missing {name} shard {p}')
        actual = ar.md5_file(p)
        if actual != digest:
            raise RuntimeError(f'{name} shard MD5 mismatch {p}: {actual} != {digest}')
        expected[fname] = actual
    disk = {p.name for p in shard_dir.glob(glob_pat)}
    expected_matched = {f for f in expected if fnmatch.fnmatch(f, glob_pat)}
    if disk != expected_matched:
        raise RuntimeError(f'{name} shard set mismatch on disk: {sorted(disk ^ expected_matched)}')
    return expected


def verify_all_archives(names: tuple[str, ...] = ('stageA2', 'stageA6')) -> dict[str, dict[str, str]]:
    return {name: verify_archive(name) for name in names}


def verify_freeze_commit_if_git(freeze_commit: str, live_own: dict[str, str]) -> bool:
    repo_root = EXP.parent
    probe = subprocess.run(
        ['git', '-C', str(repo_root), 'rev-parse', '--is-inside-work-tree'],
        capture_output=True, text=True, check=False,
    )
    if probe.returncode != 0 or probe.stdout.strip() != 'true':
        return False
    chk = subprocess.run(
        ['git', '-C', str(repo_root), 'cat-file', '-e', f'{freeze_commit}^{{commit}}'],
        capture_output=True, text=True, check=False,
    )
    if chk.returncode != 0:
        raise RuntimeError(f'freeze_commit {freeze_commit} not found in git repo: {chk.stderr.strip()}')
    top = Path(subprocess.run(
        ['git', '-C', str(repo_root), 'rev-parse', '--show-toplevel'],
        capture_output=True, text=True, check=True,
    ).stdout.strip())
    rel_dir = HERE.relative_to(top)
    for name, exp_md5 in live_own.items():
        blob = subprocess.run(
            ['git', '-C', str(repo_root), 'show', f'{freeze_commit}:{rel_dir.as_posix()}/{name}'],
            capture_output=True, check=False,
        )
        if blob.returncode != 0:
            raise RuntimeError(f'{name} missing from freeze_commit {freeze_commit}')
        if hashlib.md5(blob.stdout).hexdigest() != exp_md5:
            raise RuntimeError(f'Live {name} differs from freeze_commit {freeze_commit}')
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


# --------------------------------------------------------------------------- Fast exact cyclic-banded SB NLL & gradient
def prepare_fast_geom(geom: dict[str, Any]) -> dict[str, Any]:
    """Precompute cyclic-banded block-tridiagonal index maps and scratch buffers (exact match to stageA5)."""
    n, p = int(geom['n']), int(geom['p'])
    delays = np.asarray(geom['delays'], dtype=np.int64)
    B = int(delays.max() - delays.min()) if p > 0 else 0
    b_blk = max(B, 64)
    if B == 0 or b_blk >= n // 3 or (n - B) // b_blk < 3:
        return dict(geom, fast_ok=False)
    N1 = n - B
    n_full = N1 // b_blk
    rem = N1 % b_blk
    sizes = [b_blk] * (n_full - 1) + [b_blk + rem]
    M = len(sizes)
    starts = np.cumsum([0] + sizes[:-1]).tolist()
    ends = np.cumsum(sizes).tolist()
    k = geom['k']
    pair_ops = []
    for i in range(p):
        for j in range(p):
            if i == j:
                continue
            m = geom['cross_col'][i, j]
            mk_ab = (k < N1) & (m < N1) & (k >= m)
            k_ab = k[mk_ab]
            m_ab = m[mk_ab]
            d_ab = k_ab - m_ab
            mk_12 = (k < N1) & (m >= N1)
            k_12 = k[mk_12]
            m_12 = m[mk_12]
            c_12 = m_12 - N1
            mk_22 = (k >= N1) & (m >= N1)
            k_22 = k[mk_22]
            m_22 = m[mk_22]
            r_22 = k_22 - N1
            c_22 = m_22 - N1
            pair_ops.append((i, j, k_ab, m_ab, d_ab, k_12, m_12, c_12, k_22, m_22, r_22, c_22))
    return dict(
        geom,
        fast_ok=True,
        B=B,
        N1=N1,
        M=M,
        sizes=sizes,
        starts=starts,
        ends=ends,
        pair_ops=pair_ops,
        _ab=np.zeros((B + 1, N1), dtype=np.complex128),
        _C12=np.zeros((N1, B), dtype=np.complex128),
        _C22=np.zeros((B, B), dtype=np.complex128),
        _C=np.zeros((n, n), dtype=np.complex128),
        _Cinv=np.zeros((n, n), dtype=np.complex128),
    )


def sb_nll_only_fast(
    stageA5,
    nu: np.ndarray,
    g: np.ndarray,
    fgeom: dict[str, Any],
    shifted_pt: np.ndarray,
    r: np.ndarray,
    vd: float,
    sigma2: float,
) -> float:
    """Exact Gaussian NLL = logdet C + e^H C^-1 e via cyclic-banded Schur complement (~5 ms/call)."""
    if not fgeom.get('fast_ok', False):
        th = np.concatenate([np.asarray(nu, dtype=np.float64), np.real(g), np.imag(g)])
        return float(stageA5.sb_nll_and_grad(th, fgeom, shifted_pt, r, vd, sigma2)[0])
    B, N1 = fgeom['B'], fgeom['N1']
    ab, C12, C22 = fgeom['_ab'], fgeom['_C12'], fgeom['_C22']
    ab.fill(0.0)
    C12.fill(0.0)
    C22.fill(0.0)
    c_mat = stageA5.doppler_vectors(fgeom, nu)
    diag_val = float(sigma2) + float(vd) * float(np.sum(np.abs(g) ** 2))
    ab[0, :] = diag_val
    idx_b = np.arange(B)
    C22[idx_b, idx_b] = diag_val
    gc_all = float(vd) * (g[:, None] * c_mat)
    g_conj_c = np.conj(g[:, None] * c_mat)
    for (i, j, k_ab, m_ab, d_ab, k_12, m_12, c_12, k_22, m_22, r_22, c_22) in fgeom['pair_ops']:
        gi = gc_all[i]
        gj = g_conj_c[j]
        if len(k_ab):
            ab[d_ab, m_ab] += gi[k_ab] * gj[m_ab]
        if len(k_12):
            C12[k_12, c_12] += gi[k_12] * gj[m_12]
        if len(k_22):
            C22[r_22, c_22] += gi[k_22] * gj[m_22]
    try:
        Lb = cholesky_banded(ab, lower=True, overwrite_ab=True, check_finite=False)
        d_lb = Lb[0].real
        if np.any(d_lb <= 0.0) or not np.isfinite(d_lb).all():
            return 1e30
        V, info = ztbtrs(Lb, C12, uplo='L', trans='N', diag='N')
        if info != 0:
            return 1e30
        S = C22 - V.conj().T @ V
        LS, _ = cho_factor(S, lower=True, overwrite_a=True, check_finite=False)
        dLS = np.diag(LS).real
        if np.any(dLS <= 0.0) or not np.isfinite(dLS).all():
            return 1e30
    except Exception:
        return 1e30
    logdet = 2.0 * (float(np.sum(np.log(d_lb))) + float(np.sum(np.log(dLS))))
    e = r - np.sum((g[:, None] * c_mat) * shifted_pt, axis=0)
    y1, info1 = ztbtrs(Lb, e[:N1, None], uplo='L', trans='N', diag='N')
    if info1 != 0:
        return 1e30
    y1 = y1[:, 0]
    rhs2 = e[N1:] - V.conj().T @ y1
    alpha2 = cho_solve((LS, True), rhs2, check_finite=False)
    val = logdet + float(np.vdot(y1, y1).real + np.vdot(rhs2, alpha2).real)
    return val if np.isfinite(val) else 1e30


def sb_nll_and_grad_fast(
    theta: np.ndarray,
    fgeom: dict[str, Any],
    shifted_pt: np.ndarray,
    r: np.ndarray,
    vd: float,
    sigma2: float,
    stageA5,
) -> tuple[float, np.ndarray]:
    """Exact Gaussian NLL and analytic gradient via block-Takahashi + Woodbury (~15 ms/call, <1e-12 exact)."""
    if not fgeom.get('fast_ok', False):
        return stageA5.sb_nll_and_grad(theta, fgeom, shifted_pt, r, vd, sigma2)
    p = fgeom['p']
    n = fgeom['n']
    B, N1, M = fgeom['B'], fgeom['N1'], fgeom['M']
    sizes, starts, ends = fgeom['sizes'], fgeom['starts'], fgeom['ends']

    nu = theta[:p]
    g = theta[p:2 * p] + 1j * theta[2 * p:3 * p]
    c_mat = stageA5.doppler_vectors(fgeom, nu)

    C = fgeom['_C']
    C.fill(0.0)
    k_idx = fgeom['k']
    cross_col = fgeom['cross_col']
    C[k_idx, k_idx] = float(sigma2) + float(vd) * float(np.sum(np.abs(g) ** 2))
    for i in range(p):
        gi_ci = (float(vd) * g[i]) * c_mat[i]
        for j in range(p):
            if i == j:
                continue
            m_idx = cross_col[i, j]
            C[k_idx, m_idx] += gi_ci * np.conj(g[j] * c_mat[j, m_idx])

    L_blks, Linv_blks, G_blks, F_blks = [], [], [], []
    D_cur = C[starts[0]:ends[0], starts[0]:ends[0]].copy()
    for m in range(M):
        try:
            Lm, _ = cho_factor(D_cur, lower=True, overwrite_a=True, check_finite=False)
        except Exception:
            return 1e30, np.zeros(3 * p, dtype=np.float64)
        dL = np.diag(Lm).real
        if np.any(dL <= 0.0) or not np.isfinite(dL).all():
            return 1e30, np.zeros(3 * p, dtype=np.float64)
        Lm_tril = np.tril(Lm)
        Linv = solve_triangular(Lm_tril, np.eye(sizes[m], dtype=np.complex128), lower=True, check_finite=False)
        L_blks.append(Lm_tril)
        Linv_blks.append(Linv)
        if m < M - 1:
            Em = C[starts[m + 1]:ends[m + 1], starts[m]:ends[m]]
            Gm = Em @ Linv.conj().T
            Fm = Linv.conj().T @ Gm.conj().T
            G_blks.append(Gm)
            F_blks.append(Fm)
            D_cur = C[starts[m + 1]:ends[m + 1], starts[m + 1]:ends[m + 1]] - Gm @ Gm.conj().T

    V_blks = [None] * M
    V_blks[0] = Linv_blks[0] @ C[starts[0]:ends[0], N1:]
    for m in range(1, M):
        V_blks[m] = Linv_blks[m] @ (C[starts[m]:ends[m], N1:] - G_blks[m - 1] @ V_blks[m - 1])
    V = np.vstack(V_blks)

    S = C[N1:, N1:] - V.conj().T @ V
    try:
        LS, _ = cho_factor(S, lower=True, overwrite_a=True, check_finite=False)
    except Exception:
        return 1e30, np.zeros(3 * p, dtype=np.float64)
    dLS = np.diag(LS).real
    if np.any(dLS <= 0.0) or not np.isfinite(dLS).all():
        return 1e30, np.zeros(3 * p, dtype=np.float64)
    LS_tril = np.tril(LS)
    LS_inv = solve_triangular(LS_tril, np.eye(B, dtype=np.complex128), lower=True, check_finite=False)

    logdet = 2.0 * (sum(float(np.sum(np.log(np.diag(Lm).real))) for Lm in L_blks) + float(np.sum(np.log(dLS))))
    mu = np.sum((g[:, None] * c_mat) * shifted_pt, axis=0)
    e = r - mu
    y1_blks = [None] * M
    y1_blks[0] = Linv_blks[0] @ e[starts[0]:ends[0]]
    for m in range(1, M):
        y1_blks[m] = Linv_blks[m] @ (e[starts[m]:ends[m]] - G_blks[m - 1] @ y1_blks[m - 1])
    y1 = np.concatenate(y1_blks)
    y2 = LS_inv @ (e[N1:] - V.conj().T @ y1)
    nll = logdet + float(np.vdot(y1, y1).real + np.vdot(y2, y2).real)
    if not np.isfinite(nll):
        return 1e30, np.zeros(3 * p, dtype=np.float64)

    alpha2 = LS_inv.conj().T @ y2
    RHS_back = np.empty((N1, B + 1), dtype=np.complex128)
    RHS_back[:, :B] = V @ LS_inv.conj().T
    RHS_back[:, B] = y1 - V @ alpha2

    X_back = [None] * M
    X_back[M - 1] = Linv_blks[M - 1].conj().T @ RHS_back[starts[M - 1]:ends[M - 1]]
    for m in range(M - 2, -1, -1):
        X_back[m] = Linv_blks[m].conj().T @ RHS_back[starts[m]:ends[m]] - F_blks[m] @ X_back[m + 1]
    U_all = np.vstack(X_back)
    U = U_all[:, :B]
    alpha = np.concatenate([U_all[:, B], alpha2])

    Z_diag = [None] * M
    Z_sub = [None] * (M - 1)
    Z_diag[M - 1] = Linv_blks[M - 1].conj().T @ Linv_blks[M - 1]
    for m in range(M - 2, -1, -1):
        Z_sub[m] = -Z_diag[m + 1] @ F_blks[m].conj().T
        Z_diag[m] = Linv_blks[m].conj().T @ Linv_blks[m] - F_blks[m] @ Z_sub[m]

    Cinv_band = fgeom['_Cinv']
    for m in range(M):
        s0, e0 = starts[m], ends[m]
        Um = U[s0:e0]
        Cinv_band[s0:e0, s0:e0] = Z_diag[m] + Um @ Um.conj().T
        if m < M - 1:
            s1, e1 = starts[m + 1], ends[m + 1]
            blk = Z_sub[m] + U[s1:e1] @ Um.conj().T
            Cinv_band[s1:e1, s0:e0] = blk
            Cinv_band[s0:e0, s1:e1] = blk.conj().T
    C12_inv_top = -U[starts[0]:ends[0]] @ LS_inv
    Cinv_band[starts[0]:ends[0], N1:] = C12_inv_top
    Cinv_band[N1:, starts[0]:ends[0]] = C12_inv_top.conj().T
    C12_inv_bot = -U[starts[M - 1]:ends[M - 1]] @ LS_inv
    Cinv_band[starts[M - 1]:ends[M - 1], N1:] = C12_inv_bot
    Cinv_band[N1:, starts[M - 1]:ends[M - 1]] = C12_inv_bot.conj().T
    Cinv_band[N1:, N1:] = LS_inv.conj().T @ LS_inv

    grad = np.empty(3 * p, dtype=np.float64)
    for i in range(p):
        qi = np.zeros(n, dtype=np.complex128)
        for j in range(p):
            m_idx = cross_col[i, j]
            w_mk = Cinv_band[m_idx, k_idx] - alpha[m_idx] * alpha.conj()
            qi += np.conj(g[j] * c_mat[j, m_idx]) * w_mk
        s_i = (2.0 * float(vd)) * qi
        v_nu = g[i] * c_mat[i] * fgeom['k_norm']
        v_rg = c_mat[i]
        v_ig = 1j * c_mat[i]
        grad[i] = float(np.real(np.sum(s_i * v_nu)) - 2.0 * np.real(np.vdot(alpha, v_nu * shifted_pt[i])))
        grad[p + i] = float(np.real(np.sum(s_i * v_rg)) - 2.0 * np.real(np.vdot(alpha, v_rg * shifted_pt[i])))
        grad[2 * p + i] = float(np.real(np.sum(s_i * v_ig)) - 2.0 * np.real(np.vdot(alpha, v_ig * shifted_pt[i])))
    if not np.isfinite(grad).all():
        return 1e30, np.zeros(3 * p, dtype=np.float64)
    return nll, grad


def _run_lbfgs_bounded(
    stageA5,
    fgeom: dict[str, Any],
    shifted_pt: np.ndarray,
    r: np.ndarray,
    vd: float,
    sigma2: float,
    nu0: np.ndarray,
    g0: np.ndarray,
    nu_bounds: list[tuple[float, float]],
    *,
    maxiter: int = 80,
    ftol: float = 1e-10,
) -> tuple[float, np.ndarray, np.ndarray]:
    p = fgeom['p']
    nu_start = np.array([np.clip(nu0[i], nu_bounds[i][0], nu_bounds[i][1]) for i in range(p)], dtype=np.float64)
    g_start = np.clip(np.real(g0), GAIN_MIN, GAIN_MAX) + 1j * np.clip(np.imag(g0), GAIN_MIN, GAIN_MAX)
    theta0 = np.concatenate([nu_start, g_start.real, g_start.imag])
    bounds = list(nu_bounds) + [(GAIN_MIN, GAIN_MAX)] * (2 * p)
    res = minimize(
        sb_nll_and_grad_fast,
        theta0,
        args=(fgeom, shifted_pt, r, float(vd), float(sigma2), stageA5),
        method='L-BFGS-B',
        jac=True,
        bounds=bounds,
        options={'maxiter': maxiter, 'ftol': ftol, 'gtol': 1e-6},
    )
    nu = np.asarray(res.x[:p], dtype=np.float64)
    g = np.asarray(res.x[p:2 * p] + 1j * res.x[2 * p:3 * p], dtype=np.complex128)
    nll = sb_nll_only_fast(stageA5, nu, g, fgeom, shifted_pt, r, vd, sigma2)
    return float(nll), nu, g


def _escape_sweeps(
    stageA5,
    fgeom: dict[str, Any],
    p_t: np.ndarray,
    shifted_pt: np.ndarray,
    r: np.ndarray,
    vd: float,
    sigma2: float,
    nu_in: np.ndarray,
    g_in: np.ndarray,
    nll_in: float,
    lag_counts: Counter,
    freqs: np.ndarray,
    valid_idx: np.ndarray,
    *,
    n_fft: int = 4096,
    n_peaks: int = 4,
    sweeps: int = 2,
) -> tuple[np.ndarray, np.ndarray, float, bool]:
    n, p = fgeom['n'], fgeom['p']
    delays, cp = fgeom['delays'], fgeom['cp']
    nu_best, g_best, nll_best = nu_in.copy(), g_in.copy(), float(nll_in)
    escaped = False
    p_pow = float(np.mean(np.abs(p_t) ** 2))
    for _ in range(sweeps):
        improved = False
        for i in np.argsort(-np.abs(g_best)):
            i = int(i)
            c_c = stageA5.doppler_vectors(fgeom, nu_best)
            mu_all = np.sum((g_best[:, None] * c_c) * shifted_pt, axis=0)
            r_tilde = r - mu_all
            xi = np.zeros(n, dtype=np.complex128)
            w_cov = 0.0
            for j in range(p):
                if j == i:
                    continue
                dl = int(delays[i] - delays[j])
                if dl == 0:
                    continue
                m_ij = fgeom['cross_col'][i, j]
                wt = 1.0 / float(lag_counts[dl])
                xi += wt * g_best[j] * cp[j, m_ij] * np.conj(r_tilde[m_ij]) * np.exp(2j * np.pi * m_ij * nu_best[j] / n)
                w_cov += wt * (abs(g_best[j]) ** 2)
            xi = np.conj(cp[i]) * r_tilde * xi
            r_minus_i = r - (mu_all - g_best[i] * c_c[i] * shifted_pt[i])
            xi_pil = np.conj(cp[i]) * np.conj(shifted_pt[i]) * r_minus_i
            comb = float(vd) * xi + xi_pil
            buf = np.zeros(n_fft, dtype=np.complex128)
            buf[:n] = comb
            spec = np.fft.fft(buf)
            mag = np.abs(spec[valid_idx])
            ord_k = np.argsort(-mag)
            peaks = []
            denom = n * (float(vd) * float(vd) * w_cov + p_pow)
            for idx_v in ord_k:
                fk = float(np.clip(freqs[valid_idx[idx_v]], NU_MIN, NU_MAX))
                if abs(fk - nu_best[i]) < 0.30:
                    continue
                if all(abs(fk - pv[0]) >= 0.30 for pv in peaks):
                    gk = complex(spec[valid_idx[idx_v]]) / max(denom, 1e-12)
                    peaks.append((fk, gk))
                    if len(peaks) == n_peaks:
                        break
            for fk, gk in peaks:
                nu_try = nu_best.copy()
                nu_try[i] = fk
                g_try = g_best.copy()
                g_try[i] = np.clip(gk.real, GAIN_MIN, GAIN_MAX) + 1j * np.clip(gk.imag, GAIN_MIN, GAIN_MAX)
                nll_try = sb_nll_only_fast(stageA5, nu_try, g_try, fgeom, shifted_pt, r, vd, sigma2)
                if nll_try < nll_best - 0.05:
                    nll_best, nu_best, g_best = nll_try, nu_try, g_try
                    improved = True
                    escaped = True
        if not improved:
            break
    return nu_best, g_best, nll_best, escaped


def estimate_sb_global(
    stageA5,
    fgeom: dict[str, Any],
    p_t: np.ndarray,
    r: np.ndarray,
    vd: float,
    sigma2: float,
    *,
    nu_pw_pre: tuple[np.ndarray, np.ndarray] | None = None,
    maxiter: int = 65,
    ftol: float = 1e-9,
) -> tuple[np.ndarray, np.ndarray]:
    """Truth-free global semi-blind Gaussian ML estimator over [-3, 3]^P x [-10, 10]^{2P}.

    Architecturally receives ONLY (fgeom, p_t, r, vd, sigma2); never sees truth Doppler, gains, or data.
    """
    n, p = fgeom['n'], fgeom['p']
    delays, cp, k_idx = fgeom['delays'], fgeom['cp'], fgeom['k']
    shifted_pt = p_t[fgeom['cols']]
    lag_counts = Counter(int(delays[i] - delays[j]) for i in range(p) for j in range(p) if i != j)
    full_nu_bounds = [(NU_MIN, NU_MAX)] * p

    n_fft = 4096
    freqs = np.fft.fftfreq(n_fft, d=1.0 / n)
    diff_idx = np.flatnonzero(np.abs(freqs) <= 6.0)
    diff_freqs = freqs[diff_idx]
    valid_idx = np.flatnonzero((freqs >= NU_MIN) & (freqs <= NU_MAX))

    # Candidate 0: Pilot-white (PW) + coordinate sidelobe escape screen
    if nu_pw_pre is None:
        nu_pw, g_pw = stageA5.estimate_pw(fgeom, p_t, r)
    else:
        nu_pw, g_pw = np.asarray(nu_pw_pre[0], dtype=np.float64).copy(), np.asarray(nu_pw_pre[1], dtype=np.complex128).copy()
    nll_pw0 = sb_nll_only_fast(stageA5, nu_pw, g_pw, fgeom, shifted_pt, r, vd, sigma2)
    nu_pw_esc, g_pw_esc, nll_pw_esc, _ = _escape_sweeps(
        stageA5, fgeom, p_t, shifted_pt, r, vd, sigma2,
        nu_pw, g_pw, nll_pw0, lag_counts, freqs, valid_idx, n_fft=n_fft, n_peaks=4, sweeps=2,
    )

    # Candidate 1: Pairwise non-wrapped data cross-lag FFT + coherent pilot global-offset alignment + escape screen
    pair_peak = np.zeros((p, p), dtype=np.float64)
    pair_dnu = np.zeros((p, p), dtype=np.float64)
    pair_c = np.zeros((p, p), dtype=np.complex128)
    for i in range(p):
        for j in range(i + 1, p):
            dl = int(delays[i] - delays[j])
            if dl == 0:
                continue
            ks = np.arange(max(0, dl), min(n, n + dl), dtype=np.int64)
            ms = ks - dl
            buf = np.zeros(n_fft, dtype=np.complex128)
            buf[ks] = r[ks] * np.conj(r[ms]) * np.conj(cp[i, ks]) * cp[j, ms]
            spec = np.fft.fft(buf)[diff_idx] / float(lag_counts[dl])
            bk = int(np.argmax(np.abs(spec)))
            dnu = float(diff_freqs[bk])
            cv = complex(spec[bk]) / float(len(ks) * max(float(vd), 1e-6))
            pair_peak[i, j] = pair_peak[j, i] = abs(cv)
            pair_dnu[i, j] = dnu
            pair_dnu[j, i] = -dnu
            pair_c[i, j] = cv
            pair_c[j, i] = np.conj(cv)

    if np.max(pair_peak) > 0.0:
        anchor = int(np.argmax(np.sum(pair_peak, axis=1)))
        nu_rel = pair_dnu[:, anchor].copy()
        nu_rel[anchor] = 0.0
        g_a_mag = max(0.1, float(np.sqrt(max(pair_peak[anchor].max(), 1e-4))))
        g_rel0 = pair_c[:, anchor] / g_a_mag
        g_rel0[anchor] = g_a_mag

        lo_a = max(NU_MIN, float(NU_MIN - np.min(nu_rel)))
        hi_a = min(NU_MAX, float(NU_MAX - np.max(nu_rel)))
        if lo_a >= hi_a:
            lo_a, hi_a = NU_MIN, NU_MAX
        grid_a = np.linspace(lo_a, hi_a, 241)
        c_rel = stageA5.doppler_vectors(fgeom, nu_rel)
        q_i = g_rel0[:, None] * c_rel * shifted_pt
        phase_mat = np.exp(2j * np.pi / n * np.outer(grid_a, k_idx))
        corr_all = ((np.conj(q_i) * r[None, :]) @ np.conj(phase_mat).T) * np.exp(2j * np.pi / n * np.outer(delays, grid_a))
        coh_score = np.abs(np.sum(corr_all, axis=0)) ** 2
        nu_a = float(grid_a[int(np.argmax(coh_score))])
        nu_cov = np.clip(nu_rel + nu_a, NU_MIN, NU_MAX)
        g_cov = g_rel0 * np.exp(-2j * np.pi * (delays - delays[anchor]) * nu_a / n)
        c_c = stageA5.doppler_vectors(fgeom, nu_cov)
        mu0 = np.sum((g_cov[:, None] * c_c) * shifted_pt, axis=0)
        if np.vdot(mu0, mu0).real > 1e-12:
            g_cov = g_cov * np.exp(1j * np.angle(np.vdot(mu0, r) / np.vdot(mu0, mu0)))
        nll_cov0 = sb_nll_only_fast(stageA5, nu_cov, g_cov, fgeom, shifted_pt, r, vd, sigma2)
        nu_cov_esc, g_cov_esc, nll_cov_esc, _ = _escape_sweeps(
            stageA5, fgeom, p_t, shifted_pt, r, vd, sigma2,
            nu_cov, g_cov, nll_cov0, lag_counts, freqs, valid_idx, n_fft=n_fft, n_peaks=4, sweeps=2,
        )
    else:
        nll_cov_esc, nu_cov_esc, g_cov_esc = 1e30, nu_pw_esc, g_pw_esc

    if nll_cov_esc < nll_pw_esc:
        nu_start, g_start = nu_cov_esc, g_cov_esc
    else:
        nu_start, g_start = nu_pw_esc, g_pw_esc

    nll_best, nu_best, g_best = _run_lbfgs_bounded(
        stageA5, fgeom, shifted_pt, r, vd, sigma2, nu_start, g_start, full_nu_bounds, maxiter=maxiter, ftol=ftol
    )

    # Post-L-BFGS-B escape verification sweep
    nu_post, g_post, nll_post, escaped = _escape_sweeps(
        stageA5, fgeom, p_t, shifted_pt, r, vd, sigma2,
        nu_best, g_best, nll_best, lag_counts, freqs, valid_idx, n_fft=n_fft, n_peaks=4, sweeps=2,
    )
    if escaped:
        nll_best, nu_best, g_best = _run_lbfgs_bounded(
            stageA5, fgeom, shifted_pt, r, vd, sigma2, nu_post, g_post, full_nu_bounds, maxiter=maxiter, ftol=ftol
        )

    if not (np.isfinite(nu_best).all() and np.isfinite(g_best).all()):
        raise FloatingPointError('Nonfinite output in estimate_sb_global')
    return nu_best, g_best


# --------------------------------------------------------------------------- Diagnostic oracle & coded helpers
def _sb_optimize_gains_only(
    stageA5,
    fgeom: dict[str, Any],
    shifted_pt: np.ndarray,
    r: np.ndarray,
    vd: float,
    sigma2: float,
    nu_fixed: np.ndarray,
    g_init: np.ndarray,
) -> tuple[float, np.ndarray]:
    p = fgeom['p']
    nu_f = np.asarray(nu_fixed, dtype=np.float64)

    def obj_g(g_vec: np.ndarray) -> tuple[float, np.ndarray]:
        th = np.concatenate([nu_f, g_vec])
        val, gr = sb_nll_and_grad_fast(th, fgeom, shifted_pt, r, vd, sigma2, stageA5)
        return val, gr[p:]

    g0 = np.concatenate([np.clip(np.real(g_init), GAIN_MIN, GAIN_MAX), np.clip(np.imag(g_init), GAIN_MIN, GAIN_MAX)])
    res = minimize(
        obj_g,
        g0,
        method='L-BFGS-B',
        jac=True,
        bounds=[(GAIN_MIN, GAIN_MAX)] * (2 * p),
        options={'maxiter': 60, 'ftol': 1e-10, 'gtol': 1e-6},
    )
    g_opt = np.asarray(res.x[:p] + 1j * res.x[p:], dtype=np.complex128)
    val = sb_nll_only_fast(stageA5, nu_f, g_opt, fgeom, shifted_pt, r, vd, sigma2)
    return float(val), g_opt


def _kd_profile_nll(geom: dict[str, Any], stageA5, x_t: np.ndarray, r: np.ndarray, nu: np.ndarray, sigma2: float) -> float:
    c_mat = stageA5.doppler_vectors(geom, nu)
    A = stageA5.build_basis_matrix(geom, c_mat, x_t)
    g, _, _, _ = np.linalg.lstsq(A, r, rcond=None)
    res = r - A @ g
    return float(np.vdot(res, res).real / sigma2)


def _kd_box_min(
    geom: dict[str, Any],
    stageA5,
    x_t: np.ndarray,
    r: np.ndarray,
    nu_center: np.ndarray,
    sigma2: float,
    half: float = BOX_HALF,
) -> tuple[float, np.ndarray]:
    """Grid + bounded coordinate + L-BFGS-B minimum of known-data profile NLL inside [nu_center - half, nu_center + half]."""
    p = geom['p']
    bnds = [(max(NU_MIN, float(v - half)), min(NU_MAX, float(v + half))) for v in nu_center]
    nu = np.array([np.clip(nu_center[i], bnds[i][0], bnds[i][1]) for i in range(p)], dtype=np.float64)
    c_mat = stageA5.doppler_vectors(geom, nu)
    A = stageA5.build_basis_matrix(geom, c_mat, x_t)
    g, _, _, _ = np.linalg.lstsq(A, r, rcond=None)
    shifted = x_t[geom['cols']]
    r_norm2 = float(np.vdot(r, r).real)

    for _ in range(2):
        for idx in np.argsort(-np.abs(g)):
            p_idx = int(idx)
            lo, hi = bnds[p_idx]
            grid = np.linspace(lo, hi, 11)
            other = [j for j in range(p) if j != p_idx]
            if other:
                Q_o, _ = np.linalg.qr(A[:, other], mode='reduced')
                r_perp = r - Q_o @ (Q_o.conj().T @ r)
                r_perp_n2 = float(np.vdot(r_perp, r_perp).real)
            else:
                Q_o = None
                r_perp = r
                r_perp_n2 = r_norm2
            base_p = geom['cp'][p_idx] * shifted[p_idx]
            cols_g = base_p[:, None] * np.exp(np.outer(geom['k_norm'], grid))
            U_g = cols_g - Q_o @ (Q_o.conj().T @ cols_g) if Q_o is not None else cols_g
            un2 = np.sum(np.abs(U_g) ** 2, axis=0)
            num = np.abs(U_g.conj().T @ r_perp) ** 2
            sc = np.where(un2 > 1e-18, np.maximum(0.0, r_perp_n2 - num / np.maximum(un2, 1e-30)), r_perp_n2)
            best_g = float(grid[int(np.argmin(sc))])

            def obj_1d(val: float) -> float:
                col = base_p * np.exp(float(val) * geom['k_norm'])
                u = col - Q_o @ (Q_o.conj().T @ col) if Q_o is not None else col
                u2 = float(np.vdot(u, u).real)
                return r_perp_n2 if u2 <= 1e-18 else max(0.0, r_perp_n2 - abs(np.vdot(u, r_perp)) ** 2 / u2)

            step = (hi - lo) / 10.0
            opt1 = minimize_scalar(obj_1d, bounds=(max(lo, best_g - step), min(hi, best_g + step)), method='bounded', options={'xatol': 1e-4})
            cand = float(opt1.x)
            nu[p_idx] = cand if obj_1d(cand) <= obj_1d(best_g) else best_g
            c_mat[p_idx] = geom['cp'][p_idx] * np.exp(nu[p_idx] * geom['k_norm'])
            A[:, p_idx] = c_mat[p_idx] * shifted[p_idx]
        g, _, _, _ = np.linalg.lstsq(A, r, rcond=None)

    val_coord = _kd_profile_nll(geom, stageA5, x_t, r, nu, sigma2)
    res_b = minimize(
        lambda v: _kd_profile_nll(geom, stageA5, x_t, r, v, sigma2),
        nu,
        method='L-BFGS-B',
        bounds=bnds,
        options={'maxiter': 50, 'ftol': 1e-10},
    )
    nu_b = np.asarray(res_b.x, dtype=np.float64)
    val_b = _kd_profile_nll(geom, stageA5, x_t, r, nu_b, sigma2)
    if val_b <= val_coord:
        return float(val_b), nu_b
    return float(val_coord), nu


def bits_to_qpsk(bits: np.ndarray, vd: float) -> np.ndarray:
    """Exact frozen I-then-Q 2048-bit to 1024-QPSK mapping matching raw['data']."""
    b = np.asarray(bits, dtype=np.float64)
    n_half = len(b) // 2
    return np.sqrt(float(vd) / 2.0) * ((1.0 - 2.0 * b[:n_half]) + 1j * (1.0 - 2.0 * b[n_half:]))


def one_arm_nu_detailed(
    C,
    stageA,
    stageA2,
    stageA5,
    daft,
    obs: dict[str, Any],
    truth: dict[str, Any],
    p_vec: np.ndarray,
    r: np.ndarray,
    vd: float,
    nu_hat: np.ndarray,
    g_order: np.ndarray | None = None,
) -> dict[str, Any]:
    """Identical to stageA6.one_arm_nu while also recording terminal syndrome & joint coded profile NLL."""
    ctx, stage3 = C['ctx'], C['stage3']
    c1, c2 = ctx.system.c1, ctx.system.c2
    pert = dict(truth, k_real=np.asarray(nu_hat, dtype=np.float64).tolist())
    if g_order is not None:
        pert['g_i'] = np.asarray(g_order, dtype=np.complex128).tolist()
    dec, arrays, syndrome, _ = stageA2.f0_true(C, obs, pert, 'ls')
    s2 = float(obs['sigma2'])
    f0_err = int(stage3.e1.gd.score(ctx, dec['decoded'], truth))
    if syndrome:
        br = stage3.e1.run_branch(ctx, C['cd'], obs, arrays, 'A1')
        dec_bits = np.asarray(br['decoder']['decoded'], dtype=np.uint8)
        fin_syn = int(ctx.hd.syndrome_weight(ctx, dec_bits))
        fin_err = int(stage3.e1.gd.score(ctx, dec_bits, truth))
        fin_delays = np.array([int(p.delay) for p in br['result'].paths], dtype=np.int64)
        fin_dopplers = np.array([float(p.doppler) for p in br['result'].paths], dtype=np.float64)
    else:
        dec_bits = np.asarray(dec['decoded'], dtype=np.uint8)
        fin_syn = 0
        fin_err = f0_err
        fin_delays = np.asarray(arrays['r1_delays'], dtype=np.int64)
        fin_dopplers = np.asarray(arrays['r1_dopplers'], dtype=np.float64)

    d_hat = bits_to_qpsk(dec_bits, vd)
    x_hat_t = daft(p_vec + d_hat, c1, c2, True)
    fin_geom = stageA5.precompute_delay_geometry(fin_delays, len(r), c1)
    joint_nll = _kd_profile_nll(fin_geom, stageA5, x_hat_t, r, fin_dopplers, s2)
    return dict(
        f0_syndrome=int(syndrome),
        f0_errors=f0_err,
        final_syndrome=fin_syn,
        errors=fin_err,
        joint_coded_nll=float(joint_nll),
    )


def eval_diag_key(
    C,
    stageA,
    stageA2,
    stageA5,
    daft,
    item: dict[str, Any],
    a2_ldop_ref: dict[str, Any],
) -> dict[str, Any]:
    """Run full Stage A7 decisive diagnosis on one Stage A6 failed key."""
    t_start = time.process_time()
    st, ctx = C['stage3'], C['ctx']
    c1, c2 = ctx.system.c1, ctx.system.c2
    frame = int(item['frame'])
    s = str(item['scenario'])
    rho = int(item['rho'])
    snr = int(item['snr'])

    base = st.inputs(ctx, frame, s, rho)
    raw, obs, truth = st.observed(ctx, base, rho, snr)
    y = np.asarray(raw['y'], dtype=np.complex128)
    p_vec = np.asarray(raw['pilot'], dtype=np.complex128)
    d_vec = np.asarray(raw['data'], dtype=np.complex128)
    sigma2 = float(raw['sigma2'])
    vd = float(np.mean(np.abs(d_vec) ** 2))
    n = len(y)
    r = daft(y, c1, c2, True)
    p_t = daft(p_vec, c1, c2, True)
    x_t = daft(p_vec + d_vec, c1, c2, True)

    l_true = np.asarray(truth['l_i'], dtype=np.int64)
    nu_true = np.asarray(truth['k_real'], dtype=np.float64)
    g_true = np.asarray(truth['g_i'], dtype=np.complex128)
    geom = stageA5.precompute_delay_geometry(l_true, n, c1)
    fgeom = prepare_fast_geom(geom)
    shifted_pt = p_t[geom['cols']]

    # 1. Exact replay of A6 PW and SB
    nu_pw, g_pw = stageA5.estimate_pw(geom, p_t, r)
    nu_sb, g_sb = stageA5.estimate_sb(geom, p_t, r, vd, sigma2, nu_pw, g_pw)
    sb_replay_diff = float(np.max(np.abs(np.abs(nu_sb - nu_true) - np.asarray(item['sb_abs_err'], dtype=np.float64))))
    if sb_replay_diff >= 1e-6:
        raise RuntimeError(f'Stage A6 SB replay mismatch at {(frame, s, rho, snr)}: {sb_replay_diff}')

    # Exact reference SB NLL at A6 SB
    theta_sb = np.concatenate([nu_sb, g_sb.real, g_sb.imag])
    nll_sb_at_sb, _ = stageA5.sb_nll_and_grad(theta_sb, geom, shifted_pt, r, vd, sigma2)
    nll_sb_fast_chk = sb_nll_only_fast(stageA5, nu_sb, g_sb, fgeom, shifted_pt, r, vd, sigma2)
    if abs(nll_sb_at_sb - nll_sb_fast_chk) > 1e-8:
        raise RuntimeError(f'Fast vs exact SB NLL mismatch at {(frame, s, rho, snr)}: {abs(nll_sb_at_sb - nll_sb_fast_chk)}')

    # 2. Truth-basin SB optimum (tbox & tfree), audited by exact stageA5.sb_nll_and_grad
    _, g_sb_true = _sb_optimize_gains_only(stageA5, fgeom, shifted_pt, r, vd, sigma2, nu_true, g_true)
    box_true = [(max(NU_MIN, float(nt - BOX_HALF)), min(NU_MAX, float(nt + BOX_HALF))) for nt in nu_true]
    _, nu_sb_tbox, g_sb_tbox = _run_lbfgs_bounded(stageA5, fgeom, shifted_pt, r, vd, sigma2, nu_true, g_sb_true, box_true)
    nll_sb_tbox, _ = stageA5.sb_nll_and_grad(
        np.concatenate([nu_sb_tbox, g_sb_tbox.real, g_sb_tbox.imag]), geom, shifted_pt, r, vd, sigma2
    )
    _, nu_sb_tfree, g_sb_tfree = _run_lbfgs_bounded(
        stageA5, fgeom, shifted_pt, r, vd, sigma2, nu_true, g_sb_true, [(NU_MIN, NU_MAX)] * len(l_true)
    )
    nll_sb_tfree, _ = stageA5.sb_nll_and_grad(
        np.concatenate([nu_sb_tfree, g_sb_tfree.real, g_sb_tfree.imag]), geom, shifted_pt, r, vd, sigma2
    )

    # 3. Truth-free global SB search (SBG) + SBGdop receiver
    t_sbg0 = time.process_time()
    nu_sbg, g_sbg = estimate_sb_global(stageA5, fgeom, p_t, r, vd, sigma2)
    sbg_cpu = time.process_time() - t_sbg0
    nll_sb_sbg, _ = stageA5.sb_nll_and_grad(
        np.concatenate([nu_sbg, g_sbg.real, g_sbg.imag]), geom, shifted_pt, r, vd, sigma2
    )

    rec_sbg = one_arm_nu_detailed(C, stageA, stageA2, stageA5, daft, obs, truth, p_vec, r, vd, nu_sbg, g_order=g_sbg)
    rec_tbox = one_arm_nu_detailed(C, stageA, stageA2, stageA5, daft, obs, truth, p_vec, r, vd, nu_sb_tbox, g_order=g_sb_tbox)
    rec_sbdop = one_arm_nu_detailed(C, stageA, stageA2, stageA5, daft, obs, truth, p_vec, r, vd, nu_sb, g_order=g_sb)
    rec_ldop = one_arm_nu_detailed(C, stageA, stageA2, stageA5, daft, obs, truth, p_vec, r, vd, nu_true, g_order=None)

    if rec_sbdop['errors'] != int(item['arms']['SBdop']['errors']) or rec_sbdop['f0_syndrome'] != int(item['arms']['SBdop']['syndrome']):
        raise RuntimeError(f'Stage A6 SBdop receiver mismatch at {(frame, s, rho, snr)}')
    if rec_ldop['errors'] != int(a2_ldop_ref['errors']) or rec_ldop['f0_syndrome'] != int(a2_ldop_ref['syndrome']):
        raise RuntimeError(f'Stage A2 ldop receiver mismatch at {(frame, s, rho, snr)}')

    # 4. Known-data profile NLL comparison
    nll_kd_sb_box, _ = _kd_box_min(geom, stageA5, x_t, r, nu_sb, sigma2, half=BOX_HALF)
    nll_kd_true_box, _ = _kd_box_min(geom, stageA5, x_t, r, nu_true, sigma2, half=BOX_HALF)
    nu_kd_free, _ = stageA5.estimate_kd(geom, x_t, r)
    nll_kd_free = _kd_profile_nll(geom, stageA5, x_t, r, nu_kd_free, sigma2)

    # 5. Coded valid-codeword joint residual indicator
    code_ok = bool(
        rec_ldop['final_syndrome'] == 0
        and rec_ldop['errors'] == 0
        and (rec_sbdop['final_syndrome'] != 0 or rec_sbdop['joint_coded_nll'] > rec_ldop['joint_coded_nll'])
    )

    m_sbg, out_sbg, e_sbg = stageA5.doppler_metric(nu_sbg, nu_true, g_true)
    m_sb, out_sb, e_sb = stageA5.doppler_metric(nu_sb, nu_true, g_true)

    delta_sb = float(nll_sb_at_sb - nll_sb_tbox)
    delta_kd = float(nll_kd_sb_box - nll_kd_true_box)
    total_cpu = time.process_time() - t_start

    return dict(
        frame=frame,
        scenario=s,
        rho=rho,
        snr=snr,
        total_cpu=float(total_cpu),
        sbg_cpu=float(sbg_cpu),
        sb_replay_diff=sb_replay_diff,
        sb_metric=float(m_sb),
        sb_outlier_frac=float(out_sb),
        sb_max_err=float(max(e_sb)),
        sbg_metric=float(m_sbg),
        sbg_outlier_frac=float(out_sbg),
        sbg_max_err=float(max(e_sbg)),
        nll_sb=dict(
            at_sb=float(nll_sb_at_sb),
            at_tbox=float(nll_sb_tbox),
            at_tfree=float(nll_sb_tfree),
            at_sbg=float(nll_sb_sbg),
            delta_sb_minus_tbox=delta_sb,
            delta_sb_minus_sbg=float(nll_sb_at_sb - nll_sb_sbg),
            delta_sbg_minus_tbox=float(nll_sb_sbg - nll_sb_tbox),
        ),
        nll_kd=dict(
            at_sb_box=float(nll_kd_sb_box),
            at_true_box=float(nll_kd_true_box),
            at_kd_free=float(nll_kd_free),
            delta_sbbox_minus_tbox=delta_kd,
            kd_free_max_err=float(np.max(np.abs(nu_kd_free - nu_true))),
        ),
        receiver=dict(
            sbdop=rec_sbdop,
            sbgdop=rec_sbg,
            tbox=rec_tbox,
            ldop=rec_ldop,
        ),
        indicators=dict(
            sb_prefers_tbox=bool(delta_sb > 0.0),
            sbg_rescues=bool(rec_sbg['errors'] == 0),
            sbg_reaches_tbox=bool(nll_sb_sbg <= nll_sb_tbox + 0.1),
            kd_prefers_tbox=bool(delta_kd > 0.0),
            code_prefers_truth=code_ok,
        ),
    )


# --------------------------------------------------------------------------- Cluster bootstrap & frozen verdict
def cluster_ratio_bootstrap(
    rows: list[dict[str, Any]],
    indicator_fn,
    *,
    boot_draws: int = BOOT_DRAWS,
    boot_seed: int = BOOT_SEED,
) -> dict[str, Any]:
    """Physical-frame ratio cluster bootstrap over unique frames present in rows."""
    if not rows:
        raise ValueError('Empty rows in cluster_ratio_bootstrap')
    frames_u = sorted({int(r['frame']) for r in rows})
    f_to_idx = {f: i for i, f in enumerate(frames_u)}
    m = len(frames_u)
    k_vec = np.zeros(m, dtype=np.float64)
    s_vec = np.zeros(m, dtype=np.float64)
    hits = 0
    for r in rows:
        ci = f_to_idx[int(r['frame'])]
        val = 1.0 if bool(indicator_fn(r)) else 0.0
        k_vec[ci] += 1.0
        s_vec[ci] += val
        hits += int(val > 0.5)
    n_total = len(rows)
    pt = float(hits / n_total)
    rng = np.random.default_rng(boot_seed)
    boots = np.empty(boot_draws, dtype=np.float64)
    for b in range(boot_draws):
        w = np.bincount(rng.integers(0, m, m), minlength=m).astype(np.float64)
        boots[b] = float((w @ s_vec) / (w @ k_vec))
    lo, hi = (float(v) for v in np.percentile(boots, [2.5, 97.5]))
    return dict(
        hits=hits,
        n=n_total,
        unique_frames=m,
        point=pt,
        ci95=[lo, hi],
    )


def verdict_a7(
    sb_stat: dict[str, Any],
    sbg_rescue_stat: dict[str, Any],
    sbg_reach_stat: dict[str, Any],
    kd_stat: dict[str, Any],
    code_stat: dict[str, Any],
) -> str:
    """Exact Stage A7 4-way mutually exclusive pre-registered verdict rule (STAGEA7_PROTOCOL.md §4)."""
    f_sb, (lb_sb, _) = sb_stat['point'], sb_stat['ci95']
    f_res, (lb_res, _) = sbg_rescue_stat['point'], sbg_rescue_stat['ci95']
    f_reach = sbg_reach_stat['point']
    f_kd, (lb_kd, ub_kd) = kd_stat['point'], kd_stat['ci95']
    f_code, (lb_code, ub_code) = code_stat['point'], code_stat['ci95']

    if f_sb >= 0.80 and lb_sb > 0.50 and f_res >= 0.70 and lb_res > 0.50:
        return 'SEARCH'
    sb_failed_model = (f_sb <= 0.50) or (f_res <= 0.30 and f_reach >= 0.50)
    if sb_failed_model and f_kd >= 0.80 and lb_kd > 0.50 and f_code >= 0.80 and lb_code > 0.50:
        return 'MODEL'
    if (f_kd <= 0.50 and ub_kd < 0.75) or (f_code <= 0.50 and ub_code < 0.75):
        return 'INFO'
    return 'UNCLEAR'


def analyze_stageA7(
    rows: list[dict[str, Any]],
    *,
    boot_draws: int = BOOT_DRAWS,
    boot_seed: int = BOOT_SEED,
) -> dict[str, Any]:
    sb_stat = cluster_ratio_bootstrap(rows, lambda r: r['indicators']['sb_prefers_tbox'], boot_draws=boot_draws, boot_seed=boot_seed)
    sbg_rescue_stat = cluster_ratio_bootstrap(rows, lambda r: r['indicators']['sbg_rescues'], boot_draws=boot_draws, boot_seed=boot_seed)
    sbg_reach_stat = cluster_ratio_bootstrap(rows, lambda r: r['indicators']['sbg_reaches_tbox'], boot_draws=boot_draws, boot_seed=boot_seed)
    kd_stat = cluster_ratio_bootstrap(rows, lambda r: r['indicators']['kd_prefers_tbox'], boot_draws=boot_draws, boot_seed=boot_seed)
    code_stat = cluster_ratio_bootstrap(rows, lambda r: r['indicators']['code_prefers_truth'], boot_draws=boot_draws, boot_seed=boot_seed)
    tbox_rescue_stat = cluster_ratio_bootstrap(rows, lambda r: r['receiver']['tbox']['errors'] == 0, boot_draws=boot_draws, boot_seed=boot_seed)
    ldop_rescue_stat = cluster_ratio_bootstrap(rows, lambda r: r['receiver']['ldop']['errors'] == 0, boot_draws=boot_draws, boot_seed=boot_seed)

    verdict = verdict_a7(sb_stat, sbg_rescue_stat, sbg_reach_stat, kd_stat, code_stat)

    by_cell = {}
    for rho in (100, 150):
        for snr in CONF_SNRS:
            sub = [r for r in rows if int(r['rho']) == rho and int(r['snr']) == snr]
            if not sub:
                continue
            by_cell[f'{rho}_{snr}'] = dict(
                n=len(sub),
                sb_prefers_tbox=sum(r['indicators']['sb_prefers_tbox'] for r in sub),
                sbg_rescues=sum(r['indicators']['sbg_rescues'] for r in sub),
                tbox_rescues=sum(r['receiver']['tbox']['errors'] == 0 for r in sub),
                ldop_rescues=sum(r['receiver']['ldop']['errors'] == 0 for r in sub),
                kd_prefers_tbox=sum(r['indicators']['kd_prefers_tbox'] for r in sub),
                code_prefers_truth=sum(r['indicators']['code_prefers_truth'] for r in sub),
                median_delta_sb=float(np.median([r['nll_sb']['delta_sb_minus_tbox'] for r in sub])),
                median_delta_kd=float(np.median([r['nll_kd']['delta_sbbox_minus_tbox'] for r in sub])),
                mean_sb_mae=float(np.mean([r['sb_metric'] for r in sub])),
                mean_sbg_mae=float(np.mean([r['sbg_metric'] for r in sub])),
            )

    dsb = [r['nll_sb']['delta_sb_minus_tbox'] for r in rows]
    dkd = [r['nll_kd']['delta_sbbox_minus_tbox'] for r in rows]
    dsbg_vs_sb = [r['nll_sb']['delta_sb_minus_sbg'] for r in rows]
    sbg_t = [r['sbg_cpu'] for r in rows]

    return dict(
        n_conf_keys=len(rows),
        unique_frames=sb_stat['unique_frames'],
        boot_draws=boot_draws,
        boot_seed=boot_seed,
        verdict=verdict,
        proportions=dict(
            f_SB=sb_stat,
            f_SBG_rescue=sbg_rescue_stat,
            f_SBG_reaches_tbox=sbg_reach_stat,
            f_KD=kd_stat,
            f_code=code_stat,
            f_tbox_rescue=tbox_rescue_stat,
            f_ldop_rescue=ldop_rescue_stat,
        ),
        quantiles=dict(
            delta_sb_minus_tbox=dict(zip(('min', 'p10', 'p25', 'p50', 'p75', 'p90', 'max'),
                                         [float(v) for v in np.percentile(dsb, [0, 10, 25, 50, 75, 90, 100])])),
            delta_sb_minus_sbg=dict(zip(('min', 'p10', 'p25', 'p50', 'p75', 'p90', 'max'),
                                        [float(v) for v in np.percentile(dsbg_vs_sb, [0, 10, 25, 50, 75, 90, 100])])),
            delta_kd_sbbox_minus_tbox=dict(zip(('min', 'p10', 'p25', 'p50', 'p75', 'p90', 'max'),
                                               [float(v) for v in np.percentile(dkd, [0, 10, 25, 50, 75, 90, 100])])),
        ),
        doppler_summary=dict(
            sb_capped_mae_mean=float(np.mean([r['sb_metric'] for r in rows])),
            sbg_capped_mae_mean=float(np.mean([r['sbg_metric'] for r in rows])),
            sb_outlier_frac_mean=float(np.mean([r['sb_outlier_frac'] for r in rows])),
            sbg_outlier_frac_mean=float(np.mean([r['sbg_outlier_frac'] for r in rows])),
            sb_any_gt_0p25=int(sum(r['sb_max_err'] > OUTLIER_THRESH for r in rows)),
            sbg_any_gt_0p25=int(sum(r['sbg_max_err'] > OUTLIER_THRESH for r in rows)),
            sbg_cpu_mean_sec=float(np.mean(sbg_t)),
            sbg_cpu_median_sec=float(np.median(sbg_t)),
            sbg_cpu_p95_sec=float(np.percentile(sbg_t, 95)),
        ),
        by_cell=by_cell,
    )


def render_results_md(res: dict[str, Any]) -> str:
    a = res['analysis']
    pr = a['proportions']
    q = a['quantiles']
    ds = a['doppler_summary']

    def fstat(st: dict[str, Any]) -> str:
        return f"`{st['hits']}/{st['n']}` (`{100*st['point']:.2f}%`, 95% CI `[{100*st['ci95'][0]:.2f}%, {100*st['ci95'][1]:.2f}%]`)"

    lines = [
        '# Stage A7 Results: Decisive Diagnosis on High-SNR (4.5–5.0 dB) Stage A6 `SBdop` Failures',
        '',
        f'- Freeze commit: `{res["_config"]["freeze_commit"]}`',
        f'- Confirmation cohort: `{a["n_conf_keys"]}` keys across `{a["unique_frames"]}` unique physical frames (`snr in {res["_config"]["conf_snrs"]}`)',
        f'- Runtime: **{res["runtime"]["total_core_hours"]:.4f} core-hours** (cap `{res["runtime"]["cpu_cap_core_hours"]:.2f} h`, wall `{res["runtime"]["wall_seconds"]:.1f} s`)',
        f'- **Frozen Verdict**: **`{a["verdict"]}`**',
        '',
        '## Primary Proportions (Physical-Frame Cluster Bootstrap, 2000 draws, seed 20261125)',
        '',
        '| Observable | Count / Share [95% Cluster CI] |',
        '|---|---|',
        f'| `f_SB` (`L_SB(SB) > L_SB(truth_box)`) | {fstat(pr["f_SB"])} |',
        f'| `f_SBG_rescue` (truth-free `SBGdop` errors == 0) | {fstat(pr["f_SBG_rescue"])} |',
        f'| `f_SBG_reaches_tbox` (`L_SB(SBG) <= L_SB(truth_box) + 0.1`) | {fstat(pr["f_SBG_reaches_tbox"])} |',
        f'| `f_KD` (`L_KD(sb_box) > L_KD(truth_box)`) | {fstat(pr["f_KD"])} |',
        f'| `f_code` (coded valid-LDPC ML prefers truth over `SBdop`) | {fstat(pr["f_code"])} |',
        f'| `f_tbox_rescue` (oracle truth-box `SB` errors == 0) | {fstat(pr["f_tbox_rescue"])} |',
        f'| `f_ldop_rescue` (archived true-Doppler `ldop` errors == 0) | {fstat(pr["f_ldop_rescue"])} |',
        '',
        '## Breakdown by `(ρ, SNR)` Cell',
        '',
        '| ρ | SNR (dB) | n | `SB` prefers truth | `SBGdop` rescues | `tbox` rescues | `ldop` rescues | `KD` prefers truth | Median `ΔL_SB` (nats) |',
        '|---:|---:|---:|---:|---:|---:|---:|---:|---:|',
    ]
    for key, c in sorted(a['by_cell'].items()):
        rho_s, snr_s = key.split('_')
        lines.append(
            f'| {int(rho_s)/1000:.2f} | {int(snr_s)/100:.1f} | {c["n"]} | {c["sb_prefers_tbox"]}/{c["n"]} | '
            f'{c["sbg_rescues"]}/{c["n"]} | {c["tbox_rescues"]}/{c["n"]} | {c["ldop_rescues"]}/{c["n"]} | '
            f'{c["kd_prefers_tbox"]}/{c["n"]} | +{c["median_delta_sb"]:.2f} |'
        )
    lines += [
        '',
        '## Log-Likelihood Gap Quantiles & Doppler Diagnostics',
        '',
        f'- `ΔL_SB = L_SB(SB) - L_SB(truth_box)` (nats): min `{q["delta_sb_minus_tbox"]["min"]:.2f}`, '
        f'p25 `{q["delta_sb_minus_tbox"]["p25"]:.2f}`, median **`{q["delta_sb_minus_tbox"]["p50"]:.2f}`**, '
        f'p75 `{q["delta_sb_minus_tbox"]["p75"]:.2f}`, max `{q["delta_sb_minus_tbox"]["max"]:.2f}`.',
        f'- `ΔL_KD = L_KD(sb_box) - L_KD(truth_box)` (nats): min `{q["delta_kd_sbbox_minus_tbox"]["min"]:.2f}`, '
        f'median **`{q["delta_kd_sbbox_minus_tbox"]["p50"]:.2f}`**, max `{q["delta_kd_sbbox_minus_tbox"]["max"]:.2f}`.',
        f'- Capped MAE: `SB` `{ds["sb_capped_mae_mean"]:.4f}` -> `SBG` **`{ds["sbg_capped_mae_mean"]:.4f}`**; '
        f'path outlier frac (`>0.25` bin): `{100*ds["sb_outlier_frac_mean"]:.2f}%` -> **`{100*ds["sbg_outlier_frac_mean"]:.2f}%`**.',
        f'- Per-key `SBG` CPU time: mean `{ds["sbg_cpu_mean_sec"]:.2f} s`, median `{ds["sbg_cpu_median_sec"]:.2f} s`, p95 `{ds["sbg_cpu_p95_sec"]:.2f} s`.',
    ]
    return '\n'.join(lines) + '\n'


# --------------------------------------------------------------------------- File-IPC worker helper
def _load_runtime():
    import stageA  # noqa: E402
    import stageA2  # noqa: E402
    import stageA5  # noqa: E402
    from physical import daft  # noqa: E402

    C = stageA.setup()
    return C, stageA, stageA2, stageA5, daft


def _diag_worker(in_path: str, out_path: str):
    C, stageA, stageA2, stageA5, daft = _load_runtime()
    jobs = json.loads(Path(in_path).read_text(encoding='utf-8'))
    out = [eval_diag_key(C, stageA, stageA2, stageA5, daft, j['item'], j['a2_ldop']) for j in jobs]
    ar.atomic_write_text(Path(out_path), json.dumps(out, allow_nan=False))


def _g3_ctrl_worker(in_path: str, out_path: str):
    C, stageA, stageA2, stageA5, daft = _load_runtime()
    st, ctx = C['stage3'], C['ctx']
    c1, c2 = ctx.system.c1, ctx.system.c2
    jobs = json.loads(Path(in_path).read_text(encoding='utf-8'))
    out = []
    for item in jobs:
        frame, s, rho, snr = int(item['frame']), str(item['scenario']), int(item['rho']), int(item['snr'])
        if snr != DEV_SNR:
            raise RuntimeError(f'Firewall violation in G3 worker: snr={snr}')
        base = st.inputs(ctx, frame, s, rho)
        raw, obs, truth = st.observed(ctx, base, rho, snr)
        y = np.asarray(raw['y'], dtype=np.complex128)
        p_vec = np.asarray(raw['pilot'], dtype=np.complex128)
        d_vec = np.asarray(raw['data'], dtype=np.complex128)
        sigma2 = float(raw['sigma2'])
        vd = float(np.mean(np.abs(d_vec) ** 2))
        r = daft(y, c1, c2, True)
        p_t = daft(p_vec, c1, c2, True)
        geom = stageA5.precompute_delay_geometry(truth['l_i'], len(y), c1)
        fgeom = prepare_fast_geom(geom)
        shifted_pt = p_t[geom['cols']]

        nu_pw, g_pw = stageA5.estimate_pw(geom, p_t, r)
        nu_sb, g_sb = stageA5.estimate_sb(geom, p_t, r, vd, sigma2, nu_pw, g_pw)
        nll_sb, _ = stageA5.sb_nll_and_grad(np.concatenate([nu_sb, g_sb.real, g_sb.imag]), geom, shifted_pt, r, vd, sigma2)

        nu_sbg, g_sbg = estimate_sb_global(stageA5, fgeom, p_t, r, vd, sigma2)
        nll_sbg, _ = stageA5.sb_nll_and_grad(np.concatenate([nu_sbg, g_sbg.real, g_sbg.imag]), geom, shifted_pt, r, vd, sigma2)
        rec = one_arm_nu_detailed(C, stageA, stageA2, stageA5, daft, obs, truth, p_vec, r, vd, nu_sbg, g_order=g_sbg)
        out.append(dict(
            key=[frame, s, rho, snr],
            nll_sb=float(nll_sb),
            nll_sbg=float(nll_sbg),
            sbg_errors=int(rec['errors']),
            a6_errors=int(item['arms']['SBdop']['errors']),
        ))
    ar.atomic_write_text(Path(out_path), json.dumps(out, allow_nan=False))


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
            raise RuntimeError(f'{tag} worker {wi} exited with code {code}')
    rows: list[Any] = []
    for out_f in out_files:
        rows.extend(json.loads(out_f.read_text(encoding='utf-8')))
    return rows


# --------------------------------------------------------------------------- Gates G1-G4 (strictly snr == 400 dev only!)
def cmd_gate(args):
    print(sys.executable, flush=True)
    if platform.system() == 'Linux' and sys.executable != '/home/guoyikun/.conda/envs/AFDM/bin/python':
        raise RuntimeError(f'Wrong python interpreter: {sys.executable}')
    thread_env = ar.check_thread_env()
    if not 1 <= args.workers <= 28:
        raise ValueError('workers must be in 1..28')
    started = time.monotonic()

    gate_path = args.out.resolve()
    gate_path.parent.mkdir(parents=True, exist_ok=True)
    if gate_path.exists():
        gate_path.unlink()

    pinned_md5 = verify_pinned_code()
    manifests = verify_all_archives()
    C, stageA, stageA2, stageA5, daft = _load_runtime()
    st, ctx = C['stage3'], C['ctx']
    c1, c2 = ctx.system.c1, ctx.system.c2

    # G1: Fast NLL & gradient exactness (< 1e-10) on 4 dev keys (snr == 400) + 1 co-delay geometry
    g1_rows = []
    rng = np.random.default_rng(20261125)
    for frame, s, rho in ((41000, 'U', 100), (41001, 'G', 150), (41002, 'U', 150), (41003, 'G', 100)):
        raw, _, truth = st.observed(ctx, st.inputs(ctx, frame, s, rho), rho, DEV_SNR)
        y = np.asarray(raw['y'], dtype=np.complex128)
        p_vec = np.asarray(raw['pilot'], dtype=np.complex128)
        d_vec = np.asarray(raw['data'], dtype=np.complex128)
        s2 = float(raw['sigma2'])
        vd = float(np.mean(np.abs(d_vec) ** 2))
        r = daft(y, c1, c2, True)
        p_t = daft(p_vec, c1, c2, True)
        geom = stageA5.precompute_delay_geometry(truth['l_i'], len(y), c1)
        fgeom = prepare_fast_geom(geom)
        spt = p_t[geom['cols']]
        th = np.concatenate([rng.uniform(-2.5, 2.5, len(truth['l_i'])), rng.normal(0.0, 0.3, 2 * len(truth['l_i']))])
        nll_ref, gr_ref = stageA5.sb_nll_and_grad(th, geom, spt, r, vd, s2)
        nll_only = sb_nll_only_fast(stageA5, th[:8], th[8:16] + 1j * th[16:24], fgeom, spt, r, vd, s2)
        nll_fg, gr_fg = sb_nll_and_grad_fast(th, fgeom, spt, r, vd, s2, stageA5)
        dn1 = float(abs(nll_only - nll_ref))
        dn2 = float(abs(nll_fg - nll_ref))
        dg = float(np.max(np.abs(gr_fg - gr_ref)))
        g1_rows.append(dict(case=f'{frame}_{s}_{rho}', dnll_only=dn1, dnll_grad=dn2, max_dgrad=dg,
                            passed=bool(max(dn1, dn2, dg) < 1e-10)))
    # Synthetic co-delay case
    geom_cd = stageA5.precompute_delay_geometry(np.array([10, 10, 25, 40, 40, 55, 70, 85]), len(y), c1)
    fgeom_cd = prepare_fast_geom(geom_cd)
    spt_cd = p_t[geom_cd['cols']]
    nll_ref, gr_ref = stageA5.sb_nll_and_grad(th, geom_cd, spt_cd, r, vd, s2)
    nll_only = sb_nll_only_fast(stageA5, th[:8], th[8:16] + 1j * th[16:24], fgeom_cd, spt_cd, r, vd, s2)
    nll_fg, gr_fg = sb_nll_and_grad_fast(th, fgeom_cd, spt_cd, r, vd, s2, stageA5)
    dn1, dn2, dg = float(abs(nll_only - nll_ref)), float(abs(nll_fg - nll_ref)), float(np.max(np.abs(gr_fg - gr_ref)))
    g1_rows.append(dict(case='synthetic_codelay', dnll_only=dn1, dnll_grad=dn2, max_dgrad=dg,
                        passed=bool(max(dn1, dn2, dg) < 1e-10)))
    g1_pass = all(x['passed'] for x in g1_rows)
    print(f'G1 {"PASS" if g1_pass else "FAIL"} max_err={max(max(x["dnll_only"], x["dnll_grad"], x["max_dgrad"]) for x in g1_rows):.2e}', flush=True)

    # Load strictly DEV_SNR == 400 rows from stageA6 and stageA2 (NEVER touching 450 or 500!)
    dev_fails = []
    dev_oks = []
    for sp in sorted((HERE / 'out' / 'stageA6' / 'raw').glob('rows_shard*.jsonl.gz')):
        with gzip.open(sp, 'rt', encoding='utf-8') as fh:
            for line in fh:
                row = json.loads(line)
                if int(row['snr']) != DEV_SNR:
                    continue
                if int(row['arms']['SBdop']['errors']) > 0:
                    dev_fails.append(row)
                else:
                    dev_oks.append(row)
    dev_fails.sort(key=lambda x: (int(x['rho']), str(x['scenario']), int(x['frame'])))
    dev_oks.sort(key=lambda x: (int(x['rho']), str(x['scenario']), int(x['frame'])))

    a2_dev = {}
    for sp in sorted((HERE / 'out' / 'stageA2').glob('rows_shard*.jsonl.gz')):
        with gzip.open(sp, 'rt', encoding='utf-8') as fh:
            for line in fh:
                row = json.loads(line)
                if int(row['snr']) != DEV_SNR:
                    continue
                a2_dev[(int(row['frame']), str(row['scenario']), int(row['rho']), DEV_SNR)] = row['arms']['ldop']

    # G2 (i): Truth-invariance check on 2 dev keys
    inv_diffs = []
    for item in dev_fails[:2]:
        f, s, rho = int(item['frame']), str(item['scenario']), int(item['rho'])
        raw, _, truth = st.observed(ctx, st.inputs(ctx, f, s, rho), rho, DEV_SNR)
        y = np.asarray(raw['y'], dtype=np.complex128)
        p_vec = np.asarray(raw['pilot'], dtype=np.complex128)
        d_vec = np.asarray(raw['data'], dtype=np.complex128)
        vd = float(np.mean(np.abs(d_vec) ** 2))
        s2 = float(raw['sigma2'])
        r = daft(y, c1, c2, True)
        p_t = daft(p_vec, c1, c2, True)
        fgeom1 = prepare_fast_geom(stageA5.precompute_delay_geometry(truth['l_i'], len(y), c1))
        nu1, g1 = estimate_sb_global(stageA5, fgeom1, p_t, r, vd, s2)
        # Mutate truth['k_real'], truth['g_i'], raw['data'] in local copies and re-call
        truth['k_real'] = rng.uniform(-99.0, 99.0, len(truth['l_i']))
        truth['g_i'] = rng.normal(0.0, 50.0, len(truth['l_i'])) + 1j * rng.normal(0.0, 50.0, len(truth['l_i']))
        raw['data'] = rng.normal(0.0, 50.0, len(y))
        fgeom2 = prepare_fast_geom(stageA5.precompute_delay_geometry(truth['l_i'], len(y), c1))
        nu2, g2 = estimate_sb_global(stageA5, fgeom2, p_t, r, vd, s2)
        inv_diffs.append(float(max(np.max(np.abs(nu1 - nu2)), np.max(np.abs(g1 - g2)))))

    # G3 (includes G2(ii) replay check on 8 dev fails + 8 dev oks at 4.0 dB)
    sel_fails = dev_fails[:4] + [x for x in dev_fails if int(x['rho']) == 150][:4]
    sel_oks = dev_oks[:4] + [x for x in dev_oks if int(x['rho']) == 150][:4]
    diag_jobs = [
        dict(item=it, a2_ldop=a2_dev[(int(it['frame']), str(it['scenario']), int(it['rho']), DEV_SNR)])
        for it in sel_fails
    ]
    tmp_root = Path(os.environ.get('TMPDIR', '/data/guoyikun/tmp'))
    ipc_dir = tmp_root / f'stageA7_gates_ipc_{os.getpid()}'
    ipc_dir.mkdir(parents=True, exist_ok=True)
    try:
        fail_diag_rows = _spawn_map(_diag_worker, diag_jobs, min(args.workers, len(diag_jobs)), ipc_dir, 'g3f')
        ctrl_rows = _spawn_map(_g3_ctrl_worker, sel_oks, min(args.workers, len(sel_oks)), ipc_dir, 'g3c')
    finally:
        shutil.rmtree(ipc_dir, ignore_errors=True)

    max_replay_diff = max(float(r['sb_replay_diff']) for r in fail_diag_rows)
    g2_pass = bool(max(inv_diffs) == 0.0 and max_replay_diff < 1e-6)
    print(f'G2 {"PASS" if g2_pass else "FAIL"} inv_diff={max(inv_diffs):.1e} replay_diff={max_replay_diff:.2e}', flush=True)

    nll_nonworse_fail = sum(r['nll_sb']['at_sbg'] <= r['nll_sb']['at_sb'] + 1e-3 for r in fail_diag_rows)
    nll_nonworse_ctrl = sum(r['nll_sbg'] <= r['nll_sb'] + 1e-3 for r in ctrl_rows)
    dev_rescued = sum(r['indicators']['sbg_rescues'] for r in fail_diag_rows)
    ctrl_kept = sum(r['sbg_errors'] == 0 for r in ctrl_rows)
    g3_pass = bool(nll_nonworse_fail == 8 and nll_nonworse_ctrl == 8 and dev_rescued >= 6 and ctrl_kept == 8)
    print(
        f'G3 {"PASS" if g3_pass else "FAIL"} nll_ok={nll_nonworse_fail + nll_nonworse_ctrl}/16 '
        f'dev_rescued={dev_rescued}/8 ctrl_kept={ctrl_kept}/8',
        flush=True,
    )

    # G4: Cost projection for 38 confirmation keys <= 1.0 core-hour
    mean_diag_cpu = float(np.mean([r['total_cpu'] for r in fail_diag_rows]))
    raw_conf_h = (mean_diag_cpu * EXPECTED_CONF_N) / 3600.0 + OVERHEAD_HOURS
    proj_conf_h = raw_conf_h * COST_MARGIN
    g4_pass = bool(proj_conf_h <= STAGE_BUDGET_HOURS)
    print(f'G4 {"PASS" if g4_pass else "FAIL"} mean_cpu={mean_diag_cpu:.2f}s proj_conf_hours={proj_conf_h:.4f}', flush=True)

    all_passed = bool(g1_pass and g2_pass and g3_pass and g4_pass)
    gate_cpu_h = _used_cpu_seconds() / 3600.0
    payload = dict(
        _argv=sys.argv,
        _config=dict(
            python_executable=sys.executable,
            threads=thread_env,
            workers=args.workers,
            own_md5=own_md5(),
            pinned_code_md5=pinned_md5,
            archive_shards_verified={k: len(v) for k, v in manifests.items()},
            dev_snr_only=DEV_SNR,
        ),
        all_passed=all_passed,
        G1=dict(passed=g1_pass, rows=g1_rows),
        G2=dict(passed=g2_pass, truth_invariance_max_diff=max(inv_diffs), max_a6_sb_replay_diff=max_replay_diff),
        G3=dict(
            passed=g3_pass,
            nll_nonworse_fail=nll_nonworse_fail,
            nll_nonworse_ctrl=nll_nonworse_ctrl,
            dev_fail_rescued=dev_rescued,
            dev_ctrl_kept_ok=ctrl_kept,
        ),
        G4=dict(
            passed=g4_pass,
            mean_diag_cpu_sec=mean_diag_cpu,
            expected_conf_keys=EXPECTED_CONF_N,
            projected_hours_with_margin=proj_conf_h,
            stage_budget_cap_hours=STAGE_BUDGET_HOURS,
        ),
        gate_cpu_hours=gate_cpu_h,
        gate_wall_seconds=time.monotonic() - started,
    )
    ar.atomic_write_text(gate_path, json.dumps(payload, indent=2, allow_nan=False) + '\n')
    print(f'GATE_STATUS={"PASS" if all_passed else "FAIL"} gate_cpu_hours={gate_cpu_h:.4f}', flush=True)
    sys.exit(0 if all_passed else 1)


# --------------------------------------------------------------------------- Confirmation run (once!)
def cmd_run(args):
    print(sys.executable, flush=True)
    if platform.system() == 'Linux' and sys.executable != '/home/guoyikun/.conda/envs/AFDM/bin/python':
        raise RuntimeError(f'Wrong python interpreter: {sys.executable}')
    thread_env = ar.check_thread_env()
    if not re.fullmatch(r'[0-9a-f]{40}', args.freeze_commit):
        raise ValueError(f'freeze-commit must be 40-char hex SHA, got {args.freeze_commit!r}')
    if not 1 <= args.workers <= 28:
        raise ValueError('workers must be in 1..28')

    pinned_md5 = verify_pinned_code()
    live_own = own_md5()
    freeze_git_ok = verify_freeze_commit_if_git(args.freeze_commit, live_own)
    manifests = verify_all_archives()

    gate_path = args.gate.resolve()
    gate_bytes = gate_path.read_bytes()
    gate_md5 = hashlib.md5(gate_bytes).hexdigest()
    gate = json.loads(gate_bytes.decode('utf-8'))
    if not gate.get('all_passed'):
        raise RuntimeError('Refusing to run without passing stageA7_gate.json')
    if gate['_config']['own_md5'] != live_own:
        raise RuntimeError('stageA7_gate.json own_md5 mismatch; re-run gates before freezing')
    if gate['_config']['pinned_code_md5'] != pinned_md5:
        raise RuntimeError('Pinned dependency MD5 mismatch vs stageA7_gate.json')

    out_dir = args.out.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    res_json = out_dir / 'results.json'
    if res_json.exists():
        raise RuntimeError(f'Refusing to overwrite existing confirmation results {res_json}')

    wall_start = time.monotonic()

    # Load the 38 Stage A6 confirmation failures at snr in {450, 500}
    conf_items = []
    for sp in sorted((HERE / 'out' / 'stageA6' / 'raw').glob('rows_shard*.jsonl.gz')):
        with gzip.open(sp, 'rt', encoding='utf-8') as fh:
            for line in fh:
                r = json.loads(line)
                if int(r['snr']) in CONF_SNRS and int(r['arms']['SBdop']['errors']) > 0:
                    conf_items.append(r)
    conf_items.sort(key=lambda x: (int(x['rho']), int(x['snr']), str(x['scenario']), int(x['frame'])))
    if len(conf_items) != EXPECTED_CONF_N:
        raise RuntimeError(f'Expected {EXPECTED_CONF_N} confirmation keys, found {len(conf_items)}')

    target_keys = {(int(r['frame']), str(r['scenario']), int(r['rho']), int(r['snr'])) for r in conf_items}
    a2_ldop = {}
    for sp in sorted((HERE / 'out' / 'stageA2').glob('rows_shard*.jsonl.gz')):
        with gzip.open(sp, 'rt', encoding='utf-8') as fh:
            for line in fh:
                r = json.loads(line)
                k = (int(r['frame']), str(r['scenario']), int(r['rho']), int(r['snr']))
                if k in target_keys:
                    a2_ldop[k] = r['arms']['ldop']
    if len(a2_ldop) != EXPECTED_CONF_N:
        raise RuntimeError(f'Missing stageA2 ldop reference keys: {len(a2_ldop)} != {EXPECTED_CONF_N}')

    jobs = [
        dict(item=it, a2_ldop=a2_ldop[(int(it['frame']), str(it['scenario']), int(it['rho']), int(it['snr']))])
        for it in conf_items
    ]
    n_workers = min(args.workers, len(jobs))
    buckets = [jobs[i::n_workers] for i in range(n_workers)]
    tmp_root = Path(os.environ.get('TMPDIR', '/data/guoyikun/tmp'))
    ipc_dir = tmp_root / f'stageA7_run_ipc_{os.getpid()}'
    ipc_dir.mkdir(parents=True, exist_ok=True)

    mp_ctx = multiprocessing.get_context('spawn')
    running = {}
    out_files = []
    budget_hit = False
    print(f'Launching Stage A7 confirmation diagnosis on {len(jobs)} keys across {n_workers} workers...', flush=True)
    try:
        for wi, bucket in enumerate(buckets):
            in_f = ipc_dir / f'run_in_{wi:02d}.json'
            out_f = ipc_dir / f'run_out_{wi:02d}.json'
            in_f.write_text(json.dumps(bucket), encoding='utf-8')
            p = mp_ctx.Process(target=_diag_worker, args=(str(in_f), str(out_f)))
            p.start()
            running[p.sentinel] = (wi, p)
            out_files.append(out_f)
        while running:
            ready = wait(running, timeout=2.0)
            for s_ready in ready:
                wi, p = running.pop(s_ready)
                p.join()
                code = p.exitcode
                p.close()
                if code != 0:
                    raise RuntimeError(f'Worker {wi:02d} failed with exit code {code}')
            live_cpu = _used_cpu_seconds() + _active_pids_cpu([p.pid for _, p in running.values() if p.pid])
            if live_cpu >= STAGE_BUDGET_SEC - 60.0:
                budget_hit = True
                break
        if not budget_hit:
            rows = []
            for out_f in out_files:
                rows.extend(json.loads(out_f.read_text(encoding='utf-8')))
    finally:
        for _, p in running.values():
            p.terminate()
        for _, p in running.values():
            p.join()
            p.close()
        shutil.rmtree(ipc_dir, ignore_errors=True)

    if budget_hit or _used_cpu_seconds() >= STAGE_BUDGET_SEC:
        print(f'STOPPED_BUDGET ({_used_cpu_seconds()/3600:.4f} core-hours)', flush=True)
        sys.exit(BUDGET_EXIT_CODE)

    rows.sort(key=lambda x: (int(x['rho']), int(x['snr']), str(x['scenario']), int(x['frame'])))
    if len(rows) != EXPECTED_CONF_N:
        raise RuntimeError(f'Incomplete confirmation output: {len(rows)} != {EXPECTED_CONF_N}')

    analysis = analyze_stageA7(rows)
    total_cpu_h = _used_cpu_seconds() / 3600.0
    if total_cpu_h >= STAGE_BUDGET_HOURS:
        print(f'STOPPED_BUDGET after analysis ({total_cpu_h:.4f} core-hours)', flush=True)
        sys.exit(BUDGET_EXIT_CODE)

    results = dict(
        _argv=sys.argv,
        _config=dict(
            freeze_commit=args.freeze_commit,
            freeze_commit_git_verified=freeze_git_ok,
            python_executable=sys.executable,
            threads=thread_env,
            workers=args.workers,
            own_md5=live_own,
            pinned_code_md5=pinned_md5,
            gate_md5=gate_md5,
            archive_shards_verified={k: len(v) for k, v in manifests.items()},
            conf_snrs=list(CONF_SNRS),
        ),
        gates=dict(
            all_passed=gate['all_passed'],
            G1_passed=gate['G1']['passed'],
            G2_passed=gate['G2']['passed'],
            G3_passed=gate['G3']['passed'],
            G4_passed=gate['G4']['passed'],
        ),
        runtime=dict(
            total_core_hours=total_cpu_h,
            wall_seconds=time.monotonic() - wall_start,
            cpu_cap_core_hours=STAGE_BUDGET_HOURS,
        ),
        analysis=analysis,
        rows=rows,
    )
    ar.atomic_write_text(res_json, json.dumps(results, indent=2, allow_nan=False) + '\n')
    ar.atomic_write_text(out_dir / 'RESULTS.md', render_results_md(results))
    pr = analysis['proportions']
    print(
        f'STAGEA7_DONE verdict={analysis["verdict"]} '
        f'f_SB={pr["f_SB"]["hits"]}/{pr["f_SB"]["n"]} '
        f'f_SBG_rescue={pr["f_SBG_rescue"]["hits"]}/{pr["f_SBG_rescue"]["n"]} '
        f'f_KD={pr["f_KD"]["hits"]}/{pr["f_KD"]["n"]} '
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
