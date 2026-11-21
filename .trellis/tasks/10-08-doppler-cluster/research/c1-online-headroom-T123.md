# T1-T3: does online per-frame scheduling (A') have headroom, and is a scalar state sufficient (A)? (2026-10-13, FROZEN before analysis)

Purpose: settle the empirical part of the Claude/Codex disagreement (codex-direction-r2-20261013.md, P2 and answer 7) with
zero new simulation. Analysis-only script `experiments/headroom_ladder_20261008/c1on_analyze.py`. Development evidence, one
condition; not a confirmation.

## Data (stored, paired frames 0-299, 6.5 dB, rho .3, SPg_flat genie delays, K = 8L)
- T20, 10 rounds: `out/c1g_r10lo` (L16, L20) + `out/c1f_r10` (L24, L28, L32), arm FULL_R10.
- T40, 10 rounds: `out/c1ib2_r10` (L16-L32), arm R10T40.
- Per-round fields: ierr<r>, syn<r> (syndrome weight; 0 = valid codeword), ll_in<r> (logloss of the round-r decoder-input LLR).
- Cost: C_T(L, r) = mean over the quiet timing reference `out/c1ib2_time` (arms R10T20/R10T40, frames 0-9) of t_cum[r-1] at that
  (T, L): receiver-clock seconds through round r incl. pilot front. Secondary unit (robustness): inner updates r*T.

## T1: oracle headroom of online scheduling (upper bound for A')
- Syndrome early stop: r_s = first r with syn_r = 0. Fixed family F = {(T, Rc): T in {20, 40}, Rc in 1..10}: stop at
  min(r_s, Rc); frame fails if ierr at the stop round > 0. Cost per frame = C_T(L, stop round).
- Best fixed at L = cheapest member of F with FER <= delta = .10 ("operable L"); none -> L not operable (reported).
- Oracle: each frame takes the cheapest member under which it succeeds; frames failing under all members are given up after
  round 1 at min_T C_T(L, 1). Matched-FER oracle: also give up the most expensive successful frames (cost min_T C_T(L, 1))
  until its FER equals the best-fixed FER.
- S1(L) = 1 - mean cost(matched oracle)/mean cost(best fixed); frame bootstrap 95% CI (B = 1000, best fixed re-selected per
  resample).
- Decision: if S1 < .15 at every operable L -> A' cannot pass the G2-A' gate (15% saving) even with an oracle -> A-first.
  Otherwise -> T2 decides.

## T2: realisable saving with a deployable give-up rule
- Base = best fixed (T*, Rc*) at L. Rule: at the end of round r_g < Rc*, a frame not yet stopped with syn_{r_g} > theta is given
  up (counted as failure; cost C_T*(L, r_g)). r_g in {1, ..., min(4, Rc* - 1)}, theta over the observed syndrome values.
- Select (r_g, theta) on frames 0-149 maximising saving with FER increase <= .01 (absolute); evaluate on frames 150-299.
- Decision (at an L where T1 passed): test saving >= .15 with test FER increase <= .01 -> A' deployable-viable (A'-first
  candidate). Else -> A-first; A' stays a conditional later extension. Report-only: AUC of syn_r (r = 1..4) for final failure.

## T3: scalar-state sufficiency (offline, uses truth; G0-style)
- Samples: (T, L, frame, r), r = 1..9, frame not stopped at rounds <= r. Target y = 1{ierr_{r+1} = 0}.
  I_r = 1 - ll_in_r (bits). Condition variable k = K/256.
- M0 (scalar state + condition): logistic on [1, I, I^2, k, I k]. M1 = M0 + history [dI = I_r - I_{r-1} (0 at r = 1), r,
  log(1 + syn_r)]. Per T; 2-fold by frame (0-149 / 150-299); held-out mean log-loss (nats).
- Delta = LL(M0) - LL(M1). Decision: Delta >= .02 in both folds for both T -> scalar state insufficient (A needs >= 2 states,
  Codex's caution holds); Delta < .005 in both folds for both T -> scalar state suffices at this condition; otherwise
  inconclusive. Drop-one report of which history feature carries Delta.

## Limits (stated before results)
One condition (6.5 dB, rho .3); costs from a 10-frame reference per (T, L); the oracle uses the realised outcomes of the same
frames (upper bound by construction); the fixed family covers T in {20, 40} only; 150/150 frame split is small, so T2 numbers
are indicative. No claim beyond go/no-go for the next development step.

## Results (2026-10-13; out/c1on/analysis/on.md, frozen script commit 272094cc)
- T1: only L16 (K 128) operable at FER <= .10 (best fixed T40, Rc 7, FER .097, .698 s). Matched-FER oracle S1 = .337
  [.282, .377] (unit r*T: .460) -> go to T2.
- T2: deployable rule "give up after round 1 if syndrome weight > 264": dev saving .158 (dFER +.007), test saving .111
  (dFER .000) < .15 -> **A-first** by the frozen rule. Syndrome weight discriminates eventual failure well (AUC .96-.98, r 1-4).
- T3: Delta = +.034/+.046 (T20), +.037/+.027 (T40), all >= .02 -> **scalar state insufficient**. The history signal is carried
  by the round index (drop-one +.021 to +.036), not by dI or syndrome -> consistent with per-frame heterogeneity (frames still
  undecoded late are harder at the same I); the second state is deployable (elapsed rounds).
- Post hoc (out/c1on/analysis/posthoc_decomposition.md, not a decision input): of the 34% oracle headroom ~20 points are
  give-up/round cap at fixed T40, ~14 need per-frame T choice; a T-switching policy needs new runs.
- Disagreement status: P2 (online vs offline priority) -> Codex ordering supported (A first; A' conditional, its untested
  part is adaptive T). Answer 7 (same I, different history) -> history matters (round index); Codex caution confirmed.
  Scope: one condition, one operable load; development evidence.
