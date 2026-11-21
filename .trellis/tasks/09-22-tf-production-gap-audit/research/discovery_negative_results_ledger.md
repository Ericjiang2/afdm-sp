# Prior hypotheses and negative evidence

This ledger is a map of tests already run, not a list of method recommendations. Counts below come from distinct development, selected-frame, toy, and fresh-prospective protocols. They must not be pooled into one FER estimate. The source manifest in the final pack binds every cited file by SHA-256.

## More ordinary TF work

- **Hypothesis / motivation:** Existing TF errors mostly need more iterations or native rounds.
- **Test:** On the earlier 6.5 dB cohort's first 32 TF failures, compare frozen replay with J40R2 and J20R3.
- **Result / status:** J40R2 rescued 3/32, J20R3 8/32; union 9/32, leaving 23/32 under both finite budgets. All baseline erroneous hard vectors had nonzero syndrome. Limited-budget explanation weakened; no observed legal wrong-codeword basin.
- **Source:** `results/tf_production_gap_audit_20260922/RESULTS.md`.
- **Does not prove:** Arbitrarily longer runs or other schedules fail; no convergence or infinite-budget claim.

## Passive whitening / whitened GCV

- **Hypothesis / motivation:** Treating residual fractional-Doppler leakage as approximately white could improve acquisition or coding.
- **Test:** Earlier cached 32-block whitened-GCV screens, including W_D_ALL versus S_ALL and D_P_HALF; separate response-error analysis.
- **Result / status:** At 8 dB W_D_ALL reduced A0's 6 errors to 4, matching S_ALL and D_P_HALF in count but not error identities; at 7 dB the whitening arm still had 25/32 errors. W_D_ALL and S_ALL both had four 8 dB errors, while measured terminal cost was about 2.7 s versus 0.16 s. No distinct production arm named “passive whitening” was found. Direction unresolved/weak, not a validated production rescue.
- **Source:** `.trellis/tasks/09-13-trans-next/research/e1a-whitened-gcv-v1-results.md`; `.trellis/tasks/09-13-trans-next/research/whitened-response-errors-v1-results.md`.
- **Does not prove:** All whitening formulations fail, or fractional-Doppler tails can never be approximated usefully. A mathematical nonwhite-tail counterexample is not a production receiver test.

## Propagated scalar gain variance

- **Hypothesis / motivation:** Scalar uncertainty propagation in the TF gain channel drives the error gap.
- **Test:** TF_POINT20_R2 suppresses propagated scalar gain variance while retaining the declared mean-update structure; small direction controls and Part-A cells.
- **Result / status:** The 24 direction controls had the same frame-error counts. At 6/6.5/7 dB, TF versus POINT errors were 2/3, 1/1, 0/0; POINT→TF rescued one 6 dB frame with no reverse harm in that comparison. No independent reliability advantage established for this scalar change.
- **Source:** `results/sp_afdm_pd1q_part_a_20260921/RESULTS.md`, `master_equation_reconciliation.md`, `mechanism_definitions.md` in that result tree.
- **Does not prove:** Bitwise equivalence, calibration of scalar variance, or that richer posterior covariance is useless.

## Wider local Doppler refinement

- **Hypothesis / motivation:** The frozen local Doppler window alone blocks recovery.
- **Test:** Earlier selected 32 failures, truth-data-aided fit on fixed acquired delay support and path count, original window versus full `[-3,3]` Doppler window, then remove truth input before TF decoding.
- **Result / status:** Both windows rescued the same 20/32; wider range added zero rescues despite some lower fit errors. Window-only explanation weakened for this oracle-assisted intervention.
- **Source:** `results/tf_production_gap_audit_20260922/RESULTS.md`.
- **Does not prove:** A deployable observed-only wider search would have no effect, or that all failures stem from missing delay support.

## Conditional, profile, and marginal codeword ranking

- **Hypothesis / motivation:** Candidate-specific gain refit or marginalization might reverse the baseline word versus true-word preference.
- **Test:** On the same 32 selected failures, compare the known true word against the legal re-encoding of baseline-decoded information bits under working, widened, and true geometry.
- **Result / status:** In working geometry, conditional, unregularized profile, and Gaussian-gain marginal scores already preferred truth in 32/32; conditional→profile/marginal preference reversals were 0/32. Refit produced large true-word margins but did not create the preference. Hypothesized pairwise reversal is absent in this comparison.
- **Source:** `results/tf_production_gap_audit_20260922/RESULTS.md`, especially C witness metrics and independent verification.
- **Does not prove:** The decoder can generate the true word, that it is global MAP, or that a ranking score would rescue operational frames. The raw invalid hard vector is not the legal baseline candidate.

## Curvature and escape

- **Hypothesis / motivation:** Errors may be escape-capable negative-curvature fixed points or stable wrong basins missed by local updates.
- **Test:** N=8 enumerated-codeword toy curvature and an N=64 constructed two-codeword EM/marginal witness with a phase-diffusion negative control.
- **Result / status:** Thirty initial states had negative curvature but only one final state did; among 119 toy errors, one had negative final curvature. The constructed N=64 witness trapped EM in a positive-curvature wrong basin while exact gain-marginal MAP selected truth; the negative control escaped. Toy evidence separates mechanisms but no production-TF curvature/escape experiment exists.
- **Source:** `results/tf_production_gap_audit_20260922/inputs/TF_research_investigation_20260922.zip` (`README.md`, `results.json`, `basin_results.json`).
- **Does not prove:** Production TF errors occupy those basins, or curvature correction improves coded SP-AFDM FER.

## Non-Gaussian leakage and mixture probes

- **Hypothesis / motivation:** Fractional-Doppler leakage's non-Gaussian structure may be the missing inference ingredient.
- **Test:** N=64, one half-bin AFDM path probe; inspect fourth cumulant and exact known-channel inverse transformation.
- **Result / status:** Normalized fourth cumulant was −0.333496, while known gain/geometry inversion recovered QPSK plus Gaussian noise with maximum error about `2.59e-14`. Non-Gaussian raw leakage alone does not identify the coded production gap. No mixture receiver performance test was found.
- **Source:** Same `TF_research_investigation_20260922.zip`.
- **Does not prove:** A mixture or non-Gaussian approximation cannot help with unknown geometry/gain, or that production residuals are Gaussian.

## Code-correlation approximations

- **Hypothesis / motivation:** Symbolwise marginals may miss coded correlations relevant to gain integration.
- **Test:** Small N=12 synthetic linear-code enumeration and a pair of codeword distributions sharing per-symbol marginals.
- **Result / status:** Full collapsed code/gain Bayes factor versus an incomplete baseline rescued/harmed 33/2 at noise variance 0.3 and 22/13 at 0.6; behavior was not monotone. Identical symbol marginals coexisted with projection variances 2 versus 0. Correlation omission is a real mathematical distinction, not a validated production improvement.
- **Source:** `experiments/tf_geometry_reopen_20260922/reference/README.md`.
- **Does not prove:** The production LDPC receiver would achieve the toy gains, or that a practical approximation is affordable.

## Richer gain covariance and tangent relinearization

- **Hypothesis / motivation:** Full gain uncertainty or local relinearization may repair scalar-model failures.
- **Test:** Native-joint small screens with vector variance, off-diagonal self-feedback, P×P gain posterior covariance, dynamic and frozen tangent relinearization.
- **Result / status:** Added complexity/cost yielded no decisive frame advantage in those screens. Dynamic relinearization harmed some frames; frozen relinearization removed part of that harm but added no rescues in the cited control. Development evidence only.
- **Source:** `experiments/sp_afdm_native_joint_20260921/docs/RESEARCH_VERDICT.md`, `results/tangent_screen.json`, `results/tangent_fixed_screen.json` in that experiment tree.
- **Does not prove:** All covariance or tangent methods fail on production data.

## Structural geometry reopening and its cost

- **Hypothesis / motivation:** Search over same-delay path structure can recover states missed by local-only refinement, but full search may exceed latency gate.
- **Test:** Earlier selected 43 nonzero-syndrome frames, LOCAL20 versus GLOBAL20; 32 zero-syndrome success controls. Then exact-output CSTATE compact realization on the same 75 observations.
- **Result / status:** LOCAL rescued 10/43, GLOBAL 31/43, including 15 of 23 failures not rescued by longer ordinary TF. Controls had no harm. GLOBAL complete branch mean 0.718 s exceeded the old 0.6 s branch gate. CSTATE matched GLOBAL geometry/top-20/final decisions exactly while its branch mean/p95/max were 0.241/0.279/0.292 s. The old 75 observations are reused development evidence, not fresh FER observations.
- **Source:** `results/tf_geometry_reopen_20260922/RESULTS.md`; `results/tf_cstate_validation_20260922/RESULTS.md`.
- **Does not prove:** A new posterior principle, population effect, or universal latency passage. Fresh prospective outcomes are a separate sealed campaign.

## Oracle geometry / full H boundary

- **Hypothesis / motivation:** Quantify how much of the selected TF gap disappears when physical representation is supplied.
- **Test:** Earlier first 32 failures at 6.5 dB under true geometry with estimated gains, full true H with TF20R2, and full true H with EP8R2.
- **Result / status:** Rescues 27/32, 28/32, and 26/32 respectively; full H added one paired rescue beyond true geometry. Strong diagnostic headroom, all oracle conditions.
- **Source:** `results/tf_production_gap_audit_20260922/RESULTS.md`.
- **Does not prove:** Information-theoretic error floor, deployability, or a clean causal partition of geometry, gain, and inference error.

## Fresh confirmation (separate population)

The fresh 2026-09-23 prospective population has 1,024 new frames at each of 6, 6.5, and 7 dB. TF versus frozen TF+CSTATE produced 145/0, 34/0, and 15/0 rescue/harm pairs; 72 triggered failures remained across cells. Only 6.5 dB was prespecified confirmatory. Original unattended analysis remains `invalid` because a receipt-schema check failed before truth access; user-authorized offline recovery and original independent verifier passed on the same sealed data without receiver reruns. This fresh sample cannot be pooled with the outcome-selected older cohorts or toy probes.

Source: `results/tf_cstate_prospective_20260923/FINAL_CSTATE_REPORT.md`, `recovery_20260923/analysis/receipt.json`, `recovery_20260923/verification/receipt.json`.

## 2026-10-19 additions

### Raise the CSTATE edit budget to recover weak paths
- **Hypothesis / motivation:** Gemini reports 1 and 2 suggested more swaps inside CSTATE to recover delays missed at the pilot stage.
- **Test:** Pilot 3 (exploratory). On the pilot-2 keys (ρ .3, 4.5–5.5 dB, frames 7800–7999, caps 8 and 12), max_edits 2 → 4, paired by unit.
- **Result / status:** Full-Γ rescue +.011 at cap 8 and −.003 at cap 12. Direction not pursued.
- **Source:** `experiments/slot_mismatch_20261019/POSTHOC_CHECKS.md` (pilot 3).
- **Does not prove:** Other recovery routes fail (for example a wider pilot-stage nomination; extra F0 slots did keep weak true delays).

### Scalar-Γ penalty is pure slot displacement
- **Hypothesis / motivation:** A phantom hurts only because it pushes a true path out of a fixed 8-slot budget.
- **Test:** Pilots 2–3 (exploratory): caps 8 vs 12; edits 2 vs 4; zero-simulation replay of E-2 R edits.
- **Result / status:** On the 293 keys triggered at both caps, D₁₂/D₈ = .90. With edits doubled, D₄/D₂ = 1.00 [.95, 1.05]. Phantoms replacing only spurious slots still harm (.044 vs A5). Weakened.
- **Source:** same file, checks 1–3 and pilots 2–3.
- **Does not prove:** ρ .5 or other channel laws; the result is exploratory and not frozen.

### Swap-score rank-inversion condition (Gemini report 2, §3.3)
- **Test:** Frozen post hoc check on E-2 family R rows, with an independent recount.
- **Result / status:** PARTIAL. The power ratio predicts phantom acceptance, but the formula's ρ factor has the wrong sign and there is no |D|² scaling.
- **Source:** `experiments/posthoc_rank_inversion_20261019/SUMMARY.md` (with its correction note).
- **Does not prove:** Any decision-level theory fails; only this formula.

### SBL reversal as "full Γ prematurely prunes companion atoms" (Gemini reports 1 and 2)
- **Test:** No run. Compared against the saved E-3 census.
- **Result / status:** Contradicted.
  - Co-delay pairs: L-cov 5.11 vs true-data SBL 5.50.
  - Mean atoms: L-cov 19.5 vs true-data SBL 13.9.
  - Full Γ does not prune below the true-data fit.
- **Source:** `experiments/tf_e3_sbl_20261017/out/analysis/e3_summary.md`.
- **Does not prove:** What does explain the reversal. That remains open; see the detector gain-re-estimation lead in STATE.

### Heteroscedastic weighted kernel for same-delay coupling (Gemini report 1)
- **Result / status:** Refuted analytically. For any AF-diagonal V, the same-delay Γ equals Σv·D_N(Δν).
- **Source:** `results/cstate_method_closure_20260928/MANUSCRIPT_THEOREM_TEXT.md` (AFDM/CPP corollary).

## 2026-11-09 addition

### Fixed-H OAMP/LDPC continuation on the archived 6.5 dB cohort

**Correction after the user questioned the comparison.** The entry below records a two-call screen only. Same-adapter continuation to20 rounds recovers15 frames versus9 at round2, and24 frames still change hard decisions at round20. An exact cyclic-band linear solve on one real frame is5.36× faster than dense setup+update. The old screen does not justify eliminating OAMP or assigning its dense implementation cost to the entire algorithm family. Full diagnostic details are in the linked report.

The bounded screen failed its frozen continuation criterion. Among all 40 archived native-syndrome triggers, two new OAMP/LDPC calls recover 9 frames versus 14 for matched fixed-gain TF/LDPC, and 34 for archived CSTATE. OAMP versus fixed TF has one rescue and six harms. The dense OAMP adapter has median complete continuation time 0.629 s versus 0.086 s, including median setup 0.574 s. Raw saved-output recount passes. Applicability is limited to the untrained scalar adapter, fixed channel, two-call budget, and reused September population. [Scope and evidence](oamp-ldpc-screen-20261109.md).

## 2026-11-19 addition

### Identifiability gate predicts a placement flip in exchange at low ρ (refuted by a post hoc readout)

- **Idea (Claude, 11-19).** With unit total power per sample, the mean waveform energy is E = N − u, so the exchange-stage gate reads (N − 2u)·x < σ². For ρ < .5 a failed frame with u > N/2 would make the gate fire widely, and stage-specific placement ("no floor in exchange") would flip — possibly inside the ρ < .25 collapse of the ρ sweep.
- **Test.** Zero-cost readout of the archived ρ-sweep rows (62,400 keys, triggered frames only, all ρ ∈ {.15….50}, 3–8 dB): distribution of u/N.
- **Result / status.** Refuted. u/N never exceeded 0.31 (max 0.309 at ρ .5, 3 dB; at ρ .15 the median is 0.07–0.21); no triggered frame has u/N > 0.45. The gate therefore cannot fire through E − u → 0 in the tested range, and the collapse is not a placement flip. Not pursued.
- **Source.** Claude readout on deinlab, `experiments/rho_sweep_20261119/out/main_20261119/rows_shard*` (field `u`), recorded in [miao-assessment-claude-20261119.md](miao-assessment-claude-20261119.md).

### Grid fineness η as one knob that amplifies both opposite failures (not supported prospectively, 2026-11-20)

- **Idea.** Claude merged Astra ① and agy ③: a finer Doppler grid should make scalar scoring easier to fool in exchange and widen the exact-Γ deficit in SBL.
- **Test.** Frozen fresh-frame test `b6046c54`. Exchange: forced-miss units 56000–56999, competitor at .25 / .125 / .0625 bin. SBL: second-stage grid η ∈ {2, 4, 8}, frames 6800–6999, 6 dB.
- **Result / status.** Not supported.
  - Exchange: direction holds but is tiny (interaction +1.6 pp [0.7, 2.5] against a predicted 10 pp). |D_N| is already 0.90 at 0.25 bin, so the split reward is near saturation on the standard grid.
  - SBL: the frozen rule flags a reversal (G_B 33.8 / 56.5 / −2.3 pp). It is driven by the scalar R0's 0% convergence at η = 8 within the frozen 100 iterations; R1 stays at 64–70% across η.
  - Not pursued. A longer-EM replay at η = 8 is the cheapest open check.
- **Source.** [res-20261119-09](../../../../research-assets/res-20261119-09.md).

### Decision-directed σ² "minus → plus" sign flip (refuted at zero cost, 2026-11-20)

- **Idea.** agy (early answer after reading the handoff): the frozen `sigma2_dd` estimator subtracts hᴴΓ(v)h, which assumes symbol errors independent of noise. For posterior APP moments E‖y − Hμ‖² = Nσ² − E[hᴴΓh], so the EM-style plus sign should remove the DD bias and recover most of the +1.64 dB loss.
- **Test.** Zero-cost readout of saved rows: deinlab `experiments/sigma2_dd_20261118/out/main_20261118/rows_shard*.jsonl.gz`, fields `residual_power` and `uncertainty_power` (shard000 md5 matches `REMOTE_ROWS_MD5.txt`). Predictions written before looking: Claude, triggered plus-ratio median > 1.15 at most SNRs (P .65); agy, ~1.0–1.15.
- **Result / status.** Refuted as a one-sign fix.
  - On DD-triggered keys the plus estimate overshoots: σ̂²/σ² median 1.40 [p10 1.30] at 4.5 dB, 1.52 at 5.5 dB, 1.91 at 6.5 dB, 2.82 at 8.0 dB. Untriggered keys give 1.08–1.21 under either sign.
  - The minus rationale is wrong in principle (triggered residual/σ² median 0.73 at 4.5 dB, below the noise floor), but missed-path power or APP miscalibration dominates the other side; these rows cannot separate the two.
  - res-20261118-05's verdict and Eric's 11-19 σ² decision are unaffected. Not pursued.
- **Source.** [agy-early-routes-check-20261120.md](agy-early-routes-check-20261120.md) §2.

### Non-constant-modulus (16-QAM) decoder-interface line (closed for this paper, Eric 2026-11-20)

- **Idea.** Astra 11-19: for QPSK the soft means fix every variance, so "linear summaries needed to rebuild the co-delay block" (rank S_W) and "numbers the decoder must pass" coincide; 16-QAM separates them, so a same-mean, same-u redistribution of variance might flip a real support decision.
- **Assessment.** Claude, Astra and agy independently (16qam-line-* files): in frozen AFDM the co-delay block is u-only for any variance profile (Prop 1) and cross-delay terms are chirp-suppressed (≤ 0.82% of u on initial supports), so no could-fail prediction exists here. An in-memory OTFS flip exists (Astra) but OTFS co-delay leverage is small (≤ 2u/32 per entry; agy: 1/k₀ phase spread plus multipath row symmetry).
- **Result / status.** Closed for this paper by Eric; rank remark stays a remark; 16-QAM/OTFS is follow-up material. The nearby a₁ ∈ {0, 1, 5} chirp-transition test stays open as a candidate (not part of this closure).
- **Source.** [16qam-line-divergence-20261120.md](16qam-line-divergence-20261120.md).

### "Exact co-delay covariance is the paper's principle" main line (closed, Eric 2026-11-20)

- **Idea.** From 10-17 to 11-19 the TCOM framing credited the support-exchange rescue to the exact co-delay uncertainty block (`CODELAY`) and built the paper on it ("covariance-aware support acquisition", "unified mechanism", the 妙 search inside the current receiver).
- **Result / status.** Closed. Deleting Γ in the exchange is equivalent on P1 and FER-equivalent on genuine doublets (res-20261120-01/02/03); the guarded diagonal mistake is used by no published receiver (lit-diag-soft-variance-20261120); the receiver shell is known parts in a new combination (novelty-gemini-20261120). The paper now centres on "iterate or re-search after a decoding failure"; the covariance trap is one section. Do not reopen "exact block necessary" without a new architecture where Γ = 0 fails (it does fail in overcomplete SBL, res-20261018-03).
- **Related correction.** The dense-cluster route is not a large-headroom candidate: on the same 160 frames a wide-basis (DPSS) receiver is 0.59 dB from true H (`afdm_sp_joint_unrolled/outputs_dpss_paired_screen_20261111_v2/summary.json`); only "when per-path estimation is needed" remains open.
- **Source.** [retrospective-20261120/divergence.md](retrospective-20261120/divergence.md) and the files it links.

### Low-pilot missed-path line (two-week time box, stopped by stop condition 3, Eric 2026-11-20)

- **Idea.** At low pilot fraction the initial estimate misses paths; ask when decoder feedback recovers them, when more search cannot, and whether a receiver-visible quantity predicts it well enough to change pilot or compute allocation (task `11-20-low-pilot-missed-path`).
- **Test.** Zero-simulation readouts of saved edit-budget rows (fresh frames 6400–6799): residual missing true-path power after CD4, CD4→CD6 recovery, and a visible-feature probe (syndrome, entry geometry, CD2 trace) against cell-only and syndrome baselines.
- **Result / status.** At ρ = .15 (6–8 dB) CD4 failures still carry unmodelled weak paths (median 0.19σ²; successes 0) and CD6 recovers 0/19 of them, so more swaps on the same feedback do not help. At the operating point ρ = .30 failures carry almost none (median 0.012σ²); syndrome alone predicts failure there (within-cell AUC .81) and the other visible features add nothing (Δ upper bound .011). At ρ = .15 visible features reach ≤ .65 versus .83 for the true entry-missing power; the probe's primary contrast is inconclusive (Δ −.031 [−.144, .078]). Stopped: the phenomenon exists only at pilot fractions nobody would pick. The absorption-versus-noise-floor mechanism was not resolved (no residuals in saved rows).
- **Revival condition.** (i) A system setting where pilot overhead costs rate or ρ ≥ .30 is infeasible (e.g. multi-user pilot power limits, larger P), making ρ ≤ .20 an operating point; or (ii) iterate-versus-research data show a receiver-visible quantity that predicts residual weak paths (within-cell AUC ≥ .80).
- **Does not prove.** That residual- or soft-information-based quantities carry no extra information; that re-decoding before re-searching cannot recover the weak paths (never tested; all swaps reuse one F0 soft-symbol set).
- **Source.** [step1-readout-20261120.md](../../archive/2026-11/11-20-low-pilot-missed-path/research/step1-readout-20261120.md), [visible-probe-readout-20261120.md](../../archive/2026-11/11-20-low-pilot-missed-path/research/visible-probe-readout-20261120.md).

### "With decoder feedback, pilots only need to acquire" — pilot-acquisition scaling law (stopped, Eric 2026-11-21)

- **Idea.** External candidate (11-20): with decoding feedback, the pilot only has to make every decoding-relevant path detectable in round 0; the collapse point ρ* is set by a detection threshold and ρ*·N is roughly constant (up to ln M).
- **Test.** Frozen zero-receiver calculation (`experiments/pilot_acquisition_calc_20261120/`, rules `944f49e7`): exact first-round pilot matched filter on archived ρ-sweep truth with the real ZC pilot and AFDM chirp (model matches the generator to 1e-12).
- **Result / status.** R1 failed (no ρ reaches 1% acquisition failure, i.e. it predicts a collapse the receiver does not show), R2 failed (CD-failure risk ratio 1.16 [1.03, 1.32]), R3: ZC pilot sidelobes dominate weak-path detection (80%). A post hoc variant excluding DAFT-adjacent columns changed nothing. Stopped by the candidate's own kill rule.
- **Revival condition.** A pilot with near-ideal ambiguity (e.g. a single embedded pilot), or a measured F0 round-0 capture curve showing interference-limited rather than sidelobe-limited detection.
- **Does not prove.** That the real F0 front end (greedy least squares, which removes strong paths and their sidelobes) fails at the same ρ; it was not run.
- **Source.** [READOUT.md](../../../../experiments/pilot_acquisition_calc_20261120/READOUT.md).
