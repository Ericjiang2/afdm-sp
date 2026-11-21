# L2 batch 1 predictions (written 2026-11-21 before any run output was read; runner l, Claude Fable 5.2)
c08 (rho .10; 100 frames x U,G; SNR 3/4/5 dB)
- P1 joint mode: gain100 and gain200 F0 failure within 3 pp of ref (pooled) — .85
- P2 joint mode: dop200 F0 failure >= 80% at every SNR <= 5 dB — .85; dop100 between ref and dop200
- P3 fixed mode: gain200 F0 failure exceeds ref|fixed by >= 20 pp (pooled) — .65; its excess within a factor 2 of dop200|fixed's excess — .40
c02 (true round-0 channel; rho .05/.075/.10)
- P4 rho .05: joint F0 failure >= 95% at all SNR; fixed <= 10% at >= 6 dB — .85
- P5 rho .05 joint: |common gain rotation| > 45 deg in >= 50% of keys — .60; rho .075 joint failure >= 50% at 6 dB — .40
- P6 fixed mode at 4 dB: F0 failure at rho .05 lower than at rho .10 — .55
c10 (pilot swap, same frame/noise/data)
- P7 rand vs zc7: round-0 support_right up >= 10 pp at rho .10-.15 — .40; final failure at rho .15, 5 dB down >= 5 pp — .30; imp no better than zc7 — .50
