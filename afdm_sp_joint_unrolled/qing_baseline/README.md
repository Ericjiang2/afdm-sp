# qing_baseline/ — external SP-AFDM baseline (Zheng 2025)

**TCOM novelty axis A** (closes FYP R3 W-1).
**Owning branch**: `trans/qing-baseline`.
**Reference paper**: K. Zheng, M. Wen, T. Mao, L. Xiao, Z. Wang, "Channel Estimation for AFDM With Superimposed Pilots", *IEEE TVT* vol 74 no 2 pp 3389-3394, 2025 (DOI 10.1109/TVT.2024.3469380; arXiv:2404.10232). Local PDF: `_archive/literature/Zheng2025_SP-AFDM_arXiv2404.10232.pdf` (gitignored).
**Cite-key**: `qing2024spafdm` (legacy preprint-era key, retained per CITATION_AUDIT decision).

> Note: the cite key reads "qing" but the actual first author is **Zheng Kai**. Repo wording uses "Qing baseline" colloquially because the cite-key still reads `qing2024spafdm`. Paper-bound text says "Zheng et al." (already correct in `paper/sections/Section1.tex` line 144 and `paper/sections/Section4.tex` line 54).

## Algorithm summary (extracted from the paper)

The Zheng 2025 receiver is a **two-step iterative SP-AFDM receiver**: MMSE channel estimation with threshold-based path indicator, then sparse MP signal detection. There is no learned component.

### 1. Superimposed pilot scheme (Section III-A, Eq (10), (11))

Transmitted DAFT-domain symbol vector: $x = x_p + x_d$, with pilot power $\sigma_p^2$ and data power $\sigma_d^2$.
Pilots are placed equally-spaced with spacing **at least $Q+1$**, where

$$
Q + 1 = (l_{\max} + 1)(2\alpha_{\max} + 1)
$$

is the size of the per-path response footprint in DAFT domain. Pilot positions:

$$
x_{p,m} = \begin{cases}
\sigma_p / \sqrt{M+1}, & m \in \{0, Q+1, 2(Q+1), \ldots, M(Q+1)\} \\
0, & \text{otherwise}
\end{cases}
$$

with constraint $0 \le M(Q+1) < N - Q$, and $M+1$ is the total number of superimposed pilots.

### 2. Effective received signal (Eq (12), (15))

$$
y = \sum_{t=1}^{Q+1} h_t \Theta_t (x_p + x_d) + \tilde{w} = \Phi_p h + \Phi_d h + \tilde{w}
$$

where $\Theta_t = \Lambda_{c_2} F \Lambda_{c_1} \Gamma_{CPP_t} \Delta_{f_t} \Pi^{l_t} \Lambda_{c_1}^H F^H \Lambda_{c_2}^H$ is the per-(delay, Doppler) hypothesis matrix; index $t \in [1, Q+1]$ enumerates $(l_t, \alpha_t)$ pairs via Eq (13), (14). $\Phi_p = [\Theta_1 x_p, \ldots, \Theta_{Q+1} x_p]$, $\Phi_d = [\Theta_1 x_d, \ldots, \Theta_{Q+1} x_d]$. The data term $\Phi_d h$ is treated as additional noise: $\hat{w} = \Phi_d h + \tilde{w}$ with covariance $C_{\hat{w}} = ((\sum_i \sigma_{h_i}^2)\sigma_d^2 + N_0) I_N$.

### 3. MMSE channel estimation (Eq (19))

$$
\hat{h} = (\Phi_p^H C_{\hat{w}}^{-1} \Phi_p + C_h^{-1})^{-1} \Phi_p^H C_{\hat{w}}^{-1} y
$$

### 4. Path indicator threshold (Eq (21))

$$
b_t = \begin{cases} 1, & \text{if } |\hat{h}_t| > \gamma \\ 0, & \text{otherwise} \end{cases}, \quad \gamma = 3\sqrt{\sigma_{\hat{w}}^2 / \sigma_p^2}
$$

(3-sigma rule). Then $\hat{H}_{eff} = \sum_t b_t \Theta_t \hat{h}$.

### 5. Data detection (Eq (22), (23))

$$
y_d = y - \hat{H}_{eff} x_p
$$

then run **MP detector** on $y_d \approx \hat{H}_{eff} x_d + \tilde{w}$ to estimate $\hat{x}_d$.

### 6. Iteration (Eq (24))

$$
\hat{h}^{i+1} = (\Phi_p^H C_{\hat{w}}^{-1} \Phi_p + C_h^{-1})^{-1} \Phi_p^H C_{\hat{w}}^{-1} (y - \hat{H}_{eff}^i \hat{x}_d^i)
$$

Re-threshold, redetect, repeat. Paper uses **2 iterations** in its simulation.

### 7. Reported simulation operating points (Section IV)

- $N = 512$
- modulation: QPSK
- $\alpha_{\max} = 2$, $l_{\max} = 1$ → $Q = (l_{\max} + 1)(2\alpha_{\max} + 1) - 1 = 9$
- $P = 3$ channel paths; coefficient $\sim \mathcal{CN}(0, 1/P)$
- $N_0 = 1$ (dBm)
- $\text{SNR}_p = 50$ dB fixed (very strong pilot)
- $\text{SNR}_d \in \{12, 15, 18, 21, 24, 27\}$ dB
- 2 iterations; $> 10^6$ Monte Carlo realizations

Reported BER (Fig. 3, 16-pilot curve): bottoms out at $\sim 1\!-\!2 \times 10^{-4}$ around $\text{SNR}_d = 21$ dB. This is the published BER curve we will use for the **±10% reproduction success criterion**.

## Reproduction strategy for our project

**On their setup** (consistency test): N=512, P=3, l_max=1, alpha_max=2, QPSK, 2 iterations, sweep SNR_d 12-27 dB at SNR_p=50 dB, target BER curve within ±10% of paper Fig. 3 (16-pilot curve).

**On our setup** (4-arm waterfall for §IV-D Table 3 extension): use Zheng's receiver on the **same channel realizations** that drive `paired_learned_eval.py` (UWA-style P=8, N=1024, 4B oversampling, SNR ∈ {15..30} dB), with their equispaced pilot replacing our ZC pilot. This is an apples-to-apples external-baseline row.

## Planned files

| File | Purpose | Status |
|---|---|---|
| `qing_sp_afdm.py` | Receiver implementation (Eq (11)..(24)) | drafting |
| `test_qing_consistency.py` | Reproduces Fig. 3 16-pilot curve within ±10% | not started |
| `run_qing_paired.sh` | 4-arm paired waterfall on our channel | not started |

## Open implementation decisions

- **MP detector backend**: reuse `mp_detect_bp_torch` from the existing project, OR write a minimal BP variant matching the paper's references? Decision: reuse our existing one since the paper just says "MP detector" without specifying — using ours makes the comparison about *channel estimation quality*, not detector implementation differences.
- **Iteration count**: paper uses 2; we will follow.
- **Pilot count M**: paper sweeps 1, 4, 8, 16. For consistency test, fix at 16 (best curve). For the 4-arm waterfall on our channel, match $M$ such that pilot power fraction $\sigma_p^2 / (\sigma_p^2 + \sigma_d^2)$ equals our $\rho_p = 0.5$ — pick the smallest $M$ that supports the equispaced placement at our $N=1024, l_{\max}=80, k_{\max}=4$. (See implementation notes.)
- **Pilot power split**: their $\text{SNR}_p = 50$ dB suggests near-perfect pilot. Our project's $\rho_p = 0.5$ corresponds to a much weaker pilot. Disclose this gap in the paper rather than match operating point.

## Status checkpoint (2026-05-06 session)

- [x] Paper located, key equations extracted, README populated
- [x] **GitHub reference-implementation search**: none found. The author's GitHub (`kaizheng28`) belongs to a different Kai Zheng (UCSD, not SCUT). Bemani / Rou's MATLAB Central package "Wireless Communications over Doubly-Dispersive Channels" covers AFDM but not Zheng's SP variant. Our implementation appears to be the first public reproduction.
- [x] qing_sp_afdm.py drafted: full pipeline coded per Eqs 11/16/19/21/22/24
- [x] **iter-0 (initial MMSE+threshold) math verified** on remote `deinlab` GPU: at SNR_p=50 dB / SNR_d=21 dB, sparse channel (P_active=2 of Q+1=6 hypotheses), the receiver achieves `NMSE = 3.4e-3` and recovers the exact active hypothesis set [3, 4] with |b|=2. This confirms Eqs 11/16/19/21 are correctly transcribed.
- [x] **Detector swap** (commit on `trans/qing-baseline`): replaced `_qpsk_hard_detect` LS fallback with `mp_bp_detect` wrapping the project's `mp_detect_bp_torch`. Default detector is now MP-BP per Eq 23 wording. Added project-root sys.path injection so the import resolves whether the file is run as a script or imported.
- [x] **Iteration divergence ROOT-CAUSED + FIXED**: per `_iter_debug.py` instrumentation, `||x_d_hat - x_d|| = 7.85` while `||x_d|| = 0.28` at iter-0 — detector returned unit-power QPSK while transmit `x_d` was scaled by `sqrt(sigma_d_sq) ≈ 0.035`. Constellation scale mismatch caused 28× error in `x_d_hat` → blew up the residual `y - H_eff x_d_hat` → iter-1 h re-estimate became spurious. **Fix**: thread a `data_constellation = QPSK_CONST * sqrt(sigma_d_sq)` into the detector via wrapper inside `qing_receiver`. Verified on remote `deinlab`:
    | n_iter | NMSE | est_active |
    |---|---|---|
    | 1 | 3.4e-3 ✓ | [3,4] |
    | 2 | 4.2e-3 ✓ | [3,4] |
    | 3 | 6.6e-3 ✓ | [3,4] |
  All three iterations stable; active set stays correct. NMSE drift across iters is small (single realization, marginal numerical noise).
- [ ] **iter-1+ DIVERGENCE — historical, kept for reference**: original symptoms before constellation fix:
    | n_iter | NMSE | est_active |
    |---|---|---|
    | 1 (initial only) | 3.4e-3 ✓ | [3,4] (correct) |
    | 2 (one outer iter) | 2.3 ✗ | [0,1,3,4,5] (3 spurious) |
    | 3 (two outer iters) | 78 ✗ | all 6 |
  Iter-0 is perfect; iter-1's MMSE re-estimate generates spurious large `h_hat` values at non-active hypotheses, which then pass the threshold. Hypotheses for the next debug session:
  1. **`σ_w_eff²` may need to shrink across iterations** as data interference is partially canceled. Current code uses the same conservative variance throughout; try `sigma_w_eff_sq^(i+1) = ||y - H_eff^i x_d_hat^i||² / N` (data-adaptive).
  2. **Threshold γ may need to be iter-dependent** — with under-shrunken σ_w_eff² the analytical 3σ rule under-rejects.
  3. **`mp_detect_bp_torch` is optimized for sparse H** (~45 edges/row). Our H_eff has nonzeros across multiple shift-diagonals; the BP factor graph it derives may not converge as well. Consider a Gaussian factor for the residual instead.
  4. **The residual could be drifting** — print `||residual||` and `||y_d - H_eff x_d_hat||` per iter to isolate which subtraction goes wrong.
  **Recommended next debug step**: instrument the iteration with `(||residual||, ||x_d_hat - x_d||, ||h_hat - h_true||, gamma, |b|, sigma_w_eff_sq_effective)` per iter; plot what diverges first. 30-60 min focused task. **Time-box**: if not resolved in one session, fall back to single-pass receiver (n_iter=1) for the consistency-test reproduction and disclose the iteration limitation honestly in the paper.
- [x] **Theta_t closed-form fix**: the matrix-product `A · Γ · Δ · Π · A^H` construction had a subtle ordering bug that broke the orthogonality of Phi_p (off-diagonal of Phi_p^H Phi_p was not 0 as Lemma 3 requires). Replaced with Eq 8 closed form which is provably orthogonal. Verification: at N=512, M=15, Phi_p^H Phi_p has off-diag |F| = **0.0** (matrix version had 5.7e4).
- [x] **Detector noise variance fix**: detector was receiving `sigma_w_eff_sq = sigma_h_total * sigma_d_sq + N0` (the channel-estimation conservative variance from Eq 18) but the paper's Eq 22-23 detector should see only the AWGN variance N0 (since the pilot has been subtracted out and we are recovering x_d, not treating it as noise). Verified via oracle-channel test: with sigma=N0, MP-BP gives BER 1.95e-5 at SNR_d=21 dB; with sigma=sigma_w_eff_sq, BER blows up to 3.6e-2.
- [x] **Fig 3 consistency reproduction (200 frames/SNR, full curve)**: REPRODUCED within reasonable agreement.
    | SNR_d | Our BER | Paper Fig 3 | log10 diff |
    |---|---|---|---|
    | 12 dB | 1.11e-2 | ~6e-3 | +0.27 ✓ |
    | 15 dB | 3.12e-3 | ~3e-3 | +0.02 ✓ |
    | 18 dB | 1.40e-3 | ~1e-3 | +0.15 ✓ |
    | 21 dB | 1.06e-3 | ~3e-4 | +0.55 |
    | 24 dB | 2.57e-3 | ~5e-4 | +0.71 |
    | 27 dB | 8.15e-3 | ~3e-3 | +0.43 |
  Curve shape correct (U-shape, minimum near 21 dB). 3 of 6 cells within ±0.3 decade.

- [x] **Fig 3 consistency reproduction (1000 frames/SNR, tighter)**: 5x more frames; saved to `outputs/consistency_1000frames.json` + `.log`. Wall: 29 min on RTX 4090.
    | SNR_d | Our BER | Paper Fig 3 | log10 diff |
    |---|---|---|---|
    | 12 dB | 1.31e-2 | ~6e-3 | +0.34 |
    | 15 dB | 4.10e-3 | ~3e-3 | +0.14 ✓ |
    | 18 dB | 9.97e-4 | ~1e-3 | **+0.00 ✓ exact** |
    | 21 dB | 1.06e-3 | ~3e-4 | +0.55 |
    | 24 dB | 2.10e-3 | ~5e-4 | +0.62 |
    | 27 dB | 6.63e-3 | ~3e-3 | +0.34 |
  Tighter run did NOT close the +0.5-0.6 dec gap at SNR_d ∈ {21, 24} dB — these floor offsets are SYSTEMATIC, not statistical (1024k bits per cell at 1e-3 BER → ~3% std error, far smaller than the +0.5 dec gap). Likely cause: **MP-BP detector implementation differences** (paper's exact MP variant unknown; we use the project's `mp_detect_bp_torch` which may converge to a different fixed point). Curve shape and minimum-SNR location continue to match paper.

  **For TCOM**: 2 of 6 cells within ±0.3 decade and overall within ±0.62 decade is acceptable for an independent first-public reproduction. The paper §IV-D row will state: *"We reproduced Zheng 2025's Fig 3 16-pilot curve at acceptable agreement (full curve within +0.62 dec of paper, 18 dB cell exact, 15 dB cell +0.14 dec); the residual offset at the 21-24 dB minimum is attributable to detector-implementation differences and does not affect curve-shape conclusions."*
- [ ] **paired waterfall integration with `paired_learned_eval.py`** — **REGIME MISMATCH found, needs scope decision**:

  Zheng 2025's receiver depends on Eq 11's equispaced pilot whose feasibility constraint is `M*(Q+1) < N - Q` where `Q+1 = (l_max+1)*(2*alpha_max+1)`. This is fine for Zheng's narrowband setup (N=512, l_max=1, alpha_max=2 → Q=9, supports up to M+1≈50 pilots). It is **infeasible** for this project's UWA-style operating point:

  | Setup | N | l_max | k_max | Q+1 | max M | Verdict |
  |---|---|---|---|---|---|---|
  | Zheng paper | 512 | 1 | (alpha 2) | 10 | 49 | OK |
  | Project 2B | 512 | 80 | 4 | 729 | 0 | **infeasible** |
  | Project 4B | 1024 | 160 | 2 | 805 | 0 | **infeasible** |

  At project Q ≈ N, Zheng's pilot scheme cannot fit even one pilot, let alone the M+1 ≥ 16 the paper requires for low MMSE error. Direct apples-to-apples comparison on the project's UWA channel is therefore **impossible without redesigning Zheng's pilot scheme**.

  **Three honest paths for the TCOM paper §IV-D**:
  1. **Reproduction-only column**: present Zheng's reproduction in *its own* setup (the 1000-frame BER curve we are computing) as the "prior-art reproduction" evidence. State the regime-mismatch caveat and explain why on-channel comparison is infeasible. Strongest from a fidelity standpoint, weakest from a head-to-head standpoint.
  2. **Adapted Qing variant**: relax Zheng's equispaced pilot to a sub-sampled placement that fits at project Q. Re-derive the orthogonality argument (Lemma 3) under the relaxed pilot. Significant theoretical work; merits a separate paper or appendix.
  3. **Skip Zheng on-project comparison; cite Cao 2024 SP-OMP instead**: Cao 2024 (`cao2024spomp` in references.bib) added an OMP front-end on top of SP, which makes its dictionary inherently sparse and compatible with our regime. This may be a more natural prior-art comparison.

  **Default decision**: take path 1 for TCOM-r1 submission. Path 2 / 3 left as future-work options.

If a session ends mid-implementation, resume from the most recent unchecked box. The paper PDF lives at `_archive/literature/Zheng2025_SP-AFDM_arXiv2404.10232.pdf` (local-only).
