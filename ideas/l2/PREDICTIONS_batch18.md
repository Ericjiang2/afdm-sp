# L2 batch 18: decision rule and prediction (written 2026-11-21 18:2x before running; runner l, Claude Fable 5.2)
Card l10 (child of l08; my own): the residual left by per-path time scaling after the best pure-shift fit obeys
  residual / signal = (pi^2 / 36) * (rms over paths of a_i N)^2      (full-band flat-spectrum signal, small drift).
Already checked on the l08 rows (no new run): out10/law_check.json.
New run (same script, mode run3): dose-response of the FER penalty. Arm "corr" of l08 with the residual path speeds scaled by 0.3 and 0.6
(rho .10, 4 dB, full receiver, fresh frames 43000-43599 for each scale). Law predicts median residuals of about -26.2 dB and -20.2 dB.
- Rule (fixed now): the law is useful for design if the measured median residual is within 1 dB of the prediction at both scales AND the extra FER is
  ordered (scale 0.3 < scale 0.6 < 14.9 pp from l08). "Negligible" is defined as a one-sided 95% upper bound below 3 pp (l08's line).
- Predictions: residual within 1 dB at both — .90; scale 0.3 negligible (upper bound < 3 pp) — .45; scale 0.6 point estimate between 3 and 10 pp — .60.
