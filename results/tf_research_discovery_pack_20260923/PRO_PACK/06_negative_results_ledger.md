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
