# L2 batch 12: decision rule and prediction (written 2026-11-21 18:0x, after batch 11 was read, before this run; runner l, Claude Fable 5.2)
l09 stage 1, extreme-case extension (METHODS G7): how large can AFDM's lead over single carrier get when the channel is made as time-selective as possible?
- Channels (same frames 41000-41059, unit total power, Doppler 2 cos(theta) bins, theta ~ U[0, 2 pi)):
  tap1x8 = all power on one delay, 8 rays (pure time-selective flat fading); tap2x8 = the two strongest delays of the frame, 8 rays each, powers as in the frame.
- Same quantities and tunnel threshold as batch 11 (same script, variant argument).
- Rule (fixed now): the card's claim (iii) "AFDM leads single carrier by >= 0.5 dB when same-delay Doppler spread is large" survives as an extreme-case statement
  if the tunnel-threshold lead is >= 0.5 dB on tap1x8; if it is < 0.5 dB even there, claim (iii) is dropped for rate-1/2 coded reception.
- Predictions: lead >= 0.5 dB on tap1x8 — .50; lead on tap2x8 between 0.1 and 0.5 dB — .55.
