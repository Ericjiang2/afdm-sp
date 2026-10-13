"""
joint_omp_bpmp_afdm.py — Standalone AFDM + OMP + BP-MP joint iterative simulator.

Single-file extraction of the project's canonical joint iterative receiver
(afdm_sp_joint_unrolled/afdm_baselines.py::joint_omp_mp_iterative with
mp_mode='bp'), self-contained — no project imports.

Pipeline per Monte-Carlo frame:
  1. Draw UWA acoustic channel: 5 Rayleigh paths, exponential PDP,
     per-path Gaussian velocity → fractional Doppler.
  2. Expand fractional Doppler into integer virtual taps via Dirichlet kernel.
  3. Build effective DAFT channel H_eff (N×N, Frobenius-normalised to √N).
  4. Build SP frame: sqrt(1-ρ)·QPSK + sqrt(ρ)·ZC pilot on every subcarrier.
  5. y_daft = A · H_time · A^H · x_full + n, σ²=1/SNR (fixed Es/N0).
  6. Joint OMP↔BP-MP iterative receiver (n_outer=5).
  7. Record BER and channel NMSE.

Run (from this directory):  python joint_omp_bpmp_afdm.py
Outputs: ./results/ber_nmse.npz  +  ber_waterfall.png, nmse_curve.png, console table.
"""
from __future__ import annotations
import os
import time
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


# ============================================================
#  PRESETS
# ============================================================
UWA_PRESET = dict(          # underwater acoustic
    N=100, fc=12e3, fs=8e3, delta_f=15.0, c_sound=1500.0,
    P_paths=5, tau_spread=10e-3, tau_mean=0.8e-3, att_dB=20.0,
    v_mean=2.0, v_std=0.5,
    l_max_cap=15, k_max_cap=2, k_guard=4, k_v=0,
    uwa_resample_max_tries=32,
)

LEO_PRESET = dict(          # 3GPP TR 38.811 NTN-TDL (Ku-band LEO)
    N=256, fc=12e9, delta_f=15e3,
    ntn_profile="NTN-TDL-C",
    use_dominant_2taps=False,
    H_sat=600e3, R_earth=6371e3, G_earth=3.986e14,
    alpha_min_deg=30.0, ue_speed=0.0, local_doppler_spread_hz=50.0,
    l_max_cap=1, k_max_cap=16, k_guard=0, k_v=4,
    P_paths=2,
)


# ============================================================
#  CONFIG — edit `channel_type` and `pilot_type` to switch
# ============================================================
CONFIG = dict(
    # --- scenario selectors ---
    channel_type="leo_ntn",                 # "uwa" | "leo_ntn"
    pilot_type="random_qpsk",                    # "zc" | "random_qpsk" (original MATLAB uses random_qpsk)

    # --- common frame / Doppler quantization ---
    rho=0.5,
    zc_root=7,
    use_frac_doppler=True,
    k_leak=2,
    frac_prune_rel_thres=0.01,

    # --- Joint iterative receiver ---
    n_outer_iter=5,
    bp_iter=20,
    bp_threshold=1e-4,
    bp_damp=0.5,
    gamma_h=0.7,
    gamma_x=0.6,
    lambda_ls_factor=1e-3,
    tau_h_factor=0.01,
    tau_h_sigma_factor=0.1,
    eps_stop_rel=1e-3,
    update_sigma2=True,

    # --- Monte-Carlo sweep ---
    snr_db_list=(0, 5, 10, 15, 20, 25),
    n_frames=100,
    rng_seed=20260422,
    out_dir="results",
)


def resolve_cfg(cfg: dict) -> dict:
    """Merge the active preset into cfg (top-level keys override preset)."""
    cfg = dict(cfg)
    preset = UWA_PRESET if cfg["channel_type"] == "uwa" else LEO_PRESET
    for k, v in preset.items():
        cfg.setdefault(k, v)
    return cfg


# ============================================================
#  AFDM physics:  chirp params, DAFT matrix, channel H_eff
# ============================================================

def chirp_params(N: int, k_max: int, k_v: int = 0) -> tuple[float, float]:
    """c1 = (2·(k_max + k_v) + 1) / (2·N);   c2 = (√2−1)/(2·N²).

    k_v is the Doppler oversizing guard (0 for UWA, 4 for LEO — matches
    original MATLAB `c1 = (2*(max_Doppler+k_v)+1) / (2*N)`).
    """
    c1 = (2.0 * (k_max + k_v) + 1.0) / (2.0 * N)
    c2 = (np.sqrt(2.0) - 1.0) / (2.0 * N * N)
    return c1, c2


def build_daft_matrix(N: int, c1: float, c2: float) -> tuple[np.ndarray, np.ndarray]:
    """A = Λ_{c2} · F_N · Λ_{c1};  returns (A, A^H)."""
    n = np.arange(N)
    F_N = np.exp(-2j * np.pi * np.outer(n, n) / N) / np.sqrt(N)
    Lambda_c1 = np.diag(np.exp(1j * 2.0 * np.pi * c1 * n ** 2))
    Lambda_c2 = np.diag(np.exp(1j * 2.0 * np.pi * c2 * n ** 2))
    A = Lambda_c2 @ F_N @ Lambda_c1
    return A, A.conj().T


def dirichlet_alpha(m: int, kappa: float, N: int) -> complex:
    """Dirichlet-kernel weight for fractional Doppler bin split
    (MATLAB dirichlet_alpha.m port)."""
    x = m + kappa
    if abs(x) < 1e-12:
        return 1.0 + 0j
    denom = np.sin(np.pi * x / N)
    if abs(denom) < 1e-12:
        return complex(np.exp(1j * np.pi * (N - 1) * x / N))
    return complex(
        np.exp(1j * np.pi * (N - 1) * x / N) * np.sin(np.pi * x) / (N * denom)
    )


def gen_h_daft(
    N: int, c1: float, c2: float,
    chan_coef: np.ndarray, delay_idx: np.ndarray, doppler_idx: np.ndarray,
) -> np.ndarray:
    """Analytical DAFT-domain H from integer-bin taps (Python convention).

        H[m, n] += g_i · exp(j·2π · [ -c1·l² + c2·(m²-n²) - l·n/N ])
        m = (n + l·K + k) mod N,  K = 2·k_max+1 = round(2·N·c1).
    """
    K_factor = max(int(round(2.0 * N * c1)), 1)
    H = np.zeros((N, N), dtype=complex)
    n_arr = np.arange(N, dtype=np.float64)
    for g, l_i, k_i in zip(chan_coef, delay_idx, doppler_idx):
        l_i = int(l_i); k_i = int(k_i)
        delta = l_i * K_factor + k_i
        m_arr = (n_arr.astype(int) + delta) % N
        m_f = m_arr.astype(np.float64)
        phase = np.exp(1j * 2.0 * np.pi * (
            -c1 * (l_i ** 2)
            + c2 * (m_f ** 2 - n_arr ** 2)
            - float(l_i) * n_arr / N
        ))
        H[m_arr, np.arange(N)] += g * phase
    return H


# ============================================================
#  3GPP TR 38.811 NTN-TDL profiles (LEO)
# ============================================================
_NTN_TDL = {
    "NTN-TDL-A": dict(
        tau_norm=[0.0, 1.0811, 2.8416],
        p_db=[0.0, -4.675, -6.482],
        fad=["Rayleigh", "Rayleigh", "Rayleigh"],
        K_db=0.0,
    ),
    "NTN-TDL-B": dict(
        tau_norm=[0.0, 0.7249, 1.0771, 1.9092],
        p_db=[0.0, -4.926, -6.902, -8.717],
        fad=["Rayleigh", "Rayleigh", "Rayleigh", "Rayleigh"],
        K_db=0.0,
    ),
    "NTN-TDL-C": dict(
        tau_norm=[0.0, 0.0, 14.8124],
        p_db=[-0.394, -10.618, -23.373],
        fad=["Rician", "Rayleigh", "Rayleigh"],
        K_db=10.224,
    ),
    "NTN-TDL-D": dict(
        tau_norm=[0.0, 0.0, 0.5596, 7.3340],
        p_db=[0.016, -12.968, -9.887, -16.771],
        fad=["Rician", "Rayleigh", "Rayleigh", "Rayleigh"],
        K_db=11.707,
    ),
}


def get_ntn_tdl_profile(name: str) -> dict:
    key = name.strip().replace(" ", "").upper()
    if key not in _NTN_TDL:
        raise ValueError(f"Unknown NTN-TDL profile: {name}")
    return _NTN_TDL[key]


def _select_dominant_2taps(prof: dict) -> dict:
    """Merge delay=0 components into one, pick strongest non-zero delay tap."""
    tau = np.asarray(prof["tau_norm"], dtype=float)
    p_db = np.asarray(prof["p_db"], dtype=float)
    fad = list(prof["fad"])
    idx0 = np.where(np.abs(tau) < 1e-12)[0]
    p_lin0 = np.sum(10.0 ** (p_db[idx0] / 10.0))
    p0_db = 10.0 * np.log10(p_lin0 + 1e-300)
    fad_first = "Rician" if any(fad[i] == "Rician" for i in idx0) else "Rayleigh"
    K_db_first = prof["K_db"] if fad_first == "Rician" else 0.0

    rem = [i for i in range(len(tau)) if i not in idx0]
    if not rem:
        return dict(tau_norm=[0.0], p_db=[p0_db], fad=[fad_first], K_db=K_db_first)
    best = rem[int(np.argmax(p_db[rem]))]
    return dict(
        tau_norm=[0.0, float(tau[best])],
        p_db=[float(p0_db), float(p_db[best])],
        fad=[fad_first, fad[best]],
        K_db=K_db_first,
    )


def generate_leo_ntn_channel(cfg: dict, rng):
    """3GPP TR 38.811 NTN-TDL SISO channel (port of generate_NTN_TDL_channel_SISO).

    Returns (gain_tap, l_i, k_real) — physical taps with *continuous* k_real
    (subject to Dirichlet expansion downstream if use_frac_doppler=True).
    """
    prof = get_ntn_tdl_profile(cfg["ntn_profile"])
    if cfg.get("use_dominant_2taps", False):
        prof = _select_dominant_2taps(prof)

    tau_norm = np.asarray(prof["tau_norm"], dtype=float)
    p_db = np.asarray(prof["p_db"], dtype=float)
    fad = list(prof["fad"])
    K_db = float(prof["K_db"])
    P_phy = len(p_db)

    # ── 1) delay bins: map max(tau_norm) to l_max_cap sample delay
    N = int(cfg["N"])
    Ts = 1.0 / (N * cfg["delta_f"])
    l_max_samp = int(cfg["l_max_cap"])
    ds_scale_s = (l_max_samp * Ts) / max(np.max(tau_norm), 1e-12)
    tau_sec = tau_norm * ds_scale_s
    l_i = np.clip(np.round(tau_sec / Ts).astype(int), 0, l_max_samp)

    # ── 2) per-tap complex gain (Rician or Rayleigh), power-normalized
    p_lin = 10.0 ** (p_db / 10.0)
    p_lin = p_lin / np.sum(p_lin)
    chan = np.zeros(P_phy, dtype=complex)
    for i in range(P_phy):
        if fad[i] == "Rician":
            K_lin = 10.0 ** (K_db / 10.0)
            los = np.sqrt(p_lin[i] * K_lin / (K_lin + 1.0)) * np.exp(
                1j * 2.0 * np.pi * rng.random()
            )
            nlos = np.sqrt(p_lin[i] / (K_lin + 1.0)) * (
                (rng.standard_normal() + 1j * rng.standard_normal()) / np.sqrt(2.0)
            )
            chan[i] = los + nlos
        else:
            chan[i] = np.sqrt(p_lin[i]) * (
                (rng.standard_normal() + 1j * rng.standard_normal()) / np.sqrt(2.0)
            )

    # ── 3) orbital-geometry Doppler
    V_SAT = np.sqrt(cfg["G_earth"] / (cfg["R_earth"] + cfg["H_sat"]))
    alpha_deg = cfg["alpha_min_deg"] + rng.random() * (90.0 - cfg["alpha_min_deg"])
    c_light = 3e8
    v_rel = V_SAT * (cfg["R_earth"] / (cfg["R_earth"] + cfg["H_sat"])) * np.cos(
        np.deg2rad(alpha_deg)
    )
    f_d_sat = (v_rel / c_light) * cfg["fc"]
    f_d_ue = (cfg["ue_speed"] / c_light) * cfg["fc"]
    sign_fd = 1.0 if rng.random() > 0.5 else -1.0
    f_d_base = sign_fd * (f_d_sat + f_d_ue)

    local = cfg["local_doppler_spread_hz"] * (2.0 * rng.random(P_phy) - 1.0)
    f_d_taps = f_d_base + local
    k_real = f_d_taps / cfg["delta_f"]
    return chan, l_i, k_real


# ============================================================
#  UWA acoustic channel generation
# ============================================================

def generate_uwa_channel(cfg: dict, rng: np.random.Generator):
    """Rayleigh multipath with exponential PDP + per-path Gaussian velocity.
    Ported from afdm_env.py::generate_uwa_channel.

    Returns:
        delays (P,) — corrected delays (s)
        gain_tap (P,) complex — path gains, ||gain||_2 = 1
        delay_idx_bar (P,) int — Doppler-corrected 1-based sample delay indices
        doppler_a (P,) float — scaling factors v_i/c_sound
    """
    P = int(cfg["P_paths"])
    Ts = 1.0 / cfg["fs"]
    N_total = int(cfg["N"])
    delay_res = 1.0 / (N_total * cfg["delta_f"])
    max_supp = int(np.floor(cfg["l_max_cap"] * delay_res / Ts)) + 1

    for _ in range(cfg["uwa_resample_max_tries"]):
        d_tau = rng.exponential(scale=cfg["tau_mean"], size=P)
        d_tau_idx = np.maximum(1, np.ceil(d_tau / Ts).astype(int))
        delay_index = np.cumsum(d_tau_idx)
        delay_vec = (delay_index - 1) * Ts

        alpha = np.log(10 ** (cfg["att_dB"] / 10.0)) / cfg["tau_spread"]
        path_var = np.exp(-alpha * delay_vec)
        sigma = np.sqrt(path_var * 2.0 / (4.0 - np.pi))
        amp = rng.rayleigh(scale=sigma)
        nrm = np.linalg.norm(amp)
        if nrm > 0:
            amp = amp / nrm
        phases = 2.0 * np.pi * rng.random(P)
        gain_tap = amp * np.exp(1j * phases)

        velocities = np.abs(cfg["v_mean"] + cfg["v_std"] * rng.standard_normal(P))
        doppler_a = velocities / cfg["c_sound"]
        delay_idx_bar = np.maximum(
            1, np.ceil(delay_index / (1.0 + doppler_a)).astype(int)
        )
        if np.max(delay_idx_bar) <= max_supp:
            delays = (delay_idx_bar - 1) * Ts
            return delays, gain_tap, delay_idx_bar, doppler_a

    # Fallback: clip once
    delay_idx_bar = np.minimum(delay_idx_bar, max_supp)
    delays = (delay_idx_bar - 1) * Ts
    return delays, gain_tap, delay_idx_bar, doppler_a


def expand_fractional_doppler(cfg: dict, gain_tap, l_i, k_real):
    """Dirichlet decomposition: each physical path → 2·k_leak+1 integer virtual taps."""
    N = int(cfg["N"])
    k_leak = int(cfg["k_leak"])
    k_guard = int(cfg["k_guard"])
    k_clip = min(cfg["k_max_cap"], int(np.floor(N / 2) - k_guard - 1))
    k_real = np.clip(k_real, -float(k_clip), float(k_clip))
    prune = cfg["frac_prune_rel_thres"]
    m_range = np.arange(-k_leak, k_leak + 1, dtype=int)

    if not cfg["use_frac_doppler"]:
        k_int = np.clip(np.round(k_real).astype(int), -k_clip, k_clip)
        return (np.asarray(gain_tap, dtype=complex),
                np.asarray(l_i, dtype=int),
                k_int)

    gains_ex, l_ex, k_ex = [], [], []
    for i in range(len(gain_tap)):
        k_base = int(round(k_real[i]))
        kappa = k_real[i] - k_base
        a_vec = np.array(
            [dirichlet_alpha(int(m), kappa, N) for m in m_range], dtype=complex
        )
        a_vec /= np.sqrt(np.sum(np.abs(a_vec) ** 2) + 1e-300)
        a_pow = np.abs(a_vec) ** 2
        a_peak = np.max(a_pow)
        for mm, m in enumerate(m_range):
            k_eff = k_base + int(m)
            if abs(k_eff) > k_clip:
                continue
            if a_pow[mm] < prune * a_peak:
                continue
            gains_ex.append(gain_tap[i] * a_vec[mm])
            l_ex.append(int(l_i[i]))
            k_ex.append(k_eff)
    return (np.asarray(gains_ex, dtype=complex),
            np.asarray(l_ex, dtype=int),
            np.asarray(k_ex, dtype=int))


def build_channel(cfg: dict, rng):
    """Returns (H_eff, H_time) with ||H_eff||_F = sqrt(N).
    Dispatches on cfg["channel_type"] ∈ {"uwa", "leo_ntn"}.
    """
    N = int(cfg["N"])
    c1, c2 = chirp_params(N, cfg["k_max_cap"], cfg.get("k_v", 0))

    if cfg["channel_type"] == "leo_ntn":
        gain_tap, l_i, k_real = generate_leo_ntn_channel(cfg, rng)
    else:                                           # "uwa"
        delays, gain_tap, _, doppler_a = generate_uwa_channel(cfg, rng)
        delay_res = 1.0 / (N * cfg["delta_f"])
        l_i = np.clip(np.round(delays / delay_res).astype(int), 0, cfg["l_max_cap"])
        k_real = (doppler_a * cfg["fc"] / cfg["fs"]) * N

    gains_ex, l_ex, k_ex = expand_fractional_doppler(cfg, gain_tap, l_i, k_real)

    if gains_ex.size == 0:
        H_eff = np.zeros((N, N), dtype=complex)
    else:
        H_eff = gen_h_daft(N, c1, c2, gains_ex, l_ex, k_ex)

    fro = np.linalg.norm(H_eff, "fro")
    if fro > 0:
        H_eff *= np.sqrt(N) / fro
    A, A_H = build_daft_matrix(N, c1, c2)
    H_time = A_H @ H_eff @ A
    return H_eff, H_time, (c1, c2, A, A_H)


# ============================================================
#  Frame + AWGN
# ============================================================

_QPSK = np.array([1 + 1j, 1 - 1j, -1 + 1j, -1 - 1j], dtype=complex) / np.sqrt(2.0)


def zc_sequence(N: int, root: int) -> np.ndarray:
    n = np.arange(N)
    return np.exp(-1j * np.pi * root * n * n / N)


def build_sp_frame(cfg: dict, rng):
    """Returns (x_full, data_symbols, x_pilot_scaled).
    pilot_type="zc": ZC sequence (Python-repo default, condition-number-stable)
    pilot_type="random_qpsk": fresh random QPSK per frame (original MATLAB convention)
    """
    N = int(cfg["N"])
    rho = float(cfg["rho"])
    if cfg.get("pilot_type", "zc") == "random_qpsk":
        pilot = np.sqrt(rho) * _QPSK[rng.integers(0, 4, size=N)]
    else:
        pilot = np.sqrt(rho) * zc_sequence(N, cfg["zc_root"])
    idx = rng.integers(0, 4, size=N)
    data_syms = _QPSK[idx]
    x_full = np.sqrt(1.0 - rho) * data_syms + pilot
    return x_full, data_syms, pilot


def add_awgn_fixed(signal: np.ndarray, snr_db: float, rng) -> tuple[np.ndarray, float]:
    """σ² = 1/SNR (fixed Es/N0 reference, matches MATLAB baseline)."""
    sigma2 = 10.0 ** (-snr_db / 10.0)
    n_c = rng.standard_normal(len(signal)) + 1j * rng.standard_normal(len(signal))
    noise = np.sqrt(sigma2 / 2.0) * n_c
    return signal + noise, sigma2


# ============================================================
#  OMP sensing matrix, solver, H reconstruction
# ============================================================

def construct_sensing_matrix(
    N: int, x_pilot_scaled: np.ndarray, c1: float, c2: float,
    l_max: int, k_max: int,
) -> np.ndarray:
    """Φ[q, col(l,k)] = exp(j·2π·[-c1·l² + c2·(q²-p²) - l·p/N]) · x_p[p]
    with p = (q - l·K - k) mod N,  col(l,k) = l·K + (k + k_max),  K = 2·k_max+1.
    """
    K = 2 * k_max + 1
    Q = (l_max + 1) * K
    q = np.arange(N, dtype=np.float64)
    Phi = np.zeros((N, Q), dtype=complex)
    col = 0
    for l in range(l_max + 1):
        l_sq = float(l) ** 2
        for k in range(-k_max, k_max + 1):
            delta = l * K + k
            p_arr = (q - delta) % N
            phase = np.exp(1j * 2.0 * np.pi * (
                -c1 * l_sq + c2 * (q ** 2 - p_arr ** 2) - float(l) * p_arr / N
            ))
            Phi[:, col] = phase * x_pilot_scaled[p_arr.astype(int)]
            col += 1
    return Phi


def omp_sparse(y: np.ndarray, Phi: np.ndarray, sparsity: int):
    """Standard OMP with final LS on active support."""
    Q = Phi.shape[1]
    residual = y.copy()
    support: list[int] = []
    Phi_H = Phi.conj().T
    for _ in range(int(sparsity)):
        corr = np.abs(Phi_H @ residual)
        for idx in support:
            corr[idx] = 0.0
        support.append(int(np.argmax(corr)))
        Phi_S = Phi[:, support]
        gains_S, *_ = np.linalg.lstsq(Phi_S, y, rcond=None)
        residual = y - Phi_S @ gains_S
        if np.linalg.norm(residual) < 1e-10 * np.linalg.norm(y):
            break
    h_est = np.zeros(Q, dtype=complex)
    if support:
        Phi_S = Phi[:, support]
        g_final, *_ = np.linalg.lstsq(Phi_S, y, rcond=None)
        for i, idx in enumerate(support):
            h_est[idx] = g_final[i]
    return h_est, support


def reconstruct_H_from_support(
    N: int, c1: float, c2: float, k_max: int,
    support_l: np.ndarray, support_k: np.ndarray, gains: np.ndarray,
) -> np.ndarray:
    """Build H_eff (N×N) from (l, k, g) triples via Python phase convention."""
    if len(support_l) == 0:
        return np.zeros((N, N), dtype=complex)
    K = 2 * k_max + 1
    n_arr = np.arange(N, dtype=np.float64)
    H = np.zeros((N, N), dtype=complex)
    for l_i, k_i, g in zip(support_l, support_k, gains):
        l_i = int(l_i); k_i = int(k_i)
        delta = l_i * K + k_i
        m_arr = (n_arr.astype(int) + delta) % N
        m_f = m_arr.astype(np.float64)
        phase = np.exp(1j * 2.0 * np.pi * (
            -c1 * (l_i ** 2) + c2 * (m_f ** 2 - n_arr ** 2) - float(l_i) * n_arr / N
        ))
        H[m_arr, np.arange(N)] += g * phase
    return H


def build_da_ls_column(
    N: int, l_p: int, k_p: int, c1: float, c2: float, k_max: int, x_total: np.ndarray
) -> np.ndarray:
    """Single dictionary column on (l,k) with full known signal x_total."""
    K = 2 * k_max + 1
    n_arr = np.arange(N, dtype=np.float64)
    delta = l_p * K + k_p
    m_arr = (n_arr.astype(int) + delta) % N
    m_f = m_arr.astype(np.float64)
    phase = np.exp(1j * 2.0 * np.pi * (
        -c1 * (l_p ** 2) + c2 * (m_f ** 2 - n_arr ** 2) - float(l_p) * n_arr / N
    ))
    a_col = np.zeros(N, dtype=complex)
    a_col[m_arr] = phase * x_total
    return a_col


# ============================================================
#  BP-MP (full belief-propagation) detector
# ============================================================

def mp_detect_bp(
    y: np.ndarray, H: np.ndarray, sigma2: float, constellation: np.ndarray,
    n_iter: int = 20, threshold: float = 1e-4, damp: float = 0.5,
) -> np.ndarray:
    """Factor-graph Gaussian BP detector (port of MATLAB MP_detection_optimized)."""
    N = H.shape[0]
    if N == 0:
        return np.zeros(0, dtype=complex)

    mask = np.abs(H) >= threshold
    row_idx, col_idx = np.nonzero(mask)
    h_vals = H[row_idx, col_idx]
    E = len(h_vals)
    if E == 0:
        return np.zeros(N, dtype=complex)

    row_edges: list[list[int]] = [[] for _ in range(N)]
    col_edges: list[list[int]] = [[] for _ in range(N)]
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

        # Observation (row) → variable messages
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
                h_e = h_d[local_idx]; mu_e = mu_in[local_idx]; var_e = var_in[local_idx]
                z_ext = z_total + h_e * mu_e
                V_ext = max(V_total - (abs(h_e) ** 2) * var_e, sigma2 * 0.1)
                if abs(h_e) > 1e-10:
                    var_o2v[e] = max(V_ext / (abs(h_e) ** 2), 1e-10)
                    mu_o2v[e] = z_ext / h_e
                else:
                    var_o2v[e] = 1e10
                    mu_o2v[e] = 0.0

        # Variable (column) → observation messages
        for n in range(N):
            edges = col_edges[n]
            if not edges:
                continue
            var_in = var_o2v[edges]; mu_in = mu_o2v[edges]
            prec_total = 1.0 / prior_var + np.sum(1.0 / var_in)
            mean_total = prior_mean / prior_var + np.sum(mu_in / var_in)
            for e in edges:
                var_e = var_o2v[e]; mu_e = mu_o2v[e]
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

    x_est = np.zeros(N, dtype=complex)
    for n in range(N):
        edges = col_edges[n]
        if not edges:
            x_est[n] = prior_mean
            continue
        var_in = var_o2v[edges]; mu_in = mu_o2v[edges]
        prec_total = 1.0 / prior_var + np.sum(1.0 / var_in)
        mean_total = prior_mean / prior_var + np.sum(mu_in / var_in)
        var_post = 1.0 / max(prec_total, 1e-10)
        mu_post = var_post * mean_total
        x_est[n] = constellation[np.argmin(np.abs(constellation - mu_post))]
    return x_est


# ============================================================
#  Joint OMP + BP-MP iterative receiver
# ============================================================

def joint_omp_bpmp_iterative(
    y_daft: np.ndarray, x_pilot_scaled: np.ndarray,
    N: int, c1: float, c2: float, l_max: int, k_max: int,
    sigma2: float, constellation_data: np.ndarray,
    cfg: dict,
) -> tuple[np.ndarray, np.ndarray]:
    """Port of joint_omp_mp_iterative with mp_mode='bp'."""
    K = 2 * k_max + 1
    Q = (l_max + 1) * K
    n_paths = int(cfg["P_paths"])
    n_outer = int(cfg["n_outer_iter"])
    k_leak = int(cfg["k_leak"])
    gamma_h = float(cfg["gamma_h"]); gamma_x = float(cfg["gamma_x"])
    lambda_ls_factor = float(cfg["lambda_ls_factor"])
    tau_h_factor = float(cfg["tau_h_factor"])
    tau_h_sigma_factor = float(cfg["tau_h_sigma_factor"])
    eps_stop_rel = float(cfg["eps_stop_rel"])
    update_sigma2 = bool(cfg["update_sigma2"])

    Phi = construct_sensing_matrix(N, x_pilot_scaled, c1, c2, l_max, k_max)

    H_hat = np.zeros((N, N), dtype=complex)
    x_soft = np.zeros(N, dtype=complex)
    sigma2_eff = float(sigma2)
    lambda_ls = max(1e-6, lambda_ls_factor * sigma2_eff)
    prev_resnorm = np.inf

    sup_l = np.array([], dtype=int)
    sup_k = np.array([], dtype=int)
    gains_S = np.array([], dtype=complex)

    for outer in range(n_outer):

        # ---- (A) Channel estimation update ----
        if outer == 0:
            h_omp, sup_idx = omp_sparse(y_daft, Phi, n_paths)
            s_l, s_k, s_g = [], [], []
            for idx in sup_idx:
                g = h_omp[idx]
                l_dec = idx // K
                k_dec = (idx % K) - k_max
                s_l.append(l_dec); s_k.append(k_dec); s_g.append(g)

            # Cluster expansion ±k_leak
            ex_l, ex_k, ex_g = [], [], []
            for i in range(len(s_l)):
                for m in range(-k_leak, k_leak + 1):
                    k_new = s_k[i] + m
                    if abs(k_new) > k_max:
                        continue
                    ex_l.append(s_l[i]); ex_k.append(k_new)
                    ex_g.append(s_g[i] if m == 0 else 0.0)

            if ex_l:
                pairs = np.column_stack([ex_l, ex_k])
                gains_arr = np.array(ex_g, dtype=complex)
                u_pairs, inv = np.unique(pairs, axis=0, return_inverse=True)
                merged = np.zeros(len(u_pairs), dtype=complex)
                np.add.at(merged, inv, gains_arr)
                sup_l = u_pairs[:, 0].astype(int)
                sup_k = u_pairs[:, 1].astype(int)
                gains_S = merged
            else:
                sup_l = np.array([], dtype=int)
                sup_k = np.array([], dtype=int)
                gains_S = np.array([], dtype=complex)

        else:
            # Data-aided LS: x_total = pilot + hard-decided data
            x_hard = np.array(
                [constellation_data[np.argmin(np.abs(s - constellation_data))]
                 for s in x_soft], dtype=complex,
            )
            x_total = x_pilot_scaled + x_hard
            P = len(sup_l)
            if P > 0:
                A_tot = np.zeros((N, P), dtype=complex)
                for p in range(P):
                    A_tot[:, p] = build_da_ls_column(
                        N, int(sup_l[p]), int(sup_k[p]), c1, c2, k_max, x_total
                    )
                AhA = A_tot.conj().T @ A_tot
                Ahy = A_tot.conj().T @ y_daft
                gains_S = np.linalg.solve(
                    AhA + lambda_ls * np.eye(P), Ahy + lambda_ls * gains_S
                )

        # Reconstruct H from (sup_l, sup_k, gains_S)
        H_new = reconstruct_H_from_support(N, c1, c2, k_max, sup_l, sup_k, gains_S)
        H_hat = (1.0 - gamma_h) * H_hat + gamma_h * H_new

        # Sparsify
        max_h = np.max(np.abs(H_hat))
        if max_h > 0:
            tau = max(tau_h_factor * max_h, tau_h_sigma_factor * np.sqrt(sigma2_eff))
            H_hat[np.abs(H_hat) < tau] = 0.0

        # ---- (B) BP-MP detection ----
        y_data = y_daft - H_hat @ x_pilot_scaled
        x_mp = mp_detect_bp(
            y_data, H_hat, sigma2_eff, constellation_data,
            n_iter=int(cfg["bp_iter"]),
            threshold=float(cfg["bp_threshold"]),
            damp=float(cfg["bp_damp"]),
        )
        x_soft = (1.0 - gamma_x) * x_soft + gamma_x * x_mp

        # ---- (C) Adaptive σ² ----
        if update_sigma2 and outer > 0:
            x_hard_res = np.array(
                [constellation_data[np.argmin(np.abs(s - constellation_data))]
                 for s in x_soft], dtype=complex,
            )
            x_tot_res = x_pilot_scaled + x_hard_res
            resid = y_daft - H_hat @ x_tot_res
            sigma2_new = float(np.sum(np.abs(resid) ** 2)) / N
            sigma2_eff = 0.7 * sigma2_eff + 0.3 * max(sigma2_new, 1e-12)
            lambda_ls = max(1e-6, lambda_ls_factor * sigma2_eff)

        # ---- (D) Early stop ----
        x_hard_stop = np.array(
            [constellation_data[np.argmin(np.abs(s - constellation_data))]
             for s in x_soft], dtype=complex,
        )
        x_tot_stop = x_pilot_scaled + x_hard_stop
        curr_resnorm = float(np.sum(np.abs(y_daft - H_hat @ x_tot_stop) ** 2))
        if prev_resnorm < np.inf:
            rel = (prev_resnorm - curr_resnorm) / max(curr_resnorm, 1e-12)
            if 0 <= rel < eps_stop_rel:
                break
        prev_resnorm = curr_resnorm

    return x_soft, H_hat


# ============================================================
#  Orchestration
# ============================================================

def ber_qpsk(x_true: np.ndarray, x_det: np.ndarray) -> float:
    err_i = np.mean((np.real(x_true) > 0) != (np.real(x_det) > 0))
    err_q = np.mean((np.imag(x_true) > 0) != (np.imag(x_det) > 0))
    return 0.5 * float(err_i + err_q)


def nmse(H_true: np.ndarray, H_est: np.ndarray) -> float:
    num = float(np.linalg.norm(H_true - H_est, "fro") ** 2)
    den = float(np.linalg.norm(H_true, "fro") ** 2)
    return num / den if den > 0 else float("inf")


def run_one_frame(cfg: dict, snr_db: float, rng) -> tuple[float, float]:
    N = int(cfg["N"]); rho = float(cfg["rho"])
    H_eff, H_time, (c1, c2, A, A_H) = build_channel(cfg, rng)
    x_full, data_syms, pilot = build_sp_frame(cfg, rng)

    s = A_H @ x_full                     # AFDM modulate (time domain)
    r = H_time @ s                       # channel
    r_n, sigma2 = add_awgn_fixed(r, snr_db, rng)
    y_daft = A @ r_n                     # DAFT demodulate

    const_data = np.sqrt(1.0 - rho) * _QPSK
    x_soft, H_est = joint_omp_bpmp_iterative(
        y_daft, pilot, N, c1, c2, cfg["l_max_cap"], cfg["k_max_cap"],
        sigma2, const_data, cfg,
    )

    # x_soft is at data-scale (√(1-ρ)·QPSK); compare bits with transmitted data_syms
    # Both are on the same scale only if we also scale data_syms by √(1-ρ) — we
    # instead compare sign patterns (QPSK), so scale cancels.
    ber = ber_qpsk(data_syms, x_soft)
    ch_mse = nmse(H_eff, H_est)
    return ber, ch_mse


def sweep(cfg: dict):
    cfg = resolve_cfg(cfg)
    rng = np.random.default_rng(cfg["rng_seed"])
    snr_list = list(cfg["snr_db_list"])
    n_frames = int(cfg["n_frames"])
    ber_arr = np.zeros(len(snr_list))
    nmse_arr = np.zeros(len(snr_list))

    t0 = time.time()
    print(f"channel_type = {cfg['channel_type']},  pilot_type = {cfg['pilot_type']},  "
          f"use_frac_doppler = {cfg['use_frac_doppler']}")
    print(f"# frames/SNR = {n_frames},  N = {cfg['N']},  ρ = {cfg['rho']},  "
          f"l_max = {cfg['l_max_cap']},  k_max = {cfg['k_max_cap']}")
    print(f"{'SNR_dB':>6} {'BER':>12} {'NMSE_dB':>10} {'time_s':>8}")
    for i, snr in enumerate(snr_list):
        t_snr = time.time()
        b_sum = 0.0; m_sum = 0.0
        for _ in range(n_frames):
            b, m = run_one_frame(cfg, float(snr), rng)
            b_sum += b; m_sum += m
        ber_arr[i] = b_sum / n_frames
        nmse_arr[i] = m_sum / n_frames
        nmse_db = 10.0 * np.log10(max(nmse_arr[i], 1e-30))
        print(f"{snr:>6} {ber_arr[i]:>12.4e} {nmse_db:>10.3f} {time.time() - t_snr:>8.1f}")
    print(f"total wall time: {time.time() - t0:.1f} s")
    return np.asarray(snr_list, dtype=float), ber_arr, nmse_arr


def plot_results(snr_db, ber, nmse, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    # BER waterfall
    plt.figure(figsize=(6, 4))
    plt.semilogy(snr_db, np.maximum(ber, 1e-6), "o-", linewidth=2)
    plt.xlabel("SNR (dB)")
    plt.ylabel("BER")
    plt.title("AFDM joint OMP + BP-MP (SP mode, QPSK)")
    plt.grid(True, which="both", linestyle=":")
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, "ber_waterfall.png"), dpi=150)
    plt.close()

    # NMSE-SNR
    plt.figure(figsize=(6, 4))
    plt.plot(snr_db, 10.0 * np.log10(np.maximum(nmse, 1e-30)), "s-", linewidth=2)
    plt.xlabel("SNR (dB)")
    plt.ylabel("Channel NMSE (dB)")
    plt.title("Channel estimation NMSE vs SNR")
    plt.grid(True, linestyle=":")
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, "nmse_curve.png"), dpi=150)
    plt.close()


def main():
    cfg = dict(CONFIG)
    snr_db, ber, ch_mse = sweep(cfg)
    os.makedirs(cfg["out_dir"], exist_ok=True)
    np.savez(
        os.path.join(cfg["out_dir"], "ber_nmse.npz"),
        snr_db=snr_db, ber=ber, nmse=ch_mse, config=np.array([repr(cfg)]),
    )
    plot_results(snr_db, ber, ch_mse, cfg["out_dir"])
    print(f"Saved: {cfg['out_dir']}/ber_nmse.npz, ber_waterfall.png, nmse_curve.png")


if __name__ == "__main__":
    main()
