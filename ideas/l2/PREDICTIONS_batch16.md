# L2 batch 16: decision rule and prediction (written 2026-11-21 18:2x before running; runner l, Claude Fable 5.2)
l09, the check the gate asked for (ideas/l2/l2_l09_coded.py): finite-length paired comparison under perfect channel knowledge.
- Same true channels (U scenario, frames 41000-41199), same codewords, same noise realisation, same budget (10 outer rounds, decoder 50 iterations,
  stop when the parity check passes). Receiver for every basis: soft-cancellation LMMSE with per-symbol priors from the decoder's check extrinsic,
  the project's (3,6) LDPC decoder (ctx.native.decoder_messages). No pilot (channel known). Bases: AFDM (the frame's DAFT-domain matrix),
  single carrier with cyclic prefix (time-domain matrix), OFDM. Nominal SNR 2.0 / 2.5 / 3.0 / 3.5 dB at rho .10 (data SNR about 0.46 dB lower).
- Rule (fixed now), pooled over the four SNRs, paired by (frame, SNR), bootstrap over frames:
  "no measurable detection advantage of AFDM over single carrier on P1" is supported if FER(SC) - FER(AFDM) has a point estimate within +-3 pp and a
  two-sided 95% interval inside +-6 pp. It is refuted if the lower end of the interval is above +3 pp.
- Predictions: supported — .75; OFDM worse than AFDM by more than 3 pp pooled — .70; AFDM FER at 3.0 dB between 2% and 40% — .70.
