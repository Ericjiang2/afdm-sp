---
title: "Certified Soft-Output List Evaluation for Coded SP-AFDM"
subtitle: "Fractional-Doppler likelihoods, posterior-mass allocation, and a verified computation–fidelity tradeoff"
author: "Research continuation V4"
date: "19 September 2026"
fontsize: 11pt
geometry: margin=0.82in
colorlinks: false
header-includes:
 - \usepackage{amsmath,amssymb,mathtools,booktabs,longtable}
 - \usepackage{microtype}
 - \usepackage{fancyhdr}
 - \pagestyle{fancy}
 - \fancyhf{}
 - '\fancyhead[L]{\small Coded SP-AFDM: certified list evaluation}'
 - \fancyfoot[C]{\thepage}
 - \setlength{\headheight}{14pt}
 - \setlength{\emergencystretch}{3em}
---

# 1. Research decision and scope

**Select certified, computation-adaptive evaluation of an expanded codeword list as the main contribution to develop.** The central object is not a new channel estimator or a new decoding family. It is a receiver component that evaluates a coupled, channel-marginalized SP-AFDM likelihood while (i) preserving the exact maximizing word in the declared list, (ii) bounding the discarded probability under that same likelihood, and (iii) bounding the induced change in the posterior channel mean. An alternate hard-decision mode uses the saved likelihood work to examine additional candidates without sacrificing the best score available from a smaller nested list.

This is a **credible ordinary Transactions development case**, supported by exact theory, a working implementation, comparisons with stronger implementations of the same computation, and a reproducible scoped advantage. It is not a completed production-I1 superiority claim, a claim of global-codebook MAP, or a claim that recursive Gaussian updates and pruning were invented here.

The important shift from V3 is operational. V3 found that incorrect list decisions on its longer codes coincided with omission of the true word; polishing scores among the same few words could not repair that omission [P1]. This continuation first attempted new proposal mechanisms. They did not clearly beat the stronger branch control. It then attacked the *cost of assessing more hypotheses*. Unlike adding another confidence diagnostic, the selected method actually reduces the work needed to examine a larger specified list.

The contribution belongs to the complete mechanism: full fractional-Doppler AFDM time-domain regressors, a properly normalized monotone marginalized score, probability-budgeted stopping, channel-mean fidelity, and a measured search-size/accuracy/cost tradeoff. Its main limitation is equally explicit: **it does not certify probability outside the list supplied to it**. Candidate acquisition and channel-model error remain distinct sources of error.

# 2. Starting state and alternative mechanisms actually tested

The inherited V3 physical and coding implementations are reused without modification. New methods are separate. This run does not repeat the historical audit or relabel historical I1 results as new experiments. V3's documented complete runtime and prior physical checks are inherited assets, while the new core computations are independently cross-checked below.

Three proposal-side mechanisms were implemented before selecting the scorer accelerator: conditional-bit reliabilities obtained by refitting/marginalizing the channel for each probe; nonlinear most-reliable-basis bit-neighbor search; and multiple channel-conditioned branches, including observation-distance-based diversity. They are different operations, not merely different regularization values.

| Discovery comparison | New numerical outcome | Interpretation |
|---|---|---|
| Cold-start screen, 64 draws | OSD-64: 32 errors; conditional-bit proposal: 30; nonlinear beam: 31; four-phase proposal: 36; inherited branch: 23 | None justified displacing the stronger branch control. Conditional probes incur additional likelihood evaluations. |
| Warm-feedback screen, 192 draws | Five-round soft CE: 106; ten rounds: 103; BP-proposed OSD-64 with fixed-channel scoring: 91; marginalized/profile scoring: 83 | Refitting the channel for rescue words is useful, but profiling is a strong simpler comparator. |
| Branch-selection screen, 256 draws | Single marginalized OSD-64: 107; top-score branches: 103; diverse branches: 102 | The one-frame difference does not justify a diversity-specific headline, especially with extra decoder calls. |

The screens use full fractional propagation and paired receiver arms. They are exploratory, have different generated streams, and are not pooled into one statistical experiment. Details, seeds, full arm definitions, and costs are preserved in `screen_search.py`, `screen_hybrid.py`, `adaptive_rescue.py`, and the corresponding CSV/NPZ files. The `beam_search` implementation actually ranks marginalized scores; its historical unused `kind` argument does not establish a separate profiled-beam experiment.

A separate structural alternative, dual-domain AFDM equalization, was screened through the closest literature. Time-domain/AFDM-domain processing and low-complexity equalization are already developed [R4,R5]. No new equalizer was executed or claimed in this pass. Their existence is not a proof that all SP-specific extensions lack novelty; it made the concrete list-scoring bottleneck the more focused opportunity.

# 3. Conditional receiver model

## 3.1 Physical and statistical assumptions

Let the information message determine a codeword and scaled QPSK vector $d\in\mathbb C^N$. The known SP vector $p$ already includes its power. The model is

$$
y=\sum_{s=1}^{S}g_sU(l_s,\nu_s)(p+d)+w,
\qquad w\sim\mathcal{CN}(0,\sigma^2I_N). \tag{1}
$$

Integer sample delays, an adequate chirp-periodic prefix, blockwise-fixed path parameters, ideal synchronization, and proper sampled thermal noise are assumed. Dopplers $\nu_s$ are real and are **not rounded or truncated in propagation or candidate scoring**. Fractional delay, unknown pulse-shaping filters, and inter-block drift are outside the tested model.

Path geometry is frozen during a scoring call. It can be supplied by an earlier estimator, but the main matched tests use known geometry and unknown gains; the stress tests use deliberately mismatched geometry. No true gains or data are supplied to the operational scorer.

The gain prior is an exogenous

$$g\sim\mathcal{CN}(0,C_g),\qquad C_g=C_g^H\succ0. \tag{2}$$

It is a working model, not a covariance estimated from the same observation and then asserted to be independent evidence. True Bayesian interpretation requires the specified model. Pointwise approximation guarantees survive model mismatch because they compare two computations of the same frozen working likelihood.

## 3.2 Why the AFDM implementation matters

Use the handoff's positive-chirp convention,

$$A=\Lambda^+_{c_2}F\Lambda^+_{c_1},\qquad
[\Lambda^+_c]_{nn}=e^{j2\pi cn^2},$$

with a negative-exponent unitary DFT. Let $Y=A^Hy$ and $X_d=A^H(p+d)$. For row $n$ define

$$f_{d,n,s}=\chi_{l_s}(n)e^{j2\pi\nu_sn/N}
X_d[(n-l_s)\bmod N], \tag{3}$$

where $\chi_l(n)=1$ for $n\ge l$ and

$$\chi_l(n)=e^{j2\pi c_1[N^2+2N(n-l)]},\quad n<l.$$

Then $Y_n=f_{d,n}g+W_n$, and the rows form a matrix $\Phi_d$. Equation (3) follows directly by applying each delayed path, its prefix phase and Doppler phase in time, before DAFT demodulation. Since $A$ is unitary, transforming the observation preserves the likelihood and white-noise variance.

A candidate requires one IDAFT followed by shifted sample reads and phase multiplications; no dense $N\times N$ fractional-Doppler channel is needed by the scorer. This does not assert independent QPSK symbols in time: **the entire coded DAFT-domain candidate is generated first**. The temporal factorization conditions on that complete candidate and on the gain, not on independent time-domain symbols.

This is the useful structural distinction from a conventional subcarrier-symbol search in a diagonal OFDM model. A partial set of AFDM data symbols does not, in general, determine an independent observation prefix. The proposed method instead uses complete codewords and successively reveals their observation likelihoods.

## 3.3 Finite-list contract

A front end supplies an ordered, duplicate-free list $\mathcal B(y)=\{d_1,\ldots,d_B\}$. In the tests it is an order-at-most-two OSD proposal ordered by information-bit reliability penalties. The theorem does not depend on that particular proposal. The list may depend on $y$; after construction it is frozen.

All words have equal message prior in the experiments. Their posterior *conditional on this finite list* is

$$P_B(d\mid y)=\frac{e^{-F_N(d)}}{\sum_{e\in\mathcal B}e^{-F_N(e)}}. \tag{4}$$

A nonuniform specified prior could be included as an initial candidate cost $-\log\pi(d)$. This extension is not the executed experiment. Decoder APPs are not multiplied into the final physical score as fresh independent observations.

# 4. Proposed method: monotone channel-marginalized scoring

## 4.1 Exact marginalized metric

Integrating (2) gives covariance $C_d=\sigma^2I+\Phi_dC_g\Phi_d^H$. After subtracting the common noise normalization, the cost is

$$F_N(d)=Y^HC_d^{-1}Y+
\log\det\left(I+\sigma^{-2}\Phi_dC_g\Phi_d^H\right). \tag{5}$$

For comparison, let

$$B_d=C_g^{-1}+\sigma^{-2}\Phi_d^H\Phi_d,
\qquad b_d=\sigma^{-2}\Phi_d^HY.$$

Completing the square and using the determinant lemma yield

$$F_N(d)=\frac{\|Y\|^2}{\sigma^2}-b_d^HB_d^{-1}b_d
+\log\det B_d+\log\det C_g,\qquad m_d=B_d^{-1}b_d. \tag{6}$$

The reference batch implementation uses (6). The independent verifier uses (5), not the same recursion.

The quadratic part without the determinant is regularized profile scoring. It is an important alternative inference target, but silently dropping the determinant does not accelerate the same marginal likelihood. Classical recursive least-squares pruning [R1,R2] and Gaussian marginalization are acknowledged foundations.

## 4.2 Innovation form and its normalization

Choose any row permutation $\pi$, frozen during the call. Initialize $m_0=0$, $V_0=C_g$, $F_0=0$. At row $f=f_{d,\pi(t)}$, set

$$a=V_{t-1}f^H,\quad v=\sigma^2+fa,\quad
 e=Y_{\pi(t)}-fm_{t-1}, \tag{7}$$

$$\begin{split}
F_t&=F_{t-1}+\frac{|e|^2}{v}+\log\frac{v}{\sigma^2},\\
m_t&=m_{t-1}+ae/v,\\
V_t&=V_{t-1}-aa^H/v.
\end{split} \tag{8}$$

**Proposition 1 (exact monotone metric).** In exact arithmetic, $V_t\succeq0$, $v\ge\sigma^2$, $F_t$ is the normalized marginal cost of the selected first $t$ rows, and

$$0\le F_t\le F_{t+1}\le F_N. \tag{9}$$

*Proof.* The Gaussian conditional density of the next observation has mean $fm_{t-1}$ and variance $v$. The Gaussian conditioning formula gives the two posterior updates. Multiplying predictive densities gives the full density; subtracting one $\log\sigma^2$ per observed row gives (8). Both incremental terms are nonnegative, proving (9). Equivalently, the Schur complement factors the determinant and quadratic form in (5). $\square$

The $\log(v/\sigma^2)$ term is essential. Using $\log v$ would be negative whenever $v<1$, so an unnormalized prefix would not be the stated lower bound. Sorting rows by descending $|Y_n|^2$ is the tested heuristic; it is not asserted to be optimal. Data dependence of this permutation does not invalidate the algebraic identity for the realized arrays. The prefix is evaluated as a fixed-subset density, not interpreted as the distribution additionally conditioned on the selection event.

## 4.3 Exact finite-list hard decision

Maintain the smallest cost $F_*$ among fully scored candidates. Stop evaluating a new candidate once $F_t>F_*$. That candidate cannot beat the incumbent by (9).

**Corollary 1.** Completing the scan preserves the exact minimizing word in $\mathcal B$. Ties are resolved by retaining the first minimizer, using strict rejection. This is a finite-list guarantee, not a certificate that an ungenerated codeword is worse.

Only fully scored words have valid full conditional means $m_d$. Using intermediate posterior means from pruned words as though they were full-observation estimates is incorrect.

# 5. Soft output and posterior probability budgets

Hard pruning alone can throw away substantial posterior probability. Its normalized survivor posterior is not necessarily suitable for channel estimation, even though its MAP word is exact. The following two policies retain the same MAP word and control this separate error.

## 5.1 Computable discarded-mass bound

Let $\mathcal K$ be the fully evaluated words and $\mathcal P$ the stopped words. For each stopped word retain its prefix cost $\underline F_d$. Define

$$Z_K=\sum_{d\in\mathcal K}e^{-F_N(d)},\qquad
U_P=\sum_{d\in\mathcal P}e^{-\underline F_d}. \tag{10}$$

The unknown actual discarded weight $Z_P$ satisfies $Z_P\le U_P$. Thus

$$\epsilon_B=P_B(\mathcal P\mid y)
\le\bar\epsilon_B=\frac{U_P}{Z_K+U_P}. \tag{11}$$

This is a deterministic bound under the same coupled likelihood, not a proxy-decoder confidence estimate, Monte Carlo bound, or random-codebook approximation.

### Uniform reserve policy

For a requested $0<\epsilon<1$, choose

$$T=\max\left\{0,\log\frac{B(1-\epsilon)}{\epsilon}\right\} \tag{12}$$

and stop a candidate only at $F_t>F_*+T$.

**Proposition 2 (uniform soft guarantee).** The policy retains finite-list MAP and ensures $\bar\epsilon_B\le\epsilon$.

*Proof.* The final incumbent cost is no greater than any preceding incumbent. Every stopped candidate has upper weight less than $e^{-F_*^{\rm final}-T}$. There are at most $B$ of them, while $Z_K\ge e^{-F_*^{\rm final}}$. Hence $U_P/Z_K\le Be^{-T}\le\epsilon/(1-\epsilon)$ whenever the logarithmic threshold is positive. If it is negative and $T=0$, then $B\le\epsilon/(1-\epsilon)$ already. Equation (11) proves the result. $T\ge0$ also proves MAP preservation. $\square$

### Adaptive reserve allocation

The selected implementation reduces unnecessary conservatism by maintaining $Z_K$ and $U_P$ online. Put $r=\epsilon/(1-\epsilon)$. Before a candidate with $R$ candidates still to assess, allocate

$$a_d=\frac{rZ_K-U_P}{R}. \tag{13}$$

The first word is fully evaluated. If $a_d\le0$, no soft rejection is permitted. Otherwise, stop the current candidate only when

$$F_t>\max\{F_*,-\log a_d\}. \tag{14}$$

On stopping, add $e^{-F_t}$ to $U_P$; on completion, add $e^{-F_N}$ to $Z_K$ and update the incumbent. Overshoot below the allocated weight remains available to subsequent candidates. All calculations use logarithmic sums to avoid underflow.

**Proposition 3 (adaptive budget invariant).** After every candidate, $U_P\le rZ_K$. The final decision is finite-list MAP and the final posterior error obeys (11) with $\bar\epsilon_B\le\epsilon$.

*Proof.* Initially $U_P=0$. A fully evaluated word increases $Z_K$ and leaves $U_P$ unchanged. A stopped word adds at most $(rZ_K-U_P)/R\le rZ_K-U_P$, preserving the invariant. The independent incumbent condition in (14) ensures that no potentially winning word is discarded. $\square$

There is no theorem that this equal-remaining-budget allocation minimizes computation or uniformly outperforms (12). In the held-out test its reduction over the uniform policy is small; the main gain is relative to full evaluation, not the adaptive-versus-uniform difference.

## 5.2 Meaning for soft output and channel estimation

Let $P_K=P_B(\cdot\mid\mathcal K)$. Directly summing probability differences gives

$$\operatorname{TV}(P_B,P_K)=\epsilon_B\le\bar\epsilon_B. \tag{15}$$

Any bit probability changes by at most $\bar\epsilon_B$. An unrestricted LLR error does **not** follow: probabilities close to zero can amplify logarithmic errors. The same TV bound holds for the joint codeword/gain mixture when each retained word keeps its exact conditional gain distribution.

**Proposition 4 (gain-mean fidelity).** Define

$$R_g=\frac{\sqrt{\lambda_{\max}(C_g)}\,\|Y\|}{2\sigma}.
\tag{16}$$

Every complete conditional mean obeys $\|m_d\|\le R_g$, and

$$\|\mathbb E_{P_B}g-\mathbb E_{P_K}g\|
\le2R_g\bar\epsilon_B. \tag{17}$$

*Proof.* Write $T_d=\Phi_dC_g^{1/2}/\sigma$. The conditional mean equals

$$m_d=C_g^{1/2}T_d^H(I+T_dT_d^H)^{-1}Y/\sigma.$$

The middle matrix has singular values $t/(1+t^2)\le1/2$, proving (16). The full mean is a mixture of retained and discarded means. Their difference is $\epsilon_B$ times the difference between two means in the radius-$R_g$ ball, proving (17). $\square$

For a desired absolute CE tolerance $\tau$, use

$$\epsilon_{\rm used}=\min\{\epsilon_0,\tau/(2R_g)\}, \tag{18}$$

with the zero-observation case handled directly. This option is implemented and tested. It bounds the approximation to the finite-list posterior gain mean, **not** the true gain error, channel NMSE, or the update of an arbitrary approximate turbo receiver.

V2's ungenerated-codeword issue has not disappeared. If $\epsilon_{\rm gen}=P(\mathcal C\setminus\mathcal B\mid y)$ is the global posterior mass outside the supplied list, total excluded mass after pruning is

$$\epsilon_{\rm gen}+(1-\epsilon_{\rm gen})\epsilon_B. \tag{19}$$

Only the second component is controlled here. No outside-list estimate is fabricated. The practical benefit is that a larger list can be evaluated affordably without adding another uncontrolled soft truncation inside it.

# 6. Alternate fixed-work mode

A second operating mode is intended for terminal hard decoding. Suppose the baseline fully scores the first $B_0$ candidates, requiring $B_0N$ row updates. Apply hard pruning to the same nested ordering, allowing up to $B_{\max}$ candidates but stopping after $B_0N$ updates.

**Proposition 5 (nested work-budget dominance).** The best fully evaluated score returned by this mode is no greater than the best full score among the first $B_0$ words.

*Proof.* Each candidate requires at most $N$ row updates, so all first $B_0$ candidates can be assessed within the budget. An early-stopped candidate cannot improve the incumbent. At budget exhaustion, any partially processed extra word cannot remove the already assessed first-$B_0$ result. Extra completed words can only improve the incumbent. $\square$

This is a dominance statement for scalar innovation work and the specified score. When that score is proportional to the true posterior, the conditional probability of the selected message is no smaller. Realized errors on a finite sample can still fluctuate; under a mismatched model only the score statement remains.

Additional proposals and IDAFTs cost work too. Equal $B_0N$ row budgets are not equal wall-clock budgets. Moreover, unvisited candidates have no completed soft certificate. **Do not advertise simultaneous fixed total latency and unconditional soft fidelity without charging a fallback or accepting an uncertified result.**

# 7. Algorithm and complexity

A complete soft-scoring call performs the following operations.

1. Freeze $(y,p,\{l_s,\nu_s\},C_g,\sigma^2)$ and generate a duplicate-free finite list from allowed decoder/equalizer outputs. Keep its prior interpretation explicit.
2. Transform $Y=A^Hy$ and each complete $X_d=A^H(p+d)$. Precompute path phases and choose a row permutation.
3. Fully score the first candidate. For each remaining word form only the needed rows (3), update (7)-(8), and apply the uniform or adaptive soft threshold.
4. Accumulate exact completed weights and upper stopped weights. Return the best word, retained posterior weights and gain mean, $\bar\epsilon_B$, the mean-error bound, and the actual work count.
5. Treat a failed numerical-positive-definiteness check as a numerical failure, not an absence of posterior mass. The reference raises an error; production software should have an explicitly charged stable-factorization fallback.

If $M=\sum_dm_d\le BN$ is the number of evaluated observation rows, the principal online cost is

$$C_{\rm proposal}+O(BN\log N)+O(MS^2)+O(BS+NS). \tag{20}$$

The $S\times S$ rank-one recursion replaces repeated full information-matrix accumulation. A full unpruned implementation has $M=BN$; a straightforward batch method additionally solves/factors each small candidate matrix. The actual implementation stores all candidate time vectors: memory is $O(BN+BS+NS+S^2)$. Streaming their IDAFTs could reduce memory, but no unimplemented saving is credited.

Worst-case $M=BN$. Diffuse likelihoods, large gain dimension, poorly conditioned proposals, low SNR, or near-indistinguishable words can eliminate the saving. Candidate generation may dominate total latency even when scoring improves substantially. Compilation, code construction, and common initialization are separately identified in timing records.

# 8. Numerical evidence

## 8.1 Discovery and frozen validation contracts

The physical propagation uses the unmodified full fractional-Doppler function from the supplied handoff. The candidate scorer uses (3), independently reconstructed from time samples. No truncation renormalization, true-data cancellation, or true gain input is used by the operational methods.

The development test contains 192 independent draws over $N\in\{12,48,96,192\}$ and $\sigma^2\in\{0.05,0.2,0.5\}$, with 16 draws per cell. At $N=12$ the 256-word codebook is exhausted. The three tolerances $0.1,0.01,0.001$ are evaluated on the same draws and are not three independent datasets.

The frozen validation contains **192 independent channel/message/noise draws**, paired across methods: $N=48,96,192$, $S=3,6$, $\rho=0.15,0.5$, $\sigma^2=0.05,0.2$, eight draws per cell. The binary code length is $2N$, built once per length from the supplied Gallager generator. The list has 256 words. Pilot magnitude is $\sqrt\rho$; QPSK energy is $1-\rho$. Noise variance is complex variance, not the standard deviation.

The working covariance has entries proportional to $0.45^{i+j}0.35^{|i-j|}$. For $S=6$, actual gains are additionally normalized and actual Dopplers are shifted by $0.06\sin(s+0.3)$ relative to the working model. This tests correctness of the approximation under prior/geometry mismatch, not adequacy of that mismatched statistical model. Because this covariance favors a few paths, a separate equal-power test follows.

The uniform policy was frozen before validation. Adaptive allocation was synthesized afterward and evaluated on the same validation data; its small incremental advantage is therefore a **post-synthesis ablation**, not a second independent confirmation.

## 8.2 Exact decisions, controlled moments, and row work

Every uniform and adaptive decision equals the full 256-list marginal MAP decision. The full and certified methods produce 48 failed frames out of 192; the nested 16- and 64-word exhaustive alternatives produce 64 and 54 failures. The difference belongs to examining a larger list, not to pruning changing a fixed list's decision.

For $\epsilon=0.01$:

| Quantity | Uniform reserve | Adaptive reserve |
|---|---:|---:|
| Mean fraction of full row work | 0.435906 | 0.432639 |
| Maximum actual discarded list mass | 0.000143605 | 0.002907262 |
| Maximum reported upper bound | 0.004106376 | 0.009921849 |
| Maximum channel-mean change | $1.18\times10^{-5}$ | $9.20\times10^{-5}$ |
| Disagreements with full-list MAP | 0/192 | 0/192 |

Adaptive allocation spends more of the available fidelity budget; this is not deterioration beyond the prescribed limit. Its benefit over uniform allocation is modest and is not a separate major contribution.

| $N$ | Adaptive row fraction, $\sigma^2=0.05$ | Adaptive row fraction, $\sigma^2=0.20$ |
|---:|---:|---:|
| 48 | 0.334035 | 0.605194 |
| 96 | 0.271392 | 0.560575 |
| 192 | 0.181355 | 0.643284 |

These average over the declared two path-count and two pilot-power settings, not over an unspecified universal channel distribution.

![Work reduction relative to complete evaluation of the same 256 candidates. Each noise curve summarizes 96 held-out draws.](../figures/work_reduction.png){width=88%}

## 8.3 A hard-pruning counterexample with an actual consumer

In the complete $N=12$, 256-word codebook fixture `N12_s0.5_f0`, hard pruning preserves exact global codeword MAP but discards **0.748950** posterior probability. Renormalizing its completed words changes the posterior gain mean by **0.289413**. The mass-aware rule protects against precisely this failure.

This is a selected counterexample, not an average effect size. It demonstrates why a classical hard-search accelerator plus survivor renormalization is not an adequate comparator for the claimed soft-output contract.

## 8.4 Balanced-path stress and CE tolerance

An additional 48 independent draws use equal-power $C_g=I/S$, $N=48,96$, $S=3,6$, $\rho=0.5$, and $\sigma^2=0.05,0.2,0.5$. The uniform mass policy and its $\tau=10^{-3}$ gain-mean-tolerance option are tested on the same draws. All exact-decision, probability, and mean-bound checks pass.

| $S$ | $\sigma^2$ | Mass-policy work fraction | CE-tolerance work fraction |
|---:|---:|---:|---:|
| 3 | 0.05 | 0.265625 | 0.275080 |
| 3 | 0.20 | 0.574524 | 0.605810 |
| 3 | 0.50 | 0.863383 | 0.886719 |
| 6 | 0.05 | 0.291555 | 0.299408 |
| 6 | 0.20 | 0.748072 | 0.773697 |
| 6 | 0.50 | 0.938721 | 0.967194 |

The last row is an important failure boundary: the method processes almost the whole list and can offer little time saving. Hard pruning on this stress stream has maximum discarded mass 0.714241 and maximum mean change 0.123264 despite preserving MAP. Zero observations, tolerance values near one, and rejection of nonpositive gain covariances are separately checked.

## 8.5 Reinvesting hard-decision work

On the 192 validation draws, the hard fixed-work mode gives:

| Baseline size $B_0$ | Fixed-prefix errors | Pruned expanded-search errors | Mean candidates visited |
|---:|---:|---:|---:|
| 16 | 64 | 64 | 59.72 |
| 32 | 58 | 57 | 115.99 |
| 64 | 54 | 52 | 179.93 |

The score-dominance property holds on every draw. The error differences are small exploratory observations, not a statistically established population FER advantage. Equal core work does not include the additional proposal/transform cost. This mode and the soft-certified mode are distinct operating contracts.

## 8.6 Wall-clock results with stronger baselines

The final timing test uses 15 randomized, interleaved repetitions on each of four representative fixtures. Every timed arm includes OSD from existing LLRs, QPSK mapping, candidate IDAFTs, score evaluation, and the posterior gain mean. Initial CE and equalizer/LDPC processing that produced the LLRs are excluded, as are common observation transforms, static code construction, and JIT compilation. All 480 individual times are saved.

The unpruned sequential baseline uses the same compiled recursion. This isolates pruning gains from Python-versus-compiled implementation differences. Batch marginalization is another control.

| $N$ | $\sigma^2$ | $B$ | Batch (ms) | Unpruned compiled (ms) | Adaptive (ms) |
|---:|---:|---:|---:|---:|---:|
| 96 | 0.05 | 256 | 17.917 | 16.370 | 12.697 |
| 96 | 0.05 | 1024 | 47.400 | 42.170 | 27.519 |
| 96 | 0.20 | 256 | 16.596 | 16.246 | 15.137 |
| 96 | 0.20 | 1024 | 46.752 | 42.474 | 34.974 |
| 192 | 0.05 | 256 | 55.990 | 54.885 | 48.695 |
| 192 | 0.05 | 1024 | 132.953 | 123.552 | 96.500 |
| 192 | 0.20 | 256 | 57.109 | 55.263 | 54.238 |
| 192 | 0.20 | 1024 | 132.783 | 122.875 | 120.237 |

At $B=1024$, $\sigma^2=0.05$, reductions versus the same compiled full scorer are **34.74% and 21.90%** for $N=96,192$. At $N=192$, $\sigma^2=0.20$, the reduction is only 2.15%. These are fixture-specific medians, not hardware-independent confidence intervals or percentages for the complete I1 receiver. Amdahl's law applies to integrating the component into a larger receiver.

![Rescue-stage latency, including proposal and transforms but excluding prior CE/LLR production. The exact scored list and final MAP decision are common across compared arms.](../figures/rescue_latency.png){width=91%}

# 9. Closest prior work and the complete novelty case

Recursive updates, candidate ordering, and pruning are established. Al-Naffouri et al. [R1] derive partial-sequence RLS bounds for blind OFDM, and Zaib and Al-Naffouri [R2] study related semiblind STBC-OFDM search. Their role here is an explicit intellectual and algorithmic foundation, not something to conceal. The inspected derivations optimize a profiled channel metric over a symbol tree; they do not establish this manuscript's full-SP finite-list soft-mass and gain-mean contract.

Feng, Duffy, and Medard [R3] address probability outside visited codewords in soft OSD/GRAND/GCD/SCL. Their inspected formulation uses known-channel bitwise likelihood structure and codebook models for unvisited hypotheses. Our result is narrower globally but deterministic within its declared expanded list, uses a coupled channel-marginalized likelihood, and requires no factorized-codeword posterior or random-codebook approximation for (11). It does not replace their treatment of ungenerated words.

Dual-domain EP [R4], structured AFDM equalization [R5], and matched-filter graph methods [R9] establish that changing the processing domain can reduce fractional-Doppler detection cost. The contribution cannot be 'process AFDM in time'. The present use of that domain enables exact cheap observation rows for *complete candidate codewords*, preserving both pilot/data coupling and the specified marginal score.

SP-AFDM iterative estimation [R6], data-aided fractional AFDM SBL [R7], and SP-OTFS soft message passing [R8] establish the broader receiver setting. This method need not invent those primitives to be useful. Its proposed difference is a **controlled alternative to either paying full cost for every code–channel hypothesis or applying unquantified pruning that corrupts the next estimation step**.

Additional nearest-neighbor checks include low-complexity SOSD in NOMA [R10] and adaptive soft sphere-decoder clipping [R11]. Both reinforce that soft search complexity is not a new general topic. The narrower paper must compare objectives and guarantees, not simply claim 'soft pruning for the first time'. No exhaustive first-ever claim or acceptance guarantee is made.

A plausible contribution set is therefore: (C1) exact observation-prefix evaluation for channel-marginalized fractional SP-AFDM; (C2) a probability-budgeted pruning and gain-mean-fidelity controller; (C3) an executable finite-list fidelity/complexity tradeoff, with a separately stated fixed-work extension. The small adaptive-versus-uniform improvement, OSD itself, Gaussian integration, and the old pilot-only CE are not separate contributions.

# 10. Independent verification, reproducibility, and remaining confirmation

`independent_verify.py` imports no candidate modules. It builds an explicit dense IDAFT, constructs time regressors independently including prefix phases, and evaluates $N\times N$ observation-covariance determinants and solves. It checks selected complete and partial candidate scores, conditional means, all frame decisions, and probability/mean bounds. There are **3,392 comparisons on 192 frames**, with maximum absolute discrepancy $4.37\times10^{-11}$.

`verify_adaptive.py` independently recomputes the retained weights, upper mass sums, gain means, all saved-prefix inequalities and adaptive bounds. Its **1,536 checks** have maximum equality discrepancy $5.66\times10^{-12}$. These counts are numerical consistency checks, not independent human reviews or scientific replications.

A fresh execution reproduces **all 2,496 saved validation arrays exactly** in the same environment. Timing is excluded. The implementation uses floating-point arithmetic with a conservative comparison tolerance. The theorem is exact-arithmetic; these tests are not machine-certified interval arithmetic. A very ill-conditioned production implementation should use stable square-root updates and a charged fallback rather than silently trusting a failed positive-variance check.

The accompanying independent-confirmation driver is executable and configured but **not run** at its planned sample size. Its engineering smoke path was executed on 24 draws (one per cell), excluded from the scientific tables above. It increases the number of independent validation draws after freezing both policies and reports comparisons against full batch/full sequential evaluation and nested smaller lists. Production integration must separately charge its front end and compare against the frozen I1 operating point. There is no new I1/LDPC production FER or end-to-end latency claim in this report.

The research decision does not require universal superiority. The intended regime is moderate-dimensional frozen path hypotheses, finite codeword-list rescue or short-packet joint reception, and enough posterior separation that many candidate likelihoods can be stopped early. The executed counter-regime is diffuse, noisy, balanced multipath, where little work is saved. The remaining study should confirm a useful operating envelope rather than hide that boundary.

# 11. Claim-to-evidence map

| Claim | Status | Mathematical / implementation source | Numerical evidence |
|---|---|---|---|
| Prefix costs are exact lower bounds | Proved and independently checked | (3),(5),(7)-(9); `sequential_search.py` | `independent_verification.json`, saved validation arrays |
| Uniform pruning preserves finite-list MAP and mass budget | Proved and executed | Proposition 2; `certified_mass.py` | `holdout.csv`, `mass_screen.csv` |
| Adaptive pruning maintains the probability invariant | Proved and executed; post-synthesis ablation | Proposition 3; `adaptive_mass.py` | `adaptive_mass.csv`, `adaptive_verification.json` |
| Gain-mean tolerance is controlled | Proved and executed | Proposition 4; both soft wrappers | `balanced_stress.csv` |
| Hard pruning alone can corrupt CE moments | Executed counterexample | Survivor conditioning | `hard_soft_ablation.csv` |
| Fixed core budget preserves the nested-prefix best score | Proved and executed | Proposition 5; `budget_and_timing.py` | `budget.csv` |
| Meaningful rescoring-stage time saving in stated fixtures | Empirical, implementation-specific | `timing_final.py` | `timing_raw.csv`, `timing_contract.json` |
| Superiority over complete I1, unknown-support recovery, global posterior coverage | Unresolved; not asserted | Requires separate integration and confirmation | No new production result |

# References and source record

Public sources were checked on 19 September 2026. Full source records and consulted scope are preserved in `literature.json`. No external paper's performance curves are represented as independently reproduced here.

[R1] T. Y. Al-Naffouri et al., “Low Complexity Blind Equalization for OFDM Systems with General Constellations,” *IEEE Transactions on Signal Processing*, 60(12), 6395–6407, 2012, DOI: 10.1109/TSP.2012.2218808; arXiv:1207.2546. Author manuscript, partial-cost and RLS derivations inspected. Web screenshot rendering failed; parsed mathematical text was available.

[R2] A. Zaib and T. Y. Al-Naffouri, “Blind and semi-blind ML detection for space-time block-coded OFDM wireless systems,” *EURASIP Journal on Advances in Signal Processing*, 2014:131, DOI: 10.1186/1687-6180-2014-131. Primary article.

[R3] “Leveraging Code Structure to Improve Soft Output for GRAND, GCD, OSD, and SCL,” arXiv:2503.16677, 2025, by Feng, Duffy, and Medard. Primary manuscript, likelihood assumptions and unvisited-word probability treatment inspected.

[R4] “A Novel Low-Complexity Dual-Domain Expectation Propagation Detection Aided AFDM for Future Communications,” arXiv:2603.29218, 2026. Primary manuscript.

[R5] “Joint Chirp Parameter Selection and Low-Complexity MMSE Receiver Design for AFDM Systems,” arXiv:2607.20227, 2026. Primary record and manuscript consulted.

[R6] K. Zheng, M. Wen, T. Mao, L. Xiao, and Z. Wang, “Channel Estimation for AFDM With Superimposed Pilots,” arXiv:2404.10232, 2024; *IEEE Transactions on Vehicular Technology*, 2025.

[R7] “Data-aided Channel Estimation and Sensing With Sparse Bayesian Learning for AFDM-ISAC System,” arXiv:2607.18881, 2026. Primary manuscript.

[R8] F. Huang et al., “Message Passing-Based Joint Channel Estimation and Signal Detection for OTFS with Superimposed Pilots,” arXiv:2309.08177; *IEEE Transactions on Vehicular Technology*, 2024.

[R9] L. Wu et al., “AFDM signal detection based on message passing scheme,” *Digital Signal Processing*, 2024. Matched-filter-domain method; prior V3 closest-work record retained.

[R10] C. Yue et al., “NOMA Joint Decoding based on Soft-Output Ordered-Statistics Decoder for Short Block Codes,” arXiv:2110.15010, 2021. Primary abstract record; no formula-level equivalence claim beyond its stated scope.

[R11] K. Nikitopoulos and G. Ascheid, “Complexity Adjusted Soft-Output Sphere Decoding by Adaptive LLR Clipping,” arXiv:1011.2113, 2010. Primary abstract record; a related complexity/soft-output alternative, not a same-model certified comparator.

[P1] *SP-AFDM method-design continuation*, supplied V3 `method_design_report.pdf` and editable counterpart. Sections on longer-code candidate omission, marginalized/profile competitors, and implementation interfaces establish the inherited starting state. Earlier audits are not substituted for this latest evidence.
