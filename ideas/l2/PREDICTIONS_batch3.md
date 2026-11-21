# L2 batch 3 predictions (written 2026-11-21 16:4x before any output was read; runner l, Claude Fable 5.2)
l01 (round-0 decoder input, reliabilities moved to other symbol positions)
- P1 pooled FER(orig) - FER(random order) below 5.8 pp, i.e. the card is killed by its own rule — .75
l03 (10% / 20% of data symbols known to the channel estimator only)
- P2 rho .15, 4 dB: final failure with 20% known symbols still >= 10% (card killed: not enough to pay a 0.65 dB rate tax) — .55
- P3 round-0 Doppler error at rho .15 drops by at least a third with 20% known symbols — .70
l04b (re-send at more points; failed frames from stage A)
- P4 net rescue (n+ - n-)/A_fail >= .5 at rho .10, 8 dB — .70; at rho .20, 5 dB — .35 (noise matters more near the waterfall)
