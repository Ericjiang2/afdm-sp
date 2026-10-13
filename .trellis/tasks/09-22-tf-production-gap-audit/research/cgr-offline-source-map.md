# Bounded source/timing reconciliation for the offline CGR diagnostic

This is the brief Astra/main static reconciliation. Runtime saved-array identity checks, analytical JVP qualification and final evidence review belong to Sol; NPZ availability/source-seal hash checks belong to Luna. This note does not claim that the new transport prediction has succeeded.

## Exact source map

`run_observed._branch` supplies one fixed `entering.check` prior to `scalar_joint(iterations=20, damping=.3, gain_mode='joint', record_states=True)`, then calls `decoder_messages` once with `clip(extrinsic,-20,20), maxiter=50`. The new analysis reads its saved input/output; it must not call either routine.

Each saved scalar TF state has mixed timing: `h_pre` is input gain; `hbar`/`xbar` are the newly damped barred means; `s`, `alpha`, `bar`, `vp`, `vr`, `vq` are this step's updated residual/precision quantities; `h`, `mu`, `v`, `x`, `vh` are post-denoiser outputs. The data expression uses input `mu` and input scalar gain variance, not same-row output `mu`/`vh`: at step0 obtain moments from fixed entering.check and u=1/P, and subsequently use the previous saved row. `Bb` equals B(xbar) by linearity, including the initial step; prior is never updated inside TF20.

The data marginal executes before the gain-mean output is stored. It does not recompute data LLRs from that post-update gain. Thus the final gain-only impulse has exactly zero path to that batch's returned data LLRs. Gaussian gain output differs at a common state by `-alpha*N*vx/(P+1/vq) * (M-I)@hbar`; no extra damping factor multiplies this post-denoiser impulse. Damping enters the barred-state/residual histories instead.

`messages.marginal` computes raw APP log-odds, extrinsic=APP-prior and softmax moments with no LLR clipping inside TF. Its data variance has max(pd-|mu|²,0). The actual all-I then all-Q decoder input is clipped only at the wrapper boundary. With input mu and u, gamma=1/vr, omega=alpha*P*u, the exact unrounded QPSK identity is f=gamma*mu+H(hbar)^H*s-omega*xbar and Lext=(4a Re(f),4a Im(f)); saved-array comparisons must quantify finite-precision residuals. The analytical derivative must honor max/floor and declared one-sided clipping behavior.

## Old physical-anchor and normalization check

`analyze_r2._physical_error` evaluates unnormalized Frobenius squared mismatch as N times the augmented-path quadratic form. Its physical_trace rows use saved `state.h` (post-update BASE gain), and compare that with `state.h + common.dh`. The anchor matches the protocol's post-update intervention. No old-anchor discrepancy was found in static source inspection.

The producer's `base_common_state.physical_norm_squared` stores dh^H R dh without N. Therefore the new finite/infinitesimal panel must use Q=N*dh^H R dh, retain the original D, and set A=D+Q. Summing rows from different BASE states is descriptive only. No new local panel revises the old engineering gate.

## Source byte identities at inspection

| File | SHA-256 |
| --- | --- |
| `experiments/tf_cgr_mechanism_20260923_v2/tf_base.py` | `0e3a94045b0b395c28efa02f181433bbc3aa2f569c05683ad83e1d1cf4f9699e` |
| `experiments/tf_cgr_mechanism_20260923_v2/tf_cgr.py` | `bd501df2e6b20dd19fd89da59c82a11efad3d80824ebbfbbb471b953eb7e0f85` |
| `experiments/tf_cgr_mechanism_20260923_v2/tf_sham.py` | `899998232217c3dd9a54288781fc906fe071f14005f426b682d939dd565a08fa` |
| `experiments/tf_cgr_mechanism_20260923_v2/run_observed.py` | `dbec307da176a328c36622f9e25ae512de0b4afb821f7f0de5175e2b7d9d9796` |
| `experiments/sp_afdm_frozen_20260920/src/messages.py` | `9b19937c90a6e2b15f30d4e326320a38cd2635f9c0c5b14814406991da25ec95` |
| `experiments/tf_cgr_mechanism_20260923/analyze_r2.py` | `8c8fb1c236f4ebec322051b89bf7395a5886a3aaa8f3e5de57d4ca496ec5b452` |

Luna independently verifies the producer/source identities against the actual observed inventory. The r2 analyzer has its own recorded revision history; its identity is not represented as part of the earlier producer seal.
