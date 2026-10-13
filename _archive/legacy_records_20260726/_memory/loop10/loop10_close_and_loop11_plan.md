# Loop 10 close + Loop 11 plan

Date: 2026-04-23 00:35 CST
Source: Oracle R2 (9/10 close v2) + Oracle R2-followup-visibility.

## Loop 10 close

- **Ship**: `v2` — P=10 Loop-9 ckpt cross-applied at P=8 + force-topk + per-SNR `tau-lookup {30:999}` + short-circuit at tau ≥ 100.
- **Headline figure**: `figures/loop10/tau30cutoff_official_v2.png`
- **Headline claim**: "ranking-informed support augmentation with SNR-adaptive commit calibration; head trained in harder P=10 regime transfers to P=8 when commit aggressiveness is calibrated by SNR. Stat-sig BER reduction vs torch-ref at SNR ∈ {20, 25, 30}: −14.4 % (p=1.5e−19), −11.4 % (p=2.7e−8), −14.7 % (p=8.4e−11)."
- **Honest limitation**: visible gap in log waterfall is ~0.3–0.5 dB SNR-shift at SNR ≥ 20. Stat-sig but not "visibly separated" in the way a typical comm paper's 1–2 dB shift is.
- **Decisions ruled out** this loop:
  - Variant A (P=8 retrain) — lost at SNR=25 (Oracle H2: logit-range / bias calibration mismatch).
  - F1 alone (no-prune) — WORSE than v2 (support pollution, SNR=30 regress +42 %). Prune-by-|gain| was doing real work.

## Loop 11 plan (from Oracle)

**Target**: ≥ 1 dB visible shift at SNR=20/25 (20 % absolute BER ratio ≤ 0.75 at SNR=20, ≤ 0.70 at SNR=25). 2 dB at P=8 acknowledged as unlikely.

### R1 — fast screen (budget: 1 day)
Configs to run at SNR={20, 25} only (~100 frames each, 800-err adaptive stop):
1. **F1** — no-prune (already have smoke: null)
2. **F2** — multi-round refinement (`--refine-rounds 2`): re-trigger C2-rel on DA-LS residual at iter 1, update support, redo DA-LS. NEW CODE.
3. **F1 + F2** — no-prune + refinement together.
4. **P=10 backup** — F1+F2 at P=10 as parallel sanity.

Gate: promote if learned/classical ≤ 0.75 at SNR=20 OR ≤ 0.70 at SNR=25, monotone waterfall, no low-SNR regression.

### R2 — medium sweep on survivors
- Full 5 SNRs {10,15,20,25,30}, 200-f cap, `--with-pcsi`.
- If P=8 misses, add tau=15 ms (harder channel, same P).
- Gate: ≥ 0.2 decades log-BER gap at SNR=20 or 25 (≈ 1 dB visually), McNemar stat-sig, no high-SNR regression vs torch-ref.

### R3 — official long run on best survivor.

### Hard stop rule
- If best P=8 config still has < 40 % BER reduction at both SNR=20 AND SNR=25 after R2 → stop selling "1–2 dB at P=8". Pivot to either:
  - **Harder-regime story** (tau=15 ms or v=3; frame as stress test not visual shift), or
  - **F3 learned swap** (12–20 h implementation; replaces prune-by-|gain| heuristic with trained head).

### Not this loop
- F4 (BP-differentiable BER fine-tune): 20 h+ and unstable. Keep for Loop 12 if needed.
- F5 (LISTA / learned OMP): major redesign, out of scope.

## Concrete next action (already coded)

- `--no-prune` flag: done, smoke-tested (alone: hurt, so needed WITH F2).
- `--refine-rounds N` flag: **NOT YET implemented**. Loop-11 R1 requires this new code.
  - Change site: `classical_joint_unrolled.py:1348` area — after DA-LS iter 1 completes, re-enter cand_active_rel forward with updated `support_idx` + `g_ls_new` from DA-LS; rescore; re-propose adds; redo support union / prune / refit.
  - Est. code time: 2 h + 30 min testing.
- Plot: `--no-prune` smoke figure done; need a comparison plot that overlays v2, F1, F2 once F2 runs.
