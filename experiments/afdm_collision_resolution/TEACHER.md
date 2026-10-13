# Actual collision log-tangent teacher

## Scope and prerequisite

This module uses the same frozen G0 normalization and clipped/pruned Dirichlet
geometry as `afdm_efficient_information.prior_likelihood`. The declared slice is
N=4, two physical paths, common rounded delay zero, independent uniform DAFT-domain
QPSK, positive circular Gaussian noise, and an actual PDP mixture conditional on
that slice. It is not the full eight-path production population. The public
collision point is `(mu,tau,sigma2)`; observation evaluation accepts only Y.
A scientific run requires the density expansion and nuisance conditions in
`DENSITY_THEORY.md` and `NUISANCE_THEORY.md` to be established before admission.

Let q=delta^2 and r=q log(1/q). At a fixed nonplatform collision branch let w be
the common G0 time-response vector, b=w_mu-w(w^H w_mu)/(w^H w), u0=w/||w|| and
u1=b/||b||. The model retains the conditional latent PDP and both path labels.
At collision the two integer PDP limits coincide, so the label mixture is
exchange symmetric. Its leading coefficient is

    kappa = E[4 D1 D2/(D1+D2)^2] ||b||^2/||w||^2.

`collision_geometry` computes w_mu analytically. It writes the Dirichlet kernel
as a finite Fourier sum, differentiates its full pre-pruning normalization, and
uses the existing frozen physical mask. The reproduced weights must match the
existing generator. All declared finite-difference stencils must retain the
physical/PDP signature. Platforms, clipping and stencil boundary crossings are
rejected; no eigenvalue or matrix is jittered. The unit-vector derivative keeps
the full normalization derivative, including a possible unobservable phase.

## Observation likelihood and score

For each of the 4^(N-1)=64 QPSK global-phase orbit representatives in time
coordinates, define m0=sqrt(tau N) u0 .* x and m1=sqrt(tau N) u1 .* x. Integrate
the common uniform phase exactly. With c=y^H m0, d=y^H m1, e=m0^H m1,
z=2|c|/sigma2 and rho=I1(z)/I0(z), its log likelihood is

    -N log(pi sigma2) - (||y||^2+||m0||^2)/sigma2 + log I0(z).

Scaled Bessel functions avoid overflow. The component tangent divided by its
component density is

    (|d|^2+|e|^2-2 rho Re[d conj(e) conj(c)/|c|])/sigma2^2
    - ||m1||^2/sigma2 - (rho |c|-||m0||^2)/sigma2.

The c=0 expression uses its continuous zero limit. The posterior QPSK average,
multiplied by kappa, is s_r. The other score columns are mu, log_tau and
log_sigma2; their derivatives use the same posterior and exact phase integrals.
The teacher is exact in its finite-symbol/phase elimination, up to floating
arithmetic, conditional on the proved asymptotic density tangent. It is not a
finite-delta likelihood and does not assume known true nuisance at deployment.

## Exact algebraic power moments

For k in N^4, conditional Gaussian independence gives

    E prod_i |Y_i|^(2 k_i)
      = prod_i sum_(l=0)^k_i binom(k_i,l)^2 l! sigma2^l |m0_i|^(2(k_i-l)).

Average these finite expressions over all QPSK orbit representatives. Each
noiseless monomial f=prod_i m_i^a_i conj(m_i)^a_i has r derivative

    kappa [sum_ij m1_i conj(m1_j) d_m_i d_conj(m_j) f - |a| f].

The mu derivative is its directional derivative along m_mu; the log_tau and
log_sigma2 derivatives count signal and noise degrees, respectively. Polynomial
powers are evaluated without division, so zeros in m0 are legal. Degree-one
powers plus all degree-two power products make 14 fixed features. Covariances
use exact Gaussian/symbol identities up to total power degree four. These are
classical moments, not a novelty claim. Floating evaluation is distinguished
from an interval or symbolic positivity certificate.

## Actual sampling and qualification

`sample` first samples the actual conditioned PDP component, independent complex
Gaussian gains, and their original Gram normalization. At collision, the
response equals sqrt(N) u0 times a uniform phase: the complex linear gain sum is
circular Gaussian for every positive PDP and its magnitude cancels exactly.
The phase is independent of independent QPSK and noise. Thus the analytical
rank-one density equals the physical latent sampler; no quadrature nodes are
sampled. Saved latent arrays are external replay evidence only.

Deterministic qualifications include all QPSK orbit means with a 256-point
uniform-phase sum compared with the Bessel formula on three fixed observations,
three-step nuisance density finite differences, actual generator bitwise
sampling parity on eight labelled fixtures, analytic geometry derivatives,
constant-moment zero derivative, explicit first moments, polynomial tangent
phase differentiation including zero means, covariance PSD, and invalid branch
rejection. These fixtures are not scientific observations or evidence of
positive Fisher information. The constant derivative and conditional Gaussian
polynomial identities prove zero expected tangent; finite-sample score means
are reported separately with batch standard errors.
