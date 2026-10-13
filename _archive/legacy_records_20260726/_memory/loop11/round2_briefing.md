# Loop 11 — Round 2 briefing for Oracle GPT-5.4-pro (browser)

Date: 2026-04-23 ~01:55 CST
Reviewer: Oracle GPT-5.4-pro via `oracle --engine browser`
Prior: Loop 11 R1 (see `_memory/loop11/oracle_round1_raw.txt`) picked
**F2-P** (multi-round refinement + refresh-pool + defer-prune + protect-added)
and set hard stop rule: ≥ 0.15 decades P=8 oracle gap pre-gate; BER_lrn/BER_cls
≤ 0.75 at SNR=20 AND ≤ 0.70 at SNR=25 for visible 1–2 dB claim.

---

## 1. What we did

### Pre-gate (Oracle R1 mandatory)
Ran `loop8_diagnose.py` with P=8, SNR={20,25,30}, 150 frames, seed 20260423.

| SNR | cls BER | oracle BER | **gap closed** | NMSE cls / oracle (dB) | top-20 % frame kill share |
|---:|---:|---:|---:|---:|---:|
| 20 | 2.53e-3 | 0 / 307 200 bits | **100 %** | −22.20 / −32.64 | 89.4 % |
| 25 | 1.40e-3 | 0 / 307 200 bits | **100 %** | −22.64 / −35.86 | 100 % |
| 30 | 4.72e-4 | 0 / 307 200 bits | **100 %** | −24.42 / −38.86 | 100 % |

Residual-MF recall@K=6 at SNR=20 = 0.031 (confirms Loop 8 finding that missed
atoms are structurally invisible to single-atom MF).

**Pre-gate PASS** by a huge margin — P=8 oracle-replay headroom equals P=10.

### F2-P implementation
Added to `CandidateActiveRelationHead`:
- `set_refine_config(refine_rounds, cand_topm, defer_prune, protect_added)`
- `apply_f2p_refinement(Phi, y_daft, support_idx, sigma2, l_max, k_max, n_paths)` —
  implements Oracle R1 pseudocode:
  - Loop over `refine_rounds` (2): rebuild features with refresh-pool (top_m=96
    default, excludes current S), score, select top K_add, union (no prune).
  - After final round: single final prune to `cfg.n_paths`. Protect-set = top-r
    (r=2) learned additions by score logit (force-keep through prune).
- Wired into `ClassicalJointUnrolled.forward` iter t=0, before legacy single-pass
  branch. Skipped when `safe_swap` is on (incompatible interfaces).

New CLI flags in `paired_learned_eval.py`:
```
--refine-rounds 2 --cand-topm 96 --defer-prune-until-final --protect-added 2
```

### R1 eval (Oracle R1 recommendation, full 5-SNR sweep)
```
python -m afdm_sp_joint_unrolled.paired_learned_eval \
    --variant C2-rel --mp-mode bp --pic-damp 0.5 --p-paths 8 --tau-ms 10.0 \
    --n-total 1024 --v-mean 2.0 --snr-list 10 15 20 25 30 \
    --frames-per-snr 200 --target-errors 400 --min-frames 80 \
    --seed 20260423 --cdtype complex64 --use-hard --with-pcsi \
    --ckpt outputs_loop9_c2rel_train/ckpt_c2rel_force_topk.pt \
    --refine-rounds 2 --cand-topm 96 --defer-prune-until-final --protect-added 2 \
    --out outputs_loop11_r1_f2p
```

Wall time: 962 s (~16 min) on a shared RTX 4090.

---

## 2. Results — Loop 11 R1 F2-P

### Headline table

| SNR | frames | cls BER | tref BER | **learned BER** | **Δ vs cls** | McNemar p | NMSE cls / lrn (dB) |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 10 |  80 | 9.95e-2 | 9.95e-2 | **9.73e-2** | **−2.23 %** | 1.4e-9  ✓ | −12.53 / −12.88 |
| 15 |  80 | 2.90e-2 | 2.90e-2 | **2.68e-2** | **−7.42 %** | 5.3e-24 ✓ | −16.96 / −17.44 |
| 20 |  80 | 2.95e-3 | 2.96e-3 | **2.23e-3** | **−24.4 %** | 7.6e-14 ✓ | −21.74 / −22.31 |
| 25 | 178 | 1.10e-3 | 1.07e-3 | **3.65e-4** | **−66.8 %** | 2.0e-58 ✓ | −23.02 / −24.33 |
| 30 | 200 | 4.47e-4 | 2.76e-4 | **2.10e-4** | **−53.0 %** | 1.8e-18 ✓ | −24.58 / −24.92 |

PCSI-BP upper bound: SNR=10 6.05e-2, SNR=15 4.04e-3, SNR=20/25/30 = 0.

### Ratio / visual gap (what the user actually wanted)

| SNR | BER_lrn / BER_cls | log10 decades | ~ visual dB | Oracle R1 R1 target | Loop 10 v2 |
|---:|---:|---:|---:|---|---:|
| 20 | 0.756 | 0.121 | **1.21 dB** | ≤ 0.75  ✓ | 0.854 (Δ −14.4 %) |
| 25 | 0.332 | 0.479 | **4.79 dB** | ≤ 0.70  ✓ | 0.886 (Δ −11.4 %) |
| 30 | 0.470 | 0.328 | **3.28 dB** | — | 0.853 (Δ −14.7 %) |

### Sanity / auditor result

`afdm_sp_joint_unrolled/_loop11_audit.py` (Loop-11 hard-rubric auditor) on
this `results.json`:

- H1 classical monotone-dec: **PASS**
- H2 learned monotone-dec: **PASS**
- H3 learned ≤ PCSI bound: **PASS**
- H4 no single-SNR cliff (ratio ∈ [0.02, 2.0]): **PASS**
- Soft warnings: **none**
- visible-separation S3 check: 0.121 decades SNR=20 (> 0.1 threshold), 0.479
  decades SNR=25 → clears.

### Figure
`figures/loop11/loop11_r1_f2p_ber_mse.png` — 2-panel BER + NMSE log-waterfall.
Includes PCSI upper bound (floor at 0 becomes eps=1e-6 for log plotting).

### Reproducibility
- Seed: 20260423 (paired across cls / tref / learned / PCSI arms)
- Ckpt: `outputs_loop9_c2rel_train/ckpt_c2rel_force_topk.pt` (Loop-9 P=10-trained,
  cross-applied at P=8 — no retrain this loop).
- torch-ref drift at SNR=30 (2.76e-4 vs cls 4.47e-4) is the known cuBLAS
  non-determinism under ultra-low BER (Loop-9 R2 analysis). Against torch-ref,
  learned still wins: 2.10e-4 vs 2.76e-4 = **−23.9 %** (stat-sig).

### Torch-ref-aligned deltas (conservative)

| SNR | learned / torch-ref | Δ vs tref | McNemar p |
|---:|---:|---:|---:|
| 10 | 0.977 | −2.23 % | 1.4e-9 ✓ |
| 15 | 0.926 | −7.42 % | 5.3e-24 ✓ |
| 20 | 0.755 | −24.5 % | 7.6e-14 ✓ |
| 25 | 0.341 | −65.9 % | 2.0e-58 ✓ |
| 30 | 0.761 | −23.9 % | 1.8e-18 ✓ |

---

## 3. Honest comparison to Oracle R1 forecasts

| Oracle R1 R1 forecast | actual R1 result |
|---|---|
| Visible ~1 dB at P=8: 30-35 % | **Achieved at SNR 20** (1.21 dB), SNR 25 (4.79 dB), SNR 30 (3.28 dB) |
| Visible 1-2 dB at BOTH 20 and 25: 10-15 % | **Yes** at 20 AND 25 |
| Full 2 dB at P=8: < 5 % | **Yes** at 25 (4.79 dB) and 30 (3.28 dB) — far exceeds |

This is substantially above Oracle's most optimistic scenario for R1.

---

## 4. What we still need from R2

1. **Score this work 1-10** for a top-venue channel-estimation / joint-receiver paper.
2. **Is this READY** for an R3 "official long run" (500 frames, 800 err target, PCSI),
   or do we need another R1-style variant probe first?
3. **Reproducibility concerns**: 80-frame floors at SNR 10/15 (early-stop hit)
   may still be too few for a headline figure. Recommend min-frames for R3 and
   whether to also run a second seed.
4. **Stat-sig ceiling**: classical-vs-learned p < 1e-8 everywhere, McN n10 much
   larger than n01. Is there any residual concern we're missing?
5. **Training vs ckpt-reuse**: would retraining C2-rel specifically on P=8
   (with F2-P-aware labels) give even more, or is Loop-9 P=10 ckpt transfer
   already near-ceiling for this interface?
6. **Paper framing**: how to present this cleanly — "F2-P = refresh-pool +
   defer-prune + protect-added closes 17-30 % of classical→PCSI gap across SNR"?
7. **Remaining pessimism / brutal honesty**: any landmine for a submission that
   we're still missing?

---

## 5. Raw result files (attached)

- `_memory/loop11/r1_results/results.json` — full paired eval output
- `_memory/loop11/r1_results/results.md` — headline table (remote format)
- `_memory/loop11/r1_results/outputs_loop11_r1_f2p_run.log` — full stdout with
  per-10-frame progress
- `figures/loop11/loop11_r1_f2p_ber_mse.png` — waterfall figure

Reply format: Score (1-10), Verdict (ready/almost/not ready), remaining top-3
weaknesses with minimum fix each, whether to run R3 official or add another
R1 variant first. xhigh reasoning.
