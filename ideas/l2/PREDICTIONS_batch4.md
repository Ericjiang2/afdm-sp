# L2 batch 4: decision rules and predictions (written 2026-11-21 17:0x before any output was read; runner l, Claude Fable 5.2)
c01s (rho .10, 5 dB, frames 41000-41059 x U/G; one path's round-0 Doppler off by e, everything else true, LS gains)
- Rule (fixed now): a path is "pulled back" if its round-1 residual is <= .05 bin, "stuck" if >= .8 e.
  Capture-range reading (card c01) predicts pulled-back share >= 80% at e <= .24 and <= 20% at e >= .26, for the strongest AND the weakest relevant path.
  Smooth reading predicts the pulled-back share changes by < 20 pp between e = .24 and .26.
- Prediction: sharp step at .25 for both paths — .15; smooth for both — .60; round-0 decode failure rises with e for the strong path only — .75.
l05 (child of l04; failed frames re-sent; capture from the average of both receptions, decode reception 2; channel identical in both)
- Rule (fixed now): joint capture is supported if pooled BJ failures <= half of pooled B failures; control: AJ failures within one third of A failures
  (same codeword in both receptions: the data interference is identical, averaging cannot remove it).
- Prediction: BJ <= B/2 — .50; control holds — .70.
