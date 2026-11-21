# (b) Strict discriminating run: risk-controlled per-frame scheduling vs strong adaptive baselines — FROZEN MANIFEST (2026-10-13)

Authority: user chose the full strict protocol (2026-10-13). Protocol text = Codex R3 notes
`codex-aprime-check-20261013.md` §6.1-6.5 (cells, frame isolation, power rule, causal replay, q model, P family, baselines
B0-B4, selection, cost, gates) and §6.5 KILL rules / G0-G5, adopted as written EXCEPT the decisions and clarifications below.
Earlier verdicts (T1-T3, A' frozen "not viable") stay on record; this is a new test with new data.

## Decisions fixed here
1. Object under test: one object = per-frame scheduler whose escalation uses the action value Delta_e(z) = q20(z) - q_e(z) and
   whose give-up uses the fixed-tail risk of the chosen continuation (Codex §6.2 P family), vs strong baselines B0-B4 (§6.3).
2. Cells (Codex §6.1): C1 6.5 dB rho .3 L16 l=.10; C2 6.5 dB L20 l=.20; C3 8 dB L28 l=.10; C4 8 dB L32 l=.20. No target
   lifting; a non-operable cell keeps its place in the denominator 4.
3. Namespaces: TRAIN = old entropy 129abc... frames 0-599 (6.5 dB: stored out/c1esc rows; 8 dB: new run out/c1apb_train8).
   CAL/TEST = new entropy SHA-256("AFDM_C1_APRIME_B_20261013_R3") =
   3263bc1d9a844f4d0939477f174cbbc356c2d2dbd534d4ebc1cc63c6b5c47521 (not found in any local run config; remote check in G0).
   CAL frames 0-599; TEST frames 600..599+n_c, n_c from the Codex §6.1 rule computed once after CAL selection is sealed
   (min 4000, cap 10000, rounded up to 100).
4. Receiver/arms: driver_c1esc.py arms E10, E0, E1, E2, E3 (R = 10), unchanged numerics. New flag --shuffle-arms: per-frame
   arm order from a PRNG seeded by (entropy, frame, L) only, recorded per row (timing balance). Closure: with shuffle on,
   E10/E0 rows of TRAIN 6.5 dB frames must equal stored rows (spot set) and all E_e prefixes must equal E10 for r <= e (G0).
5. Cost (Codex §6.4 with one practical decision): primary currency = per-row t_cum along the causal path (pilot front included,
   verified in native_twofft.receive: st set before pilot_front) + measured feature/q/decision overhead, from CAL and TEST runs
   executed at a FIXED concurrency of 64 single-thread shards with shuffled arm order (shared host; load logged per shard).
   Quiet validation: after TEST, a pre-registered stratified subset (first 200 TEST frames of each cell by frame id) is re-run
   at 8 shards; if |R_quiet - R_main| > .03 for P* vs B* in any cell, the compute gate of that cell is reported as
   "contended timing" and cannot count as a PASS. Secondary units: inner updates, rounds, LDPC iterations, p95 cost.
6. Gates/alpha/KILL: exactly Codex §6.5 (CP one-sided 98.75% upper U(p_pi) <= l and U(p_B) <= l; paired Tango score upper
   U(d) <= .01 with the exact fallback when discordant count < 20; R_hat <= .85 and bootstrap 98.75% upper U(R) < 1 with
   B = 20000 frame-block resampling synchronised across cells; >= 3/4 cells incl. both SNRs). G3 (vs B3, B4) and G4 (LOCO
   Brier gain >= .005 with CI; Delta-quintile net rescue) as secondary per §6.5. KILL 1-4 as written.
7. Seeds: bootstrap seed 20261016; ridge CV folds by frame id mod 5; mixture U-stream = PRNG seeded by (new entropy, frame, L,
   "mix") independent of message/noise/channel streams.
8. Stage order and seals: (S0) code + manifest commit -> (S1) TRAIN8 + CAL runs -> (S2) stage-1 analysis: G0, fit q on TRAIN,
   build candidates, CAL selection with margin m_c = 1.645 sqrt(l(1-l)/600), seal JSON (policies, weights, coefficients,
   hashes, n_c) and commit BEFORE any TEST run -> (S3) TEST run -> (S4) stage-2 evaluation on TEST + quiet validation ->
   result card. No TEST rows are generated before the S2 seal commit.
9. Scope: known (genie) delays; one code/N/QPSK; claims limited to this receiver family; no deployment or TCOM claim from this
   run alone (G5).

## Files
driver_c1esc.py (+ --shuffle-arms), launch_c1esc.sh; c1apb_lib.py (replay, baselines, q model, stats: CP, Tango, bootstrap),
c1apb_stage1.py, c1apb_stage2.py, unit_check_c1apb.py; outputs out/c1apb_train8, out/c1apb_cal, out/c1apb_test,
out/c1apb_quiet, out/c1apb/seal/, out/c1apb/analysis/. Division of labour: Sonnet (xhigh) implements and runs; Opus reviews
code (leakage, causal replay, gates) and outputs before each seal.

## Amendment A1 (2026-10-13 13:15, before any CAL analysis; source: codex-lit-followup-20261013.md, verdict "narrowed")
Prior work already predicts direct rescue (Akyildiz & Mahdavifar 2026, continuation-need predictor; EP4364367 remaining
iterations + success-probability target). The remaining distinction is the NET effect of the two continuations
(rescue - harm). Added baseline:
- B5 direct-rescue controller: pooled ridge logistic for the rescue probability rho_e(z) = Pr(Y20 = 1, Ye = 0 | z), fitted on
  TRAIN with the same features, metadata columns, ridge grid and CV as q; escalate at the first r <= 3 with rho_r(z) > tau_r,
  tau_r in {0, .05, .1, .2, .3, .5, 1(off)}; give-up as B4 (fixed-tail risk of the chosen continuation > tau_g, same grid);
  same Rc grid. B5 joins the union hull B*; its own CAL winner is sealed as a secondary contrast.
- G3 novelty contrasts become vs B3, B4, B5 (three contrasts, alpha = .05/3 each; P mean cost ratio <= .95, lower saving > 0,
  upper d <= .01). KILL 1 increment clause reads "increment upper CI < 5% vs each of B3, B4, B5".
Implementation owner: Codex (before running stage 1).

## Amendment A2 (2026-10-13, after CAL data, before any stage-1 analysis or TEST data; clarification only)
Quiet validation (decision 5): R_main and R_quiet are both computed on the SAME pre-registered quiet subset (first 200 TEST
frames per cell by frame id), R_main from the main-run t_cum of those frames, R_quiet from the 8-shard re-run; the
|R_quiet - R_main| <= .03 check uses this matched comparison. Full-TEST R is reported alongside. Shuffle anchors for G0 =
/data/guoyikun/tmp/c1apb_smoke (2 frames, 6.5 dB rho .3 L16, all five arms, shuffle on, old entropy; Sonnet closure 0/10
mismatches vs stored out/c1esc). Arm list order for the permutation = E10,E0,E1,E2,E3 (all runs).

## Amendment A3 (2026-10-13, after the seal commit aec90696, before any TEST data; user decision)
Seal outcome: C1 non-operable; P* == B4 in C2/C3 (R = 1), P ~ B* in C4 -> the frozen primary gate (>= 3/4 cells, R <= .85,
CIs) is unreachable by construction; recorded as the primary verdict ("one object" action-value increment not supported at
CAL). User chose a SMALL SCREENING TEST instead of the full TEST:
- TEST frames 600-1599 (n = 1000 per cell, all four cells incl. non-operable C1 for G4), new entropy, 64 shards, shuffled arms,
  out/c1apb_test. Quiet subset: TEST frames 600-699 (100 per cell), 8 shards, out/c1apb_quiet; matched comparison as A2.
- Stage 2 runs on the sealed policies unchanged, labelled SCREENING: report P* vs B* (R, d, CP, Tango, bootstrap) as
  descriptive; practical contrast B4 vs B0 (clock hull) and each class winner vs B0; G3 (P vs B3/B4/B5) and G4 (LOCO Brier,
  Delta-quintile net rescue) as screening evidence. No non-inferiority certification, no PASS claim; n_c planning rule superseded.
