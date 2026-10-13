# Geometry–covariance compatibility of the scalar contraction

Verdict: VERIFIED WITH EXPLICIT FAMILY/COORDINATE RESTRICTIONS. Independent analytic review passed; source-bound finite-dimensional tests passed (see PROOF_AUDIT.json and CLOSURE_COMPATIBILITY_TESTS.json). This is an exact compatibility statement for the already implemented physical operators and an approximate kernel contraction; it is not a new AMP theorem, inference-convergence result or FER implication.

## Definitions and scope

Let N≥2, P≥1, and U_i∈C^{N×N} be unitary path operators. A working covariance V=E[(d−μ)(d−μ)^H] is Hermitian PSD and has finite entries. Geometry and gains are fixed during this expectation. Define

Γ_ij(V)=tr(U_i^H U_j V),   R_ij=tr(U_i^H U_j)/N.

The scalar identity closure is Γ(V)=tr(V)I_P. Unitarity fixes its diagonal: Γ_ii(V)=tr(V). No pairwise-distinct-operator assumption is necessary; identical operators are also covered. V may be singular or zero. “For every V” always refers to the specified family, not to an unverified family of actual posterior covariances.

## CC1: exact family criterion

For any family F⊆H_N^+, the closure holds for every V∈F iff tr(U_i^H U_j V)=0 for every i≠j and V∈F. Equivalently the off-diagonal trace functionals annihilate the real linear span of F. For an empty or zero-only family this is vacuous and gives no geometry restriction. The family can be defined by the receiver's reached states, but its full membership must then be established separately.

- **All isotropic covariances {vI:v≥0}:** iff tr(U_i^H U_j)=0 for all i≠j. A restricted isotropic family needs at least one v>0 for necessity. Equivalently R=I_P.
- **All diagonal covariances in a fixed orthonormal basis B:** F_B={B diag(v)B^H:v∈R_+^N}, B unitary. Exact iff diag(B^H U_i^H U_j B)=0 for all i≠j. In the AF data coordinates B=I. A smaller family of diagonal covariances need not force each diagonal entry to vanish.
- **All Hermitian PSD covariances:** iff U_i^H U_j=0 for all i≠j. The complex matrix U_i^H U_j is generally not Hermitian, but complex rank-one PSD tests suffice. Because U_i^H U_j is unitary, the condition is impossible when P≥2. For P=1 the scalar identity is exact for every covariance.

“All Hermitian covariances” and “all complex matrices” are not interchangeable modeling assumptions: only PSD matrices are covariances. Vanishing on every PSD matrix nevertheless implies the same zero functional on all Hermitian matrices and, by complex linearity, all complex matrices. Testing real vectors only would be insufficient for the non-Hermitian complex functional.

## CC2: frozen AFDM/CPP specialization

Use 0≤l<N integer delays, sufficient CPP, real ν,c1,c2, positive Doppler modulation D_ν[n,n]=exp(+2πinν/N), and A=Λ_2 F Λ_1 with F_kn=N^{-1/2}exp(−2πikn/N), Λ_a[n,n]=exp(+2πic_a n²). With cyclic delay S_l and the frozen unit-modulus CPP factor C_l,

U(l,ν)=A D_ν C_l S_l A^H.

Then R_ij=1[l_i=l_j]D_N(ν_j−ν_i), where D_N(t)=N^{-1}Σ_{n=0}^{N−1}exp(+2πint/N). At equal delay, diag(U_i^H U_j)=D_N(ν_j−ν_i)1_N in **AF coordinates**. Thus a same-delay pair is compatible with every AF-diagonal covariance iff D_N(ν_j−ν_i)=0. Its nonzero finite-N zeros occur at integer separations not congruent to0 moduloN; fractional separations generally remain coherent.

At distinct delays R_ij=0, so isotropic compatibility holds. This does not force diag(U_i^H U_j)=0 in AF coordinates: actual nonuniform AF variances may leave cross-delay Γ terms. Original pre-CSTATE TF entry has distinct retained delays, but this establishes R=I only. The already audited equal-delay projection identity P_l Γ(V)=tr(V)R and orthogonal Frobenius decomposition remain valid for AF-diagonal V; they do not remove cross-delay uncertainty. No change to TF/CSTATE follows from these identities.

## CC3: exact doublet scalar limitation

For one same-delay doublet, write R=[[1,ρ],[ρ*,1]], ρ=D_N(ν_2−ν_1), r=|ρ|∈[0,1]. Its eigenvalues are1−r and1+r, and

||R−I||_2=r,    min_{c∈R}||R−cI||_2=r.

The minimum also equals r if c ranges over C; c=1 attains it. For a pair with AF-diagonal covariance V and s=tr(V), Γ(V)=sR, so min_c||Γ(V)−cI||_2=sr. When r>0 and s>0, no scalar can reproduce both eigen-directions uniformly. This does not say every particular gain vector incurs the maximum error; it does not assert harmful receiver dynamics or FER degradation. At r=0 scalar closure is exact for this two-path block; at r=1 the Gram is singular. Duplicate operators and near-duplicate synthetic fixtures are not asserted to pass CSTATE's geometry-admission rule.

## CC4: exact positive-phase Doppler-bin asymptotic

With sinc(t)=sin(πt)/(πt), for real δ use the continuous periodic value at removable singularities:

D_N(δ)=exp(+πi(N−1)δ/N) sinc(δ)/sinc(δ/N).

At δ∈N Z the finite-sum value is1. For each fixed noninteger δ,

D_N(δ) → exp(+πiδ)sinc(δ),
|D_N(δ)| → |sinc(δ)|>0.

More precisely, for |δ|≤K and integer N≥2K (with δ=0 interpreted continuously),

D_N(δ)=exp(+πiδ)sinc(δ)[1−iπδ/N−(πδ)²/(3N²)+O_K(N^{-4})].

The coefficient phase is positive because the source uses positive Doppler. R_21 conjugates the entire expression. The fixed-bin-separation limit is not the different regime δ=Nα with a fixed noninteger normalized sample-frequency offset α; in the latter regime the finite-sum magnitude is at most1/(N|sinπα|). At a fixed nonzero integer δ the kernel is eventually exactly0; at δ=0 it is1. No uniformity over δ growing without bound with N is claimed.

## Manuscript use and evidence

The safe contribution is compatibility of one scalar contraction with a specified operator geometry and covariance family. See [complete proof](CLOSURE_COMPATIBILITY_PROOF.md), [compact theorem text](MANUSCRIPT_THEOREM_TEXT.md), and [prior audited identities](../tf_scalar_closure_audit_20260924/SCALAR_CLOSURE_DERIVATION_20260924.md). Numerical source-bound tests corroborate finite cases; the proof establishes the quantifiers and asymptotic statement. No receiver, decoder, truth or new observation is needed.
