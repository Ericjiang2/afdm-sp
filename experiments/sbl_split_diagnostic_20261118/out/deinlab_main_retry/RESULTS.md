# SBL representation and support-compression diagnostic

## Observations

The deinlab Linux run replayed 200 archived keys in 50 frame clusters, using both saved upstreams. The one-key smoke used the same entry point and output a separate receipt. This supersedes the local macOS smoke as the bit-exact check. [Local smoke record](../local_smoke_retry/RESULTS.md).

- Deinlab smoke: `DONE wall_seconds=9.307 core_hours=0.002594 workers=1`. [Receipt](../deinlab_smoke_retry/gates.json).
- Full replay: `DONE wall_seconds=54.404 core_hours=0.081432 workers=7`. [Receipt](gates.json).

| Gate | Result | Evidence |
| --- | --- | --- |
| Synthetic | PASS | Maximum algebra residual 1.76e-16 |
| G1 | PASS | All 200 waveform pairs and 1,200 decoded hashes matched. Fixed/point/joint failures were 4/40/23 on L-diag and 15/11/2 on L-cov |
| G2 | PASS | All 400 decoded hashes and 400 log-loss values matched. Both upstreams had zero frame errors |
| G3 | PASS | 400 support pairs, max relative H error 1.17e-16, gain error 0, aggregate prior error 0 |
| G4 | PASS | 2 distinct-delay atoms recovered exactly, relative H error 0 |

### A. Exact duplication

With two copies per atom, a key passes the invariance rule when the first-update H relative difference is ≤ `1e-10` and the terminal maximum absolute LLR difference is ≤ `1e-9`.

| Upstream | Interface | Invariant | Decoded agreement | First H relative difference, median / max | Terminal LLR max difference, median / max |
| --- | --- | ---: | ---: | ---: | ---: |
| L-diag | fixed | 200/200 | 200/200 | 9.71e-17 / 1.17e-16 | 4.31e-14 / 2.74e-13 |
| L-diag | point | 0/200 | 90/200 | 1.09 / 2.56 | 10.2 / 26.8 |
| L-diag | joint | 0/200 | 154/200 | 0.918 / 2.27 | 4.65 / 8.37 |
| L-diag | eG | 200/200 | 200/200 | 1.16e-15 / 2.33e-15 | 2.28e-13 / 1.99e-12 |
| L-cov | fixed | 200/200 | 200/200 | 7.89e-17 / 1.13e-16 | 3.51e-14 / 2.62e-13 |
| L-cov | point | 0/200 | 175/200 | 0.504 / 1.48 | 9.35 / 15.6 |
| L-cov | joint | 0/200 | 189/200 | 0.426 / 1.27 | 4.42 / 7.8 |
| L-cov | eG | 200/200 | 200/200 | 3.49e-16 / 1.2e-15 | 8.95e-14 / 2.1e-12 |

### B. Support compression

Effects are original minus merged. A positive value means compression reduced the loss. Intervals are paired 95% percentile intervals from 10,000 resamples of the 50 frame clusters. FER values are fractions. Log loss is in nats per bit.

| Upstream | Relative operator error median [95% CI] | Q25–Q75 | Max |
| --- | ---: | ---: | ---: |
| L-diag | 0.2414 [0.2335, 0.2552] | 0.2152–0.2683 | 0.5179 |
| L-cov | 0.1504 [0.1385, 0.1649] | 0.1119–0.1996 | 0.4808 |

| Upstream | Interface | FER, original → merged | FER effect [95% CI] | Log loss, original → merged | Log-loss effect [95% CI] |
| --- | --- | ---: | ---: | ---: | ---: |
| L-diag | fixed | 0.0200 → 0.1550 | -0.1350 [-0.1850, -0.0900] | 0.2309 → 0.2604 | -0.0296 [-0.0381, -0.0224] |
| L-diag | joint | 0.1150 → 0.0300 | +0.0850 [+0.0450, +0.1250] | 0.2541 → 0.2272 | +0.0269 [+0.0223, +0.0312] |
| L-cov | fixed | 0.0750 → 0.2700 | -0.1950 [-0.2650, -0.1300] | 0.2485 → 0.2755 | -0.0270 [-0.0358, -0.0198] |
| L-cov | joint | 0.0100 → 0.0150 | -0.0050 [-0.0350, +0.0200] | 0.2191 → 0.2236 | -0.0045 [-0.0094, +0.0002] |

| Contrast | FER [95% CI] | Log loss [95% CI] |
| --- | ---: | ---: |
| L-diag, joint effect − fixed effect | +0.2200 [+0.1550, +0.2900] | +0.0565 [+0.0504, +0.0629] |
| L-cov, joint effect − fixed effect | +0.1900 [+0.1250, +0.2600] | +0.0225 [+0.0170, +0.0284] |
| L-diag contrast − L-cov contrast | +0.0300 [-0.0450, +0.1000] | +0.0340 [+0.0278, +0.0405] |

## Pre-declared category · stop and write the boundary

| Draft condition | Met |
| --- | --- |
| Fixed is invariant | Yes |
| Point is sensitive (forecast only) | Yes |
| Joint is sensitive | Yes |
| eG is invariant | Yes |
| L-diag median operator error ≤ .05 | No |
| L-diag joint minus fixed FER effect > 0 | Yes |
| L-diag joint minus fixed FER effect > L-cov | Yes |

The L-diag median relative operator error of 0.2414 exceeded the 0.05 limit and triggered the stopping rule. The empirical boundary is that the upstream FER ranking depends on the gain interface in this E-3 on-grid cohort at ρ=.3 and 7–8 dB. The data leave the mechanism of that ranking change unresolved.

| Claude draft forecast | Probability | Observed | Brier score |
| --- | ---: | --- | ---: |
| Fixed is invariant | 0.95 | Yes | 0.0025 |
| Point is sensitive (forecast only) | 0.97 | Yes | 0.0009 |
| Joint is sensitive | 0.80 | Yes | 0.0400 |
| eG is invariant | 0.45 | Yes | 0.3025 |
| L-diag median operator error ≤ .05 | 0.35 | No | 0.1225 |
| Category (continue / stop and write the boundary / unclear) | .25 / .45 / .30 | stop and write the boundary | 0.4550 |

## Untested explanation

Low confidence: compressing co-delay atoms could change the gain feedback by changing both the physical operator and the working gain prior. The observed compression effects do not separate these changes. The cohort is a replay of previously analyzed data.

## Provenance

The driver was committed at `bc672cd0` before launch. The recorded source hashes match the local sources. A local readout of all 1,600 A rows and 800 B rows reproduced the remote summary, intervals and category. The [summary JSON](summary.json) includes the three test-vector action differences and relative LLR L2 statistics. Per-key rows are retained on deinlab in `/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/sbl_split_diagnostic_20261118/out/deinlab_main_retry/`.

- `question_a.jsonl` SHA-256 `da1a5fb941f779c9082e0a5e3a197f8b35ec98fcc626ed485956a4011053d52a`
- `question_b.jsonl` SHA-256 `6c60eac0210b3a0892ff42f3df76ea34e805b516823c62a29c71881eae856b59`
