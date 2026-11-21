# L2 batch 5: decision rule and prediction (written 2026-11-21 17:0x before the readout; runner l, Claude Fable 5.2)
c35 (gate request: split the A4 gap in the true-delay arm with A4's own metric)
- Data: ideas/l2/out2/c01o_rows.jsonl.gz (pilot's round-0 Doppler, true delays, per path), 4 dB, rho .10 and .15, 300 frames each.
- Metric: per-frame power-weighted mean |error| over the paths found (stage A support_stats), averaged over frames; A4 bounds pilot_white .085 (rho .10), .068 (rho .15).
- Rule (fixed now): "outliers explain the gap" if, with every path of |e| > .25 bin set to zero error, the metric falls to within 15% of the pilot_white bound at both rho.
- Prediction: holds at both rho — .65.

c29 (gate request: pooled round-0 Doppler estimate versus the Doppler spread between paths; rho .10/.15, 5 dB, 100 frames, true delays in both arms)
- Rule (fixed now): the card's claim is supported if, at spread .02 bin and rho .15, the common estimate's power-weighted mean |error| is <= .05 bin
  AND its final failure count is not above the per-path arm's on the same frames. Report the spread at which the common arm's error exceeds the per-path arm's.
- Prediction: supported at spread .02 — .80; common worse than per-path from spread .1 on — .60; at spread .3 common final failures at least double per-path — .70.
