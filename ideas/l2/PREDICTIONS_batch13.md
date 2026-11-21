# L2 batch 13: decision rule and prediction (written 2026-11-21 18:1x before running; runner l, Claude Fable 5.2)
l08 (child of c12; the card's paired replay; ideas/l2/l2_batch7_wideband.py; U scenario, rho .10, 4 dB, base receiver F0 with pilot-only round 0)
- Construction: delays, gains, data, noise of the frame; each path's waveform is the transmitted time signal sampled at (1 + a_i)(n - N/2) + N/2 - l_i
  (band-limited periodic interpolation; delay l_i at mid-frame) times the Doppler ramp k_i n / N, with a_i = k_i fs / (fc N).
  Arm "corr": common motion removed exactly, k_i -> k_i - k(2 m/s). Arm "nocorr" (declared now, bears on parent c12): no common correction, k_i as generated.
  For each path the best pure-shift waveform (same delay, Doppler and complex gain fitted with the transmitted signal known) is computed;
  control = sum of best pure-shift waveforms + noise; experiment = sum of wideband waveforms + the same noise. Same receiver on both, paired by frame.
- Gates: G1 with a_i = 0 the path waveform equals physical.regressors to 1e-9; G2 the frame's observation is reproduced from the path model to 1e-9.
- Frames: 41000-41999 (1000 frames; the card says 400, but at about 50% FER 400 pairs cannot bring a one-sided 95% bound under 3 pp even at zero effect).
- Rule (the card's, fixed): extra FER = FER(experiment) - FER(control) in arm "corr"; kill the card's design claim if the one-sided 95% upper bound
  (paired bootstrap over frames, 4000 resamples) is below 3 percentage points.
- Predictions: "corr" not killed (upper bound >= 3 pp) — .60; "corr" point estimate between 0 and 8 pp — .80;
  "nocorr" extra FER at least 20 pp — .80.
