import json
import math
import sys
import numpy as np
from scipy.stats import t as sp_t


def json_safe(obj):
    if isinstance(obj, dict):
        return {str(k): json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [json_safe(v) for v in obj]
    if isinstance(obj, (bool, np.bool_)):
        return bool(obj)
    if isinstance(obj, (int, np.integer)):
        return int(obj)
    if isinstance(obj, (float, np.floating)):
        fv = float(obj)
        return fv if math.isfinite(fv) else None
    return obj


def save_result_json(path, payload):
    out = dict(payload)
    out.setdefault("_argv", list(sys.argv))
    with open(path, "w", encoding="utf-8") as f:
        json.dump(json_safe(out), f, indent=2, allow_nan=False)


class RateMatchedQCLDPC:
    """Deterministic systematic QC-LDPC codec supporting arbitrary (K_info, N_code) via puncturing/shortening."""

    def __init__(self, k_info: int, n_code: int, seed: int = 20261126):
        assert 8 <= k_info < n_code, f"Invalid (k_info={k_info}, n_code={n_code})"
        self.k_info = int(k_info)
        self.n_code = int(n_code)
        self.m_par = self.n_code - self.k_info
        rng = np.random.default_rng(seed + 1009 * self.k_info + 37 * self.n_code)

        # Build sparse systematic parity matrix H = [H_sys | H_par] over GF(2) where H_par is dual-diagonal lower-bidiagonal
        # (guaranteed full-rank invertible in O(M) without Gaussian elimination failure, just like 5G NR / IEEE 802.11n!)
        col_deg = 3
        H_sys = np.zeros((self.m_par, self.k_info), dtype=np.uint8)
        for j in range(self.k_info):
            deg = min(col_deg, self.m_par)
            rows = rng.choice(self.m_par, size=deg, replace=False)
            H_sys[rows, j] = 1
        # Ensure every check row has at least 2 systematic connections
        for i in range(self.m_par):
            if np.sum(H_sys[i]) < 2:
                cols = rng.choice(self.k_info, size=2, replace=False)
                H_sys[i, cols] = 1

        # Lower bidiagonal staircase H_par: p_0 = s_0; p_i = s_i ^ p_{i-1} (invertible, low error floor with 1 tail feedback col)
        H_par = np.eye(self.m_par, dtype=np.uint8)
        for i in range(1, self.m_par):
            H_par[i, i - 1] = 1

        self.H_sys = H_sys
        self.H = np.hstack([H_sys, H_par])  # (M, N)

        # Precompute edge index arrays for fast vectorized normalized min-sum / sum-product BP
        r_idx, c_idx = np.nonzero(self.H)
        self.n_edges = len(r_idx)
        self.edge_r = r_idx.astype(np.int32)
        self.edge_c = c_idx.astype(np.int32)

        # Group edges by check row (padded rectangular table for pure NumPy vectorization)
        row_lists = [np.where(self.edge_r == i)[0] for i in range(self.m_par)]
        self.max_dc = max(len(x) for x in row_lists)
        self.row_edges = np.full((self.m_par, self.max_dc), -1, dtype=np.int32)
        self.row_valid = np.zeros((self.m_par, self.max_dc), dtype=bool)
        for i, el in enumerate(row_lists):
            self.row_edges[i, : len(el)] = el
            self.row_valid[i, : len(el)] = True

    def encode(self, u_bits: np.ndarray) -> np.ndarray:
        """u_bits: (B, k_info) or (k_info,) in {0, 1}. Returns c_bits: (..., n_code)."""
        single = u_bits.ndim == 1
        U = np.atleast_2d(u_bits).astype(np.int32)
        assert U.shape[1] == self.k_info
        # s = U @ H_sys^T mod 2 (int32 avoids uint8 dot-product wraparound for k_info > 255!)
        S = ((U @ self.H_sys.astype(np.int32).T) & 1).astype(np.uint8)
        # Cumulative XOR along axis=1 solves lower bidiagonal H_par!
        P = np.bitwise_xor.accumulate(S, axis=1) & 1
        C = np.hstack([U.astype(np.uint8), P])
        return C[0] if single else C

    def decode_bp(self, llr: np.ndarray, max_iter: int = 20, alpha_nms: float = 0.78):
        """
        Vectorized Normalized Min-Sum + damped BP decoder.
        Convention: llr = log(P(b=0) / P(b=1)), so b=0 -> +LLR, b=1 -> -LLR.
        llr: (B, n_code) or (n_code,). Returns (u_hat, cw_ok_mask).
        """
        single = llr.ndim == 1
        L_ch = np.clip(np.atleast_2d(llr).astype(np.float64), -35.0, 35.0)
        B = L_ch.shape[0]
        E = self.n_edges

        c2v = np.zeros((B, E), dtype=np.float64)
        L_post = L_ch.copy()
        re_safe = np.maximum(self.row_edges, 0)
        valid_m = self.row_valid[None, :, :]  # (1, M, max_dc)

        for _ in range(max_iter):
            c_hat = (L_post < 0.0).astype(np.int32)
            syn = (c_hat @ self.H.astype(np.int32).T) & 1
            if not np.any(syn):
                break

            v2c = np.clip(L_post[:, self.edge_c] - c2v, -35.0, 35.0)  # (B, E)
            # Gather per-row messages: (B, M, max_dc)
            M_rc = v2c[:, re_safe]
            sgn = np.where(valid_m, np.where(M_rc < 0.0, -1.0, 1.0), 1.0)
            prod_sgn = np.prod(sgn, axis=2, keepdims=True)
            ext_sgn = prod_sgn * sgn

            mag = np.where(valid_m, np.abs(M_rc), 1e9)
            # First and second minimum along axis=2
            idx_min1 = np.argmin(mag, axis=2, keepdims=True)
            min1 = np.take_along_axis(mag, idx_min1, axis=2)
            mag2 = mag.copy()
            np.put_along_axis(mag2, idx_min1, 1e9, axis=2)
            min2 = np.min(mag2, axis=2, keepdims=True)

            is_min1 = np.arange(self.max_dc)[None, None, :] == idx_min1
            ext_mag = np.where(is_min1, min2, min1)
            c2v_row = alpha_nms * ext_sgn * ext_mag  # (B, M, max_dc)

            c2v_new = np.zeros_like(c2v)
            r_flat = self.row_edges[self.row_valid]
            c2v_new[:, r_flat] = c2v_row[:, self.row_valid]
            c2v = 0.85 * c2v_new + 0.15 * c2v

            L_post = L_ch.copy()
            # Accumulate c2v into L_post columns
            for b in range(B):
                np.add.at(L_post[b], self.edge_c, c2v[b])
            L_post = np.clip(L_post, -40.0, 40.0)

        c_hat = (L_post < 0.0).astype(np.uint8)
        syn_ok = np.sum((c_hat.astype(np.int32) @ self.H.astype(np.int32).T) & 1, axis=1) == 0
        u_hat = c_hat[:, : self.k_info]
        if single:
            return u_hat[0], bool(syn_ok[0])
        return u_hat, syn_ok


def make_daft_mat(N: int, c1: float, c2: float) -> np.ndarray:
    n = np.arange(N, dtype=np.float64)
    L1 = np.exp(-1j * 2.0 * np.pi * c1 * (n ** 2))
    L2 = np.exp(-1j * 2.0 * np.pi * c2 * (n ** 2))
    F = np.fft.fft(np.eye(N), axis=0) / np.sqrt(N)
    return (L2[:, None] * F) * L1[None, :]


def rrc_taps(L_os: int, beta: float, span_sym: int = 10) -> np.ndarray:
    """Unit-energy discrete RRC filter taps at oversampling L_os (sum |h|^2 = 1)."""
    n = np.arange(-span_sym * L_os, span_sym * L_os + 1, dtype=np.float64)
    t = n / float(L_os)
    h = np.zeros_like(t)
    for idx, x in enumerate(t):
        if abs(x) < 1e-12:
            h[idx] = 1.0 - beta + 4.0 * beta / np.pi
        elif beta > 0.0 and abs(abs(x) - 1.0 / (4.0 * beta)) < 1e-9:
            h[idx] = (beta / np.sqrt(2.0)) * (
                (1.0 + 2.0 / np.pi) * np.sin(np.pi / (4.0 * beta))
                + (1.0 - 2.0 / np.pi) * np.cos(np.pi / (4.0 * beta))
            )
        else:
            num = np.sin(np.pi * x * (1.0 - beta)) + 4.0 * beta * x * np.cos(np.pi * x * (1.0 + beta))
            den = np.pi * x * (1.0 - (4.0 * beta * x) ** 2)
            h[idx] = num / den
    h /= np.sqrt(np.sum(h ** 2))
    return h


def measure_bw99_and_aclr(sig_os: np.ndarray, L_os: int, bw_chan_norm: float = None):
    """
    Measure normalized BW99 (in units of 1/T_0 = symbol rate) and ACLR (dBc) from oversampled signal(s).
    sig_os: (B, N_samp) or (N_samp,). Sampling rate is f_s = L_os / T_0, so frequency axis in [-L_os/2, L_os/2).
    """
    S = np.atleast_2d(sig_os)
    N_fft = max(4096, 1 << int(math.ceil(math.log2(S.shape[1] * 2))))
    spec = np.mean(np.abs(np.fft.fftshift(np.fft.fft(S, n=N_fft, axis=1), axes=1)) ** 2, axis=0)
    freqs = (np.arange(N_fft) - N_fft // 2) / float(N_fft) * float(L_os)
    df = freqs[1] - freqs[0]
    tot = np.sum(spec)
    # Symmetric two-sided 99% power bandwidth around 0
    abs_f = np.abs(freqs)
    order = np.argsort(abs_f)
    cum = np.cumsum(spec[order]) / max(tot, 1e-30)
    idx99 = np.searchsorted(cum, 0.99)
    bw99 = 2.0 * float(abs_f[order[min(idx99, len(order) - 1)]]) + df

    if bw_chan_norm is None:
        bw_chan_norm = 1.0
    half_b = 0.5 * bw_chan_norm
    main_p = float(np.sum(spec[np.abs(freqs) <= half_b]))
    adj_l = float(np.sum(spec[(freqs >= -3.0 * half_b) & (freqs < -half_b)]))
    adj_r = float(np.sum(spec[(freqs > half_b) & (freqs <= 3.0 * half_b)]))
    aclr_dbc = 10.0 * math.log10(max(adj_l, adj_r, 1e-30) / max(main_p, 1e-30))
    return {"bw99_over_symrate": bw99, "aclr_dBc": aclr_dbc}


def snr_at_target_loglin(snrs, errs, target: float):
    for i in range(len(snrs) - 1):
        e0, e1 = float(errs[i]), float(errs[i + 1])
        if e0 >= target >= e1 and e0 > e1:
            le0 = math.log10(max(e0, 1e-9))
            le1 = math.log10(max(e1, 1e-9))
            lt = math.log10(target)
            frac = (le0 - lt) / max(le0 - le1, 1e-12)
            return float(snrs[i] + frac * (snrs[i + 1] - snrs[i])), True
    return float("nan"), False


def paired_crossing_gap_ci95(err_rival_mat, err_orc_mat, denom_per_frame: float, snrs, target: float, n_boot: int = 2000, seed: int = 20261126):
    """
    err_rival_mat, err_orc_mat: (M_scenes, len(snrs)).
    Returns SNR_rival(target) - SNR_oracle(target) in dB (positive = rival needs more SNR than Oracle = remaining headroom!).
    """
    M = err_rival_mat.shape[0]
    tot = float(M * denom_per_frame)
    sr, ok_r = snr_at_target_loglin(snrs, np.sum(err_rival_mat, axis=0) / tot, target)
    so, ok_o = snr_at_target_loglin(snrs, np.sum(err_orc_mat, axis=0) / tot, target)
    if not (ok_r and ok_o):
        return {"gap_dB": None, "snr_rival_dB": sr if ok_r else None, "snr_oracle_dB": so if ok_o else None, "ci95_dB": [None, None], "crossing_valid": False}
    pt = sr - so
    rng = np.random.default_rng(seed)
    boots = []
    for _ in range(n_boot):
        ix = rng.integers(0, M, size=M)
        br, ok1 = snr_at_target_loglin(snrs, np.sum(err_rival_mat[ix], axis=0) / tot, target)
        bo, ok2 = snr_at_target_loglin(snrs, np.sum(err_orc_mat[ix], axis=0) / tot, target)
        if ok1 and ok2:
            boots.append(br - bo)
    if len(boots) < int(0.8 * n_boot):
        return {"gap_dB": pt, "snr_rival_dB": sr, "snr_oracle_dB": so, "ci95_dB": [None, None], "crossing_valid": False}
    sb = np.sort(boots)
    lo = float(sb[int(0.025 * (len(sb) - 1))])
    hi = float(sb[int(0.975 * (len(sb) - 1))])
    return {"gap_dB": pt, "snr_rival_dB": sr, "snr_oracle_dB": so, "ci95_dB": [lo, hi], "crossing_valid": True}


def paired_geom_ratio_ci95(t_num, t_den):
    tn = np.asarray(t_num, dtype=float)
    td = np.asarray(t_den, dtype=float)
    M = len(tn)
    lr = np.log(np.maximum(tn, 1e-15) / np.maximum(td, 1e-15))
    ml = float(np.mean(lr))
    tc = float(sp_t.ppf(0.975, df=max(M - 1, 1)))
    hw = tc * float(np.std(lr, ddof=1)) / math.sqrt(M) if M > 1 else 0.0
    return {
        "geom_ratio": float(math.exp(ml)),
        "ci95": [float(math.exp(ml - hw)), float(math.exp(ml + hw))],
        "median_num_ms": float(1e3 * np.median(tn)),
        "p95_num_ms": float(1e3 * np.percentile(tn, 95)),
        "median_den_ms": float(1e3 * np.median(td)),
        "p95_den_ms": float(1e3 * np.percentile(td, 95)),
    }
