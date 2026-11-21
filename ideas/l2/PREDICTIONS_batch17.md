# L2 batch 17: decision rule and prediction (written 2026-11-21 18:2x before running; runner l, Claude Fable 5.2)
l06 (ideas/l2/l2_batch8_window.py): put the redrawn channels back. U scenario, rho .30, 7.5 dB (the card's point), full receiver (F0 + re-search).
- Natural draws: gen_fixed.one_attempt with the scenario's flags and no redraw, 600 draws (RandomState seeded by [seed, frame]); classes by the delays:
  A (last path <= 102), T (last path > 102, first-to-last spread <= 102), W (spread > 102).
- Observation: continuous transmission in the time domain; a path of delay l delivers stream sample n - l; samples before the current frame's prefix come from
  the previous frame (an independent codeword, frame + 5000). Windows: original (offset 0) and aligned to the first path. Pilot, data, noise of the frame.
  Gate: for a class-A draw with offset 0 the stream model equals physical.regressors to 1e-9.
- Rule (the card's): kill if no failed T frame is rescued by the aligned window. Reported with it: FER of A, of T and W under both windows, and the
  natural-frame FER  .514 f_A + .138 f_T + .347 f_W  under both windows (class shares from the draws).
- My reading before running: aligned T frames are ordinary in-window channels by construction, so "rescued" is close to certain; the informative numbers are
  f_T and f_W under the original window and f_W after alignment.
- Predictions: class shares within 3 pp of 51.4 / 13.8 / 34.7 — .90; card not killed — .85; f_T(original) - f_T(aligned) >= 3.6 pp — .60;
  f_W(aligned) >= 10% — .60.
