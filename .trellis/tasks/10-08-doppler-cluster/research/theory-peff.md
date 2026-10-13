# Theory: SNR-dependent effective order P_eff (draft, 2026-10-08, main session)

Status: derivation sketch + predictions; to be checked against F2 (oracle order ladder) and true-H slopes.

## Setup
Tap l time series a_l[n] = sum_{r in S_l} g_r exp(j2pi nu_r n/N), g_r ~ CN(0, p_r) independent, Dopplers given.
Conditional tap covariance R_l = V_l P_l V_l^H (V_l: N x R_l Vandermonde). Eigenvalues lambda_{l,1} >= lambda_{l,2} >= ...,
sum_k lambda_{l,k} = N E_l, E_l = sum_r p_r. Normalized mu_{l,k} = lambda_{l,k}/(N E_l).
Frame-integrated component SNR: gamma_{l,k} = lambda_{l,k} / sigma_eff^2 = mu_{l,k} N E_l / sigma_eff^2.

## Claim 1 (diversity side)
With full-diversity AFDM chirp design and coherent detection, pairwise error probability over the gain randomness
P(c -> c') <= prod_{l,k} (1 + gamma_{l,k} d_{l,k}/4)^{-1} (d: codeword-difference projections). Components with
gamma_{l,k} << 1 contribute ~1 factor -> harvested diversity at SNR = #{(l,k): gamma_{l,k} >~ 1} =: P_eff(SNR).
(Standard Chernoff/PEP argument; new part is the per-tap Doppler-Gram eigenstructure as the diversity count.)

## Claim 2 (estimation side, same threshold)
From T1 (headroom theory): each complex coefficient estimated costs ~sigma_eff^2/N residual per sample (data-aided).
Omitting component k leaves misfit mu_{l,k} E_l per sample. Include k iff mu_{l,k} E_l > sigma_eff^2/N <=> gamma_{l,k} > 1.
=> MSE-optimal per-tap order D_l*(SNR) = #{k: gamma_{l,k} > 1} -> sum_l D_l* = P_eff(SNR).
"The order a receiver should estimate equals the diversity it can harvest."
A fixed-order receiver with D_l < D_l* pays twice: misfit floor (SINR -> (1-rho)(1-eta)/(sigma^2 + eta),
eta = sum_{k>D} mu_k E) AND lost diversity. Over-order (D > D*) pays only variance (~D/N).

## Claim 3 (eigenvalue law vs spread)
mu_{l,k} for rays spread over s_l bins: s << 1: confluent/Taylor regime mu_k ~ c_k (pi s)^{2k} -> D* grows only
logarithmically: D* ~ log(N E/sigma^2) / log(1/(pi s)^2). s >~ 1: Slepian/Landau-Pollak regime: ~2s+1 eigenvalues near
1/(2s+1), then plunge -> D* ~ 2s + 1 + O(log SNR). Same basis family (DPSS around centroid / confluent atoms).
Numerical check already: confluent residuals table (../10-08-headroom-ladder/research/ideation-v2.md).

## Claim 4 (conditioning)
Per-ray parametric basis for a sub-resolution doublet: Gram cond ~ delta^-2 (measured 4.9e2 at delta .05); confluent /
DPSS basis bounded (3.29). So the estimable object is the D*-dim tap subspace, not the rays.

## Predictions for F2 (oracle ladder O_D, 1-bin sub-path grid around centroid; D in {1,2,3,5})
- D1 (single ray): D* = 1.
- N4a (5deg, mean max spread .39 bin): D* ~ 2 at 9-12 dB.
- N4b (20deg, 1.51): D* ~ 3.
- J4 (Jakes, 3.67): D* ~ 5 (2s+1 with s ~ 2 half-spread -> ~5).
- True-H FER slope grows with spread (diversity), B's does not.
Falsifier: if O_1 already ~ A3 on N4b/J4, representation is not the issue (then B's loss is acquisition/estimation).

## Novelty position (to be checked)
Pieces classical (PEP diversity counting, Landau-Pollak/DPSS dimension, confluent Vandermonde conditioning, MDL-style
order). Claimed new: the identity "estimation-optimal per-tap order = harvested diversity count" for SP-AFDM in
clustered fractional-Doppler channels, its SNR staircase, and a receiver that tracks it. Closest: Benzine-Bemani 2025
(fixed DPSS order per grid point, embedded pilots).

## Pre-registered numeric prediction (before F2 results; MC 300 taps/config, F1 law, E_l=.25, gamma_k = mu_k N E/sigma2 > 1)
| config | D* @6 dB | @9 dB | @12 dB | p10-p90 @9 |
| D1 | 1.00 | 1.00 | 1.00 | 1-1 |
| N4a | 1.93 | 2.03 | 2.14 | 1-3 |
| N4b | 2.60 | 2.69 | 2.77 | 2-4 |
| J4 | 3.52 | 3.58 | 3.63 | 2-5 |
Shallow SNR staircase because rank <= rays per tap (~4). F2 oracle ladder (1-bin grid, slightly suboptimal vs eigen-
subspace) predicted to saturate at D ~ 2 (N4a), ~3 (N4b), ~4-5 (J4), D = 1 sufficient for D1.

## F3 outcome (expected-power law, true-H, 2000 frames, SNR 6-14)
Slopes d (FER window 1e-3..1e-1): D1 3.29, N4a 3.73, N4b 3.99, J4 6.55, J8 6.77, S16 7.10. Group split resolved
({D1,N4a,N4b} vs {J4,J8,S16}; J4 > N4b P=.997); Spearman(P_eff, d) = .94; within-group order unresolved.
Claim 1 holds QUALITATIVELY (diversity governed by per-tap Doppler eigen-structure; sub-resolution clusters add ~nothing,
spread taps add as much as resolvable paths: 4 Jakes taps ~ 16 separable paths). Hard count #(gamma>1) NOT proportional
to coded slope (saturation, threshold crude) -> paper claims eigen-structure governance, not "diversity = #(gamma>1)".
Punchline: richest-diversity channels (J4) are where parametric SP receivers collapse (B FER .87 @9 dB vs true-H .002).
Caveat: F1/F2/M1 used realized per-frame power normalization (suppresses energy fading); paper-grade runs use expected.
