# One decisive production experiment: can ordinary decoder-conditioned geometry reopening close the gap?

## Purpose and interpretation

Test the important missing capability before claiming a new inference principle. The test compares one additional local coded round against the same round with a bounded **classical global geometry-replacement** step. This is a strong-control experiment, not a prospective paper confirmation and not a revived codeword-list campaign.

The new mathematical posterior-response candidate is **not** recommended for production deployment from this investigation: its practical approximations have not demonstrated a convincing advantage. Do not implement it, add a neural module, or retune covariance/Onsager rules during this experiment.

## Frozen scope

Use the original 6.5 dB, N=1024 Part-B observations and frozen numerical source
`2d130b4db9076e609be11d84035f1de5d6ee7b80`, dependency
`31d5ec0dd6d582b59e74096b945a326896e24ba3`.

Select the complete set of **43 final-nonzero-syndrome frames**, plus the first **32 zero-syndrome frames by observation ID** as forced-run negative controls. Membership is determined from the saved baseline output. In A+B+C these sets coincide with 43 failures and successful controls, respectively; that empirical correspondence is not a future truth oracle.

Two full wrapper calls per observation = **150 receiver calls**, each replaying the unchanged TF first two rounds before the added test round. No new radio observations, SNR points, code changes, pilot changes, gain-prior tuning, or competing search variants. The old 32-witness oracle results may be used only after the new outputs are committed for mechanism interpretation. This experiment uses observed-only inputs.

All observations here have already been examined. New receiver outputs on them are diagnostic/development evidence, not fresh-sample FER confirmation.

## Arms

### LOCAL20

Run the frozen TF receiver through round 2. Preserve its decisions and ready timestamp. Take final clipped decoder APP moments for CE, and the correct check-extrinsic vector for the next detector prior. Build the current physical path list, retaining its actual slots.

Call `reopen_geometry` with `max_edits=0`, `local_passes=2`, and the common parameters below. Then run **one native TF batch of 20 iterations and one LDPC call with cap 50**, using the same native coded-round reset and damping as the frozen receiver.

This matched control is not automatically identical to historical J20R3: its local windows are centered on the saved round-2 physical geometry, rather than necessarily repeating the original pilot-group initialization. Label it LOCAL20 and report this distinction. The historical J20R3 outcomes remain an additional descriptive comparator, not an invented bit-exact equivalence.

### GLOBAL20

Identical to LOCAL20, except `max_edits=2` in `reopen_geometry`. The code searches all slots and all candidate geometries for each accepted replacement. It is not restricted to the original 40 acquired integer atoms, original delay pool, or one path per delay.

Both arms use identical decoder information, refit objective, local-window rule, TF initialization, iteration count, and LDPC budget. No automatic extra round after failure.

## Common geometry configuration

- Fixed current slot count P; do not read the true physical path count.
- Integer delays 0..102, from the declared production delay range (verify the frozen manifest rather than silently hard-coding a mismatched range).
- Doppler grid -3:0.25:3, from the existing physical search domain.
- Repeated delays allowed; exclude only essentially identical same-delay Dopplers, tolerance 1e-6.
- Full-fractional CPP-aware path actions; no leakage truncation.
- Frozen q for the entire geometry operation: x_mean_AF = p + mu_APP, V = diag(v_APP).
- Exact Fourier Gamma for this diagonal working covariance.
- Ridge lambda = the original proper-complex sigma^2, matching the native refit convention.
- Maximum two global replacements; chunk size 64. Keep the current full model as incumbent.
- Then two local coordinate passes, windows centered on the geometry entering those local passes, halfwidth 0.75 intersected with [-3,3]. Per-coordinate tolerance .002 and at most 16 trial evaluations, including failed search trials. Accept only strict decreases of the common frozen objective.
- The code checks positive Schur complements; numerical failure must be recorded, not silently repaired by truth, alternate priors, or unregistered perturbations.

The supplied kernel is an adapter target, not permission to replace production physical functions without qualification. Its positive-chirp conventions must be verified against the actual frozen implementation. Prefer the production path-action and transform functions once the objectives agree.

## Critical adapter rules

1. Y is A^H y with the *production* DAFT convention. Pilot and data means are already power-scaled. Do not multiply a data variance by the power fraction again.
2. Use APP moments for the frozen CE objective and the actual check-extrinsic vector for the next detector prior. Do not add APP to the prior as another observation.
3. Enter a fresh native coded round after geometry changes. Do not transplant old Onsager/output residuals or cavity states across path sets.
4. Do not pass the result through the old one-path-per-delay grouping routine: it would silently destroy the tested capability.
5. Compute both operator Gram R and waveform-response Gram B^HB when needed; they are different objects. Preserve same-delay cross terms.
6. The ridge solution is not a Gaussian gain-marginal likelihood or calibrated posterior covariance. Scalar TF vh is not a geometry-confidence indicator.
7. Preserve the baseline fallback unchanged. All proposed decisions and timestamps must be stored even if they fail parity checks.

## Qualification before the 150 calls

Run `verify_research.py` and reproduce its algebraic tolerances. The finite-budget known-waveform recovery target is a diagnostic, not an algebra gate: one repeated-delay fixture deliberately did not meet the initial 1e-5 NMSE expectation.

On one frozen checkpoint and independent small dense fixtures, compare production and reference:
- Y and mean-waveform transformations;
- active and candidate path actions;
- Gamma, including repeated delays;
- Q, b, minimized objective, and gains/predicted signal;
- Schur candidate score vs direct replacement refit.

Use the established source's existing numerical tolerance discipline; do not loosen it to force a pass. Compare predicted signals, residuals and optimality rather than unstable coefficients when responses are nearly collinear. Record actual coefficient power and condition numbers.

## Required output per frame/arm

Store observation ID and hash; source/config hash; the two frozen baseline decisions and timestamps; final APP/check-extrinsic inputs; mu/v; starting geometry and gains; every accepted replacement; every local refinement endpoint; frozen objective before/after; final geometry/gains; Gamma and Gram diagnostics; candidate/trial counts; third-round decisions, APPs, syndrome, information/coded errors, and ready timestamp.

Timing must include transforms, all candidate columns, candidate cross-products, rejected candidates, local trials, TF, LDPC, message handling, setup per frame, and output readiness. Report full wrapper time and added branch time separately. Interleave LOCAL20 and GLOBAL20 with a fixed arm-order schedule. Do not combine original Part-B latency samples with new diagnostic timing into one distribution.

Truth can be used **after outputs are immutable** to label rescues/harms and compute operator/SP-weighted mismatch. It must never choose the slot, candidate, prior, acceptance threshold, or arm. Preserve exact code covariance when reporting SP-weighted physical mismatch; the generator has duplicate rows, so Pd I is not an exact code-law covariance.

## Primary readout

Report the complete paired 2x2 outcome table for LOCAL20 vs GLOBAL20 over all 43 triggered frames, plus each arm against the frozen fallback. Separately report GLOBAL20's rescues among the **23 original witnesses not rescued by either J40R2 or J20R3**.

Report forced-run harm on the 32 zero-syndrome controls, especially any newly produced valid-but-wrong word. A deployment wrapper would leave the original zero-syndrome decisions unchanged, but that does not make forced-run harm scientifically irrelevant or prove the absence of future undetected errors.

Preserve the original checkpoint when evaluating deadlines. Later computation must not erase a decision already available. Report deadline error/readiness at 0.5 s and 1.0 s separately from eventual completion. No assumption that the branch is useful at the original 0.5 s deadline.

## Frozen development decision rule

These are engineering continuation thresholds, not significance tests or a publication guarantee:

- GLOBAL20 should produce at least **five net additional correct decisions over LOCAL20 among the 43 triggered frames**, and at least **five rescues among the 23 witnesses missed by both earlier finite-iteration extensions**.
- Inspect every forced-run harm. Any newly valid-but-wrong output requires explicit review; do not declare syndrome a CRC.
- Target mean *additional complete branch* time <= 0.6 s on triggered frames, with p95 and maximum also reported. At the historical trigger rate 43/1024, 0.6 s corresponds arithmetically to about 25.2 ms extra work per original frame. This is a design-budget calculation, not a new measurement of complete-population latency and not a generalization to 6 dB.
- A win only in NMSE or the frozen quadratic does not meet the receiver-level gate.

The synthetic implementation took approximately 0.43–0.47 s for geometry processing alone on the local research environment. Production may differ, but the search cannot be assumed negligible.

## Interpret outcomes before any further experiment

- GLOBAL20 materially beats LOCAL20 within cost: a useful **classical** structural gap is established. It becomes a stronger mandatory baseline; it is not itself proof of a stronger core methodological contribution.
- Both continuations perform similarly well: routine refit/recentering or additional coded computation, rather than global structural access, explains the improvement.
- Global geometry improves the frozen objective or true operator fit but not decoding: the remaining issue is receiver/feedback compatibility or inadequate beliefs; do not infer that more path count, a better score, or a neural network is automatically needed.
- The bounded operation fails the cost or recovery gate: kill this specific configuration. Do not claim a universal impossibility of geometry adaptation, but do not launch a larger campaign by changing several knobs until the failed mechanism is understood.

Stop after this experiment. Return the paired outcomes, full cost/readiness records, source binding, and witness cases. No autonomous parameter sweep or new paper narrative.
