# Archived admission-law readouts

Post hoc descriptive measurements on existing fail-triggered M-family keys.
Execution uses the archived cap-8 F0 receiver, round index 1 (`r1_*`, the
second coded round), from the original admission-law replay. No new keys or
observations were sampled from the frame generator. True delays enter only
the offline class labels.

## R1 · First-exchange gross rewards

All 7,667 admission-law rows passing the archived common subset check were
used for A2 (scalar) and A1c (CODELAY). Each arm uses the same legal
candidate-by-deletion-slot grid as its frozen selector. The observer reads
the exact measured Schur gain returned by the archived logger before the
deletion proxy. A phantom has a delay occupied by a surviving atom. The true
and false new classes both require a delay absent from the entering support.
The anchor for the regression is the archived surviving anchor of the
candidate and slot attaining the maximum measured phantom gain.

An empty candidate class has a null unit-level maximum and contributes zero
reward to the summaries, with its count reported. The AUC is the empirical
probability that a draw from the first class exceeds an independent draw
from the second class, with half credit for ties. Both ridge-normalized and
gross AUCs are included. OLS has an intercept and uses positive gross phantom
gains and positive squared anchor magnitudes. The curves use strict
exceedance and share one log-spaced grid. The reported cutoff is the exact
smallest empirical threshold satisfying both 5% limits. The archived trigger
is the F0 nonzero syndrome.

## R2 · APP variance spectrum and retained cross-delay pairs

A uniform sample of 1,000 keys was drawn without replacement from the
8,102 triggered keys with archived information-bit errors. Four of the
8,106 triggered keys had zero information-bit errors. Sampling used this
pool before applying R1's eligibility check. NumPy PCG64 with seed 20261119 sampled indices of
lexicographically sorted `(frame, scenario, rho, snr_centi_db)` tuples.
The clipped F0 `r1_app` and data power `1-rho` enter the same frozen
`moments` used for the admission-law exchange. The variance vector is in the
AFDM symbol domain. The spectrum uses the unnormalized FFT, with
`u = sum(v)`. The support consists of the F0 `r1_delays` and
`r1_dopplers`. The full covariance uses the frozen `_gamma_cross` call
underlying `gamma_full`. Both maxima use the same unordered cross-delay
pairs. The OFDM calculation drops the chirp shift in the Dirichlet kernel.
The ratio is computed per unit as the AFDM maximum divided by the OFDM
maximum. The closed-form magnitude is checked on every evaluated pair.

## Receipts

[summary.json](out/summary.json) contains the executed `_argv`, `_config`,
source hashes, quantiles, all curve ordinates, parity counts and CPU time.
All 200 admission shard hashes matched. The first-shard gate matched 41 F0
records, 41 full admission records and four APP E/u records. Across the
finished replay, all 7,714 distinct F0 records, 7,667 full admission records
and 1,000 APP E/u records matched exactly. Across 28,000 cross-delay pairs,
the maximum relative Gamma error was `7.072e-16`. The successful replay and
aggregation used 1.018231 core-hours. The unit file was independently
recounted for quantiles, AUCs, OLS slopes, curves and the exact thresholds.
The frozen inputs and raw per-unit readouts are on deinlab. The latter are at
`/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/zero_sim_readouts_20261119/out/unit_readouts.jsonl.gz`.
The file's SHA-256 is in the summary. The raw rows include selected keys and
R1/R2 membership for re-aggregation.

The first launch stopped before receiver replay. The frozen loader inventories
all imported project modules and detected the early import of the new observer.
The diagnostic found that one extra module, with zero missing or changed frozen
modules. The successful launcher loads the observer after the frozen source
inventory. The startup logs are in the remote `out/startup_attempt/`. The
startup and diagnostic CPU together are bounded by 0.041 core-hours, in addition
to the measured successful run. The per-process CPU limits leave room for that
overhead within the 3 core-hour cap. The executor session records
`model: gpt-6.2-sol`.
