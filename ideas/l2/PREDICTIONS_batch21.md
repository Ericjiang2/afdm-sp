# L2 batch 21: decision rule and prediction (written 2026-11-21 18:4x before running; runner l, Claude Fable 5.2)
c06 (parked cloud card; reduced version of its parked check, within the 5 core-hour L2 cap): integer versus fractional delays, paired.
- Construction (ideas/l2/l2_batch9_fracdelay.py): U scenario, rho .25, full receiver (F0 + re-search), fresh frames 45000-45599. Same gains, Dopplers,
  data and noise. Control: delays as generated (integers). Experiment: every path's delay moved by an independent offset uniform in (-0.5, 0.5) samples
  (so the nearest integer tap is unchanged), waveform by band-limited periodic interpolation (the l08 code with zero time scaling).
  Arms per frame: control at 3.5 / 4.0 / 4.5 / 5.0 dB, experiment at 4.0 / 5.0 / 6.0 dB (noise scaled, same realisation).
- Gate: with zero offsets the experiment waveform equals the control to 1e-9 (already checked for this code path in l08's G1).
- Reading in dB, not in FER points (lesson of l08): paired comparisons on the same frames,
  "loss > 0.5 dB" if FER(exp @ 5.0) > FER(ctrl @ 4.5) with the paired-bootstrap 95% lower bound of the difference above 0;
  "loss > 1 dB"   if FER(exp @ 5.0) > FER(ctrl @ 4.0) likewise, or FER(exp @ 6.0) > FER(ctrl @ 5.0) likewise;
  "loss < 0.5 dB" if FER(exp @ 5.0) < FER(ctrl @ 4.5) with the upper bound below 0.
- Rule (fixed now): the card's premise matters for the paper if the loss is > 0.5 dB; it is a footnote if < 0.5 dB; otherwise undecided at this sample.
- Stated limits: critically sampled full-band signal (sinc leakage is the slowest-decaying case; a roll-off pulse would leak less); one rho; receiver untouched.
- Predictions: loss > 0.5 dB — .85; loss > 1 dB — .70; experiment at 6.0 dB still fails on more than 20% of frames — .50.
