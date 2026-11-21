# L2 batch 15: decision rule and prediction (written 2026-11-21 18:1x, after batch 13 was read, before this run; runner l, Claude Fable 5.2)
l08, second run. Batch 13 scored the two-round F0 output; at rho .10, 4 dB that stage fails on 948/1000 control frames, so the paired difference
(+2.9 pp, one-sided bounds 1.9 / 3.9, 34 frames worse against 5 better) sits against the ceiling. The card says "final information bits", i.e. the
full receiver with the re-search after a failed check. This run does that, on fresh frames.
- Same construction, gates and script (mode run2). Arm "corr": rho .10, 4 dB, frames 42000-42999, final errors of the full receiver (score_f0 with re-search).
  Arm "nocorr" (bears on parent c12): rho .10, 8 dB, frames 42000-42299, final errors.
- Rule (the card's, unchanged): extra FER in "corr"; kill the design claim if the one-sided 95% upper bound (paired bootstrap, 4000 resamples) is below 3 pp.
  If the control FER is above 90% or below 10% the point is called saturated and no verdict is taken from it.
- Predictions: control FER in "corr" between 35% and 65% — .80; not killed (upper bound >= 3 pp) — .70; point estimate between 1 and 8 pp — .70;
  "nocorr" at 8 dB: experiment fails on at least 90% of frames — .75.
