# 2026-04-19 Findings: N choice & DAFT convention for Python baselines

## 1. N=256/128 are INFEASIBLE for the current UWA configuration

The AFDM orthogonality inequality `δ_max < N` is formally satisfied for
N=256 (δ_max=127) and N=128 (δ_max=62) with `l_max_cap ∝ N/10, k_max_cap = 2`,
so at first glance those smaller frames look usable.  Empirically they are not:

| N | k_real = D·N | kappa (fractional Doppler) | Pact (virtual taps) | Joint BER @ 20 dB |
|---|:---:|:---:|:---:|:---:|
| 128 | 0.256 | ±0.256 | ≈ 45 – 50 | ≈ 0.22 – 0.29 |
| 256 | 0.512 | ±0.488 **(worst)** | ≈ 43 – 44 | ≈ 0.18 – 0.21 |
| 512 | 1.024 | ±0.024 | ≈ 17 – 33 | ≈ 0.01 – 0.05 |

`D = v · fc / (c_sound · fs) = 2 · 12000 / (1500 · 8000) = 0.002`.
`kappa = |k_real − round(k_real)|` is the fractional-Doppler residual that drives
the Dirichlet expansion.  When `|kappa| → 0.5` every physical path spills into
the full 2·k_leak+1 = 5 virtual integer-bin taps, so `P_actual ≈ P_paths × 5 ≈ 50`
and OMP sparsity has to climb to 50 on a dictionary of Q ≈ 130 columns — that
is the main reason the joint receiver collapses at N=256/128.

**Takeaway**: for v=2 m/s, fc=12 kHz, fs=8 kHz the good choices of N are those
with `k_real = 0.002·N` close to an integer (e.g. N=500, N=512, N=1000).
N=256 and N=128 are precisely at or near the half-integer worst case and must
be avoided.  **N=512 stays**.

## 2. Joint OMP-MP BER at 25 dB is bimodal, not a uniform floor

In the single-frame stream logs, the joint receiver is partitioned into two
regimes:
* "Good" frames (Pact ≈ 20, kappa-clean channel) → Joint BER ≈ 0 or ≈ 1e-3
* "Bad" frames (Pact ≈ 30, hard Doppler draws) → Joint BER ≈ 5 × 10⁻² — 8 × 10⁻²

The population mean ≈ 1-2 × 10⁻² at 25 dB with std ≈ 2.6 × 10⁻² reflects that
mixture, **not** a deterministic 2 % floor; enough frames are zero-error to
drag the mean down, but the 20 % tail of hard frames keeps it from matching
perfect-CSI (which handles both regimes because it has the true H).

## 3. DAFT phase / index convention — Python convention wins

The Python sensing / reconstruction / joint receiver uses `p = (q − δ) mod N`
and `-c1·l²` in the phase (consistent with Python's `gen_h_daft` Frobenius
model).  The MATLAB port uses `p = round(q − loc_val)` where
`loc_val = k + 2·N·c1·l` with `+c1·l²` phase and `c2 = 0`.  Both conventions
are internally self-consistent (channel generation, sensing and reconstruction
all use the same sign), but they produce different Φ matrices for the same
`(l, k, c1)` — the scatter direction of `x_pilot` into Φ rows is opposite.

A paired A/B comparison at SNR = 20 / 25 dB (40 frames each, adaptive stop at
300 joint error bits) resolves the question:

| SNR | Python-conv joint BER | MATLAB-conv joint BER | ratio (mat / py) |
|:---:|:---:|:---:|:---:|
| 20 dB | **2.263e-02** ± 2.1e-2 | 3.337e-02 ± 3.7e-2 | 1.48× |
| 25 dB | **2.476e-02** ± 3.0e-2 | 3.552e-02 ± 4.0e-2 | 1.43× |

The joint NMSE mirrors this: Python −15.1 dB vs MATLAB −13.5 dB at 20 dB,
Python −14.7 dB vs MATLAB −13.0 dB at 25 dB — roughly 1.7 dB lower
NMSE for Python, which carries through to the BER difference.  The reason
is that with the canonical `c1 = (2k_max+1)/(2N)` the Python convention
(with non-zero `c2` and negative `c1·l²` sign) produces a sensing dictionary
with slightly lower pairwise column coherence in the high-sparsity /
high-Pact regime that dominates high-SNR channel draws.  Full comparison
report: `paper/convention_comparison_20260419.md`.  **Decision: keep the
Python convention as the canonical one for all final numbers.**

## 4. Configuration decisions locked in (pending convention A/B outcome)

| Setting | Value | Reason |
|---|---|---|
| N_total | 512 | Only kappa-safe choice in {128, 256, 512} for UWA |
| l_max_cap | 50 | Covers the effective UWA delay window |
| k_max_cap | 2 | Enough for v=2 m/s at N=512 |
| P_paths | 10 | MATLAB reference |
| T (outer iters) | **5** | User directive — overrides earlier T=3 MATLAB-alignment |
| pic_iter (MP inner) | 20 | MATLAB-aligned |
| OMP sparsity | P_actual (dynamic) | MATLAB `ls_extract_count = P_actual` behaviour |
| LS ridge | `1e-2 · (σ² + P_d) · N` | Accounts for SP data interference |
| Monte Carlo | 150 frames cap, adaptive stop at 500 joint error bits (min 20) | Statistical stability + compute budget |

Outstanding: final full-SNR rerun and figure regeneration once the A/B
convention outcome is known.
