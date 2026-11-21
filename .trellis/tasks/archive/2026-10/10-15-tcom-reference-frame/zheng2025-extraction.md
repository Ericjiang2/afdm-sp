# Zheng et al. 2025 (GLOBECOM) — extraction for P2a (Opus, 2026-10-15)

Source: K. Zheng, M. Wen, T. Mao, L. Xiao, Y. Tang, A. D. Aref, "Joint Channel Estimation and Data Detection for AFDM
With Superimposed Pilots," IEEE GLOBECOM 2025, pp. 1298–1303, DOI 10.1109/GLOBECOM59602.2025.11432016.
Full text: `papers/Zheng2025_GLOBECOM_JCED_AFDM_SP.pdf` (git-ignored). Equation numbers below are the paper's.

## 1. System model (Sec. II)
- DAFT domain: x = x_p + x_d, no guard. Data are K-PSK with E[x_d x_d^H] = σ_d² I_N.
- Pilot (eq. 1): x_p[i] = σ_p/√M at i = t(Q+1), t = 0..M−1, and 0 elsewhere. ||x_p||² = σ_p² is the total pilot energy.
- s = A^H x. Received r[n] = Σ_i h_i s[n − l_i] e^{j2π f_i n} + w[n] (eq. 3). DAFT output: y = H_eff x + w̃ = Σ_i h_i H_i x + w̃ (eq. 4).
- H_i(n, m) = exp(j2π/N (N c1 l_i² − n l_i + N c2 (n² − m²))) at n = ⟨m + loc_i⟩_N with loc_i = α_i + 2N c1 l_i, else 0 (eq. 5).
  α_i = N f_i ∈ [−α_max, α_max] and l_i ∈ [0, l_max] are **integers**. c1 = (2α_max + 1)/(2N); c2 is "an arbitrary
  irrational number" (no value given).

## 2. Channel estimation (Sec. III-A)
- Grid size M_p = (2α_max + 1)(l_max + 1) (eq. 7). l_max and α_max are known. The guard interval needs Q ≥ M_p.
- y = Σ_{j=1}^{M_p} h_j Ξ_j x + w̃ with Ξ_j = A Γ_CPPj Δ_{f_j} Π^{l_j} A^H (eqs. 8–9),
  l_j = ⌊(j−1)/(2N c1)⌋, α_j = ⟨j−1⟩_{2Nc1} − α_max (eqs. 10–11).
- y = X h + w̃, X = [Ξ_1 x, ..., Ξ_{M_p} x] (eqs. 12–13). LS estimate: ĥ = (X^H X)^{-1} X^H y (eq. 14).

## 3. Algorithm 1 (iterative JCED inside message passing, Sec. III-B)
Inputs: y, x_p, σ², P, α_max, l_max. Initialisation: p_j^0(a_k) = p_jc^0(a_k) = 1/K, ĥ^0 = 0, Ĥ_eff^0 = 0. For i = 1..i_m:
1. Soft data: x̄_d^i[j] = Σ_k p_j^{i−1}(a_k) a_k (eq. 18).
2. CE with interference cancellation: ĥ^i = (X_p^H X_p)^{-1} X_p^H (y − Ĥ_eff^{i−1} x̄_d^i) (eq. 20), with X_p the
   matrix of eq. 13 built from x_p (orthogonal columns by the pilot spacing).
3. Path set: Ind^i = maxk(|ĥ^i|, P), i.e. keep the P largest-magnitude taps. **P (the number of paths) is assumed known**
   (eq. 21). If Ind^i ≠ Ind^{i−1}, reset p_jc^i(a_k) = 1/K.
4. Ĥ_eff^i = Σ_{j ∈ Ind^i} ĥ_j Ξ_j (eq. 22); y_d^i = y − Ĥ_eff^i x_p (eq. 24).
5. MP (from Raviteja et al. 2018, their ref. [10]), with I_c / J_j the nonzero sets of row c / column j of Ĥ_eff:
   - mean μ_cj = Σ_{e∈I_c, e≠j} Σ_k p_ec^{i−1}(a_k) a_k Ĥ(c, e) (eq. 25);
   - variance (σ_cj)² = Σ_{e≠j} (Σ_k p_ec^{i−1} |a_k Ĥ(c,e)|² − |Σ_k p_ec^{i−1} a_k Ĥ(c,e)|²) + σ² (eq. 26);
   - φ(j, e, k) = exp(−|y_de − μ_ej − Ĥ(e, j) a_k|² / (σ_ej)²) (eq. 28);
   - p̃_jc(a_k) ∝ Π_{e ∈ J_j, e ≠ c} φ(j, e, k) (eq. 27);
   - damping p_jc^i = (1 − δ) p_jc^{i−1} + δ p̃_jc (eq. 29);
   - p̃_j(a_k) ∝ Π_{e ∈ J_j} φ(j, e, k) (eq. 30).
6. Convergence (following Thaj–Viterbo): ζ_i = (1/N) Σ_j 1(1 − max_k p̃_j(a_k) < ε) (eq. 31). p_j^i = p̃_j if
   ζ_i > ζ_i^* (the largest ζ before iteration i), else p_j^{i−1} (eq. 32). Stop if ζ_i^* − ζ_i > γ or ζ_i = 1 or i > i_m.
7. Output x̂_d[j] = argmax_k p_j^{i_m}(a_k) (eq. 33). The system is **uncoded**.

## 4. Simulation parameters (Sec. IV)
N = 512, K = 4 (QPSK), δ = 0.1, γ = 0.1, ε = 0.2, i_m = 20, P = 3, l_max = 2, **α_max = 1** (the arXiv preprint uses 2).
Each path has a distinct delay index and a random integer Doppler in [−α_max, α_max]. With P = 3 and l_max = 2, the
delays are exactly {0, 1, 2}. h_i ~ CN(0, 1/P). σ² = 1 dBm; SNR_p = σ_p²/σ² (total pilot energy) and SNR_d = σ_d²/σ²
(per data symbol). The conventional SP uses n_iter = 4 and threshold-aided CE (their ref. [6]). EP uses a linear MMSE
receiver. Fig. 4 uses M = 8 pilots: its Prop. SP / SNR_p 50 dB curve coincides point by point with the M = 8 curve of Fig. 5.

## 5. Read-off values (from the 450-dpi crops; read uncertainty about ±10% on a log axis)
Fig. 4a / Fig. 5 (Prop. SP, uncoded BER, SNR_d = 8, 11, 14, 17, 20, 23 dB):
- SNR_p 50, M = 8: 4.3e-2, 1.4e-2, 3.4e-3, 9.3e-4, 3.8e-4, 3.5e-4
- SNR_p 40, M = 8: 4.3e-2, 1.4e-2, 3.9e-3, 1.25e-3, 1.0e-3, 3.9e-3 (upturn at 23 dB)
- SNR_p 50, M = 1 (Fig. 5, 11–23 dB): 1.5e-2, 5.5e-3, 3.0e-3, 2.45e-3, 2.5e-3
- SNR_p 50, M = 4 (Fig. 5, 11–23 dB): 1.45e-2, 4.3e-3, 1.7e-3, 1.18e-3, 1.2e-3
- EP, SNR_p 50: 5e-2, 2.0e-2, 7.5e-3, 1.7e-3, 3.3e-4, 5.5e-5
Fig. 2 (MSE, SNR_p 50; the MSE definition is not stated): Prop. SP about 8.4e-3, 7.8e-3, 8.0e-3, 9.0e-3, 1.07e-2,
1.4e-2; SP without IC about 1.35e-2 rising to 6.5e-2; EP flat at about 6.3e-3.

## 6. Ambiguities and the resolution used here
| Item | Paper | Resolution |
|---|---|---|
| c2 | "arbitrary irrational" | own regime: c2 = 1/(2πN²) (irrational, small), recorded as a constant; port: the production system's c2 |
| pilot phase | not stated | real positive impulses σ_p/√M |
| MSE definition (Fig. 2) | not stated | report E‖ĥ − h‖² / E‖h‖² over the M_p grid; use only orderings and trends in the gate |
| threshold-aided CE of the conventional SP / EP | ref. [6] | not reproduced (not needed for H5) |
| frames per point | not stated | 2000 frames (1024 bits each) |
| bit mapping | not stated | Gray QPSK |
