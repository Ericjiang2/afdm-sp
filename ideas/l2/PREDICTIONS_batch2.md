# L2 batch 2 predictions (written 2026-11-21 16:1x before any output was read; runner l, Claude Fable 5.2)
c01 intervention (rho .10, sigma .2 Gaussian round-0 Doppler error, LS gains; all / clipped at .25 bin / tail only)
- P1 clip arm F0 failure at 5 dB at most half of the all arm's — .55 (c01 predicts a large drop; smooth-SINR predicts ~ (variance ratio .80) a small drop)
- P2 tail arm F0 failure at 5 dB at least half of the all arm's — .50
c01 observational (pilot's own round-0 Doppler, true delays)
- P3 share of relevant paths with |e| > .25 bin at rho .10, 4-5 dB below 10% (Gaussian sigma .2 gives 21%) — .70
- P4 F0 failure rate among frames with a > .25 path at least 2x that of frames without, at rho .10, 5 dB — .60
l04 (failed frames at rho .10, 12 dB re-sent with fresh noise)
- P5 same-codeword re-send (A) fails in under 30% of repeats — .65 (i.e. failures are mostly noise/codeword draws, not channel)
- P6 net rescue (n+ - n-)/pairs >= .50 of A failures — .15
