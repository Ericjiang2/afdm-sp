# Matched soft-Gram point update: minimal qualification

Date: 2026-10-21. Engineering qualification and one-key descriptive output, not a population performance result.

The full local Gaussian gain block preserves equivalent physical representations in both predetermined cases throughout20 steps. The matched diagonal block does not. This supplies an implemented, checked candidate for a later actual-support comparison; it does not explain the original upstream SBL Gamma reversal.

## Frozen construction

Use the pre-symbol moments that formed the existing B, then apply the gain fit after the unchanged native symbol update. Both arms have zero propagated gain variance, identical right-hand side and the existing zero-mean CN(0,I/P) working prior:

`M=B^H B+Gamma(v_pre)`, `b=B^H Y`, `alpha=noise*P`.

- Full: `solve(M+alpha*I,b)`.
- Diagonal: `solve(diag(diag(M))+alpha*I,b)`.

Only off-diagonals differ within this new update family. Either arm versus native point also changes its gain-update family, including the pseudo-observation/Onsager gain formula. M contains mean-regressor and uncertainty coupling; this is not a Gamma-only ablation. The local surrogate covariance is checked but never propagated. The hybrid native symbol iteration has no global AMP/VI correctness or convergence guarantee.

Uniformly duplicate every atom twice, initialize each copy with h0/2 and use the resulting1/(2P) coordinate prior. Both initial physical H and induced working prior stay unchanged. This control does not cover arbitrary partial duplication. [Derivation](../../.trellis/tasks/10-20-sbl-freeze-replay/research/full-gram-gain-block.md).

## Observation

No SBL was run. Use the already fixed n32/P2 synthetic fixture and old real key U/rho.3/7dB/frame9100 with its saved h0/support/check prior. The real support has24 atoms,48 after duplication. One additional n32/P3 mixed-delay/nonuniform-v fixture checks the fast Gamma contraction against independent dense operators; its relative difference is1.676e-15, minimum eigenvalue10.3275.

Native clone outputs, post-update states and traces are bit-exact in both cases. The real original native scores/h20 reproduce saved run2. Full all-step aggregate gains, physical action, non-gain states/traces, extrinsic/APP LLRs and local covariance pushforward pass the frozen rtol1e-10/atol1e-12 criteria.

| Duplicate comparison | Synthetic | Old real key |
|---|---:|---:|
| Full: max relative physical difference across20 steps | 5.398e-16 | 4.426e-15 |
| Full: final LLR maximum absolute difference | 1.066e-14 | 2.056e-13 |
| Full: all20 LLR maximum absolute difference | 1.066e-14 | 2.141e-13 |
| Diagonal: first-update relative physical difference | .976126 | .990782 |
| Diagonal: final LLR maximum absolute difference | 14.2084 | 51.9350 |

Physical relative differences use the original updated operator's Frobenius norm, not truth NMSE. Independent saved-matrix recomputation confirms first full/diagonal means, full covariance aggregation (max errors2.52e-17/2.17e-16) and diagonal difference formula (<=1.12e-16).

Single-real-key decoding is descriptive:

| Gain update | Original information-bit errors | Duplicated information-bit errors |
|---|---:|---:|
| New full | 0 | 0 |
| New diagonal | 351 | 406 |
| Frozen native point | 42 | 180, from the previous frozen representation probe |
| Frozen fixed | 0 | 0, from the previous frozen representation probe |

Full original final channel NMSE=.028398; diagonal=2.812763; native point=.046200. These are one-key outcomes, not an estimated FER effect. This old real key was predetermined for the preceding representation probe, not selected using these new outcomes. Existing full-Gamma/joint2 failures/200 and scalar-fixed4/200 remain the cohort performance references; this gate does not beat them.

## Frozen verdict and untested explanation

After the same-case observer completion below, G1 (p=.90) passes: native replay and full20 duplicate invariance in both cases. G2 (p=.85) passes: diagonal first physical difference>1e-8 in both cases. Brier scores.0100/.0225; these are code-derived engineering forecasts, excluded from independent mechanism/performance calibration.

Untested explanation, confidence L: preserving soft-Gram coupling may help on the actual correlated SBL support. Exact-copy invariance and a successful old key are insufficient to establish that explanation, near-duplicate causality, the original Gamma reversal, or overall receiver quality. No200-key study or additional tuning follows automatically.

## Cost and evidence

OneCPUthread, no GPU, EXIT0; first process5.11s wall. Gate body.6463s. Instrumented real original detector calls: native28.74ms, full42.22ms, diagonal41.76ms; duplicated full/diagonal70.03/69.65ms. These single calls include qualification eigenvalue/Cholesky/covariance work and are not optimized deployment-latency estimates. Native20 has41 FFTs; either new20 has61,20 gain solves and20 diagnostic covariance solves. No two-FFT cost claim is made.

First producing local source commit: `5d2feb6e`. Final review found that gate1 retained terminal LLRs but did not directly observe all-step LLRs. Preserve it unchanged. Wrapper `62f70a16` observes existing marginal outputs without changing returns, repeats only the same two cases into gate2 and completes all-step checks (5.00s wall, .6523s gate body). Every saved numerical algorithm field equals gate1 exactly, excluding clock fields. This is an engineering observability repair, not independent performance replication. Combined process wall10.11s; no new data or tuning.

Twenty-two local NumPy tests and all four new-module compilation pass. All added local source MD5s match producing metadata; local/remote evidence SHA256s match. Main independently checked saved numerical systems without receiver reruns.

- [Summary](../../afdm_sp_joint_unrolled/outputs_sbl_freeze_replay_20261020/gram_block_gate1/summary.json), SHA256 `0073259504edb1c97779745f86dba7b6f04be683667590306466cb5c3a063206`.
- [Verification](../../afdm_sp_joint_unrolled/outputs_sbl_freeze_replay_20261020/gram_block_gate1/verification.json).
- [All-step LLR receipt](../../afdm_sp_joint_unrolled/outputs_sbl_freeze_replay_20261020/gram_block_gate2/llr_gate.json), [gate2 verification](../../afdm_sp_joint_unrolled/outputs_sbl_freeze_replay_20261020/gram_block_gate2/verification.json), [gate2 summary](../../afdm_sp_joint_unrolled/outputs_sbl_freeze_replay_20261020/gram_block_gate2/summary.json) SHA256 `83c43e2e70ae5bfc79b27c6db49d71b9fc18bf519ffe19a9b33f01e0299d3cb8`.
- [Config](../../afdm_sp_joint_unrolled/outputs_sbl_freeze_replay_20261020/gram_block_gate1/config.json), [status](../../afdm_sp_joint_unrolled/outputs_sbl_freeze_replay_20261020/gram_block_gate1/STATUS.txt), [log](../../afdm_sp_joint_unrolled/outputs_sbl_freeze_replay_20261020/gram_block_gate1/run.log).

Remote evidence has the same project-relative path under `/data/guoyikun/00inbox/AFDM-channel-estimation/`. Original receiver, helper and result files are unchanged. Task stays open for user scientific acceptance; no claim promotion, automatic expansion or archive.
