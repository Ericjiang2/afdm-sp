# C1 preliminary experiments for paper positioning (2026-10-10, FROZEN before the runs)

Context: direction analysis of 2026-10-10 (main session) proposed a centre "statistic and load, not estimator expressiveness",
benchmarked against Transformer-based CE papers (LS/threshold estimate -> learned refiner). Two cheap preliminary experiments test
its two load-bearing claims in the C1 receiver (SPg_flat FULL, genie delays, flat prior, K = 8L, QPSK, LDPC (3,6) n 2048, N 1024).
Existing evidence used, not re-run: WARM_1.0 (exact-projection round-1 start) = FULL within noise -> channel initialisation is
forgotten by the joint loop (c1-scalar-closure.md). Stored rows also show eps_det1 << eps_ce1 (e.g. .025 vs .168).

## Theory (first principles, scalar)
Round-1 pilot-only law (data as white interference, unit transmit power, sigma2 = 10^(-SNR/10)):
eps = K (sigma2 + 1 - rho)/(N rho), gamma = (1 - rho)/(sigma2 + eps), decode iff I_QPSK(gamma) >= I* = .577 -> gamma* = 1.312
(1.18 dB, the old "SINR threshold 1.37" up to the coordinate change), Kc1 = N rho [(1-rho)/gamma* - sigma2]/(sigma2 + 1 - rho).
Retrodiction vs IB2 R1 cliffs: right order (naive/measured .6-1.75), wrong rho trend (naive rho* .43/.51/.58 at 6.5/8/9.5 dB; measured
peak at rho <= .3, drop at .5). Data-aided version: training energy rho + (1-rho)(1-v), interference (1-rho) v -> rho* falls as the
soft-symbol residual v falls, i.e. as the inner budget T grows. Magnitudes overshoot ~3x with constant v (same failure as T2), so only
the direction is used. Stored IB2 ratios are direction-consistent (6.5 dB rho.2/rho.3: 1.07 -> 1.22; 8 dB rho.2/rho.3: .95 -> 1.02,
rho.5/rho.3: .72 -> .65 from T20 to T40).

Statistic gap (round-1 refit): regression design flat (ZC pilot), interference coloured, c_f = vbar |H_f|^2 + sigma2. Separable LS limit:
white/GLS error = E[c] E[1/c] = G(a) = (1 + a) e^a E1(a), a = sigma2/(1 - rho) (Rayleigh |H_f|^2). With the flat ridge prior (tau = 1/K):
bound eps_W/eps_G = (S G + K)/(S + K), S = rho N/(sigma2 + 1 - rho). Bound table (L 8/16/24/32):
- 6.5 dB: rho .1 1.40/1.28/1.22/1.18; .2 1.47/1.38/1.32/1.27; .3 1.47/1.40/1.36/1.32; .5 1.39/1.36/1.33/1.31; .75 1.21/1.20/1.19/1.19
- 8 dB:   rho .1 1.52/1.37/1.29/1.24; .2 1.61/1.50/1.42/1.36; .3 1.62/1.53/1.47/1.42; .5 1.52/1.48/1.45/1.42; .75 1.30/1.29/1.28/1.27
Cross-delay terms of B^H C^-1 B make the true GLS gain smaller than this bound (Jensen), so the bound is an upper limit.

## X1 (rho x T coupling): driver_c1ib2.py unchanged, out/c1rt
New cells: 8 dB rho .1/.15 (L 4-36), 6.5 dB rho .1/.3/.5 (L 4-32); arms R4T20, R4T40; frames 0-199. Combined with stored IB2 REP
(8 dB rho .2/.3/.5; 6.5 dB rho .2). Analysis c1rt_analyze.py. g_R(rho) = Kc_R(rho, T40)/Kc_R(rho, T20).
- P1 (primary): g_R(.1)/g_R(.3) > 1, paired CI lower end > 1, at R1 and R2, 6.5 and 8 dB; pass if >= 3/4.
- P2: argmax_rho Kc_R(rho, T40) <= argmax_rho Kc_R(rho, T20) at R1-R4, both SNRs (point; bootstrap frequency reported).
- Kill: P1 fails in >= 2/4 -> "pilot power and joint budget are substitutes" is not supported in this receiver.
- Closure: 6.5 dB rho .3 R4T20 rows equal the stored c1i FULL_R4 rows (same frames) -- checked separately.

## X2 (statistic gap): driver_c1sg.py, out/c1sg (diagnostic only; receiver outputs unchanged)
Cells SNR {6.5, 8} x rho {.1, .2, .3, .5, .75} x L {8, 16, 24, 32}, frames 0-199, receiver R2 T20. Per refit round r:
W (receiver white refit, recomputed), Wt (white, realised power), G (genie GLS, C = H_t S H_t^H + noise I), A (achievable GLS from the
receiver's current estimate). Smoke: W equals the receiver gains (0 difference), tap-operator closure ~0, eps_W1/eps_ce1/eps_ce2/ierr
equal the stored IB2 rows bit for bit (8 dB rho .3 L16 frames 0-1).
- P4: r1 = mean eps_W1 / mean eps_G1 > 1 with frame-bootstrap CI lower end > 1 in >= 38/40 cells.
- P5: r1 <= 1.05 x bound in >= 36/40 cells; fraction of the bound attained is reported.
- Report-only: rho/L trends of r1; round 2 r2 = eps_W2/eps_G2 split by final decode success; achievable recovery (W - A)/(W - G).
  Post-smoke expectation (not blind): r2 <= 1 in failing frames (decoder variances miscalibrated; GLS trusts v).
- Interpretation rule: P4 pass + r1 >= 50% of the bound -> the statistic gap of pilot-only/LS-input estimators is real; with WARM_1.0 it
  bounds what any initial-estimate refiner (whitening or learned) can do in a joint receiver. r2 <= 1 broadly -> naive coloured whitening
  inside the loop needs calibrated beliefs; not a quick method win.

## Results (2026-10-10, after the runs; card [res-20261010-02](../../../../research-assets/res-20261010-02.md))
- X1: P1 PASS 4/4 (g(.1)/g(.3) 6.5 dB R1 1.39, R2 1.17; 8 dB R1 1.25, R2 1.08; all CI > 1). P2 holds, but strictly only at R1
  (rho* 6.5 dB .2 -> .1, 8 dB .3 -> .2); R2-R4 argmax unchanged on the grid. Coupling fades by R4 at 8 dB. Closure vs c1i 0/1000.
- X2: P4 FAIL (21/40), P5 PASS (40/40). GLS beats white only in the noise-limited regime (K/S below ~.35-.65); at cliff loads
  r1 .88-.99. Round 2 (own variances) GLS worse in 39/40 cells. Achievable tracks genie where genie helps.
- Kill/interpretation per the frozen rule: the statistic-gap reading holds only at light load; with WARM_1.0 the initial-estimate
  slot has no cliff headroom in this receiver. The rho-T substitution claim survives at R1-R2 (scoped).
- Post hoc candidate mechanism (untested): SP self-interference is signal-aligned; by Jensen, GLS lowers information along the
  true channel direction while raising it elsewhere, so ridge bias dominates at high load.
