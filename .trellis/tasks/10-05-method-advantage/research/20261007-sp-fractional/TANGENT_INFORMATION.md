# Pointwise channel accuracy does not control fractional-Doppler information

## Target

Determine whether a small (even zero) channel-matrix truncation error guarantees
that a superimposed-pilot receiver retains local fractional-Doppler information.
The immediate deliverable is a modeling counterexample and a quantitative
operator identity, not a new receiver or a performance claim.

## Status

COHERENT AS STATED, pending independent mathematical review. Novelty and
practical advantage remain unestablished. First-order off-grid expansions,
variable projection and nuisance-projected Fisher information are classical.

## Invariant object

The efficient Fisher information for continuous Doppler after treating the
complex gain as an unknown deterministic nuisance. The physical observation law
is preserved: data are unknown and marginalized, not made available to the
receiver. Operator derivative energy is a separate diagnostic, not that Fisher
information.

## Assumptions and notation

Let A be the unitary DAFT in `physical.py`, N>=2, and l an integer delay. Write

    U_l(nu) = A D(nu) C_l P_l A^H,
    D(nu)[n,n] = exp(2 pi i n nu/N), n=0,...,N-1.

C_l is the actual diagonal unit-modulus CPP wrap factor and P_l the circular
delay. Both are independent of nu. Consider one physical path

    y = h U_l(nu)(p+d) + w,

with known nonzero AF-domain pilot p, unknown h!=0, unknown continuous nu,
w~CN(0,sigma2 I), sigma2>0, and independent AF-domain iid QPSK data with
E[d]=0, E[dd^H]=rho_d I, E[dd^T]=0. This is explicitly an uncoded single-path
analysis slice; it is not the production LDPC law or a multipath theorem.

Set D_N(t)=N^{-1} sum_{n=0}^{N-1} exp(2 pi i n t/N). Let U_k=U_l(k) for a
complete set of N integer residues. These operators are Frobenius orthogonal:
tr(U_j^H U_k)=N 1_{j=k}, including the actual CPP factors.

The gain is free locally. A fixed informative gain prior changes the experiment
and is not covered by the zero-information conclusion below.

## Derivation strategy and map

1. Expand the continuous path exactly in its complete integer basis.
2. Compare equality at one point with the tangent space at that point.
3. Prove a full-law SP counterexample through exact gain reparameterization.
4. Lower-bound the full physical efficient information using its first moment,
   without replacing QPSK data by Gaussian data.
5. Quantify the tail of the operator tangent and state the limits of that proxy.

## Main derivation

### 1. Exact expansion and derivatives (identities)

Finite Fourier inversion gives

    U_l(delta) = sum_k D_N(delta-k) U_k.

Thus U_l(0)=U_0. At zero,

    a_0 := D_N'(0) = i pi (N-1)/N,
    a_k := D_N'(-k) = -2 pi i / [N(1-exp(-2 pi i k/N))], k!=0,
    |a_k|^2 = pi^2/[N^2 sin^2(pi k/N)].

To check the nonzero-index derivative directly, differentiate the finite sum
and use sum_n n z^n=-N/(1-z) for z^N=1, z!=1. No singular sinc formula is
differentiated numerically.

### 2. Zero approximation error can coexist with complete information loss

Fix the retained set M={0} and use the continuous but truncated family

    U_M(delta) = D_N(delta) U_0.

It equals the full physical channel exactly at delta=0. Nevertheless the
complete marginalized SP likelihood for this family depends on (h,delta) only
through beta=h D_N(delta):

    p_M(y|h,delta) = sum_d Pr(d) phi_sigma2(y-beta U_0(p+d)).

For any sufficiently small delta, D_N(delta)!=0. The nuisance transformation
h(delta)=beta/D_N(delta) keeps this entire density fixed. Hence Doppler is
locally unidentifiable and its efficient Fisher information is zero, for any
known pilot and any fixed data/code distribution. This is a full-density
statement, not a covariance-only or Gaussian-interference assertion.

Multiplying U_M by any nonzero scalar normalization depending on delta does
not repair the defect: that scalar is absorbed into h too. If the retained set
is chosen by a positive relative-energy threshold, only index zero survives in
an open neighborhood of delta=0, so this same conclusion holds there. A
fixed multi-atom support or a truly continuous physical operator is a different
model and must not be accused of this particular zero-information defect.

### 3. The complete physical SP experiment has positive information

Let a=U_l(nu)p, b=partial_nu U_l(nu)p and
v=sigma2+rho_d |h|^2. Exact QPSK moments give

    E[y]=h a,   Cov(y)=v I,   PseudoCov(y)=0.

Let s_eff be any Doppler score minus a real linear combination of the two
gain scores. Its derivative of the mean is h b-c a, for some arbitrary complex
c. The covariance Cauchy-Schwarz inequality applied to the centered real
observation vector gives

    E[s_eff^2] >= (2/v) ||h b-c a||^2.

Regularity follows from finite positive Gaussian mixtures. Minimizing the left
side over nuisance scores defines efficient Fisher information, and minimizing
the right side over c therefore proves

    I_eff(nu) >= (2 |h|^2/v) ||P_a^perp b||^2.                  (1)

This is a lower bound for the exact finite-alphabet experiment; covariance
dependence on gain does not invalidate it. It is not claimed to be its exact
information. If data are Gaussian, the right side is the efficient information
because covariance carries only gain-amplitude information and the Doppler
projection couples only to gain phase.

For t=C_l P_l A^H p and weights w_n=|t_n|^2/||p||^2, unitarity gives

    ||P_a^perp b||^2 = 4 pi^2 ||p||^2 Var_w(n/N).              (2)

Whenever the delayed time-domain pilot occupies at least two distinct samples,
(1) is strictly positive. It applies at nu=0 as well. Thus there exist actual
CPP/AFDM/SP experiments where truncation has exactly zero channel error but
zero efficient Doppler information, while the physical law has positive
information. A time-impulse pilot makes this lower bound zero; that does not
prove the finite-alphabet experiment itself is unidentifiable.

### 4. Tangent tail law (operator identity, not a SP Fisher ratio)

The Frobenius derivative after eliminating the complex scalar operator U_0 is

    R = U_l'(0)-a_0 U_0,
    ||R||_F^2/N = sum_{k!=0}|a_k|^2
                 = pi^2/3 (1-1/N^2).                       (3)

The last equality follows equivalently from the variance of n/N under uniform
weights or sum_{k=1}^{N-1} csc^2(pi k/N)=(N^2-1)/3.

For retained symmetric indices {-K,...,K}, with 2K<N, the fraction of this
operator tangent energy retained is exactly

    r_(N,K) = [6/(N^2-1)] sum_{k=1}^K csc^2(pi k/N).        (4)

For fixed K and N tending to infinity it is

    r_K = (6/pi^2) sum_{k=1}^K 1/k^2,
    6/[pi^2(K+1)] <= 1-r_K <= 6/(pi^2 K), K>=1.            (5)

The bounds use integrals of x^-2. They concern the limiting r_K, not a uniform
finite-N approximation when K scales with N. With only the two adjacent
sidebands retained, the limit is 6/pi^2, not one, even though the channel value
at the integer point was exact with no sideband at all.

### 5. Cost implication (conditional algorithmic observation)

For any source x, the exact physical derivative is obtained by multiplying its
time-domain path response by 2 pi i n/N. Given that response, the derivative
costs O(N) and no extra FFT if downstream computations remain in time. This
already exists in `Channel.regressors(derivative=True)` and the JET diagnostic.
It avoids the slow 1/K convergence of a tangent represented through integer
sidebands, but is not a measured whole-receiver speedup or a new algorithm.

### 6. Actual G0 pruning gives an open unidentifiable interval

The frozen `afdm_env.py:586-612` first normalizes the five coefficients
k=-2,...,2 and removes any coefficient whose squared magnitude is less than
eta=0.01 times the peak squared magnitude. Normalization cancels in this
comparison. The actual `dirichlet_alpha` at line435 uses D_N(m+delta), whereas
the full physical expansion in section1 uses D_N(delta-k). These signs must
not be identified. For N>=5 and |delta|<1/2, the largest G0 side coefficient
is at m=-sign(delta). Its amplitude ratio to the central coefficient is

    sin(pi |delta|/N) / sin(pi(1-|delta|)/N).

Solving ratio<sqrt(eta) gives the exact open interval

    |delta| < delta_star(N,eta),
    delta_star = (N/pi) atan[ sqrt(eta) sin(pi/N)
                            /(1+sqrt(eta) cos(pi/N)) ].      (6)

At zero use continuous extension. For eta=0.01 the limit is 1/11 bins.
Therefore this is a positive-width interval, not an isolated integer-grid
accident. Within it, all four side coefficients are pruned. Clipping at
k_cap can remove further coefficients and cannot invalidate this sufficient
central-only interval when the central integer lies inside the cap. At the
boundary the strict '<' pruning test retains the tied threshold coefficient
only if that slot has not already been removed by the k_cap clipping test.

For one path with a free complex gain, the pre-pruning energy normalization
and post-construction scalar Frobenius normalization cannot restore
identifiability: the final channel remains a scalar times one fixed atom.
Conditional on a fixed delay and central integer Doppler, for the actual
one-path generating law with uniform initial gain phase and
post-construction Frobenius normalization, even the gain-marginal G0 law is
independent of delta on this interval: its final coefficient has unit
magnitude and uniform phase. This last statement is a conditional one-path
restriction of the generator, not the P=8 production prior or a statement
after marginalizing Doppler-dependent delay/acceptance conditions. The G1 model reuses the G0
physical gains and must be evaluated with that exact reuse rule.

If one separately assumes uniform residual delta on [-1/2,1/2], the central-only
fraction would be 2 delta_star. The actual UWA generator does not have this
declared uniform law, so no prevalence percentage is asserted for production.
For multiple paths with free gains and fixed slots, every independently
central-only path has the same nuisance reparameterization; a generating gain
prior can add information and must be analyzed separately.

## Remarks and interpretation

The failure is geometric: fitting the value of a function at a point need not
fit its derivative. The unknown complex gain absorbs the sole surviving
derivative direction; fractional information lies in directions the energy
criterion removed. Increasing SNR or the number of observations cannot repair
an exactly redundant parameterization.

The full SP data law matters for (1). Unlike a known-data CRB, this argument
does not grant the receiver the transmitted word. It uses only exact first and
second moments to obtain a lower bound on the marginalized score norm.

## Boundaries and non-claims

- No arbitrary small Frobenius error to FER/information implication is claimed.
- Equations (3)-(5) are not the Fisher loss of an arbitrary fixed pilot; applying
  operators to that pilot and projecting out nuisance directions need not
  preserve Frobenius orthogonality.
- Free h differs from the actual G0-normalized generating gain distribution.
  A Bayesian prior can introduce information absent from the likelihood.
- Production native/F1 refinement already uses full physical paths; this note
  does not identify it as defective or propose replacing it by a weaker method.
- Old JET, full time-domain derivatives and standard off-grid linearization
  remain prior project assets. Rebranding them does not satisfy the new goal.

## Open risks / next discrimination

1. Independent proof review of the exact SP bound and the nuisance argument.
2. Check neighboring off-grid/OTFS/AFDM information analyses for the same
   pointwise-exact but information-singular statement.
3. Identify a real receiver decision that still relies on value-energy alone;
   if no consequential gap versus F1 exists, retain this as a modeling note and
   continue another mechanism. Numerical checks alone cannot establish value.
