# L2 batch 8: decision rule and prediction (written 2026-11-21 17:2x before running; runner l, Claude Fable 5.2)
l07 (card's own cheapest check; N = 1024, white complex target of unit power, SNR 20 dB, unknown complex tone at JSR +20 / +30 dB,
5-bit I/Q modulo ADC with lambda = alpha * s, s = sqrt((1 + sigma_w^2) / 2); arms: blind (my implementation of the card's sketch:
torus lift, Bessel autocorrelation template for (omega, beta), grid over phase, local refinement of the circular likelihood),
genie (tone known), 5-bit clipping ADC with full scale A + 3 s and the tone removed exactly)
- Rule (the card's, fixed, at JSR +30 dB and alpha = 3): kill if blind capture rate < 95%, or mean SINR gap to genie > 2 dB, or gain over the clipping ADC < 10 dB.
  "Capture" for a frame (my definition, fixed now): blind output SINR within 3 dB of the genie's on that frame.
  Second arm declared now: alpha = 4 (same rule), because of the estimate below.
- Estimate before running: at alpha = 3 the target itself wraps with probability .27% per real dimension; each wrap is an error of 2 lambda,
  so error power = 2 * .0027 * (2 * 3 * .711)^2 = .098, i.e. the genie's SINR is capped near 10 dB (the card's +25.3 dB counts quantisation only).
  With the clipping ADC at 1.3 dB the gain would be about 9 dB, below the card's 10 dB line even for the genie. At alpha = 4: wraps 6e-5, cap about 17 dB.
- Predictions: genie SINR at alpha = 3 between 9 and 11 dB — .80; card killed at alpha = 3 by the 10 dB line — .60;
  my blind implementation reaches 95% capture at +30 dB, alpha = 4 — .35.
