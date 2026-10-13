# Research: Candidate admission after exact remainder diagnostics

- Query: Is the proposed local Gaussian/EP core admitted, and does one statistical-linearization revision address the actual failed assumption?
- Scope: internal evidence appraisal plus analytic derivation; no receiver execution.
- Date: 2026-10-03
- Status: **No-go for the specified single-global-affine residual-neglect core candidate on the registered diagnostic grid**, including justified revision 1. This is not a no-go for residual-aware EP or all local/nonlinear approaches.

## Evidence read

Current `experiments/afdm_inference_causal_20261002/{REMAINDER,ORACLE_COMPARISON,STATE_DIAGNOSTICS,PRIOR_INTERVENTION,SLR}.md`; original PLAN, current CSV CORE-01/REMAINDER-01 admission contract; this directory's joint-message-theory and literature-neighbors. These reports were inspected directly, not assumed from task status. This research does not independently rerun their numeric sources/raw receipts.

## Findings

### 1. Exact candidate definition and what failed

The candidate is a frozen first-order physical tangent around a single (h0,d0), with independent original gain prior, Gaussian/discrete block EP sites, full Gaussian cross covariance and lawful site subtraction. A later relinearization is a separately declared approximation. It is not simply CE prior unification, scalar precision replacement, or tail processing.

REMAINDER evaluates that tangent specifically at **exact global posterior marginal means** in a N=2/3 fixed-geometry model. Only 1/24 pilot-present conditions and 0/24 no-pilot conditions meet the preregistered screen requiring both remainder energy and absolute linear/remainder cross term ≤0.1 N sigma2. This is a failed **engineering admission criterion** for this tested global-mean tangent, not a mathematical necessary condition for every useful local estimator. It does not prove that a native detector's actual local mode or N=1024 posterior always fails. Conversely, no pilot-present subgroup with validated operational admissibility has been established, so a full-core prototype is not presently justified by this evidence.

No-pilot rotation symmetry is outside production SP scope; it is an informative symmetry stress test only. The more relevant pilot-present group still has mean remainder/noise energy 1.011864, mean absolute cross/noise 0.997634, and mean raw remainder energy 0.696543 versus linear energy 0.690104. Their mean cross contribution is −0.574059. Thus the failure is not solely driven by the no-pilot degeneration. These conditions have six exogenous clusters, not 48 independent channel draws; population or significance claims are inappropriate.

### 2. Other prerequisites weaken the original causal justification

- PRIOR_INTERVENTION: changing CE ridge precision alone is strongly attenuated by actual joint inference; median gain perturbation ratio .01064 after 20 steps. CE is initialization, so no implementation bug or principal failure mechanism has been established.
- STATE_DIAGNOSTICS: actual direction error is nonzero, but terminal stage has no success/failure overlap; six failures all end in f1_cstate. Its conditional known-data reference differs from the uncertain-data posterior. No adjusted causal link to FER follows.
- ORACLE_COMPARISON: pilot-present actual scalar_joint probability MSE .006657 and mean sharpness gap −.010200. Existing gain uncertainty improves substantially over point treatments. Exact product-of-marginals loses joint cross moments while retaining exact LLRs, so “missing cross moments implies wrong LLR confidence” is false without an algorithmic propagation argument.
- P-BiG-AMP already has the P*vh*vx second-order variance-product term. A new residual covariance term must repair an identified matrix/moment approximation; adding such a scalar term is not a missing-mechanism discovery.

### 3. Gaussian statistical linearization: exact scope and formula

Use augmented real coordinates z=[Re h,Im h,Re d,Im d] in a fixed, explicitly permuted convention. Any real output component of the bilinear forward map can be written
f_k(z)=c_k+b_kᵀz+zᵀA_k z,
where A_k is symmetric with off-diagonal gain/data blocks. For z=m+e with a **joint Gaussian** e~N(0,C), Isserlis gives exactly
m_f,k=f_k(m)+tr(A_k C),
J_k=b_kᵀ+2mᵀA_k,
Cov(f,e)=J C,
Cov(f)_kl=(J C Jᵀ)_kl+2 tr(A_k C A_l C).

Hence the best affine least-squares slope on the support of C is J, and the orthogonal residual has covariance
Omega_kl=2 tr(A_k C A_l C).
It is PSD because it is the covariance of the centered quadratic terms. Orthogonality Cov(residual,e)=0 does **not** imply Gaussianity or independence. The residual mean shift tr(A_k C) is essential; proper-complex independent block priors make some mean terms vanish, but posterior correlated/improper blocks need not.

Under independent gain/data Gaussian input blocks, the mean shift vanishes and the covariance reduces to the corresponding gain-covariance × data-covariance contraction (real and pseudo terms handled consistently). This is closely related to existing bilinear moment propagation. Full joint C adds cross-moment products; low P alone does not imply Omega has low rank or cheap inverse. Treating Omega as independent Gaussian noise is another approximation, not an Isserlis theorem.

Most importantly, a moment-matched joint Gaussian has zero centered third moments, so Cov(linear,quadratic residual)=0. The exact pilot-present mixture has a substantial negative linear/remainder cross term. Therefore merely adding an independent residual covariance to the old tangent—even if given the exact residual covariance—misses that observed cross contribution. Gaussian SLR cannot repair this particular non-Gaussian correlation by changing its slope, because its slope remains the tangent J.

### 4. Why the registered exact-posterior SLR revision is justified

For **any** finite-second-moment exact posterior, let Czz=Cov(z), Cfz=Cov(f,z). The optimal affine predictor is
f_aff(z)=m_f+K(z-m_z), K=Cfz Czz†,
with orthogonal residual covariance
Omega*=Cff-Cfz Czz† Czf.

Support compatibility Cfz(I-Czz†Czz)=0 must be checked; it follows analytically because any zero-variance z direction is deterministic. The Moore–Penrose inverse must use a declared rank rule with range checks, rather than silently claiming exact support removal for a poorly conditioned finite covariance.

For any alternative affine slope A with the optimal intercept,
E||f-[m_f+A(z-m_z)]||² = tr(Omega*) + tr((A-K) Czz (A-K)ᵀ).
Thus tr(Omega*) is a lower bound on mean-square residual of every affine predictor under this **fixed exact posterior**. This is a sharp finite diagnostic, not a lower bound on all receiver error or all nonlinear/mode-conditioned methods. The trace is unweighted; a weighted output norm uses the matching positive-definite weighting in both objective and comparison.

The revision can distinguish “wrong expansion center/tangent slope” from “irreducible non-affine posterior relation.” It uses the same sealed small-model posterior, zero new receiver calls, no new data population, and targets the observed failure. It is therefore a justified bounded revision within the CSV, not arbitrary scope expansion. The exact posterior moments are privileged diagnostic inputs; they cannot be passed to a claimed practical receiver. Even a successful best-affine diagnostic must be followed by a legitimate affordable moment/cavity source before CORE admission.

## Final admission and finite closure advice

The finalized `SLR.md` has now been read directly. It reports the exact best-affine revision also passes only **1/24 pilot-present conditions, 1/48 overall** at the unchanged 0.1 noise-relative threshold. Mean best-affine residual/noise energy is 0.339428 for pilot-present cases (range 0.000359–0.648728). Correcting the tangent mean reduces mean pilot residual energy from 0.696543 to 0.520314; changing to the optimal affine slope and intercept reduces it further to 0.337077. Therefore the revision genuinely improves the approximation, but does not satisfy its own admission criterion on 23/24 relevant pilot-present cases.

All 48 Czz matrices are positive definite; no positive mode was discarded. Minimum eigenvalue ratio is 1.407e−5 versus a 1e−12 cutoff; full-positive-support sensitivity is zero. Residual orthogonality error ≤7.12e−16 and direct/subtraction covariance difference ≤1.14e−15 support interpreting the measured result as the all-real-affine optimum within floating-point accuracy, not an artificially truncated lower bound. This strengthens the specific rejection beyond a poor tangent point choice. These numbers are read from the finalized report; this review has not independently rerun its source or recounted raw files.

**CORE admission: not satisfied.** The candidate requires that the omitted affine residual be small under the registered criterion; even privileged exact-posterior coefficients do not establish that on the pilot-present grid. There is also no deployable legal-message construction for those privileged coefficients. Proceeding to a full receiver and FER experiment would bypass the explicitly required approximation/message gate.

**Recommended finite closure:** close REMAINDER with the tangent result and one successful-to-execute but unsuccessful-to-admit SLR revision; close CORE as not admitted for this specific residual-neglect family. Close its dependent MECH/FRESH as not applicable because no admissible new core method exists, with **zero new core/FER runs and no same-budget advantage claim**. Preserve separately the actual prior intervention and scalar/oracle diagnostic calls; do not misstate the whole task as having zero experiments. CLAIM should report the mathematical and actual diagnostic findings, the hypothesis downgrades and candidate scope. REVIEW should check these against the raw contracts/receipts. A second revision is an allowed maximum, not a requirement to invent another approach after the causal hypothesis loses support.

This closure is justified by a conjunction: the proposed residual-neglect model fails its frozen screen, prior-only intervention has weak surviving effects, directionality lacks a stage-controlled practical association, and exact small-model comparisons refute the asserted universal overconfidence direction. None alone proves global uselessness. Together they do not justify spending full-cascade resources on the stated repair.

### What this does not close

A substantial residual can sometimes be represented explicitly rather than neglected. SLR residual orthogonality does not imply independence or Gaussianity; a residual-aware EP/SLR method would require its own distribution, cross-moment, message and complexity contract. The observed Gaussian third-moment mismatch explains why simply adding an Isserlis noise covariance is not that contract. No result here proves such a method cannot work.

Mode-conditioned inference, direct nonlinear factor EP and approximations to the exact-gain-marginal likelihood remain unrefuted. They change the inference family and can require mode acquisition or substantial new moment computation. They are not automatically owed full receiver runs under a finite CSV whose prerequisite gate has failed. State these as **untested spaces**, not promised innovations or evidence that innovation has been exhausted.

The best-affine result is conditional on the same previously exposed N=2/3 oracle posterior grid, not an independent production confirmation, not a bound on FER and not a theorem that all affine methods have inaccurate LLRs. No-pilot cases remain auxiliary; the closure does not rely on them. The 0.1 threshold is a prespecified engineering rule. A different tolerance might admit more cases, but changing it after these outcomes would be a new exploratory proposal and cannot retrospectively pass the existing gate.

## Caveats / Not Found

No new experiment, code modification, source hash verification or full performance audit was performed by this research agent. Main session and bilinear agent own the SLR computation and receipts. This final review has read all five named reports and derived the Gaussian-Isserlis vs exact-distribution SLR distinction independently; it is an admission appraisal rather than an independent numerical replication.
