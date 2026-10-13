# Proof obligations and derivation

This proof uses the definitions in [theory](CLOSURE_COMPATIBILITY_THEORY.md). All spaces are finite-dimensional. No integral/limit interchange, probability-mode upgrade, Gaussian assumption or independence assumption is used. The asymptotic limit is a scalar analytic expansion with an explicitly bounded parameter set.

## Typed symbols, dependencies and assumptions

N∈Z, N≥2; P∈Z, P≥1. U_i∈C^{N×N} are unitary. M_ij=U_i^H U_j∈C^{N×N} need not be Hermitian. V∈H_N^+ is a complex Hermitian PSD covariance; F⊆H_N^+ is a specified family. B∈C^{N×N} is a fixed unitary change of covariance coordinates. Γ(V),R∈C^{P×P} are path-index matrices. s=tr(V)∈R_+, ρ∈C, r=|ρ|∈[0,1], c∈R or C as explicitly stated. δ∈R is measured in Doppler bins. K<∞ is fixed as N→∞.

Dependency DAG: unitary operators→MC1 diagonal/PSD→MC2 family criterion→MC3/4/5 family specializations. Frozen AFDM convention→MC6 operator trace→MC7 AF-diagonal block. MC6+MC7→MC8 doublet limitation. Positive Doppler sum→MC9 exact kernel→MC10 uniform expansion. These dependencies are acyclic. Actual receiver covariance reachability is not assumed to equal any full family in MC3–5.

## MC1 — exact contraction and diagonal

For H(h)=Σ_i h_iU_i and e=d−μ with E[e]=0, covariance V=E[ee^H], write y−H(h)(p+d)=a−H(h)e, a=y−H(h)(p+μ). Expansion gives
E||a−H(h)e||²=||a||²+tr(H(h)^H H(h)V)=||a||²+h^HΓ(V)h.
Finite second moments justify each finite expectation. In particular Γ_ii=tr(U_i^HU_iV)=tr(V). For PSD V, factor V^{1/2}; Γ_ij=tr((U_iV^{1/2})^H(U_jV^{1/2})), so Γ is a Hermitian PSD Gram matrix. This argument uses the full complex trace, not its real part alone.

## MC2 — family iff and span

By MC1 the desired scalar matrix already has the correct diagonal. Equality is therefore equivalent to each off-diagonal entry being zero, for every family member. The map V↦tr(M_ijV) is complex-linear and in particular real-linear on Hermitian matrices; vanishing on a family is equivalent to vanishing on its real span. This proves both directions even for F=∅ or F={0}, where it makes no nontrivial demand on geometry.

## MC3 — isotropic iff

For V=vI, tr(M_ijV)=v tr(M_ij). If tr(M_ij)=0 the condition holds for every v≥0. Conversely choose v=1 from the full isotropic family. A restricted family must contain some v>0 for this converse. A zero-only family is a counterexample to an unqualified converse.

## MC4 — fixed-basis diagonal iff

For V=B diag(v)B^H, cyclicity yields tr(M_ijV)=Σ_k v_k(B^HM_ijB)_{kk}. The condition diag(B^HM_ijB)=0 suffices. Necessity follows by choosing v=e_k for each coordinate, which is a valid singular PSD covariance. If only strictly positive v are allowed, use differences of two strictly positive diagonal vectors to span the same diagonal subspace. If a smaller family is specified, only its span is annihilated; isotropic-only data cannot establish this full diagonal condition. A different unitary basis changes the diagonal condition, unless the covariance family is simultaneously transformed.

## MC5 — all complex PSD iff, without assuming M Hermitian

Sufficiency of M_ij=0 is immediate. For necessity, all x∈C^N give admissible V=xx^H and 0=tr(MV)=x^HMx. Put x=e_a to obtain M_aa=0. For a≠b put x=e_a+e_b, giving M_ab+M_ba=0. Put x=e_a+i e_b, giving iM_ab−iM_ba=0. Thus M_ab=M_ba=0, hence M=0. These are complex equalities. Real-vector tests alone would miss the nonzero unitary skew-symmetric matrix [[0,1],[-1,0]], for which x^TMx=0 for every real x but (1,i)^HM(1,i)≠0.

For two unitary paths M^HM=I_N, contradicting M=0. More constructively M is a normal unitary matrix, so a unit eigenvector x has x^HMx=λ with |λ|=1; its rank-one complex PSD covariance witnesses failure. For P=1 there is no off-diagonal restriction and MC1 proves exactness. Arbitrary Hermitian W=W_+−W_- is a difference of PSD matrices, and every complex X=A+iB with Hermitian A,B; these spanning facts explain equivalence of the zero-functional conclusion on those larger spaces, without interpreting non-PSD matrices as covariances.

## MC6 — exact CPP path trace and sign

Let A=Λ_2FΛ_1 be unitary with the chirps and Fourier sign in the theory document. U(l,ν)=AD_νC_lS_lA^H. D_ν,C_l are diagonal unit-modulus matrices and S_l is a cyclic permutation; every U is unitary. Cyclicity cancels A/A^H in tr(U_i^HU_j).

For l_i≠l_j moduloN, S_li^HC_li^HD_(νj−νi)C_ljS_lj is a weighted nonidentity cyclic shift and has zero diagonal. Our representative delays0≤l<N make l_i≠l_j equivalent to nonidentity. For l_i=l_j=l, diagonal CPP factors commute with D and cancel, leaving S_l^HD_(νj−νi)S_l. Its trace is the sum of exp(+2πin(ν_j−ν_i)/N), since permutation preserves trace. Division by N gives R_ij=1[l_i=l_j]D_N(ν_j−ν_i). The positive sign follows directly from D_νi^HD_νj, not from a guessed stored Gram orientation.

## MC7 — AF-diagonal same-delay identity and cross-delay limitation

At equal delay set Z=S_l^HD_(νj−νi)S_l, which is diagonal. U_i^HU_j=AZA^H. Since |A_kn|²=1/N, (AZA^H)_{kk}=Σ_n Z_nn/N=D_N(ν_j−ν_i), independently of k. Hence for AF-diagonal V, Γ_ij=tr(V)D_N(ν_j−ν_i) on equal-delay pairs. On distinct-delay pairs the operator trace vanishes by MC6, but that does not imply its AF-coordinate diagonal vanishes; a weighted nonuniform sum of those diagonal entries can be nonzero. Thus the old exact statement is the block projection P_lΓ=tr(V)R, not full Γ=tr(V)R.

The already audited Frobenius decomposition follows because Γ−tr(V)R vanishes on same-delay pairs, while R−I vanishes on distinct-delay pairs and on the path diagonal; their supports are disjoint. Therefore
||Γ−tr(V)I||_F²=tr(V)²||R−I||_F²+||Γ−tr(V)R||_F².
Distinct-delay pre-CSTATE geometry removes the first term only. Frozen original time_refine enforces that entry geometry; it does not make actual AF marginal variances isotropic.

## MC8 — doublet eigenvalues and minimax scalar

For R=[[1,ρ],[ρ*,1]], det(R−λI)=(1−λ)²−|ρ|². Positivity and unit diagonal (MC1 with V=I/N) imply0≤r=|ρ|≤1; eigenvalues areλ_±=1±r. Since R is Hermitian, ||R−I||_2=r. For any c∈C, R−cI is unitarily diagonalizable with singular values |λ_±−c|. The triangle inequality gives
2r=|λ_+−λ_-|≤|λ_+−c|+|λ_-−c|≤2 max(|λ_+−c|,|λ_-−c|).
Thus the norm is≥r; c=1 attains r. The same value holds for real scalars. Equality at r>0 forces c to the midpoint1; at r=0 minimization gives c=1 directly. For Γ=sR with s≥0 the scaled argument gives minimum sr (including s=0). Spectral norm is a uniform error over unit coefficient vectors, not a statement about a particular trajectory or decoder outcome.

## MC9 — finite Dirichlet kernel

Sum the finite geometric series for exp(2πiδ/N)≠1. Rewriting numerator and denominator with sin gives
D_N(δ)=e^{πi(N−1)δ/N} sin(πδ)/(N sin(πδ/N)).
At δ=mN, return the finite-sum value1, not0/0. This expression equals the sinc formula away from removable singularities and extends continuously. It is N-periodic, so the source's wrapping δ into[−N/2,N/2) changes no value. D_N(−δ)=D_N(δ)*. At a fixed integer δ≠0 and N>|δ| it is0, whereas atδ=0 it is1.

## MC10 — asymptotic and uniform remainder

For fixed K<∞ and |δ|≤K take N≥max(2,2K). Put x=πδ/N, so |x|≤π/2, away from nonzero poles of cot x. Algebra gives
D_N(δ)=e^{iπδ}sinc(δ)[e^{-ix}x/sin x]
=e^{iπδ}sinc(δ)[x cot x−ix].
The removable analytic even function x cot x has expansion1−x²/3+O(x⁴), with a bounded fourth-order remainder on[−π/2,π/2]. Consequently the displayed O_K(N^{-4}) expansion follows; its constant may depend on K but not δ or N in this domain. This proves the positive-phase pointwise limit for fixed noninteger δ and the nonzero magnitude limit |sincδ|. The leading imaginary correction is−iπδ/N; there is no cubic term in this bracket. The argument does not claim uniformity for δ→∞ with N. If δ=Nα with α∉Z fixed, the geometric-series magnitude instead yields |D_N(Nα)|≤1/(N|sinπα|).

## Counterexample obligations and acceptance

Finite tests must include: F={0}; trace-zero but nonzero fixed-basis diagonal M; diagonal-zero but nonzero unitary M and a complex PSD witness; real-only tests missing a skew-Hermitian/skew-symmetric operator; basis change; distinct-delay AF nonuniform covariance; same-delay fractional/integer/duplicate boundaries; positive/negativeδ finite sum and asymptotic remainder. Every algebraic statement above includes its hypotheses; finite tests do not prove universal quantifiers. Independent review must reject any FER, global optimality, posterior-exactness or general AMP reading.
