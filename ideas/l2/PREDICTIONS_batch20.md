# L2 batch 20: decision rule and prediction (written 2026-11-21 18:3x before running; runner l, Claude Fable 5.2)
l02, the paired injection the gate asked for (second review): does the old code's (extrinsic, APP) pairing create the start-up advantage?
- Tool: experiments/headroom_ladder_20261008/driver_c1e.py, unchanged, called through ideas/l2/l2_l02_inject.py which only replaces its `targets`
  function so that four arms inject fixed pairs (detector prior information I_A, re-estimation information I_R):
  arm .11 = (.1276, .4483)  matched code, round 1      arm .12 = (.1276, .5198)  what the (3,6) table assumes at the same I_A
  arm .21 = (.3173, .6134)  matched code, round 2      arm .22 = (.3173, .6669)  table
  6.5 dB, rho .3, L28, frames 500-599 (the frames of the original table), same injected noise across arms (the driver couples them).
- Readout: mean of mi_in1 (detector output information of the next round) per arm; D1 = arm .12 - arm .11, D2 = arm .22 - arm .21 (paired, with SE).
- Rule (fixed now): correct the measured inner curve T(I_A) of 6.5 dB / L28 by subtracting a piecewise-linear term through (0, 0), (.1276, D1), (.3173, D2), (1, 0)
  and rerun the receiver-schedule EXIT calculation (l2_exit_schedule.py). The card survives the pairing objection if the matched code still decodes
  within 10 outer rounds; if it stalls, the card is parked with that note.
- Predictions: D1 between .005 and .03 — .60; survives — .70.
