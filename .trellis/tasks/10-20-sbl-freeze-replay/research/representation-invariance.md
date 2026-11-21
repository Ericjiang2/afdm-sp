# Derivation Package: uniform duplicate-atom representation

Date: 2026-10-21. Internal derivation, not a paper claim.

## Target
Establish physical-channel/working-prior equivalence under uniform duplication and derive the native first point-gain update.

## Status
**COHERENT AS STATED**: independent code/algebra review and both predetermined numerical cases passed (2026-10-21).

## Invariant Object

The invariant object is the physical channel operator and its induced working Gaussian prior, not the coordinate vector or its Euclidean norm. This is the detector's assumed prior; it does not assert that the true physical generator is Gaussian. Establish an exact duplicate representation, fixed-detector invariance in exact arithmetic, and the first point-gain update under the frozen native scalar approximation. This does not claim a causal explanation of the observed scalar/full Gamma ranking.

## Assumptions
Noise, symbol prior, observation, pilot and damping are identical; every original atom is duplicated uniformly k times and all helpers stay frozen. The numerical probe uses k=2. No new observational information enters either representation.

## Notation
Let P be the existing atom count. Write H(h)=sum_p h_p U_p and B(x)=[U_1 x,...,U_P x] in the frozen detector's time-domain observation coordinates. Noise, symbol prior, observation, pilot and damping are identical. Its gain prior is CN(0,tau I_P), tau=1/P; observed h0 is initialization only. Symbol truth is never a receiver input. Uniformly duplicate EVERY atom k times (probe k=2); no partial duplication or new normalization. Define D=I_P kron [1,...,1], size P by kP. The new atoms have B'(x)=B(x)D, initialization g0=D^H h0/k, and default prior tau'=1/(kP)=tau/k. Exact duplicate delays/Dopplers are allowed by Channel; no merge occurs.

## Derivation Strategy
Push forward the duplicate prior, then compare exact physical inference with the frozen approximate coordinate update before histories diverge.

## Derivation Map

1. Exact identity: Dg0=h0, so H'(g0)=H(h0).
2. Exact Gaussian pushforward: DD^H=k I_P, so Dg~CN(0,tau I_P) under g~CN(0,tau/k I_(kP)).
3. Exact posterior statement: the likelihood depends on g only through Dg. Marginalizing duplicate contrast coordinates yields the original posterior on symbols and aggregate gains. Hence the comparison is not a changed physical prior.
4. Native fixed mode: vh=0, h frozen; all symbol/residual/damping updates depend on the fixed physical operator, so exact-arithmetic symbol outputs are invariant. Tau only enters a gain update which fixed mode never applies.
5. Native point mode: derive the first applied gain update before histories diverge. Later non-gain states and gains can coevolve; do not extend common-state algebra to every later step automatically.

## Main Derivation

First-update identity, including the existing Onsager subtraction:

Notation at the first iteration: x0=pilot+mu0 from the original check prior; vx=mean(v0); B=B(x0); h=h0; s is the common residual message AFTER its first damping update; sv its precision. The damping memories initially have xb=x0, hb=h, Bb=B. Put

- q=1/max(sv ||x0||^2,1e-12), the code's vq (same for either representation).
- a=B^H s, a P-vector.
- d=hb sv n vx, a P-vector.

The code updates rh=h+q(a-d), then h1=tau/(tau+q) rh. Its symbol marginal is evaluated BEFORE applying h1, so first symbol outputs remain identical under point duplication.

For k duplicates, hb' has k copies of hb/k and B' has k repeated columns. Thus a' repeats a; d' repeats d/k. Summing the duplicated pseudo-observations gives

D r_g = h + k q a - q d.

After the native independent scalar gain denoiser,

D g1 = tau/(tau+k q) [h+k q a-q d],

whereas

h1 = tau/(tau+q) [h+q a-q d].

Subtracting yields the exact first-step identity

D g1-h1 = tau (k-1) q / [(tau+q)(tau+k q)] * [tau a + q d - h].

All terms are complex vectors except the real positive scalars. In general this is nonzero. Do not incorrectly multiply the aggregate Onsager subtraction by k: it contains hb' and therefore sums to d, not k d. If the bracket vanishes, the first gain update is invariant for that particular input; later differences are not thereby excluded. If the aggregate gain difference lies in a physical null direction, coordinate difference alone is not proof of different channel action. The numerical probe must also check a physical-operator difference.

## Remarks and Interpretation
The gain coordinates and coordinate prior variance change, while their physical aggregate distribution is the invariant object. The native approximation need not commute with aggregation.

## Boundaries and Non-Claims

Before receiver comparisons, verify initial physical channel equality independently through Channel.apply, TimePathOps.power and the pushforward prior D(tau/k I)D^H=tau I. Tolerances are fixed BEFORE results: rtol1e-10, atol1e-12 for native floating-point parity/formula checks. Meaningful sensitivity requires the relative physical-operator difference after the first point update >1e-8; otherwise record an uninformative example rather than choose another one.

For a known synthetic n=32, P=2 case, independently build dense matrices and verify the exact Gaussian posterior aggregate for a fixed observed x. For one predetermined saved real key U/rho .3/7dB/frame9100, restore original h0/support/prior from run2; no SBL rerun. Replay native original fixed20/point20 against saved decoded/error results before comparing duplicate fixed20/point20. Keep all original code untouched. The first update formula uses v0 from prior moments, NOT the post-symbol state v1.

This is an algebra/representation probe, not a FER experiment: one real key and one synthetic fixture cannot establish a performance trend, a Gamma-specific effect, near-duplicate sensitivity, or a new method. Exact duplicates are a controlled limiting case. Finite-precision parity is not bitwise equivalence. A verified structural non-invariance does not by itself attribute all SBL reversals to it.

## Open Risks
The two predetermined native cases qualified; this does not remove the scope limits below. Floating reductions can create tiny fixed-mode discrepancies; use the declared tolerance and retain failures. A point update can differ in coordinates yet stay in an original physical nullspace, so physical operator differences are required. Exact duplication is a limiting-case probe and does not establish novelty or sensitivity to the actual near-duplicate SBL atoms.

## Numerical Qualification (2026-10-21)
Both uniform initial H/working-prior equivalence and fixed/first-symbol parity passed. Independent dense fixed-x Gaussian aggregate posterior agrees to floating precision in the synthetic case. First point physical-operator difference is .062906 relative in the synthetic fixture and1.380326 in the saved real key, both above1e-8; the closed-form gain-difference residual is below1.2e-16. Final point LLRs differ. See `experiments/sbl_freeze_replay_20261020/REPRESENTATION_SUMMARY.md` for numerical evidence and boundaries. No change to the pre-run formula or tolerance was required.
