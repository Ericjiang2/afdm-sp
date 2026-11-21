# DDST small-run protocol: does transmit-side data nulling move the SP-AFDM cliff beyond round 1? (FROZEN 2026-10-14 on user approval)

Active task: `.trellis/tasks/10-08-doppler-cluster`. Status: **FROZEN** in the commit that records the user's approval (2026-10-14); no code, smoke run or frame existed before it. Predecessor: [res-20261014-01](../../../../research-assets/res-20261014-01.md)
(zero-sim screen PASS-to-design at round 1, upper bounds, delay support known at both ends; see its Correction).

## 1. Question and what would change our mind

The accepted cards put the bottleneck at the load cliff Kc, reached through round-1 information I_1(K) and then the measured
return-map staircase (res-20261009-01, res-20261010-01). DDST removes from the data the component that reaches the pilot
correlator, so it raises the round-1 starting point. Later rounds already remove data interference through data-aided refits,
and DDST costs data dimensions in every round. Question: does a real DDST transmitter with a DDST-aware receiver move the
**round-10 cliff Kc_R10**, at equal total power and equal code rate?

- Answer "yes" (PASS): DDST becomes a candidate paper item (AFDM-specific, with the cliff staircase as the mechanism). Novelty of the
  method itself stays nil (Ghogho et al. 2005; He–Tugnait 2007–2008).
- Answer "round 1 only": a negative result for the cliff; DDST is recorded and dropped.
- Answer "no" (KILL): the zero-sim bound was too loose; recorded and dropped.

## 2. Stage 0 — transmitter without delay feedback (zero-sim, runs first, no frames)

The screen used each frame's true delays to build the nulled subspace. Stage 0 repeats `ddst_screen.py` geometry + law with the
delay-prior subspace: `M_prior(L) = E_delays M`, Monte Carlo over 32 delay sets per L (C1 law: L distinct delays uniform on {0..100}),
same L grid, same law variants, same 7 groups. Report r_90 of M_prior, phi_prior(r), g_R(prior).
- If g_R(prior) >= 1.05 in >= 5/7 groups: Stage 1 includes the arm DDST-A-blind.
- Otherwise DDST-A-blind is not run; any Stage-1 result is labelled "requires delay-support feedback".
Stage 0 does not stop Stage 1 (Tx-genie is a legitimate TDD assumption: the receiver already uses genie delays in C1).

## 3. Stage 1 — small run

### 3.1 Transmitter (generator change only)
Same C1 generator and entropy as `driver_c1` / `driver_c1ib2` (channel, info bits, noise streams unchanged, so all arms pair frame by frame).
DDST data in the DAFT domain: `data' = DAFT( c (I - U U^H) IDAFT(data) )`, `c = sqrt(N/(N - r))`, U = top-r eigenvectors of M for the
frame's delay set (Tx-genie) or of M_prior(L) (Tx-blind). Pilot unchanged. Equal total power in expectation (c fixed); the realised
data power varies by frame, so the generator replaces the frozen `observe` per-frame data-power assertion (`driver.py:240`) by
(i) an assertion on c and r and (ii) a logged realised data power. r per cell: the frozen `r_opt` at K = 8L from
`out/ddst_screen/law.json` (group c1_map 6.5 dB rho .3, resp. c1_boot 8 dB rho .3); Tx-blind uses the Stage-0 r_opt.

### 3.2 Arms (one row per frame, cell, arm; R10, T20 = frozen default schedule through `wrappers._instrumented`)
| arm | transmitter | receiver | role |
|---|---|---|---|
| SPg_flat | plain SP | frozen SPg_flat (dpss_rx, GenieRefine flat) | baseline |
| DDST-A | DDST, Tx-genie U | DDST-aware (3.3) | primary |
| DDST-N | DDST, Tx-genie U | frozen SPg_flat, distortion treated as noise | report-only lower bracket |
| DDST-A-blind | DDST, M_prior U | DDST-aware | conditional on Stage 0 |

### 3.3 DDST-aware receiver (all changes marked `# DDST`; everything else frozen)
With `G_t = c (I - U U^H)` known to the receiver (it is a function of the pilot and the genie delays it already has):
1. Detector, a copy of `dpss_rx.scalar_joint_cols`: transmitted-signal mean `st = IDAFT(pilot) + G_t IDAFT(mu)` instead of
   `IDAFT(pilot + mu)`; data adjoint `adj = DAFT(G_t^H adjoint_time(hb, s))`. Scalar variances, Onsager terms and damping unchanged
   (the per-symbol gain of G is 1 on average: `c^2 (1 - r/N) = 1`).
2. Refit, `Design`: regressor signal `IDAFT(pilot) + G_t IDAFT(mu)` instead of `IDAFT(pilot + mu)`.
3. Pilot-only first pass only: effective noise `s2 = noise + phi(r) mean(v) E` (phi from the frame's own spectrum) instead of
   `noise + mean(v) E`. Later passes keep the frozen s2. No other retuning.

### 3.4 Cells and frames
- Primary: 6.5 dB rho .3, L in {8, 12, 16, 20, 24, 28, 32} (stored cliffs R1 62 law / 76 obs, R4 168, R10 180).
- Replication: 8 dB rho .3, L in {16, 20, 24, 28, 32, 36, 40}.
- 200 fresh frames per cell, offset 5000 (assert no stored C1 row has frame >= 5000).
- Size: 14 cells x 200 frames x 3 arms (4 with blind) = 8 400 (11 200) receiver runs plus one eigendecomposition per (frame, L);
  estimated <= 20 core-hours, single-thread jobs, <= 48 concurrent on deinlab (>= 16 cores left free). Rows stay remote with md5.

## 4. Gates before any scored frame
- U1: DDST arms with r = 0 reproduce SPg_flat rows bit-exactly (2 frames x 2 L).
- U2: the DDST-aware detector with `G_t = I` reproduces `scalar_joint_cols` bit-exactly; refit likewise.
- U3: SPg_flat on 3 stored frames reproduces the stored c1i R10T20 rows (determinism against history).
- U4: measured pilot-correlator interference energy of DDST data on 20 frames is within 10% of `f(r)` from the frame's spectrum.
- U5: commit before the run; results JSON carries `_argv` and `_config`.

## 5. Metrics and decision rule (frozen at approval)
Kc_Rk = K where the round-k FER crosses .5 (linear interpolation over L of per-cell FER). CIs: paired frame bootstrap, 2 000
resamples, frames resampled jointly across L and arms.
- P1 (primary, 6.5 dB rho .3): Kc_R10(DDST-A) / Kc_R10(SPg_flat) >= 1.10 and 95% CI lower bound > 1.00.
- P2 (replication, 8 dB rho .3): ratio >= 1.05 and CI lower bound > 1.00; if a crossing is outside the L range, P2 is "not assessable",
  not a pass.
- Decision: **PASS** iff P1 and P2. **ROUND-1-ONLY** iff the R1 ratio has CI lower bound > 1 but P1 fails. **KILL** otherwise.
- Report-only: R1 and R4 ratios; DDST-N ratios (receiver-awareness value); measured R1 gain / screen bound g_R (bound looseness);
  realised data power and PAPR; per-round receiver seconds; DDST-A-blind ratios if run.
- No rescue: no change of r, cells, frames or receiver after the first scored frame. A failed gate stops the run; the fix is a new
  disclosed amendment before any scored frame.

## 6. Limits stated in advance
- Equal code rate and power; the distortion has a real detection cost that DDST-A only partly models (scalar variances).
- One rho, two SNRs, one channel law (C1 clustered, genie delays, flat DPSS prior). No claim beyond them.
- PASS would make DDST a candidate item for the TCOM evidence skeleton, not an accepted claim; acceptance stays with the user.

## 7. User decisions (2026-10-14) and ownership
1. Implementation: this Claude session. 2. Replication cell: 8 dB rho .3. 3. Compute: approved, <= 20 core-hours CPU.

| work | owner | output |
|---|---|---|
| protocol, gate review, spot-checks, decision, card, STATE | Claude main (Opus) | this file, res card |
| code, gates U1-U5, Stage 0, Stage 1 launch/merge/analysis scripts | Sonnet subagent (xhigh) | `experiments/headroom_ladder_20261008/ddst_*`, `out/ddst_s0/`, `out/ddst_s1/` |
| read-only code review before Stage 1 launch | Codex CLI (if reachable) | `research/codex-ddst-code-review-20261014.md` |
