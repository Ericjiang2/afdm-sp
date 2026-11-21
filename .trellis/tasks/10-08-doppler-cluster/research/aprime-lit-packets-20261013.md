# A' evidence packets (2026-10-13)

**PARTIAL — extraction stopped by main session; main session (Opus) will do extraction.**

Scope: facts + locations only, no novelty verdicts. Quotes are verbatim from pdftotext of the arXiv PDF unless marked. Section/eq numbers as printed in the PDF. Full text read = arXiv PDF downloaded and grepped/read in this run.

Reached: F4-01, F3-01, F2-02, F5-01, F4-03, F4-04 (full text); F2-01 (abstract-level only, via search-tool summary + Crossref/Semantic Scholar metadata).
NOT reached (stopped): F3-04, F3-06, F5-04, F2-03, F1-08, F1-06.

---

## F4-01 Kanazawa et al., "Superimposed Pilot-Based OTFS: Will It Work?" — arXiv 2501.15935v3 (24 Feb 2026), IEEE TVT DOI 10.1109/TVT.2025.3608199
Coverage: FULL TEXT (arXiv v3 PDF, 7 pp double-column).

- **System & loop** (Sec. V intro; Sec. IV-C, Algorithm 1, Fig. 3): LDPC-coded SP-OTFS, QPSK, rc = 0.75, N = M = 15, P = 4 paths, fc = 4 GHz, doubly-selective, 5G LDPC via Sionna. One loop: channel estimation -> pilot cancellation -> MP detection -> (coded iterations only) LDPC decoder -> LLR->logits->PMF->symbol replica -> data cancellation -> back to channel estimation. Channel estimation IS inside the loop. Nested inner iterations exist but are fixed parameters: MP detector iterations I_MP and BP iterations I_LDPC (Sec. IV-B "requires the number of iterations ILDPC as an input parameter"; Sec. IV-D, Table I).
- **What is adapted / granularity** (Sec. IV-C, text after Fig. 3; Algorithm 1 line 6): static switch between "uncoded iteration" (MP only, no decoder) and "coded iteration" (MP + LDPC decoder + replica). Quote: "The total number of iterations is given by rend = runc. + rcod. and is a stopping criteria for the iterative algorithm." Parameters r_unc, r_cod, r_end are global design constants, not per-frame. Contribution 2 (Sec. I): "we can alleviate the increased complexity by switching two iterative processes: uncoded and coded iterations."
- **Decision signal:** none per frame. Algorithm 1 line 17: "until A stopping criteria is satisfied" with the criterion defined as r = r_end (Fig. 3 box "r = rend"). Sec. V-C: "Based on these results, a stopping criteria is set to rend = 4 in following simulations." (Fig. 4 uses r_end = 5.) No syndrome/CRC use found in text (grep for syndrome: no hit).
- **Predictor/rule type:** fixed parameters chosen by simulation (Sec. V-C, Figs. 4-6: NMSE vs r for 0 <= r_unc <= 4; "r_unc = 0 is the best parameter setting in terms of the channel estimation accuracy").
- **Reliability control:** not stated. Metric is effective throughput (1-BLER)·Nd·rc·log2 L / NM (Eq. 34); BER, NMSE also reported.
- **Baselines / saving:** EP-based and single-SP schemes; complexity as real multiplications (Table I, Fig. 6). Quote (Sec. V-C): "The coded iteration requires" more operations (sentence continues across page break); Sec. I: "impact on the increased computational complexity is negligible compared to the conventional scheme". No per-frame saving reported.
- **Explicit future-work statement (Sec. VI, last paragraph before Acknowledgment):** "an adaptive stopping criterion can be developed to select these parameters dynamically. For example, early termination based on LLR variance or residual interference power could enable the receiver to allocate computational effort only when justified by the channel conditions or SNR level." Also: "A key advantage of the proposed system is its support for a tunable complexity-performance trade-off via the iteration parameters".

## F3-01 Strodthoff, Goktepe, Schierl, Hellge, Samek — arXiv 1807.10495v2 (25 Oct 2019), IEEE JSAC 37(11):2573-2587
Coverage: FULL TEXT (arXiv v2 PDF).

- **System & loop** (Sec. II, Table II): single-link LDPC-coded OFDM (3GPP, 1.4 MHz, TDL-C, MMSE equalizer), 360-bit transport block, rate-1/5 LDPC BG2 Z=36, min-sum, 50 decoding iterations, QPSK. No channel estimation or detection in the predicted loop; the object is the LDPC decoder's partial progress on a subcode (fraction 1/2 to 5/6 of the codeword, Sec. II "subTTI").
- **What is adapted** (Sec. I-II): the HARQ feedback (ACK/NACK) is issued early from a prediction of decoding outcome; consequence = earlier retransmission (HARQ RTT reduction, Fig. 1). Granularity: per codeword/transmission. Quote (Sec. II): "Providing early feedback (E-HARQ) implies decoupling the feedback generation from the decoding process, which introduces a misprediction probability".
- **Decision signals** (Sec. III-A, Eqs. 6-9): per-iteration Variable Node Reliability VNR_j = (1/M) Σ 1/(1+|Λ_i^(j)|) from a-posteriori LLRs of the subcode after BP iteration j; classifiers use first six values VNR_0..VNR_5 (Sec. III-B); optional history features (VNR_HIST, EUCD_HIST).
- **Predictor type** (Sec. III-B): hard threshold HT0/HT5 (prior art), logistic regression, random forest, isolation forest, supervised autoencoder (SAE). Threshold handling (Sec. III): "readjusting the decision boundary of any trained model that outputs probabilities" (threshold moving), evaluated on FNR-FPR curves (Fig. 3).
- **Reliability control** (Sec. II-A Eq. 1; II-C Eq. 4): target effective BLER 1e-5. Quote: "(1) only depends on the baseline BLERs Pe and Pe∧e0 and the classifier's false negative rate Pfn with leading order contribution given by Pfn · Pe." False negative rate is the working-point variable; Sec. II-C: FNR/FPR trade-off, finite-resource optimum ("there is an optimal operation point"); Sec. IV-C fixes FNR_eval = 8e-4 for medium-load evaluation. Reliability loss is handled via extra (re)transmissions on false positives, consuming resources.
- **Baselines / results:** regular HARQ and HT0/HT5 (Sec. IV). Sec. IV-C: effective BLERs ~1e-5 attainable (infinite resources); E-HARQ allows up to two retransmissions where regular HARQ allows one within the latency budget (Sec. II-B); decreasing subcode 5/6 -> 1/2 at 1e-5 needs "an increase of 40% and 45% in retransmissions at SNR 4 dB and 3 dB". SAE and LR best in high-load regime.

## F2-02 Haddad, Baghdadi, Jezequel — arXiv 1203.5037v1 (22 Mar 2012), "On the Convergence Speed of Turbo Demodulation with Turbo Decoding" (draft headed IEEE Trans. Signal Process.)
Coverage: FULL TEXT (arXiv v1 PDF).

- **System & loop** (Sec. II-A, Fig. 1): TBICM-ID-SSD, 1 Tx/1 Rx, Rayleigh fast fading with/without erasure, "assuming perfect synchronization"; two-level iteration: SISO demapper <-> turbo decoder (turbo decoder has its own internal iterations). No channel estimation in the loop (CSI knowledge assumption not located in text read: unverified).
- **What is adapted** (Sec. III, IV): number of demapping iterations vs turbo decoding iterations per demapping iteration; static schedule. Quote (Sec. IV): "to keep the same number of iterations for the decoder unaltered, one turbo code iteration is added after the last iteration to the demapper for each eliminated demapping iteration." Notation 6IDem, 5IDem 1EIDec, 4IDem 2EIDec. Granularity: global, offline; not per frame.
- **Decision signal:** EXIT charts (Sec. III, Eq. 14, Fig. 2), asymptotic, averaged over frames. Quote (Sec. IV): "EXIT charts are based on average calculations as many frames are simulated."
- **Rule type:** fixed schedule derived offline from EXIT analysis plus BER simulation (Fig. 3, Table I). Optimal profile: "execute only one turbo decoding iteration for each demapping iteration" (Sec. III).
- **Reliability control:** no error-rate constraint; reports loss in dB. Abstract: "reducing two demapping iterations with reasonable performance loss of less than 0.15 dB". Table I: loss 0.02-0.15 dB across modulation/rate/erasure.
- **Saving:** Sec. VII: arithmetic operations reduced "from 8.2% for QPSK configuration to N2it % [as printed; garbled, likely 2/Nit] for QAM256 (e.g. for Nit = 6 this gives a reduction of 33.3%)".
- **Relevant remark** (Sec. VI end): "applying the proposed scheduling combined with an early stopping criteria might diminish the benefit from the scheduling, but at the cost of an additional complexity."

## F5-01 Hu, Shi, Cai, Yu — arXiv 2201.08477v3 (19 Apr 2023), DDPG-driven deep-unfolding with adaptive depth for SBL channel estimation
Coverage: FULL TEXT (arXiv v3 PDF). Venue unverified (not read from PDF).

- **System & loop** (Secs. III-IV): massive-MIMO off-grid sparse channel estimation; SBL algorithm unfolded into layers. No detection, no decoder, no coded frames. What iterates = unfolded SBL layers (one loop).
- **What is adapted** (Sec. II-C, V-B): number of layers (depth) per input sample. Quote (Sec. I): "the optimal number of layers required for convergence changes with different inputs."
- **Decision signal** (Sec. V-B1, Eqs. 35-36): halting score L_t = σ(p1‖Q(y − Xĥ_t)‖² + p2), a function of the measurement residual (proxy for the unknown reconstruction error); Eq. 36 generalizes to an r-layer DNN on the residual.
- **Rule** (Eq. 39): "Ts = min{t : Lt ≤ ε}", ε pre-determined constant. Training cost Eq. 37 L(θ) = Σ_t ‖h − ĥ_t‖²/L_t + ρL_t with optimum L_t = ‖h − ĥ_t‖/√ρ (Eq. 38); DDPG learns trainable parameters (state/action/reward Sec. II-C, V-A).
- **Threshold choice** (Sec. VI-A): "we tune the hyper-parameter ǫ in (39) to ensure that the averaged number of layers of the whole dataset in DDPG Unfolding/Adaptive is the same as that of the Unfolding/Fixed."
- **Reliability control:** no target error-rate/false-alarm constraint; Sec. V-B2: ε and ρ tune "the channel reconstruction error and the number of layers".
- **Baseline / saving** (Sec. VI-B, Figs. 12-13): fixed-depth unfolding; quote: "achieves nearly the same performance as the Unfolding/Fixed with 25% fewer number of layers" (L = 6 vs L = 8 in NMSE).

## F4-03 Huang, Guo, Zhang, Zakharov — arXiv 2309.08177 (message-passing joint CE and detection for SP-OTFS)
Coverage: FULL TEXT (arXiv PDF), only iteration-setting checked per task. Not a coded system: no LDPC/decoder hits in grep; metrics BER and NMSE.

- **How iteration number is set:** fixed. Sec. V-A (Convergence Analysis): "Fig. 4(b) shows that the receiver converges when the number of iterations exceeds 70. So we choose 0.8 for the damping factor and 70 as the number of iterations." (max 100 in that experiment).
- **Stopping rule:** Algorithm 1 (Sec. III-C) line 17 reads "until terminated"; no criterion defined in the text (the only "terminated" hit is that line).
- **Stage schedule:** Sec. V intro: BEM order Q = 5 in first iteration, Q = 9 after one iteration ("a lower BEM order is used to reduce unknown parameters of the channel in first iteration, and in subsequent iterations, the BEM order is increased").
- **Complexity:** per-iteration O(QMN log(MN)) (Sec. V-B); runtime comparison with I_DD = 60, I_MP = 100 etc. (Sec. V-D, Table VI: SP-DD 0.34 s vs SP-BEM-MP 28.95 s at 125 km/h).

## F4-04 Zheng, Wen, Mao, Xiao, Wang — arXiv 2404.10232 (AFDM with superimposed pilots, 4-page letter)
Coverage: FULL TEXT (arXiv PDF), iteration-setting only. Uncoded (BER; no decoder).

- **Loop** (Sec. III-D "Iterative Channel Estimation and Data Detection"): CSI estimated by LMMSE-type Eq. 24 from y − H_eff^i x_d^i; threshold γ on the estimate gives path indicator; data re-detected by MP with y_d = y − H_eff x_p. Channel estimation inside the loop.
- **How iteration number is set:** fixed per experiment, swept. Sec. IV: "We consider the different numbers of iterations and superimposed pilots." Fig. 3 "based on the MP detector with 2 iterations". Quote: "the MSE performance is improved as the number of iterations increases." No stopping rule found.

## F2-01 Lee & Yang, "Scheduling for an Adaptive Number of Iterations in Turbo Equalizers Combined with LDPC Decoders" — IEEE TCOM 58(10):2759-2764, Oct 2010, DOI 10.1109/TCOMM.2010.082710.090533
Coverage: ABSTRACT ONLY, and only second-hand: IEEE page unreadable; full text CLOSED (Semantic Scholar openAccessPdf status CLOSED, abstract elided). Authors confirmed by Crossref: Myung-Kyu Lee, Kyeongcheol Yang (DBLP key journals/tcom/LeeY10). POSTECH OASIS records exist (handles 2014.oak/25500 and 2014.oak/1222) but the pages returned "Loading..." and were not read.

- Abstract-level content below is a PARAPHRASE returned by the WebSearch tool summary of the POSTECH abstract, NOT verified verbatim: proposes "adaptive scheduling" to reduce complexity of a turbo equalizer combined with an LDPC decoder; analyzes convergence behavior of the combined system; derives "simple metrics and criteria" for monitoring the status of iterative processing; decides whether another equalization pass is worth running; reports lower complexity than conventional schedulings at almost the same error rate.
- All other fields (loop structure, signal, threshold selection, reliability control, numeric savings): not found in any source read.

---

## Not reached
F3-04 (Kusi & Kim TWC 2026), F3-06 (Kusi ICTC 2023), F5-04 (Samsung WCNC 2021), F2-03 (Haddad EURASIP 2012), F1-08 (Shepherd 2006), F1-06 (Shin 2008): not read in this run.
