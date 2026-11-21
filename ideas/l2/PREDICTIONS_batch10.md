# L2 batch 10: decision rule and prediction (written 2026-11-21 17:5x before running; runner l, Claude Fable 5.2)
l09 stage 1, P1 part only (zero receiver, perfect channel knowledge; ideas/l2/l2_l09_basis.py; U scenario, 60 frames 41000-41059)
- Quantity: for each frame take the true time-domain channel, and for the symbol basis U in {AFDM (project DAFT), single carrier (identity), OFDM (DFT)}
  compute the per-symbol output SINR of the soft-cancellation LMMSE detector at prior variance v, gamma_k = s_k / (1 - v s_k),
  s_k = [(sigma^2 I + v G)^(-1) G]_kk, G = U H^H H U^H; bit information I = mean_k J(2 sqrt(gamma_k)).
  Threshold = SNR at which the frame-averaged I at v = 1 (no decoder feedback) reaches .57; also the area of I over v in [0, 1] at 4 dB.
- Rule (the card's, fixed): its claim (i) holds on P1 if |threshold(AFDM) - threshold(single carrier)| <= 0.15 dB.
- Not done here: the Jakes-4 cluster half of stage 1 and stage 2 (coded FER with matched pilots and estimators for each basis).
- Predictions: claim (i) holds — .70; OFDM threshold worse than AFDM by >= 0.3 dB — .70.
