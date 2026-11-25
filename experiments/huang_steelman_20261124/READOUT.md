# Huang-2010-Style Steelman Readout (`huang_steelman_20261124`)

- **Freeze commit**: `4772365c61afe29c8c01815e39c41263cc9cb182` ([PROTOCOL.md](PROTOCOL.md), [gate.json](out/gate.json))
- **Results files**: [summary.json](out/summary.json), [RESULTS.md](out/RESULTS.md), [timing_summary.json](out/timing_summary.json), [REMOTE_ROWS_MD5.txt](out/REMOTE_ROWS_MD5.txt)
- **Remote raw artifacts (kept on deinlab)**:
  - Directory: `deinlab:/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/huang_steelman_20261124/out/raw/`
  - 24 shards (`rows_shard000.jsonl`..`rows_shard023.jsonl`, 18,009 triggered rows total): MD5 manifest in [REMOTE_ROWS_MD5.txt](out/REMOTE_ROWS_MD5.txt) and `summary.json._config.raw_rows_md5`
  - Timing raw rows (`timing_rows.jsonl`, 100 triggered + 50 untriggered F0 keys): MD5 `1f0a69e2d7f80e8a22f159b180fb23b4`
- **Execution & budget accounting**:
  - Gates G1–G4: `PASS` (`0.3294` core-hours), selecting `HG` recipe `B0-p2-s0.5`, retaining `HGint` and all 6 $\rho \in \{0.15, 0.20, 0.25, 0.30, 0.40, 0.50\}$.
  - Main run: **9.8401 cumulative core-hours** ($\le 12.0$ core-hour cap; initial 24-worker pass hit the conservative 1650 s wall timeout at `8.3411` core-hours with 20/24 shards complete; remaining 4 shards `[4, 6, 13, 15]` resumed cleanly via `resume_main.py` calling the unmodified frozen `4772365c` `run_main._shard_worker` in `1.4990` core-hours).
  - Quiet timing panel: `171.8 s` wall (`0.048` core-hours $\le 0.5$ core-hour cap) on `taskset`-pinned CPU `0` (measured idle utilization `0.0%`).

---

## Layer 1 — Observation

All numbers below come directly from [summary.json](out/summary.json) (62,400 total keys across 400 physical frames `5400–5799`, scenarios U/G, 6 $\rho$, 13 SNRs; 18,009 archived F0-triggered keys; 50,000 paired physical-frame bootstrap draws, seed `20261124`; Bonferroni $\alpha = 0.05/3$, 98.33% CIs for primary Q1/Q2/Q3; 95% CIs for secondary contrasts). Positive difference means `CD` requires lower SNR (better); negative means the comparator requires lower SNR.

### 1.1 Primary Contrasts

| Question | Contrast | Point (dB) | 98.33% Primary CI (dB) | 98.33% Per-Draw CI (dB) | Per-Scenario Point & 98.33% Primary CI |
|---|---|---:|---|---|---|
| **Q1** (paired CI) | `HG(.30) − CD(.30)` | **−0.2962** | **[−0.4947, −0.1452]** | — | U: −0.2103 [−0.5000, −0.0404]; G: −0.3821 [−0.7212, −0.1529] |
| **Q2** (36-pair proj CI) | `min_ρ HG − min_ρ CD` | **−0.6533** | **[−0.9668, −0.1936]** | [−0.7981, −0.4550] | U: −0.6077 [−1.1867, −0.2877]; G: −0.6990 [−1.2222, −0.0678] |
| **Q3** (36-pair proj CI) | `min_ρ Z − min_ρ CD` | **+0.0501** | **[−0.2141, +0.3270]** | [−0.0002, +0.1722] | U: +0.0693 [−0.4515, +0.5616]; G: +0.0308 [−0.1639, +0.4007] |

### 1.2 Scene-Averaged 1% FER Crossings (dB, Point & 95% CI) and Per-$\rho$ Paired Differences

| $\rho$ | `F0` | `CD` | `Z` | `HG1` (1-pass) | `HG` (2-pass) | `HGint` (2-pass coarse) | `HG − CD` (95% CI) |
|---:|---|---|---|---|---|---|---|
| 0.15 | [12.00, +∞] | 9.0000 [7.82, +∞] | 9.0000 [7.82, +∞] | 8.4142 [7.08, 9.62] | 4.9539 [4.68, 5.81] | 6.1218 [4.97, 6.82] | −4.0461 [−∞, −2.968] |
| 0.20 | 10.3691 [9.61, +∞] | 6.3066 [5.43, 6.94] | 6.5293 [5.50, 7.02] | 5.6117 [5.15, 6.44] | **4.4462** [4.32, 4.59] | **4.5408** [4.42, 4.68] | −1.8604 [−2.499, −1.027] |
| 0.25 | 7.7192 [7.33, 8.01] | 5.1561 [5.00, 5.34] | 5.2293 [5.06, 5.58] | 5.1658 [4.97, 5.34] | 4.6297 [4.50, 4.75] | 4.7919 [4.63, 4.95] | −0.5264 [−0.728, −0.361] |
| 0.30 | 6.8066 [6.31, 7.18] | **5.0995** [4.98, 5.31] | **5.1495** [5.02, 5.34] | **5.1055** [4.99, 5.31] | 4.8033 [4.74, 4.91] | 4.8768 [4.78, 4.98] | −0.2962 [−0.456, −0.172] |
| 0.40 | **6.2386** [6.08, 6.46] | 5.5765 [5.48, 5.75] | 5.6211 [5.50, 5.78] | 5.5497 [5.45, 5.73] | 5.3888 [5.30, 5.49] | 5.4728 [5.34, 5.57] | −0.1876 [−0.327, −0.084] |
| 0.50 | 6.7319 [6.59, 6.90] | 6.2860 [6.22, 6.40] | 6.2870 [6.22, 6.40] | 6.2581 [6.21, 6.34] | 6.1272 [6.02, 6.18] | 6.1734 [6.09, 6.21] | −0.1588 [−0.281, −0.096] |

- **Point optimal $\rho$**: `F0` = `0.40`, `CD` = `0.30`, `Z` = `0.30`, `HG1` = `0.30`, `HG` = **`0.20`**, `HGint` = **`0.20`**.
- **Key secondary contrasts (best-vs-best, 95% projected CI)**:
  - `HG1 − CD`: **+0.0060 dB** `[−0.2928, +0.2940]` (at $\rho=.30$: `+0.0060 dB [-0.0015, +0.0288]`; at $\rho=.20$: `−0.6949 dB [-1.3239, -0.0242]`).
  - `HG1 − HG`: **+0.6593 dB** `[+0.2255, +0.9451]` (second global OMP pass adds 0.66 dB at best $\rho$).
  - `HGint − HG`: **+0.0946 dB** `[−0.3182, +0.2704]` (coarse integer grid `[-2..2]` loses < 0.10 dB relative to the fine `0.25`-step grid).
  - `HGint − CD`: **−0.5587 dB** `[−0.8494, −0.2677]` (coarse integer-grid 2-pass `HGint` also beats `CD` by 0.56 dB).
  - `HG − F0`: **−1.7924 dB** `[−2.6100, −1.3240]`; `Z − F0`: **−1.0890 dB** `[−1.8682, −0.8029]`.

### 1.3 Paired Rescues, Pass-2 & Support Diagnostics (18,009 Triggered Keys)

- **Paired rescues `HG` vs `CD`**: `CD_only = 18`, `HG_only = 1,827`, `both = 6,026`, `neither = 10,138`.
- **Paired rescues `Z` vs `CD`**: `CD_only = 249`, `Z_only = 93`, `both = 5,795`, `neither = 11,872`.
- **`HG` pass-2 diagnostics**: pass-1 early stop on `6,142 / 18,009` (`34.11%`); pass-2 ran on `11,867`, rescued `1,704` frames (`0` FER-harmed observed; note early stopping checks syndrome = 0 while FER scores information bits), bit-improved `7,711`, bit-worsened `3,405`.
- **1-to-1 support recovery (`l_fit == l_true`, $|\Delta k| \le 0.5$)**:
  - `HG1_omp`: `94.44%` path recall (`99.73%` pooled power) → `HG1_refined`: `87.38%` (`98.74%` power) → `HG_final_refined`: **`89.03%`** (`99.08%` power).
  - On the `11,867` keys that ran pass-2: refined recall rose from `84.61%` (`98.30%` power) in pass 1 to `87.11%` (`98.80%` power) in pass 2.
  - `CD_final_refined`: `87.43%` (`98.88%` power); `Z_final_refined`: `85.62%` (`98.48%` power).

### 1.4 Quiet Single-Core Runtime Panel ($\rho = 0.30$, 5.0 dB; 100 Triggered + 50 Untriggered F0 Keys; CPU 0, 0.0% Util)

- Shared triggered `F0` median: `269.69 ms`; untriggered `F0` mean: U `262.30 ms`, G `262.82 ms`; trigger rates at $(\rho=.30, 5.0\text{ dB})$: U `22.0%`, G `27.5%`.
- `HG` stopped at pass-1 on `91 / 100` keys in this panel.

| Arm | Per-Trigger Mean (ms) | Per-Trigger Median (ms) | Per-Trigger p95 (ms) | Ratio of Means vs `CD` | Median Paired Ratio vs `CD` | Amortized Full-Frame Mean (ms) |
|---|---:|---:|---:|---:|---:|---:|
| `CD` | 159.01 | 158.76 | 166.28 | 1.000× | 1.000× | 303.64 |
| `Z` | 159.15 | 158.38 | 165.72 | 1.001× | 1.003× | 303.68 |
| `HG` | 571.62 | 523.49 | 1055.42 | 3.595× | 3.310× | 406.58 (1.339×) |
| `HG1` | 524.24 | 523.48 | 535.48 | 3.297× | 3.295× | 394.13 (1.298×) |
| `HGint` | 188.61 | 168.34 | 341.46 | 1.186× | 1.066× | 311.33 (1.025×) |

---

## Layer 2 — Pre-Registered Verdict

Strictly applying the frozen mutually exclusive rules in [PROTOCOL.md](PROTOCOL.md) §3 (no relabelling):

1. **Q1 (consistency, fixed $\rho = 0.30$)**: **`−0.2962 dB [−0.4947, −0.1452]`** — two-pass Huang-style global OMP (`HG`) strictly outperforms `CD` at $\rho = 0.30$ in both scenarios (U and G).
2. **Q2 (primary, `min_ρ HG − min_ρ CD`)**: **`HG_AHEAD`** (`−0.6533 dB`, 98.33% 36-pair projected CI `[−0.9668, −0.1936]`, `U < 0`; `strict_lt_neg0p5_db = False` on the conservative 36-pair projection, though the point estimate is `−0.6533 dB` and per-draw CI is `[−0.7981, −0.4550]`). Consistent across both scenarios individually (`U: HG_AHEAD`, `G: HG_AHEAD`).
   - **Pre-registered meaning for the paper**: The published-style two-pass global OMP steelman (`HG`) beats local exchange (`CD`) on 1% FER accuracy. Even stronger, the coarse integer-grid variant (`HGint`) also beats `CD` (`−0.5587 dB [−0.8494, −0.2677]`) at nearly identical runtime (`1.066×` median per-trigger, `1.025×` amortized full-frame). Therefore, **local exchange (`CD`) cannot be framed as accuracy-superior or Pareto-dominant over Huang-2010-style data-aided global OMP re-acquisition** on this regime.
3. **Q3 (independent primary, `min_ρ Z − min_ρ CD`)**: **`Z_EQUIVALENT`** (`+0.0501 dB`, 98.33% 36-pair projected CI `[−0.2141, +0.3270]`, wholly inside `[−0.5, +0.5]` dB, `strictly_nonzero = False`).
   - **Pre-registered meaning for the paper**: Setting $\Gamma = 0$ inside the local exchange branch (`Z`) is within the $\pm 0.5$ dB equivalence margin of `CODELAY` (`CD`) on the 6-point $\rho$ grid. This directly challenges framing the `CODELAY` projected-covariance $\Gamma$ term as essential for end-to-end 1% FER performance against the simplest zero-variance exchange baseline.

### Competing Hypotheses Adjudication (Pre-Registered Predictions Only)

- **H-local predictions**: **Not matched (refuted on this cohort)** — `HG` beat `CD` at every $\rho$ including low $\rho$, and pass-2 rescued 1,704 additional frames (`HG1 − HG = +0.6593 dB` best-vs-best, `+0.3022 dB` at fixed $\rho=.30$).
- **H-global predictions**: **Matched by the observed primary and secondary readouts** (`HG_AHEAD`, point optimal $\rho$ shifted down from `0.30` to `0.20`).
- **H-grid predictions**: **Not matched** (`HGint − HG = +0.0946 dB [−0.3182, +0.2704]` best-vs-best; `HGint − CD = −0.5587 dB [−0.8494, −0.2677]`).

---

## Layer 3 — Candidate Explanations (Untested) & Limits

The following mechanisms are **untested post-hoc interpretations**, not proven claims:

1. **Why two-pass global OMP beats local exchange (`max_edits=2`) especially at $\rho = 0.15\text{–}0.20$ [Confidence: H]**: At low pilot fraction ($\rho \le 0.20$), `F0` often misses more than 2 paths or starts with a severely corrupted support, whereas `CD` is capped at `max_edits = 2` sequential 1-for-1 swaps from `F0`'s support. By contrast, global OMP rebuilds the entire 8-path support from `pilot + mu` (`HG1_omp` already hits 94.44% path recall), and a second pass (`HG1 − HG`: `0.6593 dB` best-vs-best; `0.3022 dB` at fixed $\rho=.30$) exploits the newly decoded soft symbols to bootstrap out of low-$\rho$ failures (driving $\rho=0.15$ from `8.41 dB` down to `4.95 dB`, and $\rho=0.20$ from `5.61 dB` down to `4.45 dB`).
2. **Why `HG1` ties `CD` at $\rho \ge 0.25$ yet beats `CD` at $\rho \le 0.20$ [Confidence: H]**: At $\rho = 0.30$, `F0` typically misses only 1–2 weak paths, so `CD`'s 2-edit budget already reaches the same single-pass support quality (`87.43%` vs `HG1_refined` `87.38%`, `HG1 − CD = +0.006 dB`). Note that `HG` uses up to 4 total rounds (2 F0 + 2 HG) vs `CD`'s 3 total rounds (2 F0 + 1 CD); whether a 2-pass `CD` (or `max_edits > 2`) would close part of the gap was not tested here.
3. **Why `HGint` captures almost all of `HG`'s gain at 1.07× `CD` latency [Confidence: H]**: Shrinking the OMP dictionary from 2,575 columns (`0.25` step on `[-3, 3]`) to 515 columns (`-2..2` integer grid, **1/5 the dictionary size**) still places atoms near the integer Doppler bin, after which `time_refine(mode='soft', max_paths=8, rounds=2)` performs continuous off-grid Doppler refinement; testing `HGint` without `time_refine` would be needed to confirm this separation.
4. **Why `Z` ($\Gamma = 0$) is equivalent to `CD` on 1% FER [Confidence: M]**: Earlier comparisons on the same `rho_sweep_20261119` archive contrasted `CD` against *diagonal* $\Gamma$ (`A2`), where `A2 − CD` was `+0.7864 dB` at $\rho=.30$ and `+1.3394 dB` at $\rho=.25$ ([rho_sweep RESULTS.md](../rho_sweep_20261119/out/main_20261119/RESULTS.md)) due to scalar/diagonal phantom-admission bias. Zeroing $\Gamma$ removes that diagonal phantom-admission bias altogether, leaving only a `0.0501 dB` (`+249` vs `+93` rescues on 18,009 keys) difference from the exact co-delay block covariance `CD` — a much smaller gap than previously seen against `A2`.

### Scope Limits

- `HG` uses two-pass OMP (`B0-p2-s0.5`) rather than Huang 2010's exact Basis Pursuit ($\ell_1$-LS) and 6–10 outer passes; `HG` also retains `time_refine(mode='soft', max_paths=8, rounds=2)` as a steelman concession.
- Single modulation/code/frame setting (QPSK, LDPC (3,6) $n=2048$, $N=1024$), known $\sigma^2$, $P=8$ distinct true delays (no clustered same-delay twin paths).
- Quiet timing was measured only at $(\rho = 0.30, 5.0\text{ dB})$ where 91% of `HG` triggers stopped on pass 1; pass-2 frequency and latency at $\rho = 0.20$ near `HG`'s 4.45 dB operating point were not measured and remain untested.
