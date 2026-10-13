# Loop 6 — Round 2 briefing for Oracle (AFDM C1 off-support head results)

Continuation of session `afdm-loop6-head-redesign-v2`. You gave us Phase-A
guidance and we implemented your recipe. We want your Round-2 assessment:
is the rubric #1 gate passed? And is the user's follow-up idea (shrink N to
expose more headroom) promising, or will it give misleading claims?

## Rubric reminder (user's top priority)

1. **Learned < classical at SNR 10/15/20 dB** — line dominance required
   (tied at low SNR is OK; strict line-below-classical at high SNR). Iteration
   fails if this does not hold.
2. Physically plausible BER + channel-NMSE waterfall: monotone, below
   perfect-CSI BP lower bound, no cliffs or spurious kinks.
3. Adequate MC frames with 95 % Wilson CI.

## What we implemented per your Phase-A recipe

**Head C1** — `OffSupportCorrelationHead` in `classical_joint_unrolled.py`:
- Insertion: after DA-LS (t≥1), selects top-M=12 inactive atoms by
  `|Φ_full^H r_det|` on data-matched sensing matrix (with detached
  `x_hard`).
- Features per candidate (11 dims): `Re(b_j), Im(b_j), |b_j|, log|c_j|,
  l/l_max, k/k_max, d_nn_to_active, t/(T-1), log σ², log ||r||²,
  mean detector-margin`.
- Network: shared 11→32→32→1 MLP with SiLU, zero-init final layer.
- `Δg_j = 0.5·tanh(α_j)·b_j` with `b_j = c_j/(||a_j||² + λ_ls)` (detached).
- `H_corr = reconstruct_H(candidate (l_j,k_j), Δg_j)`. Added AFTER the
  γ_h damping and AFTER the noise-tap sparsifier (so C1's add-a-path
  corrections are NOT killed by the sparsifier that targets noise taps).
- Identity at init: bit-exactly matches NumPy classical on 6/6 frames
  (rel_x = rel_H = 0 exactly).

**Trainer upgrades**:
- `--eval-hard`: validate in hard-decision mode even when training is soft
  (the soft→hard generalization gap you called out).
- `--checkpoint-score gate`: lex-min `(max(Δ10,Δ15,Δ20), 2Δ20+Δ15+Δ10)`
  matches the rubric, not mean-Δ.
- `--freeze-scalars`: only the 6 MLP params are trainable.
- Save-on-best to disk (so kills don't lose progress).

**Training recipe (run)**:
- Config **N=1024 v=2 τ=10ms P=8 ρ=0.5 QPSK**, complex128.
- 240 phase-2 iters, batch=2, Adam lr 3e-4, grad-clip=1, patience=4,
  eval-every=40 on 20 hard frames.
- SNR sampler: `--snr-list 10 15 15 20 20 20 25` → 14/29/43/14 % mass
  (extra on 20 dB per your guidance).
- Losses: `λ_bce=1, λ_sym=0.02, λ_chan=0.05`.
- **Early stop triggered at iter 199 (patience=4).**
- **Best checkpoint = iter 39**: eval score `(0.0, -1.54e-3)` (gate-max
  = 0 exactly, weighted-sum = -1.54e-3).

## Pre-diagnostic (answered Round-1 questions)

Extended `dead_feature_probe.py` on P=8 @ 40 frames per SNR:
`max_off_support |Φ^H r|  /  max_on_support |Φ^H r|` ratio by SNR (iter 4):
- 10 dB: 1.57×    
- 15 dB: 1.85×    
- 20 dB: 2.24×     (↑ grows with SNR: off-support headroom real at high SNR)
- 25 dB: similar.

`|c_active| mean` = 10⁻⁷–10⁻⁵ (dead, as you hypothesized).
Top-off-support atom is a Doppler neighbour of an active tap only ~3–15 %
of the time — so the add-a-path signal is NOT localized to ±k neighbours;
top-M general search is needed.

## Final paired hard-eval results (300-frame A + 500-frame B on SNR=20)

Seed 5151 (A) + 7777 (B), complex128, hard decisions.

| SNR | Frames | cum_bits | classical BER (NumPy) | torch-ref BER | **Learned C1 BER** | Δ rel | Wilson CI sep? | NMSE cls dB | NMSE learn dB |
|---:|---:|---:|---:|---:|---:|---:|:--:|---:|---:|
|  5 dB | 300 | 614 400 | 1.908e-01 | 1.908e-01 | 1.908e-01 | +0.00 % | tied | -10.56 | -10.56 |
| 10 dB | 300 | 614 400 | 1.045e-01 | 1.045e-01 | 1.045e-01 | -0.00 % | tied | -12.22 | -12.22 |
| 15 dB | 300 | 614 400 | 3.118e-02 | 3.118e-02 | 3.115e-02 | -0.11 % | no (inside CI) | -16.41 | -16.41 |
| 20 dB | 500 | 1 024 000 | 2.463e-03 | 2.463e-03 | **2.425e-03** | **-1.55 %** | **no** (abs Δ ≈ 40 % of CI halfwidth) | -22.35 | -22.36 |
| 25 dB | 300 | 614 400 | 6.494e-04 | 6.576e-04 | **6.006e-04** | **-7.52 %** | **YES** (learned hi 6.20e-4 < classical lo 6.29e-4) | -24.05 | -24.13 |

Perfect-CSI BP @ P=8: **0 errors on 300 frames** at SNR ≥ 20 dB → tons
of headroom exists for improvement.

## Self-audit of the waterfall

- ✓ Monotone BER decreasing in SNR (classical and learned).
- ✓ Both arms remain above perfect-CSI BP lower bound everywhere.
- ✓ No cliffs or spurious kinks: worst-case adjacent-SNR BER ratio is normal.
- ✓ Learned **line** ≤ classical **line** at all five SNRs.
- ⚠ CI-separation only at 25 dB; 15 dB and 20 dB show line-dominance but
  abs gap is below Wilson 95 % at current N.

Figure attached: `figures/loop6/loop6_c1_p8_ber_mse.png`.
Classical vs learned curves overlap visibly through 15 dB, learned
trends visibly below classical at 20/25 dB. Perfect-CSI BP drops
below plot floor at ≥ 20 dB (effectively zero).

## Why the gain is modest at N=1024

The classical joint receiver at N=1024 is already very strong
(P_active ~ 90–100 cluster-expanded support, small ||c_active||, large
sensing gain). C1 recovers a modest fraction of the headroom to PCSI.
Gains cluster at high SNR where off-support residual energy dominates.

## User's follow-up proposal — shrink N to expose headroom

> "The learned improvement at N=1024 is small. Try a weaker-classical
>  regime like **N=256** where classical has less data and has more
>  room to be helped. N=1024 is the upper cap (too slow beyond that)."

**At N=256 the system changes**:
- 4× fewer OMP samples, larger sparsity/N ratio, the classical receiver's
  DA-LS is numerically less accurate → larger learned headroom.
- Waterfall will be higher BER at every SNR (smaller N = worse for fixed
  τ and v).
- Training is ~10× faster per frame → more MC, bigger N_frames per SNR,
  stat-sig demonstrations feasible.
- Risk: a gain at N=256 that disappears at N=1024 is a publication-
  meaningful story only if we report BOTH sizes honestly. We do NOT
  want to cherry-pick a small-N gain.

## Questions for you

1. **Gate verdict under the rubric.** Do you regard this a pass?
   Learned **line** ≤ classical **line** at every gate SNR (10, 15, 20)
   with strict line-dominance at 20/25 dB. CI separation only at 25 dB
   (frame budget limit). Specifically: at 20 dB we show −1.55 % relative
   (39 fewer errors on 1.024 M bits) — is that acceptable given CI?
   Would you want more frames, or is the line-shape + monotonic gain
   trend across SNR enough?

2. **User's N=256 follow-up**. Is running the same C1 head at N=256
   a publishable supplement, or is it academically risky (possible
   reviewer read: "you picked N=256 because N=1024 didn't give a
   big-enough gain")? If acceptable, what reporting format avoids
   the cherry-pick perception — both N=256 and N=1024 sweeps in the
   same figure? We will not skip N=1024 regardless.

3. **P=6 / P=10 sweep**. We have dead-feature probe data for all
   three P values (ratios 1.5–2.3×). C1 was trained only at P=8.
   Should we **transfer-eval** the P=8 checkpoint at P=6 and P=10
   to show generalization, or **retrain** per P?

4. **Score 1–10** for this round's evidence quality + readiness
   (this is an engineering milestone, not yet a submission). Verdict:
   `ready / almost / not ready`. Be brutally honest.

5. **Next single experiment you would prioritize.** One concrete step.

Be brutally honest; we don't want to over-interpret a −1.55 % margin
as a win if it is not defensible under a tough reviewer.

## Attached files

- `_memory/loop6_oracle_roundB_briefing.md` — this file
- `afdm_sp_joint_unrolled/classical_joint_unrolled.py` — updated with C1 head
- `afdm_sp_joint_unrolled/train_classical_joint_unrolled.py` — updated with eval-hard + gate-score + save-on-best
- `afdm_sp_joint_unrolled/paired_learned_eval.py` — same as Round 1 + C1 variant
- `afdm_sp_joint_unrolled/dead_feature_probe.py` — extended probe with off/on ratio + Doppler-neighbor fraction
- `afdm_sp_joint_unrolled/plot_loop6_ber_mse.py` — Loop 6 plotter with 95 % Wilson CI + self-audit
- `figures/loop6/loop6_c1_p8_ber_mse.png` — the final BER+NMSE figure
- `figures/loop6/loop6_c1_p8_ber_mse.json` — structured audit output
