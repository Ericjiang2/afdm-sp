# Frozen C1 matched-LDPC kill test

## Codes and receiver

Use the historical C1 `SPg_flat` / `FULL_R10` receiver, true delays only,
eight DPSS basis functions per delay, flat channel prior, external pilot
fraction 0.30, ten outer rounds, twenty detector updates per round, and at
most fifty flooding BP iterations per decode. Pass actual decoder APP and
extrinsic messages through the original receiver. Frame error means any
wrong information bit in the final decision.

- Regular control is the existing `(3,6)` Gallager code with seed 20260726.
- Matched code target variable-edge weights are `(2: .45, 3: .30, 30: .25)`.
  The finite node counts are `(2: 1377, 3: 620, 30: 51)` with 1024 checks of
  degree 6. PEG base seed is 20261122.
- AWGN control target variable-edge weights are `(2: .20, 3: .40, 12: .40)`.
  The finite node counts are `(2: 768, 3: 1024, 12: 256)` with 512 checks each
  of degrees 7 and 8. This realizes mean check degree 7.5 as an integer
  mixture. PEG base seed is 20261222.
- Require rank 1024 and code length 2048 for all arms. For each PEG arm take
  the first full-rank graph from base seed plus 0 through 31 inclusive. The
  ascending attempt order is structural and cannot depend on decoder results.

## Frames and grid

Use all 200 paired frames 12000–12199 inclusive at every measured cell, in the
same C1 RNG domain and with the historical `C1_MAP_ENTROPY`. Reuse physical
channel, information bits, pilot and unit noise across arms. Reuse frame IDs,
information bits and unit noise across SNR and both loads. The historical key
for regular-arm interface qualification is L28, 6.5 dB, frame 1000. Fresh
qualification uses frames 11998–11999, outside the measurement cohort. The
AWGN sanity check uses the separate C1 T1 domain, 200 frames 12000–12199 per
point, and data-symbol SNRs of 0.8, 1.0, 1.2, 1.4 and 1.6 dB. Require the
regular FER-50% crossing's analytic bit MI to lie within 0.025 of 0.5770.

The L28 primary grid is 5.25–10.50 dB inclusive in 0.25 dB steps. The low
window is 5.25–6.75 dB. The historical L28 reference was still at 84–85% FER
at 6.5 dB, motivating the upper extension. Use this order to maximize decision
coverage within the cap:

1. Measure L28 6.50 dB and advance upward in increments of 0.25 dB until all
   arms are at or below 10% empirical FER or the grid maximum is reached.
2. Ensure L28 6.75 dB is measured. Measure L28 from 6.25 down to 5.25 dB in
   steps of 0.25 dB. Measure L16 at 6.50, 6.75 and 7.00 dB, in that order.
3. If an L28 arm still has no measured FER at or below 1%, extend the measured
   L28 grid upward by 0.25 dB until all do or the grid maximum is reached.

Do not drop arms, shorten receiver schedules, reduce the registered number
of frames per cell, or count qualification data as evidence. An interrupted
cell stays partial. Total CPU allocation, including qualification and analysis,
is 20 core-hours. Forecast the next complete cell from measured CPU use and
stop if it cannot fit. Enforce the ceiling independently of this forecast.

## Frozen decision and uncertainty

Fit non-increasing FER by equal-weight isotonic regression over complete SNR
cells. Interpolate linearly in FER across adjacent grid points and use the first
SNR at or below the target for exact ties. Report left/right censoring at the
observed endpoints and do not extrapolate. Let `G_R` and `G_A` be the regular
and AWGN 10% crossings minus the matched 10% crossing, respectively, in dB.

- **KILL** if `G_R < 0.3` or `G_A <= 0`. This applies before the continue gate.
- **CONTINUE** if `G_R >= 0.8` and `G_A > 0`.
- **MIDDLE** if `0.3 <= G_R < 0.8` and `G_A > 0`.
- Censored inputs can determine the label only when all admissible values
  imply it. Otherwise the scientific verdict is unresolved. Budget and
  qualification failures are execution stops rather than scientific verdicts.

Draw 4000 paired frame-cluster bootstrap replicates with seed 20261123,
resampling each frame jointly across SNR and arms. Rerun the crossing analysis
in each draw. For each gain report the 2.5% quantile of lower endpoints and
97.5% quantile of upper endpoints, retaining infinite endpoints when present.
These are descriptive bootstrap intervals on the measured grid. Apply the
decision thresholds to the point gain or its grid-censoring bounds. Report the
entire interval and whether it spans the decision boundary. At 1% FER use a
separate conservative crossing confidence set by inverting simultaneous 95%
Clopper–Pearson binomial limits across the allowed L28 grid and all three arms
(Bonferroni), and difference those sets. Treat 1% as secondary only. Report the
L16 FER observations descriptively.

## Forecasts

The Gaussian-feedback model gives a larger gain than I expect to survive a
real finite-length receiver. Conditional on a resolved primary verdict, my
probabilities are KILL 0.45, MIDDLE 0.30, CONTINUE 0.25. Score the multiclass
Brier loss when resolved. I assign 0.65 probability that the matched code
beats the AWGN code on the primary L28 crossing. Score that prediction only
when the sign is identified. The two PEG arms share a construction policy.
The regular arm preserves the deployed reference graph. Limit this test's
conclusions to the actual codes within this C1 receiver.
