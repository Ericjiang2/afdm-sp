# Paper Claim Audit Report

**Date**: 2026-05-16
**Auditor**: Manual arithmetic verification (Claude Sonnet 4.6) — cross-model Codex MCP unavailable (auth expired)
**Paper**: Faithful Differentiable Unrolling of Joint OMP-MP Receivers for SP-AFDM
**Assurance**: submission

## Overall Verdict: WARN

This audit is now stale after the May 16 Fig. 3/Fig. 5 data refresh. The
original manual arithmetic check found all 18 verifiable quantitative claims
matched raw result files, but the current draft now uses the May 8
outer-iteration sweep for Fig. 3 and the May 7 physical-support-oracle JSON for
Fig. 5. Re-run `paper-claim-audit` on the current TeX/PDF before submission.

Current paper-facing refreshed sources:

- Fig. 3: `afdm_sp_joint_unrolled/outputs_ablation_H_outer_iter_20/CEILING_TEST_SUMMARY.md`
- Fig. 5: `afdm_sp_joint_unrolled/outputs_omp_extended_4B_big_headroom_results.json`

## Claims: 18 total — 17 exact_match, 1 rounding_ok, 0 mismatch

| # | Location | Paper Value | Raw Value | Status |
|---|---|---|---|---|
| 1 | Table 1 SNR=20 classical BER | 3.0×10⁻³ | 3686/(600×2048)=3.00×10⁻³ | PASS |
| 2 | Table 1 SNR=25 classical BER | 1.40×10⁻³ | 2209/(773×2048)=1.40×10⁻³ | PASS |
| 3 | Table 1 SNR=30 classical BER | 4.36×10⁻⁴ | 1160/(1300×2048)=4.36×10⁻⁴ | PASS |
| 4 | Table 1 SNR=20 learned BER | 1.87×10⁻³ | 2295/(600×2048)=1.87×10⁻³ | PASS |
| 5 | Table 1 SNR=25 learned BER | 8.35×10⁻⁴ | 1322/(773×2048)=8.35×10⁻⁴ | PASS |
| 6 | Table 1 SNR=30 learned BER | 2.72×10⁻⁴ | 724/(1300×2048)=2.72×10⁻⁴ | PASS |
| 7 | Table 1 Δ SNR=20 | -37.7% | (2295-3686)/3686=-37.74% | PASS |
| 8 | Table 1 Δ SNR=25 | -40.2% | (1322-2209)/2209=-40.15% | PASS |
| 9 | Table 1 Δ SNR=30 | -37.6% | (724-1160)/1160=-37.59% | PASS |
| 10 | OMP-(P+K) baseline SNR=15 | 1.98×10⁻² | 1.975×10⁻² | rounding_ok |
| 11 | OMP-(P+K) baseline SNR=20 | 3.89×10⁻⁴ | 3.887×10⁻⁴ | PASS |
| 12 | OMP-(P+K) baseline SNR=25 | 3.46×10⁻⁴ | 3.457×10⁻⁴ | PASS |
| 13 | OMP-K=2 GC SNR=20 | -61.3% | (3.887e-4−6.270e-4)/(3.887e-4)=-61.3% | PASS |
| 14 | Gap-closed SNR=15 | 61% | (1.975e-2−1.508e-2)/(1.975e-2−1.209e-2)=61% | PASS |
| 15 | Gap-closed SNR=20 | 81% | (3.887e-4−7.394e-5)/(3.887e-4)=81% | PASS |
| 16 | Gap-closed SNR=25 | 98% | (3.457e-4−5.580e-6)/(3.457e-4)=98% | PASS |
| 17 | Attention: 4-head, 0.0418, +9.7% | 4/0.0418/+9.7% | train_log: heads=4, best_eval_ber=0.04178, penalty=9.7% | PASS |
| 18 | Width-MLP 64→256: -23.5%; 256→512: -6.8% | -23.5%/-6.8% | arithmetic: (0.0381-0.0498)/0.0498=-23.5%; (0.0355-0.0381)/0.0381=-6.8% | PASS |

## Unverified (no raw file in scope)
- 1041-parameter count (architectural constant)
- Wall-clock timing and MAC counts (source: draft_section_IV_F_complexity.md — excluded from zero-context scope)
- Multi-seed -5.17%±0.57 (source: outputs_canonical_grid/ not in audit set)
