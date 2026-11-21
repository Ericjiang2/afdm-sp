# Uniform-symbol-variance Gamma adequacy

Date: 2026-10-21. Producing source `de5926faa3555d7e8abe6dd70c992fe5160b8aaf`. Same old
200 keys / 50 shared P1 frame clusters, U/G, rho .3, SNR 7/8 dB. Informed exploratory
screening; independent saved-raw/count/bootstrap audit passed. No SBL fit or new frame.

Replacing each symbol variance by its average, while retaining the full mean Gram and the
atom geometry, preserves essentially all of the full-versus-diagonal Gamma logloss benefit.
Both upstreams pass the pre-registered 90% retention criterion; all four cells pass
pointwise. This identifies the same-delay block projection as the relevant structure in this
cohort and removes the need for per-symbol heteroscedastic variance in the gain update.

## Observation

Same saved support/h0/check prior, full `BHB`, 20 steps, damping .3, zero propagated gain
variance. The only new arm is
`Q = BHB + Gamma(vbar*1) + noise*P*I`, `vbar = mean(v_pre)`; the full and Gamma-only-diagonal
references are the immutable `gram_cohort1/full` and `gamma_ablation1/gamma_diag` scores.
For integer delays in `[0,N)`, `Gamma(vbar*1)` equals the same-delay block projection of the
original Gamma. This identity is exact and was qualified on synthetic and saved real moments
at relative tolerance 1e-10 (40 projection calls per terminal, 20 steps).

| Saved upstream | Full Gamma logloss | Diagonal Gamma logloss | Uniform Gamma logloss | Full / diagonal / uniform failures |
|---|---:|---:|---:|---:|
| L-diag | .189826 | .235469 | .189827 | 0 / 6 / 0 of 200 |
| L-cov | .189927 | .202184 | .189927 | 0 / 0 / 0 of 200 |

| Upstream | Primary T = mean(.1D+.9F-U) | Pointwise 95% CI | Retention R | 95% CI | Verdict |
|---|---:|---:|---:|---:|---|
| L-diag | +.004564 | [.004243,.004892] | .999996 | [.999818,1.000162] | **PASS** |
| L-cov | +.001225 | [.001041,.001422] | .999945 | [.999081,1.000799] | **PASS** |

`F/D/U` are the paired per-key logloss values from saved full, diagonal and uniform arms;
`T` is the linear 90% margin. Ratios above 1 are sampling noise, not a claimed improvement
over full Gamma. All four cells individually pass:

| Cell | L-diag T [95% CI] | L-cov T [95% CI] |
|---|---|---|
| U, 7 dB | +.004888 [.004349,.005417] | +.001016 [.000728,.001313] |
| U, 8 dB | +.003942 [.003241,.004645] | +.001280 [.000963,.001600] |
| G, 7 dB | +.005279 [.004856,.005699] | +.001460 [.001160,.001780] |
| G, 8 dB | +.004148 [.003551,.004748] | +.001145 [.000765,.001546] |

FER transitions from full to uniform are `0->0` for all 200 keys under both upstreams; there
is no failure change to interpret. Channel NMSE and data MSE also match the full arm to the
reported precision (e.g. L-diag NMSE .024835 vs .024835; L-cov .026482 vs .026482).

## Frozen verdict

Protocol and UG1/UG2 were committed before any new-arm outcome. Both informed forecasts pass:
UG1 p=.70, Brier .0900; UG2 p=.65, Brier .1225. Joint adequacy requires both upstream PASS and
is true. Bootstrap: 10000 draws, seed 20261029, resampling all 50 shared P1 frames jointly
across both variants and all four cells, with the actual resampled row denominator. The 90%
margin is a user-approved practical threshold, not an equivalence, noninferiority, mechanism
or novelty test.

## Interpretation and decision boundary

Tested component effect: in this old cohort, the full-Gamma advantage over the diagonal arm is
carried by the same-delay block of the uncertainty Gram; replacing the individual variances by
one average changes the logloss by about `4e-5` or less. The earlier co-delay-only question is
therefore answered affirmatively, and nonuniform per-symbol variance is not necessary here.

This supports retaining atom geometry (the same-delay kernel) while dropping the cross-delay
and nonuniform-variance terms, i.e. it weakens a claim that heteroscedastic symbol variance is
necessary. It does not distinguish structured exploitation from a generic expected-Gram/EIV
estimator: under uniform variance the generic estimator reduces to exactly this same-delay
block (see the
[positioning review](../../.trellis/tasks/10-20-sbl-freeze-replay/research/novelty-positioning-review.md)).
It also does not show that the dropped terms are irrelevant elsewhere.

Perturbation size was not recorded: the raw rows save the identity residual and the minimum
eigenvalues of the original and uniform Gamma, but not `||Gamma-Gamma_u||` or per-symbol
`v_pre`, so the norm cannot be reconstructed offline. The only saved proxy, on the gate frame
9100 (160 projection calls), is the relative change in minimum eigenvalue, median `5.0e-4`
(range `8.5e-6`..`1.1e-2`). This is consistent with a small perturbation but is not a
norm. Near-full retention may therefore partly reflect a small intervention rather than a
strong structural effect.

It does not prove a unique
mechanism for the original native-gain failure, does not establish novelty of the update
formula (the expected-Gram formula remains standard), and does not establish FER superiority,
noninferiority or deployment value.

Practical reading: a single average variance plus the same-delay kernel may be a sufficient
simplification. The current arm still computes the full Gamma twice per step (40 Gamma FFTs
plus 41 native transforms = 81 actual detector transforms), so this run makes no optimization
or cost claim. Precomputing the kernel for fixed support is a possible next engineering step,
not demonstrated here.

Strongest alternative to this comparison is the direct operator mapping to a published
structured soft-symbol EM/VI update; it is the right next step for novelty, while this arm
only answers whether the uniform-variance geometry is adequate. The old cohort, integer
delays, rho .3 and SNR 7/8 dB remain limits; no fresh frames, off-grid/rho/SNR extension,
tuning or automatic follow-up is included.

## Execution and provenance

Gate on frame 9100 / all four cells / both upstreams: 8 full replays, 8 new uniform calls and
8 observer-off calls, i.e. 24 receiver and 16 decoder calls, zero SBL. All saved full scores,
hashes, traces and observer parity passed. Main: 200 keys, 400 receiver and 400 decoder calls,
zero SBL; twelve single-thread shards exited 0. Aggregation validated 200 keys and wrote
`summary.json`. Observed filesystem span from `PRODUCING_COMMIT.txt` to `STATUS.txt` DONE is
41 s (not a process timer), within the 845 s / 3 core-hour cap.

Independent audit (`audit_uniform_gamma.py`, stdlib + NumPy, zero generator/SBL/receiver/decoder
calls) read all 12 raw shards directly and independently recomputed the pooled and per-cell
T/CI/retention, call counts, row qualification, projection tolerance and raw SHA256 inventory.
It reproduced the summary to the reported precision and wrote `verification.json` with
`pass: true`.

Pre-run engineering repairs, before the gate: added the missing
`test_aggregate_uniform_gamma.py` referenced by the source inventory, and relaxed one fixture
magnitude assertion from 0.1 to 1e-3 because the actual nonuniform-minus-uniform Gamma norm is
0.0396; the exact identity assertions were unchanged. Eighteen tests pass in the server AFDM
environment and locally. These are pre-run tests/engineering, not scientific outcomes.

- [Summary](afdm_sp_joint_unrolled/outputs_sbl_freeze_replay_20261020/uniform_gamma1/summary.json),
  SHA256 `8800e93c4959a33d5dc88bb915688acfa2ee4a88b0813f990738205d1d193bc8`: all cells,
  paired effects, source identity, raw/config/gate hashes.
- [Verification](afdm_sp_joint_unrolled/outputs_sbl_freeze_replay_20261020/uniform_gamma1/verification.json),
  SHA256 `0cccec85e37ebe09f6e103841090898d380acf1a13ff35dfb181e277f6b4c9eb`.
- [Config gate](afdm_sp_joint_unrolled/outputs_sbl_freeze_replay_20261020/uniform_gamma1/config_gate.json),
  [gate](afdm_sp_joint_unrolled/outputs_sbl_freeze_replay_20261020/uniform_gamma1/gate.jsonl),
  [status](afdm_sp_joint_unrolled/outputs_sbl_freeze_replay_20261020/uniform_gamma1/STATUS.txt),
  [producing commit](afdm_sp_joint_unrolled/outputs_sbl_freeze_replay_20261020/uniform_gamma1/PRODUCING_COMMIT.txt),
  [aggregate log](afdm_sp_joint_unrolled/outputs_sbl_freeze_replay_20261020/uniform_gamma1/aggregate.log).
- Twelve raw `rows_shard000.jsonl`..`rows_shard011.jsonl`, 9,947,895 bytes total, remain under
  `/data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_sbl_freeze_replay_20261020/uniform_gamma1/`;
  per-file SHA256 is in `summary.json` and `verification.json`.
