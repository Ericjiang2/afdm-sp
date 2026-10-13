"""
afdm_baselines.py — Classical iterative (OMP + PIC) baseline receiver for AFDM SP.

Implements the joint OMP channel estimation + message-passing detection algorithm
ported from MATLAB's joint_omp_mp_ls_sparse, adapted for:
  - Full-domain ZC superimposed pilot (not random QPSK)
  - c2 ≠ 0  (Python chirp params include non-zero c2)
  - Terrestrial EVA/EPA channel model (5 paths default)

MATLAB → Python adaptation notes
  • MATLAB c2 = 0 everywhere  →  Python adds  +c2*(q²-p²)  to every phase formula
  • MATLAB pilot = random QPSK →  Python pilot = sqrt(rho)*zc_seq (full-domain ZC)
  • MATLAB GEN_H_DAFT phase: -c1·l² - l·p/N (c2=0 dropped)
                Python adds:  + c2·(q² - p²)

Algorithm overview (n_outer_iter outer iterations):
  1. OMP:     Estimate sparse channel h from (partially cleaned) pilot obs
  2. Reconst: Reconstruct H_eff (N×N) from OMP sparse gains
  3. DA-LS:   (iter > 0) subtract data interference → refine pilot observation
  4. PIC MP:  Parallel Interference Cancellation with damped constellation projection

Public module functions:
    construct_sensing_matrix   — build OMP dictionary Φ ∈ ℂ^{N×Q}
    omp_sparse                 — standard OMP
    reconstruct_H_from_omp     — sparse gains → N×N H_eff
    mp_detect_pic              — PIC detector with damped updates
    joint_omp_mp_iterative     — full joint algorithm

Mixin class:
    AFDMBaselinesMixin         — wrappers that bind to AFDMSystem attributes
        .omp_channel_estimate()
        .omp_lmmse_detect()
        .joint_iterative_detect()
"""
import numpy as np
from .physical_stride import physical_stride


# ================================================================
# 1. OMP sensing matrix
# ================================================================

def construct_sensing_matrix(N, x_pilot_scaled, c1, c2, l_max, k_max):
    """
    Build AFDM OMP sensing matrix Φ ∈ ℂ^{N × Q}.

    For a single unit-gain path at delay l, integer Doppler k, the expected
    DAFT-domain received signal at sub-carrier q is:

        Φ[q, col(l,k)] = exp( j2π(−c1·l² + c2·(q²−p²) − l·p/N) ) · x_p[p]
        where  p = (q − δ) mod N,  δ = l·(2·N·c1) + k.

    Column ordering:
        col(l, k) = l * K + (k + k_max)          (k in [−k_max, +k_max])

    Parameters
    ----------
    N               : int    — total DAFT-domain subcarriers
    x_pilot_scaled  : (N,)   — pilot frame  (e.g. sqrt(rho) * zc_seq)
    c1, c2          : float  — AFDM chirp parameters
    l_max           : int    — maximum delay tap index   (0 … l_max)
    k_max           : int    — maximum Doppler index     (−k_max … +k_max)

    Returns
    -------
    Phi : (N, Q) complex ndarray,   Q = (l_max+1) * (2*k_max+1)
    """
    K = 2 * k_max + 1                            # columns per delay row
    stride = physical_stride(N, c1)
    Q = (l_max + 1) * K                          # total dictionary columns
    q_arr = np.arange(N, dtype=np.float64)       # row indices (all N)

    Phi = np.zeros((N, Q), dtype=complex)

    col = 0
    for l in range(l_max + 1):
        l_sq = float(l) ** 2
        for k in range(-k_max, k_max + 1):
            delta = l * stride + k               # physical DAFT shift
            p_arr = (q_arr - delta) % N          # input sub-carrier indices (N,)
            phase = np.exp(1j * 2.0 * np.pi * (
                -c1 * l_sq
                + c2 * (q_arr ** 2 - p_arr ** 2)
                - float(l) * p_arr / N
            ))
            Phi[:, col] = phase * x_pilot_scaled[p_arr.astype(int)]
            col += 1

    return Phi


# ================================================================
# 2.  OMP solver
# ================================================================

def omp_sparse(y, Phi, sparsity):
    """
    Standard Orthogonal Matching Pursuit (OMP).

    Solves:  min ‖y − Φ·h‖₂   s.t.  ‖h‖₀ ≤ sparsity

    Parameters
    ----------
    y         : (N,) complex — observation vector
    Phi       : (N, Q) complex — sensing / dictionary matrix
    sparsity  : int — maximum number of non-zeros to recover

    Returns
    -------
    h_est   : (Q,) complex — sparse coefficient vector (zeros outside support)
    support : list[int]    — column indices selected
    """
    Q = Phi.shape[1]
    residual = y.copy()
    support = []
    Phi_H = Phi.conj().T          # precomputed conjugate-transpose

    for _ in range(sparsity):
        correlations = np.abs(Phi_H @ residual)     # (Q,) correlation magnitudes
        # Suppress already-selected columns
        for idx in support:
            correlations[idx] = 0.0
        new_idx = int(np.argmax(correlations))
        support.append(new_idx)

        # Least-squares on current support
        Phi_S = Phi[:, support]                     # (N, s)
        gains_S, _, _, _ = np.linalg.lstsq(Phi_S, y, rcond=None)

        # Update residual
        residual = y - Phi_S @ gains_S

        # Early stop: relative residual power negligible
        if np.linalg.norm(residual) < 1e-10 * np.linalg.norm(y):
            break

    # Final LS refinement on full support
    h_est = np.zeros(Q, dtype=complex)
    if support:
        Phi_S = Phi[:, support]
        gains_final, _, _, _ = np.linalg.lstsq(Phi_S, y, rcond=None)
        for i, idx in enumerate(support):
            h_est[idx] = gains_final[i]

    return h_est, support


def extract_delay_doppler_from_h(h, n_paths, max_delay, max_doppler):
    """MATLAB-style top-magnitude extraction from flattened delay-Doppler vector."""
    h = np.asarray(h)
    if h.size == 0 or n_paths <= 0:
        return (
            np.array([], dtype=int),
            np.array([], dtype=int),
            np.array([], dtype=complex),
        )
    take = min(int(n_paths), h.size)
    top_idx = np.argsort(np.abs(h))[::-1][:take]
    gains = h[top_idx]
    num_dopplers = 2 * max_doppler + 1
    delays = top_idx // num_dopplers
    dopplers = (top_idx % num_dopplers) - max_doppler
    return delays.astype(int), dopplers.astype(int), gains.astype(complex)


def construct_sensing_matrix_matlab(N, x_pilot_scaled, c1, l_max, k_max):
    """MATLAB `construct_afdm_sensing_matrix()` port with `+c1*l^2` convention."""
    K = 2 * k_max + 1
    Q = (l_max + 1) * K
    q_arr = np.arange(N, dtype=np.float64)
    Phi = np.zeros((N, Q), dtype=complex)

    col = 0
    for l in range(l_max + 1):
        for k in range(-k_max, k_max + 1):
            loc_val = k + 2.0 * N * c1 * l
            p_arr = np.mod(np.round(q_arr - loc_val).astype(int), N)
            phase = np.exp(1j * ((2.0 * np.pi / N) * (N * c1 * (l ** 2) - q_arr * l)))
            y_col = np.zeros(N, dtype=complex)
            np.add.at(y_col, p_arr, phase * x_pilot_scaled)
            Phi[:, col] = y_col
            col += 1

    return Phi


# ================================================================
# 3. Reconstruct H_eff from OMP gains
# ================================================================

def reconstruct_H_from_omp(N, h_omp, k_max, l_max, c1, c2, threshold=1e-3):
    """
    Reconstruct the N×N effective channel matrix from OMP sparse gains.

    Uses the same phase formula as AFDMEnvMixin._reconstruct_H_eff_from_taps_2d:

        H[m_arr[n], n] += g · exp( j2π(−c1·l² + c2·(m²−n²) − l·n/N) )
        where  m = (n + δ) mod N,  δ = l·(2·N·c1) + k.

    Parameters
    ----------
    N         : int    — total subcarriers
    h_omp     : (Q,)   complex — OMP gain vector
    k_max     : int    — maximum Doppler index
    l_max     : int    — maximum delay index
    c1, c2    : float  — chirp parameters
    threshold : float  — relative gain threshold (entries below → skip)

    Returns
    -------
    H_est : (N, N) complex ndarray
    """
    K = 2 * k_max + 1
    stride = physical_stride(N, c1)
    n_arr = np.arange(N, dtype=np.float64)
    H_est = np.zeros((N, N), dtype=complex)

    # Relative threshold: skip paths below threshold × peak gain
    max_gain = np.max(np.abs(h_omp))
    if max_gain < 1e-30:
        return H_est              # no signal — return zeros
    thr_abs = threshold * max_gain

    col = 0
    for l in range(l_max + 1):
        l_sq = float(l) ** 2
        l_f  = float(l)
        for k in range(-k_max, k_max + 1):
            g = h_omp[col]
            col += 1
            if abs(g) < thr_abs:
                continue

            delta  = l * stride + k
            m_arr  = (n_arr + delta) % N            # output row indices (float)
            m_idx  = m_arr.astype(int)

            phase = np.exp(1j * 2.0 * np.pi * (
                -c1 * l_sq
                + c2 * (m_arr ** 2 - n_arr ** 2)
                - l_f * n_arr / N
            ))
            H_est[m_idx, np.arange(N)] += g * phase

    return H_est


def reconstruct_H_from_omp_matlab(N, h_omp, k_max, l_max, c1, threshold=1e-3):
    """MATLAB `GEN_H_DAFT()` reconstruction with `+c1*l^2` convention and `c2=0`."""
    K = 2 * k_max + 1
    q_arr = np.arange(N, dtype=np.float64)
    H_est = np.zeros((N, N), dtype=complex)

    max_gain = np.max(np.abs(h_omp)) if np.size(h_omp) else 0.0
    if max_gain < 1e-30:
        return H_est
    thr_abs = threshold * max_gain

    col = 0
    for l in range(l_max + 1):
        for k in range(-k_max, k_max + 1):
            g = h_omp[col]
            col += 1
            if abs(g) < thr_abs:
                continue
            loc_val = k + 2.0 * N * c1 * l
            p_arr = np.mod(np.round(q_arr - loc_val).astype(int), N)
            phase = np.exp(1j * ((2.0 * np.pi / N) * (N * c1 * (l ** 2) - q_arr * l)))
            H_est[p_arr, np.arange(N)] += g * phase

    return H_est


# ================================================================
# 4. PIC (Parallel Interference Cancellation) detector
# ================================================================

def mp_detect_pic(y_data, H, sigma2, constellation, n_iter=15, damp=0.5):
    """
    Parallel Interference Cancellation (PIC) detector with damped updates.

    Implements a simplified Gaussian message-passing / PIC loop:

        z        = H^H·r / (diag(H^H·H) + σ²)    [MRC correction]
        r        = y − H·x̂_hard                   [residual]
        x̂_hard  = nearest constellation point
        x̂(t+1) = α·x̂_hard + (1−α)·x̂(t)         [damped update]

    Initialisation: matched-filter output (MF-ZF) hard-projected to constellation.

    Parameters
    ----------
    y_data       : (N,) complex — pilot-cancelled received signal
    H            : (N, N) complex — estimated effective channel
    sigma2       : float  — noise variance σ²
    constellation : (M,) complex — symbol alphabet at data scale
    n_iter       : int   — PIC iterations
    damp         : float — damping factor α (0 = no update, 1 = pure hard)

    Returns
    -------
    x_detect : (N,) complex — hard-decided data symbols
    """
    # Column energies: diag(H^H · H)
    HH_diag = np.sum(np.abs(H) ** 2, axis=0)        # (N,)
    inv_denom = 1.0 / np.maximum(HH_diag + sigma2, 1e-30)

    # Initialise: matched-filter → hard decision
    x_mf = H.conj().T @ y_data * inv_denom
    x_hat = np.array(
        [constellation[np.argmin(np.abs(xv - constellation))] for xv in x_mf],
        dtype=complex)

    for _ in range(n_iter):
        r = y_data - H @ x_hat                       # (N,)  residual
        x_new = x_hat + H.conj().T @ r * inv_denom   # MRC correction
        x_hard = np.array(
            [constellation[np.argmin(np.abs(xv - constellation))] for xv in x_new],
            dtype=complex)
        x_hat = damp * x_hard + (1.0 - damp) * x_hat

    return np.array(
        [constellation[np.argmin(np.abs(xv - constellation))] for xv in x_hat],
        dtype=complex)


def mp_detect_bp(y, H, sigma2, constellation, n_iter=20, threshold=1e-4, damp=0.5,
                 return_soft=False):
    """Port of MATLAB `MP_detection_optimized()` full BP detector.

    Parameters
    ----------
    return_soft : bool
        When True, also returns per-symbol BP posteriors as
        ``(x_est, mu_post_arr, var_post_arr)`` where mu_post_arr is complex
        (posterior mean in constellation space) and var_post_arr is float
        (posterior variance). Backward-compatible: default is False.
    """
    N = H.shape[0]
    if N == 0:
        return np.zeros(0, dtype=complex)

    mask = np.abs(H) >= threshold
    row_idx, col_idx = np.nonzero(mask)
    h_vals = H[row_idx, col_idx]
    E = len(h_vals)
    if E == 0:
        return np.zeros(N, dtype=complex)

    row_edges = [[] for _ in range(N)]
    col_edges = [[] for _ in range(N)]
    for e, (r, c) in enumerate(zip(row_idx, col_idx)):
        row_edges[r].append(e)
        col_edges[c].append(e)

    prior_mean = np.mean(constellation)
    prior_var = float(np.var(constellation))
    mu_v2o = np.full(E, prior_mean, dtype=complex)
    var_v2o = np.full(E, prior_var, dtype=float)
    mu_o2v = np.zeros(E, dtype=complex)
    var_o2v = np.ones(E, dtype=float)

    for _ in range(n_iter):
        mu_old = mu_v2o.copy()

        for d in range(N):
            edges = row_edges[d]
            if not edges:
                continue
            h_d = h_vals[edges]
            mu_in = mu_v2o[edges]
            var_in = var_v2o[edges]
            z_total = y[d] - np.sum(h_d * mu_in)
            V_total = sigma2 + np.sum((np.abs(h_d) ** 2) * var_in)

            for local_idx, e in enumerate(edges):
                h_e = h_d[local_idx]
                mu_e = mu_in[local_idx]
                var_e = var_in[local_idx]
                z_ext = z_total + h_e * mu_e
                V_ext = max(V_total - (abs(h_e) ** 2) * var_e, sigma2 * 0.1)
                if abs(h_e) > 1e-10:
                    var_o2v[e] = max(V_ext / (abs(h_e) ** 2), 1e-10)
                    mu_o2v[e] = z_ext / h_e
                else:
                    var_o2v[e] = 1e10
                    mu_o2v[e] = 0.0

        for n in range(N):
            edges = col_edges[n]
            if not edges:
                continue
            var_in = var_o2v[edges]
            mu_in = mu_o2v[edges]
            prec_total = 1.0 / prior_var + np.sum(1.0 / var_in)
            mean_total = prior_mean / prior_var + np.sum(mu_in / var_in)

            for e in edges:
                var_e = var_o2v[e]
                mu_e = mu_o2v[e]
                prec_ext = max(prec_total - 1.0 / var_e, 1e-10)
                mean_ext = mean_total - mu_e / var_e
                var_ext = 1.0 / prec_ext
                mu_ext = var_ext * mean_ext
                dist_sq = np.abs(constellation - mu_ext) ** 2
                log_prob = -dist_sq / (2.0 * var_ext)
                log_prob -= np.max(log_prob)
                prob = np.exp(log_prob)
                prob /= np.sum(prob)
                mu_new = np.sum(prob * constellation)
                var_new = max(np.sum(prob * (np.abs(constellation) ** 2)) - abs(mu_new) ** 2, 1e-10)
                mu_v2o[e] = (1.0 - damp) * mu_old[e] + damp * mu_new
                var_v2o[e] = var_new

        denom = max(np.linalg.norm(mu_v2o), 1e-10)
        if np.linalg.norm(mu_v2o - mu_old) / denom < 1e-4:
            break

    x_est       = np.zeros(N, dtype=complex)
    mu_post_arr  = np.zeros(N, dtype=complex)
    var_post_arr = np.zeros(N, dtype=float)
    for n in range(N):
        edges = col_edges[n]
        if not edges:
            x_est[n]       = prior_mean
            mu_post_arr[n] = prior_mean
            var_post_arr[n] = prior_var
            continue
        var_in = var_o2v[edges]
        mu_in = mu_o2v[edges]
        prec_total = 1.0 / prior_var + np.sum(1.0 / var_in)
        mean_total = prior_mean / prior_var + np.sum(mu_in / var_in)
        var_post = 1.0 / max(prec_total, 1e-10)
        mu_post = var_post * mean_total
        x_est[n]        = constellation[np.argmin(np.abs(constellation - mu_post))]
        mu_post_arr[n]  = mu_post   # complex soft mean
        var_post_arr[n] = var_post  # posterior variance

    if return_soft:
        return x_est, mu_post_arr, var_post_arr
    return x_est


# ================================================================
# 5. Joint OMP + MP iterative algorithm
# ================================================================

def joint_omp_mp_iterative(y_daft, x_pilot_scaled, N, c1, c2, l_max, k_max,
                            sigma2, constellation_data, n_paths=5,
                            n_outer_iter=5, rho=0.3,
                            pic_iter=15, pic_damp=0.5,
                            mp_mode='pic', threshold_mp=1e-4,
                            gamma_h=0.7, gamma_x=0.6,
                            lambda_ls_factor=1e-3,
                            tau_h_factor=0.01, tau_h_sigma_factor=0.1,
                            k_leak=2, eps_stop_rel=1e-3,
                            update_sigma2=True,
                            phase_convention='python',
                            return_soft=False,
                            data_pos=None,
                            return_trajectory=False,
                            oracle_support=None,
                            reomp_per_iter=False,
                            n_paths_reomp=None):
    """
    oracle_support : (K_ora,) int ndarray — optional. When given, the first
        outer iteration *skips* OMP and uses these column indices (into the Q
        dictionary columns) as the seed support.  Used by the diagnose_joint_ber
        experiment to isolate whether the BER gap is OMP-caused or downstream.

    reomp_per_iter : bool — when True, at outer iteration >= 1, rebuild the
        sensing matrix on the data-aided carrier x_pilot + x_hard and re-run
        OMP before the existing DA-LS gain refit. Cluster-expand + DA-LS +
        sparse MP-BP downstream remain byte-identical to the baseline path.
        Default False preserves the OMP-once + iterate-only design. Used by
        the TCOM W3-W4 ablation (`--with-ours-reomp` in paired_learned_eval).
        Cf. Cao 2024 ICCT Eq 24 "W^(n) = Psi_p + Psi_d^(n-1)".
    n_paths_reomp : int | None — OMP sparsity for the re-OMP step. None
        (default) reuses `n_paths`. Setting to `n_paths * (2 * k_leak + 1)`
        approximates the cluster-expanded virtual-tap count.
    """
    """
    Joint OMP channel estimation + MP iterative receiver.

    Faithful port of MATLAB ``joint_omp_mp_ls_sparse()``:

      - Iter 1 : OMP determines sparse support → cluster-expand ±k_leak
                  → reconstruct H → MP detect data
      - Iter 2+: Data-Aided LS (pilot + hard-decided data as known signal)
                  → reconstruct H → MP detect data
      - Channel damping (gamma_h), symbol damping (gamma_x)
      - Channel sparsification after each iteration
      - Adaptive noise variance estimation
      - Early-stop on relative residual improvement

    Parameters
    ----------
    y_daft            : (N,) complex
    x_pilot_scaled    : (N,) complex — sqrt(rho)*zc_seq
    N                 : int
    c1, c2            : float
    l_max, k_max      : int
    sigma2            : float — initial noise variance
    constellation_data : (M,) complex — QPSK at data scale √(1-ρ)/√2
    n_paths           : int — OMP sparsity
    n_outer_iter      : int
    rho               : float
    pic_iter          : int — MP inner iterations
    pic_damp          : float — MP damping
    gamma_h           : float — channel estimate damping
    gamma_x           : float — symbol estimate damping
    lambda_ls_factor  : float — Tikhonov regularisation coefficient
    tau_h_factor      : float — relative sparsification threshold
    tau_h_sigma_factor: float — noise-based sparsification threshold
    k_leak            : int — cluster-support Doppler half-width
    eps_stop_rel      : float — early-stop threshold
    update_sigma2     : bool — adaptive noise estimation

    Returns
    -------
    x_data_hat : (N,) complex
    H_est      : (N, N) complex
    """
    K = 2 * k_max + 1
    Q = (l_max + 1) * K
    stride = physical_stride(N, c1)
    P_data = 1.0 - rho
    data_pos_arr = np.arange(N, dtype=np.int64) if data_pos is None else np.asarray(data_pos, dtype=np.int64)

    # Build OMP sensing matrix once (pilot only, scaled by sqrt(rho))
    if phase_convention == 'matlab':
        Phi = construct_sensing_matrix_matlab(N, x_pilot_scaled, c1, l_max, k_max)
    else:
        Phi = construct_sensing_matrix(N, x_pilot_scaled, c1, c2, l_max, k_max)

    # State variables
    H_hat = np.zeros((N, N), dtype=complex)
    x_soft_scaled = np.zeros(N, dtype=complex)
    sigma2_eff = sigma2
    lambda_ls = max(1e-6, lambda_ls_factor * sigma2_eff)
    prev_resnorm = np.inf

    # Support set (delays, dopplers, gains)
    support_delays = np.array([], dtype=int)
    support_dopplers = np.array([], dtype=int)
    gains_S = np.array([], dtype=complex)
    seed_delays = np.array([], dtype=int)
    seed_dopplers = np.array([], dtype=int)
    trajectory = [] if return_trajectory else None

    for outer in range(n_outer_iter):

        # ============ (A) Channel Estimation Update ============
        if outer == 0:
            # --- First iteration: OMP (or oracle support, if provided) ---
            if oracle_support is not None and len(oracle_support) > 0:
                # Diagnostic: skip OMP, use caller-provided dict column indices.
                support_idx = list(int(i) for i in oracle_support)
                # Seed gains with a LS fit on the provided support columns.
                Phi_S = Phi[:, support_idx]
                gains_on_support, _, _, _ = np.linalg.lstsq(Phi_S, y_daft, rcond=None)
                h_omp = np.zeros(Q, dtype=complex)
                for col_i, gv in zip(support_idx, gains_on_support):
                    h_omp[col_i] = gv
            else:
                h_omp, support_idx = omp_sparse(y_daft, Phi, n_paths)

            # Decode column indices → (l, k) pairs + gains
            s_delays = []
            s_dopplers = []
            s_gains = []
            for idx in support_idx:
                g = h_omp[idx]
                l_dec = idx // K
                k_dec = (idx % K) - k_max
                s_delays.append(l_dec)
                s_dopplers.append(k_dec)
                s_gains.append(g)
            seed_delays = np.asarray(s_delays, dtype=int)
            seed_dopplers = np.asarray(s_dopplers, dtype=int)

            # Cluster-support expansion: add ±k_leak Doppler neighbours
            exp_delays = []
            exp_dopplers = []
            exp_gains = []
            for i in range(len(s_delays)):
                for m in range(-k_leak, k_leak + 1):
                    k_new = s_dopplers[i] + m
                    if abs(k_new) > k_max:
                        continue
                    exp_delays.append(s_delays[i])
                    exp_dopplers.append(k_new)
                    exp_gains.append(s_gains[i] if m == 0 else 0.0)

            # Merge duplicate (l, k) pairs
            if len(exp_delays) > 0:
                pairs = np.column_stack([exp_delays, exp_dopplers])
                gains_arr = np.array(exp_gains, dtype=complex)
                unique_pairs, inverse = np.unique(pairs, axis=0, return_inverse=True)
                merged_gains = np.zeros(len(unique_pairs), dtype=complex)
                np.add.at(merged_gains, inverse, gains_arr)
                support_delays = unique_pairs[:, 0].astype(int)
                support_dopplers = unique_pairs[:, 1].astype(int)
                gains_S = merged_gains
            else:
                support_delays = np.array([], dtype=int)
                support_dopplers = np.array([], dtype=int)
                gains_S = np.array([], dtype=complex)

        else:
            # --- Subsequent iterations: Data-Aided LS ---
            # Hard-decide current symbol estimate
            x_hard_scaled = np.array(
                [constellation_data[np.argmin(np.abs(s - constellation_data))]
                 for s in x_soft_scaled], dtype=complex)
            # Total known signal = pilot + hard-decided data
            x_total = x_pilot_scaled + x_hard_scaled

            if reomp_per_iter:
                # Re-OMP on data-aided sensing matrix (cf. Cao 2024 Eq 24).
                # Updates support_delays / support_dopplers / gains_S; the
                # downstream DA-LS body then refits gains on the new support.
                if phase_convention == 'matlab':
                    Phi_n = construct_sensing_matrix_matlab(N, x_total, c1, l_max, k_max)
                else:
                    Phi_n = construct_sensing_matrix(N, x_total, c1, c2, l_max, k_max)
                K_omp = int(n_paths) if n_paths_reomp is None else int(n_paths_reomp)
                h_omp_n, support_idx_n = omp_sparse(y_daft, Phi_n, K_omp)
                # Decode column indices -> (l, k) pairs + gains (mirror iter-0)
                s_delays_n = []
                s_dopplers_n = []
                s_gains_n = []
                for idx in support_idx_n:
                    g = h_omp_n[idx]
                    l_dec = idx // K
                    k_dec = (idx % K) - k_max
                    s_delays_n.append(l_dec)
                    s_dopplers_n.append(k_dec)
                    s_gains_n.append(g)
                seed_delays = np.asarray(s_delays_n, dtype=int)
                seed_dopplers = np.asarray(s_dopplers_n, dtype=int)
                # Cluster-support expansion ±k_leak (mirror iter-0)
                exp_delays_n = []
                exp_dopplers_n = []
                exp_gains_n = []
                for i in range(len(s_delays_n)):
                    for m in range(-k_leak, k_leak + 1):
                        k_new = s_dopplers_n[i] + m
                        if abs(k_new) > k_max:
                            continue
                        exp_delays_n.append(s_delays_n[i])
                        exp_dopplers_n.append(k_new)
                        exp_gains_n.append(s_gains_n[i] if m == 0 else 0.0)
                # Merge duplicate (l, k) pairs
                if len(exp_delays_n) > 0:
                    pairs_n = np.column_stack([exp_delays_n, exp_dopplers_n])
                    gains_arr_n = np.array(exp_gains_n, dtype=complex)
                    unique_pairs_n, inverse_n = np.unique(
                        pairs_n, axis=0, return_inverse=True)
                    merged_gains_n = np.zeros(len(unique_pairs_n), dtype=complex)
                    np.add.at(merged_gains_n, inverse_n, gains_arr_n)
                    support_delays = unique_pairs_n[:, 0].astype(int)
                    support_dopplers = unique_pairs_n[:, 1].astype(int)
                    gains_S = merged_gains_n
                else:
                    support_delays = np.array([], dtype=int)
                    support_dopplers = np.array([], dtype=int)
                    gains_S = np.array([], dtype=complex)

            # Build dictionary columns for current support
            num_paths = len(support_delays)
            if num_paths > 0:
                A_total = np.zeros((N, num_paths), dtype=complex)
                n_arr = np.arange(N, dtype=np.float64)
                for p in range(num_paths):
                    l_p = int(support_delays[p])
                    k_p = int(support_dopplers[p])
                    a_col = np.zeros(N, dtype=complex)
                    if phase_convention == 'matlab':
                        q_arr = n_arr
                        loc_val = k_p + 2.0 * N * c1 * l_p
                        p_arr = np.mod(np.round(q_arr - loc_val).astype(int), N)
                        phase = np.exp(1j * ((2.0 * np.pi / N) * (N * c1 * (l_p ** 2) - q_arr * l_p)))
                        np.add.at(a_col, p_arr, phase * x_total)
                    else:
                        delta = l_p * stride + k_p
                        m_arr = ((n_arr.astype(int) + delta) % N)
                        m_f = m_arr.astype(np.float64)
                        phase = np.exp(1j * 2.0 * np.pi * (
                            -c1 * (l_p ** 2)
                            + c2 * (m_f ** 2 - n_arr ** 2)
                            - float(l_p) * n_arr / N
                        ))
                        a_col[m_arr] = phase * x_total
                    A_total[:, p] = a_col

                # Weighted LS with Tikhonov: (A'A + λI)^{-1} (A'y + λ·g_prev)
                AhA = A_total.conj().T @ A_total
                Ahy = A_total.conj().T @ y_daft
                g_new = np.linalg.solve(
                    AhA + lambda_ls * np.eye(num_paths),
                    Ahy + lambda_ls * gains_S)
                gains_S = g_new

        # Reconstruct channel from support + gains
        if phase_convention == 'matlab':
            h_vec = np.zeros((l_max + 1) * K, dtype=complex)
            for l_p, k_p, g in zip(support_delays, support_dopplers, gains_S):
                h_vec[int(l_p) * K + (int(k_p) + k_max)] = g
            H_new = reconstruct_H_from_omp_matlab(N, h_vec, k_max, l_max, c1, threshold=0.0)
        else:
            H_new = np.zeros((N, N), dtype=complex)
            n_arr = np.arange(N, dtype=np.float64)
            for p in range(len(support_delays)):
                l_p = int(support_delays[p])
                k_p = int(support_dopplers[p])
                g = gains_S[p]
                delta = l_p * stride + k_p
                m_arr = ((n_arr.astype(int) + delta) % N)
                m_f = m_arr.astype(np.float64)
                phase = np.exp(1j * 2.0 * np.pi * (
                    -c1 * (l_p ** 2)
                    + c2 * (m_f ** 2 - n_arr ** 2)
                    - float(l_p) * n_arr / N
                ))
                H_new[m_arr, np.arange(N)] += g * phase

        # Channel damping
        H_hat = (1.0 - gamma_h) * H_hat + gamma_h * H_new

        # Sparsification: zero out small entries
        max_h = np.max(np.abs(H_hat))
        if max_h > 0:
            tau_rel = tau_h_factor * max_h
            tau_sigma = tau_h_sigma_factor * np.sqrt(sigma2_eff)
            tau = max(tau_rel, tau_sigma)
            mask = np.abs(H_hat) < tau
            H_hat[mask] = 0.0

        # ============ (B) Data Detection: MP ============
        y_data = y_daft - H_hat @ x_pilot_scaled
        if mp_mode == 'bp':
            x_mp, mu_soft_iter, var_soft_iter = mp_detect_bp(
                y_data, H_hat, sigma2_eff, constellation_data,
                n_iter=pic_iter, threshold=threshold_mp, damp=pic_damp,
                return_soft=True)
        else:
            x_mp = mp_detect_pic(y_data, H_hat, sigma2_eff, constellation_data,
                                 n_iter=pic_iter, damp=pic_damp)
            h_power = np.sum(np.abs(H_hat) ** 2, axis=0)
            var_soft_iter = sigma2_eff / np.maximum(h_power, 1e-10)
            mu_soft_iter = x_mp.copy()

        # Symbol damping
        x_soft_scaled = (1.0 - gamma_x) * x_soft_scaled + gamma_x * x_mp

        # ============ (C) Adaptive Noise Estimation ============
        if update_sigma2 and outer > 0:
            x_hard_for_res = np.array(
                [constellation_data[np.argmin(np.abs(s - constellation_data))]
                 for s in x_soft_scaled], dtype=complex)
            x_total_res = x_pilot_scaled + x_hard_for_res
            residual = y_daft - H_hat @ x_total_res
            sigma2_new = float(np.sum(np.abs(residual) ** 2)) / N
            sigma2_eff = 0.7 * sigma2_eff + 0.3 * max(sigma2_new, 1e-12)
            lambda_ls = max(1e-6, lambda_ls_factor * sigma2_eff)

        # ============ (D) Early Stop ============
        x_hard_stop = np.array(
            [constellation_data[np.argmin(np.abs(s - constellation_data))]
             for s in x_soft_scaled], dtype=complex)
        x_total_stop = x_pilot_scaled + x_hard_stop
        curr_resnorm = float(np.sum(np.abs(y_daft - H_hat @ x_total_stop) ** 2))
        if return_trajectory:
            support_mask = np.zeros(Q, dtype=np.float32)
            seed_mask = np.zeros(Q, dtype=np.float32)
            gain_dense = np.zeros(Q, dtype=np.complex64)
            for l_p, k_p in zip(seed_delays, seed_dopplers):
                idx = int(l_p) * K + (int(k_p) + k_max)
                if 0 <= idx < Q:
                    seed_mask[idx] = 1.0
            for l_p, k_p, g_p in zip(support_delays, support_dopplers, gains_S):
                idx = int(l_p) * K + (int(k_p) + k_max)
                if 0 <= idx < Q:
                    support_mask[idx] = 1.0
                    gain_dense[idx] = np.complex64(g_p)

            mu_d = mu_soft_iter[data_pos_arr]
            var_d = np.maximum(var_soft_iter[data_pos_arr], 1e-10)
            var_cmp = np.maximum(var_d / 2.0, 1e-10)
            llr_r = 2.0 * np.real(mu_d) / var_cmp
            llr_i = 2.0 * np.imag(mu_d) / var_cmp
            trajectory.append({
                "seed_mask": seed_mask,
                "support_mask": support_mask,
                "gain_dense": gain_dense,
                "sigma2_eff": np.float32(sigma2_eff),
                "residual_norm": np.float32(curr_resnorm),
                "mu_x": np.concatenate([np.real(mu_d), np.imag(mu_d)]).astype(np.float32),
                "var_x": np.concatenate([var_cmp, var_cmp]).astype(np.float32),
                "llr_x": np.concatenate([llr_r, llr_i]).astype(np.float32),
            })
        if prev_resnorm < np.inf:
            rel_improve = (prev_resnorm - curr_resnorm) / max(curr_resnorm, 1e-12)
            if 0 <= rel_improve < eps_stop_rel:
                break
        prev_resnorm = curr_resnorm

    if return_soft:
        # Compute per-symbol soft posterior for teacher-label generation.
        y_data_final = y_daft - H_hat @ x_pilot_scaled
        if mp_mode == 'bp':
            # Re-run one final BP pass to extract per-symbol posteriors.
            _, mu_soft, var_soft = mp_detect_bp(
                y_data_final, H_hat, sigma2_eff, constellation_data,
                n_iter=pic_iter, threshold=threshold_mp, damp=pic_damp,
                return_soft=True)
        else:
            # Matched-filter approximation: var_n = sigma2 / ||h_n||^2.
            h_power = np.sum(np.abs(H_hat) ** 2, axis=0)   # (N,)
            var_soft = sigma2_eff / np.maximum(h_power, 1e-10)
            mu_soft  = x_soft_scaled.copy()
        if return_trajectory:
            return (
                x_soft_scaled, H_hat, mu_soft, var_soft,
                {
                    "stages": trajectory,
                    "iters_used": len(trajectory),
                    "stopped_early": len(trajectory) < n_outer_iter,
                },
            )
        return x_soft_scaled, H_hat, mu_soft, var_soft

    if return_trajectory:
        return (
            x_soft_scaled, H_hat,
            {
                "stages": trajectory,
                "iters_used": len(trajectory),
                "stopped_early": len(trajectory) < n_outer_iter,
            },
        )
    return x_soft_scaled, H_hat


# ================================================================
# 6. Mixin class — integrates with AFDMSystem via MRO
# ================================================================

class AFDMBaselinesMixin:
    """
    Mixin providing classical OMP + MP baseline receivers.

    Relies on attributes provided by AFDMEnvMixin (via MRO):
        self.N_total, self.c1, self.c2
        self.k_max_cap, self.l_max_cap, self.rho
        self._zc_seq
        self._lmmse_detect_np(H_est, y_daft, x_p_frame, data_pos, sigma_w2)
    """

    # Default fallback sparsity. Prefer `self.P_paths` from AFDMEnvMixin when present.
    _OMP_N_PATHS: int = 10

    def _get_omp_n_paths(self):
        """Return the OMP sparsity level calibrated to the active channel model.

        For SP (superimposed pilot) mode, uses ``P_paths`` (physical path
        count) rather than P_actual (Dirichlet-expanded virtual-tap count).
        SP observations contain data interference that limits OMP's effective
        SNR; using a high sparsity causes overfitting.

        NOTE: MATLAB uses ``sparsLevel = P_actual`` because it operates in EP
        (embedded pilot) mode with clean observations.  If the Python system
        is ever switched to EP mode, this should return ``self._P_actual``.
        """
        mode = getattr(self, 'omp_sparsity_mode', 'p_paths')
        if mode == 'p_actual':
            return int(getattr(self, '_P_actual', getattr(self, 'P_paths', self._OMP_N_PATHS)))
        return int(getattr(self, 'P_paths', self._OMP_N_PATHS))

    def _get_default_pilot_scaled(self):
        pilot_kind = getattr(self, 'sp_pilot_kind', 'zc')
        if pilot_kind == 'random-qpsk':
            qpsk = np.array([1+1j, 1-1j, -1+1j, -1-1j], dtype=complex) / np.sqrt(2)
            return np.sqrt(self.rho) * qpsk[np.random.randint(0, 4, self.N_total)]
        return np.sqrt(self.rho) * self._zc_seq

    def _use_matlab_baseline_phase(self):
        return getattr(self, 'baseline_phase_convention', 'python') == 'matlab'

    def omp_channel_estimate(self, y_daft, x_pilot_scaled=None):
        """
        OMP-based channel estimation using system parameters.

        Parameters
        ----------
        y_daft          : (N,) complex — received DAFT-domain vector
        x_pilot_scaled  : (N,) or None — if None, defaults to sqrt(rho)*zc_seq

        Returns
        -------
        H_est : (N, N) complex — estimated effective channel
        """
        if x_pilot_scaled is None:
            x_pilot_scaled = self._get_default_pilot_scaled()
        N = self.N_total
        if self._use_matlab_baseline_phase():
            Phi = construct_sensing_matrix_matlab(
                N, x_pilot_scaled, self.c1,
                self.l_max_cap, self.k_max_cap)
        else:
            Phi = construct_sensing_matrix(
                N, x_pilot_scaled, self.c1, self.c2,
                self.l_max_cap, self.k_max_cap)
        h_omp, _ = omp_sparse(y_daft, Phi, self._get_omp_n_paths())
        if self._use_matlab_baseline_phase():
            return reconstruct_H_from_omp_matlab(
                N, h_omp, self.k_max_cap, self.l_max_cap, self.c1)
        return reconstruct_H_from_omp(
            N, h_omp, self.k_max_cap, self.l_max_cap, self.c1, self.c2)

    def dictionary_ls_estimate(self, y_daft, sigma2, x_pilot_scaled=None):
        """
        Dictionary-based ridge LS channel estimation (matches MATLAB LS baseline).

        Builds the OMP sensing matrix Φ (scaled by √ρ), then solves:
            h_LS = (Φ'Φ + λI)⁻¹ Φ'y
        where λ = 1e-2 × σ²_eff × N.

        In SP mode, the observation y contains data interference with power
        P_data = (1-ρ).  The effective noise for the dictionary regression is
        σ²_eff = σ² + P_data, NOT just σ².  Using only σ² under-regularises
        and causes severe over-fitting to the data interference, especially
        at high SNR.

        The top-P entries are extracted by magnitude (matching MATLAB
        ``extract_delay_doppler_from_h``), and used to reconstruct H_eff.

        Parameters
        ----------
        y_daft : (N,) complex — received DAFT-domain signal
        sigma2 : float        — noise variance

        Returns
        -------
        H_est : (N, N) complex — estimated effective channel
        """
        N = self.N_total
        P_data = 1.0 - self.rho
        if x_pilot_scaled is None:
            x_pilot_scaled = self._get_default_pilot_scaled()
        if self._use_matlab_baseline_phase():
            Phi = construct_sensing_matrix_matlab(
                N, x_pilot_scaled, self.c1,
                self.l_max_cap, self.k_max_cap)
        else:
            Phi = construct_sensing_matrix(
                N, x_pilot_scaled, self.c1, self.c2,
                self.l_max_cap, self.k_max_cap)

        Q = Phi.shape[1]

        # Ridge regression: In SP mode, effective noise = thermal + data interference
        sigma_eff = sigma2 + P_data
        lambda_ridge = 1e-2 * sigma_eff * N
        h_ls = np.linalg.solve(
            Phi.conj().T @ Phi + lambda_ridge * np.eye(Q),
            Phi.conj().T @ y_daft)

        # Extract top-P entries by magnitude (physical path count, not P_actual)
        # Note: P_actual (Dirichlet-expanded) extracts too many noise entries
        # from the dense ridge solution.  P_paths captures the main peaks only.
        n_extract = self._get_omp_n_paths()
        top_indices = np.argsort(np.abs(h_ls))[::-1][:n_extract]

        # Zero out all but top-P entries
        h_ls_sparse = np.zeros_like(h_ls)
        h_ls_sparse[top_indices] = h_ls[top_indices]

        if self._use_matlab_baseline_phase():
            return reconstruct_H_from_omp_matlab(
                N, h_ls_sparse, self.k_max_cap, self.l_max_cap, self.c1)
        return reconstruct_H_from_omp(
            N, h_ls_sparse, self.k_max_cap, self.l_max_cap, self.c1, self.c2)

    def omp_mp_detect(self, y_daft, x_p_only, sigma2, num_iter=20, threshold=1e-4):
        """OMP channel estimate followed by selectable MP detector."""
        H_est = self.omp_channel_estimate(y_daft, x_p_only)
        y_data = y_daft - H_est @ x_p_only
        qpsk = np.array([1+1j, 1-1j, -1+1j, -1-1j], dtype=complex) / np.sqrt(2)
        const = np.sqrt(1.0 - self.rho) * qpsk
        if getattr(self, 'baseline_mp_detector', 'pic') == 'bp':
            x_hat = mp_detect_bp(y_data, H_est, sigma2, const,
                                 n_iter=num_iter, threshold=threshold)
        else:
            x_hat = mp_detect_pic(y_data, H_est, sigma2, const,
                                  n_iter=num_iter, damp=0.5)
        return x_hat, H_est

    def omp_lmmse_detect(self, y_daft, x_p_only, data_pos, sigma2):
        """
        OMP channel estimation followed by LMMSE detection (OMP+LMMSE baseline).

        Parameters
        ----------
        y_daft   : (N,) complex — received DAFT-domain vector
        x_p_only : (N,) complex — pilot-only frame (sqrt(rho)*zc_seq, zero elsewhere)
        data_pos : (n_d,) int   — data symbol positions
        sigma2   : float        — noise variance

        Returns
        -------
        x_hat : (n_d,) complex — LMMSE-detected data symbols
        H_est : (N, N) complex — OMP channel estimate
        """
        x_pilot_scaled = x_p_only.copy()
        H_est = self.omp_channel_estimate(y_daft, x_pilot_scaled)
        x_hat = self._lmmse_detect_np(H_est, y_daft, x_p_only, data_pos, sigma2)
        return x_hat, H_est

    def joint_iterative_detect(self, y_daft, x_p_only, data_pos, sigma2,
                                n_outer=5):
        """
        Joint OMP↔MP iterative detector (faithful MATLAB port).

        Uses DA-LS, cluster-support expansion, channel/symbol damping,
        channel sparsification, and adaptive noise estimation — matching
        MATLAB ``joint_omp_mp_ls_sparse()``.

        Parameters
        ----------
        y_daft   : (N,) complex — received DAFT-domain vector
        x_p_only : (N,) complex — pilot-only frame
        data_pos : (n_d,) int   — data symbol positions
        sigma2   : float        — noise variance
        n_outer  : int          — outer loop iterations (default 5)

        Returns
        -------
        x_hat : (n_d,) complex — detected data symbols (√(1−ρ)·QPSK scale)
        H_est : (N, N) complex — final channel estimate
        """
        N = self.N_total
        rho = self.rho

        # Constellation at data power: sqrt(1-rho) * QPSK / sqrt(2)
        QPSK  = np.array([1+1j, 1-1j, -1+1j, -1-1j], dtype=complex) / np.sqrt(2)
        const = np.sqrt(1.0 - rho) * QPSK

        x_pilot_scaled = np.sqrt(rho) * self._zc_seq

        # k_leak for cluster-support expansion (matches MATLAB K_LEAK)
        k_leak = getattr(self, 'k_leak', 2)

        x_data_all, H_est = joint_omp_mp_iterative(
            y_daft, x_pilot_scaled, N,
            self.c1, self.c2,
            self.l_max_cap, self.k_max_cap,
            sigma2, const,
            n_paths=self._get_omp_n_paths(),
            n_outer_iter=n_outer,
            rho=rho,
            k_leak=k_leak,
            mp_mode=getattr(self, 'baseline_mp_detector', 'pic'),
            phase_convention=getattr(self, 'baseline_phase_convention', 'python'))

        # Return only entries at data_pos (consistent with _lmmse_detect_np)
        return x_data_all[data_pos], H_est
