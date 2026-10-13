# Uncertain Doppler must preserve the unitary covariance law

## Target

Derive how continuous Doppler uncertainty acts on the SP signal, and determine
whether a first-order uncertain tangent is a statistically consistent model.
The proposed organizing object is the expected quadratic likelihood term used
by joint inference. No performance, new algorithm, or historical novelty is
claimed by these identities.

## Status

COHERENT AS STATED for the independent-factor uncertainty model below;
independent mathematical review pending. Its usefulness as a deployable method
versus full physical F1 remains open.

## Invariant object, assumptions, notation

Work first in the time domain after inverse DAFT. For a fixed delay and central
Doppler, let U0 be the exact unitary path with its CPP boundary factors. Let
T=diag(2*pi*n/N) and let delta be an uncertain real residual Doppler,
independent of the AF-domain data under a declared prior/cavity/mean-field
factor. The physical uncertain path is

    U_delta = exp(i delta T) U0.

Let x=p+d, m=E[x]=p+mu, V=Cov(x), P=E[(x-m)(x-m)^T], all expressed in the
appropriate input coordinates (with DAFT transforms when using AF-domain V).
In the time-domain output define a=U0 m, R=U0 V U0^H, and S=U0 P U0^T.
The gain h is fixed for this slice and nonzero; noise is independent proper
CN(0,sigma2 I). Unknown multi-path gains are treated separately below.

Delta has characteristic function chi(t)=E exp(i t delta). Gaussian delta is
an illustrative mathematical law; it is not the actual production Doppler
prior. In particular, a posterior fitted from y must not be reintroduced as
an independent measurement or prior.

## Derivation strategy and map

1. Derive exact first/second moments by entrywise phase multiplication.
2. Use unitary energy conservation to test a tangent approximation.
3. Recover the missing curvature and distinguish pilot uncertainty from data
   covariance transport.
4. Generalize to path pairs and identify the expected-likelihood computation.
5. State what remains to be designed before an inference prototype exists.

## Main derivation

### 1. Exact characteristic-function transport (identity)

Writing t_n=2*pi*n/N,

    E[U_delta x]_n = chi(t_n) a_n,
    E[(U_delta x)(U_delta x)^H]_(n,m)
       = chi(t_n-t_m) [R_(n,m)+a_n conj(a_m)],                (1)
    E[(U_delta x)(U_delta x)^T]_(n,m)
       = chi(t_n+t_m) [S_(n,m)+a_n a_m].                     (2)

Centering by the mean outer product gives covariance and pseudo-covariance.
For delta~N(0,tau2), chi(t)=exp(-tau2*t^2/2). Thus the covariance transport is
a Hadamard product with a positive-semidefinite Gaussian difference kernel.
Its diagonal is exactly one; it preserves trace and positive semidefiniteness.
These are standard characteristic-function/random-unitary facts.

If the data factor is isotropic, V=rho_d I, then R=rho_d I and

    E[exp(i delta T) R exp(-i delta T)] = rho_d I              (3)

for ANY delta distribution. Unknown data do not acquire extra second-order
power solely because a unitary single-path Doppler is uncertain. The known
pilot/soft mean does contribute Cov(exp(i delta T)a). Finite QPSK has the same
identity (3), although its higher-order distribution still depends on delta.
For proper Gaussian isotropic data the rotated data are actually independent
of delta; that stronger distributional statement is not asserted for QPSK.

### 2. A naive random tangent violates (3) at its own leading order

Assume E[delta]=0, E[delta^2]=tau2. The first-order path

    U_tan = (I+i delta T) U0

would predict, for zero-mean data alone,

    E[U_tan V U_tan^H] = R + tau2 T R T.                     (4)

For R=rho_d I this adds rho_d*tau2*T^2, a generally high-rank positive term,
despite the exact covariance being rho_d I. Its added trace is
rho_d*tau2*tr(T^2)>0. This is a modeling error at order tau2, the same order as
the uncertainty correction one hoped to capture. Small uncertainty does not
make (4) a valid second-order expansion of the physical covariance.

The high rank in (4) comes from multiplying the unknown data by the uncertain
real parameter; retaining only the rank-one term (T a)(T a)^H also omits that
product. Neither observation alone licenses a covariance model: the exact
second-order curvature must be included before deciding the net correction.

### 3. Curvature restores the conservation law (expansion)

Retain the -delta^2 T^2/2 term of the exponential on BOTH sides. To second order,

    E[U_delta V U_delta^H]
      = R + tau2 [T R T - (T^2 R + R T^2)/2] + remainder
      = R - (tau2/2) [T,[T,R]] + remainder.                  (5)

The displayed correction has trace zero. For R=rho_d I it vanishes exactly.
For a centered Gaussian delta, the full exact map is

    exp(-(tau2/2) ad_T^2) R,
    ad_T(R)=[T,R],                                           (6)

as is seen entrywise from (1). For a bounded centered delta with a finite third
absolute moment, Taylor expansion has an O(E|delta|^3 ||T||^3 ||R||) remainder
in any fixed finite-dimensional compatible norm, with an appropriate constant;
no tau2-only remainder is claimed for arbitrary heavy-tailed distributions.

Mean subtraction also matters. In the Gaussian small-tau case,

    Cov(exp(i delta T)a) = tau2 (T a)(T a)^H + O(tau2^2),
    PseudoCov(exp(i delta T)a) = -tau2 (T a)(T a)^T + O(tau2^2).

This rank-one improper component belongs to the deterministic pilot/soft mean.
The transported data covariance must be added using (1), not by independently
adding the positive tangent term (4). Changing the time origin moves common
phase into the gain, so the joint gain/offset law must be pushed forward.
For an independent circularly symmetric gain prior, multiplication by the
offset-dependent unit phase preserves both that prior and independence;
this is an important exception. A phase-sensitive prior need not be preserved.
A fixed deterministic gain also needs its corresponding reparameterization.

### 4. Exact multi-path expected quadratic term

Assume the entire offset vector is jointly independent of x in this declared
factor model; pairwise marginal independence alone is insufficient. For fixed
h_i and fixed central path U_i, let a_i=U_i m and
R_ij=U_i V U_j^H. Define the joint characteristic function

    chi_ij(s,t)=E exp(i s delta_i + i t delta_j).

Then every cross-path second moment is obtained by

    E[(D_delta_i U_i x)(D_delta_j U_j x)^H]_(n,m)
       = chi_ij(t_n,-t_m) [R_ij(n,m)+a_i(n) conj(a_j(m))].    (7)

Multiply by h_i conj(h_j), sum i,j, and include independent noise. For
independent offsets i!=j the factor separates as chi_i(t_n) chi_j(-t_m).
For centered correlated Gaussian offsets it is

    exp(-[s^2 Sigma_ii + 2 s t Sigma_ij + t^2 Sigma_jj]/2).

Nonzero means add the factor exp(i[s E(delta_i)+t E(delta_j)]).

For i=j, (7) always uses the SAME random delta_i twice, hence chi_i(t_n-t_m).
Replacing it by chi_i(t_n)chi_i(-t_m) invents independent phase draws on the two
sides and loses energy conservation. Independent path offsets do not mean
independent copies of one path offset at different samples.

In a mean-field variational model q(x)q(h)q(delta) the expected negative
log-likelihood quadratic is exactly

    E||y-H_delta x||^2
      = ||y||^2 - 2 Re[y^H E(H_delta)m]
        + tr(E[H_delta(V+mm^H)H_delta^H]).                   (8)

Gain second moments E[h_i conj(h_j)] replace fixed products when that gain
factor is independent of delta. If q(h,delta,x) is coupled, (8)'s compact
factorized evaluation is not exact; mixed moments must be retained. This is
an explicit approximation boundary, not an assertion that the true posterior
factorizes.

### 5. A computational avenue, not an implemented method

Equation (8) needs the trace of (7), not its full N-by-N matrix. Its pairwise
phase factor on that trace is E exp(i t_n(delta_i-delta_j)). This suggests an
O(N P^2) physical-path contraction once the diagonal cross-path source moments
and characteristic-function values are available. For AF-diagonal q(x), the
cross moments use one FFT(v) and exact CPP/delay phases, so moment evaluation
costs O(N log N + N P^2) if each needed characteristic-function value is
analytically O(1). For arbitrary q(delta), its construction and characteristic
function integration cost must be added. No dense uncertainty covariance is
required for this trace. A source-matched implementation is still owed.

The potential method is variational continuous-geometry inference using exact
unitary moment transport, with a Dirac-geometry control and the same priors,
observations and decoder budget. This differs from assigning independent
complex gains to tangent columns. It also has close antecedents in off-grid
variational Bayes and expectation propagation; no firstness is claimed.

## Remarks and interpretation

Curvature is not an optional higher-order refinement when the reported quantity
is a variance: the first useful variance correction is already second order.
This supplies a concrete scientific test for a proposed uncertain-Doppler
model before investing in a large experiment. SP is consequential because the
known pilot/soft mean and unresolved data respond differently at second order.

## Boundaries and non-claims

- Current native/F1 is not alleged to implement the invalid random Doppler
  tangent (4); native's joint tangent study concerns gain/data and is distinct.
- Isotropic single-path covariance invariance does not extend automatically
  to multipath, nonuniform soft symbol variances, or the full QPSK density.
- A scalar iid gain working prior is not the actual normalized production prior.
- Full Gaussian covariance transport is not a complete bit-message algorithm.
- Positive approximate kernels, new inference rules, convergence, and complete
  receiver performance/cost must be derived, implemented and verified separately.

## Open risks

Existing off-grid Bayesian literature may already contain the entire useful
mechanism. A strong point-geometry F1 or real-parameter Bayesian baseline may
eliminate the claimed performance-cost margin. If so, keep the conservation
identity as a diagnostic and continue; do not equate it with the active goal.
