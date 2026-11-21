# L2 batch 9: decision rule and prediction (written 2026-11-21 17:2x before running; runner l, Claude Fable 5.2)
l05 scan asked by the gate (two paths 30 ns apart, -1 dB; Rel-18-like timing: each hop 2 symbols on air + 2 symbols retune, ABBA's two B hops
back to back; measurement centres ABAB (1,5,9,13) T, ABBA (1,5,7,11) T with T = delta / 4; Doppler difference 10/30/60/125/400 Hz;
delta .143/.5/1 ms; SNR 0/10/20 dB; 256 paired trials per point; same estimator and energy for all schemes)
- Rule (the gate's, fixed): metric = 90th percentile of |first-path delay error|; improvement of ABAB weighted (1/4, 3/4) over the better of the
  two equal-weight schemes. Kill if, at every point with Doppler difference <= 194 Hz (30 km/h at 3.5 GHz, opposite directions), the paired-bootstrap
  95% upper bound of the improvement is below 20%.
- Second reading (fixed now): if no point at delta = .143 ms (the Rel-18 hop timing) with Doppler difference <= 194 Hz has an upper bound >= 20%,
  the card's value is set to 1 (it only helps with hop intervals several times longer than the standard's).
- Not done here (stated): the gate's two stronger baselines (joint four-snapshot estimator, four different bands) and the 7-path EPA profile.
- Predictions: no improvement at delta = .143 ms for <= 194 Hz — .85; improvement >= 20% survives at (125 Hz, 1 ms) under this timing — .70.
