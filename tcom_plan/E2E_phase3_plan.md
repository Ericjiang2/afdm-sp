# E2E Phase 3 — push past Path F 5% BER via training-layer tricks

**Date**: 2026-05-13
**Status**: in-flight (Path G launched on `deinlab:g_path_g`, ETA ~2.5h)
**Context**: User pushback "5% BER 看 OTFS-SP 文献那么好感觉太高了" triggered triple parallel literature search. Key findings drive Phase 3 design.

## Literature reality check (most important finding)

User's premise that "OTFS-SP E2E 那么好" is **not supported by the actual literature**:

- **Lei et al. 2026** (arXiv 2601.22523, "Superimposed-Pilot OTFS Under Fractional Doppler: Modular E2E Learning"): explicitly quote that classical OMP-SP-OTFS **"saturates around 3×10⁻²" BER** — that's the OMP ceiling for the entire OTFS-SP family. The 3% floor is the field's reality, not 1e-4.
- All OTFS-SP E2E papers (Singh 2025, Tian 2025, Naikoti & Chockalingam, Mishra/Yuan) publish only **qualitative curves** approaching "perfect CSI"; none tabulate < 1e-2 BER numbers at typical SNRs. The "close-to-perfect" framing is visual, not numerical.
- OTFS-SP literature uses **N=8 to N=20** grids (we use N=1024 → 50-100× larger). Apples-to-oranges.
- Most OTFS-SP papers also use **fixed-SNR** training; we use **multi-SNR uniform 15/20/25 dB** (harder generalisation regime).

→ Our **Path F BER 0.0498 is in-band with OTFS-SP literature**, not embarrassingly worse. The visual gap user perceived comes from comparing against our own exceptionally strong B+ classical baseline (~0% BER from iter=10 classical OMP + MP-BP + B+ multi-component head + learned candidate rerank), not from comparing against published OTFS-SP E2E numbers.

## Three directions evaluated (parallel literature scan)

### A. Beyond-LISTA architectures (Direction-4 winner from scan)
**Softsort-OMP / LGM-style hybrid** (arXiv 2505.15661, Cohen 2021 LGM): hard top-k at inference + softsort relaxation at train. Mechanistically targets our K=20 collapse (soft-sigmoid support drift at depth). 50-line patch to existing K=10 stack. **Reserved as Phase 3 Path H if Path G plateaus**.

### B. Training-layer tricks (highest ROI, this Phase 3)
ROI ranking from scan:
1. ★★★ **EMA / SWA** (0.5h): direct fix for loss=0.24-0.31 oscillation observed in Path F late-iter logs. Standard SWA use case.
2. ★★ **Deep supervision (per-iter NMSE)** (1-2h): ISTA-Net++ standard. Reports 0.5-2 dB NMSE / 20-30% BER reduction in CS-style unrolled nets.
3. **Classical-teacher distillation** (6-10h, high effort): would distill from B+ iter=10 mid-state; reserved for Phase 4 if Path G is meaningful but not breakthrough.

### C. Architectural changes (not pursued in Phase 3)
- Transformer over DD support: architectural mismatch (attention shines for cross-frame correlation, we're single-frame).
- Diffusion prior: rebuilds whole stack (no support recovery — works on dense channel).
- ALISTA: subsumed by current per-iter MLP (strictly more expressive).

## Phase 3 design — Path G

**Hypothesis**: Path F's 5% plateau is partly a **training optimisation symptom** (loss oscillation 0.24-0.31, late-iter swing), not purely an architectural ceiling. Two training-layer additions (additive, no conflict):

### Path G = Path F + Deep Supervision + EMA

| Component | Implementation | Expected mechanism |
|---|---|---|
| Deep supervision | Per-iter NMSE-on-H_true via `_HReconstructor(g_dd^(k))` reconstruction at each of K=10 iters; total DS loss = Σ_k w_k · NMSE^(k). | Provides gradient signal at every unrolled iter instead of only final iter — smooths credit assignment, attacks late-iter loss oscillation. |
| EMA | `torch.optim.swa_utils.AveragedModel` with decay=0.999, updates after warmup, eval on EMA shadow weights. | Averages out the 0.05↔0.07 swings observed in Path F final 1500 iters → flat-basin averaging. |

### Default hyperparams (matched to Path F best)
- `--model pathF --path-f-iters 10 --path-f-untied`
- `--snr-list 15 20 25 --iters 5000 --batch 16`
- `--pretrain-iters 1000 --lam-h-nmse 0.5 --lam-bce 1.0 --lam-sym 0.5`
- `--lr 1e-3 --warmup 200 --lr-min 1e-6` (cosine)
- **new**: `--deep-supervision --ds-weight 0.5 --ds-decay 1.0` (uniform across K)
- **new**: `--ema-decay 0.999`

### Predicted outcomes (with mechanism for each branch)
- **Best case**: BER 0.050 → 0.030-0.035 (~30% reduction), driven primarily by EMA smoothing + DS gradient. Would close ~half remaining gap to classical OMP single-pass 0.014.
- **Modest case**: BER 0.050 → 0.040-0.045 (~10-20%). DS helps a bit, EMA smooths but doesn't shift mean.
- **Null case**: same plateau ~0.050. Would suggest 5% is the *architectural* floor of K=10 unrolled per-bin MLP — and we'd then go to Path H (Softsort-OMP).

## Operational notes

- Tmux session: `deinlab:g_path_g` (auto-detached, follow with `tmux attach -t g_path_g`)
- Output dir: `/data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_e2e_ladder_phase2/pathG_ds_ema/`
- ETA: ~2.5h (DS adds ~50% overhead vs Path F's 100min due to K=10× extra H_eff reconstructions per train step).
- Files modified:
  - `afdm_sp_joint_unrolled/path_e_models.py`: `UnrolledOMPNet.forward` returns `g_dd_history` (List[(L,K)] per iter)
  - `afdm_sp_joint_unrolled/train_path_e.py`: `_deep_supervision_nmse()`, `--deep-supervision/--ds-weight/--ds-decay`, `--ema-decay` + AveragedModel wrapper + EMA-eval branch
- Smoke verified locally (AST parse) + remote (50 iter, BER 0.54→0.32, no crash, EMA/DS both active).

## Reservation list (Phase 4 if Path G doesn't break 5%)

1. **Path H — Softsort-OMP**: hard top-k at inference + softsort relaxation at train. Attacks soft-support leakage that K=20 retrogression hinted at.
2. **Classical-teacher distillation**: per-iter MSE on g_dd^(k) vs B+ iter=k classical state. High-effort, high-payoff.
3. **Two-stage decoupled training**: freeze CE → train detector → freeze detector → train CE. 2 dB NMSE gain reported in Ye et al. on OFDM.
4. **Longer training + warm restart**: 5000 → 20000 iter with cosine warm restart.

## Lessons logged (post-finding)

1. **Always reality-check user's literature impression**: user's "OTFS-SP 那么好" was a memory artifact, not a citable fact. Lei et al. 2026 OMP-SP-OTFS 3% ceiling quote is the correct anchor.
2. **5% BER in N=1024 multi-SNR is competitive**: don't anchor on N=8-20 fixed-SNR OTFS-SP papers as the benchmark.
3. **Loss oscillation is a training-layer signal, not always architectural**: SWA-style averaging is the standard fix before claiming "architectural ceiling".

## Files

- `tcom_plan/E2E_phase3_plan.md` — this doc
- `tcom_plan/E2E_phase2_results.md` — Path F + K=20 ablation (the immediate predecessor)
- `tcom_plan/E2E_phase1_snapshot.md` — phase 1 record
