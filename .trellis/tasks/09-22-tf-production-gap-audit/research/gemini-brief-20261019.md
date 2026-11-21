# Deep Research brief: SP-AFDM data-aided receiver — contribution assessment and improvement ideas

I am preparing an IEEE Transactions on Communications (TCOM) submission. Below are the current main line, the evidence I
hold (favourable and unfavourable), and its known weaknesses. I want three things from you: an independent judgement of
whether the contribution is sufficient for TCOM, a prior-art search that tries to **break** my novelty claims, and
improvement ideas. "The main line is too weak; change the framing or direction" is an acceptable answer.

Evidence conventions: unless stated otherwise, results are pre-registered tests on fresh frames with frame-bootstrap 95%
CIs. Items marked *(post hoc)* were found after seeing data; items marked *(draft)* are recent and not yet accepted by me.

## 1. System and receiver

- **Waveform.** Affine frequency division multiplexing (AFDM), N = 1024, chirp-periodic prefix (CPP), single antenna.
  **Superimposed pilot (SP)**: pilot and data share all N chirp subcarriers; pilot power fraction ρ ∈ {0.3, 0.5}.
- **Coding.** QPSK, regular (3,6) LDPC, n = 2048 (rate 1/2). σ² known at the receiver.
- **Channel.** 8 paths, integer delays up to 102 samples, fractional Doppler (|α| ≤ 2 bins). Two Doppler laws: an
  underwater-acoustic-type positive-Doppler law (U) and a Jakes-type law ν = 1.62 cos θ (G). Per-frame unit path power, no
  large-scale fading. Delays are capped at the receiver's delay bank by redrawing (48.6% of natural draws redrawn). In the
  main generator every path has a distinct delay. A second test family has same-delay Doppler clusters (Jakes-4 rays per
  tap).
- **Generator history.** The main results use a corrected generator (delay-cap and subcarrier-spacing defects fixed, unit
  per-frame power). An earlier developmental study on the uncorrected generator had concluded that the CSTATE benefit was
  specific to F0 and that global reopening had no advantage over local refinement; the corrected-generator confirmation below
  reversed both.
- **F0 (baseline deployable receiver).** Pilot-only front end (delay detection, Doppler/gain fit), then a turbo loop: a
  two-FFT (TF) data detector with data-aided channel refinement (20 inner iterations, 2 outer rounds) and LDPC decoding.
- **CSTATE (added on top of F0).** Triggered only when F0's LDPC syndrome is nonzero. It rebuilds the sensing dictionary
  from the decoder's soft symbols (mean μ, variance v) and runs a fixed-cardinality (P = 8 slots) global support exchange:
  every slot × candidate atom in a delay–Doppler bank gets an exact joint replace score from A = BᴴB + Γ + λI with objective
  ‖y‖² − bᴴA⁻¹b. Up to two swaps are accepted, followed by local Doppler refinement and one more TF + LDPC continuation.
  Γ is the full projected data-uncertainty covariance, Γ_ij = tr(U_iᴴ U_j V) with V = diag(v). The SP-OTFS/AFDM
  data-aided papers I have read model the data residual as scalar/white interference, i.e. Γ = Σv · I. CSTATE's score is the
  exact second moment of an EM-type objective, so I do not regard the scoring rule itself as a new algorithm.
- **Theory in hand (restricted).** The scalar model is exact iff the off-diagonal trace functionals vanish on the covariance
  family. For a same-delay doublet in the AFDM/CPP dictionary, the uncertainty Gram has eigenvalues 1 ± |D_N(Δν)|
  (Dirichlet kernel), so the scalar model's worst-case spectral error is |D_N(Δν)|. In OFDM tap dictionaries with constant
  symbol variance the scalar model is exact. The theorem says nothing about FER, convergence or optimality, and the
  2×2 eigenvalue fact itself is elementary.

## 2. Evidence

### Claim A — receiver performance against references

FER = 1e-2 crossing points, 2000 frames per SNR point, 4 cells (U/G × ρ .3/.5); "B" = F0 + CSTATE.

| comparison | result |
|---|---|
| B vs F0 | gain +1.27 to +1.88 dB at ρ .3, +0.45 to +0.56 dB at ρ .5; no frame where F0 decodes and B fails; B removes F0's error floor at ρ .3. The pre-registered hypothesis is formally INCONCLUSIVE because one cell (U, ρ .5) has 2/3 significant SNR points (one under-powered high-SNR point), although the gain CI excludes 0 in all four cells |
| B vs true-H receiver | 0.12–0.14 dB at ρ .5. At ρ .3 it is 0.48–0.55 dB, so the pre-registered "within 0.5 dB of genie" fails at ρ .3 |
| B vs stronger front end F1 | B better by 0.37–0.90 dB at 0.47–0.57× F1's run time. F1 + CSTATE is the most reliable arm, at about 2× B's time |
| B vs local-only variant | local refinement instead of global exchange loses 0.18–1.34 dB |
| run time (mean s/frame, shared host) | F0 .255, B .299, F1 .572, true-H .157 |
| vs published SP-AFDM JCED (Zheng et al., GLOBECOM 2025) | The printed constants do not reproduce the paper's own figures; authors asked. Ported to my channel (with my labelled adaptations, including a stronger OMP path selection; the baseline is given the true path count P, mine is not; its coded-feedback variant was not run), every variant stays above FER 1e-2 at 8 dB. B crosses at 5.1–6.3 dB, so the gain is a censored lower bound of ≥ 1.75–2.88 dB. The baseline was designed for small integer grids, so this shows a regime mismatch, not that it is poor in its own regime |
| vs embedded-pilot (EP) AFDM | Analytical: EP is infeasible in the main channel (guard 2Q+1 = 1029 > N). In a constructed short-delay variant, at equal energy per frame, B at ρ .3 gives ~33% more goodput from 5 dB up; at ρ .5 EP is better below 6 dB (MIXED). The grid starts at 4.5 dB, where EP is already at its goodput cap, so EP's low-SNR advantage region is unresolved. The EP estimator is my implementation, not published code |
| channel MSE vs constrained MCRB (genie delays, P known) | B is 4.9–11.5 dB above the bound at every point; NMSE floor ≈ −16 dB (ρ .3) / −20 dB (ρ .5). The bound covers only locally unbiased estimators and has no term for delay detection |
| where the residual gap sits | The true delay set removes 73–81% of the NMSE gap. With true delays the refit is within ~3 dB of the MCRB at ρ .5 but stays 4.5–5.3 dB above it at ρ .3. *(post hoc)* With true delays plus the same CSTATE branch, the FER gap to true H vanishes at ρ .5 and is 0.12–0.20 dB at ρ .3 |
| not paired, not pre-registered | A Luo-style data-aided SBL (Section 3) on the same generator but different frames crosses FER 1e-2 at 7.0–10.4 dB (best variant 7.0–8.2 dB at ρ .3, ~7.6 dB at ρ .5), versus 5.1–6.3 dB for B |

### Claim B — mechanism of CSTATE and the role of Γ

- **Factorial ablation** (16,379 F0-failed units, 4.5–8 dB). CSTATE rescues .302, one more F0 round .160, a detector rerun
  .142. Support swaps carry ~89% of the geometry gain; gain refit ≈ 0. Rescue rates are conditional on F0 failure and do not
  translate directly into FER; the set is dominated by low-SNR units where rescue is rare (.25 at 4.5 dB, .96–1.00 at
  6.5–8 dB). Removing the off-diagonal part of Γ removes more than the whole swap gain (share 1.18). **The frozen verdict was
  MIXED, not a clean pass:** swaps scored with scalar Γ are *harmful* at 4.5–6 dB (worse than no swaps at all), which the
  rule had assumed would not happen.
- *(post hoc, then tested)* Under scalar Γ, the swap search inserts near-duplicate atoms on already-occupied true delays
  (94% of units vs 1.3% with full Γ).
- **Guard test** (fresh frames). Banning co-delay atoms makes scalar Γ exactly match full Γ (recovery 1.002), so on channels
  without true co-delay paths the whole Γ effect is phantom suppression. On same-delay cluster channels the same ban
  collapses rescue from .126 to .016 while full Γ keeps it. A theorem-derived near-duplicate ban (|D_N| threshold) ties on
  clusters but loses .033 on the main family, because scalar Γ also accepts harmful co-delay atoms with |D_N| < .5, which the
  theorem does not predict. Only full Γ is best or tied-best in both channel classes.
- **Prospective replication** *(draft)* on fresh frames: full-Γ swap decisions beat scalar ones by +.18 rescue.

## 3. Known weaknesses

1. **The Γ result reverses in another estimator class** *(mostly draft)*. In a Luo-style data-aided EM-SBL (on-grid,
   simplified from Luo's off-grid D-GESBL; my detector and decoder), scalar Γ creates the same co-delay atoms but decodes
   *better*: FER .110 vs .149 (full Γ); with continuous Doppler refinement .028 vs .164. Full Γ is no better than Luo's
   hard-decision version. Follow-up tests:
   - Adding an isotropic ridge Σv·I to full Γ recovers 92% of the gap.
   - Replacing the APP variances by the realised per-symbol error energy (an oracle error profile) makes full Γ worse,
     not better.
   - The reversal persists (+1.37 dB NMSE) when the data are drawn from the decoder posterior, i.e. when the full-Γ
     model is exactly correct. Decoder APP variances are miscalibrated (realised error energy ≈ 2.15× APP variance), but
     these two results argue against miscalibration as the explanation.
   - A "full Γ for decisions, isotropic for gain estimation" split was refuted prospectively: on fixed atoms, isotropic
     gains are worse than full-Γ gains, in both receiver families.
   - The scalar-SBL advantage is therefore unexplained; it disappears once atoms are fixed, so it seems to sit in the joint
     SBL atom-selection dynamics. The claim "full Γ is the right model" currently holds only for fixed-cardinality swap
     search.
2. **Method novelty is thin.** Decoder-aided support re-acquisition exists for SP-OTFS/AFDM; the contribution is the
   mechanism and the covariance used in the discrete decision.
3. **Scope.** One N, QPSK, one LDPC code, SISO, known σ², one 8-path law with truncated delays, no large-scale fading,
   two Doppler laws. Gains at ρ .5 are ≈ 0.5 dB.
4. **Clustered channels are not solved.** On same-delay cluster channels F0 FER is .89–.99 and CSTATE rescues 12.6% of
   failed frames; the 8-slot, one-Doppler-per-path model bounds every variant.
5. **The remaining gap is in the pilot front end** (missed weak-path delays under superimposed-data interference). The
   paper diagnoses this but does not fix it. Pilot-only information sits 5.9–10.6 dB above the MCRB.
6. **Baselines.** The only published SP-AFDM JCED baseline is a port of a paper that did not reproduce; Kanazawa and Luo
   were not reproduced faithfully.

## 4. Prior art I already know (try to find more, and tell me if I mis-position any of these)

- Errors-in-variables sparse regression with dictionary error covariance: corrected Lasso (Loh–Wainwright, AoS 2012), MU
  selector (Rosenbaum–Tsybakov, AoS 2010), weighted/structured S-TLS (Zhu–Leus–Giannakis, IEEE TSP 2011). Chen–Caramanis
  (arXiv:1206.0823): with independent errors, support recovery needs no noise statistics.
- Duplicate neighbouring atoms under unmodelled perturbation / off-grid: S-TLS DoA experiments; Duval–Peyré (Inverse
  Problems 2017); band exclusion (Fannjiang–Liao, SIAM J. Imaging Sci. 2012).
- Fractional Doppler represented by several adjacent same-delay atoms as a *normal* feature: DA-OMP (arXiv:2412.01498),
  Yin et al. (IEEE TWC 2024). A reviewer may use these to argue that same-delay multi-atom fits are expected, not phantoms.
- AFDM model-order-adaptive estimation with neighbourhood exclusion and correlated-atom false-alarm correction
  (Wang et al., arXiv:2610.09970; pilot-only, white noise, no data uncertainty).
- SP-OTFS/AFDM data-aided receivers: Mishra et al. (IEEE TWC 2021, arXiv:2010.15066), Zheng et al. (IEEE TVT 2024,
  arXiv:2404.10232), Kanazawa et al. (arXiv:2501.15935), Luo et al. (arXiv:2607.18881), Zheng et al. (GLOBECOM 2025).
  Kanazawa and Zheng report detecting non-existent paths and attribute it to interference exceeding the threshold.
- Gaps in my search: IEEE pay-walled full texts not read (e.g. Prasad TSP 2014 J-SBL; Yuan WCL 2021; Yin TWC 2024);
  little free-text search on soft-decision channel estimation and on Dirichlet-kernel same-delay coherence.

## 5. Directions already tested and stopped

Listed so you do not spend effort re-deriving them. If you think one of them was stopped for a design-specific reason and
deserves another form, say so and explain why.

- A load-cliff / mutual-information "first-round law" as a design criterion: it predicts the cliff for 1–4 rounds but did
  not yield a transferable design rule. Information-theoretic upper/lower bounds on the cliff were too loose at these SNRs.
- Online scheduling / early-abandon controllers; directed soft-feedback correction; inner-loop acceleration (Anderson
  mixing, adaptive damping).
- Data-dependent superimposed training (DDST) at this rank: shifted the cliff the wrong way.
- Whitened (ridge-GLS) refit statistics: help MSE only in the noise-limited regime.
- Learned / deep-unfolded receivers belong to a separate paper and are out of scope here.

## 6. What I want from you

1. **Contribution verdict.** Judging from the literature you find, is this TCOM-level? Which of Claims A and B is the
   stronger core, and which parts would you cut or demote?
2. **Adversarial prior-art scan** (2019–2026, emphasis 2024–2026, IEEE Xplore and arXiv). Look for work that already does
   or implies any of the following:
   - non-white decoder-induced data uncertainty or soft-symbol covariance in a delay–Doppler (or chirp/OCDM) dictionary;
   - spurious same-delay or duplicate paths caused by data uncertainty;
   - fixed-cardinality support exchange or swap scoring with soft data.
   For each hit, state the overlap and what distinction, if any, remains.
3. **Improvement ideas.** Give 5–8 ideas from your own reading of the evidence and the literature. They may change the
   receiver, the theory, the experiments, the channel class or the paper's framing. For each: the idea; why it would raise
   the contribution; the closest prior work; the smallest experiment or derivation that tests it; cost; failure risk.
   Rank them.
4. **Reviewer attacks.** The five strongest objections a TCOM reviewer would raise against Claims A and B, and what
   evidence would answer each one.
5. **Framing.** Which framing of the paper would you choose given the literature? Argue for it and against at least one
   alternative.

Cite every source with title, authors, venue/year and DOI or arXiv ID, and mark which statements you checked in the full
text and which you inferred from abstracts.
