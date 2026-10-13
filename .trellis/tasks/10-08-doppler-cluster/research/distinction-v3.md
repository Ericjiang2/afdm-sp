# Distinction judgment (main session, from lit-v3.md evidence packets; A8 quote re-verified from source)

## C2 — AFDM diversity under general Doppler spectra
Shared core (build on, cite): Sayeed-Aazhang 1999 (Doppler spread = diversity ~ time-bandwidth product);
Ma-Giannakis 2003 (max diversity = rank of BEM-coefficient correlation, multiplicative (Q+1)(L+1)); Ma-Leus-Giannakis
2005 (rank-based, holds for Jakes channels). Bemani 2023: AFDM diversity = min rank Phi(delta) <= P, model already allows
multiple Doppler paths per delay tap; proof given ONLY for integer Doppler, fractional claimed without proof.
Our distinct piece: proof that AFDM (with its c1 condition) attains the rank-based maximum for fractional/continuous
per-tap Doppler spectra, i.e. closes Bemani's integer-only gap and restates AFDM full diversity as Ma-Giannakis rank.
Substantive but narrow -> supporting theorem/lemma, not the paper core.

## C1 — SP bootstrapping limit in rich doubly-dispersive channels
Shared core (build on, cite):
- Convergence thresholds of iterative CE+decoding exist: Porto-de Lamare (threshold tied to initial estimation error,
  which depends on #pilots vs #unknowns, T >> L_e K); Takeuchi (density-evolution SNR threshold, pilot-aided);
  Liang-Rave-Fettweis (SP-OFDM density evolution vs rho and burst length; optimal rho); EXIT with channel estimation.
- Richness double-edge exists qualitatively/quantitatively for PILOT-based receivers: Baissas-Sayeed 2000;
  Zhou-Wu-Fan TWC 2015 (Doppler diversity vs estimation error, repetition code); Wang 2026 AFDM (BER rises with path
  count under fixed pilot overhead — verified).
- BEM order trade-off precision vs unknowns: Benzine-Bemani 2025 (embedded pilots, known support, Q_BEM 3-4).
- SP + DPSS doubly-selective estimation with self-interference: older superimposed-training papers (titles only).
Our distinct contribution (substantive if experiment confirms):
1. For SP the pilot "count" is fixed (= N, all chips); the binding resource becomes self-interference-limited energy.
   Closed form DoF budget K* ~ rho N [(1-rho)/gamma_th - sigma^2]/(sigma^2 + 1 - rho): SP-specific counterpart of
   "pilots >> unknowns". Not stated in any packet.
2. Mechanism is a THRESHOLD (loop fails to start) rather than smooth MSE degradation -> predicts a sharp,
   non-monotone FER vs richness cliff for SP receivers, distinct from the smooth pilot-based trade-off (Zhou-Wu-Fan,
   Wang 2026).
3. Joint diversity (C2) + bootstrapping (C1) frame for SP-AFDM: operating region in (K, rho, N, SNR); prior/order
   shaping (Slepian/Wiener: K -> K_eff) moves K*; explains why BEM order is irrelevant far from K* (our M2) yet decisive
   near it; order-progressive bootstrapping as the design consequence.
Must cite/build on: Porto-de Lamare, Takeuchi, Liang et al., Zhou-Wu-Fan, Wang 2026, Benzine et al., Zemen 2012,
superimposed-training + DPSS line, Ma-Giannakis, Bemani.
Status: core concepts shared; the SP-specific DoF budget, threshold (cliff) mechanism and diversity-bootstrapping
operating region are the distinct, testable contribution. Decisive experiment required before any claim.

## Decisive experiment (design)
Isolate bootstrapping from acquisition: genie delay support for SP receivers (coefficient DoF is the variable), clustered
Jakes taps, L in {4, 8, 12, 16, 24, 32} (K = L x 8 DPSS coeffs), rho in {.2, .3, .5}, SNR fixed (8 dB) + one other.
Arms: true H; SP-DPSS flat prior; SP-DPSS Slepian prior; (later) order-progressive. Log first-pass (pilot-only) SINR.
Predictions: (i) true-H FER decreases monotonically with L; (ii) SP FER U-shaped with a cliff near K*(rho); K*
ordering rho .5 > .3 > .2 roughly as formula (~200/152/109 at 8 dB); (iii) first-pass SINR follows (1-rho)/(sigma^2+eps)
with eps ~ K(sigma^2+1-rho)/(rho N); (iv) Slepian prior pushes the cliff outward vs flat prior.
Kill: no cliff/U-shape, or cliff location independent of rho.

## C1 decisive experiment outcome (out/c1_boot; 144000 rows; genie delays; Jakes taps L 4..32; rho .2/.3/.5; 8/11 dB)
(i) CONFIRMED: true-H FER non-increasing in L (0/30 increases).
(ii) Cliff CONFIRMED (SP FER <=1% -> .6-1.0 while true-H ~0; L32 8 dB: .99 vs 0). U-shape REFUTED in this SNR range
     (true-H already ~0 at small L). Naive K* = rho N[(1-rho)/g - s2]/(s2+1-rho) REFUTED (rho order reversed at 8 dB).
(iii) Mechanism CONFIRMED: eps1 = shrinkage-corrected LS law within 0-7%; cliff = near-universal first-pass SINR
     threshold g ~ 1.3-1.5 (round-1 reliability AUC .996-.999; logistic 10-90% ln-width .17-.33).
(iv) Slepian-prior outward shift REFUTED (sign depends on rho).
Main-session re-derivation (flat-prior LMMSE): eps = K s/(1+K s), s = (s2+1-rho)/(rho N); threshold (1-rho)/(s2+eps)=g
  => K* = b/((1-b) s), b = (1-rho)/g - s2.  g=1.3: 8 dB pred 180/219/229 vs obs 186/201/161 (rho .2/.3/.5);
  11 dB pred 269/334/388, obs order matches (rho>=.3 censored >256). Agent fit: g 1.37, rms log err .115.
  rho .5 @8 dB miss coincides with decoder waterfall (SP FER .10-.15 already at small L) — confound, not refutation.
Status: C1 = SP bootstrapping cliff + universal first-pass SINR threshold + shrinkage-corrected DoF budget (~12%).
Dropped: U-shape claim (untested regime), prior-shaping claim. Next: lower-SNR/finer-L map of the diversity-vs-cliff
trade-off; order-progressive bootstrapping (reduce first-pass DoF) as the design consequence.

## C1 follow-up outcome (out/c1_map 40k rows; out/c1_tdl 96k rows; commit 35225b4c)
Part A (rho .3, genie delays, L 2..32, 5/6.5 dB):
- U-shape (richness double edge) CONFIRMED at 6.5 dB: SP FER .213 (L2) -> .127 (L6) -> 1.0 (L32); split-sample p=3e-4;
  true H monotone. At 5 dB not significant (waterfall floor). -> restore U-shape claim WITH regime qualifier.
- K*(g=1.37) fitted at 8/11 dB predicts cliff out-of-sample: 6.5 dB 134 vs K_c 134 [131,137] (raw level .5);
  5 dB only with conditional definition P(SP fails | A3 decodes) = 70 [67,73] vs 73 (definition post hoc, label it).
- eps1 obs/pred 1.00-1.03 (shrinkage law exact to 3%).
- SP - A3 gap nonzero at every L (L2 @6.5 dB: 38/0): smooth sub-cliff loss + cliff. Hypothesis (untested): sub-cliff loss
  = local variance law ~10log10(1+K/N), amplified by the code waterfall; both regimes scale with K/N.
Part B (TR 38.901 TDL-A/B/C, values verified vs Tables 7.7.2-1..3; Jakes taps nu_max 2 bins; max delay 30/60 samples):
- Genie-support SP: K/K* .29-.91, never past cliff; still .11-.39 FER above true H at 8 dB (P(SINR1<g) only .02-.12 at
  rho .5 -> converged-loss shoulder at the waterfall, not loop-start failure; at rho .2 P(SINR1<g) .15-.36 ~ FER).
- Count-blind SP (acquired delays, dev-tuned theta 3): acquisition-limited (keeps 6-12 of 13-18 true delays, 0-9 false,
  missed energy 2-11%), worse than genie in 24/24; second failure mode = support acquisition under SP self-interference.
- Production parametric B: FER >= .96 in 24/24 (cluster model mismatch + 8-slot cap) -> standard 3GPP TDL channels
  break the paper's parametric SP receiver.
Scaling (main session): K* = kappa N, kappa = b rho/((1-b)(s2+1-rho)) = .155/.198/.345 (8 dB rho .2 / 8 dB .5 / 11 dB .5).
Feasibility T*D < kappa N. With D ~ 2 nu_max + 1 + margin: N 1024 nu 2 -> TDL below cliff (observed); N 256 nu 1
(common AFDM regime) -> K ~ 60-90 vs K* 40-51 -> predicted PAST cliff. P2 (K* proportional to N) still UNTESTED.
Open: g is fitted (decoder/detector/schedule property) -> needs EXIT-type prediction, not a fit.
Status: C1 = cliff + universal g + K* = kappa N (in- and out-of-sample) + U-shape at moderate SNR. TDL at N1024 sits on
the shoulder, not past the cliff; realism claim hinges on N-scaling.
