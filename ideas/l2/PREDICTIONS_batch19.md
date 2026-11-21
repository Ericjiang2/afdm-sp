# L2 batch 19: decision rule and prediction (written 2026-11-21 18:2x before running; runner l, Claude Fable 5.2)
l08 / c12, the control the gate asked for (item 2): is the time-scaling residual harmful because of its structure, or only as extra noise power?
- Same construction as l08 "corr" (common motion removed, residual speed spread as generated), rho .10, 4 dB, full receiver, fresh frames 44000-44599.
  Four observations per frame, same data and thermal noise:
  ctrl   = best pure-shift waveforms + noise
  exp    = time-scaled waveforms + noise
  awgn   = ctrl + white complex Gaussian noise of the same power as that frame's residual (exp - ctrl), independent seed
  exp_s2 = exp, with the receiver's noise variance raised by that frame's residual power
- Rule (fixed now; paired bootstrap over frames, 4000 resamples, 95%):
  "acts as noise": FER(exp) - FER(awgn) has a two-sided interval inside +-5 pp;
  "structure matters": the lower end of that interval is above +3 pp.
  "telling the receiver helps": FER(exp_s2) - FER(exp) has its upper end below -3 pp.
- Predictions: awgn - ctrl between 4 and 10 pp — .60; structure matters — .45; telling the receiver helps — .25.
