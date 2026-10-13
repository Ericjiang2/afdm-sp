---
title: "Technical Master Document: Native Tensor-Free Joint Coded SP-AFDM"
subtitle: "Authoritative derivation, implementation, and evidence reference — final Part-A / Part-B edition"
author: []
date: ""
lang: en-US
---

# Authority, scope, and how to read this document

## The current scientific object

The current receiver is `TF_J20_R2`: native observed-pilot acquisition, two coded rounds, twenty scalar bilinear iterations per round, damping $0.3$, soft physical-path refinement, and a fifty-iteration LDPC cap. The numerical source is `2d130b4d`; the qualified baseline is `31d5ec0d`. “Native” means that the receiver does not first run the former I1 outer loop. “Tensor-free” describes its joint-inference core, not the entire Python process or the pilot dictionary.

The central contribution is a full-fractional AFDM/SP computational specialization within an established parametric bilinear inference family. It is not a new AMP family, a new turbo principle, a new form of Gaussian shrinkage, or an exact acceleration of PBiGaBP's richer cavity map. The exact implementation results concern one declared scalar approximation. The communication result concerns its complete coded realization on a frozen experimental ensemble.

This reference is intentionally broader than the manuscript. It preserves derivations that explain the model and its failure modes, even when those derivations are not contribution statements. Earlier whitening, support-exchange, sparse-innovation, and finite-list ideas are retained only where they supply useful mathematics or negative evidence. They are not alternate current methods.

## Source precedence

The following evidence order governs every numerical or interpretive statement.

| Label | Source | Authority |
|---|---|---|
| E-B | Final `RESULTS(20260922-014341).md` | Prospective performance, final paired bounds, complete latency and deadline results |
| E-A | Final `RESULTS(20260922-014351).md` | Final numerical qualification, attribution, isolated memory, saved-trace closure |
| E-D | `SP_AFDM_Paper_Design_v1(3).md` | Frozen receiver equations, theoretical backbone, prospectively stated contract |
| E-N | `SP_AFDM_Native_Joint_Research_Verdict_20260921(2).md` | Native implementation rationale and earlier engineering evidence |
| E-M | `TABLES(3).md` | Earlier descriptive saved-state mechanism table, superseded where E-A expands it |
| E-T | `theory_chapter(9).pdf` | Exact supporting theory and earlier small mathematical witnesses |
| E-C | Archived native/frozen source packages inspected for this edition | Function-level explanation; not a byte-identical substitute for the final remote checkout |

E-B supersedes statements in E-D and E-N that publication-level prospective evidence is still pending. E-A's “Part B not started” is a status statement at Part-A closure; E-B is later evidence and supersedes that status without contradiction. The numerical receiver identity remains the same. E-A supersedes an earlier tentative mechanism statement that a POINT–FIXED intervention is still needed: that intervention has now been performed on saved observations.

Dates embedded in attachment filenames identify records; they are not new simulations or independently replicated experiments in this writing session. Heavy final arrays remain in the remote evidence archive described by the reports. The present edition uses the supplied final summaries, their stated recount receipts, and separately inspected archived reference code. It does not claim to have locally replayed the final 9,696 receiver attempts.

## Epistemic labels

An important equation can have one of several different statuses. The distinction should remain visible in manuscripts and reviewer responses.

**Exact physical identity:** an algebraic consequence of the stated sampled linear channel, transform, prefix, or probability distribution. Examples are unitarity, the finite integer expansion, and conditional Gaussian covariance for a known waveform.

**Exact algorithm identity:** an algebraic property of the declared scalar update, conditional on its state definitions and numerical guards. Observation-unitary equivariance and the scalar variance identity belong here. They do not prove that the approximation equals the true posterior.

**Conditional bound:** a statement requiring explicit lower bounds, fixed moments, or a fixed model. The small-$P/N$ feedback argument and the identifiability eigenvalue bound are examples. Removing their conditions changes the statement.

**Inferential approximation:** factorized symbol beliefs, scalar variance replacement, approximate Onsager reactions, proper-complex Gaussianization, or a plug-in geometry estimate. These choices define the practical receiver.

**Experimental result:** a measured quantity with a specified observation ensemble, source, denominator, and uncertainty procedure. Part-B paired reliability is distinct from Part-A reused-frame attribution and deterministic qualification.

**Mechanism interpretation:** an explanation consistent with theory and intervention evidence. It must not be promoted to a universal theorem or to exclusive attribution of every frame rescue.

## What is now established

The final prospective study contains 3,072 fresh independent observations and 9,696 paired receiver attempts. All six simultaneous one-sided reliability upper bounds meet their registered margins. At 6 and 6.5 dB, the upper bounds against both EP configurations are negative. At 7 dB, they establish the practical excess-FER tolerance but not superiority. Complete median latency is 42.1–42.6% lower than EP2 and 60.0–60.6% lower than EP4. The final report records no numerical failure, missing decision, or unknown scored bit [E-B].

Part A provides a strong implementation-level gain-mean intervention: on the same sixteen saved observations per cell, FIXED-inner fails on 16/13/6 frames, POINT on 3/1/0, and TF on 2/1/0 at 6/6.5/7 dB. This supports the role of within-batch gain-mean adaptation on those saved frames. It is not a new fresh-sample population estimate [E-A].

The prospective POINT subset does not establish a general incremental reliability advantage from propagated gain variance. Its frame counts are close to TF and its runtime is similar. Therefore full scalar propagation remains the frozen primary, but is not marketed as an independently validated source of reliability gain.

## Remaining documentation gaps, not invented parameters

The compact final reports refer to records that are retained remotely but are not reproduced in the supplied text: the exact CPU/runtime/thread manifest, numerical chirp constants, pilot sequence/root, full generator delay/Doppler/gain sampling law, precise SNR conversion, bootstrap block length and number of replicates, exact decoder/code construction fields, final stage-time CSVs, and the equation/cost baseline map. These records may already be complete remotely; their absence here is not evidence that they were never recorded.

The drafts do not fill these fields from general knowledge or from older experiments with superficially similar names. Archived code explains how the receiver is computed, while E-A/E-B establish which frozen source was evaluated. Before release, the missing manifest fields should be transcribed into the configuration table. This does not require a new Monte Carlo experiment.

The raw Part-B primary BER totals, final channel NMSE table, full latency ECDFs, and three of the five deadline fractions are also not present in the compact final summary. None is inferred from frame counts or quantiles. The supplied tables are sufficient for the principal scoped latency–reliability claim, but not for those additional plots or statements.

# Notation and assumptions

## Dimensions and indexing

| Symbol | Meaning and dimension |
|---|---|
| $N$ | Useful block length and DAFT dimension |
| $K$ | Number of information bits; $K=1024$ in the primary code |
| $c$ | Binary codeword of length $2N$ |
| $d$ | Scaled QPSK data vector in $\mathbb C^N$ |
| $p$ | Known, scaled superimposed pilot in $\mathbb C^N$ |
| $x=p+d$ | Transmitted AF-domain variable |
| $x_T=A^Hx$ | Time-domain waveform; not independent QPSK |
| $y,Y=A^Hy$ | AF-domain and rotated observation vectors |
| $P_\star$ | Physical truth path count |
| $P$ | Working fitted path dimension in one inference batch |
| $S$ | Active integer dictionary coefficient count in historical methods |
| $Q$ | Pilot dictionary size, 515 in the reference acquisition interface |
| $(l_i,\nu_i,h_i)$ | Working integer delay, real normalized Doppler, and complex gain |
| $M_i,U_i$ | Time-domain phase-shift path and AF-domain path, both $N\times N$ |
| $H_\star,H(h)$ | True and working channel operators |
| $B(x)$ | $N\times P$ matrix with columns $U_ix$ |
| $B_T(x)$ | $A^HB(x)$, the time-observation response matrix |
| $\widetilde H(h)$ | $A^HH(h)$, mapping AF variables to time observations |
| $\mu,v,V$ | Symbol mean, marginal-variance vector, and covariance/working diagonal matrix |
| $v_x$ | Mean symbol marginal variance, $N^{-1}\sum_kv_k$ |
| $u_t$ | Pre-update propagated scalar gain variance |
| $v_{h,t}^{\rm post}$ | Gain-denoiser posterior scalar after iteration $t$ |
| $v_r,v_q$ | Scalar data and gain pseudo-observation variances |
| $s_t,\alpha_t$ | Observation residual/score and scalar output precision |
| $\bar x_t,\bar h_t$ | Barred mean states used by the damped map |
| $\bar v_{p,t},v_{p,t}$ | Separately stored damped output-variance quantities |
| $\Gamma$ | $P\times P$ projected symbol-uncertainty matrix used by CE |
| $R$ | $P\times P$ physical-path Frobenius Gram divided by $N$ |
| $\beta$ | Fixed damping, $0.3$ in the primary |
| $\tau$ | Inner gain-prior variance, $1/P$ |
| $\sigma^2$ | Complex thermal-noise variance per sample |
| $\rho,P_d$ | Pilot-power fraction and data symbol energy, $P_d=1-\rho$ |

All sample indices are zero-based and circular when explicitly reduced modulo $N$. Superscripts $H$, $T$, and $*$ mean conjugate transpose, transpose, and conjugate. $\operatorname{tr}$ is trace; $\|\cdot\|$ on a vector is Euclidean norm; $\|\cdot\|_F$ is Frobenius norm; $\|\cdot\|_2$ on a matrix is spectral norm. Logarithms in likelihoods are natural. “pp” denotes percentage points, not relative percent.

The symbol $P$ is deliberately not used for all forms of sparsity. Eight physical paths, forty acquired integer coefficients, and 515 dictionary columns are different dimensions. A proof that uses a fixed working $P$ does not automatically apply when acquisition produces a number of paths growing with $N$.

## Physical assumptions and the tested operating scope

The sampled channel has integer delays, arbitrary real fractional Dopplers, sufficient chirp-periodic prefix, ideal synchronization, proper white sampled noise, and fixed gains/geometry within a useful block. The primary receiver uses at most eight observed delay groups and one physical path per group. Its algebra handles repeated delays, but that does not imply that its selected estimator resolves multiple close Dopplers at the same acquired delay.

The primary evidence is at $N=1024$, nominal $P_\star=8$, QPSK, LDPC$(2048,1024)$, and $\rho=0.5$. It does not contain a final code-family sweep, fractional-delay experiment, lower-pilot-power study, or arbitrary unresolved-path validation. Kernel qualification at $N=256,512,1024,2048$ and path counts 4/8/16 concerns exactness and cost, not FER generalization.

The physical gain-generation law and the receiver prior must remain separate. The working inner prior is $\mathcal{CN}(0,I/P)$. The native verdict records normalized physical gains in the generator lineage; the exact final law is fixed by the retained generator manifest and is not reconstructed from that broad description. A receiver can be useful under prior mismatch without being the Bayes-optimal receiver for the physical law.

## Power, code mapping, and noise units

For $a=\sqrt{P_d/2}$,

$$
d_k=a[(-1)^{c_k}+j(-1)^{c_{N+k}}],\qquad x=p+d. \tag{T1}
$$

The stored bit order is all in-phase bits followed by all quadrature bits. Positive LLR favors bit zero and hence the positive component. The primary alphabet is $\{\pm0.5\pm0.5j\}$, so $\mathbb E|d_k|^2=0.5$. A variance computed from this alphabet already contains the data power.

The noise convention is

$$
w\sim\mathcal{CN}(0,\sigma^2I),\qquad
\mathbb E|w_k|^2=\sigma^2,
\qquad
\operatorname{Var}(\Re w_k)=\operatorname{Var}(\Im w_k)=\sigma^2/2. \tag{T2}
$$

The pilot–data cross term contributes to an individual frame's energy:

$$
\|p+d\|^2=\|p\|^2+\|d\|^2+2\Re(p^Hd). \tag{T3}
$$

It is not set to zero by post-generation normalization. Ensemble cancellation of its expectation, when valid, is a different statement. SNR, data SNR, and $E_b/N_0$ are not interchangeable labels. The frozen final SNR definition must be retained from its manifest rather than guessed from a normalization used in an earlier campaign.

# DAFT, CPP, and full fractional-path algebra

## Unitary transform and its fast actions

The negative-exponent unitary DFT and positive chirps are

$$
F_{mn}=\frac1{\sqrt N}e^{-j2\pi mn/N},
\quad \Lambda_c^+=\operatorname{diag}(e^{j2\pi cn^2}),
\quad A=\Lambda_{c_2}^+F\Lambda_{c_1}^+. \tag{T4}
$$

Thus

$$
Az=\Lambda_{c_2}^+F(\Lambda_{c_1}^+z),
\qquad
A^Hz=(\Lambda_{c_1}^+)^HF^H((\Lambda_{c_2}^+)^Hz). \tag{T5}
$$

Both actions require chirp multiplications and one normalized FFT/IFFT. All factors are unitary, so $A^HA=AA^H=I$, energy is preserved, and a proper white Gaussian vector remains proper white Gaussian under either action.

The invariance of a probability law and the independence of transformed symbols must not be confused. A white Gaussian noise vector retains independent components. A finite QPSK vector transformed by a dense unitary matrix generally does not remain a vector of independent QPSK symbols. The receiver rotates observations for computation and preserves the coded variables in their original AF coordinates.

## Delayed samples and the chirp-periodic prefix

For an integer delay $l$, define

$$
[\Pi_lz]_n=z_{(n-l)\bmod N},
\qquad
[\Delta_\nu^+]_{nn}=e^{j2\pi\nu n/N}, \tag{T6}
$$

$$
\chi_l(n)=
\begin{cases}
e^{j2\pi c_1[N^2+2N(n-l)]},&n<l,\\
1,&n\ge l,
\end{cases}
\qquad M(l,\nu)=C_l\Delta_\nu^+\Pi_l. \tag{T7}
$$

The sample action is

$$
[M(l,\nu)z]_n
=\chi_l(n)e^{j2\pi\nu n/N}z_{(n-l)\bmod N}. \tag{T8}
$$

$\Pi_l$ is a permutation and both diagonal factors have unit magnitude. Hence $M^HM=I$. The CPP factor must be retained even when particular chirp/block settings make it numerically one. Omitting it because it vanishes in a convenient test can invalidate later nontrivial-prefix settings.

To derive the adjoint, set $k=(n-l)\bmod N$ and reverse the mapping in the inner product. The result is

$$
[M(l,\nu)^Hz]_k
=\chi_l((k+l)\bmod N)^*
 e^{-j2\pi\nu((k+l)\bmod N)/N}
 z_{(k+l)\bmod N}. \tag{T9}
$$

The location at which the phase is evaluated matters. Conjugating a phase at $k$ instead of at the shifted observation index is generally incorrect.

## Explicit AF-domain path entry: a complete derivation

The effective path is $U(l,\nu)=AM(l,\nu)A^H$. On a nonwrapped sample $n\ge l$, expanding the two transforms and the delayed waveform gives the phase terms

$$
c_1n^2-c_1(n-l)^2=2c_1nl-c_1l^2,
$$

$$
\frac{-mn+k(n-l)+\nu n}{N}
=\frac{(k-m+\nu)n-kl}{N},
$$

and the outer chirps give $c_2(m^2-k^2)$. On a wrapped sample, the delayed time index is $n-l+N$. The extra quadratic-chirp phase from replacing $n-l$ by $n-l+N$ is canceled by (T7). The additional DFT phase is an integer multiple of $2\pi$ because $k$ is integer. Thus the same expression holds for every sample.

With

$$
D_N(t)=\frac1N\sum_{n=0}^{N-1}e^{j2\pi nt/N}, \tag{T10}
$$

summing over $n$ yields

$$
\boxed{
[U(l,\nu)]_{mk}
=e^{j2\pi[-c_1l^2-kl/N+c_2(m^2-k^2)]}
D_N(k-m+\nu+2Nc_1l).
} \tag{T11}
$$

This is the positive-convention expression used by the present reference. The older theory chapter defines negative chirps and negative Doppler exponentials. Its formula becomes (T11) under $(c_1,c_2,\nu)\mapsto(-c_1,-c_2,-\nu)$. Reversing only $\nu$ leaves inconsistent chirp phases and effective shifts.

If $\alpha=2Nc_1$ and $\nu=q$ are integers, $D_N$ vanishes except when

$$
k=m-q-\alpha l\pmod N. \tag{T12}
$$

Therefore the effective cyclic shift is $s=q+\alpha l$. Distinct physical delay–Doppler coordinates can share an effective shift. The existence or absence of such collisions is a property of the actual dictionary and chirp setting, not an automatic fact of AFDM.

## Finite fractional-Doppler expansion

Consider the sampled modulation vector $z_n=e^{j2\pi\nu n/N}$. Its discrete Fourier coefficients under the finite integer basis are

$$
c_q(\nu)=\frac1N\sum_{n=0}^{N-1}e^{j2\pi(\nu-q)n/N}
=D_N(\nu-q). \tag{T13}
$$

Finite Fourier inversion gives

$$
e^{j2\pi\nu n/N}
=\sum_{q=0}^{N-1}c_q(\nu)e^{j2\pi qn/N}.
$$

Multiplying by the fixed delay/prefix and DAFT factors proves

$$
\boxed{U(l,\nu)=\sum_{q=0}^{N-1}c_q(\nu)U(l,q),
\qquad \sum_q|c_q(\nu)|^2=1.} \tag{T14}
$$

The last equality is Parseval because $|z_n|=1$. A fractional path is therefore exactly representable on a complete finite integer dictionary. This does not imply that a small integer support is exact or that all $N^2$ possible coefficients can be identified from one $N$-sample observation.

The important distinction is between three dimensions: a small physical path count, the potentially large number of coefficients required by an exact integer expansion, and the number of inference messages used by a receiver. The native method selects the compact physical parameterization and avoids a second approximation that truncates an included path's leakage.

## Orthogonality, coherent merging, and tail energy

For complete integer coordinates,

$$
\operatorname{tr}\{U(l,q)^HU(l',q')\}
=N\mathbf1_{\{l=l'\}}\mathbf1_{\{q=q'\}}. \tag{T15}
$$

For unequal delays the time-domain product is a nonzero cyclic shift and has zero trace. For equal delays the prefix and common shift cancel under trace invariance, leaving an integer-exponential sum. Unitary conjugation preserves the trace product.

If several physical paths contribute to the same integer coordinate, merge their complex amplitudes before computing energy:

$$
g_{lq}=\sum_{r:l_r=l}h_r c_q(\nu_r),\qquad
H=\sum_{l,q}g_{lq}U(l,q). \tag{T16}
$$

The Frobenius projection onto a set $\mathcal S$ satisfies

$$
\left\|H-\sum_{(l,q)\in\mathcal S}g_{lq}U(l,q)\right\|_F^2
=N\sum_{(l,q)\notin\mathcal S}|g_{lq}|^2. \tag{T17}
$$

It is generally wrong to sum separate physical-path tail energies: their amplitudes can interfere at a shared integer coordinate. It is also wrong to renormalize retained coefficients and call the result the original physical channel. Renormalization cannot reconstruct removed phase relationships or couplings.

The earlier theory's half-bin $N=64$ energy calculation retained 40.5366%, 81.0732%, and 91.7251% of a path's operator energy with one, two, and five largest coefficients. These are deterministic representation figures, not FER or channel-acquisition results [E-T, Sec. 3.2]. They are useful for understanding why “few paths” and “few AF diagonals” are different claims.

## Fractional physical-path Gram matrix

For arbitrary real Dopplers,

$$
R_{ij}=\frac1N\operatorname{tr}(U_i^HU_j)
=\mathbf1_{\{l_i=l_j\}}D_N(\nu_j-\nu_i). \tag{T18}
$$

The integer orthogonality proof extends except that the equal-delay Doppler sum need not vanish. Thus

$$
c(h)=\|H(h)\|_F^2/N=h^HRh. \tag{T19}
$$

$R$ is Hermitian positive semidefinite because it is a Gram matrix of operators. A small negative value of $h^HRh$ from rounding may be clipped under a stated tolerance; a materially negative value indicates an implementation or numerical failure. It is not evidence that a physical channel has negative power.

Distinct delays imply $R=I$. Repeated delays do not. Frobenius orthogonality of the operators also does not imply that their responses to a particular waveform are independent. That distinction is central to the posterior-identifiability counterexample below.

# The SP inference problem from first principles

## Why there is no universal linear pilot extractor

Suppose the allowed data vectors span $\mathbb C^N$ and a fixed linear operation $L$ obeys $LHd=0$ for every allowed data vector. By linearity it vanishes on their span, so $LH=0$ and therefore $LHp=0$. A universal linear operation that deletes all unknown data also deletes the pilot response under this condition.

This is a limited impossibility statement. It does not apply to nonlinear joint inference, restricted data subspaces, independent training observations, or other information that changes the problem. It explains why using code constraints or data replicas is qualitatively different from searching for a universally separating linear filter.

A one-path flat example shows the estimator-specific nature of SP floors. If

$$
y_n=h(\sqrt{P_p}+\sqrt{P_d}z_n)+w_n,
\qquad \hat h=\frac1{N\sqrt{P_p}}\sum_ny_n,
$$

with independent zero-mean unit-variance $z_n$, then

$$
\mathbb E[|\hat h-h|^2\mid h]
=\frac{P_d|h|^2+\sigma^2}{NP_p}. \tag{T20}
$$

Subtract $h$, expand the two zero-mean sums, and use their independence. The surviving data term at vanishing thermal noise is a floor of this particular averaging estimator at fixed $N$, not a lower bound on all coded SP receivers.

## Conditional disturbance moments are not a likelihood theorem

For prior data mean zero and covariance $V_0$, independent of thermal noise,

$$
\operatorname{Cov}(Hd+w\mid H)=HV_0H^H+\sigma^2I. \tag{T21}
$$

No Gaussian-data assumption is needed. For $H=hU$ with unitary $U$ and $V_0=P_dI$, the covariance is scalar even for fractional Doppler. For $H=h_0I+h_1\Pi$, cross terms in $HH^H$ can make it colored without fractional Doppler. If zero-mean uncorrelated path gains are averaged out, cross-path terms can disappear in an ensemble covariance; that does not make each realized channel's covariance white.

Code constraints can change data correlations, so $V_0=P_dI$ requires a specified code ensemble or approximation. After conditioning on the same observation, data errors and thermal noise are generally dependent. Reusing (T21) with posterior moments as though those errors were independent of the original noise is not automatically valid.

## Reference posterior and practical approximation

For a fixed working geometry and code prior,

$$
p(d,h\mid y,\theta)
\propto P_{\mathcal C}(d)
\exp[-\|y-H(h,\theta)(p+d)\|^2/\sigma^2]
\exp[-P\|h\|^2]. \tag{T22}
$$

The likelihood is bilinear in unknown data and gains. Exact codeword summation and gain integration are different from scalar symbol denoising. The native receiver uses a factorized approximate symbol distribution and scalar precision summaries; it updates the two means together. Its finite-alphabet probabilities need not be the marginals of an exact codeword posterior.

Known SP enters naturally through the shifted support $x_k\in p_k+\mathcal Q$. The prior for $x$ is not a new independent pilot measurement. Similarly, a gain fitted from $y$ may initialize an iterative state but is not an independent prior mean unless the receiver defines a separate empirical-Bayes or conditional-training interpretation. The frozen method avoids that extra claim by keeping its gain prior zero-centered.

## The reference objective is communication risk under complete cost

Let $\hat b_{\mathcal A}$ be a receiver's completed information decision and $T_{\mathcal A}$ its online latency. Useful objectives include unrestricted risk $\Pr(\hat b_{\mathcal A}\ne b)$ and risk under a common deadline, using the last completed checkpoint. Optimizing channel NMSE, an internal residual, or a scalar confidence alone is not equivalent to optimizing those risks.

An implementation can lower the same algorithm's cost without changing its statistical approximation. Another receiver can change both cost and approximation quality. These comparisons must be separated experimentally. The two-FFT/four-FFT/dense qualification is a same-map comparison. TF/EP/PBi is a different-map comparison. Neither is exact-posterior inference unless separately established.

# The current scalar joint-inference map

## State initialization and update order

A batch uses one fixed geometry estimate, positive thermal variance, and one frozen code-check prior. At its start, the symbol means and marginal variances are computed from that prior. This differs from initializing the inner means directly from the previous decoder APP used by CE. The fitted gains initialize $h_0$. TF initializes $u_0=1/P$; POINT initializes $u_0=0$.

Set $x_0=p+\mu_0$, $\bar x_{-1}=x_0$, $\bar h_{-1}=h_0$, $s_{-1}=0$, and $\alpha_{-1}=0$. Output-variance histories are unset until the first iteration. The response cache initially equals the response of $x_0$. Every coded round resets these observation-factor histories because its geometry can change.

The order within each iteration is part of the numerical method: calculate the current response and raw variances from unbarred states; update residual and precision; update barred means/cached responses; calculate both pseudo-observations; denoise data and gains; then store the new propagated gain variance. Using post-update $v_x$ or $v_h$ in an earlier step is a different algorithm.

## Raw scalar variance from an isotropic working model

A useful interpretation of the raw variance terms starts with working independent errors $e$ and $\delta h$ satisfying $\mathbb E[ee^H]=v_xI$ and $\mathbb E[\delta h\delta h^H]=uI$. Expand

$$
\sum_i(h_i+\delta h_i)U_i(x+e)-H(h)x
=H(h)e+B(x)\delta h+\sum_i\delta h_iU_ie. \tag{T23}
$$

All three cross terms vanish under the stated independent zero-mean surrogate. Their average output energies are respectively

$$
\frac{v_x\|H(h)\|_F^2}{N}=v_xc(h),
\quad
\frac{u\|B(x)\|_F^2}{N}=Pu\frac{\|x\|^2}{N},
\quad
\frac{uv_x\sum_i\|U_i\|_F^2}{N}=Puv_x. \tag{T24}
$$

This explains the structure of the scalar quantities. The actual available data variances need not be equal; the algorithm replaces them by their mean at this interface. Nor does the diagonal/isotropic surrogate prove that the actual posterior data and gain errors are independent. Equations (T23)–(T24) justify the second moments of the declared surrogate, not exact inference for the coupled coded posterior.

The two raw quantities are

$$
\bar b_t=v_{x,t}c(h_t)+Pu_t\frac{\|x_t\|^2}{N},
\qquad b_t=\bar b_t+Pu_tv_{x,t}. \tag{T25}
$$

The distinction between $\bar b_t$ and $b_t$ is retained in the reaction/output steps; they must not be merged into one undocumented variance.

## Damped output step

At $t=0$, use $\bar v_{p,0}=\bar b_0$ and $v_{p,0}=b_0$. At $t>0$,

$$
\bar v_{p,t}=\beta\bar b_t+(1-\beta)\bar v_{p,t-1},
\qquad
v_{p,t}=\beta b_t+(1-\beta)v_{p,t-1}. \tag{T26}
$$

The predicted observation, approximate Onsager correction, residual, and precision are

$$
\hat z_t=B_T(x_t)h_t-\bar v_{p,t}s_{t-1}, \tag{T27}
$$

$$
s_t=\beta\frac{Y-\hat z_t}{\sigma^2+v_{p,t}}+(1-\beta)s_{t-1},
\qquad
\alpha_t=\frac{\beta}{\sigma^2+v_{p,t}}+(1-\beta)\alpha_{t-1}. \tag{T28}
$$

For a scalar Gaussian latent-observation approximation and Gaussian thermal noise, the undamped Gaussian score has the residual-over-summed-variance form used here. The extra reaction in (T27), the scalar approximations that generated its inputs, and the chosen damping belong to the inherited P-BiG-AMP-type map [3]. They do not follow from an exact posterior factorization of the finite deterministic AFDM problem.

Notice that raw variances are not multiplied by $\beta$ at the first iteration, while the residual and precision are. The first output precision is $\beta/(\sigma^2+v_{p,0})$, not $1/(\sigma^2+v_{p,0})$. This matters when reconstructing startup traces.

## Barred states, pseudo-variances, and reactions

Update

$$
\bar x_t=\beta x_t+(1-\beta)\bar x_{t-1},
\qquad
\bar h_t=\beta h_t+(1-\beta)\bar h_{t-1}. \tag{T29}
$$

For fixed geometry, cache

$$
B_T(\bar x_t)=\beta B_T(x_t)+(1-\beta)B_T(\bar x_{t-1}). \tag{T30}
$$

The initial previous means equal the initial current means, so the first barred means equal $x_0,h_0$. Let $\epsilon_0=10^{-12}$. The implemented reciprocal quantities are

$$
v_{r,t}=\frac1{\max(\alpha_tc(\bar h_t),\epsilon_0)},
\qquad
v_{q,t}=\frac1{\max(\alpha_t\|\bar x_t\|^2,\epsilon_0)}. \tag{T31}
$$

The two pseudo-observations are

$$
r_{x,t}=x_t+v_{r,t}\left[
\widetilde H(\bar h_t)^Hs_t-\alpha_tPu_t\bar x_t
\right], \tag{T32}
$$

$$
r_{h,t}=h_t+v_{q,t}\left[
B_T(\bar x_t)^Hs_t-\alpha_tNv_{x,t}\bar h_t
\right]. \tag{T33}
$$

These equations are different in three ways that should remain visible. The data reaction uses the propagated gain variance $u_t$; the gain reaction uses the current mean symbol variance $v_{x,t}$. Their multiplicities are $P$ and $N$, respectively. The starting means outside the brackets are unbarred, while the reaction means and adjoint operators use barred states.

The algorithm does not claim that $v_r$ and $v_q$ are the exact covariance of physical estimation errors. They are scalar pseudo-channel parameters of the approximation. When a numerical floor is active, an identity that cancels $v_q^{-1}$ or $v_r^{-1}$ using the unfloored expression no longer applies. E-A reports that no precision floor fired in the audited trace subset, not that no floor can ever be active in another regime.

## Finite-alphabet denoising with the superimposed pilot

Let $\mathcal Q=\{a(\pm1\pm j)\}$ with $a=\sqrt{P_d/2}$. The exact finite sum at the declared scalar pseudo-channel is

$$
\ell_{k,t}(a)=\log\pi_k(a)
-\frac{|r_{x,k,t}-p_k-a|^2}{v_{r,t}},
\qquad
q_{k,t}(a)=\frac{e^{\ell_{k,t}(a)}}{\sum_{a'}e^{\ell_{k,t}(a')}}. \tag{T34}
$$

A log-sum-exp calculation is used for numerical stability. The pilot is subtracted once in the pseudo-channel likelihood. It is not independently canceled using a second channel estimate at this step. Equivalently, the denoiser could operate on the shifted alphabet $p_k+\mathcal Q$.

The output moments are

$$
\mu_{k,t+1}=\sum_a a q_{k,t}(a),
\qquad
v_{k,t+1}=\sum_a|a|^2q_{k,t}(a)-|\mu_{k,t+1}|^2.
\tag{T35}
$$

Since QPSK has constant modulus, the first term is $P_d$. The implementation clips small negative numerical values at zero. The next transmitted mean is $x_{t+1}=p+\mu_{t+1}$.

The finite sum is exact for the scalar pseudo-likelihood and prior supplied to it. That statement must not be confused with exact marginalization of the full codeword posterior. The correlations induced by the physical observation and LDPC graph are not all retained in the scalar map.

## Gaussian gain denoising

For the pseudo-observation $r_h=h+\eta_q$ with working $\eta_q\sim\mathcal{CN}(0,v_qI)$ and prior $h\sim\mathcal{CN}(0,\tau I)$, expand

$$
\frac{\|r_h-h\|^2}{v_q}+\frac{\|h\|^2}{\tau}
=\left(v_q^{-1}+\tau^{-1}\right)
\left\|h-\frac{\tau}{\tau+v_q}r_h\right\|^2+\text{constant}.
$$

Thus

$$
h_{t+1}=\frac{\tau}{\tau+v_{q,t}}r_{h,t},
\qquad
v_{h,t}^{\rm post}=\frac{\tau v_{q,t}}{\tau+v_{q,t}},
\qquad \tau=1/P. \tag{T36}
$$

TF propagates $u_{t+1}=v_{h,t}^{\rm post}$. POINT still computes $v_q$ and the gain-mean shrinkage but sets $u_{t+1}=0$. FIXED-inner additionally holds the gain mean constant within that batch. It still receives updated gains from the outer refit. These definitions explain why POINT and FIXED are different mechanisms even though both have zero propagated gain variance.

There is no extra damping of the denoiser means after (T35)–(T36). The fixed damping acts through (T26), (T28), and (T29). A rewritten algorithm that damps the final means once more is not the frozen primary.

## Full batch pseudocode with state timing

```text
Inputs: y, p, sigma2, fixed working paths, incoming code prior.
Compute Y = IDAFT(y), physical phases, delayed-read indices, and R.
Initialize mu,v from the code prior; x=p+mu; h=fitted gains.
Set u=1/P, old barred means=x,h, old residual=0, old precision=0.
For t=0,...,19:
    B_current <- full time-path responses of IDAFT(x).
    vx <- mean(v); current_power <- h^H R h.
    Form raw bar_b and b from PRE-update x,h,u,vx.
    Set or separately damp bar_vp and vp.
    Form prediction using B_current,h and PREVIOUS residual.
    Update residual and precision with beta=.3.
    Update barred means; update B_bar by the matching linear recurrence.
    Form vr,vq with the explicit 1e-12 denominator guards.
    Form aggregate data adjoint and gain adjoint from barred states.
    Form rx,rh, including both displayed reaction terms.
    Finite-alphabet denoise rx-p with the frozen code prior.
    Gaussian-denoise rh; store POST-update h and vh_post.
    Propagate vh_post for TF (or zero for POINT).
    Check finite states; record exact pre/post conventions when instrumented.
Return detector APP/extrinsic, data moments, gain means, and propagated variance.
```

At $\beta=1$ the barred means are current means and the stored output quantities equal raw quantities, giving the undamped scalar form in the earlier native verdict. That form is useful for interpretation but does not replace the fixed-$\beta$ implementation in a reproduction specification.

# Observation equivariance and tensor-free computation

## Exact algorithmic equivariance

**Lemma T-A.** For the declared scalar map with isotropic Gaussian output noise, let $V$ be any unitary observation transformation. Replace $y$ by $Vy$ and all $U_i$ by $VU_i$, leaving unknown-variable priors and initial means unchanged. Then every scalar quantity and unknown-variable pseudo-observation/denoiser output is unchanged, while the observation residual is multiplied by $V$.

**Proof in update order.** The transformed response matrices are $B'=VB$ and $H'=VH$. Their Euclidean/Frobenius norms are unchanged. The initial residuals satisfy the statement. Assuming it holds before an iteration, the raw and stored damped variances are identical, and the predicted observation is rotated. The scalar Gaussian output operation and its scalar damping give $s'=Vs$, with identical output precision. The barred means remain identical, and linear caching gives $B'(\bar x)=VB(\bar x)$. Finally,

$$
(VH)^H(Vs)=H^Hs,\qquad (VB)^H(Vs)=B^Hs. \tag{T37}
$$

Both pseudo-observations agree, so finite-alphabet and gain denoisers agree. Induction proves the whole batch, and identical decoder inputs extend the equality through coded rounds when the corresponding refit objective is also evaluated equivalently. $\square$

The last qualification is not a claim that any unrelated geometry algorithm commutes with the rotation. Here the same squared-residual refit is evaluated in two unitary-related domains, with the same search and moments. Exact arithmetic gives the same objective values; finite-precision search ties can require a numerical tolerance contract.

The proof is not a statement about arbitrary vector-variance AMP. A row-dependent diagonal precision generally becomes dense after a unitary rotation. Nonlinear componentwise output likelihoods are likewise not preserved as the same separable factors. The invariance also cannot improve $H^HH$, because $(VH)^H(VH)=H^HH$. The role is computational, not conditioning-based robustification.

## Computational contractions

Choose $V=A^H$. Form $x_T=A^Hx$ once per iteration and

$$
[B_T(x)]_{ni}=\varphi_i[n]x_T[(n-l_i)\bmod N]. \tag{T38}
$$

The prediction and gain adjoint are

$$
z_T[n]=\sum_i[B_T(x)]_{ni}h_i,
\qquad
[B_T(x)^Hs]_i=\sum_n[B_T(x)]_{ni}^*s_n. \tag{T39}
$$

For the data adjoint, reverse the physical action using (T9), sum the paths in time, and apply one DAFT:

$$
\widetilde H(h)^Hs=A\sum_i h_i^*M_i^Hs. \tag{T40}
$$

The scalar normalization requirements follow from path unitarity and (T18):

$$
\|H(h)\|_F^2=Nh^HRh,
\quad \|B(x)\|_F^2=P\|x\|^2,
\quad \sum_i\|U_i e_k\|^2=P,
\quad \sum_k\|U_i e_k\|^2=N. \tag{T41}
$$

These expressions cover every contraction used by the scalar map. They do not omit cross-path terms in the channel norm; those are encoded by $R$. They also do not assume independent transformed data. They operate on the current deterministic mean vector inside an approximate algorithm.

A competent AF-observation realization can use the same path operations with four transforms per iteration. Its unknown-variable iterates are identical to the two-transform realization by Lemma T-A. The earlier per-path-FFT reference was a weaker implementation and is not the principal transform-count comparator. Part A now supplies a competent same-map comparison over six fixtures.

## Quantities counted and not counted

The inner map needs $O(NP)$ phase/read/adjoint operations, $O(N\log N)$ transform operations, and up to $O(P^2)$ norm work. Its persistent response/path state is $O(NP+P^2)$. The input code prior, symbol moments, residuals, and pseudo-observations add $O(N+P)$ terms already below that bound for positive $P$.

The bound assumes a fixed batch geometry and does not include acquisition, geometry trials, decoder graph storage, or language/runtime overhead. It is not an assertion that every PBiGaBP or EP implementation must allocate a dense tensor. It is a positive statement that this implementation does not need one.

# LDPC APP, extrinsic information, and CE consumers

## Bitwise prior and symbol marginalization

For a QPSK label $(b_I,b_Q)$ and code-check LLRs $(L_I,L_Q)$,

$$
\log\pi(a)=\frac12(1-2b_I)L_I+\frac12(1-2b_Q)L_Q-\log Z. \tag{T42}
$$

For any symbol log-likelihood $\ell(a)$, define

$$
L_I^{\rm APP}=\log\sum_{a:b_I=0}e^{\ell(a)+\log\pi(a)}
-\log\sum_{a:b_I=1}e^{\ell(a)+\log\pi(a)}. \tag{T43}
$$

Since the target in-phase prior is constant within each sum, its contribution is exactly $L_I$. The target-prior-excluded message is

$$
L_I^{\rm ext}=L_I^{\rm APP}-L_I. \tag{T44}
$$

The other bit's prior remains inside both sums. It affects the marginal likelihood when I/Q evidence is coupled and should not be subtracted a second time. The same derivation applies to the quadrature target.

For an independent scalar proper Gaussian channel $z=d+n$ and uniform QPSK, this reduces to

$$
L_I=4a\Re z/\sigma_n^2,\qquad
L_Q=4a\Im z/\sigma_n^2. \tag{T45}
$$

The factor of four follows by subtracting the two squared distances and using complex variance $\mathbb E|n|^2=\sigma_n^2$. Using a real-component variance in the denominator without adjusting the factor is a common unit error.

## Decoder exchange and actual clipping

Each detector output is clipped before it is passed to the LDPC decoder. The actual clipped input must be the quantity subtracted from decoder APP when constructing raw check extrinsic. Subtracting an unclipped precursor from an APP produced using a clipped input breaks the recorded interface identity.

The frozen interface uses clipping at $[-20,20]$. The newly obtained clipped check extrinsic replaces the old prior. It is not added to the old prior as another independent observation. The decoder's returned hard decision is scored using the frozen information-coordinate extraction map, not by assuming that the first $K$ positions of every code construction must be the information bits.

A zero syndrome means that a decoded vector is a valid codeword, not necessarily the transmitted codeword. It is not a CRC unless a separate transmitted CRC exists in the rate accounting. No such extra oracle correctness test is inserted into TF.

## Moments passed to CE

For independent bit probabilities, let $t_I=\tanh(L_I/2)$ and $t_Q=\tanh(L_Q/2)$. Then

$$
\mu=a(t_I+jt_Q),
\qquad
v=a^2(2-t_I^2-t_Q^2),
\qquad
\zeta=\mathbb E[(d-\mu)^2]=a^2(t_Q^2-t_I^2). \tag{T46}
$$

The variance follows from $\mathbb E|d|^2=2a^2$; the pseudo-variance follows from subtracting $\mu^2$ from $\mathbb E[d^2]$. Even when the prior constellation is proper, different I/Q reliabilities can make the working posterior improper.

The physical-refit objective requires posterior-like moments that include observation information. The current receiver therefore uses clipped decoder APP moments for the next refit. The code-check prior initializes the next joint batch. Extrinsic-only CE would be a different approximation and is not implied by the rule that detector messages must exclude the target's input prior.

The proper scalar map ignores pseudo-covariance in its Gaussian pseudo-channel. That is a declared approximation, not an assertion that $\zeta=0$. The earlier noncircular extension is retained in the historical technical material but is not part of the final primary.

## Damping is not automatically a mixture of posteriors

If two actual distributions are mixed as $q=(1-\eta)q_0+\eta q_1$, their moments obey

$$
\mu=(1-\eta)\mu_0+\eta\mu_1,
$$

$$
V=(1-\eta)V_0+\eta V_1+
\eta(1-\eta)(\mu_1-\mu_0)(\mu_1-\mu_0)^H. \tag{T47}
$$

The last term follows by expanding raw second moments and subtracting $\mu\mu^H$. A similar transpose expression holds for pseudo-covariance. Damping a mean while leaving an unrelated variance unchanged does not implement this mixture.

The barred means in the frozen scalar map are algorithmic history states. They are not described as moments of the probability mixture in (T47). Therefore there is no reason to add the mixture's between-mean covariance to that map unless the method itself is changed. This resolves an easy but incorrect reconciliation between older moment-consistent damping theory and the current implementation.

## What interface correctness proves

The APP/extrinsic identities and clipping checks establish that the same explicit input is not counted again through the stated interface. They do not remove all dependence in a loopy code/channel graph, prove posterior calibration, or establish a new independent training observation. The final Part-A recount verifies these numerical contracts on retained arrays; the final Part-B performance evaluates the resulting complete receiver.

# Observed geometry acquisition and physical refinement

## Pilot initializer: what is shared and what is not known

The native receiver begins with `pilot_front`, not the full I1 loop. The archived implementation forms integer pilot-response columns on delays $0,\ldots,l_{\max}$ and five integer Dopplers $-2,\ldots,2$. The primary interface has $Q=515$ columns. It invokes the B0-p2-s0.5 initializer with a support budget of forty and the specified full-rank least-squares driver. Selected observed coordinates and coefficients initialize the physical grouping.

The dictionary includes the pilot power through the actual pilot vector. An initializer that normalizes columns must account for the normalization in its coefficient output; that implementation contract is inherited from the qualified baseline. The current documents do not reinterpret the label B0-p2 as a new estimator derivation.

The observed initializer is intentionally imperfect. Its selected delay groups can omit a physical path. The subsequent one-path-per-group refit does not create an oracle delay detector. The primary evidence demonstrates the complete pipeline under its frozen ensemble; it does not establish perfect support acquisition.

## Grouping and bounded coordinate search

For every selected delay, the reference groups the squared magnitudes of its integer coefficients and ranks delays by their summed observed energy. At most eight groups are retained. Within each group, the strongest observed Doppler coefficient supplies the initial physical Doppler center. One physical path is fitted per selected delay.

Each refit performs two coordinate passes. Coordinate $i$ remains in the intersection of its initial center plus/minus $0.75$ with $[-3,3]$. The bounded scalar search uses tolerance $0.002$ and at most sixteen scalar evaluations per update. The initial centers are recomputed from the current observed state each coded round. Every accepted coordinate update improves the same frozen objective, and all candidate evaluations count toward cost.

These settings define a local estimator. They are neither a global off-grid optimum nor a theorem that the true path lies inside every search interval. When the working path set is empty or invalid, a numerical/protocol failure must be reported; no hidden truth-guided replacement is permitted.

## Expected complete-data loss: detailed derivation

Fix a distribution $q(d)$, observations, path operators, and gain vector $h$. Let $e=d-\mu$, with $\mathbb E_qe=0$ and covariance $V$. Since

$$
y-H(h)(p+d)=y-H(h)(p+\mu)-H(h)e,
$$

expanding the norm and averaging gives

$$
\mathbb E_q\|y-H(h)(p+d)\|^2
=\|y-H(h)(p+\mu)\|^2+
\mathbb E_q[e^HH(h)^HH(h)e].
$$

Use $\mathbb E(e^HKe)=\operatorname{tr}(KV)$ and expand $H(h)=\sum_i h_iU_i$ to obtain

$$
\mathbb E_q\|y-H(h)(p+d)\|^2
=\|y-\Phi_\mu h\|^2+h^H\Gamma h,
\qquad
\Gamma_{ij}=\operatorname{tr}(U_i^HU_jV). \tag{T48}
$$

For any $h$, $h^H\Gamma h=\operatorname{tr}(HVH^H)\ge0$ because $V\succeq0$. Thus $\Gamma$ is positive semidefinite. This proof requires no Gaussian $q$ and no properness. The pseudo-covariance does not appear independently in this proper complex squared norm. If a different real/noncircular loss is used, that conclusion need not transfer unchanged.

With a proximal penalty $\lambda\|h-h_0\|^2$, the normal equations are

$$
(\Phi_\mu^H\Phi_\mu+\Gamma+\lambda I)h
=\Phi_\mu^Hy+\lambda h_0. \tag{T49}
$$

Adding $\Gamma$ is a zero-centered uncertainty penalty. Increasing a proximal regularizer changes both sides of (T49) when $h_0\ne0$, so the two operations are not interchangeable.

## Fourier Gamma reduction

For the current diagonal working covariance $V=\operatorname{diag}(v)$, write

$$
\Gamma_{ij}=\sum_k v_k\sum_m U_i[m,k]^*U_j[m,k].
$$

Substituting (T11), the phase factors depending on $c_2$ cancel. Let $\Delta l=l_j-l_i$. The residual column phase is

$$
e^{j2\pi c_1(l_i^2-l_j^2)}e^{-j2\pi k\Delta l/N}.
$$

The finite-kernel product sum is

$$
\sum_m D_N(k-m+\nu_i+2Nc_1l_i)^*
D_N(k-m+\nu_j+2Nc_1l_j)
=D_N(\nu_j-\nu_i+2Nc_1\Delta l). \tag{T50}
$$

To verify (T50), expand both kernels into length-$N$ sums. Summation over $m$ eliminates every unequal Fourier-index pair, leaving the single finite exponential sum on the right. Therefore

$$
\boxed{
\Gamma_{ij}=
 e^{j2\pi c_1(l_i^2-l_j^2)}
 D_N(\nu_j-\nu_i+2Nc_1(l_j-l_i))
 \widehat v(l_j-l_i).
} \tag{T51}
$$

The Fourier samples of $v$ are reused across all Doppler trials in a refit because $q$ is frozen. Only the finite-kernel arguments change. The implementation explicitly Hermitian-symmetrizes the computed matrix to suppress roundoff; that does not justify repairing a materially incorrect or indefinite formula.

The diagonal is $\sum_kv_k$. When $v$ is uniform and delays are distinct, every nonzero-delay Fourier sample vanishes, so the matrix reduces to a scalar diagonal even with fractional Dopplers. For repeated delays, the same simplification does not follow. Under integer monomial operators with distinct effective shifts and diagonal $V$, the historical formula $\Gamma=(\sum v_k)I$ follows by a separate support argument. Neither degeneracy proves the covariance correction is always unnecessary; both require the stated structure.

## Gain elimination and profile objective

The frozen current refit uses $h_0=0$ and $\lambda=\sigma^2$. Let

$$
Q_\theta=\Phi_\mu^H\Phi_\mu+\Gamma(\theta)+\sigma^2I,
\qquad b_\theta=\Phi_\mu^Hy.
$$

Positive thermal variance makes $Q_\theta$ positive definite. Completing the square gives

$$
Q(h,\theta)
=\|y\|^2-b_\theta^HQ_\theta^{-1}b_\theta
+(h-Q_\theta^{-1}b_\theta)^HQ_\theta(h-Q_\theta^{-1}b_\theta). \tag{T52}
$$

Thus the gain solution is $Q_\theta^{-1}b_\theta$ and the minimized objective is

$$
Q^*(\theta)=\|y\|^2-b_\theta^HQ_\theta^{-1}b_\theta. \tag{T53}
$$

The same value is obtained with $Y=A^Hy$ and $B_T(p+\mu)$ because the transform is unitary. This is the exact reason that the time-domain refit optimization can be shared by TF and the competing refit-based receivers without changing its numerical objective.

The objective uses a point gain minimizer, not a gain-marginal likelihood. Integrating a Gaussian gain prior adds a determinant term, whereas profiling does not. The final receiver does not silently use the list evaluator's marginalized metric in place of (T53).

## Why the complete pipeline is not exact EM

The reference coded-data free energy, for a fixed channel parameter and valid-code prior, is

$$
\mathcal F(q,h)=\sigma^{-2}\mathbb E_q\|y-H(h)(p+d)\|^2
+D_{\rm KL}(q\|P_{\mathcal C}).
$$

Bayes' rule gives

$$
\mathcal F(q,h)
=-\log p(y\mid h)+D_{\rm KL}(q\|p(d\mid y,h))+\text{constant}. \tag{T54}
$$

An exact E-step makes the KL term zero. A nonincreasing M-step for that exact fixed distribution, followed by another exact E-step, proves nondecreasing observed likelihood. It does not prove global optimum or FER descent [15].

The frozen native receiver does not satisfy those exact-EM premises. Its data beliefs are approximate; its inner dynamics include damping and approximate reactions; its geometry is updated locally; and its refit penalty $\sigma^2\|h\|^2$ is not the $P\sigma^2\|h\|^2$ penalty implied by its inner prior. The local objective decrease is still a useful computational contract, but it is not one common Bayesian descent theorem for the entire receiver.

The older exact-code toy counterexample remains useful: a mean-only channel update can reduce the true marginal likelihood even when the starting data posterior is exact, whereas the moment-consistent update including $\Gamma$ follows the correct expected-loss calculation [E-T, Sec. 8.1]. That counterexample does not establish a population FER gain from the full off-diagonal matrix in the current receiver.

## Fixed-objective sensitivity

Let $M=\Phi_\mu^H\Phi_\mu+\Gamma+\lambda I\succ0$, $b=\Phi_\mu^Hy+\lambda h_0$, and $h=M^{-1}b$. If $\widetilde\Gamma=\Gamma+E$ while the same mean/right-hand side is retained, then

$$
\widetilde h-h=-(M+E)^{-1}Eh. \tag{T55}
$$

If $\|E\|_2<\lambda_{\min}(M)$,

$$
\frac{\|\widetilde h-h\|}{\|h\|}
\le\frac{\|E\|_2}{\lambda_{\min}(M)-\|E\|_2}, \qquad h\ne0. \tag{T56}
$$

This bound is obtained from the inverse norm and eigenvalue perturbation inequality. It is conditional on the same $\Phi_\mu$, $b$, support, and regularization. A different decoder mean changes both the design and right-hand side and requires additional perturbation terms. The bound concerns two optimizer outputs, not true channel error or FER.

# Mechanism: scalar variance, startup, and gain-mean motion

## The exact scalar identity and its proper interpretation

With the gain pseudo-variance floor inactive, the Gaussian posterior scalar is

$$
v_{h,t}^{\rm post}
=\frac1{P+v_{q,t}^{-1}}
=\frac1{P+\alpha_t\|\bar x_t\|^2}.
$$

Let $a_t=\|\bar x_t\|^2/N$. Then

$$
\boxed{Nv_{h,t}^{\rm post}=\frac1{\alpha_ta_t+P/N}.} \tag{T57}
$$

This is an exact identity of the executed scalar Gaussian denoiser, not an approximation in $N$. Its conditional asymptotic reading needs a family of states for which $\alpha_ta_t$ stays bounded away from zero. If $\alpha_ta_t\ge\kappa>0$, then

$$
Pv_{h,t}^{\rm post}\le\frac{P/N}{\kappa}. \tag{T58}
$$

For fixed $P$ and order-one precision/mean-waveform power, the scalar variance is order $1/N$. But if the pseudo-channel is uninformative, if the mean waveform becomes very small, or if the numerical floor is active, that informal scaling cannot be applied unchanged. The trace audit at $N=1024$ checks the identity, not an empirical exponent across block lengths.

## Direct output and data-reaction contributions

The raw output correction attributable to propagated gain variance is

$$
\delta_t^{\rm out}=Pu_t\left(\|x_t\|^2/N+v_{x,t}\right). \tag{T59}
$$

If the previous posterior update satisfies (T58), and both bracketed quantities are bounded, then $\delta_t^{\rm out}=O(P/N)$. This is an absolute statement. A percentage normalized by a small data-only variance can be large even when the absolute correction is small.

The explicit data-side reaction is

$$
w_t^{\rm react}=v_{r,t}\alpha_tPu_t\bar x_t
=\frac{Pu_t}{c(\bar h_t)}\bar x_t, \tag{T60}
$$

again requiring the relevant floor to be inactive. The coefficient is small only if $c(\bar h_t)$ does not vanish. A ratio to the norm of another nearly zero update has no general smallness guarantee.

The saved percentage diagnostics use precisely defined source normalizations. E-A identifies the actual reaction/backprojection ratio and records direct-term norms in the retained extended table. That detailed definition file is not reproduced in the compact upload. This master therefore gives the algebraic terms (T59)–(T60) and reports the audited percentages as source-defined quantities, rather than inventing an unprovided denominator for every old summary column.

## Startup and damping memory

At the beginning of each TF coded round, the propagated variance is

$$
\boxed{u_{\rm start}=1/P,\qquad P u_{\rm start}=1.} \tag{T61}
$$

Thus (T59) starts at $\|x_0\|^2/N+v_{x,0}$, and (T60) has coefficient $1/c(\bar h_0)$. Neither has a $P/N$ prefactor. There are two such resets in the evaluated receiver.

On a fixed state trajectory, suppose the isolated raw contribution is $\delta_0$ at startup and at most $C\varepsilon$ later, where $\varepsilon=P/N$. Solving the scalar damping recurrence gives

$$
e_t=(1-\beta)^t\delta_0+
\beta\sum_{k=1}^{t}(1-\beta)^{t-k}\delta_k, \tag{T62}
$$

$$
e_t\le(1-\beta)^t\delta_0+C\varepsilon[1-(1-\beta)^t]. \tag{T63}
$$

The geometric sum proves the inequality. It is a bound on the memory of one explicitly isolated term. TF and POINT do not follow the same state trajectory once the startup variance differs, so (T63) does not bound their LLR difference, decoding probability, or channel estimate. In particular, it cannot justify an untested policy that switches off propagation at a chosen iteration.

The final Part-A extension reports initial output-correction ratios spanning 196%–467%. The earlier E-M table reports pooled per-SNR medians of approximately 227%, 284%, and 388%. These are not contradictory: they are different summaries of the startup rows. The final expanded range is used for the overall startup statement, and the older medians are retained only with their original aggregation label.

## Exact mean-motion identity

Write

$$
g_t=B_T(\bar x_t)^Hs_t-\alpha_tNv_{x,t}\bar h_t.
$$

Equation (T33) gives $r_h=h_t+v_qg_t$. The Gaussian mean update therefore obeys

$$
h_{t+1}-h_t
=\frac{v_q(g_t-Ph_t)}{1+Pv_q}.
$$

With the reciprocal floor inactive,

$$
\boxed{
h_{t+1}-h_t=
\frac{B_T(\bar x_t)^Hs_t-\alpha_tNv_{x,t}\bar h_t-Ph_t}
{P+\alpha_t\|\bar x_t\|^2}.
} \tag{T64}
$$

This identity holds for TF and POINT. The first two numerator terms accumulate over $N$ observations and can be order $N$. The denominator's order alone does not make the movement order $P/N$.

For a deterministic one-path state, take $\alpha=1$, $\|\bar x\|^2=N$, $v_x=0.1$, $h=\bar h=0.2$, and $B^Hs=0.5N$. Then

$$
h^+-h=\frac{0.48N-0.2}{N+1}\longrightarrow0.48,
\qquad v_h^{\rm post}=\frac1{N+1}\longrightarrow0. \tag{T65}
$$

This example proves that small scalar variance does not logically force small gain-mean movement. It is not a prediction of the receiver's typical trajectory or a demonstration that mean motion dominates every other term.

## What the interventions establish

The most direct causal comparison is POINT versus FIXED-inner. Both suppress propagated variance, retain the gain pseudo-variance/shrinkage machinery as specified, retain the same outer geometry refits, and use the same decoder schedule. FIXED-inner holds the gain means fixed inside each batch. The large error differences in final Part A therefore support a role for the mean adaptation on those saved observations.

TF versus POINT changes the propagated scalar uncertainty and the resulting trajectory. The final Part-B subset shows only small, mixed differences in frame outcomes and similar latency. It does not establish a general reliability advantage from propagation, and it does not establish equivalence. The correct conclusion is to preserve the frozen primary and limit the mechanism claim.

The NO-FEEDBACK and NO-GEOMETRY interventions support retaining standard coded exchange and observed geometry updates in this implementation. They are scoped interventions on eight reused observations at one SNR. They do not identify a universal minimum pilot fraction or show that every data-aided receiver requires the same schedule.

# Posterior identifiability and limits of scalar uncertainty

## Exact known-waveform covariance

Assume the waveform $x$ and geometry are known, the gain prior is $\mathcal{CN}(0,I/P)$, and the physical observation is linear Gaussian:

$$
y=B(x)h+w.
$$

Completing the complex Gaussian square yields

$$
C_{h\mid x,y}=\left(PI+\sigma^{-2}B^HB\right)^{-1},
\qquad
m_{h\mid x,y}=C_{h\mid x,y}\sigma^{-2}B^Hy. \tag{T66}
$$

If

$$
\lambda_{\min}(B^HB/N)\ge\gamma>0,
$$

then

$$
\|C_{h\mid x,y}\|_2\le\frac1{P+N\gamma/\sigma^2}. \tag{T67}
$$

This is a genuine conditional posterior bound. Its hypothesis is excitation in every gain direction, not merely large total waveform energy. The scalar algorithm variance in (T57) contains only an aggregate pseudo-precision and cannot certify this eigenvalue condition.

## A complete counterexample

Take a valid zero-Doppler, unit-CPP-phase special case with $P=2$, $M_1=I$, and $M_2$ a nontrivial cyclic shift. Choose a constant time-domain waveform $x_T$ with $\|x_T\|^2=N$. Then $M_1x_T=M_2x_T=x_T$, so

$$
B_T=[x_T,x_T],\qquad
B_T^HB_T=N\begin{bmatrix}1&1\\1&1\end{bmatrix}. \tag{T68}
$$

The normalized gain-sum vector $(1,1)^T/\sqrt2$ has Gram eigenvalue $2N$, whereas the gain-difference vector $(1,-1)^T/\sqrt2$ has eigenvalue zero. Under prior covariance $I/2$, the exact posterior variances in these directions are

$$
\lambda_{\rm sum}=\frac1{2+2N/\sigma^2},
\qquad
\lambda_{\rm difference}=\frac12. \tag{T69}
$$

Increasing $N$ does not identify the difference of the two gains. Yet a scalar rule based on $\alpha=1/\sigma^2$ and waveform energy $N$ returns $1/(2+N/\sigma^2)$ and tends to zero. At $N=64$, $\sigma^2=0.2$, the exact unobserved-direction variance is $0.5$, the observed-direction variance is approximately $0.00155763$, and the scalar value is approximately $0.00310559$.

The path operators can be Frobenius-orthogonal while these particular waveform responses coincide. This is why the exact operator Gram $R$ and the conditional training Gram $B(x)^HB(x)$ answer different questions.

The construction is a conditional known-waveform counterexample. It does not assert that this constant waveform belongs to the evaluated code-and-pilot ensemble or occurs with significant probability there. It is sufficient to falsify the universal implication from scalar shrinkage or waveform energy alone to posterior concentration.

## Unknown codewords add another uncertainty layer

For a joint code/channel posterior,

$$
\operatorname{Cov}(h\mid y)
=\mathbb E_{d\mid y}[\operatorname{Cov}(h\mid d,y)]
+\operatorname{Cov}_{d\mid y}(\mathbb E[h\mid d,y]). \tag{T70}
$$

The second term represents disagreement among code-conditioned channel explanations. Even a small conditional covariance for each codeword need not imply a concentrated mixture. The current scalar receiver does not preserve every code-conditioned mode, and it does not claim that its scalar variance measures the complete covariance in (T70).

This does not invalidate the receiver as a computation-limited approximation. It defines the boundary of the interpretation: scalar gain-variance propagation is an algorithmic uncertainty device, not a certified physical confidence interval for every path.

# Complexity, storage, and implemented state

## Inner-loop arithmetic and storage

The following accounting refers to one fixed-geometry joint batch. It includes the actual operations required by the map, not just its forward model.

| Operation | Direct structured cost | State or qualification |
|---|---|---|
| Path phase/index preparation | $O(NP)$ | Full fractional phases and CPP; once per geometry |
| Physical Frobenius Gram $R$ | $O(P^2)$ | Retain repeated-delay terms |
| Current IDAFT | $O(N\log N)$ | One transform per inner iteration |
| Current response $B_T(x)$ | $O(NP)$ | $N\times P$ complex array |
| Prediction and gain adjoint | $O(NP)$ | No dense path tensor |
| Cached barred response | $O(NP)$ | Linear recurrence, no extra transform |
| Aggregate time adjoint | $O(NP)$ | Phase conjugation and reversed shifts |
| Return DAFT | $O(N\log N)$ | One transform per inner iteration |
| Channel scalar norm | Up to $O(P^2)$ | $h^HRh$; $O(P)$ for distinct delays |
| QPSK probabilities and moments | $O(4N)$ | Log-sum-exp and marginalization |
| Gain denoiser | $O(P)$ | Scalar pseudo-variance shared across gains |

Thus one iteration costs $O(NP+N\log N+P^2)$ and stores $O(NP+P^2)$ path/response state. The statement is exact about the implementation structure and asymptotic in operation count; it does not identify a hardware-independent constant.

A complex128 $P\times N\times N$ tensor at $N=1024,P=8$ occupies 128 MiB. One complex128 $N\times P$ response array occupies 128 KiB, or 0.125 MiB. The implementation has multiple arrays and its pilot initializer retains a larger dictionary. The two array sizes must never be quoted as the complete process-memory reduction.

## Complete cost and amortization boundaries

For coded rounds $r=1,2$,

$$
C_{\rm complete}=C_{\rm acquisition}
+\sum_{r=1}^{2}\left[C_{\rm refit}^{(r)}+20C_{\rm inner}^{(r)}+C_{\rm LDPC}^{(r)}\right]
+C_{\rm interface}. \tag{T71}
$$

The acquisition term includes the observed dictionary processing and least-squares work. The refit term includes every bounded scalar trial. A direct refit complexity bound is $O(N\log N+J(NP^2+P^3))$, where $J$ is the total number of objective evaluations, not the number of accepted changes. The decoder term uses the actual graph and executed sweeps; a cap does not mean every call necessarily executes the cap.

Fixed code/configuration construction can be amortized only when the same convention applies across all compared arms. Online observation transforms, model updates, copies, clipping, and checkpoint hooks are charged. A later failure does not erase earlier cost; only a completed decision may be used as fallback or deadline output. Offline truth scoring and bulk storage remain distinct categories in the retained measurement contract.

No claim is made that all setup is $O(NP)$, or that end-to-end memory has the inner-state order. The pilot dictionary has size $N\times Q$; $Q=515$ in the primary interface. In a different physical scaling law, $Q$ itself may change with block length, delay spread, or Doppler extent. That behavior must be documented rather than hidden behind a fixed-$Q$ experiment.

## Isolated process memory versus sampled visible arrays

Final Part A uses a fresh CPU process per arm, one warmup plus one measured call on the same audit observation. Its baseline is after imports, static context, and input loading. Total high-water includes warmup, measurement, and evidence instrumentation.

| Arm | Baseline RSS (KiB) | Process peak (KiB) | Visible NumPy subtotal (approx. MB) |
|---|---:|---:|---:|
| TF | 594,880 | 623,296 | 8.45 |
| EP2 | 594,868 | 623,524 | 8.45 |
| EP4 | 594,976 | 623,588 | 8.45 |
| PBi | 595,484 | 1,148,064 | 403.63 |

The visible subtotal is a deduplicated lower bound sampled at selected function returns. It omits hidden BLAS/native/Torch workspace and unsampled temporaries. Total high-water is not a sum of those sampled arrays. The result supports similar observed total peaks for TF and EP and a larger peak for the implemented dense PBi adaptation on this frame. It does not support a claim that TF has lower complete process memory than EP [E-A].

The earlier shared sequential-process peak cannot be substituted for these isolated probes. Instrumented memory-call latency is excluded from ordinary latency statistics. Memory repetitions do not increase the number of independent fading observations.

# Mathematics-to-code map and numerical contracts

## Archived anchors and final-source authority

The table below uses function anchors from the supplied archived implementation. E-A reports that the final remote source and equations were reconciled and that replay outputs matched. The archived files inspected for this edition are not asserted to be byte-identical to the final remote checkout. Source hashes and final line numbers must come from the retained final manifest.

| Mathematical object | Archived implementation anchor | Audit invariant |
|---|---|---|
| DAFT and inverse DAFT | `physical.py::daft` | Unitary normalization and positive chirps |
| Physical phases/indices/$R$ | `twofft.py::TimePathOps.__init__` | Full CPP, arbitrary real Doppler, repeated-delay Gram |
| $B_T(x)$ | `TimePathOps.responses_time` | Phase times shifted reads |
| $\sum h_i^*M_i^Hs$ | `TimePathOps.adjoint_time` | Reverse shift, conjugate phase/gain |
| $c(h)$ | `TimePathOps.power` | Real nonnegative Gram quadratic within tolerance |
| Damped scalar map | `twofft.py::scalar_joint` | Pre/post variance and barred/unbarred state timing |
| Physical refit | `twofft.py::time_refine` | Same frozen objective, bounded coordinate trials |
| Complete native rounds | `native_twofft.py::receive` | No I1 front-loop tax, two checkpoints, observed-only inputs |
| Pilot acquisition | `receiver.py::pilot_front` | Same observed initializer and actual dictionary cost |
| QPSK prior/marginals | `messages.py::alphabet`, `logprior`, `marginal`, `moments` | All-I-then-all-Q order, target-prior removal, power units |
| LDPC exchange | `decoder_messages` in upstream message support | APP minus actual clipped input; replace feedback |
| Structured EP | `structured_ep.py::ep_t`, `CyclicSolver` | Exact band Gaussian subsolve; declared domain projection |
| PBi family adaptation | `bilinear.py::pbigabp` | Observation cavities and candidate-dependent SP variance |
| SBL/GAMP acquisition reference | `offgrid.py::estimate`, `gamp` | Prior-variance convention and charged grid evolution |

The archived primary rejects extra observation keys beyond $y$, pilot, and noise in its observed-input dictionary. System/code configuration remains an explicit separate input. The path estimator receives observed coordinates and coefficients, not true delays or gains. The final empirical integrity claim relies on the retained source and recount contracts, not on the existence of this table alone.

## Concrete implementation details that matter

The primary's arithmetic is not uniformly one dtype throughout the complete pipeline. The archived pilot initializer converts dictionary/observation arrays through complex64 Torch inputs; the native path and scalar routines use NumPy complex arithmetic, normally complex128 in the reference. A claim of an entirely float64 receiver would therefore need verification against the final dtype manifest.

`scalar_joint` calculates the prediction from unbarred current gains and responses. It then updates residual/precision and barred means before the pseudo-observations. The stored scalar trace `data_variance` and `gain_variance` is post-update. A mechanism calculation requiring pre-update $u_t$ must align to the appropriate preceding state or use the extended audit arrays. Directly reading the old scalar column as pre-update would shift the mechanism by one iteration and misrepresent both startup resets.

The positive reciprocal floor is $10^{-12}$. The code checks finite gains, data means/variances, and residuals. Materially invalid path dimensions or nonfinite geometry are rejected. Such checks are numerical safeguards, not physical statistical guarantees. Inactive guards permit the exact rational identities stated earlier; active guards must be logged and interpreted as guarded numerical operations.

The gain prior remains $1/P$ each batch. The estimate returned by the refit is an initialization, not a nonzero prior mean. The code evaluates $\Gamma$ from CE moments without secretly changing the inner gain prior to match the refit regularizer. The mismatch of the two objective conventions is stated rather than silently “corrected,” because changing it would change the frozen receiver.

## Qualification incidents and why they are not receiver failures

E-A retains two initial harness defects: a residual comparison performed before AF/time alignment and a scoring wrapper that interpreted packed truth as unpacked bits. They were repaired in the qualification/scoring machinery, not used to alter numerical receiver settings. Original failed receipts remain in the provenance.

The completed numerical qualification passes six prescribed size/path fixtures. E1 saved-output recount covers 252 attempts and 504 checkpoints; new attribution covers 91 attempts and 182 checkpoints; isolated memory covers eight attempts and sixteen checkpoints. The mechanism recount covers 240 vector-derived rows and 1,920 scalar rows. These counts answer different audit questions and are not combined into a fictitious number of independent scientific replications [E-A].

Final Part B reports 9,696 successful attempts and 19,392 recounted checkpoints. The zero-failure result is empirical under the tested configuration. It is not an unconditional convergence proof or evidence that every structured AFDM initialization is safe.

# Comparator definitions and fair interpretation

## Structured EP2 and EP4

The primary EP controls are native coded/SP proper-complex adaptations, not the original authors' software. Each uses two coded rounds, with two or four EP sweeps per round. Their physical refit is mean-only. The stronger EP4 must remain in the comparison because it improves accuracy over EP2 in Part B.

For a fixed fitted physical channel, form the sparse time-domain matrix $G_T=\sum_i h_iM_i$ and the pilot-canceled observation $Y_d=A^H(y-Hp)$. Gaussian EP sites are represented by diagonal precisions $\lambda$ and natural means $\eta$. A Gaussian module solves

$$
Q_T=\sigma^{-2}G_T^HG_T+\operatorname{diag}(\lambda),
\qquad
m_T=Q_T^{-1}(\sigma^{-2}G_T^HY_d+\eta),
\qquad v_T=\operatorname{diag}(Q_T^{-1}). \tag{T72}
$$

The archived implementation computes these Gaussian means and inverse diagonals through a cyclic-band factorization with a Schur boundary partition. This subsolve is numerically exact for the supplied precision matrix; it is not a diagonal approximation to that solve.

The approximate cavity precision and mean are

$$
\rho=1/v_T-\lambda,
\qquad
v_c=1/\rho,
\qquad
m_c=v_c\odot(m_T/v_T-\eta). \tag{T73}
$$

After numerical positivity guards, the cavity mean is transformed to the AF domain. The covariance crossing is projected to its marginals; because the DAFT has constant entry magnitude, a diagonal time covariance gives uniform AF marginal variance equal to the average. The finite-alphabet/code factor is applied in AF coordinates. The updated mean is transformed back, a scalar variance projection is used in the archived implementation, and positive finite site updates are damped.

Thus EP also respects the location of the QPSK constraints. It must not be described as treating independent time-domain samples as QPSK. Its approximation lies in its Gaussian/site and domain-crossing covariance projections, not in an incorrect constellation domain.

The implemented cyclic-band cost depends on $b=\max l_i-\min l_i$. The reference uses a dense fallback when the bandwidth becomes large relative to $N$; that cost is charged. $O(Nb^2+b^3)$ describes the implemented solver structure, not a universal lower bound for all possible EP implementations.

## PBiGaBP-family coded/SP adaptation

The PBi reference uses eight bilinear iterations per round and two coded rounds, with a soft physical refit. It maintains observation-specific gain and symbol cavities and explicitly forms dense path coefficients in the archived reference. This is a richer approximation than the scalar TF map, not the same map before optimization.

The SP-specific candidate variance should not be ignored. For one observation and target data symbol $d_k=a$, let

$$
z_i(a)=U_{ik}(p_k+a)+\sum_{j\ne k}U_{ij}(p_j+\mu_j).
$$

Under the declared independent working gain/symbol marginals, the conditional observation mean is

$$
M(a)=\sum_i m_{h_i}z_i(a),
$$

and its variance is

$$
\begin{split}
S(a)=\sigma^2
&+\sum_{j\ne k}\left|\sum_i m_{h_i}U_{ij}\right|^2v_j\\
&+\sum_i v_{h_i}\left[|z_i(a)|^2+\sum_{j\ne k}|U_{ij}|^2v_j\right].
\end{split} \tag{T74}
$$

The Gaussianized target score is $-\log S(a)-|y-M(a)|^2/S(a)$. The known pilot and target symbol both enter $z_i(a)$, so $S(a)$ can depend on the candidate. The adaptation retains that dependence. These are exact first/second moments under its working independence assumptions, but the Gaussianized factor and cavity approximation are not exact joint inference.

The gain cavity excludes the target observation's precision/natural-mean contribution. Probability-mixture damping of gain beliefs includes the between-mean variance term, unlike the algorithmic barred-state damping of TF. Those are different algorithms and must not be forced into an alleged same-message equivalence.

The Part-B PBi subset is the first 32 observations per SNR, selected before outcomes. It is a meaningful expensive reference but not a full-population or universal family comparison. Its larger memory footprint and long runtime refer to this implementation. Nothing in the tensor-free theorem prevents future optimized PBiGaBP variants from changing that frontier.

## Off-grid SBL and GAMP: retained positioning, not a missing Part-B arm

The archived D-GESBL-family adaptation uses an evolved dictionary $A(\nu)$, Gaussian coefficient prior variances $\delta$, and a declared effective CE noise scalar. Its exact Gaussian-SBL backend is

$$
\Sigma=(A^HA/\nu_w+\operatorname{diag}(\delta^{-1}))^{-1},
\qquad
m=\Sigma A^Hy/\nu_w. \tag{T75}
$$

The GAMP backend approximates this inference with scalar/componentwise updates. With $\delta$ denoting a prior variance, the Gaussian denoiser is $\delta r/(\delta+v_r)$ and its variance is $\delta v_r/(\delta+v_r)$. Confusing prior variance with precision changes the method.

Grid evolution minimizes a frozen posterior residual objective including covariance, and exact dictionary columns are refreshed after accepted parameter changes. Decoder APPs provide new waveform moments; code priors replace rather than accumulate. General full $\Gamma$ coupling cannot be inserted into an independent scalar denoiser for free without an additional factor/augmented-observation formulation.

Those acquisition controls were tested and not selected in the predecessor study. Their earlier negative results constrain the research history but are not a new prospective Part-B comparison against the final TF receiver. The paper cites off-grid acquisition work as close prior art and does not claim that all GAMP or SBL alternatives have been ruled out.

## Internal controls

POINT suppresses the propagated scalar gain variance but retains gain-mean adaptation, pseudo-variance, shrinkage, refits, and coding. FIXED-inner suppresses within-batch gain movement in addition to propagated variance. NO-FEEDBACK retains both decoder calls while suppressing returned code information. NO-GEOMETRY retains observed acquired centers and gain adaptation rather than substituting oracle paths.

These definitions are the causal interpretation of the controls. They should be included beside result tables, not hidden in a filename. The small runtime differences among reused-observation controls are not a newly optimized receiver frontier, particularly when POINT combines older and newly executed batches.

# Final experimental contract and source reconciliation

## Part A: qualification and attribution only

Part A's 99 successful calls comprise three primary replays, twenty-four missing POINT controls, forty-eight FIXED-inner controls, eight NO-FEEDBACK, eight NO-GEOMETRY, and eight isolated-memory warmup/measured calls. The 48 reused observations are bound by the retained input manifest. There are zero new radio observations [E-A].

The kernel experiment has six size/path fixtures, seven interleaved timing repeats after parity qualification, and twenty iterations per kernel. It is not a cold-process test. The dense reference is run only at $N=256,P=8$. Its setup time and basis storage are reported separately rather than hidden in or omitted from an ambiguous end-to-end number.

The attribution design uses the first sixteen saved observations per SNR for TF/POINT/FIXED. NO-FEEDBACK and NO-GEOMETRY use the first eight at 6.5 dB. These predefined, reused sets support local mechanism attribution. They are not pooled into the final prospective FER.

## Part B: the final prospective allocation

Part B has 1,024 fresh independent observations at each of 6, 6.5, and 7 dB. Each observation is paired across TF, EP2, and EP4. POINT runs on the first 128 per cell and PBi on the first 32. Therefore

$$
3072\times3+3\times128+3\times32=9696\text{ attempts}. \tag{T76}
$$

Each method has two coded-round checkpoints, giving 19,392 checkpoints. This arithmetic is consistent with the supplied report; it does not create an extra experimental replicate. The report records zero numerical failures, missing decisions, and unknown scored bits. No retuning or scope extension occurred [E-B].

The primary code, geometry-acquisition, pilot fraction, and CPU configuration are frozen. Final results must not be described as universal superiority or as a comparison against every possible EP implementation. Their strength is that the selected concrete methods are compared prospectively, with complete online work and all three SNR cells retained.

## Timing and decision eligibility

A completed decoder output has a recorded ready timestamp. At a deadline, only outputs with timestamps at or before that deadline are eligible. If no output has completed, the frozen missing-decision rule applies; the eventual final decision cannot be credited retroactively. A later numerical failure does not remove an earlier completed output, and failed work is not erased from complete cost.

The earlier E1 EP2-median reference times are fixed before Part B. Final deadline comparisons do not use a retrospectively optimized deadline or the older development value $0.678048$ s. The compact Part-B summary reproduces fractions 1.0 and 0.6 of those references; the other three registered fractions remain in the retained CSV, not invented in this document.

Online receiver latency, process wall time, warmup, radio generation, offline truth scoring, storage, and transfer are different categories. The final elapsed 2 h 17 min 5 s is a campaign/process report, not the sum of median receiver times and not a latency sample. Benchmark intervals use paired moving-block resampling to retain serial dependence; independent frame statistics do not justify ignoring thermal/load dependence in elapsed times.

## Final source and evidence identities

The numerical source remains `2d130b4d` with baseline `31d5ec0d`. Part A records runner scoring repair `d1fd9d4f` and mechanism recount `2311922f`. Those are orchestration/audit identities, not new receiver settings. Three primary replays matched prior saved decoded bits, LLRs, and path values [E-A].

Part A reports 591 retained files, approximately 49.63 MiB, with heavy mechanism arrays remote and 145 returned compact files transfer-verified. Part B reports 45,021 files, 1,565,009,669 bytes, approximately 1.46 GiB, with eight analysis/recount files verified against its inventory. These inventory claims are reported provenance. The writing session does not claim to have downloaded or independently recounted every remote artifact.

The local drafting package preserves exact copies of the supplied principal records and their SHA-256 hashes. It also records arithmetic reconstruction of the paired upper bounds from reported counts. This is useful traceability, but is not a substitute for the remote per-frame recounts.

# Statistical interpretation of the final results

## Primary rates and paired outcomes

The final unrestricted information-frame counts are:

| SNR | TF errors/1,024 | EP2 errors/1,024 | EP4 errors/1,024 | TF FER | EP2 FER | EP4 FER |
|---:|---:|---:|---:|---:|---:|---:|
| 6.0 | 206 | 487 | 309 | 0.201172 | 0.475586 | 0.301758 |
| 6.5 | 43 | 140 | 74 | 0.041992 | 0.136719 | 0.072266 |
| 7.0 | 14 | 29 | 20 | 0.013672 | 0.028320 | 0.019531 |

Rates are derived only by dividing the supplied counts by 1,024. Their decimals are not additional measurements. The primary result concerns information-frame error: any incorrectly recovered information bit makes that frame an error. The final compact summary does not include the full primary BER totals, so a BER graph must come from the retained bit-count CSV rather than from these frame counts.

For each paired comparison, define $R$ as comparator-error/TF-correct and $H$ as TF-error/comparator-correct. The empirical excess risk is $(H-R)/n$. The paired identities can be checked directly against marginal counts; for example, at 6 dB against EP2, $283-2=487-206=281$.

| SNR | Comparator | Rescue / harm | Excess upper (pp) | Registered margin (pp) | Interpretation |
|---:|---|---:|---:|---:|---|
| 6.0 | EP2 | 283 / 2 | −23.094 | 2 | Upper is negative |
| 6.0 | EP4 | 112 / 9 | −6.538 | 2 | Upper is negative |
| 6.5 | EP2 | 98 / 1 | −6.554 | 2 | Upper is negative |
| 6.5 | EP4 | 32 / 1 | −1.129 | 2 | Upper is negative |
| 7.0 | EP2 | 17 / 2 | 0.131 | 1 | Tolerance, not superiority |
| 7.0 | EP4 | 9 / 3 | 0.793 | 1 | Tolerance, not superiority |

The bounds are a simultaneous one-sided 95% family for $\mathrm{FER}_{\rm TF}-\mathrm{FER}_{\rm comparator}$. At the first two SNRs, their negativity supports lower FER within the frozen ensemble. At 7 dB, they permit a small positive excess but stay below the practical tolerance. It would understate the evidence to call the first four comparisons merely promising development observations; it would overstate the evidence to call the last two superior or equivalent.

## Exact-binomial construction and coverage proof

Let $p_H$ and $p_R$ be the harm and rescue probabilities. For $m=6$ comparisons, use $\eta=0.05/(2m)=0.05/12$. The one-sided Clopper–Pearson components are

$$
U_H=\begin{cases}
1,&H=n,\\
\operatorname{Beta}^{-1}(1-\eta;H+1,n-H),&H<n,
\end{cases}
$$

$$
L_R=\begin{cases}
0,&R=0,\\
\operatorname{Beta}^{-1}(\eta;R,n-R+1),&R>0.
\end{cases} \tag{T77}
$$

Each upper/lower event fails with probability at most $\eta$. On their intersection, $p_H-p_R\le U_H-L_R$. A union bound over twelve events gives

$$
\Pr\{\Delta_j\le U_{H,j}-L_{R,j}\text{ for all }j=1,\ldots,6\}\ge0.95. \tag{T78}
$$

No independence among comparisons is needed. The comparisons share methods and may share structure, but the union bound remains valid. Within one paired cell, harm and rescue events are mutually exclusive; treating them as two independent binomials is unnecessary. The construction uses marginal exact coverage and is conservative.

Using the reported counts reproduces the six upper bounds as approximately −23.093502, −6.538481, −6.554463, −1.128516, 0.130676, and 0.793275 percentage points before display rounding. This independent arithmetic check is saved in the drafting package. It is not a new raw-array statistical analysis.

The lower bounds in the remote paired-count file form a separate coverage family. Combining an upper family and a lower family does not automatically yield joint two-sided 95% coverage. The manuscript therefore uses the registered upper family for its reliability claims and does not invent two-sided intervals by pairing separately calibrated endpoints.

## Superiority, noninferiority, equivalence, and zero counts

A noninferiority statement with margin $\delta$ asks whether $\Delta<\delta$. A superiority statement asks whether $\Delta<0$. If the same valid upper bound is negative, it supports both statements under the specified coverage. A positive bound below $\delta$ supports only the practical tolerance.

Equivalence would require both directions relative to explicitly chosen positive/negative margins, with appropriate simultaneous coverage. It is not implied by a confidence interval containing zero, equal observed frame counts, or zero paired harms. The final results are not described as equivalence.

The POINT and PBi subsets have their own smaller denominators and were not included in the primary six-bound family. A zero error count on 32 frames does not establish zero population error or an error floor. Likewise, a zero failure count among the 9,696 numerical attempts is a useful implementation observation, not a proof that arbitrary structured inputs converge.

Information bits within a frame cannot be counted as independent Bernoulli reliability samples. Their sum is a useful BER diagnostic, but frame-level pairing or resampling must be retained for uncertainty. The final primary FER denominators remain 1,024 per cell even though each frame contains 1,024 information bits and each method has forty inner iterations.

## Complete latency and moving-block uncertainty

The final pointwise 95% paired moving-block bootstrap intervals are retained verbatim below. The same serial block indices are used across paired methods by the reported procedure. The exact block length and replicate count are retained in the remote analysis manifest; they are not specified in the compact report and are not invented here.

| SNR | Method | Median [CI], s | p90 [CI], s | p95 [CI], s |
|---:|---|---|---|---|
| 6.0 | TF | .2882 [.2873,.2890] | .3071 [.3058,.3093] | .3130 [.3111,.3152] |
| 6.0 | EP2 | .5020 [.4967,.5097] | .6929 [.6845,.7004] | .7195 [.7102,.7258] |
| 6.0 | EP4 | .7310 [.7205,.7490] | 1.1237 [1.1049,1.1333] | 1.1751 [1.1612,1.1907] |
| 6.5 | TF | .2862 [.2852,.2869] | .3046 [.3026,.3080] | .3103 [.3085,.3127] |
| 6.5 | EP2 | .4947 [.4905,.4979] | .6802 [.6695,.6900] | .7171 [.7053,.7267] |
| 6.5 | EP4 | .7161 [.7102,.7223] | 1.1081 [1.0802,1.1223] | 1.1583 [1.1411,1.1877] |
| 7.0 | TF | .2842 [.2830,.2852] | .3043 [.3025,.3057] | .3097 [.3078,.3119] |
| 7.0 | EP2 | .4916 [.4870,.4976] | .6760 [.6629,.6871] | .7069 [.6933,.7223] |
| 7.0 | EP4 | .7132 [.7074,.7239] | 1.0836 [1.0595,1.1120] | 1.1531 [1.1323,1.1835] |

The reported TF/EP2 median-ratio upper bounds are .580/.583/.583. The reported p90 ratios are .443/.448/.450. TF median latency is 42.1–42.6% lower than EP2 and 60.0–60.6% lower than EP4. These quantities are complete online receiver measurements on the frozen CPU setting, not ratios of theoretical FLOP counts.

A ratio of medians and the median of per-frame ratios are different statistics. A confidence interval for one is not substituted for the other. Pointwise timing intervals are also not automatically a simultaneous family over all methods, SNRs, and quantiles. The primary reliability family and timing bootstrap answer different uncertainty questions.

Only quantiles are available in the supplied final text. A plotted smooth CDF reconstructed from those quantiles would invent a distribution. The drafts instead plot the given medians and tail quantiles with their reported intervals.

## Deadline errors

| SNR | Fraction of fixed E1 EP2-median deadline | TF /1,024 | EP2 /1,024 | EP4 /1,024 |
|---:|---:|---:|---:|---:|
| 6.0 | 1.0 | 206 | 649 | 897 |
| 6.5 | 1.0 | 43 | 336 | 596 |
| 7.0 | 1.0 | 14 | 168 | 358 |
| 6.0 | 0.6 | 214 | 955 | 1,024 |
| 6.5 | 0.6 | 44 | 696 | 1,024 |
| 7.0 | 0.6 | 14 | 496 | 1,024 |

The reference times are approximately 0.50 s; their 0.6 fractions are approximately 0.30 s. Exact per-cell thresholds should be taken from the frozen record, not rounded and used to rescore raw timestamps. All five registered fractions remain in the original CSV. The two displayed rows per cell are the subset reproduced by the supplied summary.

These results answer whether a useful completed decision exists by a common elapsed-time budget. They do not imply hard real-time guarantees, zero jitter, or energy efficiency. A method that eventually decodes correctly but has no completed result at the deadline cannot be credited with that future result.

## Mechanism and control tables after final reconciliation

Part A's reused-observation intervention is:

| SNR | TF FE /16 | POINT FE /16 | FIXED FE /16 | TF / POINT / FIXED information errors |
|---:|---:|---:|---:|---:|
| 6.0 | 2 | 3 | 16 | 155 / 214 / 1,734 |
| 6.5 | 1 | 1 | 13 | 97 / 122 / 1,294 |
| 7.0 | 0 | 0 | 6 | 0 / 0 / 435 |

Each cell has 16,384 information bits. FIXED-to-POINT rescues are 13/12/6 with zero harms; POINT-to-TF gives one rescue only at 6 dB. The large intervention effect supports within-batch mean adaptation on these saved states. The inference does not become a population confidence statement by counting all 49,152 bits as independent.

Part B's prospective POINT subset is:

| SNR | TF FE /128 | POINT FE /128 | TF rescue / harm |
|---:|---:|---:|---:|
| 6.0 | 21 | 20 | 2 / 3 |
| 6.5 | 8 | 9 | 1 / 0 |
| 7.0 | 2 | 3 | 1 / 0 |

There is no consistent large propagated-variance benefit. Similar latency removes a compelling simplification incentive, and the primary remains frozen TF. The subset does not establish equivalence of LLRs, BER, or future risks.

Part B's richer-inference subset is:

| SNR | TF FE /32 | PBi FE /32 |
|---:|---:|---:|
| 6.0 | 6 | 21 |
| 6.5 | 2 | 10 |
| 7.0 | 0 | 0 |

PBi median time is approximately 14.36 s versus TF's approximately 0.29 s. This is a limited predefined subset of a specific coded adaptation; no universal statement about all PBiGaBP software is supported.

## Final mechanism trace summary

The extended Part-A traces retain pre/post alignment, raw and damped variances, direct-term norms, and mean motion. For the predeclared vector-audit frame at each SNR, the late-window medians are:

| SNR | $Nv_h^{\rm post}$ | Output correction | Reaction / backprojection | TF motion | POINT motion |
|---:|---:|---:|---:|---:|---:|
| 6.0 | .710 | 1.204% | .824% | .735% | .233% |
| 6.5 | .640 | 1.178% | .767% | .830% | .357% |
| 7.0 | .567 | 1.185% | .756% | .576% | .419% |

Late means inner indices 5–19 in each round. The two rounds are pooled only for these descriptive within-frame medians. They are not independent-sample estimates of a scaling exponent. The first iteration of each round resets $u$ to .125; the extended startup correction range is 196–467%. Both round resets must remain visible in any trajectory plot.

The old scalar trace columns are post-update. The final extended reconstruction explicitly aligns the current $v_q$, precision, pre-update propagated variance, and post-update gain movement. Reproducing the exact scalar identity with the wrong iteration alignment would be meaningless even if a pooled curve looked plausible.

# Claim–evidence map

The following table is the current claim ledger. It is intended for manuscript editing and reviewer responses, not as a list of extra contributions.

| Claim | Supporting evidence | Status and boundary |
|---|---|---|
| The positive-convention full path is a unitary CPP phase-weighted delay between DAFT transforms | T4–T11; E-T translated consistently; E-A dense CPP parity | Exact under sampled-model assumptions |
| Fractional paths need not be truncated to evaluate the chosen map | T13–T19 and T38–T41 | Exact representation/computation; fitted geometry can still be wrong |
| Observation rotation preserves the scalar-map unknown-variable iterates | Lemma T-A; E-A four-FFT/dense qualification | Exact algorithm identity, not PBiGaBP equivalence or better conditioning |
| Inner work/state are $O(NP+N\log N+P^2)$ / $O(NP+P^2)$ | Operation decomposition and source anchors | Core bound only, not whole-process memory |
| TF has a useful complete latency–reliability operating point against EP2/EP4 | Final E-B counts, six upper bounds, timing/ratio intervals | Prospective supported result in frozen 6–7-dB configuration |
| FER is lower at 6 and 6.5 dB against both EP controls | Four negative simultaneous excess upper bounds | Supported within registered ensemble |
| Reliability at 7 dB meets the practical tolerance | Upper bounds .131/.793 pp below1 pp | Noninferiority criterion, not superiority/equivalence |
| Inner gain-mean adaptation matters in the tested implementation | E-A POINT–FIXED intervention on first16 saved frames/cell | Scoped causal intervention, not fresh population theorem |
| Coded feedback and geometry updates are useful | E-A NO-FEEDBACK/NO-GEOMETRY first8 at6.5dB | Scoped controls, not universal minimum requirements |
| Late scalar gain variance is conditionally small | T57–T60 and saved-state algebra | Algorithm-specific identity/conditional bound |
| Gain variance is negligible throughout | None; T61–T63 and startup traces contradict it | Unsupported and explicitly excluded |
| Propagated scalar gain variance independently improves reliability | E-B POINT comparison has small mixed differences | Not established |
| Mean motion need not vanish when scalar variance vanishes | T64–T65 | Exact identity and counterexample |
| Scalar variance is the true physical posterior covariance | T66–T70 contradict a universal interpretation | Unsupported |
| Two FFTs are the main explanation for complete speed | Same-map four-FFT control | Unsupported as a principal headline |
| TF uses less total process memory than EP | E-A peaks are nearly equal | Not supported |
| Current dense PBi adaptation has higher measured memory/latency | E-A isolated probe; E-B limited subset | Implementation- and scope-specific |
| All algorithms or hardware are dominated | No such evidence | Explicitly excluded |

A statement can be supported without being historically new. Unitarity, Gaussian conditioning, finite Fourier expansion, and expected-loss identities are mathematical infrastructure. The substantive paper claim is their exact computational specialization within the implemented native coded receiver and its measured operating point.

# Novelty boundary and reference positioning

## What the closest literature already owns

P-BiG-AMP already supplies scalar-variance parametric bilinear updates, approximate Onsager corrections, damping ideas, and structured parameterizations [3]. FFT-specialized coded joint reception for frequency-selective channels already exists [4], and FTN multicarrier bilinear reception is another close precedent [11]. No first-FFT, first-turbo, or new-general-AMP claim is defensible.

AFDM parametric bilinear Gaussian BP already exists [5]. Our scalar map does not preserve its observation-specific cavities. The speed comparison is between different approximations, not an exact compression of that algorithm. Structured dual-domain EP already respects AF-domain constellation constraints while exploiting time-domain Gaussian structure [6]; the comparator cannot be caricatured as a wrong-domain or deliberately dense method.

SP-AFDM iterative estimation [2], SP-OTFS message-passing estimation [9], coded SP feedback [8], and data-aided AFDM grid-evolution SBL/GAMP [10] establish broad combinations of pilots, coding, and data-aided channel refinement. The proposed receiver reuses those principles. The distinction is not an unprecedented arrangement of familiar module labels.

Bilinear UAMP and BAd-VAMP provide other inference designs [12], [13]. The observation-only rotation here preserves iterates and cannot be claimed to produce their robustness properties. POINT is a controlled deletion in this scalar map, not a faithful implementation of those alternatives.

## What is the defensible remaining contribution

The exact computation includes the full fractional/CPP path model, both unknown-variable adjoints, scalar norm terms with coherent repeated-delay handling, correct SP shifted priors, cached damping responses, and a native coded execution path. Omitting one of those pieces can leave a purported “FFT implementation” with unnecessary per-path transforms, a dense tensor, a wrong variable prior, or an incompletely specified message map.

The contribution is therefore a concrete application-specific computational and receiver specialization. Its publication value is supported by final complete-cost evidence, not by asserting that every constituent identity was historically absent. The competent four-FFT realization largely shares the same tensor-free opportunity; its modest extra cost is part of the implementation qualification rather than the main scientific story.

The exact observation-equivariance proposition is particularly useful for separating computation from inference. It proves why the domain change may simplify execution but may not explain a new FER curve within the same map. This prevents assigning the complete receiver's performance to a mathematically impossible conditioning effect of an invariant transformation.

## Adverse literature and unresolved access boundaries

The OTFS bilinear comparison [7] reports important finite-structure limitations of PBiGAMP. Our useful initialized coded-SP regime does not refute that evidence. The fixed damping and finite schedule remain empirical choices, and the present derivations supply no state evolution for arbitrary AFDM channels.

The primary records for FTN multicarrier bilinear reception and the EURECOM time-domain AFDM work establish close overlap, but their full manuscripts were not fully retrieved in the documented project audit. This edition does not claim equation-level historical non-equivalence to inaccessible text. The public records checked while preparing the drafts update bibliography status only where supported; for example, the D-GESBL author record states TCOM acceptance, while the dual-domain EP record is an arXiv/workshop record rather than a presumed journal publication.

A novelty statement should therefore be framed around what was constructed, proved relative to its map, and measured. “To our knowledge, no paper has exactly these names” is not an adequate substitute for that substance.

# Supporting theory retained from earlier work

This chapter preserves mathematics that remains useful for model checking and reviewer questions. None of the constructions below is an additional current receiver module. Their evidence comes from the cited theory/design records, and their older small-system numerical witnesses are not pooled into Part B.

## Fractional leakage need not Gaussianize QPSK interference

Assume independent proper QPSK symbols $d_n$ with energy $P_d$ and $z=\sum_n a_nd_n$. Expanding the fourth moment, independence and zero means leave only pairings. Properness removes terms containing $\mathbb E[d_n^2]$, while constant modulus gives $\mathbb E|d_n|^4=P_d^2$ instead of the Gaussian value $2P_d^2$. Therefore

$$
\mathbb E|z|^4-2(\mathbb E|z|^2)^2
=-P_d^2\sum_n|a_n|^4. \tag{T79}
$$

The normalized fourth cumulant is

$$
-\frac{\sum_n|a_n|^4}{(\sum_n|a_n|^2)^2}
=-\frac1{M_{\rm eff}},
\qquad
M_{\rm eff}=\frac{(\sum|a_n|^2)^2}{\sum|a_n|^4}. \tag{T80}
$$

It is the effective mixing count, not the array length alone, that controls this diagnostic. For the coefficients $c_q(\nu)$ in (T13), one can calculate that diagnostic exactly. Let $z_n=e^{j2\pi\nu n/N}$ and form its normalized circular autocorrelation. At lag $r$, its magnitude squared is

$$
|r_z[r]|^2=1-4\sin^2(\pi\nu)\frac{r(N-r)}{N^2}.
$$

Parseval for the autocorrelation spectrum gives

$$
\sum_q|c_q(\nu)|^4=\frac1N\sum_r|r_z[r]|^2.
$$

Since $\sum_{r=0}^{N-1}r(N-r)=N(N^2-1)/6$, writing $\nu=k+\delta$ yields

$$
\boxed{\sum_q|c_q(\nu)|^4
=1-\frac23(1-N^{-2})\sin^2(\pi\delta).} \tag{T81}
$$

At half-bin offset and large $N$, $M_{\rm eff}\to3$ and the normalized cumulant tends to $-1/3$, not zero. At integer Doppler, one coefficient remains. Thus the blanket argument “large $N$ makes fractional-path QPSK interference Gaussian” is false. More diffuse multipath or strong thermal noise may improve a particular approximation, but needs its own argument.

Adding independent Gaussian noise leaves the fourth cumulant numerator unchanged while increasing the variance denominator. An invertible unitary transformation cannot turn an exactly discrete joint law into an exactly Gaussian joint law. These qualifications support the current paper's explicit scalar-approximation language; they do not forbid an empirically useful Gaussian-message algorithm.

## Truncation creates coherent mean error and dependent residuals

Let $H=H_R+H_T$. The omitted response is $H_Tp+H_Td$. For isotropic zero-mean data,

$$
\operatorname{Cov}(H_Rd,H_Td)=P_dH_RH_T^H. \tag{T82}
$$

Frobenius orthogonality $\operatorname{tr}(H_R^HH_T)=0$ is only one scalar condition and does not force the matrix product in (T82) to vanish. Treating the tail as independent white noise is a receiver approximation, not a consequence of retaining the largest integer coefficients.

The older exact-decoding toy experiment makes another caution concrete. It used a fixed $N=8$ fractional path, a sixteen-word repetition codebook, and exact codeword likelihood comparison. For the same 40,000 message/noise draws, a matching truncated generator was optimistic for retention sizes 1, 2, and 3, but pessimistic for retention size 5. The full-channel endpoint agreed [E-T, Sec. 11.2]. A matching truncated simulation is therefore neither a universal upper nor a universal lower bound for full propagation. The toy has no direct LDPC/production performance interpretation.

## Posterior noise energy and same-observation dependence

For known $H$ and exact posterior data moments, let

$$
\mu(y)=\mathbb E[d\mid y],\qquad V(y)=\operatorname{Cov}(d\mid y).
$$

Since $w=y-H(p+d)$,

$$
\mathbb E[w\mid y]=y-H(p+\mu(y)),
\qquad
\operatorname{Cov}(w\mid y)=HV(y)H^H.
$$

The law of total variance and zero noise mean give

$$
\boxed{N\sigma^2
=\mathbb E\|y-H(p+\mu(y))\|^2
+\mathbb E\operatorname{tr}(HV(y)H^H).} \tag{T83}
$$

A same-observation posterior-mean residual can therefore have average energy below the thermal-noise energy without a factor-of-two mistake. Equation (T83) is an expectation over observations, not a per-frame equality. Unknown-channel fitting and approximate moments require additional qualifications. Data and noise are dependent after conditioning on $y$, so adding their posterior covariances as if they were independent can be wrong.

## Proper and improper scalar Gaussian approximations

For a zero-mean complex variable $e$, define variance $v=\mathbb E|e|^2$ and pseudo-variance $\zeta=\mathbb E[e^2]$. Writing $e=e_R+je_I$ gives

$$
\operatorname{Cov}\begin{pmatrix}e_R\\e_I\end{pmatrix}
=\frac12\begin{bmatrix}
v+\Re\zeta&\Im\zeta\\
\Im\zeta&v-\Re\zeta
\end{bmatrix}. \tag{T84}
$$

A nonsingular complex Gaussian approximation requires $v>|\zeta|$. Inverting the real covariance gives, up to a normalization constant,

$$
\log p(e)
=-\frac{v|e|^2-\Re(\zeta^*e^2)}{v^2-|\zeta|^2}. \tag{T85}
$$

For independent errors passed through scalar coefficients $a_k$, their variances add as $\sum|a_k|^2v_k$ and pseudo-variances as $\sum a_k^2\zeta_k$. Dividing a complex pseudo-observation by $h$ divides variance by $|h|^2$ and pseudo-variance by $h^2$.

This is standard noncircular processing, not a new current contribution [17]. The frozen TF denoiser uses a proper scalar Gaussian pseudo-channel. Its finite QPSK moments may still be improper. The earlier noncircular extension did not earn a mandatory primary role; its existence does not change the evaluated algorithm.

## Pilot-sensitive model mismatch and risk transfer

Let $H$ and $G$ be fixed alternative channel operators, with common message prior, pilot, and thermal variance. Put $\Delta H=H-G$, data prior mean $\mu_0$, covariance $V_0$, and

$$
R_x=V_0+(p+\mu_0)(p+\mu_0)^H.
$$

Then

$$
\mathcal J_H(G)
=\mathbb E\|\Delta H(p+d)\|^2
=\|\Delta H(p+\mu_0)\|^2+
\operatorname{tr}(\Delta HV_0\Delta H^H). \tag{T86}
$$

For zero-mean isotropic data this is $\|\Delta Hp\|^2+P_d\|\Delta H\|_F^2$, not generally a scalar multiple of channel NMSE. The fixed pilot contributes a directional term.

For the joint message/observation laws $P_H$ and $P_G$, the conditional observations are equal-covariance proper Gaussians. Their mean difference for each message is $\Delta H(p+d)$, so averaging the Gaussian divergence gives

$$
D_{\rm KL}(P_H\|P_G)=\mathcal J_H(G)/\sigma^2. \tag{T87}
$$

Pinsker's inequality then yields, for one fixed receiver map used under both propagation laws,

$$
|R_H(\mathcal A)-R_G(\mathcal A)|
\le\min\left\{1,\sqrt{\frac{\mathcal J_H(G)}{2\sigma^2}}\right\}. \tag{T88}
$$

For exact Bayes decisions $\delta_H^*$ and $\delta_G^*$ under the respective fixed models,

$$
0\le R_H(\delta_G^*)-R_H(\delta_H^*)
\le\min\left\{1,\sqrt{\frac{2\mathcal J_H(G)}{\sigma^2}}\right\}. \tag{T89}
$$

To obtain the second inequality, insert and subtract the two risks under $G$. The difference involving $\delta_G^*$ under its own model is nonpositive, and each remaining transfer difference is bounded by total variation.

The fixed-model assumption is critical. Substituting $G(y)$ learned from the same observation into a Gaussian generative model and then applying (T87) as though its mean were exogenous is invalid without a separate conditional argument. The bounds can also be vacuous and do not establish monotone FER improvement when $\mathcal J$ decreases. They are useful representation diagnostics, not performance certificates for approximate BP or TF.

## Weighted projection and why NMSE can disagree with detection

For a fixed subspace spanned by $U_i$, minimizing $\mathcal J_H(G)$ over $G=\sum_i g_iU_i$ gives

$$
[M_R]_{ij}=\operatorname{tr}(U_i^HU_jR_x),
\qquad
[b_R]_i=\operatorname{tr}(U_i^HHR_x),
\qquad M_Rg=b_R. \tag{T90}
$$

This projection uses the true $H$ and is a diagnostic, not a deployable estimator. With $H=\operatorname{diag}(1,3)$, $G=gI$, $p=(2,0)^T$, and $V_0=0.5I$, the Frobenius-optimal $g=2$ has squared Frobenius error 2 and observation error 5. The SP-weighted optimum $g=1.2$ has squared Frobenius error 3.28 but observation error 1.8 [E-T].

A better NMSE can therefore fail to minimize even the expected observation mismatch, much less the finite-iteration coded error rate. This mathematical distinction is consistent with the stopped predecessor campaign, where a more accurate channel fit was too expensive relative to a stronger native detector. It does not imply that channel accuracy is irrelevant.

## Projected support evidence and the OMP/OLS distinction

For a deliberately simplified fixed-covariance experiment,

$$
y=\Phi_{\mathcal S}a+\phi_jh+\eta,
\qquad \eta\sim\mathcal{CN}(0,C),\quad C=LL^H\succ0,
$$

hold the current support and covariance fixed. Let $Z$ have orthonormal columns spanning the orthogonal complement of $L^{-1}\Phi_{\mathcal S}$, and define

$$
z=Z^HL^{-1}y,\qquad v_j=Z^HL^{-1}\phi_j.
$$

The reduced model is $z=v_jh+\xi$ with identity covariance. For $v_j\ne0$, least squares gives $\hat h=v_j^Hz/(v_j^Hv_j)$ and the exact residual reduction is

$$
T_j=\frac{|v_j^Hz|^2}{v_j^Hv_j}. \tag{T91}
$$

If $h\sim\mathcal{CN}(0,\tau_j^2)$ instead, the determinant lemma and rank-one inverse identity give

$$
\log B_j=\frac{b_j}{1+b_j}T_j-\log(1+b_j),
\qquad b_j=\tau_j^2v_j^Hv_j. \tag{T92}
$$

Adding prior existence log odds gives posterior odds for this projected experiment. A full prior treatment of the already-present coefficients requires its own integration; it is not supplied by projection alone. A zero projected candidate adds no identifiable direction and cannot receive a finite normalized score by dividing by zero.

For white noise, the residual reduction normalizes the candidate after projection. That is an OLS-type quantity, not ordinary OMP correlation. With existing support $e_1$, residual $e_2$, and unit columns $a_1=\sqrt{0.99}e_1+0.1e_2$, $a_2=0.8e_2+0.6e_3$, OMP energies are .01 and .64, selecting $a_2$; exact refitted reductions are 1 and .64, selecting $a_1$. Ranking equivalence requires equal projected norms and, for the Bayes score, the corresponding prior/scale conditions [16].

If the covariance is fitted from the same observation or changes when a path is added, (T91)–(T92) become frozen-model surrogate scores rather than the exact physical SP likelihood ratio. This corrects older blanket equivalences and is why whitening is retained here as supporting detection theory, not the current main contribution.

## Selection and calibration

For a preselected candidate under the identity-covariance complex Gaussian null, $T_j$ is exponential with mean one. For $M$ independent candidate statistics,

$$
\Pr\{\max_jT_j>\gamma\}=1-(1-e^{-\gamma})^M. \tag{T93}
$$

A nominal 5% single-test threshold gives about 33.66% maximum-selection probability at $M=8$. Real dictionaries induce dependence, but that does not justify applying a preselected single-test calibration to a selected maximum. Likewise, a plug-in covariance fitted from the same frame is not independent secondary training data for a classical adaptive detector.

## Exact support add/drop formulas for a fixed quadratic

Preserve one global coordinate system and objective

$$
J(g)=c_0-2\Re(g^Hb)+g^HMg,
\quad M=\Phi^H\Phi+\Gamma+\lambda I,
\quad b=\Phi^Hy+\lambda g_0,
\quad c_0=\|y\|^2+\lambda\|g_0\|^2. \tag{T94}
$$

For support $\mathcal S$ with positive-definite principal block,

$$
J_{\mathcal S}^*=c_0-b_{\mathcal S}^HM_{\mathcal S\mathcal S}^{-1}b_{\mathcal S}.
$$

For a new coordinate $j$, let $a=M_{\mathcal Sj}$,

$$
s_j=M_{jj}-a^HM_{\mathcal S\mathcal S}^{-1}a,
\qquad t_j=b_j-a^H\hat g_{\mathcal S}.
$$

Eliminating existing coordinates leaves a scalar quadratic with curvature $s_j>0$ and linear term $t_j$, so

$$
J_{\mathcal S}^*-J_{\mathcal S\cup j}^*=|t_j|^2/s_j. \tag{T95}
$$

On an augmented support $\mathcal E$, forcing coordinate $i$ to zero and refitting increases the optimum by

$$
J_{\mathcal E\setminus i}^*-J_{\mathcal E}^*
=\frac{|\hat g_{\mathcal E,i}|^2}{(M_{\mathcal E\mathcal E}^{-1})_{ii}}. \tag{T96}
$$

This follows either by a scalar Schur complement or the constrained quadratic's Lagrange multiplier. Cholesky updates and solves should implement it; the inverse notation expresses the identity. A removed coordinate's old regularization constant must remain in the global objective. Omitting $\lambda|g_{0,i}|^2$ can reward a drop for an accounting error.

Frozen-quadratic descent does not prove coded FER descent or global likelihood ascent. These formulas remain mathematical assets but are not an online stage in TF.

## An algebraically inactive self-generated constraint

If $\hat g_{\rm LS}$ minimizes $\|y-\Phi g\|^2$ and a constructed projector $P_W$ satisfies $P_W\hat g_{\rm LS}=\hat g_{\rm LS}$, then

$$
\|y-\Phi g\|^2+\lambda\|(I-P_W)g\|^2
$$

has $\hat g_{\rm LS}$ as a minimizer for every $\lambda\ge0$. The first term is already minimal there and the second is zero. A hard restriction to the projector's range attains the same minimum because it contains that solution. Uniqueness needs appropriate rank conditions.

This is the corrected explanation for one earlier null construction. It does not establish general equivalence between soft regularization and a physically meaningful hard parameterization. A regularizer constructed from a solution so that it vanishes at that solution may add no new information.

# Retained finite-list and consumer-statistic theory

## Why these results remain in the master but not the receiver

The earlier V4 work investigated certified evaluation of a declared codeword bank. Its useful distinctions remain: hard decisions, posterior sums, conditional channel means, and CE normal-equation statistics are different outputs. Its architecture was not retained because candidate acquisition and complete cost, rather than only evaluation, were decisive. No codeword list is present in the final native method.

The following mathematics is kept as a reference for posterior diagnostics and reviewer questions. It is not a competing contribution in the manuscript.

## Gaussian marginalization conditional on a complete codeword

For a complete candidate $d$, let $\Phi_d=[U_i(p+d)]_i$, gain prior $h\sim\mathcal{CN}(0,C_h)$, and positive noise variance. Define

$$
Q_d=C_h^{-1}+\sigma^{-2}\Phi_d^H\Phi_d,
\qquad b_d=\sigma^{-2}\Phi_d^Hy.
$$

Completing the square gives

$$
h\mid d,y\sim\mathcal{CN}(Q_d^{-1}b_d,Q_d^{-1}), \tag{T97}
$$

and, up to codeword-independent constants, the negative marginal cost is

$$
F(d)=\frac{\|y\|^2}{\sigma^2}-b_d^HQ_d^{-1}b_d
+\log\det Q_d+\log\det C_h. \tag{T98}
$$

The determinant term arises from integration. Maximizing over the gain instead gives a regularized profile criterion without the determinant. The two are not different implementations of the same score. The current physical refit uses the profile expected-loss calculation, not the former list-marginalization objective.

## Prefix costs and the limit of a finite-bank certificate

For a linear Gaussian model with row $f_t$, posterior gain mean $m_{t-1}$ and covariance $V_{t-1}$, let

$$
q_t=\sigma^2+f_tV_{t-1}f_t^H,\qquad
e_t=y_t-f_tm_{t-1}.
$$

The normalized negative predictive increment is

$$
\Delta F_t=|e_t|^2/q_t+\log(q_t/\sigma^2)\ge0. \tag{T99}
$$

The inequality follows from $V_{t-1}\succeq0$. Gaussian conditional updates make the sum equal the complete marginal cost on the processed rows. The normalization is essential: $\log q_t$ alone need not be nonnegative when variance units are below one.

A stopped candidate's partial cost therefore upper-bounds its remaining probability weight. If completed bank weight is $Z_K$ and the sum of stopped upper weights is $U_P$, its conditional bank mass can be bounded by $U_P/(Z_K+U_P)$. This controls evaluation error **inside the bank**. If probability $\eta$ is outside the generated bank and conditional bank mass $\delta$ is discarded, the full discarded mass is

$$
\eta+(1-\eta)\delta. \tag{T100}
$$

No evaluator can certify the unknown outside-bank mass by merely calculating its existing words more accurately. Hard-MAP preservation also does not bound discarded probability sums: many nonwinning candidates may collectively matter to a soft consumer.

## Posterior fidelity and CE optimizer fidelity are different

For a frozen distribution $q$, define $K_d=\Phi_d^H\Phi_d$, $b_d=\Phi_d^Hy$, and

$$
g_q=(\mathbb E_qK_d+\lambda I)^{-1}(\mathbb E_qb_d+\lambda g_0).
$$

For another distribution $P$, let $A_P=\mathbb E_PK_d+\lambda I$ and

$$
r_d(g)=K_dg-b_d+\lambda(g-g_0).
$$

Then subtracting the normal equation under $P$ gives

$$
\boxed{g_q-g_P=A_P^{-1}\mathbb E_P r_d(g_q).} \tag{T101}
$$

Completing the quadratic square gives the exact excess expected loss

$$
J_P(g_q)-J_P(g_P)
=\bar r^HA_P^{-1}\bar r,
\qquad \bar r=\mathbb E_Pr_d(g_q). \tag{T102}
$$

Thus a large distributional error can cancel in the estimating equation and leave one CE optimizer unchanged. Conversely, a preserved MAP word does not preserve the mean/covariance pair used by CE. A singleton conditional distribution has zero covariance even if its word is the complete posterior's maximizer.

A finite coreset of at most $2P+1$ words can preserve one known complex $P$-dimensional optimizer: express the zero mean of the real/imaginary parts of $r_d(g_P)$ as a convex combination and apply Carathéodory's theorem. This is an existence/compression result after the necessary statistics are acquired. It does not supply an inexpensive algorithm for discovering the posterior or the optimizer in the first place. That acquisition limitation was central to the earlier negative list results.

## Joint code–channel statistics cannot be replaced by separate means

A code-conditioned Gaussian mixture has

$$
\mathbb E[H(h)(p+d)\mid y]
=\sum_d w_d\Phi_dm_d.
$$

In general,

$$
\sum_d w_d\Phi_dm_d\ne\Phi_{\bar d}\bar h.
$$

The difference is a code–channel cross-moment. Opposing code/gain hypotheses can have canceling separate means while their joint predicted signals reinforce. This limits an interpretation of a posterior gain mean as a universally sufficient input to a subsequent bilinear stage.

The current scalar receiver does not explicitly preserve all such modes. Its usefulness is empirically evaluated, not inferred from a claim that separate scalar means and variances encode the complete mixture. This retained fact is a limitation and a source of future questions, not a reason to add a large list back into the present method.

# Negative results and corrected interpretations

## The predecessor campaign remains stopped

The full-physical/sparse-inference predecessor was evaluated with a registered continuation rule and did not pass. In its independent Stage 2, two additional correct frames at 6 dB and one at 8 dB relative to native EP cost about 2.27 and 2.47 times as much. Better channel NMSE did not supply an adequate complete-cost communication advantage. That failed allocation decision is not erased by the later native receiver's success.

The native method is a different architecture: it removes the I1 pre-loop and changes the inner inference representation. Its Part-B success must not be described as retroactive validation of the predecessor's graph-selection or weak-edge covariance modules. Those modules are absent from the final primary [E-N and retained predecessor report].

## Full Gamma, richer covariance, and extra transforms

Earlier matched scalar/full Gamma screens gave nearly identical outcomes and very small off-diagonal ratios in their tested setting. The final paper therefore does not claim an off-diagonal-Gamma FER mechanism. Full Gamma remains a well-defined, inexpensive refit calculation.

The native exploration implemented vector-variance and gain-covariance-block variants without a decisive screen improvement. Dynamic tangent relinearization could harm observations. These variants remain negative evidence, not hidden optional rescue modes in TF.

An initially inefficient per-path-transform reference made the two-FFT implementation look unusually favorable. A competent four-FFT version evaluates the same map much more efficiently. Final Part A retains that stronger comparator. The modest two/four difference is not the explanation for the complete latency advantage against EP.

## Earlier I1 and truth interventions

I1's historical improvement was real in its tested development conditions, but did not establish a new turbo principle. The archived mechanism has persistent code-informed detector priors and CE effects, not just terminal decoding. Its default mean-only CE also means the improvement cannot be assigned to an unimplemented $\Gamma$ penalty.

A one-time true-symbol CE intervention is not a universal oracle for every receiver schedule. It cannot underperform because the supplied true hard symbols contain decision errors. Differences must be explained by scheduling, interfaces, which modules receive truth, and what other quantities change. The later theory chapter corrects the overbroad earlier explanation.

## The four-channel-use factorial sign correction

An earlier summary used counts $(37,7,3,0)$ out of 256 for estimated/estimated, true cancellation only, true data channel only, and both true. The raw additive risk interaction is

$$
0-7/256-3/256+37/256=27/256.
$$

But the extra joint risk reduction beyond the sum of individual reductions is

$$
(37-0)/256-[(37-7)+(37-3)]/256=-27/256. \tag{T103}
$$

The improvements overlap and are subadditive on this scale, not positively superadditive. The interventions still show that both channel uses matter. A different transformed risk scale would define a different interaction and must be stated explicitly.

## What null results do not prove

A null improvement from one BP iteration extension does not establish that every stronger detector is irrelevant. A confidence interval containing zero does not establish equivalence. A small whitening gain or an ineffective covariance proxy does not prove that all statistical whitening is impossible. A higher-NMSE channel producing better FER under one approximate detector does not violate a Frobenius projection theorem.

Historical G0 matched/truncated-generator results, full-G1 results, development-selected observations, reused Part-A frames, and fresh Part-B observations are separate evidence classes. Their numerical counts cannot be pooled just because the project name or block length matches. The final manuscript uses Part B for its primary performance and retains earlier results only for their stated diagnostic roles.

# Claims for writing and reviewer responses

## Supported wording

The following formulations are supported by the current combined record:

“An exact full-path implementation evaluates the declared damped scalar bilinear map without explicitly forming the path tensor or truncating included fractional paths.”

“In the frozen prospective 6–7-dB experiment, TF meets all six simultaneous one-sided reliability tolerances against the two local structured-EP configurations and has substantially lower complete median and tail latency.”

“At 6 and 6.5 dB, the simultaneous excess-FER upper bounds are negative against both EP controls. At 7 dB, the inference is the registered tolerance statement, not superiority.”

“Controlled reused-observation interventions support within-batch gain-mean adaptation, coded feedback, and geometry updates. The prospective POINT subset does not establish a general incremental reliability advantage from propagated scalar gain variance.”

“Late scalar gain-variance corrections are consistent with a conditional fixed-$P$ scaling argument at the measured operating point; startup corrections are not uniformly small.”

These claims are strong enough for the paper without declaring every constituent formula new.

## Unsupported wording and the exact reason

| Tempting statement | Why it is not supported |
|---|---|
| “TF is an exact Bayesian receiver.” | Scalar beliefs/reactions and plug-in geometry are approximate. |
| “Rotation improves AMP convergence.” | The proved map has identical iterates before/after rotation. |
| “Two FFTs explain the entire 42–61% latency gain.” | Complete receiver comparison changes inference computations; competent four-FFT control is close. |
| “The algorithm is globally convergent.” | No deterministic structured-AMP or whole-pipeline convergence theorem is supplied. |
| “Small gain variance proves physical certainty.” | Conditional response rank can remain deficient; T66–T70 provide a counterexample. |
| “POINT is equivalent to TF.” | Small mixed frame differences and similar timing do not establish distribution/message equivalence. |
| “Full variance propagation causes the reliability gain.” | Prospective POINT results do not establish that effect. |
| “TF uses less total memory than EP.” | Final isolated process peaks are nearly equal. |
| “All EP or PBiGaBP implementations are slower/worse.” | Only declared local adaptations and hardware were tested. |
| “The main result holds for arbitrary pilot power/code/path resolution.” | No final scope-extension evidence is supplied. |
| “A zero numerical-failure count proves stability for all channels.” | It is an empirical count in one frozen ensemble. |
| “The final study shows a $10^{-4}$ error floor.” | The observed FERs and sample sizes do not resolve that regime. |

## How to answer the central novelty objection

A reviewer may correctly observe that scalar P-BiG-AMP, FFT parameterizations, and coded feedback predate the work. The response should agree and identify the actual contribution: the full AFDM/SP path-specific implementation of all scalar contractions, correct variable-domain treatment and damping cache, native coded integration with observed geometry, and a prospective complete-cost operating advantage.

A reviewer may also ask whether a simpler point-gain receiver explains the method. The answer is the recorded POINT/FIXED/TF evidence: point gain adaptation captures much of the behavior, and propagated variance has no general independent benefit established here. The paper does not rely on a stronger variance story. The primary remains the frozen validated algorithm, and the simplified control is reported rather than renamed as a new method after confirmation.

Finally, a reviewer can fairly demand complete configuration details. The correct response is to provide the retained manifests and local adaptation map, not to infer missing final values from memory. The missing-field table below makes that release work explicit.

# Technical release checklist and unresolved record fields

| Field | What is known from supplied evidence | Required archival completion |
|---|---|---|
| Primary and baseline source | `2d130b4d` / `31d5ec0d` | Final source manifest and complete file hashes |
| Main numerical schedule | Two coded rounds, twenty inner iterations, damping .3, LDPC cap50 | Per-module final defaults and guard placement from final map |
| Power and code | N1024, nominalP8, QPSK, LDPC2048/1024, rho.5 | Actual generator/parity matrices, information map, pilot identifier |
| Physical transform | Positive DAFT/CPP definitions fixed | Final numerical $c_1,c_2$ and prefix length |
| Propagation ensemble | Full fractional paths; inherited frozen law | Exact delay/Doppler/gain sampling and normalization fields |
| SNR | Frozen 6/6.5/7-dB labels | Exact conversion to complex noise variance, without reinterpreting as Eb/N0 |
| Hardware/runtime | Same frozen CPU implementation and reported complete seconds | CPU model, OS, BLAS/Torch/library versions, thread/affinity settings |
| Reliability statistics | Six simultaneous exact one-sided upper bounds and margins | Final analysis source and allocation lock |
| Timing statistics | Paired moving-block bootstrap intervals | Block length, bootstrap count/seed, run order, exact ratio convention |
| Deadline curve | Two supplied fractions of fixed E1 references | All five fractions and exact per-cell reference seconds |
| Stage cost and final BER/NMSE | Referenced remotely, not tabulated in compact report | Transcribe retained CSVs; do not fabricate from FER |
| Full traces | Recounted and remotely retained | Exact diagnostic definitions and selected raw states for plotting |
| Release metadata | Internal filenames and inventories available | Author list/affiliations, public artifact identifier, licenses |

Completing this table is documentation and artifact preparation, not an implicit authorization for more simulation. The final Part-B statistical contract is already complete and passed. Changes to the numerical method after that point require a new version and cannot inherit the same confirmation claim without an explicit equivalence argument or new evidence.

# Evidence-supported summary

The present project has a complete scoped scientific story. A compact full fractional-path model enables a tensor-free evaluation of a declared scalar bilinear inference map. The native receiver uses that map to update gains and coded data together after observed acquisition and within a documented two-round information flow. Exact identities establish the computation and clarify its scalar uncertainty mechanism; they do not promise exact posterior inference. Final Part A qualifies the implementation and isolates gain-mean adaptation on saved observations. Final Part B supplies fresh prospective latency–reliability evidence against two strong local EP configurations, while the POINT and PBi subsets constrain interpretation.

The paper's strongest claim is neither an unconditional asymptotic theorem nor a catalogue of successful patches. It is an exact computational specialization and a complete native coded receiver with a prospectively demonstrated operating advantage. All remaining limitations—model scope, approximation fidelity, scalar uncertainty, comparator implementation, hardware, and missing compact-manifest fields—are explicit in this reference rather than hidden behind the word “joint.”

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


[16] C. Soussen, R. Gribonval, J. Idier, and C. Herzet, “Joint k-Step Analysis of Orthogonal Matching Pursuit and Orthogonal Least Squares,” *IEEE Transactions on Information Theory*, vol. 59, no. 5, pp. 3158–3174, 2013, doi: 10.1109/TIT.2013.2238606. Author manuscript: arXiv:1111.0522.

[17] S. Yang, L. Wang, T. Lv, and L. Hanzo, “Approximate Bayesian Probabilistic-Data-Association-Aided Iterative Detection for MIMO Systems Using Arbitrary M-ary Modulation,” *IEEE Transactions on Vehicular Technology*, vol. 62, no. 3, pp. 1228–1240, 2013, doi: 10.1109/TVT.2012.2227863. Author manuscript: arXiv:1311.1712.

## Internal source record {.unnumbered}

E-B: final prospective `RESULTS(20260922-014341).md`. E-A: final qualification/attribution `RESULTS(20260922-014351).md`. E-D: `SP_AFDM_Paper_Design_v1(3).md`. E-N: `SP_AFDM_Native_Joint_Research_Verdict_20260921(2).md`. E-M: `TABLES(3).md`. E-T: `theory_chapter(9).pdf`. Exact supplied copies and SHA-256 records are included in the drafting package's `source_records` directory.

The retired finite-list and consumer-statistic material is inherited from the supplied earlier manuscript/supplement and research continuation records in the conversation. Its equations are retained as supporting mathematical references, not as new empirical results or current online modules. E-C anchors refer to inspected archived native/frozen source files; final remote line-level provenance remains in the Part-A source/equation reconciliation record.

External primary records were used to verify bibliography and the stated prior-art boundaries. They were not used to fill missing private experimental configuration or to replace the final Part-A/Part-B evidence. No new receiver simulation, raw remote recount, or scope-extension experiment is claimed by this drafting edition.
