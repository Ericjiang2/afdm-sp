# L2 batch 7: decision rule and prediction (written 2026-11-21 17:1x before running; runner l, Claude Fable 5.2)
"Why AFDM" check (ideas/l2/l2_batch6.py; U scenario, rho .25, 5 and 6 dB, frames 41000-41099, same receiver and frames, c1 = project value vs c1 = 0)
- Rule (fixed now, one-sided): "the chirp matters" under a Doppler law if, pooled over the two SNRs, final failures with c1 = 0 are at least
  twice those with the project's c1 AND at least 10 frames more. Otherwise "no measurable chirp advantage at this sample size".
- Prediction: chirp matters under the project's Doppler law — .60; under the near-common law (spread .02 bin) — .30.
