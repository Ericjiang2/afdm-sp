# Derivation Package: relative likelihood integration

## Target

Prove the relative-error and common-node variance identities for one **unchanged** bit likelihood object, then test a defensive contrast-guided importance proposal against both fixed common nodes and independent nodes at matched accuracy and complete message cost. The target is the outgoing message for I bit 0; its own incoming factor is excluded.

## Status

COHERENT AS STATED for the identities and conditional IID claims below. The proposed numerical rule is an unproven candidate with no promised gain. Gaussian-outside likelihood is a declared approximation and is never substituted silently for the full QPSK marginal. Numerical integration cannot recover information already removed by that approximation.

## Invariant Object

For fixed geometry, observation y, noise variance sigma²>0, gain prior pi and legal external cavity, define `f_b(h)=p_work(y|bit=b,h)` for b=0,1, with all other incoming factors integrated exactly as specified. Then

\[
m_b=\int f_b(h)\pi(dh),\quad L=\log m_0-\log m_1.
\]

The experiment stores both normalized likelihood densities m_b, the normalized two-bit probabilities, and L. It never evaluates only L while silently changing m_b's base measure.

## Assumptions

- Other incoming factors are normalized, independent of this observation factor, or legitimate cavity messages with this factor's site removed. No same-y posterior is reused as a physical prior.
- Noise is nondegenerate; finite-state QPSK weights are legal. The outside-Gaussian option uses the full real cavity covariance, retaining nonuniform I/Q impropriety.
- IID results require independent draws from a fixed proposal rho conditional on any independently constructed pilot proposal, pi absolutely continuous with respect to rho on the integrands' support, 0<m_b<infinity, and finite second moments of both importance weights.
- The Gaussian prior is CN(0,I/P). The normalized comparison is the controlled isotropic complex unit sphere. Neither is identified with the actual latent-PDP and truncated-G0-normalized production prior.
- A fixed nonlinear pushforward h=T(z) is integrated over base z~CN(0,I). For Gaussian h=z/sqrt(P); for sphere h=z/||z|| (the zero point has base probability zero). Proposal corrections are made in z space, where densities are available; no angular-density or Jacobian approximation is needed.

## Notation

`w_b(z)=phi(z) f_b(T(z))/rho(z)`; phi is the fixed standard complex Gaussian base density. `mhat_b=K^-1 sum_i w_b(z_i)`. The proposal may depend on y through a separate pilot batch. `e_b=mhat_b/m_b-1`. K is the number of final IID proposal nodes; a separate pilot count is included in the total work budget.

## Derivation Strategy

Exact ratio algebra -> mean-value bound -> joint IID CLT and delta method -> proposal design criterion -> defensive full-support rule -> same-object numerical comparison. QMC comparisons instead use deterministic refinement and independent scrambles empirically.

## Derivation Map

1. The logarithm identity and epsilon bound need positive estimated integrals, not IID sampling.
2. Proportional conditional likelihoods cancel under any identical positive node/weight rule.
3. The asymptotic variance requires the joint finite-variance IID CLT; independent nodes remove the covariance term.
4. Contrast-optimal importance sampling depends on unknown m_b and may lack full support. The implemented fit is an approximation to that proposal criterion, not an approximation to pi.
5. An independent pilot, fresh final IID samples and exact defensive pi/rho corrections preserve the target integral.

## Main Derivation

**Identity.** With mhat_b=m_b(1+e_b)>0,

\[
\widehat L-L=\log(1+e_0)-\log(1+e_1).
\]

**Proposition.** If |e_b|<=epsilon<1, the derivative of log(1+x) on [-epsilon,epsilon] is at most 1/(1-epsilon). The mean-value theorem between e_0 and e_1 therefore gives

\[
|\widehat L-L|\le |e_0-e_1|/(1-\epsilon).
\]

This is stronger than adding separate absolute errors when the two relative errors nearly agree, but it does not establish that they agree. Near-zero m_b makes a fixed absolute integration error inadequate; there is no uniform guarantee over arbitrarily rare likelihood regions. Log-domain evaluation prevents numerical underflow, not sampling uncertainty.

**Identity.** If f_0=c f_1, c>0, and identical nodes/weights are used, mhat_0=c mhat_1 at every sample size. Lhat=log c exactly in real arithmetic, up to floating-point roundoff. Independent node sets generally lose this samplewise identity.

**IID proposition.** The two-dimensional sample-mean CLT and the derivative `(1/m_0,-1/m_1)` of the log ratio imply

\[
\sqrt K(\widehat L-L)\Rightarrow N(0,V_\rho),\quad
V_\rho=\operatorname{Var}_\rho\left(\frac{w_0}{m_0}-\frac{w_1}{m_1}\right).
\]

The normalized difference has expectation zero. Relative to independently sampled sides, shared nodes change the variance by `-2 Cov(w_0/m_0,w_1/m_1)`. That covariance can be negative: on equiprobable z=+-1, f_0=1+a z, f_1=1-a z, 0<a<1, shared variance is 4a² while independent-side variance is 2a². Common nodes therefore have no universal variance advantage. Finite-sample log ratios are biased even when each mhat_b is unbiased.

**Finite-variance boundary.** Full support alone is insufficient. On (0,1), pi(x)=1 and rho(x)=2x have the same support. With f_0=1 and f_1=1+x, m_0=1 and m_1=3/2; the normalized weight difference is `(1-2x)/(6x)`. Its rho-second moment integrates `(1-2x)^2/(18x)` and diverges logarithmically at zero. The IID normal approximation is not justified there.

**Proposal criterion and controlled approximation.** For g=f_0/m_0-f_1/m_1, Cauchy–Schwarz bounds `int phi² g²/rho >= (int phi |g|)²`; formal equality uses rho proportional to phi|g|. Unknown m_b and possible zero support make this an unattainable/default-unsafe oracle recipe. The implemented candidate uses 64 independent prior pilot nodes, estimates m_b, and fits a proper Gaussian q to pilot weights proportional to |f_0/mhat_0-f_1/mhat_1|. Its covariance is an explicit proposal regularization `.9 C_weighted+.1 I`; it is not a changed physical covariance or hidden numerical jitter. Exactly zero pilot contrast is a declared degenerate case and uses q=phi.

The final proposal is rho=.5 phi+.5 q. It has full support and phi/rho<=2. Gaussian observation densities here obey `0<f_b<=(pi sigma²)^(-N)` because each conditional covariance is at least sigma²I and cavity weights sum to one. Thus both corrected weights are bounded for each fixed sigma²>0, proving finite second moments for the implemented candidate. Fresh final nodes are independent of the pilot. Conditional on that pilot, each mhat_b is unbiased and the conditional IID CLT applies. With a fixed random pilot, unconditional asymptotics can be a mixture of normals; no single unconditional variance theorem is asserted. Pilot nodes are not recycled into the final sample mean.

## Numerical contract

The frozen grid uses N=3/P=2, 3 exogenous draws, Gaussian/sphere gains, two noise levels (.15,1.2), uniform/nonuniform incoming factors and two likelihood objects: 12 distinct saved y shared by 48 cases. Gaussian QPSK likelihoods use analytic gain elimination as reference. Other references use fixed positive rules: Gaussian Hermite order 33 and Sobol 2^18/2^19 plus an independent 2^19 scramble; sphere orders 13/21 plus the same Sobol sizes. Numerical reference gates are max LLR difference .008, bit-probability difference .002 and log-density difference .015. All failed reference cases remain visible.

Arms are fixed common Sobol, common prior IID, independent prior IID, and defensive contrast IID. Budgets are 256/1024/4096 paired-node equivalents with four estimator replicates. The candidate spends 64 of each budget on the pilot. Independent sides each evaluate half of the candidate states, so all arms evaluate the same number of conditional word responses at a given budget; covariance reuse, node generation and proposal overhead can still differ and are explicitly timed. Final precision requires full-group LLR RMSE<=.05, 95th-percentile absolute error<=.1, and both-side relative-density RMSE<=.05. The cost comparison selects each arm's cheapest measured budget meeting these same full-group criteria, with no selection of successful samples. A missing precision-qualified budget is reported, not discarded.

Complete per-message cost includes node construction, pilot work, fitting, all word responses, conditional and proposal Cholesky factorizations, probability/LLR construction and raw artifact persistence. Fixed-geometry construction is a shared one-time cost and is separately reported; independent-reference computation and external error scoring are also separate. Whole-stage time and failures remain in the attempt ledger. Serial timing is exploratory local CPU cost, not production receiver latency.

Every message stores actual base nodes, log likelihood sides, importance ratios, proposal moments and pilot data where applicable. Observations/truth are saved once; truth enters only external observation generation and scoring. QMC has no IID variance or CLT field: its error is checked against independent/refined rules. The empirical replicates and their shared observation groups are not claimed as new communication frames.

## Remarks and Interpretation

This is classical correlated sampling, delta-method analysis and defensive importance sampling applied to a precisely defined AFDM bit integral. Learning a proposal with correction differs from replacing the prior. A proposal found useful here would improve integration of its existing likelihood object, not repair a Gaussian-outside model's lost high-order information. No novel-method or FER claim follows.

## Boundaries and Non-Claims

- No proposal-response or Onsager derivative is asserted; an observation-dependent proposal would contribute chain terms to a differentiated finite-sample receiver map.
- The stated IID theorem is not a scrambled-QMC CLT.
- The controlled sphere prior is not the actual production prior or an oracle production input.
- No receiver, decoder, remote execution or confirmation stream is used.

## Open Risks

Pilot contrast can be poorly estimated and a single Gaussian proposal can miss separated likelihood regions. The defensive component prevents support/variance invalidity but does not ensure efficiency. Fixed common Sobol can already be superior. All negative, precision-failed and reference-nonconverged cases must be retained and interpreted before any algorithmic conclusion.
