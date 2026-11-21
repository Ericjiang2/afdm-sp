# DRAFT v2 — Forced-miss weak-path power-ratio sweep

Phase 1b is authorized by the [execution brief](../../.trellis/tasks/11-18-ratio-sweep/research/codex-sol-phase1b-brief.md).
Design source and rationale are in the [v2 draft](../../.trellis/tasks/11-18-ratio-sweep/research/protocol-v2-DRAFT.md)
and [external critique](../../.trellis/tasks/11-18-ratio-sweep/research/external-critique-gemini-20261119.md).
The natural-miss calibration undersamples low R and overrepresents decoded units at high R. Forced miss retains the paired intervention at every R.

## Channel and receiver intervention

Use the Phase 1 scenario G, corrected P1 geometric Doppler law, eight integer-delay paths, distinct-delay rejection, known noise, cap-eight two-round F0, and common channel, message, and noise draws across conditions. Designate strong and weak indices by the extrema of the original P1 path powers. Divide each of the six background powers by the original strong power and clip to [.1, .4]. Set the strong power to 1 and the designated weak power to 1/R. Normalize the eight powers to sum to one and retain the phases. The strong path is the unique maximum. The designated weak path can outrank background paths.

Use R ∈ {1.5, 2, 3, 4, 6, 8, 12, 16, 24, 32, 64, 128} and ρ ∈ {.3, .5}. Retain the Phase 1 entropy, domain, and component scheme. Calibration uses frame IDs 54000–54199 at each cell. The proposed main block uses IDs 55000–55999 at each selected cell.

Mask all five pilot Doppler atoms at the designated weak delay before OMP. Each F0 time-domain refinement selects only from the entering delays and adjusts Dopplers at fixed delays. Both detector and decoder rounds use the resulting masked support. Retain the native r1 arrays as the checkpoint consumed by the theory and exchange paths.

For the proposed main run, all frame × ρ × R units are eligible for both first exchanges. Start A2 and CODELAY from the same masked-F0 r1 checkpoint with the full exchange bank. Use the original continuation on F0 nonzero syndrome, whose first step supplies the first edit. Run only the first exchange on zero syndrome and use the F0 decode for terminal FER. Phase 1b runs exchange qualification exclusively on historical inputs. V2 calibration computes F0 and theory quantities only.

## Closed-form calibration and theory curve

Let μ and v be the E-1 symbol moments of r1 APP clipped to [-20, 20], with the receiver's internal data power .5. Let E = ||pilot + μ||², u = Σv, and λ = the internal observation noise variance. The anchor is the r1 path with largest estimated squared gain, breaking ties by slot index. Use the closest Doppler in the full exchange bank on the anchor delay that is legal after deleting some other slot, retaining the anchor. Break equal Doppler distances by lower Doppler. Let z = |dkernel(ν_candidate − ν_anchor, N)|. A missing anchor or legal candidate leaves the window undefined.

- T = E + u + λ.
- R_A2* = (T² − z²E²) / [z²(u + λ)²].
- R_C* = (T² − z²(E + u)²) / (z²λ²). Use +∞ for a nonpositive numerator. At z = 0, both thresholds are +∞.
- ξ = R / R_A2*. At z = 1 the thresholds simplify to 1 + 2E/(u + λ) and 1 + 2(E + u)/λ.

Calibrate SNR ∈ {4.5, 5.5, 6.5, 7.5, 8.5} dB with 200 frames in each of the 120 cells. Report F0 FER for the full cell, the window-defined count, coverage of ξ ∈ [1/4, 4], and 0/5/25/50/75/95/100 percentiles of E, u, λ, z, R_A2*, R_C*, and ξ among defined units. Strict JSON represents an infinite quantile as `"+inf"` and an empty distribution as null. Report P̂_A2 = share(ξ > 1) and P̂_C = share(R > R_C*) over window-defined units.

For each ρ, select the SNR with the greatest sum of counts of defined units in ξ ∈ [1/4, 4] across all 12 R values. Break ties by lower SNR. Use that SNR for every R at that ρ. The selected-cell shares in `out/phase1b/predictions_v2.json` are the theory curve to register before main execution. The draft decisions below use the A2 curve for S4.

## Proposed main decisions

Use 20,000 physical-frame cluster bootstrap replicates with seed 20261119, resampling each frame jointly across R and ρ. Report the window-defined population pooled and by ρ. Record each arm's first-edit class in precedence order: no edit, phantom on a delay that survives slot deletion, recovery of the designated weak delay, recovery of another missing true delay, other. Log the theory quantities and report the undefined-window share, spacing strata, five-class composition by R, and triggered FER/rescue. The secondary directional prediction for the CODELAY advantage in triggered FER is an inverted U across R.

- **S1.** The lower interval bound for the A2 phantom-rate difference between ξ ≥ 2 and ξ ≤ 1/2 exceeds .50.
- **S2.** Regress the A2 phantom-versus-weak-recovery outcome on log ξ using only those two classes. The interval for ξ₅₀ entirely inside [1/2, 2] is SUPPORTED and an interval disjoint from [1/2, 2] is REFUTED. Otherwise it is INCONCLUSIVE.
- **S3.** Within 1 < ξ and R < R_C*, the CODELAY phantom-rate interval upper bound is at most .10 and the lower bound on its weak-recovery rate minus A2's exceeds zero.
- **S4.** Among (ρ, R) cells with at least 30 defined units, compare the observed A2 phantom share to P̂_A2. Maximum absolute deviation at most .15 is SUPPORTED, above .30 is REFUTED, and intermediate values are INCONCLUSIVE.

H1 predicts a sharp A2 transition near ξ = 1 and no CODELAY flip within the predicted window. H2 predicts an A2 transition below ξ = 1, for example if off-grid weak paths receive smaller gains than modeled. H3 predicts too few phantoms and weak recoveries to locate the transition because other edits or no edit dominate. A rise in other-delay recoveries would flag interference from additional misses induced by masked F0. Claude's v2 predictions are S1 .80, S2 SUPPORTED .45 / REFUTED .25, S3 .75, and S4 SUPPORTED .40.

## Phase 1b gates and cost

- **G1.** Repeat the original Phase 1 archive check for the 32 frozen historical keys. With masking disabled, compare v2 to the same archived keys and compare the saved native states to the original F0. Stop on any frozen-source or archive mismatch.
- **G2.** Check the designated ratio, normalized power, clipping, and unique strong gain across the v2 grid. Verify deletion of precisely the designated delay's columns and exclusion through both F0 rounds. At z = 1 compare both thresholds to their simplified forms within 10⁻¹². Qualify the r1 handoff, full bank, and first-only/full decision parity on earlier frames.
- **G3.** Verify fresh v2 calibration and main IDs against both prior blocks in the namespace, including component descriptors, channel seeds, and local and deinlab namespace inventories.
- Calibration uses one compute thread per worker in `g_sweep` on deinlab, with 14 workers plus the coordinator and multiprocessing resource tracker. The calibration deadline is 18 minutes. Receipt files record runtime configuration and source identities. Preserve a failed attempt before fixing and rerunning an experiment-code defect.
- Project 24,000 main units using selected-cell F0 and window CPU, timed historical first pairs for all units, and the incremental full-pair CPU for the projected nonzero-syndrome count from calibration. Include 30% headroom and report an all-trigger scenario. The draft cap is 10 core-hours.

## Deviations from the task's v2 draft

- Phase 1 chooses the anchor by the designated strong truth delay and true Doppler. Phase 1b uses the strongest estimated r1 gain so the computation honors the explicit no-truth constraint. The estimate can anchor on a different delay if F0 missed or misranked the true strong path. Candidate-bank geometry and the remaining moment definitions follow Phase 1.
- The rewritten R_C* infinity condition checks the numerator as required by the execution brief. Zero coherence separately makes both thresholds infinite because their denominators vanish.
- The calibration records nonzero syndrome counts to price continuation before any v2 exchange. The first-pair cost is included in the full-pair timing, so each triggered unit is charged once. The calibration uses 14 CPU workers so the coordinator and resource tracker fit within the 16-process limit.
- Phase 1b implements and tests the main handoff only. The main analysis rules remain a draft for a later run.

## Superseded v1 design

<details>
<summary>Phase 1 protocol and original decision rules</summary>

# DRAFT — Controlled weak-path power-ratio sweep

Origin: [Claude's 2026-11-18 draft](../../.trellis/tasks/11-18-ratio-sweep/research/protocol-DRAFT.md). Eric authorized Phase 1. Astra predicts from the calibration block, then Eric decides whether to freeze and run the main block.

## Design

Scenario G, known noise, eight transmitter paths and F0 cap eight. Use the corrected P1 geometric Doppler law, delay-cap rejection and integer delay grid. Draw the P1 paths once per physical frame, rejecting the entire delay/gain/velocity draw if its delay bins collide or exceed the cap. Keep the phases and Dopplers. Fix the strong and weak indices to the maximum and minimum original P1 Rayleigh powers. Ties use the first index. For R in 2, 4, 8, 16, 32, 64, 128, 256, set the unnormalized strong and weak powers to 1 and 1/R. For each of the six other paths, divide its original power by the original strong power and clip to [(1+10⁻⁶)/R, 1−10⁻⁶]. Normalize all eight powers by their sum and apply the original phases. Total physical power is one because distinct integer delays are Frobenius-orthogonal. Absolute strong and intermediate powers can change after normalization.

Use the P1 `SeedSequence` descriptor with entropy `a07ed5cd6343eb6c7443735dfdcbca71455412cb37a6631126cc374d98612659` and domain `0x52535750`. Calibration IDs are 52000–52199 (200 each cell). Main IDs are 53000–53999 (1000 each cell). The frame, channel/message/noise component and this namespace determine each RNG stream. R, ρ and SNR do not enter that key. Across R within ρ/SNR the delay, Doppler, phases, pilot, data, message and additive noise are shared. The SNR grid uses common underlying noise with P1's usual change in scale. Keep the same exogenous frame together across all cells when resampling.

Use `ρ ∈ {0.3, 0.5}` and SNR candidates `{4.5, 5.5, 6.5, 7.5, 8.5, 10.0}` dB on the P1 transmit-power convention. For each ρ compute both F0 rates pooled over the eight equally sized R cells at each SNR. Choose the lowest candidate where the pooled weak-path miss rate is at least 30% and pooled F0 FER is at most 50%, using integer counts without rounding. If none qualifies, report no selection for that ρ and stop after Phase 1. Use the chosen SNR for every R at that ρ.

## Calibration and main readout

F0 eligibility means the designated weak delay is absent from the captured `r1` support, the actual input to first exchange. F0 FER uses information-bit mismatch over all frames. Calibration runs F0 alone and exports per-cell counts and 0/5/25/50/75/95/100 percentiles on eligible frames. Compute `E=||pilot+μ||²`, `u=Σv` and `λ=obs.sigma2` in the receiver's normalized data-power-.5 convention, using the actual clipped F0 APP and E-1 symbol moments. Use the physical pilot fraction in `x=2(1−ρ)·mean(v)` to convert the average symbol variance back to transmit units. For geometry use the F0 path on the designated strong truth delay nearest its true Doppler, then the nearest same-delay grid candidate legal after deleting some other slot with the anchor retained. Ties use the lowest slot or Doppler. Store the absolute spacing in Doppler bins and complex κ=BₐᴴB꜀/E and D=dkernel(ν꜀−νₐ,N) via separate real, imaginary and magnitude quantiles. Report the geometry denominator and use null quantiles when no pair exists. Eligibility does not require an anchor. Calibration performs no exchange scoring or selector calls.

Main logging starts A2 and CODELAY from the same saved F0 state. For each eligible unit log both classes, independent of F0 syndrome. Class precedence is no edit, phantom (incoming delay belongs to the support surviving deletion), weak recovery, other missing true delay recovery, then other. The last three use missing delays at branch entry. Run the original two-exchange, two-local-pass continuation on native nonzero syndrome keys for secondary rescue and FER. On eligible zero-syndrome keys, run just the first exchange. Phase 1 qualifies this logging on historical keys only.

## Gates and cost

G1 is admission-law G1 unchanged on the 32 archived cap-8 N keys. A1c in the archive is the bound CODELAY arm. Compare archived F0 and logged continuation fields exactly and check that first-only decisions match the first decision of the full path. Also exercise the new five-class logger and full continuation on historical G/U keys, using forced first-only versus full-path class parity on the same F0 state.

G2 checks the realized ratio and total path power at 10⁻¹² tolerance and strict power ranks on synthetic keys across the full R grid. Verify array equality of geometry and exogenous inputs, and check CPP against the independent dense P1 operator. G3 checks disjoint block IDs, all three RNG descriptors and channel-seed uniqueness across both blocks, and searches the local and deinlab experiment inventories for the new namespace. Main-block freshness checking consumes seed descriptors only.

Calibrate under `g_sweep` on deinlab with up to 16 one-thread CPU workers. The calibration stage has an 18-minute wall deadline. Estimate 16,000-arm-paired-unit main cost using selected-cell calibration CPU for F0 and historical CPU timings for first-only and full continuations. Take the measured mean per historical eligible pair for first-only, and the measured mean per triggered pair for full continuations, including small record serialization. Report an upper planning scenario charging full continuation on every key plus the eligible first-only workload, with 30% headroom rounded up to a whole core-hour as the suggested main cap.

## Main decision rules retained from the original draft

Use 20,000 paired physical-frame cluster bootstrap replicates. Report by ρ.

- S1. A2 phantom rate rises monotonically with R and the lower interval bound on the difference between extreme R values exceeds .30.
- S2. Compute the A2 R₅₀ by logistic interpolation on log R, using only phantoms and weak recoveries. SUPPORTED if it lies within Astra's predicted interval. REFUTED if it lies outside and the bootstrap and predicted intervals are disjoint. Otherwise INCONCLUSIVE.
- S3. CODELAY phantom rate is at or below Astra's upper bound at every R. At the highest R, the lower interval bound for the CODELAY minus A2 weak recovery rate exceeds zero.
- Secondary reads are triggered rescues and FER, other true-delay recoveries, and spacing strata.

Claude's original predictions are S1 probability .85, S2 SUPPORTED .50, S3 .75. Astra supplies cell predictions for both arms and an R₅₀ point and interval before main execution. Competing outcomes include a misplaced or absent A2 crossing and a CODELAY crossing. Sparse eligible or two-class samples and competing true-delay recoveries limit interpretation.

## Phase 1 revision reasons

- The original R grid is retained. Explicit rank selection, relative clamping and normalization make the intervention reproducible and keep the designated paths strictly extreme. Rejecting collided delays removes true doublets from this single-delay mechanism test.
- A fresh namespace and explicit disjoint frame ranges make block assignment auditable. Sharing component streams across conditions removes changes in geometry and noise draws from the R contrast.
- The SNR grid spans the historical crossing neighborhood and adds higher candidates for the controlled channel. Equal-R pooling selects one SNR per ρ without changing SNR across the R contrast. A null selection prevents post hoc grid tuning.
- `r1` names the receiver snapshot that actually enters exchange. The coherence definitions and missing-pair rule tie calibration to a specific legal comparison without exposing decisions. Complex quantiles preserve phase information in addition to magnitude.
- Exact archived replay, generator invariants, a separate historical logger check and freshness checks qualify different parts of the pipeline. The explicit cost scenario distinguishes historical branch timing from controlled F0 timing.
- The reporting and decision sections retain the draft's targets and make the two-class S2 denominator and joint resampling explicit.

</details>

## Concurrent main-design amendment

While Phase 1b was starting, the [Astra amendment](../../.trellis/tasks/11-18-ratio-sweep/research/protocol-v2-DRAFT.md#6-冻结前修订按-astra-设计评审2026-11-19本节优先于-2) proposed replacing S1–S4 as the main criteria with P1–P4, based on direct paired phantom/weak Schur gains under one fixed deletion slot, with global first-edit classes as secondary. It also specifies an oracle anchor and its coverage, separation, and two-block comparison rules.

The Phase 1b curve follows the execution brief's truth-free anchor. Its probabilities therefore apply to that anchor definition. An oracle-geometry main analysis would require a matching oracle-geometry calibration curve before testing P4. The new candidate-score instrumentation belongs to that later main design. Phase 1b qualified the shared masked-r1 handoff using historical inputs and ended before main execution or freeze.

The calibration receipt's protocol digest covers the text above this post-launch amendment.
