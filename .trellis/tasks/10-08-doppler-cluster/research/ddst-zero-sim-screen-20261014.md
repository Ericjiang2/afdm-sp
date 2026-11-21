# DDST zero-simulation screen: can transmit-side data nulling move the round-1 cliff? (frozen 2026-10-14)

Active task: `.trellis/tasks/10-08-doppler-cluster`. Origin: review of the external "AFDM论文创新与主线规划.docx"
(direction 2, Slepian-DDST); user approved a zero-simulation screen on 2026-10-14. This file is frozen in the commit that
adds it, before any number below exists. It does not reopen the C1 method search (terminated 2026-10-14, 63eed73b).

## 1. Question

The accepted cards (res-20261009-01, res-20261010-01) put the SP-AFDM bottleneck at the load cliff Kc, entered through the
round-1 information I_1(K). Data-dependent superimposed training (DDST; Ghogho, McLernon et al., IEEE SPL 2005; DPSS/BEM
variants He-Tugnait 2007-2008) removes from the data the component that leaks into the pilot correlator. Question: with the
C1 operator geometry, can DDST raise I_1(K) enough to move Kc_R1 right by >= 15%, under bounds that favour DDST?

## 2. Object 1: interference geometry (exact linear algebra, no frames, no receiver)

Time-domain model of the C1 receiver (IDAFT is unitary): `Y = sum_j h_j T_j s`, `(T_j s)[k] = phase_j[k] s[(k - l_j) mod N]`,
`phase_j = _cp(N, c1, l_j) * m_d`, `m_d = sqrt(N) v_d` (DPSS, W = 2.5, D = 8, centre 0), j = (tap l, d), K = 8L — the
SPg_flat column set of `driver_c1.py`. Pilot regressors `A = [T_j pt]` (N x K), `pt = IDAFT(pilot)`, frozen ZC pilot.
With the flat prior `E hh^H = I/K` and white data, the data energy reaching the pilot correlator is `x^H M x`,

    M = (1/K) sum_j T_j^H A A^H T_j      (N x N, Hermitian PSD).

Full DDST nulls the data in span{T_j^H A}, whose dimension can reach min(N, K^2). Rank-r DDST removes the top-r
eigenvectors of M from the data and rescales the data to keep power a = 1 - rho:

    f(r)   = sum_{i > r} lambda_i / sum_i lambda_i          (residual interference fraction, white data)
    phi(r) = f(r) N / (N - r)                               (after power rescaling)

Reported per L: r_90, r_99 (smallest r with f <= .10, .01), f(K), f(N/4), f(N/2), eigenvalue quantiles.
Delay sets: L distinct delays uniform without replacement from {0..100} (the C1 law), 4 draws per L, own seed stream
`SeedSequence([20261014, 0x44445354, L, draw])`; geometry statistics are the median over draws.
L in {4, 8, 12, 16, 20, 24, 28, 32, 40, 48} (K 32-384; covers all stored Kc and a 1.5x shift of the largest).
Outside K 32-384, phi is clamped at the edge value; if phi grows with K this favours DDST above K = 384.

## 3. Object 2: round-1 law with DDST (two upper bounds)

Baseline = `c1r1_model.LoopLaw`, mode H_w, LMMSE link (unchanged). DDST law, rank r:

- Refit (optimistic for DDST): every data-uncertainty interference term is reduced by phi(r):
  `s_D(v) = (n + a v phi(r)) / ((rho + a (1 - v)) N)`, pilot-only start `s = (n + a phi(r)) / (rho N)`.
  (In the receiver only the pilot-regressor share benefits; applying phi to all of it favours DDST.)
- Detector: per-symbol SINR q(e) as baseline (rescaled data keeps per-symbol signal energy); the distortion `P_r x` is
  assumed known to the detector (free; favours DDST).
- Variant U (no dimension cost): `I_1 = J_unc(q(e*_D))`, r = N/2 (largest allowed).
- Variant R (dimension cost, still an upper bound): data occupy N - r dimensions, so per data symbol
  `I_1 = min( J_unc(q(e*_D)),  (1 - r/N) log2(1 + q(e*_D) N/(N - r)) / 2 )`  (Gaussian-input capacity of N - r dims at the same
  total energy, per coded bit), r optimised on the grid {0, 8, ..., 512} for each K. r = 0 reproduces the baseline exactly.
- phi(r) at any K: linear interpolation in K of the per-L median phi(r) (K = 8L).
- eta per cell: the frozen T2 values in `out/c1_t2/predictions.json` (same as `c1r1_model retro`); per group, eta
  interpolated in K. K grid 16..1024 step 4 for the crossing; Kc_R1 = crossing of I_1(K) with I* (`i_star()`).
- Groups: the 7 stored groups of `c1r1_model retro` (c1_boot 8 dB rho .2/.3/.5, 11 dB rho .2/.3/.5; c1_map 6.5 dB rho .3).
  Groups whose eta table does not cover the needed K are reported, not extrapolated beyond the table edge (clamp).

## 4. Decision rule (frozen)

Ratio g = Kc_R1(DDST, variant R) / Kc_R1(baseline law), per group.
- PASS-to-design iff g >= 1.15 in >= 5 of 7 groups. PASS only permits writing a separate small-run protocol (new user
  approval); it is not a performance claim.
- Otherwise KILL: DDST is dropped for this setting; the result is recorded as a negative result with the geometry numbers.
- Variant U is report-only (it shows how much of any gain the dimension cost removes); it cannot rescue a KILL.
- Geometry flag (report-only, explains the outcome): r_90 / N at K = Kc_R1(baseline).

## 5. Limits stated in advance

- The law is a single-constant calibrated predictor (V2 rejected its mechanism; V3 bracket 20/20, Kc_R1 |ln| <= .21).
  The decision uses a within-law ratio, so a common bias partly cancels; it does not cancel a DDST-specific error.
- Round 1 only. A round-1 shift is necessary, not sufficient, for a Kc_R10 shift.
- Both variants are upper bounds on DDST benefit in this model; a KILL is conclusive for this model, a PASS is not evidence.
- Equal total transmit power; PAPR and the distortion-recovery cost are not scored.

Amendment 1 (2026-10-14, after c53641e6, before any geometry or law number exists): the stored T1 curve J_unc lies
.0003-.003 above log2(1 + q)/2 at q <= -5 dB (11/45 points; Monte-Carlo noise of the curve), so "r = 0 reproduces the
baseline" failed as written. Variant R now uses J_unc(q) at r = 0 and the min with the Gaussian term only for r > 0.
Near I* = .577 (q ~ 1 dB) the Gaussian term exceeds J_unc by > .01, so the bound is unchanged where the gate is decided.

## 6. Artefacts

Code `experiments/headroom_ladder_20261008/ddst_screen.py` (geometry: deinlab, AFDM env, frozen context via
`driver.load_context`; law: same script, mode `law`). Outputs `experiments/headroom_ladder_20261008/out/ddst_screen/`
(`geometry.json`, `law.json`, `RESULTS.md`; each JSON carries `_argv` and `_config`). Commit before and after the run.
