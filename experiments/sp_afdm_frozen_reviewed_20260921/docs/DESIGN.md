# Frozen scientific design: coded SP-AFDM with a matrix-free fractional-path interface

Date: 20 September 2026. Version: SPAFDM-FREEZE-20260920-v1.

## 1. Decision and claim contract

The architecture is retained, but its claimed novelty is narrowed. Full-mean preservation with weak-edge Gaussianization is partial soft interference cancellation, not a new inference principle. LDPC extrinsic feedback, APP-based channel refinement, variable projection, sparse Bayesian grid evolution, and hybrid strong/weak graphs are established. The potentially publishable contribution is an exact, matrix-free implementation of the fractional-path statistical interfaces required by a coded receiver, coupled to a measured, conditional complete-cost benefit. Ordinary Transactions publication is not established by a new acronym or by the identities alone.

The central thesis is: a compact full fractional-path estimate can supply full mean responses, code-conditioned projected moments, and per-row weak-edge uncertainty without constructing a dense AF-domain channel. A separately sparse graph can then use these quantities. The claim is about computational realization and its useful operating regime, not a newly exact posterior, new turbo principle, or guaranteed frame-error improvement.

The supplied I1 remains the preterminal backbone. It still constructs dense quantities. Therefore the delivered complete receiver is not claimed to have subquadratic memory or complexity. The new refinement/terminal stage avoids an additional dense physical matrix; complete savings must be measured.

Three connected prospective contributions are frozen:

1. Exact fractional-path reductions for projected CE uncertainty, cyclic-diagonal innovation energies, and rowwise omitted variance, including degeneration conditions and a coherent multipath treatment.
2. An executable coded receiver that uses one full physical refinement and a separately sparse, mean-preserving terminal inference model with a correct information-flow contract.
3. A reproducible complete-cost comparison against native coded grid-evolution SBL/GAMP, parametric bilinear Gaussian message passing, and structured dual-domain EP adaptations, as well as matched-front and same-channel controls.

The third item is an experimental contribution to be established locally, not an already demonstrated result. The first two are implemented and checked as described below.

## 2. Hostile novelty audit

### 2.1 Abstract form

Let y=H(theta)(p+d)+w, d restricted by a linear code, and let a practical receiver provide product working marginals q(d)=product_k q_k(d_k). Write mu=E_q d and V=diag(v). For a frozen estimated channel Hbar and sparse matrix G, R=Hbar-G:

    y - Hbar(p+mu) + G mu = G d + R(d-mu) + w + physical-model error.

A Gaussian weak-edge approximation replaces R(d-mu) by its frozen mean zero and some representation of R V R^H. This is partial soft IC / a hybrid strong-edge Gaussian approximation. It is also related to preconditioning when used in a linear iteration. No additional observation or previously unavailable information is introduced.

E-JSG, Section IV and equations (54)-(55), already retain weak-edge mean and variance aggregates and select complete cyclic shifts. Its displayed implementation uses common weak-edge aggregate moments; the present implementation retains the nonuniform per-symbol working moments. This is a more precise implementation contract, not a different inference family. Its importance must survive a same-statistics implementation comparison.

PBiGaBP already uses soft interference cancellation and Gaussian approximation of residual uncertainty. Its code-symbol prior can be replaced by an LDPC check-extrinsic prior. Conventional coded SP-OTFS already feeds decoder-informed symbol replicas back to CE. Neither adding LDPC nor retaining a pilot term is novel.

D-GESBL's equations (31)-(32) give the familiar Gaussian SBL posterior. Grid evolution and data-aided refinement already occupy the broad off-grid-SP-AFDM combination. Our local physical variable projection is not a new off-grid family.

EP-T equations (35)-(37) use a Gaussian time-domain approximation and quasi-banded precision. Domain projection and finite-alphabet inference belong to the comparator, not a weakness to suppress by using a dense unstructured baseline.

### 2.2 What survives

Gamma=E[Phi_e^H Phi_e] is standard complete-data second-moment algebra. The Dirichlet/Fourier formula below is a specific efficient evaluation of it. Cyclic-diagonal energy ranking is separable fixed-cardinality optimization once the energies are known. Neither is a deep new statistical theorem.

The useful technical result is the complete computational chain: fixed physical paths plus diagonal working symbol moments produce Gamma, all diagonal energies, selected coefficients, full mean action, and exact rowwise weak variances without a dense H. The final row-variance calculation is important: retaining only a scalar sum of omitted energy does not implement the same rowwise Gaussian model as a dense weak-edge receiver.

No exact equivalent of this entire three-output physical-path implementation was located in the inspected closest papers. This is a bounded literature conclusion, not a proof of historical firstness. The paper should claim the explicit computational reduction and measured benefits, not a generic first use of full-model/sparse-inference separation.

### 2.3 Prior-art references and equation map

[L1] Q. Luo et al., Joint Sparse Graph for Enhanced MIMO-AFDM Receiver Design, arXiv:2503.19143v1. Section IV, weak aggregates (54), cyclic-shift eSNR selection (55). https://arxiv.org/html/2503.19143v1

[L2] Y. Luo et al., Data-aided Channel Estimation and Sensing With Sparse Bayesian Learning for AFDM-ISAC System, arXiv:2607.18881v1. Sections III-IV, posterior (31)-(32), hyperparameter and grid updates; GAMP acceleration. https://arxiv.org/html/2607.18881v1

[L3] K. R. R. Ranasinghe et al., Joint Channel, Data, and Radar Parameter Estimation for AFDM Systems in Doubly-Dispersive Channels, IEEE TWC 24(2), 1602-1619, 2025; arXiv:2405.16945v4. Section III-A, signal/gain SIC, cavity beliefs (38)-(41), denoisers (42)-(43), Algorithm 1. https://arxiv.org/html/2405.16945v4

[L4] A Novel Low-Complexity Dual-Domain Expectation Propagation Detection Aided AFDM for Future Communications, arXiv:2603.29218v1. Section III-C, time-domain Gaussian model and precision (35)-(37), cavity removal and domain projection. https://arxiv.org/html/2603.29218v1

[L5] Y. Kanazawa et al., Superimposed Pilot-Based OTFS: Will It Work?, arXiv:2501.15935v3. Decoder-aided data feedback and iterative schedule. https://arxiv.org/html/2501.15935v3

[L6] F. Huang et al., Message Passing-Based Joint Channel Estimation and Signal Detection for OTFS with Superimposed Pilots, arXiv:2309.08177v2. BEM and BP/mean-field joint inference. https://arxiv.org/html/2309.08177v2

[L7] M. Tuchler, R. Koetter, and A. C. Singer, Turbo Equalization: Principles and New Results, IEEE Transactions on Communications, 2002. Classical a-priori-aided interference cancellation/equalization. https://ieeexplore.ieee.org/document/1006557

The mathematical contracts below are independently derived for the exact sign convention in the supplied executable code. They are not transcriptions of every published implementation or reproductions of published curves.

## 3. Signal and information contracts

N useful samples; integer delays; fractional Dopplers; gains and delays/Dopplers fixed within a block; adequate CPP; ideal synchronization; proper thermal noise E|w_n|^2=sigma^2. Full physical propagation is always used. Neither omitted leakage nor a truncated channel is renormalized.

The principal implementation uses N=1024, the frozen (2048,1024) code, all-I-bits-then-all-Q-bits ordering, and internal data alphabet {+/-0.5 +/-0.5j}. Thus P_d=0.5. External pilot fractions other than 0.5 are supported by a uniform input unit transformation: divide y and p by a=sqrt(2(1-rho)), divide sigma^2 by a^2, and retain the same channel. This makes the data energy 0.5 without changing the inference problem. Do not apply the power fraction a second time to symbol variances.

Positive chirps and Doppler are used:

    A = Lambda^+_c2 F Lambda^+_c1,
    U(l,nu) = A C_l Delta^+_nu Pi_l A^H,
    D_N(t) = (1/N) sum_n exp(2 pi j n t/N).

Each U is unitary; a multipath sum need not be. The independent tests explicitly construct F, CPP and the time-domain delay matrix rather than calling the fast kernels.

The explicit entry is

    U(l,nu)[m,k] = exp{2 pi j[-c1*l^2-k*l/N+c2(m^2-k^2)]}
                    D_N(k-m+nu+2*N*c1*l).

q is a receiver working distribution, not the exact codeword posterior. Channel refinement consumes approximate APP moments from the latest detector with the currently retained decoder check prior. The proper-complex complete-data squared loss depends on V, not an additional pseudo-covariance term. Pseudo-covariance can matter in Gaussian detection approximations and is an optional ablation, not silently declared zero in reality.

### Correct message routing

Let L_DET be the detector's prior-excluded bit likelihood, L_C the LDPC check prior, and L_APP the relevant posterior LLR. Detector-to-decoder output is formed by marginalizing symbol weights and subtracting the target bit's own input L_C. In a coupled I/Q likelihood, the other bit prior remains in the marginalization.

For each LDPC call, retain its actual incoming LLR and raw APP. Its new check prior is raw_APP - actual_incoming, clipped to the declared finite bound. Replace the old check prior; do not accumulate APP. The CE marginal includes observation information and applicable code information: it is APP-like, not check-extrinsic alone.

When the channel or graph changes, reset observation-factor messages. Retaining the last LDPC check prior is a standard approximate turbo initialization; it is not proof of independence from the reused observation. The new detector must remove this prior before a further decoder call.

No same-observation CE estimate is treated as an independent Gaussian prior. The physical gain ridge is zero centered. Native bilinear inference uses an exogenous zero-mean gain prior and an observation-derived starting mean, not a new independent measurement.

## 4. Propositions and proofs

### Proposition 1: frozen-q complete-data objective

For Phi_mu=[U_i(p+mu)],

    E_q ||y-H(h)(p+d)||^2
       = ||y-Phi_mu h||^2 + h^H Gamma h,
    Gamma_ij = tr(U_i^H U_j V),  Gamma >= 0.

Proof: write d=mu+e; the cross term vanishes under frozen q; expand E||H(h)e||^2. Positive semidefiniteness follows from nonnegativity of this expectation for every h. With lambda>0 the gain minimizer is unique:

    h = (Phi_mu^H Phi_mu + Gamma + lambda I)^-1 Phi_mu^H y.

The variable-projection Doppler search is locally decreasing only for this frozen objective. Approximate APPs and later feedback do not inherit global EM or FER monotonicity.

For two uncertainty matrices Gamma and Gamma0, let h0 solve the Gamma0 problem and Q_Gamma be the Gamma information matrix. Then

    h0-h_Gamma = Q_Gamma^-1 (Gamma-Gamma0) h0.

This controls gain-update sensitivity, not communication risk. It provides a useful scalar-vs-full diagnostic.

### Proposition 2: Fourier evaluation of Gamma

For V=diag(v), define vhat(r)=sum_k v_k exp(-2 pi j r k/N). Then

    Gamma_ij = exp{2 pi j c1(l_i^2-l_j^2)}
               D_N(nu_j-nu_i + 2 N c1(l_j-l_i)) vhat(l_j-l_i).

Proof: multiply corresponding entries of U_i and U_j, sum over output rows, and use finite Fourier orthogonality. The c2 phase cancels. The remaining column phase is a Fourier sample of v. This uses the full CPP model and does not truncate fractional leakage.

Computational cost: O(N log N + P^2). The diagonal is sum(v). With distinct delays and uniform v, off-diagonal entries vanish. With one path, there is no nontrivial off-diagonal correction. Integer monomial/noncolliding-shift special cases also reduce to scalar regularization. These are useful degeneracies, not failures of the formula.

### Proposition 3: all cyclic-diagonal energies

Let s=(m-k) mod N,

    D_si = D_N(nu_i + 2 N c1 l_i - s),
    C_ik = h_i exp{-2 pi j(c1 l_i^2 + l_i k/N)}.

Apart from the common unit-magnitude chirp, H[k+s,k]=(D_s C)_k. Let

    W_ij = h_i h_j^* exp{2 pi j c1(l_j^2-l_i^2)} vhat(l_i-l_j).

Then

    E_s = sum_k |H[k+s,k]|^2 v_k = D_s W D_s^H,
    sum_s E_s = h^H Gamma h.

Proof: expand the squared coherent path sum before averaging over k. The remaining phase-weighted sum is vhat(l_i-l_j). This matters when multiple fractional paths contribute to the same diagonal; independently summing their powers is not equivalent.

All N energies cost O(NP^2 + N log N), and M selected diagonals cost O(NMP). Their complex coefficients are generated directly, with no dense H.

### Proposition 4: restricted optimal mask and centering

For a mask S containing complete cyclic diagonals and G equal to Hbar on that mask,

    D_S = tr((Hbar-G) V (Hbar-G)^H) = sum_{s not in S} E_s.

For equal per-diagonal work, selecting the M largest E_s minimizes D_S among masks of cardinality M. Proof: a swap of a retained lower energy with an omitted higher energy cannot increase the residual sum. This is not optimality over arbitrary sparse graphs or optimality for FER.

Raw sparse-model substitution has frozen-q distortion

    ||(Hbar-G)(p+mu)||^2 + D_S.

Full modeled mean preservation has distortion D_S. Proof: center d-mu and apply its zero mean. The identity is classical soft cancellation, not a new architecture.

If v is identically zero then every mask has zero frozen innovation distortion, even though the hard decisions may be wrong. A minimum graph degree and a fixed cap are retained; a small D_S is not a decoder-correctness certificate.

### Proposition 5: exact rowwise weak covariance diagonal

For R=Hbar-G, define the omitted-diagonal mask b_s and

    a_ij[s] = b_s D_si D_sj^*,
    z_ij[k] = v_k exp{-2 pi j(l_i-l_j) k/N},
    kappa_ij = h_i h_j^* exp{2 pi j c1(l_j^2-l_i^2)}.

Then

    [R V R^H]_m,m = sum_{i,j} kappa_ij (a_ij *_circular z_ij)[m].

Proof: put s=m-k in the expanded row energy. The quadratic output/input chirps cancel in absolute squared coefficients. The remaining sum over k is precisely a circular convolution. Conjugate pair symmetry permits P(P+1)/2 convolutions. The implementation checks significant negative numerical results rather than silently accepting an invalid variance.

Cost O(P^2 N log N); storage can stream pairs and is O(NP+NM+P^2). This gives the exact heterogeneous-symbol row moments of the chosen working model, not just a single tail-energy scalar.

An analogous sum without conjugation gives diag(R diag(t) R^T) for symbol pseudo-variances t. Its input sequence additionally contains exp(-4 pi j c2 k^2); the output contains exp(4 pi j c2 m^2). Implemented and independently checked, but not in the primary proper-Gaussian receiver.

Disjoint entry masks do not imply G V R^H=0 globally. Nor does diagonal-q covariance make the true residual white, Gaussian, or independent of the observation used to produce q. Gaussianization and cross-row independence remain the message-passing approximation. Under product q and a retained target edge, the omitted same-row term contains no target symbol, which supports the local cavity construction, not a global independence theorem.

## 5. Exact minimal receiver

1. Run the supplied formal I1 preterminal loop with the B0-p2 initializer, explicit full-rank `gels` least-squares driver, 10 outer iterations, 12 BP sweeps and code checkpoint 1. Its upstream files are unmodified. The preterminal state is verified against the full upstream adapter. No old terminal pass is performed and discarded.
2. Use the latest finite-alphabet APP mean/variance with its retained check prior. There is no new decoder call solely to obtain CE moments. Fresh-decoder APP is an ablation.
3. Group observed integer support by delay; retain up to eight strongest groups; seed one Doppler per group from its strongest observed integer coefficient. Missing delays are not created by this refit. Search two bounded coordinate passes, initial center +/-0.75 clipped to [-3,3], scalar x tolerance 0.002, at most 16 scalar evaluations per update. Gain solve uses lambda=sigma^2. Fixed waveform transforms and Fourier variance samples are cached once per refit.
4. Use the full Gamma objective. Scalar Gamma and mean-only correction remain mandatory ablations. Full Gamma is chosen for a consistent cheap objective, not because the current data prove an off-diagonal FER advantage.
5. Compute E_s, select complete cyclic diagonals, generate their coefficients, compute the full modeled mean and exact rowwise omitted variance. Default cap M=24; the only proposed-family development choices are M in {16,24,32} and terminal BP sweeps in {8,20}. No hidden per-frame oracle routing is permitted.
6. Supply y_eff=y-Hbar(p+mu)+Gmu and sigma^2+weak_row_variance to a fresh proper-Gaussian finite-alphabet BP batch, damping 0.5, temperature 1, retaining the old LDPC check prior. Weak mean/variance are frozen within this batch. Full observation-factor messages are restarted.
7. Pass the target-prior-excluded detector LLRs to one LDPC decode, at most 50 iterations. Save actual input, APP and check-extrinsic output. Do not count a zero syndrome as known correct decoding.

Only one physical-refit/terminal batch is in the primary method. Native competitors may perform multiple coded rounds within their declared budget; the proposal is not protected by restricting their schedule.

The current implementation's inherited I1 stages estimate effective variance. The new full-physical terminal uses known thermal variance plus its declared weak-interference variance. A same-channel new-interface control is included so a temperature/noise-interface change is not misattributed to physical refinement.

## 6. Comparator implementations and their limits

These are explicit coded adaptations, not asserted reproductions of the original authors' curves or full MIMO/ISAC functionality. All run on the same full physical observations and code. No true geometry or gain is supplied.

### 6.1 Grid-evolution SBL/GAMP

`offgrid.py` implements a Gaussian-SBL reference and an approximate complex Gaussian-prior GAMP backend on a full 515-column integer-delay/integer-Doppler dictionary, with exact fractional dictionary refresh after grid motion. Native startup uses observed pilot OMP, not an I1 warm state. Shared-I1 variants separately isolate the estimator change. All costs are charged.

At fixed mean waveform x=p+mu, the SBL equations are Sigma=(A^H A/nu_w+Delta^-1)^-1 and m=Sigma A^H y/nu_w. Delta denotes prior variance. The GAMP scalar Gaussian denoiser must use delta*r/(delta+tau), with posterior variance delta*tau/(delta+tau). The scalar convention is tested. A matched linear Gaussian test recovers the mean fixed point, but GAMP variances are not asserted exact for arbitrary deterministic AFDM matrices.

The hypervariance update corresponds to a weak exponential variance prior. Doppler motion is generated from the frozen posterior quadratic, including its covariance term, then checked against the exact nonlinear refreshed dictionary and backtracked through {1,1/2,1/4}. Native coded rounds preserve grid, gain, and variance-hyperparameter state. They replace the decoder prior and use decoder APP moments in the next mean-data waveform. A learned scalar effective CE nuisance variance is lower-bounded by thermal noise; it is not asserted to equal the true colored SP disturbance covariance. Thermal variance is retained in the common detector.

Integer delays are held fixed because that is the declared study model. Native estimates may retain different active coordinates, including more than one at a delay. No original fractional-delay search or sensing-association task is claimed reproduced.

Inserting a general full Gamma into the independent GAMP scalar denoiser is not algebraically free. It creates coupled precision unless explicitly represented by additional factors/augmented observations. The delivered GAMP comparator uses its declared mean-data/scalar-nuisance approximation; exact Gaussian SBL is a posterior-reference comparator. The paper must not call the two uncertainty models identical.

### 6.2 Parametric bilinear Gaussian BP

`bilinear.py` implements a PBiGaBP-family SP adaptation with observation-specific symbol/gain cavity states, proper exogenous gain prior and code-aware finite-alphabet marginals. Geometry is initialized/refined from observations outside each batch and charged. It is not the entire radar estimation procedure of [L3]. Native and shared-start modes prevent an artificial I1 initialization tax.

For a target d_k=a and one observation, set x_k=p_k+a, x_j=p_j+mu_j for j!=k, and z_i(a)=sum_j U_ij x_j. Under independent q(h_i),q(d_j), the exact conditional first two moments are

    M(a) = sum_i m_hi z_i(a),
    S(a) = sigma^2 + sum_{j!=k}|sum_i m_hi U_ij|^2 v_j
             + sum_i v_hi [|z_i(a)|^2 + sum_{j!=k}|U_ij|^2 v_j].

The Gaussianized candidate metric is -log S(a)-|y-M(a)|^2/S(a). A constant target variance is generally unjustified, because p_k+a and the other soft means affect gain uncertainty. The explicit code uses the candidate dependence. The gain update still Gaussianizes uncertainty in its own regressor, as specified by the algorithm family.

This is a necessary SP/coded moment treatment, not automatically a second novel contribution: it follows from conditional moments in a classical Gaussian-factor construction. Its extra cost, versus a constant-variance approximation, is measured rather than hidden.

### 6.3 Structured dual-domain EP

`structured_ep.py` implements a proper-complex dual-domain EP variant, not the original real-valued EP-T verbatim. It applies constellation/code factors only in the AF domain. A unitary transform does not turn QPSK symbols into independent time-domain QPSK symbols.

The time-domain Gaussian precision is Q=H_T^H H_T/sigma^2+diag(lambda). The actual cyclic band is solved by a Schur boundary partition and banded Cholesky; selected inverse diagonals use the Takahashi recurrence. These standard numerical operations are not claimed as new. Exact mean and inverse-diagonal outputs are verified against dense solves. When the bandwidth approaches N, the implementation declares its dense fallback.

Domain crossings project covariances to a proper diagonal approximation; resulting finite-alphabet marginals include the code prior, and the target prior is subtracted on output. The covariance projection is not exact posterior transport. With noncircular data, real/imaginary variance transport requires the appropriate real/imaginary squared transformation blocks; a simple jI rotation swaps the component variances. The primary comparator is explicitly proper-complex, so it does not silently advertise an exact noncircular implementation.

Complexity depends on delay spread as well as P. The implemented cyclic solve costs O(N b^2+b^3), with b the relevant time-domain half-bandwidth, not merely path count. This is the cost of this exact solver, not a lower bound on every structured EP implementation or ordering.

### 6.4 E-JSG/weak-edge control

The common sparse BP implementation can run on the actual I1 channel, with no full physical refinement. Its complete-shift selection, full mean, and weak moments are exposed separately. Magnitude/eSNR-like ranking and raw truncation controls are provided. The paper cannot obtain novelty by weakening this comparator to zeroing every omitted mean.

A further source audit found that I1's returned coefficient vector does not reconstruct its damped, pointwise-masked H_est. On a checked block, the discrepancy was about 5.74%. The corrected same-channel controls recover the integer coefficients from the actual H_est, with relative reconstruction discrepancy 4.85e-8. All retained same-channel comparison records use this corrected path. Using only the last undamped gains would be an invalid same-channel comparison.

## 7. Complexity and output contract

Let C be the actual number of variable-projection evaluations, P the physical path count, M the retained diagonal count, I the terminal BP sweeps, Q the full sparse-estimation dictionary size, and b the TD half-bandwidth.

- Physical mean action: O(N log N+NP), two transforms plus time-domain path operations.
- Fixed-q physical refit: O(C[PN log N+NP^2+P^3]), with fixed transforms/variance Fourier samples prepared once.
- Gamma: O(N log N+P^2), or O(P^2) after fixed-v preparation.
- All E_s: O(NP^2+N log N).
- Selected coefficients: O(NMP).
- Weak row variances: O(P^2 N log N).
- Sparse QPSK BP: O(I NM |alphabet|), with O(NM |alphabet|) messages.
- GAMP: O(NQ) per inner linear update, plus dictionary/grid work; full SBL additionally factors Q-dimensional precision. Store diagonal GAMP posterior variance as a vector, not a needless dense diagonal matrix.
- PBiGaBP-family reference: O(I PN^2 |alphabet|) work and O(PN^2+N^2|alphabet|) memory in the delivered dense reference.
- Dual-domain EP: cyclic-band Gaussian solver plus transforms and code factors; its measured complete cost is the comparator.

Include initialization, transforms, decoder calls, parameter grouping, code-prior mapping, variance acquisition, mask generation, numerical fallbacks and conversions. Static code/dictionary construction may be outside online timing only when all arms receive the same declared offline allowance. Every frame-dependent quantity is charged.

The observed benchmark shows cached dense H can be faster for the same moment outputs. A legitimate matrix-free claim compares either full fresh construction plus the same outputs, or a memory/update regime in which dense caching is not affordable. Never compare only row counts, or claim the moment-stage speed ratio is the complete receiver speed ratio.

## 8. Executed evidence, not confirmation

All current numerical results are in `results/`; the scripts define their seeds and scope. The core test was rerun after the final fixed-q cache optimization. Cached and uncached refinement outputs were checked separately; maximum discrepancy was below 7.0e-18 on the four cache fixtures.

`test_core.py`: 134 numerical comparisons, including independent CPP matrices, full means/adjoints, Gamma, energies, weak row covariance and pseudo-covariance, target-bit extrinsic accounting, scalar detector likelihoods, conditional SP moments, and explicit degeneracies. Maximum discrepancy 1.45e-9 arose in finite differencing, whose tolerance is 2e-7. Algebraic comparisons have much smaller errors. These are consistency checks, not independent radio trials.

`test_baselines.py`: 22 comparisons for cyclic solves/selected inverse diagonals, time/AF operators, Gaussian posterior conventions, scalar EP likelihoods and frozen-grid objectives. A retained counterexample shows a GAMP variance discrepancy about 0.2944 despite a correct Gaussian mean fixed point; GAMP is not certified exact for arbitrary AFDM matrices.

The SP conditional-moment fixture gives different conditional variances for four QPSK targets (approximately 5.5334, 5.3285, 4.7466, 4.5417). This kills the claim that a constant variance can always be reused when gain uncertainty and a superimposed waveform are present. It does not prove a receiver FER advantage from the more detailed metric.

The actual upstream preterminal loop agrees bitwise with the unchanged formal adapter using the same explicit gels initializer. Native GAMP, dual-domain EP and bilinear comparator rounds execute at N=1024 with finite output. These are implementation smokes, not successful reproductions of any published performance distribution. A separate recount verified all 104 saved mechanism/interface information-error totals without importing the proposed receiver modules.

### Small mechanism screen

Four exogenous blocks at 7 and 8 dB yield eight observations. They are reused across arms, and the I1 preterminal state is shared. This is not a matched-complete-deadline or population FER experiment.

- Old I1 terminal: 7 failed observations.
- Full-physical mean-only CE: 2.
- Scalar Gamma CE: 0; full Gamma CE: 0.
- Fresh decoder APP before mean-only CE: 3.
- Mean-only with omitted weak variance: 2.
- Mean-only with reset check prior: 2.
- Mean-only with magnitude mask: 2.
- Mean-only with raw truncation: 5.
- Full-physical mean-only plus structured EP: 0.
- Full Gamma with noncircular terminal: 0.

Additional corrected actual-I1-matrix controls failed on 8/8 (new sparse BP) and 7/8 (EP). Their matched-physical controls use the same new terminal interfaces; these records reinforce a model issue but are still tiny selected-regime evidence.

Decisions: mean-only correction is not assumed sufficient; the consistent soft objective is the primary. No separate off-diagonal Gamma benefit is established, because the scalar control matches it. No extra decoder refresh, noncircular module, or adaptive mask-gain claim is promoted from these tests. Structured EP is a surviving strong competitor that ties the favorable physical-refinement error pattern.

The earlier 16-observation study had equal mean-only and soft decisions. There is no contradiction: it was a different moment/terminal contract and different observations. Neither small screen supports a universal ordering.

### Same-output matrix benchmark

Seven interleaved timing repetitions per fixture; all arms compute matching energies, mask, selected coefficients, row variance and full mean. Median milliseconds:

| N | P | Matrix-free | Dense construction + outputs | Already-cached dense outputs |
|---:|---:|---:|---:|---:|
| 256 | 3 | 0.978 | 3.497 | 0.184 |
| 256 | 8 | 2.471 | 4.000 | 0.215 |
| 1024 | 3 | 2.382 | 53.329 | 1.927 |
| 1024 | 8 | 5.620 | 49.856 | 1.927 |

The cached dense comparator is faster on all four fixtures. The matrix-free path avoids dense construction and storage, not all possible dense-kernel arithmetic. The output discrepancies are below 2.5e-12. This benchmark does not establish complete-receiver superiority.

## 9. Remaining empirical questions and falsification

Remaining questions are: actual complete deadline-error/memory frontiers, frequency of the model failures, robustness to initial delay omission and collisions, worthwhile M/I settings, relative value of scalar/full Gamma, calibration of the Gaussian approximations, and transfer across registered code/pilot/channel regimes. They require independent local computation rather than more algebraic renaming.

Abandon the new receiver performance claim if the best coded off-grid/structured-inference comparator removes the complete-cost advantage; if useful initialization requires hidden true geometry; if a static cached full-model implementation makes the claimed memory/update regime irrelevant; or if the result is only a temperature, normalization, or message double-counting correction. A valid efficient implementation can still be useful software, but that is not automatically a Transactions paper.

Remove individual headline claims if their own controls explain them: no observed full-versus-scalar Gamma advantage means no off-diagonal-uncertainty performance headline; no mask advantage means mask selection is a justified implementation choice, not a separate empirical contribution. A null complete frontier ends this path; it does not authorize an additional list/scorer/learning patch.

The algorithm and comparison contracts are frozen. Local development selects only the finite resource settings and primary operating points, then creates an immutable source/configuration lock before confirmation. No confirmatory claim has been made in this report.
