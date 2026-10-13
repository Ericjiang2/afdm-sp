# Derivation Package: geometry-dependent normalized prior

## Target

Determine when the actual G0-normalized gain law admits finite observable
moments and legitimate geometry derivatives, and whether the Gaussian control
model's positive collision information transfers to it. The invariant object is
the **pushforward distribution of the observed waveform**, not the latent gain
covariance alone. This document owns PRIOR-01 and PRIOR-02.

## Status

COHERENT AFTER REFRAMING / EXTRA ASSUMPTION. The actual frozen simulator has an
open rank-one pruning plateau. Its G0 output is exactly uninformative about the
separation; its G1 output can have infinite second moment when the G0-normalized
gains are reused. Positive Gaussian-control information therefore does not
transfer universally. A regular positive-definite branch permits full
derivatives; a finite-rule derivative is not itself an efficient-information
proof.

## Assumptions and notation

Let z be uniform on the complex unit sphere in C^P, D a fixed positive diagonal
PDP matrix, W(theta) the frozen G0 physical-to-virtual-atom matrix, and
R=W^H W. Define u=D^(1/2)z, e=u^H R u, h=u/sqrt(e). The null event e=0 is
excluded; it has zero probability when rank R>0. If R=0, this probability model
is undefined. The original implementation's zero-matrix fallback is not used
as a mathematical prior extension.

B(theta) maps physical gains to a declared signal/output. For G0 atom
coefficients B=W; for same-delay zero-delay G1 time samples,
B_np=exp(2 pi i nu_p n/N). Noise is CN(0,sigma2 I), sigma2>0. In the blind moment
slice d consists of independent unit-power QPSK symbols and s=A^H d, with A
unitary and equal-modulus. A deterministic signal operator is independent of d.

The stored simulator PDP depends on the original pre-Doppler delay-index
sequence: `D_ii=exp(-alpha*(delay_index_i-1)*Ts)`. Thus a Doppler perturbation
with this latent sequence fixed has D'=0. Changing the latent sequence, its
acceptance branch, the rounded delay, or the velocity-to-delay ceiling is a
separate discrete change. These conditional calculations are not a derivative
of the unconditional production law conditioned on an observed geometry.

## Derivation strategy and map

1. Read the two normalizations in the frozen source and cancel the first radial
   normalization algebraically.
2. Classify regular branches and map the normalization nullspace.
3. Derive observable moments and their full fixed-base derivative.
4. Construct an exact zero-information counterexample and a divergent-moment
   counterexample before using numerical quadrature.
5. On regular branches compare positive product and independently scrambled
   positive Sobol rules. Retain unresolved near-singular cases.

## Main derivation

### 1. Actual normalization: identity and source trace

`afdm_env.py:generate_uwa_channel` draws independent Rayleigh amplitudes with
variance proportional to D and uniform phases, then divides by their Euclidean
norm. This is the angular distribution of D^(1/2)g for isotropic complex
Gaussian g. `generate_channel_matrix` builds each path's finite Dirichlet
weights, normalizes their full leakage-window energy, clips out-of-range atoms,
then prunes powers below `.01 * peak`. Only after summing paths does it normalize
the matrix Frobenius norm. In the legal orthogonal integer-atom basis,
`||H0||_F²/N=||W u||²=u^H R u`. The first radial normalization cancels, yielding
h above. Scaling all of D by one positive constant also cancels.

Before these virtual-weight operations, `generate_channel_matrix` clips the
physical Dopplers to the design cap. The adapter applies this same scalar cap
and records requested and actual Dopplers. The two mu=2 cases cross this
physical cap; their actual paths are (2-delta,2), so the requested mu/delta
labels are not the actual midpoint/half-spacing there. The regular derivative
case mu=.27, delta=.12 is strictly inside the cap.

`budgeted_support_diagnostics.py:physical_cluster_weights` is imported through
`production_prior.py`, preserving normalize-before-clip/prune order.
`prior.geometry` restricts to same zero delay and checks its Gram independently
against the actual `gen_h_daft` dense matrices. G1's
`supplement_g1.py:physical_observation` explicitly uses `params['g_i']` and
`GAIN_RULE='reuse_g0_physical_gains_without_rescaling'`; it does not renormalize
G1 power.

### 2. Smoothness and singularity: propositions

On an open branch with unchanged rounding, clipping, pruning and delay support,
D,W,B are smooth wherever their defining scalar functions are smooth. If
lambda_min(D^(1/2) R D^(1/2)) is uniformly positive on a parameter neighborhood,
h and all finite-order local derivatives are uniformly bounded on the compact
sphere. Every polynomial output moment is finite and can be differentiated
under the integral. Finite QPSK and positive Gaussian noise then give a smooth
mixture density with finite local score norm. More explicitly, augment the
observation with the parameter-independent latent (z,d). For a real geometry
parameter its conditional Gaussian score is
`2 Re[(y-m)^H m_dot]/sigma2`, with conditional second moment
`2 ||m_dot||²/sigma2`. Uniformly bounded m_dot makes the augmented experiment
DQM with finite information. Marginalization gives the observed score by
conditional expectation, so Jensen bounds its L2 norm by the augmented one.
This proves the needed regular-score condition without differentiating a
singular gain density. The raw moving-support gain law
need not have a Lebesgue density; differentiating `log pi_theta(h)` is not the
appropriate starting point. One differentiates the fixed-z pushforward.

At a pruning threshold a coefficient of nonzero magnitude is dropped. The map
W generally jumps. R, the prior and G0 output can jump too. At a rounding
half-integer the finite leakage window changes; clipping support can also
change. Physical Doppler clipping is continuous but generally has a derivative
kink. A derivative through any such boundary is not the regular-branch score.
The implementation records the first prune threshold and both sides; it does
not insert jitter, truncate gains, or smooth the simulator's rule.

Let 0<r=rank R<P. Since D is invertible, the quadratic form in the denominator
has rank r. Decompose an isotropic sphere direction into its r-dimensional
range and (P-r)-dimensional nullspace components. The squared range norm U has
Beta(r,P-r) density, behaving as a positive constant times U^(r-1) near zero;
its quadratic energy is bounded above and below by positive multiples of U.
The numerator ||D^(1/2)z|| is uniformly bounded above and below. Consequently

`E ||h||^(2k) < infinity iff k<r`.

The equality k=r diverges logarithmically. When r=P all gain moments are
bounded. For an observable B h, if `ker W subset ker B`, B factors through W
and `||B h|| <= ||B W^+||`, so all its moments are bounded even if gains have
infinite moments. If B is nonzero on ker W, a positive-measure set of nullspace
directions has nonzero numerator; the same threshold k<r applies. This proves
that finite G0 energy does not imply finite G1 energy.

### 3. Exact counterexample: an open zero-information G0 interval

Choose N=16, common delay zero, mu=0, k_leak=2, prune ratio .01, and
nu=(-delta,+delta). At delta=0 the only retained atom is k=0. By continuity of
the finite Dirichlet amplitudes, an open interval around zero retains exactly
this one atom for both paths. The registered source calculation locates the
first threshold. In fact the boundary has a closed form. Let c=pi/N and
a=sqrt(.01)=.1. Before rounding changes, the first retained side atom has
amplitude ratio `sin(c delta)/sin(c(1-delta))` to the peak. Its threshold is

`delta_star = (N/pi) atan[a sin(pi/N)/(1+a cos(pi/N))]`.

For `0 <= delta < delta_star`, all side atoms are strictly below the threshold;
normalizing the whole leakage window cancels in these ratios. At N=16 this is
approximately .09047461579. The endpoints are excluded from the open plateau
because the frozen comparison retains equality. This exact expression gives
an independent check of the registered numerical root. The mu=0 coordinate
slice includes negative Doppler, whereas the original UWA velocity sampler
uses nonnegative velocities. An integer shift to mu=1 preserves every weight
and Gram in this plateau, merely changing the retained atom from k=0 to k=1;
then both physical Dopplers are positive and below the cap. Thus the
zero-information construction does not depend on allowing negative velocity.
It still concerns a declared two-path conditional geometry, not the frequency
of such configurations under the original eight-path sampling distribution.

There W=e_0 a(delta)^T and R has rank one throughout the interval. Therefore

`W h = e_0 [a^T u / |a^T u|]`.

The phase in brackets is uniform by global circular symmetry of z, for every
positive D and every delta in this branch. Thus G0's random operator has the
same distribution for all delta, including zero. This remains true for any
independent data/prior/pilot/coding law, not only iid QPSK. The normalized G0
output distribution and every subsequent likelihood are identical. Both raw
and nuisance-efficient information for q=delta² are **exactly zero**. Its KL
is exactly zero throughout this branch; no R^(-1/4) separation law follows.
The noise variance and unknown signal scaling do not alter this conclusion.

For G1 and delta>0, the two physical exponentials are linearly independent
(for the stated small separations), so its map cannot annihilate the
one-dimensional nullspace of W. The second signal moment is infinite by the
previous proposition. At delta=0 both physical columns coincide and G1 does
annihilate the nullspace, so its output is bounded. This is a concrete
nonuniform singular limit. It invalidates the finite-moment four-order
information bound in this branch. It **does not prove that the noisy G1
likelihood or its Fisher information is undefined**: the distribution exists
almost surely, while its moment-based argument does not apply. We do not
assert a q-log-q density expansion without a separate proof.

### 4. Second/fourth moments: identities

For any declared response b_n^T h=v_n and n!=m, let
M_n=E|v_n|² and Q_nm=E|v_n|²|v_m|². Independent QPSK through the equal-modulus
unitary transform has E s_n s_m*=0 and
E|s_n|²|s_m|²=1-1/N. Provided the moments are integrable,

`E r_n r_m*=0 (n!=m),  E|r_n|²=M_n+sigma2`,

`E|r_n|²|r_m|²=(1-1/N) Q_nm+sigma2(M_n+M_m)+sigma2²`,

`E T_ab=(1-1/N)(Q_0a-Q_0b)+sigma2(M_a-M_b)`.

The second moment need not be a scalar multiple of I under the actual
geometry-dependent normalization. It is therefore invalid to transfer the
Gaussian control's zero second-order information. These exact identities
reduce the study to gain-only positive integrals; no new observations are
simulated. For P=2, write z=(sqrt(t),sqrt(1-t)e^(i phi)) modulo a global phase,
t uniform [0,1], phi uniform [0,2pi). Positive Gauss-Legendre x phase rules and
independent positive Sobol rules integrate the same angular measure.

The fixed-energy control uses `D^(1/2)z/||D^(1/2)z||`; equal-PDP Gaussian uses
CN(0,I/2). For the latter the radial second moment is 1 and radial fourth
moment is 3/2, multiplying the same angular second/fourth integrals exactly.
This separates radial Gaussianization and actual G0 normalization effects.

### 5. Complete derivative: identity

For a real parameter theta on a regular branch,

`u_dot = (1/2) D^(-1/2) D_dot z`,
`e_dot = 2 Re(u_dot^H R u) + u^H R_dot u`,
`h_dot = u_dot/sqrt(e) - h e_dot/(2e)`,
`v_dot = B_dot h + B h_dot`.

Thus `M_dot=E[2 Re(v* v_dot)]` and the fourth-moment derivative follows the
product rule. For delta>0, d/dq=(1/(2delta))d/ddelta. Both R_dot and B_dot must
be retained. `pushforward_jvp` also supports D_dot; the registered Doppler
slice fixes the original latent D, hence D_dot=0. The derivative study compares
this JVP against direct full pushforward differences and an explicitly labeled
frozen-prior ablation. It verifies stable active support at every stencil.

### 6. Nuisance-efficient information: conditional proposition and non-claim

Let F be any real finite-variance feature vector, J_q=d E F/dq, and J_eta the
Jacobian for the declared nuisance parameters. On the regular density branch,
choose any c with c^T J_eta=0. Center T=c^T(F-EF). Score identities give
E[T s_eta]=0 and E[T s_q]=c^T J_q. Therefore

`I_eff,qq >= (c^T J_q)^2 / Var(T)`.

A sufficient condition for positive efficient information is
`J_q not in col(J_eta)`, finite Var(T), and the regular score assumptions.
This is not equivalent to J_q!=0. The numerical study records the moment
Jacobian and its residual after projection against mu, log-PDP ratio,
log-signal-scale and noise variance. Quadrature/difference residuals alone do
not certify exact rank or a positive lower bound. No positive actual-prior
Fisher value is claimed. The G0 plateau is an exact zero-information example
even with every nuisance included; G1 in that branch has no usable finite
second/fourth-moment bound. These are completed negative mathematical results,
not unresolved attempts to prove the Gaussian coefficient universally.

## Remarks and interpretation

The latent gain singularity is a property of normalization by a possibly
rank-deficient **truncated** channel. Its consequences differ between that
same G0 operator and the separate untruncated G1 operator. Three old saved
geometries with distinct delays and positive Gram do not rule out this
same-delay counterexample. Known D is an oracle conditional analysis; its
common scaling cancels but its ratios generally do not.

## Boundaries and non-claims

No receiver/decoder or fresh production observation is run. No FER explanation,
unconditional production tail law, universal collision scaling, positive
actual-prior efficient information, or new literature priority follows.
Finite-node numbers in divergent cases are stored only to expose the failure
of moment quadrature, never as finite population moments. Cases failing the
predeclared refinement checks remain explicitly unresolved.

## Open risks and evidence

`prior_study.py:CONFIG` fixes all geometry, node, seed, threshold and derivative
choices before the registered execution. `test_prior.py` independently checks
real dense G0 Gram, open plateau, G1 nullspace failure, full D/R/B JVP, and
Gaussian radial identity. Registered `prior_v2` completed with 120 moment cases: all 114 finite-moment
cases passed the declared positive-rule refinement checks; six G1 cases have
provably infinite moments and retain their finite-node outputs without treating
them as population moments. Dense Gram error was at most 2.22e-16. The first
attempt remains an invalid partial due to late-loading OpenMP inventory; the
source correction and the physical Doppler cap correction are documented in
`results/afdm_higher_order_information/PRIOR_BRIDGE_RESULTS.md`. No registered
source or raw output was rewritten after execution.
