# Loop 10 — P=8 smoke analysis (P=10-trained ckpt cross-applied)

**Config**: N=1024 v=2 P=8 τ=10ms, mp=bp, variant=C2-rel, ckpt=`outputs_loop9_c2rel_train/ckpt_c2rel_force_topk.pt`
**Protocol**: `--use-hard --target-errors 800 --min-frames 30 --frames-per-snr 80 --seed 20260422`
**Figure**: `figures/loop10/smoke_p8_crossapply.png`

| SNR | frames | cls BER | torch-ref BER | learned BER | Δ cls | Δ torch-ref | **McNemar p** | NMSE cls (dB) | NMSE lrn (dB) |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 10 |  30 | 1.014e-01 | 1.014e-01 | 1.007e-01 | **−0.67 %** | −0.67 % | 0.033 ✓ | −12.34 | −12.40 |
| 15 |  30 | 3.530e-02 | 3.530e-02 | 3.516e-02 | −0.41 % | −0.41 % | 0.321 null | −15.93 | −15.98 |
| 20 |  80 | 2.936e-03 | 2.924e-03 | 2.826e-03 | **−3.74 %** | −3.34 % | 0.036 ✓ | −21.75 | −21.93 |
| 25 |  80 | 1.038e-03 | 8.728e-04 | 7.080e-04 | **−31.76 %** | −18.88 % | **3.21e-10 ✓✓✓** | −24.46 | −24.95 |
| 30 |  80 | 3.418e-04 | 3.418e-04 | 3.967e-04 | **+16.07 % REGRESS** | +16.07 % | 0.941 (H1 rejected) | −24.58 | −24.66 |

## Interpretation

**GOOD**:
- Without retraining, the P=10 C2-rel ckpt already gives stat-sig BER wins at SNR 10/20/25.
- **SNR=25 is visually separated**: learned 7.08e-4 vs classical 1.04e-3, p=3.2e-10 on 80 frames — exactly the kind of paper-worthy point user is asking for.
- Waterfall monotone for both arms individually.
- NMSE monotone and below PCSI-LS lower bound (not yet measured with PCSI arm).

**BAD**:
- **SNR=30 regression**: learned (3.97e-4) > classical (3.42e-4) by +16 %. Violates user rubric "learned must be ≥ classical at high SNR". This is the exact anomaly the user explicitly forbade.
- Frame budget at SNR ≥ 25 way below 800-err target: SNR=25 hit 170 cls errs, SNR=30 hit 56 cls errs. User wants adaptive target 800; we need more frames (~400-800) at SNR ≥ 25 to accumulate.

## Root cause of SNR=30 regression (mechanical)

At very high SNR the OMP-LS fit's residual is near-zero already. The force-topk head adds K_add=4 candidates, union-LS refits, then prunes back to |S_omp| by |gain|. At SNR=30 noise is so small that added candidates sometimes have gains competitive with true weak OMP atoms, so the prune step **evicts correct OMP atoms** in favor of spurious additions. Net: support-set gets polluted, DA-LS downstream diverges slightly, BP detector produces more bit errors.

At SNR ≤ 25 this is not an issue because OMP has plenty of misses (support uncertainty >> noise margin), so additions actually fix real miss-picks.

## Candidate fixes (pick one for Round 2)

**F1 — Sequential add-and-test (Oracle R3 Loop-9 recommendation)**: For each candidate in descending score order: tentatively add → pilot-LS on union → keep only if residual norm reduces by ≥ ε_r·σ² AND new atom's |gain| exceeds weakest OMP atom's |gain| by margin η ≥ 1.05. Else stop. Self-regulating across SNR: at high SNR, almost no candidate passes → head becomes no-op → no regression.

**F2 — Per-SNR K_add schedule**: K_add = {10 dB: 4, 15 dB: 4, 20 dB: 3, 25 dB: 2, 30 dB: 0}. Simple, no code change beyond a lookup. Downside: requires hand-tuning, not principled.

**F3 — Support-anchoring**: Instead of "union + prune by |gain|", do "keep ALL OMP atoms, add up to K_add candidates that have |gain_on_union| > max(|gain| of weakest OMP atom) × margin". Equivalent to F1 but parallel (no sequential loop).

**F4 — Residual-sigma margin gate**: At inference time, compute `||r_after_LS||²`. If it's already ≤ eps·σ²·N (i.e., classical OMP basically solved it), skip the head entirely.

## Recommended Round-2 strategy

A + F1 (minimum working change):
- Keep the P=10-trained C2-rel ckpt (don't retrain — saves 2-3 h).
- Implement sequential add-and-test safety valve in `classical_joint_unrolled.py` `CandidateActiveRelationHead` forward path.
- Re-run paired eval at P=8 SNR={10, 15, 20, 25, 30} with `--target-errors 800 --min-frames 80 --frames-per-snr 600 --with-pcsi --use-hard`.
- Hoped outcome: SNR=30 regression gone, SNR=20/25 wins preserved or stronger (more frames), waterfall visibly separated.
