# TF receiver exploration — independent mathematical probes

Date: 2026-09-22. Baseline under discussion: TF_J20_R2, production numerical source 2d130b4d.

## Evidence boundary

This directory contains **new, independent reference calculations**, not a replay of production TF, LDPC(2048,1024), or the final Part-B campaign. The September 17 ZIP is an older handoff, not a version-matched final TF implementation. Production stage-cost CSVs and failed-frame traces were not available here. No production FER or latency benefit, new-algorithm superiority, or publication-level novelty is claimed.

The current research judgment is conditional: investigate irreversible physical-hypothesis restriction and joint code/channel basin trapping before adding richer variance, a learned denoiser, or a curvature correction. The candidate methodological opportunity is **inexpensive generation of useful joint corrections**, not another noncoherent list evaluator. Existing noncoherent OSD, per-survivor processing, channel-hypothesis GRAND, NOMP, off-grid SBL and PBiGAMP/Newton methods are essential prior art.

## Run

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python probe.py
OPENBLAS_NUM_THREADS=1 python basin_probe.py
OPENBLAS_NUM_THREADS=1 python verify_saved_witnesses.py
```

Requirements: NumPy and SciPy. `environment.json` records the versions used. Seeds are fixed. The JSON outputs and NPZ witnesses are supplied. The scripts do not read any remote data, use training labels for a deployable algorithm, or modify the frozen receiver.

## What was tested

### 1. Raw non-Gaussianity is not necessarily a detector gap

At N=64, the normalized fourth cumulant of one half-bin AFDM path's QPSK response is -0.33349609375. Yet for known nonzero gain h and unitary physical path U, `U^H y/h - p = d + U^H w/h` exactly. A separate nontrivial CPP fixture verifies the identity with maximum error 2.59e-14. Thus raw fractional leakage does not, by itself, justify a Gaussian-mixture detector.

### 2. Average nuisance variance does not control all likelihood directions

An exogenous local Gaussian surrogate has covariance `sigma2 * (I + Q Q^H)`, with eight orthonormal nuisance directions in N=1024. The average variance increment is 0.78125% of thermal noise, but the exact precision in a nuisance-aligned direction is halved. An isotropic trace approximation gives 0.992248 rather than 0.5. In 2,000 random directions, the mean nuisance overlap is only 0.007774. This negative control matters: production codeword contrasts must be shown to align with relevant nuisance directions before inferring receiver-level benefit.

This is NOT a claim that a posterior covariance estimated from the same received block is an independent generative-noise covariance.

### 3. Missing-information curvature exists, but a curvature-only rescue is not supported

A fixed N=8, two-dimensional-real-gain, known-fractional-path model uses a deterministic random binary linear (16,8) code (256 QPSK codewords), rho=0.5, Gaussian gain prior, and complex noise variance 0.35. The E-step exactly sums the codebook. These are not LDPC or TF experiments.

For negative log marginal likelihood, the exact Hessian is the mean complete-data Hessian minus the covariance of code-conditioned score vectors, plus prior curvature. Finite differencing agrees within 2.98e-6.

Among 256 generated observations, negative observed curvature appears at 30 initializers but only one final iterate after 20 exact EM updates. There are 119 final EM code errors; only one has negative final curvature. Exact gain-marginal MAP has 107 errors (17 paired rescues and 5 harms relative to EM); known-gain MAP has 94. These descriptive toy counts do not estimate production headroom. They weaken a generic 'detect negative curvature and escape' recommendation.

### 4. A strict, positively curved wrong code/channel basin

A constructed N=64 two-word QPSK code, rho=0.5, one known full-fractional/CPP path, and a nearly aligned deterministic pilot phase pattern gives a counterexample. The observation is noiseless, while the receiver uses a positive noise variance 0.05 and a CN(0,1) gain prior. Starting from the gain fitted to the wrong word:

- Fixed-gain residual squared: wrong word 0.373650; true word 11.227967.
- Candidate-specific regularized gain refit: wrong 0.373650; true 0.000129556.
- After 100 exact-code EM updates: true-word conditional probability 5.26e-95.
- After exact gain marginalization: true-word probability 0.999770895.
- Conditional wrong-word gain variance: 0.000459333.
- Final observed Hessian eigenvalues: both +4354.14.

Thus small conditional gain variance, an exact constellation/code E-step, and positive local curvature can coexist with a wrong joint explanation. A finite joint code/gain move is needed in this witness. The low-rate code and specially chosen pilot are deliberate; no claim is made that this event occurs in the production ensemble. A phase-spread pilot negative control escapes to the true word under the same EM procedure. This is not a pilot-design recommendation.

`verify_saved_witnesses.py` independently computes the two exact likelihoods using dense 64x64 observation covariances. It reproduces the saved marginal posterior. It also checks the proposed local nuisance-profile Schur metric against augmented least squares for 20 binary patterns, maximum error 1.14e-13.

### 5. An immutable missing-delay representation error

For three physical paths with distinct delays but a working span containing only two, even a true-channel Frobenius projection has a nonzero error equal to the missing path's energy. The chosen numerical witness gives 11.8881%. This is a model-span fact, NOT an FER floor or an estimate of current acquisition miss frequency.

## Potential mechanism and unresolved step

At a hard decision c_hat, QPSK changes caused by a binary error vector e are exactly affine: `delta_d = D(c_hat) e`, with parity constraint `H_code e = H_code c_hat (mod 2)`. A local real-valued physical linearization gives residual `r - A e - J eta`. Profiling small continuous channel corrections produces

`Q(e) = ||r-Ae||^2 - [J^T(r-Ae)]^T (J^T J + Lambda)^(-1) [J^T(r-Ae)]`.

Here Lambda is a declared local regularizer, not an independent prior learned from the same observation. This is an exact Schur identity for the linearized surrogate; omitted bilinear/geometry terms require exact full-path candidate checks. Original gain-prior centering must be handled correctly in an augmented formulation. A fixed-J proposal factorization is reusable; exact candidate-dependent refits are additional cost.

The prospective research question is whether this coupled metric can guide **code-feasible candidate discovery** at lower complete cost than ordinary reliability-ordered candidates followed by the same noncoherent scoring. The Schur identity itself is standard and is not the novelty. If candidate discovery remains expensive, or ordinary noncoherent OSD / random channel restarts match the result, this direction should be killed as a stronger-method paper.

## Core primary literature checked

- Coşkun, Liva, Östman and Durisi, *Low-Complexity Joint Channel Estimation and List Decoding of Short Codes*, arXiv:1901.05409 (2019): pilot-derived list generation and noncoherent list selection.
- Wiame, Duffy and Médard, *Joint Error Correction and Fading Channel Estimation Enhancement Leveraging GRAND*, arXiv:2506.14756 (2025): multiple nearby channel hypotheses, repeated ORBGRAND and posterior selection.
- Raheli, Polydoros and Tzou, *Per-Survivor Processing*, Digital Signal Processing (1993): candidate/survivor-dependent unknown-parameter processing.
- Mamandipoor, Ramasamy and Madhow, *Newtonized Orthogonal Matching Pursuit: Frequency Estimation over the Continuum*, arXiv:1509.01942: birth, continuous refinement and cyclic refitting.
- Luo et al., *Data-aided Channel Estimation and Sensing With Sparse Bayesian Learning for AFDM-ISAC System*, arXiv:2607.18881 (2026): direct SP-AFDM data-aided grid evolution/SBL/GAMP overlap.
- Louis, *Finding the Observed Information Matrix When Using the EM Algorithm*, JRSS B 44(2), 226–233 (1982): missing-information curvature and EM acceleration.
- Wang et al., *PBiGAMP-Based Joint Channel Estimation and Data Detection Under Nonuniform Doppler Shifts*, DOI 10.1109/JOE.2025.3565111 (2025): rely on the supplied equation-level novelty audit for the detailed NDS comparison; the current investigation independently verified the publication record, not a newly retrieved full NDS manuscript.

See CODEX_REQUEST.md for the production investigation that would decide whether either opportunity is useful.
