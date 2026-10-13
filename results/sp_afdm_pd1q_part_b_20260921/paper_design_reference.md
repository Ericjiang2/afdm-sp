# Paper Design v1
## Tensor-Free Joint Channel Estimation and Decoding for Superimposed-Pilot AFDM

**Decision:** commit to the independently validated native receiver, without changing the primary numerical method.  
**Design date:** 21 September 2026.  
**Primary identity:** `TF_J20_R2`, numerical source `2d130b4d`, qualified baseline `31d5ec0d`; direction-validation runner `beb5ab73`.  
**Status:** manuscript architecture and analytical backbone, not a claim of publication-level statistical confirmation.

## 0. Evidence and provenance contract

This design is grounded in three distinct evidence layers:

- **E1 — Independent direction validation:** supplied `RESULTS(6).md`, 96 fresh observations across 6/6.5/7 dB, 252 measured calls. Source and allocation remained frozen. Its results and limitations are binding.
- **E2 — Mechanism audit:** supplied `TABLES(1).md`. The audit reuses E1 states: full vector diagnostics for one existing frame per SNR, paired scalar diagnostics for the first eight per SNR. It contains no new radio observations or receiver calls. Iterations are not statistical replicates.
- **E3 — Existing design and implementation:** supplied native-joint research verdict, handoff, and archived implementation package; plus the 26-page theory chapter. The archived implementation was inspected here. It is not claimed to be a byte-identical checkout of the remote validation commit. E1 and E2, not a reconstructed local run, remain the authority for the latest performance.

**New in this design pass:** conditional mechanism propositions, an explicit startup-memory analysis, a gain-mean identity, a counterexample separating scalar algorithm variance from actual posterior uncertainty, and deterministic algebra/state checks. No new FER or Monte Carlo evidence was generated. The checks reconstruct 60 states in the archived scalar implementation, not the remote E1 state files.

The old full-physical/sparse-innovation campaign remains stopped. Earlier G0 waterfalls, later full-G1 experiments, exploratory native screens, and E1 must not be pooled. The historical theory chapter uses negative chirps/Dopplers; this design uses the positive convention of the executed native code. Translate `(c1,c2,nu)` together when borrowing a formula.

## 1. Final scientific thesis

> A compact full fractional-path channel permits native joint gain/data adaptation at path-operator cost rather than dense tensor or observation-specific cavity cost. For coded SP-AFDM, an exact computational specialization of a declared scalar-variance bilinear inference map yields a useful measured latency–reliability operating point. The analytical and experimental mechanism distinguishes useful gain-mean adaptation from the unproven incremental value of propagating scalar gain variance.

The paper is an **algorithmic specialization and communication-receiver paper**, not a new general AMP family, a new turbo principle, or a posterior-optimality theorem.

The thesis has two inseparable parts. First, the chosen approximate inference map can be evaluated without materializing a `P x N x N` tensor, while retaining the full fractional forward model. Second, this inexpensive native implementation updates gains and data together and, in the validated setting, has a better observed cost/reliability operating point than the practical structured-EP control. Neither part alone is the whole contribution.

The 2-versus-4-FFT difference is not the explanation for the observed complete-receiver speed advantage. The competent four-FFT implementation evaluates the same map, and the earlier same-map benchmark showed small differences. The paper must compare exact implementations separately from different inference approximations.

### 1.1 Contribution statement suitable for the introduction

Use three connected statements, not a catalogue of modules:

1. **An exact full-path realization of scalar bilinear inference.** Derive observation-unitary equivariance and the AFDM/CPP contractions needed for predictions, gain/data adjoints, and scalar norm calculations. This eliminates explicit path tensors without deleting fractional-Doppler leakage or moving finite-alphabet constraints to the time samples.
2. **A native coded receiver with explicit information and cost contracts.** Couple this realization to observed-only physical acquisition/refinement and legal LDPC message replacement. The main receiver operates without an I1 warm-up loop, codeword-list search, or sparse AF-domain graph construction. Its value is measured against native coded EP and PBiGaBP-family adaptations, with all online work counted.
3. **A qualified mechanism and operating-envelope analysis.** Establish the exact scalar variance/mean-update identities, conditional small-`P/N` feedback bounds, and the non-negligible startup exception. Use POINT and fixed-gain controls to distinguish inference roles without claiming that uncertainty propagation independently creates the FER benefit.

Statement 3 supports and limits the method; it is not marketed as a new asymptotic Bayesian optimality result. The final empirical operating-envelope claim is subject to the submission study below.

## 2. What the current evidence establishes

### 2.1 Primary validation

| SNR | TF/EP2 failures, n=32 | Rescues/harms | Median TF/EP2, s | p90 TF/EP2, s |
|---:|---:|---:|---:|---:|
| 6 | 6/9 | 3/0 | 0.2955/0.5013 | 0.3128/0.7081 |
| 6.5 | 1/6 | 5/0 | 0.2969/0.5018 | 0.3176/0.6711 |
| 7 | 1/1 | 0/0 | 0.2946/0.5031 | 0.3068/0.6869 |

This is independently reproduced engineering evidence: median latency ratios 0.586–0.592, p90 ratios 0.442–0.473, and no observed cellwise FER penalty. It is not statistical equivalence. The retained conservative cellwise intervals for `FER_EP2 - FER_TF` all include zero.

The eight rescues and zero harms may be reported as a descriptive aggregate. Do not retroactively pool selected SNRs to create a new primary significance claim. All three prospective cells remain visible.

### 2.2 Stronger and simplifying controls

EP4 matches TF frame outcomes on all 24 predefined control observations but costs about 2.4–3.3 times as much on the matched subsets. It is therefore a necessary stronger-accuracy comparator, not an eliminated method.

POINT also matches TF frame outcomes on those 24 observations. Its information errors are 178/122/0 versus TF 155/97/0 across 6/6.5/7 dB; runtime is similar. Thus neither message equivalence nor equal BER is established. Removing a handful of scalar variance operations has not demonstrated a runtime advantage.

PBiGaBP is approximately 47–49 times slower in the twelve predefined control observations. Its small-subset error counts are not a universal ranking of the published family. Keep it as a correctly labeled, expensive native joint-inference reference.

### 2.3 Mechanism audit

For the three vector-audited observations, late posterior `N v_h` medians are 0.567–0.710, late output-variance corrections are about 1.18–1.20%, and late actual reaction diagnostics about 0.76–0.82%. Those are descriptive within-run medians. They do not estimate a large-N exponent.

At the first inner iteration of **each** coded round, propagated `v_h = 1/P`. E2 reports output corrections of 227–388% and reaction diagnostics of 112–168%. Therefore variance feedback is not uniformly negligible across the receiver trajectory.

POINT keeps gain-mean adaptation and the gain pseudo-variance/shrinkage calculation while setting propagated gain variance to zero. Its nonzero mean movement is entirely consistent with the equations. This is not a full-gain-covariance comparison and not a new Gamma ablation.

## 3. Problem, variables, and assumptions

Let `d(c)` be the scaled QPSK vector associated with a valid LDPC codeword. With deterministic scaled pilot `p`,

\[
x=p+d(c),\qquad y=H(\theta,h)x+w,\qquad
w\sim\mathcal{CN}(0,\sigma^2I_N).
\]

Use `E|w_n|^2 = sigma^2`; each real component has variance `sigma^2/2`. At the primary setting, `rho=0.5` and QPSK points are `±0.5 ± 0.5j`. There is no per-frame renormalization of the pilot/data cross term or a truncated channel.

With the negative-exponent unitary DFT `F`, define

\[
A=\Lambda_{c_2}^{+}F\Lambda_{c_1}^{+},\qquad
[\Lambda_c^{+}]_{nn}=e^{j2\pi cn^2},
\]

\[
U_i=A M_iA^H,\qquad M_i=C_{l_i}\Delta_{\nu_i}^{+}\Pi_{l_i},\qquad
H(h)=\sum_{i=1}^{P}h_iU_i.
\]

`P` is the working fitted path dimension; it need not equal an unknown physical truth count. The primary experiments use eight paths and a receiver cap of eight observed delay groups. Each path is unitary. The sum need not be unitary or well conditioned.

The CPP multiplier is

\[
\chi_l(n)=\begin{cases}
e^{j2\pi c_1[N^2+2N(n-l)]},&n<l,\\
1,&n\ge l.
\end{cases}
\]

The primary model has integer sampled delays, fractional Dopplers, adequate CPP, fixed parameters within a block, ideal synchronization, and known positive thermal variance. One resolved physical path per acquired delay group is the estimator's operating scope. Algebra supporting repeated delays does not establish that the chosen estimator resolves such paths.

The code operates with a factorized symbol approximation and scalar variances, not the complete codeword posterior. The gain prior `CN(0,I/P)` is a working prior. Estimated gains are initial states, not independent same-observation prior means. The physical generator and working Gaussian gain law must be documented separately if their normalizations differ.

## 4. Exact minimal receiver and equations

### 4.1 Freeze the validated primary

Retain `TF_J20_R2`: two coded rounds, twenty inner iterations per round, damping 0.3, soft physical refit, the existing LDPC code and fifty-iteration decoder cap. Do not replace it by POINT because the control has matched frame decisions. No cheaper receiver has been established by that deletion, and startup trajectories differ.

For each coded round:

1. Obtain/refine the working geometry using the current APP-like moments and observed pilot initialization.
2. Reset channel-factor residual histories. Keep the current code-check prior as the approximate turbo prior. Initialize gains from the refit and propagated gain variance at `1/P`.
3. Run the tensor-free scalar joint map for twenty iterations.
4. Send target-prior-excluded LLRs to LDPC. Form new check extrinsic by removing that invocation's actual input, and replace the prior. APP-derived moments supply the next physical refinement.

There are two completed decision checkpoints, not a hidden last-stage decoder. The latest valid completed checkpoint is the fallback if a later numerical stage fails. Failed work remains charged.

### 4.2 Information interfaces

The unknown data remain in the AF domain even when observations are rotated. For symbol `a`,

\[
q_k(a)\propto \pi_k(a)\exp[-|r_{x,k}-p_k-a|^2/v_r].
\]

The prior `pi_k` is built from the incoming code-check LLRs. APP bit LLRs are obtained by symbol marginalization; subtract the target bit's own prior. Under coupled I/Q likelihoods, the other bit's prior is not deleted indiscriminately. Use the upstream all-I-then-all-Q bit order.

The decoder uses its actual clipped input and produces APP and check-extrinsic outputs; clipping to `[-20,20]` is retained. A new decoder invocation replaces old feedback. This prevents a specific explicit duplication, not all dependence in a loopy graph.

CE consumes posterior-like moments including the observation contribution. Feeding only decoder extrinsic into an expected complete-data CE loss would define a different approximation. Do not confuse correct detector extrinsic routing with a demand that CE must use extrinsic-only means.

### 4.3 Damped scalar map: the code, not an undamped substitute

Let `x_t=p+mu_t`, symbol marginal variances `v_k,t`, and `v_x,t=mean_k(v_k,t)`. Let `u_t` denote the propagated **pre-update** gain variance. Initially `u_0=1/P` for TF and zero for POINT. Write `beta=0.3`, `tau=1/P`.

Set

\[
B(x)=[U_1x,\ldots,U_Px],\qquad
c(h)=\|H(h)\|_F^2/N.
\]

In the time-observation equations, `Y=A^H y`, `B_T(x)=A^H B(x)` and `tilde_H(h)=A^H H(h)=sum_i h_i M_i A^H`. Only the observation coordinate is rotated; `x` and its prior remain in the AF domain.

Raw variances are

\[
\bar b_t=v_{x,t}c(h_t)+Pu_t\|x_t\|^2/N,\qquad
b_t=\bar b_t+Pu_tv_{x,t}.
\]

At `t=0`, use these directly; afterwards damp each raw variance with its previous stored value. Denote the resulting scalars by `bar_vp,t` and `vp,t`. In the time observation domain,

\[
\hat p_t=B_T(x_t)h_t-\bar v_{p,t}s_{t-1},
\]

\[
s_t=\beta\frac{Y-\hat p_t}{\sigma^2+v_{p,t}}+(1-\beta)s_{t-1},\qquad
\alpha_t=\frac{\beta}{\sigma^2+v_{p,t}}+(1-\beta)\alpha_{t-1}.
\]

Start `s_{-1}=0`, `alpha_{-1}=0`. The barred means are updated by

\[
\bar x_t=\beta x_t+(1-\beta)\bar x_{t-1},\quad
\bar h_t=\beta h_t+(1-\beta)\bar h_{t-1}.
\]

Their initial old states are `x_0,h_0`. Cache `B_T(bar_x_t)` by the same linear recurrence rather than applying an additional transform.

With positive numerical floors inactive,

\[
v_{r,t}=[\alpha_t c(\bar h_t)]^{-1},\qquad
v_{q,t}=[\alpha_t\|\bar x_t\|^2]^{-1},
\]

\[
r_{x,t}=x_t+v_{r,t}\left[\widetilde H(\bar h_t)^Hs_t-\alpha_t P u_t\bar x_t\right],
\]

\[
r_{h,t}=h_t+v_{q,t}\left[B_T(\bar x_t)^Hs_t-\alpha_tNv_{x,t}\bar h_t\right].
\]

The finite-alphabet denoiser gives the new symbol moments. The Gaussian gain denoiser gives

\[
h_{t+1}=\frac{\tau}{\tau+v_{q,t}}r_{h,t},\qquad
v^{post}_{h,t}=\frac{\tau v_{q,t}}{\tau+v_{q,t}}.
\]

For TF, `u_{t+1}=v_h,t^post`. POINT uses the **same** gain-mean formula and computes `v_q`, but sets `u_{t+1}=0`. FIXED holds the within-batch gain mean fixed and is a separate control.

The actual implementation guards denominators at `1e-12`. Equalities that eliminate inverse pseudo-variance assume those guards are inactive. The manuscript algorithm must state guards and numerical-failure handling; an active guard is not silently interpreted as the same statistical formula.

### 4.4 Physical refinement: necessary infrastructure, not a second invention

Retain the observed-only pilot initializer and bounded refit. At most eight delay groups, one path per group, two coordinate passes, each initial Doppler center ±0.75 clipped to [-3,3], scalar tolerance 0.002 and at most sixteen scalar evaluations per update. Every accepted update decreases the frozen local objective.

For fixed symbol moments,

\[
Q(h,\nu)=\|y-\Phi_\mu(\nu)h\|^2+h^H\Gamma(\nu)h+\lambda\|h\|^2,
\quad \lambda=\sigma^2,
\]

\[
\Gamma_{ij}=\operatorname{tr}(U_i^HU_j\operatorname{diag}(v)).
\]

Its gain elimination and Fourier Gamma calculation are existing verified assets. Reuse the time-domain refit in all eligible competing receivers. The refit's `lambda=sigma^2` is an algorithmic initializer/refinement choice; it is not the `P sigma^2` penalty implied by the inner gain prior. The whole receiver is therefore not claimed to minimize one common Bayesian free energy through exact EM steps.

## 5. Analytical backbone

### Proposition 1. Exact observation-unitary equivariance of the declared scalar map

For isotropic complex Gaussian observation noise, fixed scalar damping, fixed priors and matching initial states, replace observations and all path operators by

\[
y'=Vy,\qquad U_i'=VU_i
\]

for any unitary `V`. Unknown-variable pseudo-observations, scalar variances and denoiser outputs remain identical. Observation residuals are rotated by `V`.

**Proof.** `B'=VB`, `H'=VH`; relevant Euclidean/Frobenius norms are invariant. The scalar Gaussian output update maps `s` to `Vs`. Adjoint terms satisfy `(VH)^HVs=H^Hs` and `(VB)^HVs=B^Hs`. Linear damping and barred-response caching commute with the rotation. Induction proves equality at every iteration. Unknown-variable priors and code processing are unchanged. QED.

This is an exact statement about a specified approximation, not about PBiGaBP's individual cavity updates or arbitrary vector-variance AMP. Colored/quantized/nonlinear observation models need their own argument. Since `(VH)^H(VH)=H^HH`, the operation cannot improve that map's conditioning or convergence. It is not a UAMP robustness claim.

### Proposition 2. Tensor-free AFDM contractions and complexity

Take `V=A^H`. Let `x_T=A^Hx`, `Y=A^Hy`,

\[
[B_T(x)]_{ni}=\chi_{l_i}(n)e^{j2\pi\nu_i n/N}x_T[(n-l_i)\bmod N].
\]

`B_T h` and `B_T^H s` take `O(NP)`. The data adjoint is

\[
\widetilde H(h)^Hs=A\sum_i h_i^*M_i^Hs.
\]

Define

\[
R_{ij}=\mathbf1_{\{l_i=l_j\}}D_N(\nu_j-\nu_i),\qquad
D_N(t)=N^{-1}\sum_{n=0}^{N-1}e^{j2\pi nt/N}.
\]

Then

\[
\|H(h)\|_F^2=Nh^HRh,\qquad
\|B(x)\|_F^2=P\|x\|^2,\qquad
\sum_i\|U_i\|_F^2=NP.
\]

**Proof.** Each `M_i` is a unit-modulus weighted permutation. For unequal delays, `M_i^HM_j` has no diagonal entries; for equal delays the prefix and delay factors cancel under the trace, leaving the finite Doppler sum. Unitary conjugation preserves the Frobenius product. Unitarity of each path gives the column norm. The adjoints follow by reversing the phase-weighted shifts. QED.

One IDAFT computes the current `x_T`, one DAFT returns the combined adjoint, and `B_T(bar_x)` is cached by linearity. Thus the inner map needs

\[
O(NP+N\log N+P^2)\ \text{work},\qquad O(NP+P^2)\ \text{state}.
\]

For distinct delays, `R=I`; for repeated delays it must be retained. No `P x N x N` tensor, leakage truncation, or independent time-domain QPSK assumption is introduced. This complexity is not a lower bound for all competitors or a complete-receiver memory bound.

### Proposition 3. Conditional scale of scalar gain-variance feedback

Let `a_t=||bar_x_t||^2/N`, and assume the pseudo-variance floor is inactive. The Gaussian gain denoiser satisfies exactly

\[
\boxed{Nv^{post}_{h,t}=\frac{1}{\alpha_ta_t+P/N}.}
\]

If `alpha_t a_t >= kappa > 0`, then

\[
Pv^{post}_{h,t}\le \frac{P/N}{\kappa}.
\]

Let `epsilon=P/N`. After an update satisfying this condition, bounded `||x||^2/N` and `v_x` give an `O(epsilon)` **raw absolute** gain-uncertainty contribution

\[
\delta_t^{out}=Pu_t\left(\|x_t\|^2/N+v_{x,t}\right).
\]

The explicit gain-variance reaction in the data pseudo-observation is

\[
\boxed{v_{r,t}\alpha_tPu_t\bar x_t
=\frac{Pu_t}{c(\bar h_t)}\bar x_t.}
\]

Its coefficient is `O(epsilon)` only when channel power is bounded away from zero. Relative comparisons to a vanishing data variance, vanishing update, or vanishing channel power do not inherit this bound. Thermal-inclusive denominators can avoid one of these degeneracies, not all of them.

**Proof.** Substitute `tau=1/P` and `v_q=1/(alpha N a)` into Gaussian posterior variance; the bounds and reaction identity follow. QED.

This is a conditional deterministic scaling statement about an **algorithmic scalar variance**. It is not a true posterior contraction theorem, proof of AMP state evolution, or empirically measured asymptotic exponent. E2 checks it at one `N=1024` only.

### Corollary 3a. Startup and damping memory prevent uniform neglect

At the beginning of every TF coded round, `u_0=1/P`, so `P u_0=1`. The raw output correction is `||x_0||^2/N+v_x,0`, with no `epsilon` prefactor. The reaction coefficient is `1/c(bar_h_0)`.

On a **fixed state trajectory**, isolate the gain-uncertainty contribution `e_t` to the damped output variance. If raw contributions satisfy `delta_t <= C epsilon` for `t>=1`, then

\[
e_t=(1-\beta)^t\delta_0+\beta\sum_{k=1}^t(1-\beta)^{t-k}\delta_k
\le (1-\beta)^t\delta_0+C\epsilon[1-(1-\beta)^t].
\]

This is a bound on the memory of one explicitly identified term, not a bound on complete TF-versus-POINT trajectories. A large startup perturbation can alter later mean states even after the direct variance contribution becomes small. A logarithmic damping-memory scale does not predict a universal receiver convergence time. The reset occurs twice in the validated receiver.

### Proposition 4. Gain-mean adaptation has no obligatory P/N prefactor

The implemented Gaussian gain update gives

\[
\boxed{
 h_{t+1}-h_t=
 \frac{B_T(\bar x_t)^Hs_t-\alpha_tNv_{x,t}\bar h_t-P h_t}
 {P+\alpha_t\|\bar x_t\|^2}.
}
\]

This equality applies to TF and POINT. The numerator contains an observation-accumulating score and a data-variance reaction; both can be order `N` at fixed path dimension. Thus a posterior scalar variance of order `1/N` does not force gain-mean movement to order `P/N`.

A deterministic one-path state with `alpha=1`, `||bar_x||^2=N`, `v_x=.1`, `h=bar_h=.2`, and `B^Hs=.5N` yields movement tending to `.48`, while scalar variance tends to zero as `1/N`. This is a counterexample to a universal small-mean-motion implication, not a claim that typical receiver movements have that limit.

The empirical early movement in E2 is consistent with this separation. Neither that single-N audit nor this existence example proves that mean movement dominates every variance term, or that it alone causes every frame rescue.

### Proposition 5 / limitation result. Scalar algorithm variance is not posterior identifiability

With a *known transmitted waveform* and fixed geometry, the genuine Gaussian conditional covariance is

\[
C_{h|x,y}=(PI+B(x)^HB(x)/\sigma^2)^{-1}.
\]

A legitimate sufficient condition for conditional concentration is

\[
\lambda_{\min}(B^HB/N)\ge\gamma>0
\quad\Longrightarrow\quad
\|C_{h|x,y}\|\le(P+N\gamma/\sigma^2)^{-1}.
\]

Energy alone does not provide this eigenvalue condition. Two distinct delay operators `I` and a cyclic shift are Frobenius-orthogonal, but they produce identical responses to a constant time waveform. For `P=2`, prior covariance `I/2`, and waveform energy `N`, the exact posterior has variance `1/2` in the unobserved gain-difference direction and `1/(2+2N/sigma^2)` in the gain-sum direction. The scalar algorithm can nevertheless report `1/(2+N/sigma^2)`.

At `N=64,sigma^2=.2`, those values are `.5`, `.00155763`, and `.00310559`. The example is a conditional known-waveform construction, not a claimed typical coded-SP frame. Its purpose is to prevent mistaking scalar shrinkage for a theorem about every physical gain or every joint code/channel mode. Even the conditional eigenvalue bound does not remove unknown-codeword multimodality.

### 5.1 What is already proved versus still empirical

| Item | Status | Permitted use |
|---|---|---|
| Full CPP/path operators and finite fractional expansion | Existing theory + verification | Model fidelity |
| Scalar-map observation equivariance and tensor-free contractions | Existing native derivation; restated proof | Exact implementation equivalence and inner complexity |
| Gaussian scalar variance identity | Algebraically exact; E2 replay check | Conditional mechanism |
| Conditional feedback scaling and damping-memory bound | Proved here | Qualify small-P/N interpretation |
| Mean-motion identity and lack of obligatory epsilon prefactor | Proved here; archived-state check | Separate mean and variance roles |
| True posterior concentration from scalar shrinkage | False without additional assumptions | Counterexample/limitation |
| TF and POINT equivalent decoding | Not established | Do not claim |
| TF globally stable/Bayes-optimal on structured AFDM | Not established | Do not claim |
| Complete practical advantage in the supplied regime | Independent direction evidence | Exploratory engineering result; larger study pending |

## 6. The actual mechanism and the role of each asset

The proposed interpretation is **efficient joint adaptation, with exact full-path computation**. Do not turn a plausible mechanism into an already completed causal attribution.

- **Tensor-free realization:** eliminates large representations and their repeated contractions for the selected scalar map. It cannot by itself change the exact scalar-map decisions.
- **Within-batch gain-mean updates:** a low-dimensional adaptation driven by all samples. Historical controls and E2 motivate their importance. A matched POINT-versus-FIXED intervention is the clean remaining causal test because both suppress propagated gain variance.
- **Gain-variance propagation:** keep it in the frozen primary. It has an order-one startup role and small explicit late corrections in the audited runs. No independent FER benefit or useful runtime saving from deletion is established.
- **Physical-path refinement:** supplies and periodically updates a compact full model; it is shared infrastructure. Do not give it sole credit for the TF-versus-EP gap when both receive comparable refits.
- **LDPC feedback:** constrains data and assists subsequent CE. Its novelty is not claimed; its exact interface is part of reproducibility.
- **Structured EP:** practical comparator and stronger EP4 accuracy control. It also uses time-domain structure and respects AF-domain symbol constraints. The paper must not describe it as dense naive EP or as assigning independent QPSK priors to time samples.
- **PBiGaBP:** richer cavity-based parametric joint inference. It is not the same algorithm accelerated exactly by TF. Comparison measures the cost of the chosen approximation on a stated regime.
- **I1:** retain in provenance and, at most, a secondary reference. It is not the main comparator and does not precede the proposed native receiver.
- **Gamma, whitening, V4, support exchange:** verified historical assets. Only Gamma remains as a small existing physical-refit statistic. The rest need no online place or contribution slot in this paper.

## 7. Closest prior art and exact boundary

### 7.1 The equation-level comparison

| Prior work | Direct overlap | Honest distinction |
|---|---|---|
| Parker & Schniter, P-BiG-AMP, Sec. III-H/Table V and Sec. IV | Scalar variances, pseudo-observations, reaction terms, damping, structured fast contractions | Exact AFDM/CPP implementation and a measured native coded operating point; not a new generic inference map |
| Sun et al., frequency-selective few-bit JCED, Sec. III | FFT-specialized scalar bilinear inference and turbo decoding | Full nonstationary fractional Doppler/CPP path action with shifted SP prior, rather than the stationary convolution instance; not first FFT-coded bilinear reception |
| Ranasinghe et al., AFDM PBiGaBP, Algorithm 1/Sec. III-B | Full parametric channel/data estimation | Different lower-state scalar approximation; not exact equivalence with PBiGaBP or an inherent lower bound against all PBiGaBP optimizations |
| Yi et al., dual-domain EP, Sec. III-C/D | Time-domain Gaussian inference, AF-domain constellation constraints and quasi-banded solves | Different contraction-based scalar joint map with no inner banded solve; costs depend on path count rather than the implemented solve's delay bandwidth |
| Kanazawa et al., coded SP-OTFS | Decoder soft replicas and coding schedules | No new turbo/SP-feedback principle claimed |
| D-GESBL/D-GAMP-GESBL | Data-aided off-grid acquisition; GAMP channel-estimation backend | Joint two-unknown inner map versus that channel-estimation backend; prior negative GAMP results do not eliminate every joint AMP family |
| Bilinear unitary AMP/BAd-VAMP | Robust bilinear approximations, unitary transforms or parameter adaptation | TF's observation rotation preserves the chosen scalar iterates and is not a new conditioning improvement; POINT is not a BAd-VAMP reproduction |

The complete receiver includes standard infrastructure, but this does not make a useful computational specialization scientifically empty. Its claimed value must be substantive in complete cost and operating scope, not solely a difference of notation or two FFT calls.

### 7.2 The adverse literature must be discussed

Ito et al.'s OTFS study reports finite-system and correlation limitations of PBiGAMP relative to PBiGaBP/BAd-VAMP. The inspected coded comparison invokes the decoder after demodulation, whereas this receiver exchanges code information across two joint rounds. Pilot arrangement, geometry treatment and numerical schedules also differ. Those differences delimit the comparisons; they do not prove that coding or SP fixes AMP's general finite-structure limitations.

Include this adverse evidence in the discussion, with the actual implementation assumptions. The current independent successes establish a useful tested regime, not a refutation of the paper's reported regimes.

### 7.3 Additional close precedents and access limits

Ma et al., *Parametric Bilinear Iterative Generalized Approximate Message Passing Reception of FTN Multi-Carrier Signaling* (IEEE TCOM 69(12), 8443–8458, 2021, DOI 10.1109/TCOMM.2021.3114873), is another direct structured-multicarrier precedent. Its primary author-repository abstract describes block-circulant/2D-FFT processing and a scaled-identity modification. The full manuscript was not retrievable in this pass; no equation-level absence or historical-firstness claim is made against inaccessible content. Li et al.'s EURECOM record 8323, *Joint channel estimation and signal detection for AFDM transmission with time-domain pilot arrangement*, establishes a BEM/bilinear sampling-EP AFDM precedent at the abstract level. The current work must not claim the first time-domain or bilinear AFDM receiver.

These precedents reinforce rather than broaden the selected novelty boundary: show the exact full-fractional path specialization and its complete coded operating benefit; do not use generic FFT, SP, or bilinear labels as evidence of novelty.

### 7.4 Novelty conclusion

Commit to a **scoped AFDM/SP computational and receiver contribution**. Do not advertise observation-unitary invariance, Gaussian scalar shrinkage, or turbo coding as independently new principles. The exact composition of full-path contractions, native coded execution, and qualified mechanism/complete-cost evidence is the case for the paper.

The search supports this narrow boundary, not an exhaustive historical firstness certificate. A single competent prior implementation with the same contractions and comparable coded operating point would require rewriting the novelty case. Baselines that implement the very same map should yield the same decisions; they are implementation references, not methods the proposal is supposed to beat in FER.

## 8. Complexity and implementation claims

For `R_c=2` coded rounds and `T=20` inner iterations,

\[
C_{\rm complete}=
 C_{\rm acquisition}+
 \sum_{r=1}^{R_c}\left[
 C_{\rm refit}^{(r)}+
 T\,O(NP+N\log N+P^2)+C_{\rm LDPC}^{(r)}
 \right]+C_{\rm interface}.
\]

Acquisition includes the `N x Q` pilot dictionary (`Q=515` in the primary setup), observed support selection, and actual least-squares work. Refits include every bounded scalar trial and gain solve, not merely the final accepted trial. Code/dictionary construction is either clearly offline configuration setup or charged online, consistently across arms.

For a refit with `J` objective evaluations, a direct bound is `O(N log N + J(NP^2+P^3))`, plus any fixed dictionary work. Do not identify `J` with the number of accepted updates. LDPC complexity is counted using real executed calls/sweeps and graph size.

The core state bound does not remove the pilot dictionary or Python/NumPy/Torch setup. E1's shared-process peak of about 1.08 GiB is not an isolated TF memory measurement. Report array-level online state and fresh-process per-arm peaks separately.

A dense `P x N x N` complex128 tensor at `N=1024,P=8` occupies 128 MiB before working messages. The `N x P` response array is 0.125 MiB. These are calculated array sizes, not measured complete-process RSS or a compulsory allocation in every competing implementation.

The structured-EP implementation uses a cyclic-band Gaussian solve whose cost depends on bandwidth `b`; a representative implemented scaling is `O(Nb^2+b^3)` plus transforms and sites. This is not a lower bound on all future EP solvers. PBiGaBP's displayed published implementation is quadratic in N at fixed P; do not claim that generic P-BiG-AMP inherently requires dense tensor work, since its original paper explicitly permits fast structures.

Report two-versus-four FFT only in the implementation table. The main comparison is native scalar joint computation against competent native alternative inference, not against a deliberately naive tensor implementation alone.

## 9. Claims that must not appear

Do not claim:

- a new general AMP/JCED/LDPC feedback principle, a first bilinear AFDM receiver, or a first FFT-based coded joint receiver;
- Bayesian optimality, state evolution, unconditional convergence, exact posterior variance, or an EM-ascent guarantee for the complete receiver;
- that observation rotation improves conditioning/convergence of an exactly invariant scalar map;
- that PBiGaBP is exactly accelerated or that all EP/PBiGaBP implementations must be slower;
- that gain variance is uniformly negligible, empirically O(1/N) across N, or independently responsible for the validated reliability;
- that POINT equals TF in messages, BER, posterior distribution, or all future frames;
- that small direct late corrections imply small full-trajectory differences after different startup states;
- that the fitted channel equals truth, physical refinement solves arbitrary off-grid acquisition, or the current estimator resolves arbitrary same-delay paths;
- that no time-domain QPSK approximation is a distinction from every EP paper; structured EP also returns to AF constraints;
- that the 41% measured median reduction comes from halving FFT count;
- that all complete costs or memory have the inner-loop scaling;
- an empirical error floor, low-FER tail, dB gain at FER 1e-3, real-time feasibility, or hardware universality from the current 32-frame cells;
- statistically equivalent reliability from intervals containing zero, or 1920 independent mechanism samples from iteration traces.

These restrictions do not weaken the actual positive statement: the frozen receiver repeatedly delivers an attractive measured communication/cost tradeoff in the declared setting.

## 10. Manuscript organization and logical flow

### I. Introduction and closest-art positioning

Introduce the computational mismatch: few physical paths but a dense fractional AF-domain representation, with channel/data uncertainty coupled by SP. Credit P-BiG-AMP and earlier FFT/turbo specializations immediately. State the paper's target as an inexpensive full-path native coded implementation. Explain why complete latency/reliability, not CE NMSE or FFT count alone, is the metric. End with the three connected contributions and explicit scope.

### II. Signal model and inference contract

Fix signs, CPP, power/noise units, physical versus working path counts, code mapping, and unknown versus supplied quantities. State factorized/scalar inference approximations. Distinguish the full forward model from exact posterior inference.

### III. Native scalar joint receiver

Give the inherited proper-complex scalar-map equations, initial states, damping, pseudo-variances, shifted constellation denoiser, and two-round APP/extrinsic exchange. Explain physical refinement as standard shared infrastructure. Include one executable pseudocode algorithm, not several proposed variants. POINT and FIXED are controls.

### IV. Tensor-free fractional-path realization

Prove Propositions 1 and 2. Show predictions, both adjoints, norms, and cached barred responses. Distinguish exact implementation equivalence from approximation relative to richer message passing. Give the core and complete cost expressions.

### V. Mechanism, startup, and limits

Present Propositions 3 and 4, the damping/startup corollary, and a short posterior-identifiability warning. Move the full counterexample and optional perturbation commentary to an appendix. The aim is to explain why joint mean updates and propagated gain variance have different roles, not to promise an asymptotic performance theorem.

### VI. Numerical evaluation

Organize by questions: exactness and scaling; complete FER/latency against strong native controls; causal ablations; code/pilot/geometry boundary cases. State development versus independent validation versus final submission study clearly. Show all registered cells, including unfavorable ones.

### VII. Discussion and conclusion

State where the implementation is useful and where scalar approximation, model acquisition or bandwidth-optimized EP may win. Reiterate the exact-versus-approximate distinction. Do not retell the entire project history.

### Appendices / supplement

Detailed CPP contraction derivation; full code-to-equation mapping and numerical guards; conditional mechanism proofs/counterexample; baseline adaptation tables; exact tests; seed/source and resource contracts; all ablation results. Preserve historical failed directions in the research archive, not as extra manuscript contributions.

## 11. Required figures and tables

### Figures: five main scientific figures are sufficient

1. **Variable-domain and information-flow schematic.** AF-domain finite-alphabet/code variables, time-domain residual computation, compact gains, two coded rounds, APP versus extrinsic arrows. Make the absence of a time-sample QPSK prior explicit.
2. **FER versus SNR with uncertainty.** TF, EP2, EP4; POINT and PBi as clearly labeled subsets or a companion table. Three validated points are not a basis for claiming an error floor. Add curve points only prospectively if a final figure requires them.
3. **Complete latency/reliability evidence.** ECDF or tail quantiles plus the fixed-deadline error tradeoff and stage costs. Keep unrestricted final FER separate from deadline FER. Do not use a retrospectively favorable single deadline.
4. **Core scaling and complete resource breakdown.** Operation counts plus measured core time versus N/path count, competent same-map implementation, and isolated online/process memory. Show shared acquisition/refit cost rather than hiding it.
5. **Mechanism trajectories across both coded rounds.** Show pre- versus post-update variance, explicit output/reaction effects and normalized gain movement on the actual stored conventions. Mark both startup resets. Accompany single-frame full-vector traces by across-frame scalar quantiles when available. Do not call the late window convergence.

An adverse-scope figure is optional if a compact table conveys the code/pilot/geometry cases. Do not add plots merely to increase contribution count.

### Tables

- Main settings and exact baseline adaptations: priors, geometry inputs, decoder calls, damping, executed budgets, output/cost contract.
- Inner and complete complexity/array sizes: compare computational operations, not generic family slogans.
- Mechanism ablations: TF/POINT/FIXED, feedback and geometry controls, with paired counts and costs.
- Scope/boundary outcomes: one alternative code, reduced pilot power, and unresolved/missed geometry, including failures.

A theory/claim/evidence table is useful in this blueprint and supplement; it need not consume a main-paper contribution slot.

## 12. Minimum empirical work before submission

The direction decision is complete. Do not repeat another small direction-validation campaign or open another hyperparameter search. The remaining work has three purposes.

### 12.1 Close attribution and resource accounting on existing inputs

Reuse saved E1 inputs and source-qualified states. Map actual stage times and allocations. Add the clean POINT-versus-FIXED-inner intervention, retaining identical propagated gain variance (zero), decoder schedule, and physical-refit policy. Compare with TF but do not call TF-versus-FIXED a one-factor variance-free test. A small feedback-removal control may retain decoder calls while discarding their returned feedback to match work.

Rerun same-map dense/matrix-free/four-FFT equivalence on qualification fixtures. Isolate per-arm memory in fresh processes. Inspect baseline mappings for avoidable differences and report proper-complex/coded adaptations as such. This is implementation and attribution qualification, not additional tuning.

If a defect is found, fix it before the next freeze and explain the consequence for existing evidence. Do not silently relabel modified source as `2d130b4d`.

### 12.2 Main submission evidence

Recommended fixed allocation: **1024 fresh independent frames per SNR at 6, 6.5 and 7 dB**, paired across TF, EP2 and EP4. Keep the tested primary/settings. This is a precision allocation, not a universal power guarantee; paired discordance, not BER bits, determines comparison uncertainty.

PBi on the first 32 predefined frames per cell and POINT on the first 128 per cell. The existing-input FIXED, feedback and geometry controls in Part A of the accompanying Codex ticket need not be repeated throughout the submission campaign. Do not choose PBi frames based on TF failures.

The intended claim is **lower complete latency at practically controlled reliability**, not mandatory FER superiority. Predefine absolute FER noninferiority tolerances 0.02 at 6 and 6.5 dB, and 0.01 at the 7-dB guard, and report one-sided paired uncertainty against both EP2 and EP4 across all three cells, with familywise control. This is a project-level practical tolerance, not an IEEE rule. Report the full intervals even if the threshold is inconclusive.

For latency, retain medians, p90/p95, paired ratios, stage timings, and a serially interleaved schedule. Timing intervals should account for run-order dependence; use batch/block resampling of paired observations when dependence is present. Distinguish a ratio of medians from a median of per-frame ratios. Primary practical target: upper 95% median-latency-ratio bound below 0.8 and p90 ratio no greater than one in the primary setting. The validation's approximately 0.59 ratios give a margin, but not an assurance of another machine's result.

Deadline curves use the last actually completed decoder checkpoint. Fix the displayed fractions of an EP2 reference time before opening the final data; retain all fractions. State numerical failures and missing decisions explicitly.

1024 frames will not support a claimed 1e-4 FER floor. Zero errors must be accompanied by an upper bound; do not extrapolate a high-SNR curve.

### 12.3 One bounded scope/complexity check, not a Cartesian sweep

Use deterministic fixtures to measure core scaling at `N=256,512,1024,2048` with `P=8`, and at `P=4,8,16` with `N=1024`; keep total path power normalized and document which quantities remain fixed. These are kernel scaling tests, not evidence for FER at every N.

For end-to-end transportability, use 64 fresh paired observations each for: a second valid rate-near-half code/interleaver construction, lower pilot power `rho=.25`, and a predeclared unresolved/missed-delay adverse case. Keep total-noise and power conventions explicit; changing rho also changes data energy. Use TF/EP2/EP4 without tuning. Qualify configuration-generalization code separately from the original fixed-N/rho path.

These small scope tests establish illustrations/boundaries, not population universality. The main performance claim remains at the tested primary N and code if broader confidence is absent. Failure in an explicitly excluded unresolved-path regime is a scope result; failure of the advertised primary cost/reliability claim is a submission problem.

## 13. Submission and stopping decisions

Proceed to drafting now: model, algorithm, exact reductions, conditional analysis, related work, and evidence contracts are writeable. Reserve final performance numbers and strong reliability language for the submission study.

Do not abandon the paper merely because POINT remains competitive: propagation is not the paper's novelty and removing it has no demonstrated material saving. Do not upgrade POINT to the primary without a separately justified receiver change.

Reassess the main claim if a competent matched EP or another close implementation removes the complete-cost operating advantage, if true geometry is required, if reported savings come from uncounted setup/failed work, or if a directly equivalent published AFDM implementation already supplies the same computations and performance contract. In that case, no new list/learning/sparsification patch is authorized by this design.

A lack of measurable POINT/FIXED difference would require weakening the causal claim about gain adaptation, not inventing one from mean-motion traces. Similarly, a numerical same-map equivalence result never establishes equivalence to an exact posterior or to richer PBiGaBP.

## 14. Draft abstract contract

An eventual abstract should contain: (i) the full-fractional coded-SP inference problem; (ii) the compact scalar-bilinear specialization; (iii) exact path contractions and their core complexity; (iv) the conditional startup-versus-late uncertainty analysis; and (v) the final complete-cost operating result with its tested scope.

A current research-stage version is:

> Fractional Doppler makes the affine-frequency representation of an AFDM channel dense even when its physical path description is compact. This paper develops a tensor-free specialization of scalar-variance parametric bilinear inference for joint channel estimation and decoding with superimposed pilots. The receiver retains the full estimated fractional-path model while keeping finite-alphabet and coding constraints in the affine-frequency domain. Observation-unitary equivariance and exact path contractions eliminate the explicit path tensor and yield per-iteration work of order \(NP+N\log N+P^2\). A native two-round coded architecture uses observed-only geometry refinement and explicit APP/extrinsic interfaces. Conditional analysis separates gain-mean adaptation from propagated scalar gain-variance corrections, including a non-negligible startup transient; it does not assert Bayesian convergence or posterior concentration. Independent direction-validation experiments at \(N=1024\) show median complete latency approximately 59% of the practical structured-EP comparator, with no observed cellwise frame-error penalty. Stronger EP and variance-suppressed controls define the remaining scope of the performance and mechanism claims.

This is not the submission abstract: its final empirical sentence must be updated from the prospective study, not presented as completed statistical confirmation.

## References and source record

**Internal evidence:** E1 `RESULTS(6).md`; E2 `TABLES(1).md`; E3 `SP_AFDM_Native_Joint_Research_Verdict_20260921.md`, native continuation ZIP and handoff; E4 `theory_chapter(7).pdf`. Latest raw validation artifacts remain remote as indexed in E1. The new `analysis/proposition_checks.json` records deterministic checks and archived-source hashes.

**Primary public sources inspected:**

R1. J. T. Parker and P. Schniter, *Parametric Bilinear Generalized Approximate Message Passing*, arXiv:1508.07575v2. Especially Sec. III-H, Table V, damping, and structured parameterizations in Sec. IV.

R2. P. Sun, Z. Wang, R. W. Heath Jr., and P. Schniter, *Joint Channel-Estimation/Decoding with Frequency-Selective Channels and Few-Bit ADCs*, arXiv:1807.02494v2. FFT-specialized scalar bilinear inference and coded exchange are established here.

R3. K. R. R. Ranasinghe et al., *Joint Channel, Data, and Radar Parameter Estimation for AFDM Systems in Doubly-Dispersive Channels*, IEEE TWC 24(2), 1602–1619, 2025; DOI 10.1109/TWC.2024.3510935; arXiv:2405.16945v4.

R4. Q. Yi et al., *A Novel Low-Complexity Dual-Domain Expectation Propagation Detection Aided AFDM for Future Communications*, arXiv:2603.29218v1. Sec. III-C/D. Treat as a preprint unless final publication metadata are independently verified.

R5. K. Ito et al., *Joint Channel and Data Estimation via Parametric Bilinear Inference for OTFS Demodulation*, IEEE Open Journal of the Communications Society 5, 6090–6105, 2024; DOI 10.1109/OJCOMS.2024.3463202. Sec. IV contains important adverse finite-structure and coded evidence.

R6. Y. Kanazawa et al., *Superimposed Pilot-Based OTFS: Will it Work?*, arXiv:2501.15935v3. Coded feedback is prior art.

R7. Y. Luo et al., *Data-aided Channel Estimation and Sensing With Sparse Bayesian Learning for AFDM-ISAC System*, arXiv:2607.18881v1. Off-grid data-aided SBL/GAMP is prior art.

R8. Z. Yuan, Q. Guo, and M. Luo, *Approximate Message Passing with Unitary Transformation for Robust Bilinear Recovery*, arXiv:2005.14132v3. Its robustification claim is different from the exact observation equivariance used here.

R9. S. Sarkar, A. K. Fletcher, S. Rangan, and P. Schniter, *Bilinear Recovery using Adaptive Vector-AMP*, arXiv:1809.00024. POINT is not identified with this algorithm.

R10. Ma et al., *Parametric Bilinear Iterative Generalized Approximate Message Passing Reception of FTN Multi-Carrier Signaling*, IEEE TCOM 69(12), 8443–8458, 2021; DOI 10.1109/TCOMM.2021.3114873. Primary author-repository abstract inspected; full text not retrieved, so detailed equivalence is not asserted.

R11. Z. Li et al., *Joint channel estimation and signal detection for AFDM transmission with time-domain pilot arrangement*, EURECOM record 8323, 2025. Primary abstract inspected; detailed algorithm not reproduced in this pass.

No source is cited as establishing universal superiority or exclusive historical originality of this proposed specialization.
