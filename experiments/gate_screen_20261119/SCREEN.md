# Archived-state identifiability screen

The frozen one-rule criterion **passes the screen**. The gate floored 0 of 398 true 0.35-bin pair contrasts and 0 of 398 controls at 0.75 bins. Both pooled 95% intervals were 0.00% to 0.92%. On the initial sparse Bayesian learning (SBL) grid, the median full-block rank was 15 for the gate and 18 for S-lo at each signal-to-noise ratio (SNR).

## Method and verification

For each isolated co-delay block, let $D_{ij}=d_N(\nu_j-\nu_i)$ be the normalized Dirichlet kernel, $u=\sum v$ the summed soft-symbol variance, and $B$ the mean-waveform dictionary. The screen forms $V_0=(uD+\lambda_*I)^{-1}$ and $V_1=(uD+\lambda_*I+B^HB)^{-1}$ through linear solves. It flags the phase-aligned pair contrast $p$ when $2p^HV_1p>p^HV_0p$. For blocks larger than two, it takes the positive eigenspace of $2V_1-V_0$ restricted to Dirichlet eigenmodes below 1. Singleton blocks have rank zero. S-lo selects the Dirichlet eigenmodes below 0.5. [Frozen gate and decision rule](../../.trellis/tasks/11-19-gate-screen/research/codex-sol-brief.md)

**S1.** Replayed F0 through the shared state entering the support exchange for all 398 triggered frames in the MIXED8 archive (frames 1000–1599, 7 dB, pilot fraction 0.5). The frozen trigger determined membership. The replay used parity-controlled stopping for the first round of soft-message updates and all 50 message sweeps for the second round on each triggered frame. The gate used the resulting pilot-plus-soft mean, marginal variances and $\lambda_*=\sigma^2$. Archived truth supplied only the common delay and two Dopplers for each scored pair. The first 20 observation hashes and ordered supports matched before the remaining frames ran. The observation and pilot hashes and canonical ordered delay (int64) and Doppler (float64) bytes matched for all 398 frames. The archive stored these support and input fields. The F0 soft moments were reconstructed from the frozen message updates.

**S2.** Selected 200 unique archived unified-SBL keys at pilot fraction 0.3 from frames 4400–4599, across the U and G scenarios. Seed 20261119 sampled without replacement within each SNR stratum. The replay stopped at the candidate grid entering expectation-maximization and used $\lambda_*=\lambda+u/N$. The archived first-round sweep count fixed the timing of the soft messages. On all 200 keys, observation, pilot, soft-mean, variance and candidate-index hashes matched, as did the summed S-lo rank. One trial key passed these checks before the rest ran. The synthetic 25-atom reference also reproduced 15 versus 18 selected modes at both endpoint SNRs.

Both replays stopped at the states required to evaluate the gate. The screen measures decisions at supplied positions and under frozen soft feedback. Receiver performance after applying the floor remains untested.

## S1. MIXED8 true doublets

Each spacing and delay stratum contains one binary observation per physical frame. The two-sided 95% Clopper–Pearson intervals use those frames as the independent sampling units and retain a positive upper bound when no frames are floored. The frozen rule uses the pooled interval for the 0.35-bin spacing.

| Spacing (bins) | Delay (samples) | Floored / frames | Floored | 95% interval |
| ---: | ---: | ---: | ---: | ---: |
| 0.35 | Pooled | 0/398 | 0.00% | 0.00% to 0.92% |
| 0.35 | 6 | 0/171 | 0.00% | 0.00% to 2.13% |
| 0.35 | 22 | 0/227 | 0.00% | 0.00% to 1.61% |
| 0.75 | Pooled | 0/398 | 0.00% | 0.00% to 0.92% |
| 0.75 | 6 | 0/227 | 0.00% | 0.00% to 1.61% |
| 0.75 | 22 | 0/171 | 0.00% | 0.00% to 2.13% |

## S2. SBL initial grid

Each block contributes equally within its SNR. The table gives median [25th, 75th percentile]. Ratios and overlaps use blocks with positive S-lo rank. The overlap is $\operatorname{tr}(P_{\mathrm{gate}}\Pi_{\mathrm{lo}})/\operatorname{rank}(\Pi_{\mathrm{lo}})$.

| SNR (dB) | Keys | Blocks | S-lo rank zero | Gate / S-lo rank | Overlap |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 6 | 34 | 2066 | 294 | 0.333 [0.000, 0.833] | 33.3% [0.0%, 83.3%] |
| 7 | 34 | 2080 | 293 | 0.333 [0.000, 0.833] | 33.3% [0.0%, 83.3%] |
| 8 | 33 | 2044 | 273 | 0.333 [0.000, 0.833] | 33.3% [0.0%, 83.3%] |
| 9 | 33 | 2057 | 280 | 0.250 [0.000, 0.833] | 25.0% [0.0%, 83.3%] |
| 10 | 33 | 2093 | 293 | 0.000 [0.000, 0.833] | 0.0% [0.0%, 83.3%] |
| 11 | 33 | 2066 | 289 | 0.000 [0.000, 0.833] | 0.0% [0.0%, 83.3%] |

Raw-rank quartiles include all blocks. Full blocks have 25 atoms.

| SNR (dB) | Gate rank | S-lo rank | Full blocks | Full-block gate rank | Full-block S-lo rank |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 6 | 0 [0, 15] | 2 [1, 18] | 680 | 15 [15, 15] | 18 [18, 18] |
| 7 | 0 [0, 15] | 2 [1, 18] | 698 | 15 [15, 15] | 18 [18, 18] |
| 8 | 0 [0, 15] | 2 [1, 18] | 673 | 15 [15, 15] | 18 [18, 18] |
| 9 | 0 [0, 15] | 2 [1, 18] | 667 | 15 [15, 15] | 18 [18, 18] |
| 10 | 0 [0, 15] | 2 [1, 18] | 673 | 15 [15, 15] | 18 [18, 18] |
| 11 | 0 [0, 14] | 2 [1, 18] | 674 | 15 [14, 15] | 18 [18, 18] |

Astra's predictions that most 0.35-bin pairs would be spared and that the initial-grid overlap would be below 90% are directionally supported. The predicted 15 versus 18 modes also matches the median on full blocks at all six SNRs.

## Reproducibility

The archived-state replay ran on deinlab in `g_gate` with eight single-threaded CPU workers and a 2 core-hour cap. It used 0.101 core-hours (about 51.2 seconds elapsed). The producing code is `bb5ad661`. The selected S2 keys included 107 U and 93 G keys. The exact command, source and archive digests, environment, selected key list, and frame and block decisions are in the checksummed result. The source inventory also lists six `._*` AppleDouble metadata files created by the macOS transfer. All six executable source hashes match the producing commit. [screen.json](out/screen.json)
