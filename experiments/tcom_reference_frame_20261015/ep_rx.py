"""P2b embedded-pilot (EP) frame and receiver (protocol.md section 5 + implementation note I2, task 10-15-tcom-reference-frame).

Frame (DAFT domain, N = 1024):
  one pilot at index PILOT = N/2, Q = 129 = 26 x 5 - 1 zero guards on each side (l_max = 25, alpha_max = 2, K = 2 N c1 = 5),
  765 QPSK data symbols from an LDPC (3,6) code with n = 1530 built by the project's own constructor
  (afdm_sp_joint_unrolled.e1_ldpc.build_code, d_v = 3, d_c = 6, seed 20260726, cache outside the frozen tree).
  The Gallager construction has rank 763 for n = 1530, so the actual k is 767 (rate .5013); goodput uses k = 767.
  Total frame energy N; the pilot carries the fraction rho_EP, the data symbols share (1 - rho_EP) N equally.
Channel: the project's exact CPP operator (supplement_g1.physical_channel_matrix), same as the SP arms.
Estimator (pilot region only, noise variance sigma2 known):
  successive detection: the 26 five-bin delay windows of the residual are energy-tested against
  tau = sigma2 * Gamma(5,1)^-1(1 - P_FA), P_FA = 1e-3 (fixed before any tuning; noise-only window energy / sigma2 ~ Gamma(5,1));
  the strongest window above tau gets a Doppler estimate on a 0.05-bin grid over [-2, 2] by maximising the normalised
  correlation with the exact fractional-Doppler pilot response (closed-form Dirichlet kernel), polished inside the winning
  grid cell; after every addition the Doppler of every selected path is re-refined against the others' cancelled residual
  (two coordinate sweeps) and the gains are re-solved by joint LS over the detected set.
Detector: soft-input LMMSE turbo detector (exact known zeros at the guards, pilot cancelled with the estimated / true channel),
  2 rounds, LDPC BP 50 iterations, extrinsic exchange.  The frozen fixed-channel TF detector (interventions.run_fixed_channel)
  cannot be used without modification: it estimates a full 1024-QPSK vector with one scalar prior variance and the frozen 2048-bit
  code mapping, so guard zeros cannot be represented.
"""
from __future__ import annotations

import time

import numpy as np
from scipy import linalg, special

N = 1024
ALPHA_MAX = 2
K_DOPP = 2 * ALPHA_MAX + 1          # 5 DAFT bins per delay
L_MAX = 25
Q_GUARD = (L_MAX + 1) * K_DOPP - 1   # 129 per side
PILOT = N // 2
N_DATA = N - (2 * Q_GUARD + 1)       # 765
CODE_N = 2 * N_DATA                  # 1530
CODE_SEED = 20260726
P_FA = 1e-3
NU_GRID = np.round(np.arange(-2.0, 2.0 + 1e-9, 0.05), 10)
MAX_PATHS = 16
LLR_CLIP = 20.
V_FLOOR = 1e-3                       # prior-variance floor relative to the data symbol energy
REGION = np.arange(-8, K_DOPP * L_MAX + 2 + 7)  # pilot-region offsets: windows [-2, 127] plus 6 tail bins each side + 2 slack


# ----------------------------------------------------------------------------- code / frame
class EP:
    """Static EP configuration for one system (c1, c2) and one LDPC code."""

    def __init__(self, system, code, prefix_length=102):
        self.c1, self.c2, self.n = float(system.c1), float(system.c2), int(system.N_total)
        if self.n != N or int(round(2 * N * self.c1)) != K_DOPP or abs(2 * N * self.c1 - K_DOPP) > 1e-12:
            raise ValueError('EP layout assumes N = 1024 and 2 N c1 = 5 (alpha_max = 2)')
        self.prefix = int(prefix_length)
        self.code = code
        if code['n'] != CODE_N:
            raise ValueError('EP code must have length 1530')
        self.k = int(code['k'])
        self.guard = np.concatenate([np.arange(PILOT - Q_GUARD, PILOT), np.arange(PILOT + 1, PILOT + Q_GUARD + 1)])
        mask = np.ones(N, bool)
        mask[PILOT - Q_GUARD:PILOT + Q_GUARD + 1] = False
        self.data_pos = np.flatnonzero(mask)
        assert len(self.data_pos) == N_DATA
        self.rows = (PILOT + REGION) % N
        self.chirp = np.exp(2j * np.pi * self.c2 * np.arange(N) ** 2)


def build_ep_code(cache_dir):
    """Same constructor and seed convention as the project's n = 2048 code (cache outside the frozen tree)."""
    from afdm_sp_joint_unrolled.e1_ldpc import build_code
    return build_code(CODE_N, d_v=3, d_c=6, seed=CODE_SEED, cache_dir=cache_dir)


def pilot_amplitude(rho_ep):
    return float(np.sqrt(rho_ep * N))


def data_energy(rho_ep):
    return float((1. - rho_ep) * N / N_DATA)


def make_frame(ep, info_bits, rho_ep):
    """DAFT-domain frame x (N,), transmitted data symbols (765,), codeword (1530,)."""
    from afdm_sp_joint_unrolled.e1_ldpc import encode, qpsk_map
    coded = encode(ep.code, info_bits)
    sym = np.sqrt(data_energy(rho_ep)) * qpsk_map(coded, scale=1)
    x = np.zeros(N, complex)
    x[ep.data_pos] = sym
    x[PILOT] = pilot_amplitude(rho_ep)
    return x, sym, coded


# ----------------------------------------------------------------------------- exact pilot response
def dirichlet(x, n=N):
    """(1/n) sum_{t=0}^{n-1} exp(2j pi x t / n), periodic in x with period n."""
    x = np.asarray(x, float)
    x = x - n * np.round(x / n)
    return np.exp(1j * np.pi * x * (n - 1) / n) * np.sinc(x) / np.sinc(x / n)


def pilot_response(ep, delay, nu, rows=None):
    """Column PILOT of the physical operator of one unit-gain path (delay, nu), at the given rows (default: the pilot region).

    nu may be an array; the result has shape (len(rows), len(nu)) for array nu, else (len(rows),).
    """
    rows = ep.rows if rows is None else np.asarray(rows)
    nu_arr = np.atleast_1d(np.asarray(nu, float))
    d = (rows - PILOT) % N
    a = nu_arr[None, :] + K_DOPP * delay
    kern = dirichlet(a - d[:, None])
    phase = np.exp(-2j * np.pi * (ep.c1 * delay ** 2 + delay * PILOT / N))
    out = (ep.chirp[rows] * np.conj(ep.chirp[PILOT]) * phase)[:, None] * kern
    return out if np.ndim(nu) else out[:, 0]


def channel_matrix(ep, delays, dopplers, gains):
    from afdm_sp_joint_unrolled.supplement_g1 import physical_channel_matrix
    return physical_channel_matrix(N, ep.c1, ep.c2, np.asarray(delays, int), np.asarray(dopplers, float),
                                   np.asarray(gains, complex), prefix_length=ep.prefix)


# ----------------------------------------------------------------------------- estimator
def _best_nu(ep, delay, residual_rows, amp):
    """Grid maximiser (step 0.05 over [-2, 2]) of the normalised correlation with the exact response, then three local
    polishing passes inside the winning cell (steps 0.01, 0.002 and 0.0004) so that grid-residual leakage stays far below the noise."""
    cols = amp * pilot_response(ep, delay, NU_GRID)
    score = np.abs(cols.conj().T @ residual_rows) ** 2 / np.sum(np.abs(cols) ** 2, axis=0)
    best = float(NU_GRID[int(np.argmax(score))])
    for width in (0.05, 0.01, 0.002):
        grid = np.linspace(best - width, best + width, 11)
        cols = amp * pilot_response(ep, delay, grid)
        s = np.abs(cols.conj().T @ residual_rows) ** 2 / np.sum(np.abs(cols) ** 2, axis=0)
        best = float(grid[int(np.argmax(s))])
    return best


def _ls(ep, delays, dopplers, yr, amp):
    cols = np.column_stack([amp * pilot_response(ep, l, nu) for l, nu in zip(delays, dopplers)])
    gains = np.linalg.lstsq(cols, yr, rcond=None)[0]
    return gains, yr - cols @ gains, cols


def estimate_paths(ep, y, sigma2, rho_ep, p_fa=P_FA, max_paths=MAX_PATHS):
    """Returns dict(delays, dopplers, gains, n_iterations, threshold)."""
    amp = pilot_amplitude(rho_ep)
    yr = np.asarray(y)[ep.rows]
    tau = float(sigma2 * special.gammainccinv(K_DOPP, p_fa))
    delays, dopplers = [], []
    gains = np.zeros(0, complex)
    residual = yr.copy()
    offset = -REGION[0]  # region index of PILOT
    for _ in range(max_paths):
        energy = np.array([np.sum(np.abs(residual[offset + K_DOPP * l - 2:offset + K_DOPP * l + 3]) ** 2) for l in range(L_MAX + 1)])
        energy[delays] = -np.inf
        l_star = int(np.argmax(energy))
        if not energy[l_star] > tau:
            break
        nu_star = _best_nu(ep, l_star, residual, amp)
        delays.append(l_star)
        dopplers.append(nu_star)
        gains, residual, cols = _ls(ep, delays, dopplers, yr, amp)
        for _sweep in range(2):  # coordinate re-refinement of every selected Doppler against the others' cancelled residual
            for i in range(len(delays)):
                others = residual + cols[:, i] * gains[i]
                dopplers[i] = _best_nu(ep, delays[i], others, amp)
                gains, residual, cols = _ls(ep, delays, dopplers, yr, amp)
    return dict(delays=np.array(delays, int), dopplers=np.array(dopplers, float), gains=np.asarray(gains, complex),
                n_paths=len(delays), threshold=tau)


# ----------------------------------------------------------------------------- detector
def gram(ep, H):
    """H_D^H H_D for the data columns."""
    HD = H[:, ep.data_pos]
    return HD, HD.conj().T @ HD


def _tri_inverse(A):
    L = linalg.cholesky(A, lower=True, check_finite=False)
    Linv, info = linalg.lapack.ztrtri(L, lower=1)
    if info != 0:
        raise np.linalg.LinAlgError('triangular inverse failed')
    return np.tril(Linv)


def lmmse_turbo(code, HD, G, yd, sigma2, Ed, rounds=2, maxiter=50):
    """Soft-input LMMSE turbo core shared by EP / EP-genie / SP-genie-LMMSE.

    HD: (N, n_sym) columns of the (estimated or true) operator belonging to the unknown symbols; G = HD^H HD (unscaled);
    yd: pilot-cancelled observation; Ed: energy of one unknown QPSK symbol.  Returns dict(decoded, info_hat, ok, first_round_mean, ...)."""
    from afdm_sp_joint_unrolled.e1_ldpc import extract_info
    from afdm_sp_joint_unrolled.supplement_messages import decoder_messages
    a = np.sqrt(Ed / 2.)
    n_sym = HD.shape[1]
    G = G / sigma2
    b0 = HD.conj().T @ yd / sigma2
    mu = np.zeros(n_sym, complex)
    v = np.full(n_sym, Ed)
    first_mean, iterations, dec = None, [], None
    for r in range(rounds):
        A = G + np.diag(1. / v)
        Linv = _tri_inverse(A)
        rhs = b0 + mu / v
        m = Linv.conj().T @ (Linv @ rhs)
        sig = np.sum(np.abs(Linv) ** 2, axis=0)  # diag(A^-1)
        if r == 0:
            first_mean = m.copy()
        prec = np.maximum(1. / sig - 1. / v, 1e-12)
        ve = 1. / prec
        ext = ve * (m / sig - mu / v)
        llr = np.clip(np.concatenate([4. * a * ext.real / ve, 4. * a * ext.imag / ve]), -LLR_CLIP, LLR_CLIP)
        dec = decoder_messages(code, llr, maxiter=maxiter)
        iterations.append(int(dec['iterations']))
        check = np.clip(np.asarray(dec['raw_check_extrinsic']), -LLR_CLIP, LLR_CLIP)
        mu = a * (np.tanh(check[:n_sym] / 2.) + 1j * np.tanh(check[n_sym:] / 2.))
        v = np.maximum(Ed - np.abs(mu) ** 2, V_FLOOR * Ed)
    decoded = np.asarray(dec['decoded'], np.uint8)
    return dict(decoded=decoded, info_hat=np.asarray(extract_info(code, decoded), np.uint8), ok=bool(dec['decode_ok']),
                first_round_mean=first_mean, iterations=iterations, llr=np.asarray(dec['incoming_llr']),
                app=np.asarray(dec['raw_app']))


def detect(ep, y, H, sigma2, rho_ep, rounds=2, maxiter=50, hd_gram=None, truth_symbols=None):
    """EP detector: pilot cancelled with H, 765 data columns, n = 1530 code."""
    amp = pilot_amplitude(rho_ep)
    yd = np.asarray(y) - amp * H[:, PILOT]
    HD, G = hd_gram if hd_gram is not None else gram(ep, H)
    return lmmse_turbo(ep.code, HD, G, yd, sigma2, data_energy(rho_ep), rounds=rounds, maxiter=maxiter)


def detect_sp(code, H, y, pilot, sigma2, rho, rounds=2, maxiter=50, hd_gram=None):
    """SP-genie-LMMSE (report-only calibration arm): the SP frame at pilot fraction rho, true H, pilot cancelled with H,
    the same LMMSE turbo core on all 1024 data symbols (energy 1 - rho each), n = 2048 code."""
    yd = np.asarray(y) - H @ np.asarray(pilot)
    HD, G = hd_gram if hd_gram is not None else (H, H.conj().T @ H)
    return lmmse_turbo(code, HD, G, yd, sigma2, 1. - rho, rounds=rounds, maxiter=maxiter)


# ----------------------------------------------------------------------------- one frame
def observe(ep, H_true, x, noise, sigma2):
    return H_true @ x + np.sqrt(sigma2) * np.asarray(noise)


def run_ep(ep, y, sigma2, rho_ep, info, H_true=None, genie_gram=None, arms=('EP', 'EPG')):
    """Run the estimated-channel receiver (EP) and/or the genie-channel receiver (EPG, needs H_true) on one observation."""
    out = {}
    if 'EP' in arms:
        t0 = time.perf_counter()
        est = estimate_paths(ep, y, sigma2, rho_ep)
        t_est = time.perf_counter() - t0
        if est['n_paths'] == 0:
            out['EP'] = dict(decoded=np.zeros(CODE_N, np.uint8), info_hat=np.zeros(ep.k, np.uint8), ok=False, seconds=time.perf_counter() - t0,
                             est=est, estimate_seconds=t_est, iterations=[])
        else:
            H_hat = channel_matrix(ep, est['delays'], est['dopplers'], est['gains'])
            det = detect(ep, y, H_hat, sigma2, rho_ep)
            out['EP'] = dict(det, est=est, estimate_seconds=t_est, seconds=time.perf_counter() - t0)
    if 'EPG' in arms:
        t0 = time.perf_counter()
        det = detect(ep, y, H_true, sigma2, rho_ep, hd_gram=genie_gram)
        out['EPG'] = dict(det, seconds=time.perf_counter() - t0)
    for res in out.values():
        res['info_errors'] = int(np.count_nonzero(res['info_hat'] != info))
    return out


def path_match(est, true_l, true_nu):
    """Diagnostics: exact delay-set recovery, worst Doppler error on matched delays, extra / missed delay counts."""
    tl = {int(l): float(nu) for l, nu in zip(true_l, true_nu)}
    el = {int(l): float(nu) for l, nu in zip(est['delays'], est['dopplers'])}
    missed = sorted(set(tl) - set(el))
    extra = sorted(set(el) - set(tl))
    err = [abs(el[l] - tl[l]) for l in tl if l in el]
    return dict(delays_exact=bool(not missed and not extra), n_missed=len(missed), n_extra=len(extra),
                max_doppler_error=(max(err) if err else None))
