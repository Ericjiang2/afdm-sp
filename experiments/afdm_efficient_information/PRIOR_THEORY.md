# Derivation Package — actual prior, geometry and efficient information

## Target

Classify the actual G0-normalized two-path prior, including its **PDP-marginal
observed likelihood**, and construct complete scores for separation delta and
nuisance eta=(mu,log(tau),log(sigma²)). Determine where q=delta² is legitimate.
The implementation is `prior_likelihood.py`; frozen stage inputs are in
`prior_study.py`. This package owns GEOM-01 and PRIOR-INFO-01.

## Status

COHERENT AFTER REFRAMING / EXTRA ASSUMPTION. The target is a fully specified
**two-path conditional slice of the production sampling rules**, not the full
eight-path production population. Conditional latent-PDP oracle, actual
PDP-marginal law and equal-PDP control remain separate. Exact zero and
nonregular branches are analytic results; positive interior information from
finite quadrature and finite samples is explicitly numerical evidence.

## Invariant Object

The distribution of the observed time vector

`Y=sqrt(tau) diag(B(theta)h) A^H X + epsilon`,

where X is independent uniform QPSK, epsilon~CN(0,sigma²I), and
`h=D^(1/2)z / sqrt(z^H D^(1/2)R(theta)D^(1/2)z)`, R=W^H W.
G0 has B equal to its truncated integer-atom response; G1 uses physical
exponentials with the **same** G0-normalized gains. This is a pushforward law;
there is no assumed Lebesgue density for h on a moving surface.

## Assumptions

- P=2; common rounded delay zero is known. N=4 for full finite-QPSK likelihood;
  larger N supports geometry and sampling. N4 uses k_max=1 so integer atoms do
  not alias; N>=5 uses the frozen k_max=2. Chirps c1=2.5/N,c2=.1/N².
- Frozen weight order is physical Doppler clipping, full leakage-window energy
  normalization, virtual-support clipping, relative power pruning, and finally
  whole-G0 Frobenius normalization. Nothing is jittered or smoothed.
- For the actual PDP marginal, Dopplers are the nonnegative unordered pair
  {mu-delta,mu+delta}, strictly below the physical cap on differentiated
  branches. Negative-Doppler examples use a separately labeled conditional
  model. Inputs are independent of latent channel variables.
- The small slice uses frozen UWA primitive values fs=8000, fc=12000,
  delta_f=15, mean exponential increment .8 ms, spread 10 ms and attenuation
  20 dB. It is not a replay of a larger-N saved configuration with another fs.
- Smooth-branch derivatives hold delay/PDP acceptance indices, rounding,
  clipping state and pruning support fixed. Positive noise gives full support,
  but does not remove parameter kinks, rank singularities or conditional-law
  jumps.

## Notation

J1,J2 are positive integer delay increments before Doppler correction;
I1=J1,I2=J1+J2. D contains the exponential attenuation before gain normalization.
W maps physical gains to retained orthogonal integer atoms; B maps to time
response. nu1=mu-delta, nu2=mu+delta. A is the unitary DAFT. tau scales the
G0-normalized signal, so it is total mean G0 signal power per sample; under G1
it is the same physical gain scale, **not** a renormalized G1 total power.
The estimated information always states this nuisance parameterization.

## Derivation Strategy

Trace the frozen primitive distribution; condition and integrate PDP exactly;
replace radial Gaussian draws by the equivalent angular density; integrate
one global phase analytically; retain positive CP1 quadrature for the remaining
likelihood integral. Derive all scores before projecting nuisance. Use an
independent analytic covariance identity to expose collision nonregularity that
finite angular quadrature can obscure.

## Derivation Map

1. Frozen ceiled exponential increments -> finite conditional PDP mixture.
2. Gain normalization identity -> ACG angular density / fixed-base pushforward.
3. QPSK orbit and global-phase identities -> positive numerical likelihood.
4. Full pushforward JVP -> observed score -> independent nuisance projection.
5. Rank-one platform / nullspace leakage / positive-definite branch / thresholds
   -> separate exact, numerical and unresolved classifications.
6. Exact normalized covariance -> q log(1/q) collision obstruction.

## Main Derivation

### 1. Actual PDP marginal: exact conditional probability calculation

Source: frozen `afdm_sp_joint_unrolled/afdm_env.py`, `generate_uwa_channel`,
lines 312–340: exponential increments, ceiling, cumulative sums, PDP,
Rayleigh amplitudes, uniform phases, iid absolute-Gaussian velocities, and
Doppler-corrected ceilings. Lines 343–362 define acceptance and final clipping.
These source bytes are included through `production_diagnostic.source_paths()`.

With Ts=1/fs and a=exp(-Ts/tau_mean),

`Pr(J=j)=(1-a)a^(j-1), j>=1`,
`D2/D1=exp(-beta J2), beta=log(10) att_dB Ts/(10 tau_spread)`.

Let K be the largest corrected one-based delay index for which the actual
`np.round((K-1)Ts/delay_resolution)` is zero. The two physical Doppler scaling
factors are `v_i/c_sound = nu_i fs/(fc N)`. Hence under a specified assignment
of Dopplers to the two **delay-ordered** labels,

`L_i=floor[K(1+nu_i fs/(fc N))]`,
`E0={J1<=L1, J1+J2<=L2}`.

For each j=J2 and M=min(L1,L2-j)>=1, summing all J1 gives positive mass

`m_j=(1-a)a^(j-1)(1-a^M)`.

Conditional on an unordered Doppler pair the two assignments have equal prior
weights: iid velocity densities give the same product under permutation.
Multiply each m_j by 1/2 **before** conditioning. The assignments generally
do not have equal posterior weights, since E0 has assignment-dependent
probability. Normalize the combined masses; assign D=(1,exp(-beta j)) or its
reversal in ascending-Doppler coordinates. Common scaling of D cancels.

This event has positive probability whenever at least one M>=1; every retained
term is strictly positive. It is a finite exact sum, not truncated exponential
integration. Conditioning on exact continuous Dopplers means a regular
conditional distribution (not claiming that an exact velocity event has
positive mass); E0 has positive conditional probability. The final all-rejected
fallback cannot yield two rounded zero delays: at least one rejected corrected
delay is clipped to the far support endpoint, which has nonzero rounded delay.
Accepted-attempt geometric factors are constant in the selected latent draw and
cancel in this conditional law. This justifies excluding that fallback **for
this event**, not deleting it from the full generator.

A fixed unequal D is not exchangeable. Swapping delta changes its association
with columns and can change the likelihood. Swapping both columns and D leaves
it invariant. The actual mixture over both assignments is exchangeable as an
unordered physical model. Its dependence on floor-valued L_i can still jump at
conditional-law boundaries. Symmetry alone says nothing about q regularity.

### 2. Two equivalent angular representations: identities

The frozen Rayleigh-plus-phase gain vector is proportional to D^(1/2)g for
isotropic complex Gaussian g. Both its first Euclidean normalization and g's
radial part cancel in the final G0 normalization. This gives the fixed sphere
pushforward in the invariant object.

Alternatively let v=D^(1/2)g/||D^(1/2)g||. On CP1, write
`v=(sqrt(t),sqrt(1-t) exp(i phi))` modulo independent uniform global phase.
Relative to uniform t in [0,1] and phi in [0,2pi), its exact ACG density is

`f_D(t)=D1 D2/[D2 t+D1(1-t)]²`.

To derive it, the complex two-dimensional Gaussian density is proportional
to det(D)^(-1) exp(-r² v^H D^(-1)v), with polar volume r³dr.
Integrating radius gives det(D)^(-1)(v^H D^(-1)v)^(-2), which becomes
the stated formula after substituting t. Its integral over uniform t is one.
The actual PDP marginal has `f(t)=sum_j p_j f_Dj(t)`, an exact positive sum.
Now h=v/sqrt(v^H R v). This angular change of variables does not replace the
prior with a uniform sphere: the complete f(t) is retained. `sample` instead
draws exact discrete PDP and continuous Gaussian base variables; it never draws
from likelihood nodes. Independent stochastic validation therefore targets the
original slice, not its quadrature discretization.

### 3. Global-phase and finite-QPSK elimination: identities plus approximation

There are 4^(N-1) global-QPSK phase orbits. Fix the first QPSK symbol to its
first alphabet value; the independent uniform gain phase absorbs all four
members, giving exactly equal orbit weights. For one non-global-phase mean
m=sqrt(tau)diag(Bh)A^H x and c=y^H m,

`p(y|m modulo phase)=(pi sigma²)^(-N)`
`  *exp[-(||y||²+||m||²)/sigma²] I0(2|c|/sigma²)`.

The implementation uses scaled I0/I1 and logsumexp for stability. An independent
128-point explicit phase integral checks this identity on a fixed small case.
Remaining CP1 integration uses positive Gauss–Legendre×phase and independently
scrambled positive Sobol rules. Quadrature mass error is saved before weights
are normalized. These normalized finite sums are numerical references, never
called exact actual-prior Fisher information.

### 4. Complete derivative and scores: identities on declared smooth branches

For fixed base z and any real parameter,

`u=D^(1/2)z; e=u^H R u`,
`u'=1/2 D^(-1/2)D'z`,
`e'=2 Re(u'^H R u)+u^H R'u`,
`h'=u'/sqrt(e)-h e'/(2e)`,
`(Bh)'=B'h+Bh'`.

The general JVP test varies D,R,B simultaneously. On this Doppler slice each
latent D is fixed, and the finite mixture weights are constant within one
L_i branch, hence D'=0. In angular coordinates f is then fixed and the same
JVP uses D=I while retaining f as the quadrature weight. Changing a delay/PDP
branch is not an omitted small D' term: it changes a discrete conditional law.

Let r=I1(kappa)/I0(kappa), kappa=2|c|/sigma² and c'=y^H m'. For delta,mu,
log(tau), the phase-integrated component score is

`[-2 Re(m^H m')+2r Re(c* c')/|c|]/sigma²`,

with the c=0 continuous limit zero for the second term. For log(tau), m'=m/2.
The log(sigma²) component score is

`-N+(||y||²+||m||²)/sigma²-r kappa`.

Posterior averaging over all CP1/PDP/QPSK components gives the observed score.
Geometry derivatives differentiate both R and B, using centered stencils that
must preserve the full active-support/clip/PDP signature. Independent direct
log-likelihood finite differences check all four score columns and three
stencil sizes. At delta>0, s_q=s_delta/(2delta); this chain rule is never used
as a collision-limit proof.

For positive-definite R uniformly on a neighborhood, positive bounded finite
PDP mixture and fixed support, the pushforward and its derivatives are bounded
on the sphere. The augmented Gaussian experiment is DQM with finite complete
score norm; conditional expectation gives the observed finite score. This is
the legitimate interior information branch.

### 5. Efficient information and numerical decision rule

The mathematical object is `s_eff=s_delta-Pi_span(s_eta)s_delta` and
`I_eff=E[s_eff²]`. Singular nuisance directions are removed by the Moore–Penrose
projection on their span; no ridge/jitter is introduced. Numerical rank and
singular values are saved. Projection coefficients are fitted on the first 128
independent frames and evaluated on the other 128; all observations come from
the exact continuous sampler. Same-sample training information is also saved
but not used as an independent validation claim.

An independently fitted projection may retain estimation error, so a positive
finite-sample residual is not a proof of population I_eff>0. The study reports
`numerically_positive_not_certified` only after all preset node, independent
rule, every registered score-step comparison, direct finite-difference and
effective-information checks pass and the held-out value
exceeds four batch standard errors. Failed convergence is retained as
`unresolved_numerical_information`. The exact platform has `exact_zero`
regardless of quadrature or sampling. No quadrature estimate overrides an
analytic singular/moment classification.

### 6. Exact zero platform and G1 singular branch: propositions

For one retained common integer atom, W=e_k a(delta)^T. Then
`Wh=e_k (a^T u)/|a^T u|`; global circular symmetry makes the remaining phase
uniform for every positive D. Mixing D and conditioning weights changes
nothing. Thus the entire G0 observation law, for any independent input law,
is independent of delta and of local mu inside that atom plateau. Its raw and
nuisance-efficient separation information are exactly zero.

For center at an integer and prune power ratio .01, the first side atom is
retained at

`delta_star=N/pi atan[.1 sin(pi/N)/(1+.1 cos(pi/N))]`.

Equality is retained; the zero platform is open at this endpoint. The registered
geometry stage evaluates both sides and independent dense G0 Grams for N4,N8,
N16. Physical cap, rounding and clipping are recorded separately.

If rank R=r<P, normalized gain moments satisfy E||h||^(2k)<infinity iff k<r.
For Bh, all moments are bounded if ker W is annihilated by B; otherwise the
same threshold applies. G0 annihilates the nullspace. G1 at nonzero separation
on the common-atom plateau does not, so its second moment diverges for P=2,r=1.
The almost-sure noisy G1 law still exists. Divergent second moment is not a
proof of infinite Fisher information; this study refuses a regular-score claim
on that singular branch instead of manufacturing one with finite nodes.

### 7. Non-platform collision: analytic q log(1/q) obstruction

There is an independent exact covariance identity. Set
C=D^(1/2)R D^(1/2), eigenvalues 0<lambda_small<=lambda_large, rho their ratio.
After rotating isotropic Gaussian gains, squared moduli are independent Exp(1).
The expected normalized energy in the small mode is exactly

`e_small=rho*(rho-1-log(rho))/(1-rho)²`,

with limit 1/2 at rho=1. The response eigenvectors multiplied by the square
root powers and divided by sqrt(lambda) give the corresponding normalized
operator directions. Weight their outer products by (e_small,1-e_small).
This computes actual normalized covariance; it does not assert Gaussian output.
The rank-one limit is integrated on its support. A tiny numerical rank cutoff
is explicitly stated in code; no eigenvalue is moved.

On a smooth collision branch write w=B(mu,0)[:,1], w_mu its derivative, and
b=w_mu-w(w^H w_mu)/(w^H w). Let a²=||w||²/N and b²=||b||²/N. If b!=0,

`rho=q [4D1D2/(D1+D2)²] b²/a²+O(delta³)`.

For symmetric path labels, the signal-power vector consequently has

`M(delta)-M(0)=K q log(1/q)+O(q)`,
`K=E_D[4D1D2/(D1+D2)²] (b²/a²)`
`  *[|b|²/b²-|w|²/a²]`.

For fixed unequal D this is the **even part**; odd O(delta) terms can remain.
The formula follows by inserting the eigenvalue expansion in the exact energy
identity: large-mode eigenvectors vary analytically, while the small-mode
weight contributes the only leading logarithm. The marginal PDP weights must
remain on the same L_i branch. The registered sequence and analytic covariance
save the predicted K, finite-delta ratios and any failure to reach asymptotia.
Every point records active support, physical clipping, rounded Dopplers and
PDP limits, together with equality to the collision discrete branch. The
predeclared last-three-point log-slope fit is allowed only when all three
share that branch; a changed point stays in the output and marks the fit
unqualified. The expected rank change at collision is not a discrete-branch
mismatch, and no replacement tail is selected.

If any K_n is nonzero in the symmetric model, there is no finite q-DQM score
at the collision. Here is a direct observable proof: F(Y)=|Y_n|² has uniformly
bounded second moment since G0 energy is fixed, finite QPSK is bounded and
noise is Gaussian. Cauchy–Schwarz gives

`|E_q F-E_0 F| <= [2(E_q F²+E_0 F²)]^(1/2) ||sqrt(p_q)-sqrt(p_0)||_2`.

The nonzero q log(1/q) difference requires Hellinger distance to be at least a
constant times q log(1/q), contradicting the O(q) distance required by a finite
q-DQM derivative. Positive Gaussian noise cannot remove this obstruction.
If K=0 this test is inconclusive; it does not establish q regularity. The exact
single-atom plateau has b=0 and remains the separate zero-information theorem.
We do not infer the delta-coordinate DQM limit or a universal repeat-sample
separation rate from this q obstruction.

## Remarks and Interpretation

The actual-prior information problem is not the Gaussian control problem.
Actual G0 has both exact zero intervals and non-platform q-nonregular collision
branches, while positive-definite separated points admit complete regular
scores. Unknown total scale/noise must be projected even if the G0 channel is
Frobenius-normalized. PDP marginalization can restore permutation symmetry
without restoring q regularity or erasing geometry acceptance boundaries.

## Boundaries and Non-Claims

No full eight-path unconditional law, production receiver/decoder performance,
confirmed novelty or universal positive information follows. Equal-PDP and
fixed unequal-PDP columns are oracle conditionals. The actual marginal keeps
known common delay and public candidate geometry as model parameters; it does
not make true nuisance or realized latent PDP available to deployed features.
Small likelihood references carry node convergence evidence, independent exact
sampler validation and retained failures. Unresolved nodes are not silently
replaced with Gaussian likelihoods.

## Open Risks

Near-singular CP1 likelihood integrals may converge slowly despite analytic
second moments. The registered study preserves these cases. A full
multi-delay/multipath law has additional discrete conditioning and cannot be
claimed from this slice. G1 rank-deficient Fisher behavior needs its own
heavy-tail density analysis; divergent moments alone decide only the failure
of the finite-moment route. Source and raw hashes, costs, classifications and
registered sample counts are stored in each immutable stage.
