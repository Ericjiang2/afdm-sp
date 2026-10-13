# Ideation v2: universal multipath fractional-Doppler channel (2026-10-08)

User: channel should be universal (multipath + fractional Doppler), not UWA-specific. C1 (wideband scale) demoted to a
remark (its within-frame drift is also a band-limited tap variation, covered by the model below).

## Problem (new-problem level): same-delay Doppler clusters
Real multipath fractional-Doppler channels have several rays per delay bin with Doppler gaps < 1/T (Jakes per tap,
clustered geometric channels). Within one frame they are unresolvable; parametric path estimators (production B: P slots
with continuous Doppler) face model-order misfit or ill-conditioning (S7: true-geometry condition number ~8e7).
Measured (res-20261008-01): B's residual error floor disappears with genie delays+multiplicity (A1); same-delay
underfit is the consistent per-frame failure predictor (AUC .64-.77); paper theorem already has a "same-delay doublet
obstruction". Most AFDM/OTFS literature assumes few resolvable discrete paths.

## Insight
Detection needs the tap function a_l[n] = sum_{i in S_l} h_i exp(j2pi nu_i n/N), not the rays. AFDM places each tap's
Doppler spectrum in its own DAFT window (offset 2Nc1·l). A cluster with spread s (bins) is (near-)exactly representable by
D ~ 2s + 1 + O(log 1/eps) Slepian (DPSS) functions of half-bandwidth s around its centroid: dimension set by spread, not
ray count. D = 1 recovers the current parametric path.

## Model / method candidate ("Slepian cluster atoms")
Per active delay: continuous centroid nu_bar (1 real) + D complex coefficients on DPSS(N, s). Drop-in replacement of the
geometry step (time_refine) inside the SP turbo receiver; D chosen per cluster by MDL / resolvability statistic.
Theory targets: (i) representation residual <= prolate eigenvalue tail (closed form vs s, D); (ii) parametric K-path misfit
or conditioning blow-up near the resolution limit (ties to paper's doublet theorem); (iii) floor SINR = (1-rho)/eta_misfit.
Closest work: DPSS-BEM (Zemen-Mecklenbrauker 2005, OFDM), GCE-BEM SP-OTFS (Huang et al. 2024), threshold on-grid EP
(Raviteja 2018). Distinction to verify: per-cluster centroid+spread-adapted subspace inside SP-AFDM turbo, motivated by
measured floor; not a full-band BEM.

## Falsification first (no method build yet)
F1. Universal clustered generator on the physical CPP operator: L taps (exp PDP), rays per tap ~ 1 + Poisson(lambda-1),
    ray Doppler nu_max cos(theta), theta ~ U; sweep lambda in {1, 2, 4, 8}. Production B vs true H (A3).
    Prediction: B->A3 gap and floor grow with lambda; A3 roughly unchanged (diversity similar).
F2. Oracle representation test: TF detection with H projected onto (a) K-path model with B's fitted counts,
    (b) Slepian cluster atoms D in {1,2,3} around true centroids. Prediction: (b) D=2-3 ~ A3; (a) degrades with lambda.
Kill: if B->A3 gap at FER 1e-2 stays < .2 dB for lambda = 4, the cluster problem is not consequential for SP-AFDM.

## Math check: confluent atoms (2026-10-08, deinlab numpy, N=1024, 2-ray doublet nu_bar +- delta/2, 200 random gains, median)
| delta | cond doublet Gram | cond confluent | resid 1-exp best | resid confl-2 {e, t e} | resid confl-3 {e, t e, t^2 e} |
| .05 | 4.9e2 | 3.29 | 6.7e-4 | 8.5e-7 | 1.6e-10 |
| .10 | 1.2e2 | 3.29 | 3.3e-3 | 1.4e-5 | 1.1e-8 |
| .25 | 1.9e1 | 3.29 | 1.5e-2 | 5.3e-4 | 1.8e-6 |
| .50 | 4.5   | 3.29 | 6.9e-2 | 7.9e-3 | 1.4e-4 |
| .75 | 1.9   | 3.29 | 1.3e-1 | 3.7e-2 | 1.5e-3 |
| 1.0 | 1.0   | 3.29 | 1.8e-1 | 1.1e-1 | 7.0e-3 |
(t = (n-(N-1)/2)/N, atoms 2pi j t^k e_nu_bar). Doublet basis cond ~ delta^-2 (confluent Vandermonde); merging to one
exponential leaves 7-18% residual for delta in [.5,1] (twilight zone, where B likely misfits); 3 confluent atoms <= .7%
residual for all delta <= 1 at fixed conditioning. -> Method candidate: per-delay centroid + confluent (Taylor/DPSS)
atoms replacing per-path slots below the resolution limit; separate paths above it. Known primitive (Taylor atoms /
continuous basis pursuit, Ekanadham et al. 2011; DPSS-BEM) -> novelty = AFDM-SP cluster problem + conditioning theory.
