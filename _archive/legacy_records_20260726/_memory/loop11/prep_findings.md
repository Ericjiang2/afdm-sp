# Loop 11 — pre-Oracle prep findings (waiting for R1)

Date: 2026-04-23 ~01:10 CST
Status: Oracle R1 (browser) running in background; nothing implemented yet on
the method side per user instruction. Below are infra/profile findings only.

## 1. GPU state on deinlab (just before R1)

```
NVIDIA GeForce RTX 4090, 24564 MiB total, 4618 MiB used, 19464 MiB free, util 9 %
Active processes:
  pid 1605187 / wangruichang  python  512 MiB
  pid 1605530 / wangruichang  python  512 MiB
  pid 1605992 / wangruichang  python  512 MiB
  + 3 zombie / orphan procs at 1006-1008 MiB each (no resident PID name)
```

So ~19 GB free, util 9 %. Comfortably room for **5 parallel SNR processes**
(profile below estimates ~2.5 GB / process ⇒ 12.5 GB total, well under 19 GB).

## 2. Single-frame BP-joint profile (N=1024 P=8 SNR=20, no learned heads)

Script: `afdm_sp_joint_unrolled/_loop11_profile.py`
Result on RTX 4090, complex64, 20 frames after 2 warm-up:

| metric | value |
|---|---|
| mean / frame | **0.673 s** |
| median | 0.678 s |
| p90 | 0.735 s |
| p99 | 0.770 s |
| frames / min / SNR | **89** |

A 5-SNR sweep at 100 frames serial = ~5.6 minutes single-arm. The full
`paired_learned_eval.py` runs three torch arms (cls-NumPy + tref + lrn) plus
optional PCSI; observed end-to-end ~30 frames/min/SNR matches user's "感觉慢".

## 3. torch.compile() — does NOT work out of the box

Tested `torch.compile(mode="reduce-overhead", dynamic=True)` on the full
`ClassicalJointUnrolled.forward`:

```
BackendCompilerFailed: backend='inductor' raised:
RuntimeError: self.dim() cannot be 0 to view ComplexFloat as Float
While executing zeros_like(g) + g
File: classical_joint_unrolled.py:358 in expand_cluster_support
```

Inductor cannot lower `torch.zeros_like(g) + g` when `g` is a 0-dim complex
tensor. Would require refactoring `expand_cluster_support` to scalar-pad path.
**Not a safe one-line fix**. Drop torch.compile from the speedup options
unless we want to invest in module rewrites.

## 4. 4090 speedup ranked (pre-Oracle)

| option | risk | speedup ceiling | code time | notes |
|---|---|---|---|---|
| **multi-process parallel SNR** | low | **5x** on multi-SNR sweeps | 1 h | Each SNR is independent. ~2.5 GB × 5 = 12.5 GB < 19 GB free. Use Bash `&` + `wait` or a tiny Python launcher. **Recommended**. |
| **process-pool over (variant × SNR) grid** | low | up to 5–10x for R1 fast screen | 1.5 h | Same as above plus variant axis (baseline / F1 / F2 / F1+F2). |
| **torch.compile** | high | 1.5–2x if compiles | 4–8 h refactor | Fails on `expand_cluster_support` complex zero-dim view; not pursuing. |
| **CUDA graphs** | high | 1.5x | days | OMP has data-dependent control flow; no fixed shapes. Not pursuing. |
| **fp32 → bf16 / fp16 in BP** | high | 1.3–1.5x | 2 h + heavy verify | BP convergence + LS solve sensitivity unknown. Defer to Loop 12. |
| **cache `Phi_pilot` per channel realization** | low | <5 % | 1 h | Phi changes per frame (different channel + same pilot). No reuse window. |
| **batch frames into one tensor (B-dim)** | high | up to 4x | 1+ day | Invasive; OMP iter count varies per frame; would need padded-mask. Defer. |

**Pre-recommendation to Oracle**: implement multi-process parallel SNR (item 1)
as the only Loop-11 speedup. Wait for Oracle to confirm and rank against any
alternatives we haven't thought of.

## 5. Sanity auditor built and validated

Script: `afdm_sp_joint_unrolled/_loop11_audit.py`
Hard checks (red): monotone classical/learned BER, learned ≤ PCSI bound, no
single-SNR cliff (>2× rise or >50× drop between neighbours).
Soft checks (yellow): min frames/SNR, classical err count ≥ 50, decades-gap
visibility at SNR=20/25, no low-SNR regression.

Validation on Loop-10 v2 baseline (`outputs_loop10_tau30cutoff_official_v2/results.json`):
- Hard: ✅ PASS.
- Soft: only 0.069 decades (≈ 0.69 dB visual) at SNR=20, < 0.1 threshold.
- This *exactly* reproduces user's reason for rejecting Loop-10 v2 figure.

This auditor will be invoked on every Loop-11 result before showing the user a
figure. Output is plain-English and exits non-zero on hard fail.

## 6. Adaptive early-stop already in place

`paired_learned_eval.py`:
- `--target-errors N` adaptive eval stop (per SNR, after `--min-frames` floor).
  Default 0 (off). Loop-10 v2 used 800. Loop 11 will use **400** per user
  rubric ("200–500 err bits"), with `--min-frames 30` floor and `--max-frames`
  cap from Oracle's CLI sketch.
- Already supports `--with-pcsi` for paired upper-bound arm.

Training (`loop9_train_c2rel.py`):
- `--patience N` already implemented (default 2). Track val BCE; early stop on
  flat. Will keep this for any Loop-11 retrain.

## 7. Available ckpts

- Loop-9 P=10 force-topk ckpt: `outputs_loop9_c2rel_train/ckpt_c2rel_force_topk.pt`
  (the one Loop-10 v2 cross-applied — already has 14 % rel BER reduction at
  SNR=20).

## 8. Reproducibility

Fixed seeds across all Loop-11 runs:
- Master eval seed: `--seed 20260423` (today)
- Per-SNR frame seeds derived from master (pairs cls/tref/learned/PCSI per frame).

## 9. Next decision point

When Oracle R1 returns:
- If picks F2 / F1+F2: implement at `classical_joint_unrolled.py:1340` outer-iter
  loop (re-trigger C2-rel after DA-LS at iter t≥1 with data-aided residual).
- If picks divergent option (e.g., heavy-tail frame detector, learned support
  swap): plan from scratch.
- Either way: deploy via multi-process parallel SNR launcher (item 4 above).

## 10. Open questions for Oracle (already in R1 briefing)

(repeated here for self-reference, full text in `round1_briefing.md`)
1. Score of existing F1/F2/F1+F2/P=10 plan, posterior of visible 1–2 dB.
2. **Divergent**: 5+ mechanistic reasons learned can't capture oracle replay.
3. Which 1–2 to implement this loop.
4. **4090 speedups**: confirm parallel-SNR is the right call; suggest others.
5. Adaptive cap: confirm 400 err bits is OK, suggest patience numbers.
6. Hard-stop pivot threshold for "1–2 dB at P=8 impossible".
7. Anything we're missing.
