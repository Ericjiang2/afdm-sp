# FROZEN 2026-11-18 — Slot-count mismatch confirmation

Task `.trellis/tasks/10-19-slot-mismatch`. Frozen by Eric's Gate 1 decision (Accept 1–5, recorded in `.trellis/tasks/10-19-slot-mismatch/research/gate1-divergence.md` §4). Scope: complete. Cost cap: 40 core-hours. Decision rules are never relabelled after this commit. The draft used for the October pilots is preserved in Git at `08b268b6`. See [pilot evidence](POSTHOC_CHECKS.md) and the [P1 generator/SNR audit](../generator_snr_audit_20261019/REPORT.md).

## Populations and receiver arms

Use the corrected P1 U/G generator (`2261fde3…` / TCRF), physical frame IDs 10000–10999 inclusive, with paired noise/message streams across SNR and variants. The freshness search checked declared frame ranges and recorded frame IDs in 11,968 [deinlab](out/qualification_20261118/frame_audit.json) and 1,078 [local](out/gate_20261118/freshness_local.json) experiment output files, including files without a P1 flag. Neither scan reported a hit or a read error. Driver and launcher range checks also found no use of the block locally or among 677 [deinlab sources](out/gate_20261118/frame-static.txt). The search covered present experiment trees and excluded archived/vendor trees. The proposed interval appears in planning as a reservation. Rerun the inventory immediately before any main launch. Qualification used historical keys.

| Family | Channel | Receiver cap | Noise supplied to receiver |
| --- | --- | --- | --- |
| M | Original P1 U/G, physical rho .3/.5, true P=8 | 6, 8, 10, 12 | Known physical noise variance in receiver units |
| T | Same generator, only generator `P_paths` changes to 6 or 10 | 8 | Known |
| N | G, physical rho .3, true P=8 | 8, 12 | A common estimated variance per observed key |

The 4.5–8 dB grid in 0.5 dB steps is the P1 grid. Stage 3 provides direct CODELAY comparisons for U/G and both rho values where its grid overlaps. In P1, B crosses FER .01 between 5 and 5.5 dB at rho .3 and between 6 and 6.5 dB at rho .5. **Minimal** uses M at 8/12 with caps 6/10 added in G at rho .3 for Q1, plus N, all through 7 dB (24,000 M + 6,000 N = 30,000 receiver-input keys, with 12,000 extra M cap evaluations). **Complete** uses all M, T and N at all eight points (32,000 M + 64,000 T + 8,000 N = 104,000 receiver-input keys). Q2's primary comparison uses 4.5–7 dB in either scope. Unbracketed crossings are kept as bounds. Optional FULL requires a separate sample and cost allocation.

For each cap run the existing parameterized native F0, with two outer rounds, 20 detector steps, soft CE and native scalar-joint gains. On final nonzero syndrome run two continuations from that exact captured state. `A1c` uses the Stage 3 closed-form same-delay block and `A2` the E-1 diagonal scorer. Both use guard off, two swaps, two local passes, and the same detector, ridge and LDPC schedule. `B_s` uses A1c on triggered frames, F0 otherwise. A3 is the original fixed true-H reference on every key (at the same supplied noise for that family). Keep final geometry and actual slot counts. Optional FULL is a separately reported sensitivity arm with the same trigger/state. It is not included in the costed main schedules. Stage 3 observed identical per-key FER for FULL/CODELAY (0:0) on 13,600 keys, with 155 decoded-hash changes on jointly failed frames and one unresolved crossing gate. This supports using CODELAY as the specified arm for this study. It does not establish bitwise or cross-cap equivalence.

### Unknown-noise cell

The P1 receiver sees normalized AF coordinates. Set estimated noise variance to `max(1e-3, mean(abs(y)**2) - mean(abs(pilot)**2) - .5)`, computed once before the pilot front and shared by all caps/arms, including A3. The nominal data power .5 and unit ensemble channel power are fixed calibration inputs. The pilot-energy term is correct in expectation under the calibrated independent-phase, unit-operator-power channel law. Realized pilot power and signal/noise cross-terms fluctuate frame by frame. The floor is fixed in internal variance units. Inputs are y and the transmitted pilot. The estimate replaces `obs["sigma2"]` throughout the receiver, including pilot front and native CE, CSTATE ridge λ in `Gamma(v) + λI`, the detector noise term, and the likelihood/LLR computations fed to LDPC. The projected-variance Γ before ridge is a function of the APP-derived moments, so it can change indirectly through the input LLRs. Preserve the raw estimate, clipping flag and ratio to actual noise for evaluation only. N reuses M's y and pilot. It tests robustness to this calibrated estimate in one physical cell. Its outcomes remain separate from primary Q1/Q2.

**Interpretation boundary (pre-registered).** The estimate is a single-frame moment that uses the nominal data power .5 and unit
ensemble channel power, i.e. it assumes AGC-normalized receive power. Its ratio to the true variance had per-SNR SD .137–.266 on the
qualification frames (G5). If N is ROBUST, the claim is "robust under a single-frame moment estimate of σ²". If N is DEGRADED or
INCONCLUSIVE, the result is attributed to the receiver together with this estimator, not to the receiver's sensitivity to σ² alone.
No estimator change or rerun is made within this study.

## Design evidence and competing hypotheses

The 10-19 pilot informed this draft. Check 1 observed net −2.8 pp rescue versus unchanged geometry when scalar phantoms replaced only spurious slots (−4.8 pp when also replacing a true-delay slot). This favors an intrinsic penalty alongside displacement. Check 2 found that only 9.6% of 4,800 added slots held true delays, but there were 1.13 more true delays on average among cap-8 failures that cap 12 already decoded, versus 0.33 on the other keys. This supports testing pre-emption and reports why marginal trigger sets differ. Check 3 observed lower FER in the FULL cap-12 co-delay subset (.18 versus .36), with all 34 pairs formed by replacing a spurious slot. This weakens a blanket explanation based on co-delay occupancy. Pilot 2's full-vs-diagonal gaps on 293 common-trigger keys were .444 and .399 (ratio .90), versus the composition-sensitive pooled ratio .74. Pilot 3 retained the gap after doubling the edit budget (pooled ratio 1.000, 95% CI [.952, 1.051]). Both lean toward persistent ranking cost. In pilot 4 fixed gains rescued 52/283 failures and merging rescued 36/283, while harming 3/77 and 1/77 successes respectively. This suggests a secondary detector effect. These are developmental contrasts on earlier frames with FULL.

| Hypothesis | A1c rescue at cap 12 relative to cap 8 | A2 rescue at cap 12 relative to cap 8 | Paired gap and A2 phantom-first-edit share |
| --- | --- | --- | --- |
| H-displace: slot crowding dominates | Roughly stable | Rises toward A1c | D12/D8 <= .5 while phantom-first edits remain common and final cap-12 doublet share >= .5 |
| H-intrinsic: ranking or joint re-estimation penalty persists | Stable or falls when two swaps contend with more spurious slots | Stays low or also falls | D12/D8 >= .8 with a positive cap-8 gap and high phantom-first share at both caps |
| H-pre-emption: wider F0 retains weak true delays before reopen | Falls where cap 12 already covers true delays missing at cap 8 | Approximately stable as few such delays were rescued by A2 | Sol's forecast: gap narrows where cap 12 added entering coverage, with stable or higher phantom-first share. Astra's derivation (`astra-q2-prediction.md` item 2b) finds the sign of this term unidentified. Descriptive stratification only. |

For Q1, spare-cap robustness predicts crossings within ±.25 dB at 10/12. Noise/unknown-data overfitting predicts a positive shift above .25 dB despite spare slots. Under-cap loss predicts degradation at cap 6. T asks whether a fixed receiver cap remains useful for different physical P while also changing the channel law. On N, near-zero mean noise error with small per-frame scatter predicts similar crossings to M. Large scatter or clipping predicts a degraded or censored crossing even if the known-noise result is favorable.

## Proposed pre-registered estimands and decisions

Use errors in information bits and unconditional FER over all keys for Q1. Compare per-cell FER=.01 SNR crossings by first log-FER interpolation, replacing a zero by 0.5/n inside the bracket only. Use matched 20,000 physical-frame bootstrap draws (seed 20261019), resampling each frame jointly across all SNRs, scenarios, rho values, caps and variants. Preserve left/right censor bounds through each resample. Draws with an unbounded endpoint stay in the distribution. No extrapolation.

- **Q1 M:** delta = crossing(B_s) − crossing(B_8). ROBUST if the paired 95% interval lies in [−.25,.25] dB. DEGRADED if its lower bound >.25 dB. Otherwise INCONCLUSIVE. Report separately by cap and cell. For T apply the same gate to the B-minus-A3 gap relative to the matched P=8 gap in M, with shared physical frame bootstrap. Report N vs its M counterpart per cap, using the same thresholds as secondary descriptive robustness.
- **Q2 primary:** let C be the intersection of nonzero F0_8 and F0_12 syndrome on identical (scenario, rho, SNR, frame) keys in M at 4.5–7 dB. Within C define D_s = mean(success A1c_s − success A2_s). Each frame-weighted resample uses exactly the same C keys for both caps. Report paired transitions and the raw funnel by cell. If the 95% lower bound for D_8 is <=.05, label NO-BASELINE. If more than 1% of bootstrap denominators are nonpositive, label UNINFORMATIVE. With up to 1% invalid ratios, propagate their endpoints as unbounded when forming the percentile bounds. Label DISPLACEMENT-COMPATIBLE if the ratio's upper bound <=.5 and at least .5 of A2 cap-12 outputs on C retain a co-delay pair in the final geometry. Label PERSISTENT if the ratio's lower bound >=.8. Otherwise MIXED. These verdicts compare rescue gaps. Removing single-cap triggers selects a harder joint population. Changing cap changes F0's entering support and APP as well as slot capacity, so the comparison cannot identify the causal pathway by itself. A missing or failed branch makes the intended matched analysis incomplete and must be reported before assigning a verdict.
- **Secondary reads:** report D_s on its own cap-specific trigger set and the corresponding overall success difference with effect zero outside that set. Report the paired cap-10 comparison wherever measured, the 8/12 comparison restricted to units realizing both caps, and, in the complete scope, the 8/12 comparison with all eight SNRs. Record trigger and actual-slot funnels, common-trigger frame count, key-level discordance and final co-delay census. For A2's first accepted swap, remove the dropped slot from the entering support before checking whether the incoming delay already has a surviving slot. Report phantom-first edits divided by all common-trigger keys, with no-edit keys counted separately. For each accepted phantom edit record whether the dropped delay matched a true delay. For pre-emption, stratify the paired reads by whether F0_12 already retains a true delay missing from F0_8 and report rescue that adds an entering-missing true delay. N uses its own common-trigger subset for Q2. Cross-noise comparisons match the observed key.

- Paired difference D8 − D12 on the same common-trigger set C, with the same matched frame-cluster bootstrap (20,000 draws, seed
  20261019) and 95% percentile interval. Descriptive only; it carries no verdict. It is reported because the ratio of estimated gaps
  can be biased and unstable when D8 is small (Astra audit, `astra-q2-prediction.md` item 5).

**Precision check.** At 1,000 frames, 10 errors give an exact pointwise FER interval of about [.0048, .0183]. This leaves Q1 inconclusive with a shallow slope or weak pairing on the 0.5 dB grid. Keep the ±.25 dB practical band and classify censoring/uncertainty as specified. Resampling pilot-2 physical frames (20,000 draws, seed 20261019) gives [.786, 1.032] for the .90 Q2 ratio. Drawing 1,000 times from those same 200 pilot clusters gives a planning interval [.846, .956], conditional on the old trigger mix and FULL decisions. This supports retaining the .5/.8 separation. The wider rho/SNR mix can change precision or the effect.

## Pre-registered interpretation map (Q2 verdict → manuscript wording)

This map fixes, before data, which wording each Q2 verdict licenses for the narrative skeleton v1.1
(`.trellis/tasks/09-22-tf-production-gap-audit/research/tcom-narrative-skeleton-20261118.md`, points 2 and 4). The run tests the
end-to-end consequence of the cap. It does not test the local decision identity (Astra dialogue Eq. (8)); no verdict licenses a claim
about that identity.

- **PERSISTENT.** Replace "crowds out weak true paths' slots" as the stated cause with: the scalar score ranks a duplicate of a
  retained strong path above a missing weak path in the discrete support decision, and the admitted duplicate harms decoding even
  when slots are spare. Remove slot crowding as a cause of the CSTATE-vs-SBL ranking reversal; that reversal is then described only
  through the detector-interface mechanism, labelled as a candidate mechanism.
- **MIXED.** State the ranking error as the primary cause; state that spare slots reduce the gap only partly, citing D12/D8 and
  its interval. Slot crowding may appear only as a secondary contributor with that number.
- **DISPLACEMENT-COMPATIBLE.** The crowding sentence may be kept only if the paired funnel, actual slot counts and the pre-emption
  stratification are reported with it.
- **NO-BASELINE or UNINFORMATIVE.** No change to the skeleton; Q2 is not cited in the manuscript. Q1 is reported as usual.

Any rewrite is proposed in the draft result card and decided by Eric.

## Premortem and prediction ledger

- If the gap collapses, first check paired membership, actual extra slots and whether the scalar arm still inserts co-delay pairs. Higher SNR can empty the shared trigger set. Preserve denominators and cell counts rather than silently broadening eligibility.
- Pre-emption can lower the gap without increasing A2 rescue. Stratify on extra entering true coverage and report both rescue terms, the phantom-first share and support transitions. This is a descriptive stratification, since entering coverage is affected by the cap.
- P changes the channel law (e.g. delay redraw frequency and per-path energy). Frozen message/noise fingerprints and an A3 reference reduce comparability failures. They do not isolate the effect of P from the channel law.
- A biased noise moment estimator can confound geometry/decoder robustness. Check estimate/true distributions and the floor flag on the matched G keys. Promote no estimate-specific result to known-noise Q2.
- A mean timing estimate based on two old frames is sensitive to trigger mix. Use measured complete paths, include frame generation, and report a 30% planning allowance. Cost gates are prospective and require a decision before a main launch.

The [prediction ledger](../../research-assets/prediction-ledger.md) records the post-pilot, pre-main forecast. Rely on the earlier pilots only to set expectations. No data from the proposed main block enters qualification.

## Qualification and handoff

- **G1** requires decoded-bit and all r0/r1 array parity with frozen native at cap 8 on the original 40-key P1 gate list, plus an exact source diff limited to the max_paths argument and forwarding. Verify source inventories. G1 precedes other receiver runs.
- **G2** requires agreement with archived Stage 3 CODELAY and E-2 family R A2 decoded hashes on 32 historical triggers each, with F0 hashes checked on both sets. Also check CODELAY decoded bits against FULL with uniform variance once per triggered smoke family/cap.
- **G3** requires bitwise P1 generator parity for P=8 on 16 frames, expected true count and path-power error <=1e-12 for P=6/10, delay <=102, and unchanged pilot/message/noise draws. Record redraws.
- **G4** requires actual slot count = min(cap, distinct nominated delays) at both native rounds on all decoded gate/smoke units.
- **G5** describes known-truth bias, spread and floor-hit rate of the fixed receiver-side noise estimator at each SNR on 32 historical frames. No FER tuning.

Cost smoke uses frames 7800 and 7801. Time generation, native F0, triggered CODELAY and A2, and A3 with one BLAS/OpenMP thread per process and CUDA disabled. Report both scopes and stop after the Phase 1 commit. The [Trellis execution plan](../../.trellis/tasks/10-19-slot-mismatch/implement.md) governs the separate design-review and freeze decision.

The [Phase 1 receipt](out/gate_20261118/gate_summary.json) records gate outcomes, estimator diagnostics, and both cost projections.
