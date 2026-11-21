# L2 batch 6: decision rule and prediction (written 2026-11-21 17:1x before running; runner l, Claude Fable 5.2)
l05 (card's own cheapest check; two paths 30 ns apart, -1 dB, Doppler difference 125 Hz, hop interval 1 ms, two ~18 MHz bands overlapping one RB,
6 common subcarriers, 10 dB per subcarrier, 512 paired trials, two-path LS delay estimator on the stitched response)
- Rule (the card's, fixed): metric = 90th percentile of |first-path delay error|. Improvement of ABAB with (1/4,3/4) weights over the better of
  ABBA-equal and ABAB-equal; kill if the paired-bootstrap 95% upper bound of the improvement is below 20%.
- Prediction: killed (upper bound < 20%) — .50.
