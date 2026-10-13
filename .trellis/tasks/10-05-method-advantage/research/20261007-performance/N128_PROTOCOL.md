# One bounded N128/T2 acquisition comparison

Development claim: in a longer AFDM block, a fixed general-phase code plus FFT screening can improve acquisition accuracy relative to a conventional quadratic code while retaining useful full-likelihood accuracy at lower complete-call cost. This is a within-N128 claim. The information-budget and quadratic-barrier analyses motivate it but do not predict the outcome. Four earlier performance FAILs stay unchanged. No new first-in-literature claim.

## Model, immutable design, and paired cohort

N128/T2/SNR5dB, s5, CP32/frame stride160, iid fresh QPSK, one shared static physical gain. Delay uniform0…31 and integer CFO uniform0…127; radius uniform[.75,1.25] and phase uniform[0,2pi), known nominal sigma²=10^(-.5). Useful observations only. Retain the qualified physical generator.

Design D uses exactly the old129 quadratic-c2 candidates (1/(10N²) plus (k+sqrt2)/(4*129), k0…127), selecting the earliest minimum of the same restricted fourth-power ambiguity maximum. One independent general-phase code from128 Uniform[0,1) draws, seed2026100706, principal fourth-root convention. No restarts, no performance-based code selection, no further mu optimization. Reuse the existing design function. Independent design checking recomputes all130 objective values before P and verifies quadratic choice, candidate formulas, unit modulus and all saved array/file hashes. Design plus independent verification reserve2*130*127*32=1056640 geometry values; random draws128. Both costs belong to D60 seconds.

P has256 fresh independent paired groups, seed2026100707, draw order delay,CFO,rho,phase,states(2,128),realnoise,imagnoise. Share all exogenous variables between quadratic and random waveforms. Exactly four complete calls per group: each code SCREEN512 and FULL; rotate their order by group mod4, no warmup or per-observation shared cache. Save original states/noise/Y, candidate scores, choices, timing and audit provenance. No interim endpoint selection, no old-data pooling, no seed retry.

Each method uses a96-point effective-gain grid: magnitudes[.75,1,1.25] × phases r*pi/64, r0…31 (full-circle equivalent128 points moduloQPSK). This is closed under N128 Weyl cocycles. Both code arms use the same grid. Retain all4096 hypotheses; SCREEN512 keeps the highest512 fourth-power FFT scores with stable order then exact finite-grid profile reranking. Physical gain output applies the same delay phase correction. The shortlist retains1/8, matching the previous N64 SCREEN128 fraction. These changes address new-size implementation confounds; they do not make cross-N data a causal comparison. No continuous-gain ML/MAP claim.

## Frozen gates, accounting, and interpretation

All required: valid immutable source/design/raw audit andFULL>=SCREEN512 likelihood objective; random FULL/SCREEN512 cumulative complete-call time ratio>=3; random bad discordance SCREEN wrong/FULL correct one-sided95% CP upper<=.02 (at256 groups, x<=1), reverse separately; quadratic SCREEN512 minusrandom SCREEN512 error difference>=.10 and exploratory paired-normal95% interval lower>0; random SCREEN512 error<=64/256. All original substantive thresholds remain. Counts are256groups/512waveform datasets/1024new128-vectors/131072complex samples/1024acquisition calls/2359296likelihood candidates/226492416gain evaluations. D creates0 observations. P creates0 newgeometry. A creates0 observations/estimator calls/design draws and performs no new code search.

This is another outcome-informed development configuration, not globally preregistered confirmation. Passing would support only this fixed code, model, prior and algorithm comparison;129 candidates do not establish dominance over the globally best quadratic code. A negative result cannot be repaired by selecting another seed, sample subset, shortlist or threshold.

## Execution and independent audit

D60/P3000/A180 seconds, total3240seconds, CPU1/CUDAhidden, RSS2GiB/output512MiB. P estimate is roughly40minutes from prior kernel scaling; this is a budget, not a measured performance result. Committed source plus independent admission; minimal isolated Git snapshot on deinlab/AFDM. All writes/cache/temp under/data/guoyikun; g_ tmux; no concurrent timed science jobs. Preserve any failed/incomplete attempts and unused reservations.

A independently reconstructs every physical Y by explicit matrix operations, every fourth score by direct template sums, saved choices/gain mapping/ties/call counts, subset likelihood equality and objective dominance. Explicit96gain QPSK mixtures checked at fixed groups0/64/128/192 ×2codes×2candidates=16candidate checks. Recompute paired statistics, all gates and CP via independent binomial inversion. Complete source/design hashes and counters bound; limited mixture spots cannot be called全量独立似然重算. Sources: experiments/afdm_acquisition_n128_20261007; output: afdm_sp_joint_unrolled/outputs_acquisition_n128_20261007.

Main report table: two codes × two methods, errors, cumulative complete-call seconds, bad/reverse discordance, paired interval, resource/observation totals. No paper or production modifications. Mission CSV remains the live issue tracker.
