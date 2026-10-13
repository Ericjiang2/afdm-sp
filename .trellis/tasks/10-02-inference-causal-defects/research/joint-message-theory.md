# Research: Joint Gaussian elimination and lawful message exchange

- Query: Can low-path-dimensional Schur structure yield a self-consistent core detector, without a one-term AMP patch?
- Scope: mixed; mathematical derivation with current source/internal-neighbor appraisal
- Date: 2026-10-02
- Skills: formula-derivation; scientific-critical-thinking already loaded.

## Target
Derive the complete local Gaussian factor update and its discrete symbol cavity interface; specify exactly where it ceases to be the original bilinear posterior. Provide a testable core candidate, not a performance claim.

## Status
**COHERENT AFTER REFRAMING / EXTRA ASSUMPTION.** Frozen linear-surrogate EP has a coherent likelihood/site decomposition. A relinearized EP receiver is a candidate approximation, not a proven globally convergent or exact bilinear algorithm. Exact integration over gains offers an independent oracle/alternative factor formulation but does not make data inference polynomial automatically.

## Invariant Object
For fixed physical geometry and independent exogenous gain prior p0(h), the original invariant is
p(h,d|y) ∝ p0(h) p_code(d) exp(-||y-H(h)(p+d)||²/sigma2).
The observation likelihood and code indicator each occur once. No fitted CE posterior is multiplied as a fresh prior.

For the proposed local stage, explicitly replace only the nonlinear observation factor by its first-order tangent about (h0,d0). This is a different, declared surrogate factor; the independent p0(h) and code factor retain their meanings. Inner EP iterations refer to this frozen surrogate. Relinearizing changes the surrogate; there is no automatic monotonicity theorem across that change.

## Assumptions and notation
H0=sum h0_p U_p, B0=[U_p(p+d0)], r0=y-H0(p+d0). In error coordinates, r0=B0 δh+H0 δd+t+w with t=sum δh_p U_p δd.

For proper independent Gaussian input errors with means a_h,a_d and covariances Ch,Cd, W=sigma2^-1 I. These covariances are exogenous priors or explicitly derived factor cavities. They cannot be arbitrary posterior covariances from y. Singular cases use their exact support subspaces; no silent epsilon or pseudoinverse density on the ambient space.

Canonical proper complex Gaussian form is exp(-zᴴΛz+2 Re ηᴴz), with Λ=C^-1, η=C^-1m. Real Gaussian form is exp(-zᵀΛz/2+ηᵀz).

## Derivation strategy and map
1. Exact affine Gaussian completion of square → all means/covariances.
2. Schur elimination → low-path-dimensional correction, not low-rank H.
3. Canonical factor division → cavity and extrinsic messages.
4. Entire Gaussian/discrete EP update → replacement for scalar AMP, rather than an inserted precision.
5. Return to original bilinear model → remainder and geometry/decoder limitations.

## Main derivation

### 1. Full means and covariances, not only an effective precision
For the frozen local Gaussian model define
A=Ch^-1+B0ᴴWB0, E=B0ᴴWH0, D=Cd^-1+H0ᴴWH0,
η_h=Ch^-1 a_h+B0ᴴWr0, η_d=Cd^-1 a_d+H0ᴴWr0.

The joint precision is J=[[A,E],[Eᴴ,D]]. Let S=D-EᴴA^-1E. Then exactly
m_d=S^-1(η_d-EᴴA^-1η_h),
m_h=A^-1(η_h-E m_d),
C_dd=S^-1,
C_hd=-A^-1 E S^-1,
C_hh=A^-1+A^-1 E S^-1 Eᴴ A^-1.

The second positive-semidefinite term in C_hh is the extra uncertainty due to unknown d; replacing C_hh by A^-1 reports the conditional covariance as if it were marginal. This distinction provides a concrete mechanism metric against the exact small model.

With zero input error means, S=Cd^-1+H0ᴴWeff H0 and the right side for m_d is H0ᴴWeff r0, where
Weff=W-WB0(Ch^-1+B0ᴴWB0)^-1 B0ᴴW
=(sigma2 I+B0 Ch B0ᴴ)^-1.
The Schur correction has rank at most P. However S is N×N and generally dense; low P does **not** make inversion of Cd^-1+H0ᴴWH0 cheap. A matrix-free iterative solve has a stopping error and real operator cost, and diagonal posterior blocks are additional work. No O(N log N) full update follows just from Woodbury.

### 2. Exact cavity division and double counting
If a Gaussian approximation q(z) has canonical (Λq,ηq) and includes a stored Gaussian site t_a with (Λa,ηa), then q\a=q/t_a has
Λ\a=Λq-Λa, η\a=ηq-ηa.
This is exact division of the **represented factors**, not extraction of a true cavity from any estimated covariance. There must be an identifiable site to subtract. For a proper normalized Gaussian cavity require Λ\a positive definite on its support; an improper EP site itself can have negative precision while the global approximation remains proper. Arbitrarily clipping negative site precision changes the update and must be documented and evaluated; it is not an identity.

Known-data linear model example: Cpost^-1=C0^-1+BᴴWB, ηpost=C0^-1m0+BᴴWy. Removing the entire observation factor gives exactly (C0^-1,C0^-1m0). Feeding Cpost back without subtraction produces C0^-1+2BᴴWB after the next likelihood use. Current native CE gains are only mean initialization, so this is a warning for a **new covariance interface**, not evidence that current code performs this mistake.

### 3. Complete core candidate: frozen-tangent Gaussian/block-QPSK EP
Use absolute variables to avoid incorrectly centering the original gain prior at h0. Tangent identity is
H(h)(p+d) ≈ B0 h+H0 d-H0 d0.
Thus y_tilde=y+H0 d0 and L=[B0,H0]. p0(h)=CN(m0,C0) remains the original prior, with m0 often zero; CE h0 defines a tangent location, not a fresh gain-prior mean.

Represent each symbol's discrete prior by a Gaussian EP site t_i(d_i) with stored canonical precision T_i and information vector u_i. Work in real coordinates and 2×2 I/Q blocks (below). The global Gaussian approximation is
q_G(h,d) ∝ p0(h) N(y_tilde; L[h;d], Rw) product_i t_i(d_i).
Its precision/information are exactly
J=blockdiag(C0^-1,T_1,…,T_N)+LᵀRw^-1 L,
η=[C0^-1 m0; u_1;…;u_N]+LᵀRw^-1 y_tilde,
Here all quantities are realified (so C0 is the real gain-prior covariance and Rw=sigma2 I/2); T_i need not individually be positive. Solve Jm=η and the needed covariance blocks. The real data stacking must group each symbol’s I/Q coordinates, with an explicit permutation from the code’s all-I/all-Q convention.

For symbol i, obtain marginal (m_i,V_i). Remove its own Gaussian site:
Λ_i^cav=V_i^-1-T_i, η_i^cav=V_i^-1m_i-u_i.
For each of the four legal QPSK points a define
q_i^tilt(a) ∝ π_i(a) exp(-aᵀΛ_i^cav a/2+(η_i^cav)ᵀa).
Compute its exact mean m_i^tilt and full 2×2 covariance V_i^tilt. Update the site by
T_i^new=(V_i^tilt)^-1-Λ_i^cav,
u_i^new=(V_i^tilt)^-1m_i^tilt-η_i^cav.
Store and replace the old site; do not add another likelihood. Canonical damping is a possible numerical policy, not a new inference principle. Failed global SPD/cavity conditions must be reported; a bounded backtracking policy may be predefined, but no hidden floor should manufacture success. Singular deterministic symbol limits are handled by eliminating fixed coordinates.

This gives all Gaussian means, uncertainties and cross blocks, plus an explicit QPSK moment response. It replaces the scalar AMP update as a whole; there is **no extra imported AMP Onsager term**. EP's explicit factor exclusion is the relevant self-feedback control. The candidate can be first tested with uncoded independent symbols, then with a separate code-factor interface. It is standard EP applied to a task-specific surrogate; potential novelty is a verified AFDM-specific efficient structured solve or an error-controlled surrogate, not the site equations themselves.

### 4. Response/Jacobian and bit extrinsic
For a real tilted discrete distribution with canonical field η and fixed precision, differentiation gives
∂ E[a]/∂η = Cov(a).
If cavity is parameterized as Gaussian pseudo-observation r with fixed precision Λ, then ∂ E[a]/∂r=Cov(a) Λ. For the linear Gaussian block at fixed J, ∂m/∂y_tilde=J^-1 LᵀRw^-1. These provide finite-difference contracts. If tangent point, site precision, or learned covariance varies with y, these are **partial** derivatives only; their total derivative requires those dependencies. Do not label them the full algorithmic Onsager without another derivation.

For input bit priors L_j, exact symbol tilted APP gives outgoing Lext_j=Lapp_j-L_j. The subtraction must use the unaltered numerical prior actually inserted; clipping after subtraction is distinct from subtracting a differently clipped input. For a fixed cavity and other-bit prior, this extrinsic is invariant to its own L_j. That is a local message contract, not proof of independence after many loops.

π_i from LDPC check messages is the code-factor incoming message; the receiver likelihood factor must not already include the same exact code indicator. If exact short-code enumeration is used inside the receiver oracle, do not send its output through the same code factor again. Full-symbol EP site exclusion and leave-bit code-message exclusion remove different factors and must not be conflated. A fixed-point EC/code-factor construction is needed to claim a single global approximate free energy for the full coded loop.

### 5. Improper complex variables: why real 2×2 blocks are required
For complex centered z define C=E[zzᴴ], Pz=E[zzᵀ]. The augmented covariance is [[C,Pz],[Pz*,C*]]. The covariance of [Re z; Im z] is
(1/2)[[Re(C+Pz), -Im(C-Pz)],[Im(C+Pz), Re(C-Pz)]].
Proper thermal noise has real covariance sigma2 I/2. Unequal I/Q bit certainty gives nonzero pseudo-variance even for independent QPSK bits; channel/data posterior coupling can create more. Current moments function returns pseudo-variance but native discards it. A proper-complex derivation is exact only under its declared proper prior/linear surrogate assumptions, not generally for the QPSK posterior. Real representation also avoids confusing E[h d] (bilinear prediction) with E[h d*] (Hermitian cross covariance).

### 6. Exact gain marginalization remains a distinct clean route
For fixed geometry and truly independent h~CN(m0,C0), each discrete d gives
S(d)=sigma2 I+B(d)C0B(d)ᴴ,
log p(y|d)=-logdet S(d)-(y-B(d)m0)ᴴS(d)^-1(y-B(d)m0)+const.
Woodbury and determinant lemma reduce each evaluation to a P-dimensional solve. This is exact, keeps the bilinear product, and uses no local remainder approximation. But the function is nonseparable in all data symbols; exact posterior sum is exponential. Finite bank truncation, coordinate search or stochastic approximation each need a declared approximation and cost/error check. Current scope forbids enlarging candidate banks as the purported core innovation. Therefore use this first as oracle and a criterion for the local EP candidate, not as an unproven cheap decoder.

## Remarks and interpretation
- The mathematically natural decoupling is **conditional elimination with induced correlations retained**, not a projection annihilating full-dimensional unknown data.
- Schur C_hd and the positive covariance correction give a causal target: conditional-as-marginal uncertainty could make messages too confident. The exact oracle can refute that explanation if multimodality or geometry dominates instead.
- Full prior-direction covariance alone does not restore h–d coupling; compare same-surrogate full EP against block-factorized Gaussian inference with identical priors and operation accounting. Such an ablation is coherent but is a different approximation family.
- At known channel the gain variables vanish; this becomes ordinary linear channel EP. At known data it becomes exact linear Gaussian gain inference. These are useful limit tests, not evidence of globally exact bilinear inference.

## Boundaries and non-claims
The remainder t cannot simply be set to zero on hard frames. For independent centered local errors its energy formula is the PLAN formula; correlated posterior errors require joint fourth moments and nonzero mean of t can occur. Geometric uncertainty is also excluded by fixed U_p. Main session owns those numerical checks.

No proof here of convergence of parallel EP, of relinearization monotonicity, of VAMP state evolution for deterministic AFDM operators, or of improved FER. No prototype run occurred in this research. Low-rank parameter correction is insufficient by itself to solve the N-dimensional data system or recover its diagonal blocks cheaply.

## Open risks / concrete tests
1. Fixed-surrogate dense reference: verify full block inverse vs Schur means, all covariance blocks and finite-difference Jacobians.
2. Local cavity deletion: remove site algebraically and recompute from remaining represented factors; test agreement before any FER run.
3. Bit self-prior invariance with fixed cavity; full loop is not covered by this test.
4. Exact small original-bilinear oracle vs tangent EP: compare LLR, h covariance, cross moments and remainder, across near-collision and well-separated physical paths.
5. Track site indefiniteness, global precision condition and validity failures over both success/failure states; no selecting only successful EP runs.
6. Prove/measure the cost of full symbol covariance blocks. If cost has no promising budget regime, report that candidate limitation rather than declaring the entire direction exhausted.

## Files / related specs / external references
Current model details and source bindings: `model-contract.md` in this directory. Task contract: current mission PLAN §3–4. Internal closest predecessor: `.mission/20261001_23-33-35-afdm-innovation-space/bilinear/DERIVATION.md` already gives exact gain-mixture, response, CAVI and branch cavity. External closest-neighbor evidence and limitations are in `literature-neighbors.md`.
