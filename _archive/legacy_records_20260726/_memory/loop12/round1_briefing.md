# Loop 12 — Round 1 Plan Briefing (Oracle GPT-5.4-pro, browser)

## Context

Loop 11 closed 2026-04-23 with Oracle R2 score **8.2/10, verdict "almost"**.
Key Loop-11 R1 F2-P result (full 5-SNR, 80–200 frames, adaptive McNemar):

| SNR | frames | cls BER | learned BER | Δ vs cls | visible dB | McNemar p |
|---:|---:|---:|---:|---:|---:|---:|
| 10 | 80  | 9.95e-2 | 9.73e-2 | −2.23 %  | 0.10 | 1.4e-9  |
| 15 | 80  | 2.90e-2 | 2.68e-2 | −7.42 %  | 0.34 | 5.3e-24 |
| 20 | 80  | 2.95e-3 | 2.23e-3 | −24.4 %  | **1.21** | 7.6e-14 |
| 25 | 178 | 1.10e-3 | 3.65e-4 | −66.8 %  | **4.79** | 2.0e-58 |
| 30 | 200 | 4.47e-4 | 2.10e-4 | −53.0 %  | **3.28** | 1.8e-18 |

Audit H1–H4 all PASS (monotone, ≤ PCSI, no cliff).

## Oracle R2 explicit open items (Loop-12 carry-over)

1. **R3 official long**: all 5 SNRs, min-frames 200 (250 preferred @ 20 dB),
   target-errors 800, max 500-frame cap. Seed 20260423.
2. **Seed-2 reproducibility** at SNR ∈ {20, 25} — minimum; full sweep better.
3. **Classical-ablation**: same `--refine-rounds 2 --defer-prune-until-final
   --protect-added 2` skeleton with classical-only scoring (turn off learned
   head) — attribute gain to learned vs F2-P mechanics.
4. **Frame-level paired bootstrap CI** alongside bit-level McNemar — weakness (c).

## User Loop-12 rubric

- **BER/MSE waterfall must look normal**: monotone, below PCSI, learned ≤
  classical at high SNR, no cliffs / sudden reversals / step-jumps of
  10–100× at a single SNR.
- **GPU parallel**: 4090 has ~21 GB free (~15 GB usable). Must exploit.
- **Reviewer = `oracle --engine browser`** (NOT codex MCP).
- **Banner/print N, v, P, tau** every run — verify the right config is used.
- **Monte-Carlo frame count** appropriate w/ CI; not too small, not too big.
- **Lines matter**: full BER/MSE waterfall shape must look right — not just
  point-wise p-values.
- **P10-ckpt-on-P8 mystery**: user asks — why does the P=10-trained ckpt
  work better on P=8 than the P=8-retrained ckpt? Answer with evidence.
- **BP torch vs numpy**: numpy BP verified bit-exact vs torch BP at Loop-5
  (400 frames). Use torch exclusively; skip numpy unless torch arm shows
  something suspicious.

## Pre-gathered evidence for the P10-vs-P8 question

A) P=10 ckpt (`outputs_loop9_c2rel_train/ckpt_c2rel_force_topk.pt`):
   - Trained on P=10 cache (12k frames/SNR @ 10/15/20 dB).
   - Val `recall@6 = 0.893` at best epoch.
   - Loop-10 v2 tau-cutoff eval at P=8 (no F2-P): SNR=20 −14.4 %, 25 −11.4 %,
     30 −14.7 % (all stat-sig, user rubric PASS).
   - Loop-11 F2-P eval at P=8: SNR=20 −24.4 %, 25 −66.8 %, 30 −53.0 %.

B) P=8 retrained ckpt (`outputs_loop10_c2rel_train_p8/ckpt_c2rel_force_topk.pt`):
   - Trained on P=8 cache (12k frames/SNR @ 10/15/20 dB, same recipe).
   - Val `recall@6 = 0.909` — **higher** than P=10 ckpt.
   - Loop-10 tau-cutoff eval at P=8 (no F2-P, `outputs_loop10_p8retrain_tau30cutoff`):
     SNR=20 −14.23 %, 25 **−3.50 %** (vs P10 ckpt's −11.4 %, WORSE),
     30 **+8.99 %** (REGRESSION; P10 ckpt was −14.7 % GAIN).

**Apparent finding**: at the same protocol, the **P=8-retrained ckpt is
STRICTLY WORSE** at SNR ∈ {25, 30} despite higher val recall@6 (0.909 vs
0.893). The gap is largest at SNR=30 (+8.99 % vs −14.7 %), where the
classical detector is already near PCSI and any wrong add hurts.

**Working hypothesis (to validate in Loop 12)**:
- Training on the **harder P=10 distribution** acts as a regularizer → the
  ranker learns a **more conservative** atom-selection threshold.
- When cross-applied at the easier P=8 distribution, the conservative
  ranker adds fewer wrong atoms at SNR=30 (where classical is near PCSI
  and any wrong add is costly).
- P=8 retrain gets higher recall@6 (proxy) but **worse BER** because the
  proxy doesn't penalize "confidently adds a wrong atom when the ground
  truth is already found" — which is exactly what hurts at SNR=30.

**Validation planned**: run the P=8-retrained ckpt under F2-P (same
protocol as Loop-11 R1) at SNR {20, 25, 30}. Currently launched in
background tmux `g_loop12_p8f2p`. If P=8-retrain under F2-P still
underperforms P=10-under-F2-P → hypothesis confirmed.

## Loop-12 plan (pending Oracle R1 approval)

### Step 1 — R3 official long (headline)

```
python -m afdm_sp_joint_unrolled.paired_learned_eval \
    --variant C2-rel --mp-mode bp --pic-damp 0.5 --p-paths 8 --tau-ms 10.0 \
    --n-total 1024 --v-mean 2.0 --snr-list 10 15 20 25 30 \
    --frames-per-snr 500 --target-errors 800 --min-frames 200 \
    --seed 20260423 --cdtype complex64 --use-hard --with-pcsi \
    --ckpt outputs_loop9_c2rel_train/ckpt_c2rel_force_topk.pt \
    --refine-rounds 2 --cand-topm 96 --defer-prune-until-final --protect-added 2 \
    --out outputs_loop12_r3_official
```

Per-SNR estimated frames:
- 10 dB: 200 (early-stop easy)
- 15 dB: 200 (early-stop easy)
- 20 dB: ~250–300 (Oracle preferred floor)
- 25 dB: up to 500 (target-errors 800 drives it)
- 30 dB: cap at 500

Expected wall: ~45–60 min on shared RTX 4090 (Loop-11 R1 was 16 min for
80–200 frames).

### Step 2 — Seed-2 @ SNR {20, 25}

Same config, `--seed 20260424 --snr-list 20 25`, output
`outputs_loop12_seed2_s20_s25`. Verify deltas stay inside Loop-11 R1 CI.

### Step 3 — Classical-ablation at SNR {20, 25, 30}

Option A: set `--tau-lookup 20:100,25:100,30:100` — forces learned head's
commit threshold above max(logits) → no learned adds, but F2-P mechanics
(refine 2 + defer prune + protect-added) still active.

Actually `--protect-added 2` is a no-op when no adds → need
`--protect-added 0` so F2-P's "protect top-r learned picks" doesn't
evict real OMP picks. Effectively this strips F2-P to "refine 2 rounds
of classical scoring + defer prune", which is the cleanest attribution
test.

```
python -m afdm_sp_joint_unrolled.paired_learned_eval \
    --variant C2-rel --mp-mode bp --pic-damp 0.5 --p-paths 8 --tau-ms 10.0 \
    --n-total 1024 --v-mean 2.0 --snr-list 20 25 30 \
    --frames-per-snr 300 --target-errors 400 --min-frames 150 \
    --seed 20260423 --cdtype complex64 --use-hard --with-pcsi \
    --ckpt outputs_loop9_c2rel_train/ckpt_c2rel_force_topk.pt \
    --tau-lookup 20:100,25:100,30:100 \
    --refine-rounds 2 --cand-topm 96 --defer-prune-until-final --protect-added 0 \
    --out outputs_loop12_classical_ablation
```

### Step 4 — Frame-level bootstrap CI

After R3 completes, write `afdm_sp_joint_unrolled/_loop12_frame_bootstrap.py`
that reads paired per-frame error counts from `results.json` and computes
95 % paired percentile bootstrap CI on Δ(learned − classical) at each SNR
(10 000 resamples). Append to final R3 table.

### Step 5 — Audit + figure

Run `_loop11_audit.py` on R3 results → hard checks H1–H4 + soft warnings.
Generate `figures/loop12/loop12_final_ber_mse.png` (2-panel: BER + NMSE,
log-scale, PCSI upper/lower bound shaded).

## Questions for Oracle R1

1. Is the plan complete? Any missing validation (e.g., seed-2 on full
   sweep instead of just 20/25)?
2. Is the P10-vs-P8 hypothesis (train-on-harder regularization + proxy
   metric saturation at P=8) a reasonable diagnosis? How should I
   validate it?
3. For the R3 long run: is `min-frames 200` good enough for 20 dB, or
   should I raise it to 250/300 selectively? Frame budget.
4. For the classical-ablation, is `--tau-lookup 20:100,25:100,30:100
   --protect-added 0` the right way to strip the learned head while
   keeping F2-P mechanics? Or should I also disable refine-rounds (just
   test "mechanics without learned scorer" is the goal).
5. Is there any remaining blind spot that could blow up at submission
   time even if R3 passes?
6. Forecast: what score would R3 + seed-2 + classical-ablation at the
   levels I'm expecting earn vs an 8.5 (ready) vs 9.0 threshold?

Please answer with concrete dB/% floors and a go/no-go call on each sub-step.
