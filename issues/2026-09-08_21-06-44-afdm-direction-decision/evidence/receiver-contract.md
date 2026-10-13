# P0-01 Receiver and information-flow contract

Evidence: source inspection only, zero receiver calls. Source SHA256 manifest in `source-manifest.json`; numerical/runtime verification remains NUM-01/AUDIT-00. Existing E1/B0/A2 are separate identities.

## Frozen current B0

Entry `v3_baseline_run.py:43` → `build_receiver` (`budgeted_support_eval.py:89`) → `run_frame(... arms=['a0'], receiver_shell='direct40', active_cap=40, initial_estimator=InitialEstimator('b0',None))`. N1024, rho0.5, physical paths8, kmax2/lmax102, Config-A velocity2/tau10ms/fs-factor4, fractional leakage halfwidth2 and relative power prune0.01. OMP nomination40, receiver_extension0, repair off; physical generator leakage remains2. Ten outer updates, 20 BP iterations each, final extra20 BP then LDPC max50. No early outer stop. Checkpoint `ckpt_c2rel.pt.force_topk` SHA256 `052ecfab8eff7780c49038d9bb4f16f92272ee22322fa05b6f65029cc3112a91`; checkpoint values require runtime parameter fingerprint at NUM-01.

OMP (`classical_joint_unrolled.py:121`): raw absolute Phi^H residual correlation, no additional column normalization; excludes already selected indices, torch least-squares after each selection and final refit; early residual norm <1e-10*norm(y), at most40 steps. Constant-modulus pilot gives equal column norms; verify in P0-03. v3 size/ridge/SBL replace only initialization, downstream unchanged. SBL maximum20 EM iterations, relative update1e-4, fixed observable initial noise; nonconvergence reported, not hidden.

## Physical generator and pilot

`afdm_env.py:553-663`: one physical complex gain multiplies normalized Dirichlet weights. Truncation clips integer Doppler then prunes relative weight power. Matrix Frobenius scaling sqrt(N)/norm(H) rescales all physical/expanded gains together; mapping is linear in **normalized** physical gains, not globally linear from raw gains through normalization. Physical l_i/k_real/g_i and expanded coefficients retained; per-expanded path_id must be reconstructed before merge. No claim that independent atoms erase generator structure: it is the receiver parameterization that does not enforce the relationships.

Pilot is the DAFT-domain Zadoff-Chu-like unit-modulus vector `_zc_seq` (`afdm_env.py:131`), already multiplied by sqrt(rho) in `make_frame` (`budgeted_support_eval.py:123`). Data is already scaled sqrt(1-rho); noise variance is10^(-SNR/10). Therefore runtime cancellation is `y-H@pilot_scaled`: multiplying again by sqrt(rho) is an error. Actual tx-vector energy and cross-term must be recorded, without per-frame renormalization. This harness uses the analytical DAFT channel directly and has no explicit time-domain CPP insertion/removal stage. Its phase convention is frozen; k_guard=4 clips the supported Doppler domain. Do not claim physical CPP overhead was separately simulated. No new guard/CPP resource is introduced.

## H, covariance, graph and sigma versions

`classical_joint_unrolled.py:1970-2030`: DA-LS at outer1..9 uses previous H to form finite-QPSK soft data, then columns G_i*(pilot_scaled+soft_data) and a proximal regularized gain solve. For mean mode, objective is ||y-A*g||²+lambda*||g-g_previous||², lambda=max(hp.lambda_ls_factor*sigma2,1e-6); uncertainty modes are different registered objectives, not silently active in B0.

`classical_joint_unrolled.py:2100-2208`: reconstruct current active H, damp with gamma_h, soft magnitude threshold; this new H is used for cancellation and data detection. H_corr is zero unless its separate optional head is instantiated. BP reconstructs edge list from the passed H each invocation (`mp_detect_bp_torch.py:66`), threshold1e-4; no persistent graph cache. Internal BP computes in complex128/float64 even when outer H is complex64. Each call starts prior messages; final BP is another fresh graph invocation.

Within an outer iteration, cancellation H and detector H are the same current version. The H used to compute preceding DA-LS data confidence is the previous outer version, intentionally staged. Mean B0 has no full covariance consumer; its H-derived column energies are confidence approximations. After detection/symbol damping, sigma2 is updated for t>0 as 0.7*old+0.3*max(||y-H*(pilot+soft_data)||²/N,1e-12). Thus updated sigma is consumed by the **next** outer iteration; final terminal BP consumes the newly updated last sigma. It is variance, not standard deviation, not an exact thermal-noise estimate.

Terminal observer (`budgeted_support_eval.py:323`) captures H, sigma2, raw y, scaled pilot and scaled constellation before the final BP. Full graph summaries and support trace are available through graph_observe. New factorial runner must reconstruct all H_D-derived quantities and rerun cancellation on every cell; cannot reuse a prior cell's graph, means or variances. H_cov_source must describe the actual consumer or `not_used`, never invent a covariance input.

## LDPC and feedback

`e1_ldpc.py`: n2048, dv3/dc6, seed20260726, actual k from GF(2) rank (not assumed1024), generator SHA256 `bfd4247263adedc9a095b87603c2a7a4c2f2e8cb83f7e78bad721c5b06eaa6af`. Bits are all I then all Q; identity interleaver currently, not a free random permutation. LLR=log(P0/P1), positive favors zero; Gaussian demap4*amp*mu/var, amp=sqrt((1-rho)/2), clip20. Decoder flooding sum-product, syndrome early stop, max50. Final decode has no path back to outer estimation/detection (`budgeted_support_eval.py:333`). Existing soft CE feedback is not decoder extrinsic feedback. I1 needs an explicit new consumer and factor-message derivation.

## A2 cost gate

Original contract `.trellis/tasks/09-05-budgeted-support-repair/design.md:137`: **both** mean and p95 <=1.1×same-harness achievable F2-P A2; memory<=22GiB. At least1000 timing frames across>=10 interleaved blocks, >=10 warmup frames, batch1, fixed CPU threads, CUDA synchronization and no same-GPU concurrency. Block-resampled interval upper<=gate passes; lower>gate fails; overlap is insufficient evidence. Generation/IO excluded from original deployment timer, necessary transfer/init separately reported and also included in new full-cost report. Extra final BP, prior/scorer work and LDPC are counted; A2 unavailable means gate unverified. Current B_star is not a substitute denominator.

Review: traced actual generation → model → cancellation → fresh BP → LLR → LDPC; no source edits or receiver execution. This is main-session static inspection, not the future independent implementation audit.
