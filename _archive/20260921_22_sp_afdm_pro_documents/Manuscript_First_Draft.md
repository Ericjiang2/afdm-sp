---
title: "Tensor-Free Joint Channel Estimation and Decoding for Superimposed-Pilot AFDM"
subtitle: "Complete first manuscript draft — final Part-A and prospective Part-B evidence edition"
author: []
date: ""
lang: en-US
---

# Abstract {.unnumbered}

Fractional Doppler produces a dense affine-frequency-domain channel even when the underlying propagation model contains only a few physical paths. In a coded affine frequency division multiplexing (AFDM) system with superimposed pilots, this representation issue is coupled to uncertainty in both the channel and the transmitted data. This paper develops a tensor-free, full-fractional-path specialization of scalar-variance parametric bilinear inference for joint channel estimation and decoding. An observation-only unitary transformation preserves the iterates of the declared scalar approximation while leaving the finite-alphabet and coding constraints in the affine-frequency domain. Exact path contractions evaluate predictions, data and gain adjoints, and scalar norm terms with per-iteration work of order $NP+N\log N+P^2$ and state of order $NP+P^2$, without forming a dense path tensor or truncating fractional-Doppler leakage. A native two-round receiver combines observed-only physical refinement, joint gain/data updates, and explicitly defined LDPC APP/extrinsic exchange. Conditional analysis distinguishes gain-mean adaptation from scalar gain-variance propagation, including an order-one startup transient and a counterexample to interpreting scalar shrinkage as physical posterior concentration. In a frozen prospective study with 1,024 independent observations at each of 6, 6.5, and 7 dB, the receiver incurs 206, 43, and 14 frame errors, compared with 487, 140, and 29 for a two-sweep structured-EP adaptation and 309, 74, and 20 for a stronger four-sweep adaptation. Six simultaneous one-sided reliability bounds satisfy the predeclared tolerances; at 6 and 6.5 dB the bounds also establish lower frame-error probability against both comparators. Median complete online latency is 42.1–42.6% lower than the two-sweep comparator and 60.0–60.6% lower than the four-sweep comparator. These results establish a useful latency–reliability operating point for the specified channel, code, and CPU implementation, without asserting universal superiority, exact posterior inference, or convergence of the complete receiver.

**Index terms:** affine frequency division multiplexing, superimposed pilots, joint channel estimation and decoding, parametric bilinear inference, approximate message passing, fractional Doppler, tensor-free implementation.

# Introduction

Superimposing known pilot symbols on data avoids reserving pilot-only positions within an AFDM block, but it removes the simple observational separation between channel acquisition and data recovery. The same unknown channel acts on both components. An inaccurate channel estimate consequently changes both the predicted pilot contribution and the channel seen by the data detector. A serial strategy that acquires the channel once and then treats that estimate as exact can discard useful information in the code constraints, while a detailed joint receiver can be prohibitively expensive if it represents every path-to-symbol-to-observation interaction explicitly.

AFDM uses chirp-modulated Fourier processing to expose delay–Doppler structure in doubly selective channels [1]. With integer Doppler and suitable chirp parameters, individual path operators have a phase-weighted permutation structure in the affine-frequency domain. With fractional Doppler, the corresponding effective matrix generally contains nonzero entries along many cyclic diagonals. This does not mean that the physical channel has acquired a quadratic number of independent parameters. An individual path remains a cyclic delay and a samplewise phase multiplication between two unitary transforms. The distinction between the dimension of the physical model and the size of one matrix representation is the computational starting point of this work.

The statistical starting point is equally important. The unknown data are discrete and coded; the gains are continuous; and the pilot changes the support of the transmitted-variable prior from a constellation centered at zero to a known shifted constellation. Exact joint inference would sum over a codebook whose size grows exponentially with the number of information bits, and would integrate or optimize the continuous channel variables. Practical receivers must approximate that task. Our objective is not to eliminate every inferential approximation. It is to implement a useful declared approximation without adding an unnecessary dense representation or deleting parts of the fitted physical channel.

Parametric bilinear generalized approximate message passing (P-BiG-AMP) provides an established family of approximate updates for observations depending bilinearly on two sets of unknowns [3]. Its scalar-variance form replaces large collections of local variance quantities with scalar summaries. Earlier work has already developed fast parameterizations and FFT-specialized coded receivers [3], [4]. Thus, neither approximate message passing, joint gain/data adaptation, nor FFT-based turbo reception is introduced here. The contribution is an AFDM/SP-specific computational realization, its complete coded implementation, and a measured operating advantage against strong native alternatives.

Two distinctions prevent misleading interpretations of this contribution. First, a mathematically exact change in how an approximate algorithm is evaluated does not turn that algorithm into an exact posterior solver. Our observation transformation preserves the scalar-map iterates; it cannot improve their conditioning or convergence by itself. Second, a lower-complexity joint approximation is not an exact acceleration of a richer cavity-based algorithm. The comparison with PBiGaBP measures a tradeoff between different approximate inference representations, not the computational compression of identical messages.

This distinction also guides the experimental objective. Channel normalized mean-square error (NMSE), the number of FFT calls, and a per-iteration operation count are useful diagnostics, but none alone determines the usefulness of a coded receiver. Acquisition, physical refinement, all inference batches, LDPC calls, and information-interface work consume resources. We therefore evaluate both unrestricted final frame-error probability and the decision available at a fixed complete online deadline. Separate qualification experiments isolate implementation equivalence, while controlled interventions examine which internal adaptation accounts for the receiver's behavior.

The paper makes three connected contributions. We first establish an exact observation-unitary equivariance result for the declared damped scalar bilinear map and derive the full AFDM/CPP path contractions needed to implement it without a dense path tensor. We then construct a native coded receiver that uses those operations directly after observed-only pilot acquisition, with two physical-refinement/joint-inference/LDPC rounds and no preliminary serial joint-receiver loop. Finally, we provide a conditional mechanism analysis and a frozen prospective latency–reliability evaluation. The analysis separates the role of gain-mean adaptation from the unproven incremental reliability benefit of scalar gain-variance propagation and explains why startup behavior cannot be inferred from late-iteration variance magnitudes.

The final prospective evidence materially strengthens the development-stage conclusion. The proposed receiver satisfies all six predeclared simultaneous reliability criteria against two structured-EP configurations and has lower complete median and tail latency. Four of the six reliability upper bounds are negative, supporting lower frame-error probability at the two lower SNRs under the frozen experiment. At 7 dB, the result is the narrower tolerance statement. The paper preserves that distinction rather than treating every observed error-count reduction as a superiority claim.

# Related work and positioning

## AFDM, superimposed training, and coded feedback

The AFDM construction and its chirp-dependent delay–Doppler representation originate in [1]. Superimposed-pilot AFDM channel estimation and iterative detection have already been studied, including pilot-placement design [2]. Message-passing joint estimation/detection with superimposed pilots is also established for OTFS [9], and coded SP-OTFS reception uses decoder soft replicas to refine interference cancellation [8]. These works establish the utility of iterative data information; the present paper does not claim a new turbo principle or the first use of channel coding to improve superimposed-pilot estimation.

The unknown-data disturbance is not universally Gaussian or white. Its covariance, conditional on a fixed channel and prior data covariance $V_0$, is $HV_0H^H+\sigma^2I$. A single unitary path can yield white covariance even with fractional Doppler, whereas static multipath can yield colored covariance. These facts motivate care in statistical approximation but do not, by themselves, select a receiver. Our algorithm uses the full fitted physical operators and a declared scalar approximation; it does not justify that approximation by asserting that fractional leakage necessarily Gaussianizes the coded data.

## Parametric bilinear inference and fast implementations

Parker and Schniter derive P-BiG-AMP, including scalar-variance simplifications, approximate reaction terms, damping, and structured parameterizations [3]. Sun et al. specialize scalar bilinear inference to frequency-selective channels with few-bit conversion and coded exchange [4]. Structured FTN multicarrier bilinear reception provides another close precedent [11]. These precedents rule out a novelty statement based merely on combining FFTs, coding, and bilinear inference.

The present realization addresses the full nonstationary phase-weighted delayed paths of AFDM with a known superimposed pilot. It evaluates both unknown-variable adjoints, all required scalar norm quantities, and cached damped responses from the path representation. The observation transformation is particularly useful because it changes only the observation coordinates. It does not transport independent QPSK assumptions into the time domain. The proof is restricted to the isotropic Gaussian-output scalar map. It is not an automatic extension to nonlinear quantized-output likelihoods or arbitrary vector-variance updates.

Unitary AMP and adaptive vector-AMP formulations pursue other bilinear approximations and robustness mechanisms [12], [13]. Our exact observation equivariance is not a robustness theorem of that kind. Since the selected scalar map has identical iterates before and after the rotation, improved convergence cannot be credited to the rotation. The variance-suppressed POINT control used later is also not a reproduction of BAd-VAMP.

## AFDM-specific joint and structured receivers

Parametric bilinear Gaussian belief propagation has been developed directly for AFDM [5]. Its richer observation-specific cavity representation is different from the scalar approximation considered here. The published AFDM realization and the coded adaptation used in our experiment therefore provide a valuable joint-inference reference, but there is no claim that our implementation preserves its messages exactly. A more efficient implementation of that family could change the quantitative comparison.

Dual-domain expectation propagation exploits the time-domain structure of AFDM while returning to affine-frequency-domain constellation constraints [6]. It is a particularly relevant practical comparator, not a deliberately dense or incorrectly factorized alternative. The implemented comparator uses a cyclic-band Gaussian solve, selected inverse information for marginal variances, and a proper-complex coded/SP interface. Two and four EP sweeps per coded round are compared. Both have two coded rounds; the labels EP2 and EP4 do not denote two and four outer decoding rounds.

Data-aided grid-evolution SBL and its GAMP-accelerated variant address off-grid AFDM acquisition [10]. Their GAMP component accelerates a channel-estimation calculation inside a data-aided loop. This differs from updating uncertain data and gains jointly within every batch. Earlier project tests of those acquisition implementations are retained in the technical record, but they are not represented as a prospective Part-B comparison against every method called AMP.

A separate AFDM record with time-domain pilots and bilinear sampling-EP processing further limits any broad claim of first time-domain or first bilinear AFDM estimation [14]. The accessible primary record is sufficient to establish that overlap; a detailed non-equivalence claim against an unavailable full manuscript is not made.

## Adverse evidence and the scope of the claim

Bilinear inference is sensitive to finite-dimensional structure, correlation, initialization, and its variance approximations. The OTFS comparison in [7] reports important limitations of PBiGAMP relative to other bilinear methods. Our results do not refute those operating regimes. The pilot arrangement, initialized physical model, coding schedule, and implemented map differ. The contribution must therefore be evaluated as a concrete AFDM/SP specialization with a stated operating envelope, not as a universal resolution of structured-AMP instability.

The closest-method comparison can be summarized as follows: the inference family is established; the physical path model is established; and coded feedback is established. The scientific contribution is the exact and complete realization of the chosen joint map on that model, together with qualified mechanism analysis and prospective complete-cost evidence. This is a receiver contribution built from established tools, not a historical-firstness claim.

# System model and problem formulation

## Coded AF-domain signal and power convention

An information vector $b\in\{0,1\}^{K}$ is encoded into a valid LDPC codeword $c\in\mathcal C\subseteq\{0,1\}^{2N}$. The primary experiment uses $N=1024$ and $(2N,K)=(2048,1024)$. The first $N$ label bits determine the in-phase signs and the remaining $N$ bits determine the quadrature signs. With $a=\sqrt{P_d/2}$,

$$
d_k(c)=a\left[(-1)^{c_k}+j(-1)^{c_{N+k}}\right],
\qquad P_d=1-\rho. \tag{1}
$$

The deterministic, known pilot $p$ includes its power scaling. The transmitted AF-domain vector and received AF-domain observation are

$$
x=p+d(c),\qquad
 y=H_\star x+w,\qquad
 w\sim\mathcal{CN}(0,\sigma^2I_N). \tag{2}
$$

In the primary configuration, $\rho=0.5$ and $d_k\in\{\pm0.5\pm0.5j\}$. Thus the data energy is $0.5$ per symbol, not one. The variance convention is $\mathbb E|w_k|^2=\sigma^2$, with variance $\sigma^2/2$ in each real component. The pilot–data cross term need not vanish in an individual frame, and no per-frame normalization is applied to force it to vanish. The SNR labels in the final experiment retain the frozen generator's definition; they are not reinterpreted as $E_b/N_0$ in this draft.

We distinguish the true channel $H_\star$ from the working fitted channel $H(h,\theta)$. The number $P$ denotes the working path dimension within an inference batch, not an assertion that the receiver knows the physical path count. The principal experiment has nominally eight physical paths and a receiver cap of eight observed delay groups.

## Positive-chirp DAFT and CPP operators

Let the unitary DFT be

$$
F_{mn}=N^{-1/2}e^{-j2\pi mn/N},
\qquad
\Lambda_c^+=\operatorname{diag}(e^{j2\pi cn^2}),
\qquad
A=\Lambda_{c_2}^+F\Lambda_{c_1}^+. \tag{3}
$$

All sample indices are zero-based. Define the cyclic shift, Doppler modulation, and CPP phase by

$$
[\Pi_lz]_n=z_{(n-l)\bmod N},\qquad
[\Delta_\nu^+]_{nn}=e^{j2\pi\nu n/N}, \tag{4}
$$

$$
\chi_l(n)=
\begin{cases}
e^{j2\pi c_1[N^2+2N(n-l)]},&n<l,\\
1,&n\ge l,
\end{cases}
\qquad C_l=\operatorname{diag}(\chi_l(n)). \tag{5}
$$

A complete sampled path and the working channel are

$$
M(l,\nu)=C_l\Delta_\nu^+\Pi_l,\qquad
U(l,\nu)=AM(l,\nu)A^H,\qquad
H(h,\theta)=\sum_{i=1}^{P}h_iU(l_i,\nu_i). \tag{6}
$$

The useful time-domain waveform is $A^Hx$. The model assumes integer sample delays, adequate CPP, parameters fixed within a block, ideal synchronization, and proper white sampled thermal noise. Fractional Doppler is retained exactly. Fractional delay, unknown pulse shaping, oscillator impairments, and inter-block evolution are outside the primary model.

Every factor of $U(l,\nu)$ is unitary. The sum $H$ is not generally unitary or well conditioned. The positive convention in (3)–(6) is used throughout. Earlier derivations with negative chirps and Doppler are translated by reversing $(c_1,c_2,\nu)$ together, not by changing only the Doppler sign.

## Dense AF matrices do not imply dense physical parameterization

Define the finite kernel

$$
D_N(t)=\frac1N\sum_{n=0}^{N-1}e^{j2\pi nt/N}. \tag{7}
$$

Expansion of (6), including the CPP on wrapped samples, gives

$$
[U(l,\nu)]_{mk}
=e^{j2\pi[-c_1l^2-kl/N+c_2(m^2-k^2)]}
D_N(k-m+\nu+2Nc_1l). \tag{8}
$$

For integer $2Nc_1$ and integer Doppler, the kernel selects one cyclic diagonal. For fractional Doppler it generally occupies many diagonals. Nevertheless,

$$
U(l,\nu)=\sum_{q=0}^{N-1}D_N(\nu-q)U(l,q),
\qquad
\sum_{q=0}^{N-1}|D_N(\nu-q)|^2=1. \tag{9}
$$

Equation (9) is an exact finite representation, not an approximation theorem. Retaining only a subset of the integer coefficients creates a model approximation. Our inner receiver does not make that approximation: it evaluates the fitted physical paths in (6) directly. Errors due to missed paths or inaccurate fitted parameters remain and are distinct from truncating the response of an included path.

## Target inference problem and declared approximation

With fixed working geometry $\theta$, a reference joint density is

$$
p(d,h\mid y,\theta)
\propto P_{\mathcal C}(d)
\exp\!\left[-\frac{\|y-H(h,\theta)(p+d)\|^2}{\sigma^2}\right]
\exp(-P\|h\|^2), \tag{10}
$$

where the gain prior is $\mathcal{CN}(0,I_P/P)$. This prior is a working receiver assumption. The physical generator's normalized gain law is not silently identified with it. A fitted gain is used as an initial state, not as an independent prior mean derived from the same observation.

The complete codeword distribution in (10) is not computed. The receiver uses a proper-complex scalar bilinear approximation and scalar finite-alphabet denoisers with code-check priors. Geometry is estimated from the same observation and held fixed only within an inner batch. Consequently, the receiver is neither exact inference under (10) nor an exact EM algorithm for one common global objective.

Let $\mathcal A$ be a complete receiver, $T_{\mathcal A}$ its measured online latency, and $\hat b_{\mathcal A}(D)$ its last completed decision at deadline $D$. The operational quantities are

$$
R_{\mathcal A}=\Pr\{\hat b_{\mathcal A}\ne b\},
\qquad
R_{\mathcal A}(D)=\Pr\{\hat b_{\mathcal A}(D)\ne b\}. \tag{11}
$$

A missing completed decision is handled by the frozen scoring contract, not by granting a late decoder result. We compare $R_{\mathcal A}$, $R_{\mathcal A}(D)$, and the complete latency distribution. No relation of the form “smaller channel NMSE implies smaller frame-error rate” is assumed.

# Proposed native coded receiver

## Overview and observed-only initialization

The frozen primary, denoted TF, performs two coded rounds of twenty scalar joint iterations, with damping $\beta=0.3$. Each round consists of observed-only physical refinement, an inner joint batch, and one LDPC invocation capped at fifty iterations. There are two completed decoder checkpoints. If a later stage fails numerically, the latest previously completed checkpoint is retained and the failed work is still charged.

A shared pilot-only initializer supplies observed integer delay–Doppler candidates and gains. In the archived implementation, it constructs an $N\times515$ pilot-response dictionary and uses the B0-p2 configuration with a support budget of forty. This initializer is also used by eligible native comparators. It does not execute the I1 outer loop. Pilot acquisition remains a real cost and storage term; the tensor-free inner loop does not remove that dictionary.

For each physical refit, observed integer coefficients are grouped by delay. At most eight groups are retained, with one physical path per group. The strongest observed Doppler component supplies each initial center. The search takes two bounded coordinate passes with radius $0.75$, global Doppler limits $[-3,3]$, scalar tolerance $0.002$, and at most sixteen scalar evaluations per coordinate update. These are frozen algorithm settings, not estimates obtained from the final validation data. The estimator's resolved-delay scope is narrower than the algebraic path identities, which also accommodate repeated delays.

## The physical-refinement objective

For fixed APP-like symbol moments $\mu$ and $V=\operatorname{diag}(v)$, define

$$
\Phi_\mu(\theta)=[U_1(p+\mu),\ldots,U_P(p+\mu)],
\qquad
\Gamma_{ij}(\theta)=\operatorname{tr}(U_i^HU_jV). \tag{12}
$$

The exact expected squared residual under that working distribution is

$$
\mathbb E_q\|y-H(h)(p+d)\|^2
=\|y-\Phi_\mu h\|^2+h^H\Gamma h. \tag{13}
$$

To prove (13), substitute $d=\mu+e$. The cross term vanishes because $\mathbb E_qe=0$, and the remaining uncertainty term is $\operatorname{tr}(HVH^H)=h^H\Gamma h\ge0$. No Gaussian or properness assumption on $q$ is required for this squared-norm identity. Using diagonal $V$ is, however, a chosen representation of the available symbol information.

The refit minimizes the local objective

$$
Q(h,\theta)=\|y-\Phi_\mu(\theta)h\|^2
+h^H\Gamma(\theta)h+\sigma^2\|h\|^2. \tag{14}
$$

For fixed geometry,

$$
\hat h(\theta)=
\left[\Phi_\mu^H\Phi_\mu+\Gamma+\sigma^2I\right]^{-1}
\Phi_\mu^Hy. \tag{15}
$$

All accepted coordinate moves decrease the same frozen objective. The time-domain residual evaluates (14) exactly by unitarity and shares transformed inputs across coordinate trials. The Fourier implementation of $\Gamma$ is provided in Appendix A.

This stage is standard variable projection and expected-loss refinement, used as shared infrastructure. Its regularizer is $\sigma^2\|h\|^2$, whereas the inner prior in (10) has precision $PI$. The complete pipeline is therefore not a sequence of exact minimizations of one Bayesian free energy. The distinction is intentional and explicit.

## Coded initialization and state reset

At the start of each inner batch, the geometry and fitted gains are fixed as initial values. The initial symbol means and variances are formed from the incoming code-check prior. The propagated scalar gain variance is set to $1/P$, the observation residual and precision histories are zeroed, and the barred means are initialized at the current means. Thus a new physical model does not inherit residual messages computed for a different channel factor.

Decoder APP moments from the previous round guide physical refinement, while decoder check extrinsic supplies the inner symbol prior. These are distinct consumers. APP-like moments include the observation information needed by (13); sending extrinsic-only moments to that objective would define a different approximation. Conversely, feeding full APPs back as independent detector priors would explicitly duplicate observation information.

## Exact specification of the damped scalar map

Let $x_t=p+\mu_t$, $v_{x,t}=N^{-1}\sum_kv_{k,t}$, and $u_t$ be the propagated gain variance **before** inner iteration $t$. Define

$$
B(x)=[U_1x,\ldots,U_Px],\qquad
B_T(x)=A^HB(x),\qquad
\widetilde H(h)=A^HH(h),
\qquad c(h)=\frac{\|H(h)\|_F^2}{N}. \tag{16}
$$

The observation-domain variable is $Y=A^Hy$; $x_t$ itself remains in the AF domain. The raw scalar variances are

$$
\bar b_t=v_{x,t}c(h_t)+Pu_t\frac{\|x_t\|^2}{N},
\qquad
b_t=\bar b_t+Pu_tv_{x,t}. \tag{17}
$$

At the first iteration, $\bar v_{p,0}=\bar b_0$ and $v_{p,0}=b_0$. Subsequently, each variance is damped separately:

$$
\bar v_{p,t}=\beta\bar b_t+(1-\beta)\bar v_{p,t-1},
\qquad
v_{p,t}=\beta b_t+(1-\beta)v_{p,t-1}. \tag{18}
$$

With $s_{-1}=0$ and $\alpha_{-1}=0$, the output step is

$$
\hat z_t=B_T(x_t)h_t-\bar v_{p,t}s_{t-1}, \tag{19}
$$

$$
s_t=\beta\frac{Y-\hat z_t}{\sigma^2+v_{p,t}}+(1-\beta)s_{t-1},
\qquad
\alpha_t=\frac{\beta}{\sigma^2+v_{p,t}}+(1-\beta)\alpha_{t-1}. \tag{20}
$$

The barred mean states obey

$$
\bar x_t=\beta x_t+(1-\beta)\bar x_{t-1},
\qquad
\bar h_t=\beta h_t+(1-\beta)\bar h_{t-1}, \tag{21}
$$

with initial old states $x_0,h_0$. Their response $B_T(\bar x_t)$ is cached using the same linear recurrence. The prediction in (19) uses unbarred $x_t,h_t$; the pseudo-observation adjoints below use barred states. Confusing these states would define a different receiver.

With $\epsilon_0=10^{-12}$, the numerical pseudo-variances are

$$
v_{r,t}=\frac1{\max\{\alpha_tc(\bar h_t),\epsilon_0\}},
\qquad
v_{q,t}=\frac1{\max\{\alpha_t\|\bar x_t\|^2,\epsilon_0\}}. \tag{22}
$$

The data and gain pseudo-observations are

$$
r_{x,t}=x_t+v_{r,t}\left[
\widetilde H(\bar h_t)^Hs_t-\alpha_tPu_t\bar x_t
\right], \tag{23}
$$

$$
r_{h,t}=h_t+v_{q,t}\left[
B_T(\bar x_t)^Hs_t-\alpha_tNv_{x,t}\bar h_t
\right]. \tag{24}
$$

These are the declared scalar P-BiG-AMP-type updates, including the inherited approximate reaction terms [3]. They are not derived by assuming that the deterministic AFDM tensor satisfies every large-system random-matrix assumption used in generic AMP analysis.

The finite-alphabet denoiser is

$$
q_{k,t}(a)=
\frac{\pi_k(a)\exp[-|r_{x,k,t}-p_k-a|^2/v_{r,t}]}
{\sum_{a'\in\mathcal Q}\pi_k(a')\exp[-|r_{x,k,t}-p_k-a'|^2/v_{r,t}]}, \tag{25}
$$

$$
\mu_{k,t+1}=\sum_{a\in\mathcal Q}aq_{k,t}(a),
\qquad
v_{k,t+1}=P_d-|\mu_{k,t+1}|^2,
\qquad x_{t+1}=p+\mu_{t+1}. \tag{26}
$$

Numerically, negative roundoff in the last variance is clipped at zero. For $\tau=1/P$, the Gaussian gain denoiser gives

$$
h_{t+1}=\frac{\tau}{\tau+v_{q,t}}r_{h,t},
\qquad
v_{h,t}^{\mathrm{post}}=\frac{\tau v_{q,t}}{\tau+v_{q,t}},
\qquad u_{t+1}=v_{h,t}^{\mathrm{post}}. \tag{27}
$$

There is no additional, unreported damping of these denoiser outputs. The barred-state and residual recurrences implement the fixed damping policy. When $\beta=1$, the equations reduce to the corresponding undamped scalar form; replacing the executed damped map by that simpler form in the algorithm description would be incorrect.

## LDPC APP and extrinsic replacement

Take $L>0$ to favor bit zero, which corresponds to the positive sign in (1). For a QPSK label $(b_I,b_Q)$, the code prior has log weight

$$
\log\pi_k(a)=\tfrac12(1-2b_I)L^{\rm code}_{I,k}
+\tfrac12(1-2b_Q)L^{\rm code}_{Q,k}-\log Z_k. \tag{28}
$$

The detector APP for a target bit is the difference between the log sums of the symbol weights associated with labels zero and one. Its extrinsic output subtracts that target bit's incoming code prior. The other bit's prior remains in the marginalization; it is not deleted when the symbol likelihood couples in-phase and quadrature labels.

The LDPC decoder receives the detector extrinsic clipped to $[-20,20]$. Its raw APP and its actual clipped input are recorded. The new raw check extrinsic is their difference, and its clipped value replaces the old detector prior. The next physical refit uses moments reconstructed from the clipped decoder APP. For independent I/Q bit probabilities, these moments are

$$
\mu_k=a\!\left[\tanh(L_{I,k}/2)+j\tanh(L_{Q,k}/2)\right], \tag{29}
$$

$$
v_k=a^2\!\left[2-\tanh^2(L_{I,k}/2)-\tanh^2(L_{Q,k}/2)\right]. \tag{30}
$$

The data power is already present in $a$. It must not be multiplied into (30) again. These interfaces prevent explicit accumulation of the same prior as new evidence, but do not make all messages statistically independent in the loopy joint receiver.

## Algorithm 1: native coded tensor-free reception

```text
Input: observed y, scaled pilot p, positive thermal variance sigma2;
       frozen DAFT/CPP and LDPC configuration.
Acquire integer support/gains using the observed pilot-only initializer.
Set code prior to zero; initialize CE data moments to mean zero, variance Pd.
For coded round r = 1, 2:
    Group observed support by delay and retain at most eight groups.
    Refine physical Dopplers/gains with the fixed-moment objective (14).
    Form full fractional path phases and shifted-read indices; rotate y once.
    Initialize symbol beliefs from the code prior and gains from the refit.
    Reset s, alpha, variance histories, barred states; set u = 1/P.
    For inner iteration t = 0,...,19:
        IDAFT the current x; form B_T(x) by phase-weighted shifted reads.
        Evaluate (17)-(21), including separately damped variance histories.
        Cache B_T(bar_x) by linearity.
        Form both adjoints and pseudo-observations (22)-(24).
        Update finite-alphabet moments by (25)-(26).
        Update gain means and propagated scalar variance by (27).
        Reject nonfinite states as numerical failures; retain completed checkpoints.
    Marginalize symbol weights to APP bit LLRs; subtract the target prior.
    Clip the actual LDPC input; run at most fifty LDPC iterations.
    Save the completed decoded decision and its ready timestamp.
    Replace the code prior by clipped new check extrinsic.
    Use decoder APP moments and current fitted paths for the next round.
Return: latest completed decoded information vector and fitted channel state.
```

POINT suppresses $u_t$ while retaining (24) and the gain-mean part of (27). FIXED-inner additionally holds the within-batch gain mean fixed. They are interventions, not alternative proposed receivers, and POINT is not relabeled as BAd-VAMP.

# Exact tensor-free realization

## Observation-unitary equivariance

**Proposition 1 (equivariance of the declared scalar map).** Assume isotropic proper Gaussian observation noise, fixed scalar damping, fixed symbol/gain priors, and corresponding initial states. For any unitary $V$, replace $y$ by $Vy$ and every path operator $U_i$ by $VU_i$. The data/gain pseudo-observations, scalar variance states, finite-alphabet probabilities, and decoded messages produced by (17)–(30) remain identical in exact arithmetic. The observation residual is multiplied by $V$.

**Proof.** In arbitrary observation coordinates, $B'(x)=VB(x)$ and $H'(h)=VH(h)$. Hence

$$
\|B'(x)\|_F=\|B(x)\|_F,\qquad
\|H'(h)\|_F=\|H(h)\|_F. \tag{31}
$$

At initialization the unknown-variable states are unchanged and the residual is zero. Suppose the induction hypothesis holds through the preceding iteration. The raw and damped scalar variances in (17)–(18) then agree. The predicted observation and reaction correction satisfy $\hat z'_t=V\hat z_t$. Because the observation likelihood has scalar covariance, (20) gives $s'_t=Vs_t$ and $\alpha'_t=\alpha_t$. The barred unknown means in (21) are unchanged. Their response cache satisfies $B'(\bar x_t)=VB(\bar x_t)$ because the recurrence is linear.

The unknown-variable adjoints satisfy

$$
(VH)^H(Vs)=H^Hs,\qquad
(VB)^H(Vs)=B^Hs. \tag{32}
$$

Thus the denominators, pseudo-observations, denoisers, and next unknown-variable states agree. The numerical floors also give identical values when applied to identical scalar denominators, although algebraic identities obtained by eliminating them require that they be inactive. The induction proves the statement for every iteration. Unchanged finite-alphabet probabilities produce unchanged decoder inputs and subsequent code priors. $\square$

Taking $V=A^H$ yields the time-observation realization used by the receiver. This proposition does not rotate the unknown data or their prior. It also does not extend automatically to a componentwise non-Gaussian output likelihood: a general unitary rotation would couple such output factors. Row-dependent variances, colored noise, nonlinear quantization, and other damping rules require separate analysis.

Most importantly, the transformation cannot explain an accuracy improvement within the same scalar map. Its iterates are identical and $(VH)^H(VH)=H^HH$. The benefit is an implementation opportunity, not an improvement in conditioning or a new state-evolution result.

## Full physical-path predictions and both adjoints

Let $x_T=A^Hx$. For path $i$, precompute the delayed-read index $(n-l_i)\bmod N$ and phase

$$
\varphi_i[n]=\chi_{l_i}(n)e^{j2\pi\nu_i n/N}.
$$

Then

$$
[B_T(x)]_{ni}
=\varphi_i[n]x_T[(n-l_i)\bmod N]. \tag{33}
$$

The predicted observation is $B_T(x)h$ and the gain score is $B_T(x)^Hs$. Both use $O(NP)$ multiply–accumulate work once $x_T$ is available. The data score is

$$
\widetilde H(h)^Hs
=A\sum_{i=1}^{P}h_i^*M_i^Hs. \tag{34}
$$

The adjoint $M_i^H$ reverses the delayed read and conjugates the phase. Explicitly,

$$
[M_i^Hz]_k
=\varphi_i[(k+l_i)\bmod N]^*z[(k+l_i)\bmod N]. \tag{35}
$$

Accumulating the time-domain adjoints before applying $A$ avoids a separate AF transform for each path. Equations (33)–(35) include the full fractional-Doppler response of every fitted path. No cyclic-diagonal window or path-tail renormalization is introduced.

The current-symbol response requires one IDAFT and the aggregate data score requires one DAFT. The response of the barred symbol mean does not require another transform:

$$
B_T(\bar x_t)
=\beta B_T(x_t)+(1-\beta)B_T(\bar x_{t-1}). \tag{36}
$$

This equality is exact because the path action is linear in $x$ for fixed geometry. The geometry must remain fixed while the cache is updated. The implementation resets or rebuilds the relevant state when the outer refit changes the path parameters.

## Exact path norms

**Proposition 2 (physical-path contractions).** Define

$$
R_{ij}=\mathbf1_{\{l_i=l_j\}}D_N(\nu_j-\nu_i). \tag{37}
$$

For arbitrary fitted gains and AF-domain vector $x$,

$$
\|H(h)\|_F^2=Nh^HRh,
\qquad
\|B(x)\|_F^2=P\|x\|^2,
\qquad
\sum_i\|U_i\|_F^2=NP. \tag{38}
$$

**Proof.** Unitary conjugation leaves the trace inner product invariant, so $\operatorname{tr}(U_i^HU_j)=\operatorname{tr}(M_i^HM_j)$. If the relative cyclic delay is nonzero, the product is a phase-weighted nonzero shift and its diagonal is zero. If the delays are equal, the CPP factors cancel and cyclic trace invariance removes the common shift, leaving

$$
\operatorname{tr}(M_i^HM_j)
=\sum_{n=0}^{N-1}e^{j2\pi(\nu_j-\nu_i)n/N}
=ND_N(\nu_j-\nu_i).
$$

Expanding $\operatorname{tr}(H^HH)$ proves the first identity. Since each $U_i$ is unitary, $\|U_ix\|^2=\|x\|^2$; summing over paths proves the second. The final identity follows from $\|U_i\|_F^2=N$. $\square$

In the distinct-delay case, $R=I_P$. For repeated delays the off-diagonal finite-Doppler terms must be retained. Replacing $h^HRh$ by $\|h\|^2$ without that condition changes the scalar inference map. The proposition concerns the mathematical path representation; it does not prove that the selected one-path-per-delay estimator can separate unresolved paths.

## What is exact and what is approximate

There are three different comparisons. A dense implementation of (17)–(27), a competent four-FFT path implementation, and the proposed two-FFT implementation evaluate the same map. Subject to numerical arithmetic, they should have the same decisions. They are implementation references, not FER competitors.

In contrast, structured EP and PBiGaBP use different approximate message representations. Their decisions need not agree with TF. Finally, none of these approximations is identified with the exact posterior in (10). The qualification results establish the first type of equivalence; the prospective experiment measures the second type of tradeoff. Neither supplies the third type of guarantee.

# Mechanism analysis and theoretical limitations

## The scalar posterior-variance identity

A small propagated scalar gain variance is not, by itself, evidence that channel adaptation is unimportant. To analyze the two roles, distinguish the pre-update propagated value $u_t$ from the posterior scalar $v_{h,t}^{\rm post}$ computed at the end of iteration $t$.

**Proposition 3 (conditional scale of the scalar variance).** Suppose the floor in the gain pseudo-variance is inactive and let

$$
a_t=\frac{\|\bar x_t\|^2}{N}.
$$

Then the gain denoiser satisfies

$$
\boxed{Nv_{h,t}^{\rm post}
=\frac1{\alpha_ta_t+P/N}.} \tag{39}
$$

If $\alpha_ta_t\ge\kappa>0$, then

$$
Pv_{h,t}^{\rm post}\le\frac{P/N}{\kappa}. \tag{40}
$$

**Proof.** With $\tau=1/P$, (27) can be written as

$$
v_{h,t}^{\rm post}
=\frac1{\tau^{-1}+v_{q,t}^{-1}}
=\frac1{P+\alpha_t\|\bar x_t\|^2}.
$$

Multiplication by $N$ gives (39), and the lower bound on $\alpha_ta_t$ gives (40). $\square$

The conclusion is conditional on the algorithmic precision and waveform energy. It is not empirical estimation of a large-$N$ exponent and is not a contraction theorem for the true joint posterior. The main mechanism traces are at one block length only.

After a qualifying update, bounded $\|x_t\|^2/N$ and $v_{x,t}$ imply that the raw gain-uncertainty contribution to the output variance,

$$
\delta_t^{\rm out}
=Pu_t\left(\frac{\|x_t\|^2}{N}+v_{x,t}\right), \tag{41}
$$

is $O(P/N)$. This is an absolute bound on an identified term. A relative correction can remain large if its comparison denominator is small. Likewise, the data-side reaction has the exact form

$$
\boxed{
 v_{r,t}\alpha_tPu_t\bar x_t
 =\frac{Pu_t}{c(\bar h_t)}\bar x_t,
} \tag{42}
$$

when the data pseudo-variance floor is inactive. Its coefficient is conditionally $O(P/N)$ only if the working channel power is bounded away from zero. The identity does not make the entire TF and POINT trajectories close.

## Startup is an order-one event

At the beginning of each coded round, TF initializes $u_0=1/P$. Therefore $Pu_0=1$, and the raw gain-uncertainty term is

$$
\delta_0^{\rm out}=\frac{\|x_0\|^2}{N}+v_{x,0}. \tag{43}
$$

There is no $P/N$ prefactor. The corresponding reaction coefficient is $1/c(\bar h_0)$ when the floor is inactive. An argument based only on late posterior variance consequently misses the initialization of both coded rounds.

**Corollary 3a (memory of one damped contribution).** On a fixed state trajectory, isolate the gain-uncertainty contribution $e_t$ to a separately damped output variance. If $\delta_k\le C\varepsilon$ for $k\ge1$, where $\varepsilon=P/N$, then

$$
\begin{split}
e_t&=(1-\beta)^t\delta_0
 +\beta\sum_{k=1}^{t}(1-\beta)^{t-k}\delta_k\\
&\le(1-\beta)^t\delta_0
 +C\varepsilon[1-(1-\beta)^t].
\end{split} \tag{44}
$$

The proof is the solution of the linear damping recurrence and the finite geometric sum. The fixed-trajectory qualification is essential. Suppressing variance changes the means, residuals, and subsequent precisions; (44) does not bound the resulting nonlinear trajectory difference. A small direct late correction can coexist with a persistent effect of a different startup state.

The saved audit supports exactly this interpretation. Late correction ratios are small in the measured operating point, but the final Part-A extension reports initial output corrections ranging from 196% to 467% at round resets. The reported percentages use the audit's retained normalizations and are descriptive state diagnostics, not independent samples or estimates of asymptotic exponents [E-A, Sec. “Saved-trace mechanism closure”].

## Gain-mean adaptation remains a separate operation

**Proposition 4 (gain-mean movement).** With the gain pseudo-variance floor inactive,

$$
\boxed{
 h_{t+1}-h_t=
 \frac{
 B_T(\bar x_t)^Hs_t-\alpha_tNv_{x,t}\bar h_t-Ph_t
 }{P+\alpha_t\|\bar x_t\|^2}.
} \tag{45}
$$

**Proof.** Write the score in brackets in (24) as $g_t$. Since $\tau=1/P$,

$$
h_{t+1}=\frac{h_t+v_{q,t}g_t}{1+Pv_{q,t}}.
$$

Subtracting $h_t$ gives $v_{q,t}(g_t-Ph_t)/(1+Pv_{q,t})$. Replacing $v_{q,t}^{-1}$ by $\alpha_t\|\bar x_t\|^2$ proves (45). $\square$

The numerator includes a score accumulated over observations and a data-variance reaction. Both may be order $N$ at fixed $P$. Thus the denominator's order does not force the mean movement to vanish with $P/N$. For example, the consistent scalar state values $P=1$, $\alpha=1$, $\|\bar x\|^2=N$, $v_x=0.1$, $h=\bar h=0.2$, and $B^Hs=0.5N$ produce a movement $(0.48N-0.2)/(N+1)$, tending to $0.48$, while the scalar variance tends to zero. This is a deterministic counterexample to a universal small-movement implication, not a prediction of typical receiver trajectories.

POINT retains (45), including its shrinkage and data-variance reaction, even though its explicitly propagated gain variance is zero. FIXED-inner removes the within-batch mean adaptation while retaining outer refits. The POINT–FIXED intervention therefore isolates a different operation from TF–POINT. The numerical section reports both rather than conflating them.

## Scalar shrinkage is not physical identifiability

**Proposition 5 (conditional identifiability requirement).** For a known waveform $x$, fixed geometry, and the Gaussian gain prior $\mathcal{CN}(0,I/P)$, the exact conditional covariance is

$$
C_{h\mid x,y}
=\left(PI+\frac{B(x)^HB(x)}{\sigma^2}\right)^{-1}. \tag{46}
$$

If $\lambda_{\min}(B^HB/N)\ge\gamma>0$, then

$$
\|C_{h\mid x,y}\|_2
\le\frac1{P+N\gamma/\sigma^2}. \tag{47}
$$

Completing the Gaussian square gives (46); eigenvalue monotonicity gives (47). Energy alone does not establish the assumed minimum eigenvalue.

In a valid zero-Doppler, unit-CPP-phase special case, two distinct delay operators, identity and a cyclic shift, are Frobenius-orthogonal but act identically on a constant time-domain waveform. The response matrix then has two identical columns. For $P=2$ and waveform energy $N$, the posterior gain-difference variance remains $1/2$, while the gain-sum variance is $1/(2+2N/\sigma^2)$. A scalar formula depending only on total waveform energy can nevertheless return $1/(2+N/\sigma^2)$.

At $N=64$ and $\sigma^2=0.2$, these three values are $0.5$, $0.00155763$, and $0.00310559$. This constructed known-waveform example is not asserted to be a typical codeword in the evaluated SP system. It demonstrates that scalar algorithmic shrinkage cannot establish identifiability of every physical gain. Unknown codewords introduce further ambiguity beyond the conditional example.

## What the analysis does and does not explain

The analysis establishes computational equivalence, exact identities of the declared algorithm, and conditional bounds on specific feedback terms. The Part-A intervention supplies empirical attribution for gain-mean adaptation on reused observations. The prospective Part-B study supplies independent communication and latency evidence. These are complementary forms of support, not interchangeable substitutes.

No state-evolution result for the deterministic finite AFDM operators is established. No proof is given that twenty iterations converge, that additional iterations improve decoding, or that the true physical channel becomes identifiable from a small scalar variance. The fixed damping and two-round schedule are frozen numerical choices evaluated as part of the complete method. Their success in the measured setting is empirical.

# Complexity and resource accounting

## Inner computation

Preparing path phases, delayed-read indices, and the $P\times P$ norm matrix costs $O(NP+P^2)$ for a fixed geometry. An inner iteration performs one IDAFT of the current $x$, phase-weighted shifted reads, predictions and gain scores, an aggregate time-domain adjoint, and one DAFT. The finite QPSK denoiser costs $O(N|\mathcal Q|)$, with $|\mathcal Q|=4$ fixed. Therefore,

$$
C_{\rm inner}=O(NP+N\log N+P^2),
\qquad
M_{\rm inner}=O(NP+P^2). \tag{48}
$$

The response of the barred mean is cached by (36). There is no dense $N\times N$ channel or $P\times N\times N$ path tensor in this inner realization. The calculation does not depend on a chosen fractional-leakage window. With fixed $P$, the dominant scaling is quasi-linear in $N$; if $P$ grows with $N$, that qualification must be retained.

At $N=1024,P=8$, an explicit complex128 path tensor would contain 8,388,608 complex entries and occupy 128 MiB. An $N\times P$ complex128 response array occupies 0.125 MiB. These are calculated sizes of two arrays, not measured process-memory ratios and not compulsory allocations in every alternative implementation.

## Complete receiver cost

The complete online cost is

$$
C_{\rm total}=C_{\rm acquire}
+\sum_{r=1}^{2}\left[
C_{\rm refit}^{(r)}+20C_{\rm inner}^{(r)}+C_{\rm LDPC}^{(r)}
\right]+C_{\rm interface}. \tag{49}
$$

Acquisition includes observed support selection, the pilot-response dictionary operations, and the actual coefficient solves. For a physical refit with $J$ objective evaluations, a straightforward bound is

$$
C_{\rm refit}=O(N\log N+J(NP^2+P^3)), \tag{50}
$$

with transformed observations and moments reused. $J$ counts every scalar-search trial, not only accepted coordinate moves. The decoder cost depends on the actual parity graph and executed sweeps; both decoder invocations are charged. Conversion, clipping, checkpoints, and failed later work are part of the online implementation contract.

Static code/configuration construction may be amortized when it is consistently outside the online interval for all arms. It is not permissible to exclude a proposed-method online operation merely because it was expensive. Conversely, native comparators are not forced to execute I1 before their own initialization.

## Comparison with structured alternatives

The implemented time-domain EP comparator uses cyclic-band Gaussian elimination and selected inverse quantities. A representative cost for that solver is $O(Nb^2+b^3)$, where $b$ denotes its delay-related bandwidth. This is a description of the implemented solver, not a lower bound on every possible EP implementation. Its AF-domain finite-alphabet constraints are retained correctly.

The PBiGaBP-family comparator retains richer observation-specific states and has much greater state/work in the current implementation. Our scalar map is not mathematically identical to it. Generic P-BiG-AMP itself permits fast structured parameterizations [3], so a deliberately dense implementation of the same scalar map is not the strongest algorithmic comparator.

A competent four-FFT realization of the same map is retained for qualification. Its modest kernel-time difference is not the source of a claimed factor-of-two complete-receiver improvement. Different inference approximations, native execution, and their required linear-algebra operations determine the complete comparison.

## Memory measurements and their interpretation

Fresh-process Part-A probes measured nearly identical total peaks for TF, EP2, and EP4, approximately 623,000 KiB, after a baseline of approximately 595,000 KiB. The PBi adaptation reached approximately 1,148,000 KiB. The measured process totals include imports, static context, warmup, execution, and instrumentation. Thus the evidence supports a larger process footprint for that PBi implementation on the audit frame, but does not show a complete-process memory advantage of TF over EP.

The visible online NumPy subtotals were approximately 8.45 MB for TF/EP and 403.63 MB for PBi. They are sampled, deduplicated lower bounds at selected function returns; they omit hidden native workspaces and unsampled temporaries. They must not be described as exact peak live allocation. The asymptotic inner-state claim and the measured total-process claim answer different questions [E-A, Sec. “Isolated resources”].

# Experimental methodology

## Frozen numerical identity and evidence separation

The primary numerical identity is `TF_J20_R2`, source `2d130b4d`, with qualified baseline `31d5ec0d`. The method, priors, damping, iteration budgets, and primary selection were not changed during the final prospective experiment. The final evidence consists of two deliberately different parts. Part A qualifies numerical equivalence, checks saved decisions and interfaces, and performs mechanism interventions on previously acquired observations. Part B evaluates fresh paired observations under a frozen statistical contract. Part-A reused frames are not added to the Part-B sample count.

Part A completed 99 calls with zero new radio observations. It included missing mechanism controls, three primary replays, and isolated-memory probes. The upstream numerical receiver was unchanged by the reported qualification repairs: an initial residual comparison omitted the required coordinate alignment, and a wrapper initially interpreted packed truth incorrectly. Failed harness receipts were retained. Subsequent independent recounts and parity checks passed. These incidents do not create additional communication samples, nor are they hidden as successful first attempts [E-A].

Part B contains 3,072 fresh independent observations, 1,024 in each of three SNR cells: 6, 6.5, and 7 dB. The observations are paired across TF, EP2, and EP4. The three primary methods account for 9,216 calls. POINT is evaluated on the first 128 predefined observations per cell and PBiGaBP on the first 32, adding 384 and 96 calls. The total is 9,696 attempts and 19,392 completed decoder checkpoints. No data-dependent subset selection or receiver retuning is reported [E-B].

All communication results use the full fractional propagation model. Truth is used for generation and offline scoring, not for operational geometry or gain inputs. The main setting is $N=1024$, nominally eight physical paths, QPSK, LDPC$(2048,1024)$, and $\rho=0.5$. Kernel fixtures at other sizes are qualification/scaling experiments, not end-to-end FER evidence for those sizes.

## Comparator contracts

EP2 and EP4 are local proper-complex coded/SP adaptations of structured time-domain EP [6]. They perform two and four EP sweeps per coded round, respectively, with two coded rounds and mean-only physical refits. EP4 is a stronger accuracy control, not an eliminated configuration. Both start natively from observed pilot acquisition and include their online physical refinement, inference, decoder, and interface costs.

The PBi comparator is a local coded/SP PBiGaBP-family adaptation with eight inference iterations per round, two coded rounds, and soft physical refit [5]. It is not represented as the original authors' complete radar/communication software. Its predefined subset is used as a richer and expensive joint-inference reference. POINT has the same principal pipeline as TF but suppresses the explicitly propagated scalar gain variance. It is an internal control, not an independently tuned competing family.

Part-A FIXED-inner holds the gain mean fixed within each batch while retaining outer refits, gain pseudo-variance calculation, and zero propagated gain variance. Comparing POINT with FIXED-inner therefore isolates within-batch gain-mean adaptation. NO-FEEDBACK retains the decoder calls but discards feedback, while NO-GEOMETRY retains acquired path centers without the subsequent geometry updates. The last two controls do not mean “no coding” and “oracle geometry,” respectively.

| Component | TF | EP2 / EP4 | PBi | POINT |
|---|---|---|---|---|
| Native observed-only start | Yes | Yes | Yes | Yes |
| Coded rounds | 2 | 2 | 2 | 2 |
| Inner budget per round | 20 joint iterations | 2 / 4 EP sweeps | 8 bilinear iterations | 20 joint iterations |
| Physical refit | Soft | Mean-only | Soft | Soft |
| Inner gain adaptation | Yes | Through outer refits | Yes | Yes |
| Propagated gain uncertainty | One scalar | Comparator-specific | Cavity approximation | Explicit propagation disabled |
| LDPC cap per call | 50 | 50 | 50 | 50 |
| Part-B observations/SNR | 1,024 | 1,024 | First 32 | First 128 |

Table: Frozen receiver and comparator contracts. All arms are the declared local proper-complex coded/SP implementations; the PBi and POINT results use predefined subsets [E-A], [E-B].

The implementations share eligible computational optimizations, including the time-domain evaluation of physical-refit objectives. The comparison is not made favorable to TF by forcing competitors through an I1 warm-up loop or by withholding a numerically equivalent refit implementation.

## Primary paired reliability inference

For a comparison, define a rescue as a frame on which the comparator fails and TF succeeds, and a harm as a frame on which TF fails and the comparator succeeds. Let their counts be $R$ and $H$. Then

$$
\widehat\Delta
=\widehat{\mathrm{FER}}_{\rm TF}-\widehat{\mathrm{FER}}_{\rm C}
=\frac{H-R}{n}. \tag{51}
$$

The predeclared tolerances are $0.02$ at 6 and 6.5 dB and $0.01$ at 7 dB, for both EP comparators. Six simultaneous one-sided upper bounds are constructed. Their conservative exact-binomial form can be expressed as follows. Let $U_H$ be a Clopper–Pearson upper bound for the harm probability and $L_R$ a lower bound for the rescue probability, each with tail allocation $\eta=0.05/12$. Then

$$
U_\Delta=U_H-L_R. \tag{52}
$$

A union bound over twelve one-sided component events gives coverage of at least 95% for all six excess-FER upper bounds jointly. No independence between harm and rescue counts is assumed. Dependence is handled by defining the two mutually exclusive outcomes on the same paired frame. This conservative construction reproduces the supplied final upper bounds from the reported counts to their displayed precision.

A negative upper bound supports lower frame-error probability for TF in that comparison. A positive upper bound below the registered tolerance supports the narrower noninferiority criterion. It does not establish equal FER. Separate lower-bound families must not be combined with these upper bounds and called a joint two-sided 95% interval.

Bits within a decoded frame are dependent and do not increase the number of independent samples. The supplied final summary does not include the complete primary information-bit-error totals; no primary BER curve is inferred from the frame-error counts.

## Timing, checkpoints, and uncertainty

Complete online latency includes acquisition, physical refits, inference, LDPC calls, and saved-checkpoint hooks. Static configuration construction and offline truth scoring/storage follow the frozen experiment boundaries. Every online failed attempt would remain charged; the final campaign reports no numerical failures or missing decisions.

Reported timing intervals are pointwise 95% paired moving-block bootstrap intervals, preserving the paired methods and accounting for serial run-order dependence. They are not the simultaneous reliability family in (52). A ratio of medians is also distinct from the median of per-frame ratios. We report the quantities actually supplied by the final analysis and do not reconstruct an empirical latency distribution from a few quantiles.

Deadline outcomes use the last completed decoder checkpoint available before a fixed time. The reference deadlines were fixed from the earlier EP2 direction-validation medians before Part B. The final report retains five prescribed fractions; the two fractions available in the supplied compact summary are shown below. These are measured time-to-decision results on one CPU configuration, not worst-case execution-time guarantees or a claim of deployment-level real-time feasibility.

## Reproducibility boundary of this evidence edition

The final reports identify the numerical source, the code dimensions, the inherited channel/power convention, and the retained remote manifests. They do not reproduce every final execution-manifest field in the supplied text. The exact CPU model, the final dependency/thread manifest, numerical chirp constants, pilot sequence identifier, full channel-sampling law, and bootstrap block-length/replicate settings must be transcribed from those retained records before external release. They are not replaced here by values from a different archived experiment. This is a metadata limitation of the present draft, not a request to rerun the experiment or a qualification of the reported paired counts.

The manuscript includes every numerical result available in the final summaries that supports its main claims. It does not invent missing stage-time tables, full raw latency CDFs, primary BER/NMSE values, or scope-extension results. Appendix C identifies the exact retained record categories needed to complete those archival details.

# Numerical results

## Final prospective reliability

Table 2 gives the primary Part-B results. Every cell has 1,024 fresh paired observations. TF has lower observed frame-error counts at all three SNRs, and the stronger EP4 improves substantially over EP2. The comparison therefore does not depend on choosing the weakest EP setting.

| SNR (dB) | TF errors | TF FER | EP2 errors | EP2 FER | EP4 errors | EP4 FER |
|---:|---:|---:|---:|---:|---:|---:|
| 6.0 | 206 | 0.201172 | 487 | 0.475586 | 309 | 0.301758 |
| 6.5 | 43 | 0.041992 | 140 | 0.136719 | 74 | 0.072266 |
| 7.0 | 14 | 0.013672 | 29 | 0.028320 | 20 | 0.019531 |

Table: Final unrestricted information-frame errors and rates. Counts are supplied by Part B; rates are counts divided by 1,024. Each SNR remains a separate statistical cell [E-B].

![Final Part-B frame-error rates. Lines connect the three measured SNR points only; they are not an interpolation model for an error floor or an unmeasured operating range. Simultaneous paired comparison bounds are in Table 3.](figures/part_b_fer.pdf){width=85%}

At 6 dB, the empirical absolute reductions relative to EP2 and EP4 are $281/1024$ and $103/1024$. At 6.5 dB they are $97/1024$ and $31/1024$. These differences are accompanied by very few harms: two, nine, one, and one, respectively. The paired information is stronger and more informative than comparing independent marginal FER intervals.

| SNR | Comparator | Rescue / harm | Excess-FER upper (pp) | Tolerance (pp) |
|---:|---|---:|---:|---:|
| 6.0 | EP2 | 283 / 2 | −23.094 | 2 |
| 6.0 | EP4 | 112 / 9 | −6.538 | 2 |
| 6.5 | EP2 | 98 / 1 | −6.554 | 2 |
| 6.5 | EP4 | 32 / 1 | −1.129 | 2 |
| 7.0 | EP2 | 17 / 2 | 0.131 | 1 |
| 7.0 | EP4 | 9 / 3 | 0.793 | 1 |

Table: Simultaneous one-sided 95% family of upper bounds on $\mathrm{FER}_{\rm TF}-\mathrm{FER}_{\rm comparator}$. “pp” denotes percentage points. Negative values at 6 and 6.5 dB support lower FER; the 7-dB values support the registered tolerance but not superiority [E-B].

All six upper bounds satisfy the prospective criteria. The distinction at 7 dB is important: the point estimates favor TF, but the upper bounds permit a small positive excess. Consequently, the statistical conclusion there is not “TF is equally accurate” and not “TF is superior.” It is that its excess FER lies below the specified practical margin with the simultaneous coverage guaranteed by the construction.

These final results replace the earlier development-only wording about a promising speed route. The native method now has fresh, prospectively evaluated reliability evidence in the frozen 6–7-dB setting. The experiment remains limited to that setting; increasing the sample size within it does not establish generalization to different codes, pilot powers, path-resolution conditions, or hardware.

## Complete online latency

The median online latency of TF is approximately 0.284–0.288 s. EP2 requires approximately 0.492–0.502 s, while EP4 requires approximately 0.713–0.731 s. The median reduction is 42.1–42.6% relative to EP2 and 60.0–60.6% relative to EP4. The upper 95% TF/EP2 median-ratio bounds are 0.580, 0.583, and 0.583, all below the registered target of 0.8 [E-B].

| SNR | Method | Median, s [95% CI] | p90, s [95% CI] | p95, s [95% CI] |
|---:|---|---|---|---|
| 6.0 | TF | 0.2882 [0.2873, 0.2890] | 0.3071 [0.3058, 0.3093] | 0.3130 [0.3111, 0.3152] |
| 6.0 | EP2 | 0.5020 [0.4967, 0.5097] | 0.6929 [0.6845, 0.7004] | 0.7195 [0.7102, 0.7258] |
| 6.0 | EP4 | 0.7310 [0.7205, 0.7490] | 1.1237 [1.1049, 1.1333] | 1.1751 [1.1612, 1.1907] |
| 6.5 | TF | 0.2862 [0.2852, 0.2869] | 0.3046 [0.3026, 0.3080] | 0.3103 [0.3085, 0.3127] |
| 6.5 | EP2 | 0.4947 [0.4905, 0.4979] | 0.6802 [0.6695, 0.6900] | 0.7171 [0.7053, 0.7267] |
| 6.5 | EP4 | 0.7161 [0.7102, 0.7223] | 1.1081 [1.0802, 1.1223] | 1.1583 [1.1411, 1.1877] |
| 7.0 | TF | 0.2842 [0.2830, 0.2852] | 0.3043 [0.3025, 0.3057] | 0.3097 [0.3078, 0.3119] |
| 7.0 | EP2 | 0.4916 [0.4870, 0.4976] | 0.6760 [0.6629, 0.6871] | 0.7069 [0.6933, 0.7223] |
| 7.0 | EP4 | 0.7132 [0.7074, 0.7239] | 1.0836 [1.0595, 1.1120] | 1.1531 [1.1323, 1.1835] |

Table: Complete online latency from Part B. Intervals are pointwise paired moving-block bootstrap intervals, not simultaneous reliability intervals. The table preserves both central and tail summaries [E-B].

![Median complete online latency and reported pointwise 95% uncertainty. Acquisition, refits, inference, LDPC processing, and checkpoint hooks are included.](figures/part_b_median_latency.pdf){width=85%}

The tail comparison is also favorable. TF/EP2 p90 ratios are 0.443, 0.448, and 0.450. This matters because a receiver with an attractive median but a long execution tail may miss an externally imposed deadline. The present evidence shows a smaller measured tail as well as a smaller median. It does not establish a hard upper bound on execution time or predict another CPU's latency distribution.

![Reported 95th-percentile complete latency with pointwise 95% bootstrap intervals. These are quantile summaries, not reconstructed empirical CDFs.](figures/part_b_tail_latency.pdf){width=85%}

The two-FFT specialization is part of the implementation, but the complete latency advantage must not be assigned entirely to the difference between two and four transforms. The structured EP alternatives perform different Gaussian inference computations, and all receivers include acquisition, refinement, and decoding. Without the final per-stage CSV values, no numerical percentage of the overall saving is attributed to a particular stage in this manuscript.

## Decisions under fixed deadlines

At the earlier fixed EP2-median deadlines, approximately 0.50 s per cell, TF incurs the same frame-error counts as its unrestricted output. EP2 and EP4 incur more errors because the decision available at the deadline may be an earlier checkpoint. At 0.6 times those fixed reference deadlines, approximately 0.30 s, TF remains close to its unrestricted result while the EP configurations have substantially larger deadline error counts.

| SNR | Deadline fraction | TF errors/1,024 | EP2 errors/1,024 | EP4 errors/1,024 |
|---:|---:|---:|---:|---:|
| 6.0 | 1.0 | 206 | 649 | 897 |
| 6.5 | 1.0 | 43 | 336 | 596 |
| 7.0 | 1.0 | 14 | 168 | 358 |
| 6.0 | 0.6 | 214 | 955 | 1,024 |
| 6.5 | 0.6 | 44 | 696 | 1,024 |
| 7.0 | 0.6 | 14 | 496 | 1,024 |

Table: Reported deadline information-frame errors. The reference times were fixed before Part B from earlier EP2 medians. Only the two fractions reproduced in the supplied summary are displayed; the experiment retained all five registered fractions [E-B].

These results are a useful communication interpretation of the latency reduction. They do not imply that an EP receiver should be operated with insufficient time in every application. With a looser deadline, its stronger final decision may be available. The relevant result is the measured quality of the decision at the same resource deadline, not a claim that late information has no value.

## Numerical equivalence and kernel scaling

Part A qualified the proposed two-FFT realization against a competent four-FFT implementation and an independently constructed dense CPP reference. The maximum state/LLR discrepancies were $5.20\times10^{-14}$ and $4.85\times10^{-12}$, respectively. Observation residuals were compared only after the required unitary coordinate alignment. The stated tolerances were absolute $2\times10^{-9}$ and relative $10^{-8}$ [E-A].

| $N$ | $P$ | Two-FFT kernel, ms | Four-FFT kernel, ms | Ratio |
|---:|---:|---:|---:|---:|
| 256 | 8 | 10.719 | 11.820 | 0.907 |
| 512 | 8 | 13.567 | 15.379 | 0.882 |
| 1,024 | 8 | 19.052 | 23.670 | 0.805 |
| 2,048 | 8 | 31.594 | 36.393 | 0.868 |
| 1,024 | 4 | 16.948 | 20.173 | 0.840 |
| 1,024 | 16 | 24.218 | 27.521 | 0.880 |

Table: Part-A twenty-iteration kernel medians, seven interleaved repeats per fixture after numerical qualification. These times exclude radio acquisition, physical refinement, and LDPC processing [E-A].

![Part-A kernel scaling at fixed $P=8$. Both curves evaluate the same scalar map. The plot is not an end-to-end FER or complete-memory scaling experiment.](figures/part_a_kernel_scaling.pdf){width=85%}

The independent dense reference was timed only at $N=256,P=8$, where its twenty-iteration kernel required 41.877 ms, compared with 10.719 ms for TF. Its 44.240-ms dense-basis setup was recorded separately, and the retained basis occupied 8,388,608 bytes. No dense measurements at the other sizes are implied. These checks support the exact implementation claim and characterize constants; they do not establish a lower bound on other implementations.

## Attribution to gain-mean adaptation, feedback, and geometry

Part A used the same first sixteen saved validation observations in each SNR cell. The TF, POINT, and FIXED-inner outcomes were:

| SNR | TF errors / 16 | POINT errors / 16 | FIXED-inner errors / 16 | FIXED-to-POINT rescues / harms |
|---:|---:|---:|---:|---:|
| 6.0 | 2 | 3 | 16 | 13 / 0 |
| 6.5 | 1 | 1 | 13 | 12 / 0 |
| 7.0 | 0 | 0 | 6 | 6 / 0 |

Table: Controlled attribution on reused observations. POINT and FIXED-inner both suppress propagated gain variance, retain gain pseudo-variance calculations and outer refits, and differ in within-batch gain-mean adaptation [E-A].

The large POINT–FIXED difference supports the role of within-batch gain-mean adaptation on these saved frames. It is stronger mechanistic evidence than observing nonzero movement in a trace. It is not a fresh-sample population estimate and does not assert that all TF-versus-EP rescues have one exclusive cause.

On the same first eight 6.5-dB observations, TF failed on one frame, NO-FEEDBACK on five, and NO-GEOMETRY on eight. These scoped interventions support retaining the two existing functions. NO-FEEDBACK still executes both decoder calls, so the experiment concerns information availability rather than coded versus uncoded transmission. NO-GEOMETRY retains observed acquired centers and gain adaptation; it does not introduce true geometry as an oracle [E-A].

## Prospective variance and richer-inference controls

The larger predefined Part-B POINT subset gives TF error counts 21, 8, and 2 out of 128, versus POINT's 20, 9, and 3. TF rescues/harms relative to POINT are 2/3, 1/0, and 1/0. The direction of the small difference is not uniform at the lowest SNR. Latency is similar. Therefore a general reliability benefit from propagated scalar gain variance has not been established. This result does not prove equivalence in messages, information BER, or future frames, and the frozen primary remains TF.

On the first 32 Part-B observations per SNR, TF fails on 6, 2, and 0 frames, whereas the PBi adaptation fails on 21, 10, and 0. Its median latency is approximately 14.36 s, compared with approximately 0.29 s for TF. This is exploratory subset evidence about the declared implementation, not a universal ranking of PBiGaBP or proof that every richer cavity representation is unnecessary [E-B].

## Startup and late-iteration diagnostics

The final Part-A trace closure reuses one full-vector frame per SNR and the first eight paired scalar traces per SNR. It contains 240 vector-derived rows and 1,920 scalar rows, not that many independent radio observations. No precision floor fired in the audited subset.

| SNR | Median late $Nv_h^{\rm post}$ | Output correction | Reaction / backprojection | TF gain movement | POINT gain movement |
|---:|---:|---:|---:|---:|---:|
| 6.0 | 0.710 | 1.204% | 0.824% | 0.735% | 0.233% |
| 6.5 | 0.640 | 1.178% | 0.767% | 0.830% | 0.357% |
| 7.0 | 0.567 | 1.185% | 0.756% | 0.576% | 0.419% |

Table: Source-defined descriptive medians over inner iterations 5–19, pooling the two coded rounds of each vector-audit frame. “Late” is an index window, not a convergence declaration [E-A].

The posterior variance identity agrees with the saved states, and the late corrections are consistent with the conditional $P/N$ argument at $N=1024,P=8$. At each round reset, however, $u_0=0.125$ and the output correction is much larger. The extended Part-A range, 196–467%, supersedes an attempt to summarize startup only by the earlier pooled per-SNR medians. Both summaries concern different aggregations of the same retained states; neither is evidence of a universal transient law.

POINT has zero explicit propagated-variance terms but still moves its gain means. Combined with Table 7, this supports a precise mechanism statement: the receiver benefits from joint gain-mean adaptation, coded feedback, and observed geometry updates in the scoped attribution tests; the incremental reliability benefit of scalar gain-variance propagation is unresolved and is not claimed.

## Integrity of the final evidence

All 9,696 Part-B attempts produced decisions; the report records zero numerical failures, zero missing decisions, and zero unknown scored bits. All 19,392 checkpoints were recounted successfully. The raw evidence remains in the retained remote campaign archive; the supplied summary records inventory and transfer verification. This manuscript does not claim a new local recount of those remote arrays.

The numerical qualification, attribution controls, and prospective test are different layers. The final performance tables use only Part B. Earlier validation and stopped predecessor campaigns are not pooled to increase sample size or manufacture a stronger significance claim.

# Discussion and limitations

## Why the computational contribution matters

The main result is not that a generic bilinear inference formula becomes novel when used with AFDM. The exact reductions show that all operations of the selected scalar map can be realized on compact full fractional paths. The complete receiver then demonstrates that this approximation is useful at its measured cost. The value lies in connecting the physical structure to every required inference operation and evaluating the resulting native coded pipeline under a prospective contract.

This interpretation explains why exact implementation equivalence and communication improvement coexist without contradiction. The two-FFT and four-FFT implementations have the same scalar-map decisions. TF and EP differ because they use different approximate inference mechanisms, not because one implementation changed coordinates. The measured complete latency reduction cannot be assigned solely to eliminating two FFT calls. Likewise, a lower-state representation does not prove that richer per-observation messages are never useful.

## The role of initialization and coding

The receiver does not solve blind acquisition from an arbitrary starting state. It uses observed pilot acquisition, bounded geometry refinement, and a moderate pilot-power fraction. These steps provide an initial physical explanation that the joint batch can improve. The NO-GEOMETRY and NO-FEEDBACK controls support retaining those functions on the audited frames, but do not justify universal claims about the necessary amount of pilot power or coding redundancy.

The finite-alphabet prior is shifted by the known pilot, while LDPC information is exchanged through target-prior-excluded messages. This is an important implementation contract, not a guarantee that a loopy approximate posterior is calibrated. The receiver's working gain prior can differ from the physical gain-generation law, and its geometry estimate comes from the same observation. These are ordinary but material limitations of the Bayesian interpretation.

## What Part B establishes beyond development

The prospective evidence supports more than a qualitative promise. Under the predeclared experiment, TF satisfies the six reliability tolerances and achieves substantial reductions in median and tail online latency. At 6 and 6.5 dB, the simultaneous upper bounds additionally support lower FER against both EP configurations. Those are positive statistical and engineering statements that should not be weakened to “perhaps useful.”

At the same time, no claim is made for all SNRs, all channel ensembles, all LDPC constructions, or all EP implementations. The final report states that no scope extension was run. Kernel tests at other $N$ do not fill that empirical gap. The main conclusion is therefore deliberately tied to the frozen channel, coding, geometry-acquisition, and CPU configuration.

## Important unresolved boundaries

Unresolved same-delay paths, missed acquisition groups, very weak pilots, channel evolution within a frame, fractional delays, and mismatched pulse shapes may reduce the quality of the compact fitted model. The exact path identities do not rescue an incorrect model class. Colored or nonlinear observation noise may invalidate the simple observation-equivariance argument for the scalar output update. Structured scalar AMP can also be unstable outside the tested regime; no global convergence theorem is supplied.

The final experiment contains 1,024 frames per cell and does not establish a $10^{-4}$ error floor, a deep-tail outage law, or a dB advantage at an unmeasured target FER. It contains no final primary BER or channel-NMSE table in the supplied compact evidence, so none is reconstructed here. It also contains no deployment-level energy measurement or hardware-independent timing bound.

The exact CPU and execution-manifest details are an archival transcription item for release. Their absence from the compact summaries does not warrant inventing them or replacing the reported seconds with measurements from a different machine. A reproducible submission must attach or transcribe those records together with the specified local baseline adaptations.

# Conclusion

A tensor-free specialization of scalar bilinear inference has been developed for native joint channel estimation and decoding in superimposed-pilot AFDM. The receiver retains the full estimated fractional-path response, preserves the coded variables in the affine-frequency domain, and avoids the explicit dense path tensor and observation-specific cavity arrays required by some alternative realizations. Observation-unitary equivariance and exact physical-path contractions establish the implementation's equality to the declared scalar map and its per-iteration work and state bounds.

The mechanism analysis separates exact algorithmic scalar variance identities from physical posterior uncertainty. It explains the conditional small-$P/N$ scale of late explicit corrections, the order-one startup exception, and the continued importance of gain-mean adaptation when propagated variance is suppressed. Controlled reused-observation interventions support the role of within-batch gain-mean updates, decoder feedback, and geometry refinement, while the prospective POINT subset does not establish a general additional reliability benefit from scalar gain-variance propagation.

In the final frozen prospective experiment, all six simultaneous one-sided reliability criteria are satisfied against two native structured-EP adaptations. The same bounds support lower FER at 6 and 6.5 dB, while the 7-dB result remains a tolerance statement. Median complete online latency is reduced by 42.1–42.6% relative to EP2 and 60.0–60.6% relative to EP4, with smaller reported latency tails. The contribution is a substantive computational and receiver specialization within an established inference family, supported in a clearly stated operating regime rather than by claims of posterior optimality, unconditional convergence, or universal superiority.

# Appendix A: Fourier evaluation of the refit uncertainty

Let $V=\operatorname{diag}(v)$ and $\widehat v(r)=\sum_kv_ke^{-j2\pi rk/N}$. The diagonal entries of $U_i^HU_j$ can be obtained by multiplying the two explicit path columns in (8). The $c_2$ phases cancel. Writing $\Delta l=l_j-l_i$, the remaining sum over the observation index is a finite-kernel inner product and yields

$$
[U_i^HU_j]_{kk}
=e^{j2\pi c_1(l_i^2-l_j^2)}
 e^{-j2\pi k\Delta l/N}
 D_N(\nu_j-\nu_i+2Nc_1\Delta l). \tag{53}
$$

Consequently,

$$
\boxed{
\Gamma_{ij}
=e^{j2\pi c_1(l_i^2-l_j^2)}
D_N(\nu_j-\nu_i+2Nc_1(l_j-l_i))
\widehat v(l_j-l_i).
} \tag{54}
$$

One FFT of $v$ and $P^2$ scalar evaluations compute this matrix without a dense data covariance. The identity is exact for the chosen diagonal $V$. For uniform $v$ and distinct delays, the off-diagonal entries vanish because the nonzero-lag Fourier coefficients of a constant sequence vanish. Thus a full matrix is not automatically more informative than a scalar uncertainty penalty in every channel or belief state.

The refit reuses the transformed mean waveform and observation across all geometry trials. Equation (54) is supporting computational infrastructure; its presence is not used to claim that off-diagonal covariance caused the final FER advantage.

# Appendix B: Conservative simultaneous paired bounds

For $m=6$ comparisons, set $\eta=\alpha/(2m)$ with $\alpha=0.05$. For a harm count $H$ and rescue count $R$ in $n$ paired frames, define

$$
U_H=
\begin{cases}
1,&H=n,\\
\operatorname{Beta}^{-1}(1-\eta;H+1,n-H),&H<n,
\end{cases}
$$

$$
L_R=
\begin{cases}
0,&R=0,\\
\operatorname{Beta}^{-1}(\eta;R,n-R+1),&R>0.
\end{cases} \tag{55}
$$

For each comparison, $\Pr(p_H\le U_H)\ge1-\eta$ and $\Pr(p_R\ge L_R)\ge1-\eta$. The union bound across the twelve component events gives simultaneous coverage at least $1-\alpha$ for

$$
p_H-p_R\le U_H-L_R. \tag{56}
$$

No independence assumption among the comparisons or between rescue and harm events is used. The construction is conservative because it bounds the two multinomial components separately. It remains valid for zero counts and does not assign zero uncertainty to zero observed discordance. Applying (55) to the six reported Part-B pairs reconstructs the upper values in Table 3 after rounding to three decimal percentage points. This reconstruction checks summary arithmetic; it is not an independent replay of the frame-level simulator or bootstrap timing analysis.

# Appendix C: Evidence and release record

The final Part-B report is the authority for performance; Part A is the authority for final qualification and attribution. The following records distinguish what is available in this manuscript edition from what remains retained remotely.

| Record | Present evidence | Use and remaining boundary |
|---|---|---|
| Final Part-B report | Counts, paired bounds, latency quantiles/CIs, two deadline fractions, subset controls, integrity totals | All main performance tables; raw CDF and stage statistics are not reconstructed |
| Final Part-A report | Same-map parity, kernel times, reused-frame interventions, memory probes, recounts | Numerical qualification and mechanism interpretation, not fresh performance samples |
| Paper Design v1 | Full damped equations, source identities, proofs, prospective contract | Method and theoretical reference; its earlier performance language is superseded |
| Native-joint verdict/archive | Path implementation and interface design | Archived mathematical code mapping; not a byte-identical replacement for the final remote checkout |
| Latest theory chapter | Exact operator, nuisance, expected-loss, and risk identities | Supporting theory translated consistently to the positive convention |
| Final execution manifests | Referenced and retained remotely, not reproduced in the compact uploads | Exact CPU/runtime/thread settings, chirps, pilot identifier, generator law, bootstrap settings, and complete code/configuration identities require transcription |

The last row is a specific release-documentation limitation. It is not a license to infer final parameters from older unrelated experiments. The accompanying Technical Master Document records the missing fields, source precedence, corrected historical interpretations, and the mathematical-to-code map in greater detail.

# References {.unnumbered}

[1] A. Bemani, N. Ksairi, and M. Kountouris, “Affine Frequency Division Multiplexing for Next Generation Wireless Communications,” *IEEE Transactions on Wireless Communications*, vol. 22, no. 11, pp. 8214–8229, 2023, doi: 10.1109/TWC.2023.3260906. Author manuscript: arXiv:2204.12798.

[2] K. Zheng, M. Wen, T. Mao, L. Xiao, and Z. Wang, “Channel Estimation for AFDM With Superimposed Pilots,” *IEEE Transactions on Vehicular Technology*, vol. 74, no. 2, pp. 3389–3394, 2025, doi: 10.1109/TVT.2024.3469380. Author manuscript: arXiv:2404.10232.

[3] J. T. Parker and P. Schniter, “Parametric Bilinear Generalized Approximate Message Passing,” *IEEE Journal of Selected Topics in Signal Processing*, 2016, doi: 10.1109/JSTSP.2016.2539123. Author manuscript: arXiv:1508.07575v2.

[4] P. Sun, Z. Wang, R. W. Heath Jr., and P. Schniter, “Joint Channel-Estimation/Decoding with Frequency-Selective Channels and Few-Bit ADCs,” *IEEE Transactions on Signal Processing*, doi: 10.1109/TSP.2018.2887189. Author manuscript: arXiv:1807.02494v2.

[5] K. R. R. Ranasinghe, H. S. Rou, G. T. F. de Abreu, T. Takahashi, and K. Ito, “Joint Channel, Data, and Radar Parameter Estimation for AFDM Systems in Doubly-Dispersive Channels,” *IEEE Transactions on Wireless Communications*, vol. 24, no. 2, pp. 1602–1619, 2025, doi: 10.1109/TWC.2024.3510935. Author manuscript: arXiv:2405.16945v4.

[6] Q. Yi, P. Yang, Z. Liu, Z. Sui, Y. Xiao, and G. Wu, “A Novel Low-Complexity Dual-Domain Expectation Propagation Detection Aided AFDM for Future Communications,” arXiv:2603.29218v1, 2026. The checked record identifies a WCNC workshop acceptance; no journal publication is presumed.

[7] K. Ito et al., “Joint Channel and Data Estimation via Parametric Bilinear Inference for OTFS Demodulation,” *IEEE Open Journal of the Communications Society*, vol. 5, pp. 6090–6105, 2024, doi: 10.1109/OJCOMS.2024.3463202.

[8] Y. Kanazawa, H. Iimori, C. Pradhan, S. Malomsoky, and N. Ishikawa, “Superimposed Pilot-Based OTFS: Will It Work?,” *IEEE Transactions on Vehicular Technology*, 2026, doi: 10.1109/TVT.2025.3608199. Author manuscript: arXiv:2501.15935v3.

[9] F. Huang, Q. Guo, Y. Zhang, and Y. Zakharov, “Message Passing-Based Joint Channel Estimation and Signal Detection for OTFS with Superimposed Pilots,” *IEEE Transactions on Vehicular Technology*, 2024, doi: 10.1109/TVT.2024.3378833. Author manuscript: arXiv:2309.08177v2.

[10] Y. Luo, Y. L. Guan, Y. Ge, Y. Jiang, L. Meng, and D. González G, “Data-aided Channel Estimation and Sensing With Sparse Bayesian Learning for AFDM-ISAC System,” arXiv:2607.18881v1, 2026. The checked author record states acceptance by *IEEE Transactions on Communications*; final volume/pages are not supplied.

[11] Ma et al., “Parametric Bilinear Iterative Generalized Approximate Message Passing Reception of FTN Multi-Carrier Signaling,” *IEEE Transactions on Communications*, vol. 69, no. 12, pp. 8443–8458, 2021, doi: 10.1109/TCOMM.2021.3114873. Detailed comparison is limited to the primary repository scope recorded in the project sources; full author-list transcription remains a bibliography item.

[12] Z. Yuan, Q. Guo, and M. Luo, “Approximate Message Passing with Unitary Transformation for Robust Bilinear Recovery,” arXiv:2005.14132v3.

[13] S. Sarkar, A. K. Fletcher, S. Rangan, and P. Schniter, “Bilinear Recovery using Adaptive Vector-AMP,” arXiv:1809.00024.

[14] Z. Li et al., “Joint channel estimation and signal detection for AFDM transmission with time-domain pilot arrangement,” EURECOM publication record 8323, 2025. Abstract-level positioning only.

[15] A. P. Dempster, N. M. Laird, and D. B. Rubin, “Maximum Likelihood from Incomplete Data Via the EM Algorithm,” *Journal of the Royal Statistical Society, Series B*, vol. 39, no. 1, pp. 1–22, 1977, doi: 10.1111/j.2517-6161.1977.tb01600.x.

## Internal experimental and derivation records {.unnumbered}

[E-B] “Part B — frozen prospective evidence,” supplied final `RESULTS(20260922-014341).md`, numerical source `2d130b4d`. Authority for the 3,072-observation prospective results, six simultaneous upper bounds, complete latency, deadline outcomes, and final subset controls.

[E-A] “PD1-Q Part A — qualification and attribution,” supplied final `RESULTS(20260922-014351).md`, numerical source `2d130b4d`, baseline `31d5ec0d`, runner scoring repair `d1fd9d4f`, mechanism recount `2311922f`. Authority for final qualification, reused-frame interventions, memory probes, and mechanism closure.

[E-D] “Paper Design v1: Tensor-Free Joint Channel Estimation and Decoding for Superimposed-Pilot AFDM,” supplied `SP_AFDM_Paper_Design_v1(3).md`. Mathematical and method specification; development-only performance statements are superseded by [E-B].

[E-N] “Tensor-Free Joint Channel and Data Inference for Coded SP-AFDM,” supplied `SP_AFDM_Native_Joint_Research_Verdict_20260921(2).md` and archived native continuation implementation. Source of the exact computational map and earlier engineering qualification, not a substitute for the final remote numerical checkout.

[E-T] “A Consistent Theory of Coded SP-AFDM Reception,” supplied `theory_chapter(9).pdf`, 26 pages. Exact supporting theory; its negative-sign physical convention is translated consistently in this manuscript.

[E-M] Supplied `TABLES(3).md`, earlier saved-state mechanism summary. Its pre/post conventions are retained; final expanded startup ranges and attribution conclusions follow [E-A].
