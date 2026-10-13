# E2E Ladder for AFDM-SP — Results (CORRECTED 2026-05-12 evening)

**Status**: 5 E2E variants stuck at BER=0.5 (random). **The previous version of this document (and commit `51a34fd`'s commit message) attributed this to "SP single-pass fundamental infeasibility" — that mechanism explanation is wrong.** Re-diagnosis after user pushed back on the "BER=0.5" result reveals the failure is a CENet training pathology (sparse-target prediction with cold-start MSE collapses to "predict zero"), NOT an SP-regime fundamental property. Single-pass classical OMP itself achieves BER ≈ 1.4% at SNR=20 dB in this setup. The E2E ladder does not prove E2E infeasibility; it proves we could not make CENet train within the budget tried.
**Total cost**: ~75 min GPU + ~60 min implementation across 5 architectural variants and 2 oracle diagnostics.

## The corrected story

### What we tried (5 cells)

| Cell | Architecture | Loss | Result | What we learnt |
|---|---|---|---|---|
| **E0** | Pure Transformer 925K params, fixed Path C2 bugs (real pilot Re/Im, Xavier init out_proj, cosine LR, warmup) | BCE-bits + MSE-symbol | 200 iter, loss 0.95→0.95, BER 0.495 | Pure NN without inductive bias can't escape random within budget |
| **E2 v5** | DD-grid CENet (global-pool → MLP head) + ThresholdNet + analytical chirp H_eff + diff. LMMSE | BCE-bits + MSE-symbol | 500 iter, loss 3.82→0.95 ("predict-zero" plateau), BER 0.494 | LMMSE detector + bit loss admits trivial H=0 minimum |
| **E2 v6** | E2 v5 + NMSE-on-H_true pretrain | Phase 1: NMSE; Phase 2: + BCE/MSE | 300 iter pretrain: NMSE stuck at 1.0; 700 iter joint: loss 5+ plateau, BER 0.494 | H_true supervision alone doesn't unblock CENet |
| **E2 v7** | E2 v5 + supervised MSE(g_dd, OMP-output) — perfect oracle warmstart | MSE on g_dd to classical-OMP gains | 500 iter, loss 0.002, BER 0.490 | Loss **looked like** convergence but is the "predict-zero" baseline (sum\|h_omp\|²/515 ≈ 0.002) |
| **E2 v9** (per-position conv head) | Replaced global-pool→MLP with conv keeping spatial info + AdaptiveAvgPool to L | Same MSE-on-OMP | 500 iter, loss 0.002, BER 0.494 | Architecture change doesn't help; same "predict-zero" trap |
| **E2 v10** | Magnitude-weighted MSE: active bins (\|target\| > 1e-3) get 100× weight | Weighted MSE-on-OMP | 500 iter, loss 0.04 (escaped zero!), BER 0.49 | Model now outputs nonzero, but loss plateaus and BER stays random |

(v8 was a quick Xavier-init-only try, killed mid-run when it showed the same "predict-zero" pattern as v7.)

### Two oracle diagnostics (THIS is what corrected the story)

After the user challenged "BER=0.5 doesn't match prior W8 Path C C1/C3 at 8-9% — likely code bug", we ran oracle tests:

**Oracle 1: H_eff = H_true (perfect channel) → my LMMSE detector**:
- **BER = 0.0000** (perfect)
- Conclusion: LMMSE detector implementation is correct.

**Oracle 2: H_eff built from classical-OMP gains via my _HReconstructor → my LMMSE detector**:
- **BER ≈ 1.4%**
- Conclusion: My AFDM channel reconstruction is correct. Classical single-pass OMP at SNR=20 dB gives BER ≈ 1.4% — **not** BER=0.5. SP single-pass is fundamentally feasible.

**Diagnostic on E2 v9 trained CENet output** (load best_e2.pt, run inference):
- CENet g_dd: max=0.0055, mean=0.0015, sum\|.\|²=0.0022
- Classical OMP target: max=0.91, mean=0.0037, sum\|.\|²=1.07
- CENet output is **essentially zero** — model never learnt to produce OMP-like sparse gains.

Loss=0.002 was the "predict-zero" baseline (`sum(|target|²)/(L*K) ≈ 1.07/515 ≈ 0.002`), not actual learning.

## Correct interpretation

**Single-pass channel estimation is NOT the bottleneck**: classical single-pass OMP achieves BER ~1.4% at SNR=20 — far better than random. The "SP iterative IC is necessary" narrative from `51a34fd`'s commit message and the previous version of this doc is wrong; iterative IC takes BER from 1.4% (single-pass) down to ~0% (iter=10 with B+ head), but the regime is NOT "single-pass fails entirely".

**The actual bottleneck**: pure NN cold-start training to predict sparse DD-grid coefficients is a hard ML problem. We tried 5 architectural/loss variants and could not make CENet escape degenerate "predict-zero" solutions within the budget. The reasons (which apply generally to sparse-output prediction with cold-start MSE):
1. Target is ~98% zero (10 active out of 515 bins). MSE-mean gradient at zero output is dominated by the 505 "should stay zero" bins.
2. Zero-init head + zero-target most positions → gradient pulls back to zero from any small deviation.
3. Weighted MSE (v10, active bins get 100× weight) breaks the symmetric zero pull, but the model still doesn't find the right active support (gets nonzero, doesn't get OMP-correct).

**What might actually work** (NOT tried within this budget):
- Classical OMP correlation `Phi^H · y` precomputed and fed as features to CENet → essentially "OMP correlation + small NN refine" hybrid.
- Two-head output: support classification (binary BCE on bin-active) + gain regression (MSE on active bins only) → handle sparsity properly.
- Much larger training budget (10k+ iters, batch 16-32, mixed-SNR) — but unclear how much would suffice.
- Curriculum: pretrain on **dense** synthetic channel targets first, then move to sparse.

These are not impossible; we just didn't try them in this exploration. **The honest paper claim is "we tried 5 cold-start E2E variants and none beat B+, but we did not exhaust the design space"**, not "E2E is fundamentally infeasible".

## What this means for the paper

The previous draft §IV-H E2E negative paragraph in `51a34fd`'s commit body **should not be used as-is**. Honest §IV-H E2E note (replacing the wrong "SP fundamental" framing):

> "We attempted five end-to-end neural receivers spanning cold-start pure-transformer (E0), DD-grid CENet with analytical chirp channel reconstruction and differentiable LMMSE detector (E2), variants with H_true-supervised pretraining (E2+NMSE), classical-OMP-warmstart supervised distillation (E2+OMP-MSE, two architectures), and magnitude-weighted sparse-target MSE (E2+weighted-MSE). All five converged to degenerate solutions (BER at chance) within our training budget of 200-500 iterations on N=1024 at SNR=20 dB. Oracle diagnostics confirm the receiver pipeline is correctly implemented (BER=0 with H_true and BER~1.4% with classical-OMP gains plugged in), so the failure lies in cold-start training of CENet to predict sparse DD-grid coefficients — a known difficulty in compressive-recovery + deep-learning hybrids that admits known fixes (correlation pre-features, two-head support+gain decomposition, longer training schedules) which we did not exhaust. We therefore report this as a negative-by-budget rather than a fundamental-infeasibility result, and ground the paper's main contribution on the B+ multi-component head augmenting the classical iterative receiver — a strictly weaker form of learning whose effectiveness is supported by independent ablations (§IV-G, A1 features 89%-positional, A2 cross-N asymmetric)."

## Files

- `afdm_sp_joint_unrolled/outputs_e2e_ladder/{e0, e2_v5, e2_v6_pretrain_joint, e2_v7_omp_warmstart, e2_v10_weighted_mse}/train_log.json` (5 cells; v8/v9 killed mid-run without log JSON, only ckpt — they showed the same "predict-zero" pattern as v7 in capture-pane output)
- `afdm_sp_joint_unrolled/{path_e_models.py, train_path_e.py}` (final state of the code after v10; weighted-MSE + per-position conv head + Xavier init final layers)
- This doc supersedes the previous version (which made the SP-fundamental claim).
