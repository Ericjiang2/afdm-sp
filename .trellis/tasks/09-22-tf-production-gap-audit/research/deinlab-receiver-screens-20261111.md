# Deinlab receiver screens — 2026-11-11

Block comparison first, CSTATE factorial second. Both CPU runs completed, with independently recounted paired keys and error transitions. The receiver sources, protocols and old-frame ledger are identified by hashes. The forecasts were frozen in each transferred protocol before the corresponding main run. These are exploratory screens.

## Fresh integer-delay block policy

At physical rho=.3, 160 new frames per SNR. The progressive policy takes a narrow prefix, swaps delays on failed syndrome, then widens one tap at a time with the original soft state and retained delays. Controls are path B, independent archived M_adapt (WIDE), and true H. See the [protocol](../../../../experiments/dpss_paired_screen_20261111/PROTOCOL.md) and [summary](../../../../afdm_sp_joint_unrolled/outputs_dpss_paired_screen_20261111_v2/summary.json).

| Family | Comparator | FER .1 crossing difference, dB (pointwise 95% paired CI) | Observed result |
|---|---|---|---|
| P1 U | B | +.064 [-.006, +.139] | At 4.5 dB, 40 vs 26 errors |
| P1 G | B | +.105 [+.008, +.202] | At 4.5 dB, 58 vs 39 errors |
| J4 | WIDE | Unbracketed for UNIFIED | At 8.5 dB, 98 vs 4 errors, A3 2 |

The joint +.2 dB screen fails on J4. Progressive J4 had 0 rescues and 333 harms relative to WIDE across 640 cells. Its 430 failures exhausted the eight expansions, and its median measured time was .971 s per cell versus .241 s for WIDE on the shared instrumented host. This does not replace the earlier narrow-to-independent-wide evidence. The progressive arm retained exchanged delays and narrow-prefix moments through widening, while WIDE had an independent initialization and update sequence. A narrow-prefix soft-state mismatch is a candidate explanation (L, untested). Fractional delay and end-to-end scalar block estimation remain untested.

The initial Linux attempt stopped before simulation because the local pilot referenced Mac checkout directory names. The v2 run selected the Linux reviewed source paths and retained the archived source, checkpoint and LDPC identity checks. Mixed-width Gamma agreed with explicit matrix projection to 1.39e-13, and 4 of 6 smoke cells exercised widening. The completed 2240 cells took 225 s at 16 single-thread workers.

## Direction A factorial

251 archived P1 F0 triggers, 107 frame clusters. Rebuilt each F0 state from its archived key and matched all F0 hashes/syndromes and all full-score/native path B hashes and error counts. The structural scoring/acceptance policy was the only upstream intervention, and both arms used full Gamma for subsequent local refinement and initial gain fitting. The downstream mean-only expected-Gram update retains the original scalar gain-variance recursion. It is a diagnostic variant. See the [protocol](../../../../experiments/cstate_score_update_20261111/PROTOCOL.md) and [summary](../../../../afdm_sp_joint_unrolled/outputs_cstate_score_update_20261111/summary.json).

| Gain update | Full Γ failures | Scalar Γ failures | Conditional FER advantage of full Γ (95% paired CI), pp |
|---|---:|---:|---:|
| Native | 53 | 191 | 54.98 [49.22, 60.87] |
| Expected-Gram mean | 61 | 156 | 37.85 [32.11, 43.75] |

The advantage persists and shrinks by 17.13 pp [12.15, 22.76]. Coded-bit log-loss differences in the same direction were .07428 and .04117 bits/bit. Changing the gain mean improved the scalar-score arm and increased the full-score arm's failures. The study supports keeping direction A as a candidate main contribution within the tested P1 path receiver. It does not extend this evidence to true co-delay clusters or population FER. Wall time was 32 s at 12 single-thread workers.

Raw JSONL files and their MD5 manifest paths remain at deinlab under `/data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/` in `outputs_dpss_paired_screen_20261111_v2` and `outputs_cstate_score_update_20261111`. Compact receipts and the MD5 manifests were returned to the same relative directories. The combined archive SHA-256 is `196a776182e14b08c8d0e26c290ced7bfcfd40abcf58bc08e3b2968cf5953639`.
