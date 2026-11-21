"""Upper-bound screen, core (task 10-08-doppler-cluster; research/ub-screen-20261015.md, FROZEN 2026-10-15).  Plain numpy/scipy; reuses ib_screen_core (imported, not modified).

Per-frame score (section 2, bits):   u = J + Cst - f     (E[u] >= I(d; y); no QR, no channel realisation)
  f(d)  = log2 det(I + C_s(d) / sigma2),   C_s = sum_l D_l(s) R_l D_l(s)^H,  D_l(s) = diag(cp_l * S_l s),  s = pt + xt            (identical to the screen's f)
  J(G)  = log2 det(Q + C_p) - log2 det Q,  Q = sigma2 I + a diag(c),  C_p = sum_l D_l(pt) R_l D_l(pt)^H                           (identical to the screen's J)
  Cst   = sum_n log2(1 + a c_n / sigma2),  c_n = sum_l R_l[n, n]  (MODEL: ModelRef.cvec; PHYS and RAY: c_n = 1)
References: MODEL / PHYS exactly as the screen (tap covariance R_l = F F^H shared by all taps).  RAY-genie: given counts r_l = 1 + Poisson(3) and angles theta_lj ~ U[0, 2 pi) the generator's
tap sequence a_l[n] = sum_j g_lj exp(2 pi i nu_lj n / N), nu = 2 cos(theta), g_lj ~ CN(0, 1/(L r_l)) is Gaussian with R_l = F_l F_l^H, F_l = E_l / sqrt(L r_l), E_l[n, j] = exp(2 pi i nu_lj n / N)
(rank r_l, diag R_l = 1/L); taps have different R_l, so f and J use the K-side form with the stacked factor (total rank sum_l r_l <= K_SWITCH).
Seed domain: SeedSequence([20261015, 0x49425542, stage_id, L, frame, comp_id]), stage ids decision=1, ro=2, grid=3, gate=4 (timing = 5: unscored probe, not in the spec), comp ids delays=1, data=2, rays=5.
"""
from __future__ import annotations

import math
from pathlib import Path
import time

import numpy as np

import ib_screen_core as C

N = C.N
HERE = Path(__file__).resolve().parent
OUT = HERE / 'out' / 'ub_screen'
SEED_ROOT, SEED_DOMAIN = 20261015, 0x49425542  # "IBUB"
STAGE_ID = {'decision': 1, 'ro': 2, 'grid': 3, 'gate': 4, 'timing': 5}
COMP = {'delays': 1, 'data': 2, 'rays': 5}
ALPHA, TAU, TAU_EMP = 0.05, 1.0, 1.154
RATIOS = (1.10, 1.25)
RO_RATIOS = (1.0, 1.5, 2.0)
N_ENDPOINTS = len(C.CONDS) * len(RATIOS) * 3  # 5 conditions x 2 ratios x 3 references = 30
K_SWITCH = 700
CONDS = C.CONDS
COND_REPORT = (9.5, .3)  # Kc_best censored (>= 320): report-only column
FRAMES_DECISION = {'MODEL': 8192, 'PHYS': 4096, 'RAY': 4096}


def delta_endpoint():
    return ALPHA / N_ENDPOINTS


def test_L(cond, ratio):
    """L = ceil(ratio * Kc_best / 8) (K = 8 L is the cliff axis)."""
    return int(math.ceil(ratio * C.KC_BEST[cond] / 8. - 1e-12))


def decision_Ls():
    return sorted({test_L(c, r) for c in CONDS for r in RATIOS})


def ro_Ls():
    return sorted({test_L(c, r) for c in CONDS for r in RO_RATIOS})


# ------------------------------------------------------------------------------------------------------------ randomness
def rng_for(stage, L, frame, comp):
    return np.random.default_rng(np.random.SeedSequence([SEED_ROOT, SEED_DOMAIN, STAGE_ID[stage], int(L), int(frame), COMP[comp]]))


def draw_common(stage, L, frame):
    """Delays (C1 law: L distinct uniform on {0..100}, sorted) and i.i.d. unit-power QPSK; exactly the law of C.draw_common in this seed domain."""
    delays = np.sort(rng_for(stage, L, frame, 'delays').choice(101, size=int(L), replace=False)).astype(int)
    bits = rng_for(stage, L, frame, 'data').integers(0, 2, size=(N, 2))
    q = ((2 * bits[:, 0] - 1) + 1j * (2 * bits[:, 1] - 1)) / math.sqrt(2.)
    return delays, q


def ray_params(rng, L):
    """Ray counts, angles and unit-variance complex normals in exactly the draw order of C.draw_rays: counts = 1 + Poisson(3, L); then per tap theta ~ U[0, 2 pi) (r), z (r)."""
    L = int(L)
    counts = 1 + rng.poisson(3, size=L)
    thetas, zs = [], []
    for t in range(L):
        r = int(counts[t])
        thetas.append(rng.uniform(0., 2. * np.pi, r))
        zs.append((rng.standard_normal(r) + 1j * rng.standard_normal(r)) / math.sqrt(2.))
    return counts, thetas, zs


def ray_factors(thetas, counts, L):
    """F_l = E_l / sqrt(L r_l), E_l[n, j] = exp(2 pi i * 2 cos(theta_lj) * n / N): R_l = F_l F_l^H is the tap covariance of the generator's ray law given (counts, angles)."""
    k = np.arange(N)
    return [np.exp(2j * np.pi * np.outer(k, 2. * np.cos(th)) / N) / math.sqrt(L * int(r)) for th, r in zip(thetas, counts)]


# ------------------------------------------------------------------------------------------------------------ references
class RayRef:
    """RAY-genie: per-frame factors (ray_factors); c_n = sum_l R_l[n, n] = 1 and beta = sum_l max_n R_l[n, n] = 1 exactly."""
    name = 'RAY'

    def cvec(self, L):
        return np.ones(N)

    def beta(self, L):
        return 1.0


def cst(ref, L, conds=CONDS):
    """Cst = sum_n log2(1 + a c_n / sigma2) for every condition; RAY: N log2(1 + a / sigma2)."""
    s2, _rho, a = C.cond_arrays(conds)
    if ref.name == 'RAY':
        return N * np.log2(1. + a / s2)
    return cst_arr(ref.cvec(L), a, s2)


def cst_arr(c, a, s2):
    """Cst for an arbitrary diagonal c (toy gate: c = diag R); a, s2 arrays over conditions (or scalars)."""
    a, s2 = np.atleast_1d(a), np.atleast_1d(s2)
    return np.sum(np.log2(1. + (a / s2)[:, None] * np.asarray(c, float)[None, :]), axis=1)


def ub_score(f, J, cs):
    """Per-frame UB score u = J + Cst - f."""
    return np.asarray(J) + np.asarray(cs) - np.asarray(f)


def range_b(ref, L, cond):
    """Proven range of u: b_u = B_f + B_J (f in [0, B_f], J in [0, B_J]); beta = ref.beta(L) (MODEL 4.344, PHYS 1, RAY 1)."""
    r = C.term_ranges(ref, L, cond)
    return r['f'] + r['J']


# --------------------------------------------------------------------------------------------------------- RAY-genie f and J
def ray_blocks(consts, delays, q, Fs):
    """Bp, Bx (N, K): column block l = diag-scaling of F_l by u_l(pt) (resp. u_l(xt)), K = sum_l r_l;  C_s = (sqrt(rho) Bp + sqrt(a) Bx)(...)^H."""
    Up, Ux = consts.u(consts.ptil, delays), consts.u(consts.idaft(q), delays)
    Bp = np.hstack([Up[:, l, None] * F for l, F in enumerate(Fs)])
    Bx = np.hstack([Ux[:, l, None] * F for l, F in enumerate(Fs)])
    return Bp, Bx


def ray_f_and_j(consts, delays, q, Fs, conds=CONDS):
    """K-side f and J of the RAY-genie reference (Q = (sigma2 + a) I since c = 1).  Hermitised before every Cholesky.  Returns f, J, K (the stacked rank)."""
    s2, rho, a = C.cond_arrays(conds)
    K = int(sum(F.shape[1] for F in Fs))
    if K > K_SWITCH:
        raise ValueError(f'RAY stacked rank {K} > {K_SWITCH}')
    Bp, Bx = ray_blocks(consts, delays, q, Fs)
    Gpp, Gpx, Gxx = Bp.conj().T @ Bp, Bp.conj().T @ Bx, Bx.conj().T @ Bx
    idx = np.arange(K)
    f, J = np.empty(len(conds)), np.empty(len(conds))
    for c in range(len(conds)):
        M = rho[c] * Gpp + math.sqrt(rho[c] * a[c]) * (Gpx + Gpx.conj().T) + a[c] * Gxx
        M = (M + M.conj().T) / 2. / s2[c]
        M[idx, idx] += 1.
        f[c] = C.logdet2_chol(M)[0]
        Z = rho[c] * Gpp / (s2[c] + a[c])
        Z = (Z + Z.conj().T) / 2.
        Z[idx, idx] += 1.
        J[c] = C.logdet2_chol(Z)[0]
    return f, J, K


def frame_u(consts, ref, stage, L, frame, conds=CONDS, common=None):
    """f, J, u for one frame and every condition (the frame is shared across the conditions).  MODEL/PHYS need no channel draw."""
    t0 = time.perf_counter()
    delays, q = common if common is not None else draw_common(stage, L, frame)
    if ref.name == 'RAY':
        counts, thetas, _z = ray_params(rng_for(stage, L, frame, 'rays'), L)
        f, J, extra = ray_f_and_j(consts, delays, q, ray_factors(thetas, counts, L), conds)
        info = dict(rank=extra)
    else:
        f, J, side = C.f_and_j(consts, ref, L, delays, q, conds)
        info = dict(side=side)
    u = ub_score(f, J, cst(ref, L, conds))
    return dict(f=f, J=J, u=u, sec=time.perf_counter() - t0, **info)


# -------------------------------------------------------------------------------------------------------------- statistic
def ucb(u, b_u, delta=None):
    """Combined-score Bernstein UCB: mean + sqrt(2 S^2 ln(2/delta) / n) + 7 b ln(2/delta) / (3 (n - 1)); returns a dict (bits, per frame)."""
    delta = delta_endpoint() if delta is None else delta
    u = np.asarray(u, float)
    n = len(u)
    S2 = float(np.var(u, ddof=1))
    ln = math.log(2. / delta)
    var_term = math.sqrt(2. * S2 * ln / n)
    rng_term = 7. * b_u * ln / (3. * (n - 1))
    mean = float(u.mean())
    return dict(n=n, mean=mean, S=math.sqrt(S2), var_term=var_term, range_term=rng_term, ucb=mean + var_term + rng_term, b_u=b_u, delta=delta)
