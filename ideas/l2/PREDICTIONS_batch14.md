# L2 batch 14: decision rule and prediction (written 2026-11-21 18:1x before running; runner l, Claude Fable 5.2)
l02, first half of the step the gate asked for (zero simulation; ideas/l2/l2_exit_schedule.py): the receiver's own schedule instead of the merged one.
- Schedule: 10 outer rounds; in each round the decoder starts from zero messages and runs to convergence (at most 50 iterations) on the detector output
  of that round; the detector is refreshed once per round with the decoder's extrinsic information. Same EXIT model, same measured inner curves
  (c1e_phi.json, 6.5 and 8 dB, loads L8-L28), same three codes: (3,6), the best AWGN ensemble, the best ensemble for the inner loop at that load.
- Rule (fixed now): the card's L2 claim survives the schedule objection if, at 6.5 dB (measured, no extrapolation), the inner-loop-matched code succeeds
  within 10 rounds at a load where (3,6) does not (L28 is the candidate), or needs at least 3 fewer rounds at L24. Otherwise the claimed gain is a
  property of the merged schedule and the card goes back to L1 with that note.
- Prediction: survives — .50; (3,6) fails at L28 within 10 rounds at 6.5 dB — .90.
