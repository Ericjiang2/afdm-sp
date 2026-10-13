# Scalar-closure derivation — 2026-09-24

> Provenance: 2026-09-24 · Codex theory-to-code audit · source Git `49ba637bba592dcda6e612609ff3bdc27048cb8d` · verifier SHA-256 `43480bb9f2da0475cdfa4d7437e55ee8e6fffaca929c232c10f35b264ea284bf` · historical IDs H0–H6 and narrowed statements S1–S4: [PROVENANCE.json](PROVENANCE.json) · new receiver/decoder/observations = **0/0/0**. Historical gates are not superseded.

## Target and status

**COHERENT AFTER REFRAMING / EXTRA ASSUMPTION; theory verdict VERIFIED WITH RESTRICTIONS.**
Invariant object: the fixed-h working-distribution residual energy and its gain-side data-uncertainty contraction. Exact algebra is separated from the frozen scalar inference approximation. This is not a derivation of a new complete AMP algorithm.

## Assumptions and notation

N≥2 and P≥1; integer delays 0≤l_i<N, a sufficient CPP, real normalized Dopplers ν_i (positive modulation exp(+2πinν_i/N)), real c1,c2, and the frozen unitary DAFT. Delays are not identified outside this representative range. A working distribution q(d) has mean μ, covariance V=E[(d−μ)(d−μ)^H]⪰0, and finite second moments. The gain vector h and geometry θ are held fixed in that expectation; no claim about the exact joint posterior of data and gains is made. The scalar-closure specialization uses the **AF-domain** V=diag(v), v≥0, v_x=Σv_n/N. Improper complex data need no extra pseudo-covariance term for this squared Euclidean energy.

Let F_kn=N^(−1/2)exp(−2πikn/N), Λ_a=diag(exp(+2πic_a n²)), and A=Λ_2 F Λ_1. Then A^H is IDAFT. Define (S_l t)_n=t_(n−l mod N),
C_l[n,n]=exp(2πic1[N²+2N(n−l)]) for n<l, and 1 otherwise;
D_ν[n,n]=exp(+2πinν/N).
The exact AF-domain path is U(l,ν)=A D_ν C_l S_l A^H.
All factors are unitary. Source locators: physical.py::daft, regressors, Channel.apply; twofft.py::TimePathOps. Detailed file paths, hashes and timing are in the code map.

Derivation map: expected energy → Γ → operator Gram → AF-diagonal same-delay block → orthogonal matrix-error decomposition → common-state gain-mean displacement → physical norm. Only the scalar identity reaction and the exploratory replacement are inference choices.

## SC-P1 — exact working-distribution contraction (Pro equation 1)

**Statement.** With x=p+μ and e=d−μ,
E_q||y−H(h)(p+d)||² = ||y−B(x)h||² + h^HΓ(V)h,
where Γ_ij(V)=tr(U_i^H U_j V).

**Proof.** Write r=y−B(x)h. Since E[e]=0, the two cross terms in
||r−H(h)e||² vanish. The remaining expectation is
tr(H(h)^H H(h)V)
=Σ_ij h_i^*h_j tr(U_i^H U_j V).
Consequently Γ is Hermitian PSD and the stated identity follows. No Gaussianity, isotropy, independence of coordinates, or large-N limit is required. Covariance diagonalization, if used, is a property of q, not a theorem about the true posterior.

**Source/test/boundary.** CM-GAMMA; numerical IDs `eq1_trace`, `eq1_source_Gamma`. Numerical cases cover the source diagonal specialization; the arbitrary-V proof is analytic. Geometry refinement explicitly evaluates the working-q contraction; the scalar TF gain reaction does not construct this full matrix. This proposition is standard second-moment algebra, not a novelty claim.

## SC-C1 — physical operator Gram and isotropic corollary (equation 2)

**Statement.** R_ij=tr(U_i^H U_j)/N and
R_ij=1_{l_i=l_j}D_N(ν_j−ν_i), where
D_N(t)=N^(−1)Σ_(n=0)^(N−1) exp(+2πint/N)
=exp(+πi(N−1)t/N) sinc(t)/sinc(t/N).
D_N is N-periodic; use its continuous value 1 at multiples of N.
Γ(v_x I)=Nv_x R; R=R^H⪰0 and R_ii=1.

**Proof.** Unitary conjugation by A preserves the trace.
For unequal delays, S_li^H C_li^H D_(νj−νi) C_lj S_lj is a weighted nonidentity cyclic shift and has zero diagonal. For equal delay l, the two diagonal CPP factors commute with D and cancel. The product becomes S_l^H D_(νj−νi)S_l, a permutation of the modulation diagonal; its trace is Σ_n exp(+2πin(ν_j−ν_i)/N). Substitution in SC-P1 gives the isotropic corollary. This proves the sign and normalization rather than inferring them from a stored Gram.

**Source/test/boundary.** CM-U, CM-R; numerical IDs `direct_CPP_operator`, `physical_R_trace`, `eq2_isotropic`. Fractional delays, insufficient CPP, nonunitary windows or other path definitions require a fresh derivation. R is a normalized operator Frobenius Gram, not the instantaneous B(x)^H B(x)/N.

## SC-P2 — exact AF-diagonal same-delay block (equation 3)

**Statement.** For V=diag(v) in the AF coordinates and v_x=mean(v),
P_l(Γ(V))=Nv_x R, where P_l keeps precisely equal-delay index pairs.

**Proof.** For equal delay, put Z=S_l^H D_(νj−νi)S_l. It is diagonal and tr Z=ND_N(ν_j−ν_i). The AF-domain product is A Z A^H. Since every DAFT entry satisfies |A_kn|²=1/N, every diagonal element of A Z A^H is tr Z/N=D_N(ν_j−ν_i). Thus
tr(A Z A^H diag(v))=D_N(ν_j−ν_i)Σ_k v_k=Nv_x R_ij.
For unequal delays the projection is zero, and R_ij is also zero by SC-C1. Both sides therefore coincide entrywise. CPP cancellation and the constant AF-coordinate diagonal are explicit steps; “diagonal covariance” in another domain is insufficient.

**Source/test/boundary.** CM-V, CM-GAMMA; numerical IDs `eq3_same_delay`, `eq3_cross_support` and the recorded unequal-delay nonzero diagnostic. In physical.py::projected_variance, Δl=0 makes FFT(v)[0]=Σv, the chirp factor 1 and the kernel argument ν_j−ν_i. This is an exact block identity, not Γ(V)=Nv_xR in general. A time-domain diagonal covariance instead gives a variance-weighted Doppler sum and need not satisfy this statement.

## SC-C2 — exact matrix-error decomposition (equation 4)

**Statement.** Define Γ_cross=Γ(V)−Nv_xR. Then
||Γ(V)−Nv_x I||_F²
=N²v_x²||R−I||_F²+||Γ_cross||_F².

**Proof.** SC-P2 gives zero Γ_cross entries at every equal-delay pair. R−I is zero at unequal-delay pairs by SC-C1 and zero on the diagonal because R_ii=1. Thus their supports are disjoint, and
〈Nv_x(R−I),Γ_cross〉_F=0 exactly.
Expand the squared norm of their sum.

**Source/test/boundary.** CM-GAMMA/CM-IDENTITY; numerical IDs `eq4_Frobenius`, `eq3_cross_support`. Even when R=I, nonuniform AF variances can produce a nonzero Γ_cross. Replacing Nv_xI by Nv_xR removes this matrix-error component, but does not establish better approximate-inference dynamics, message calibration or FER.

## SC-C3 — common-state gain update and physical defect (equations 5–6)

**Statement and source quantities.** At one joint-gain iteration, freeze every entering value and the already computed within-step residual, precision and barred fields. Let α=sv≥0 be the damped output precision; x̄,h̄ are the within-step damped means; v_x is the **entering** mean AF data variance; τ=1/P is the CN(0,I/P) prior variance. Here P is the number of paths and, by this prior choice, the prior precision. The frozen code uses
q_g=α||x̄||², v_q=1/max(q_g,10^(−12)),
r_h^BASE=h_pre+v_q[B̄^H s−αNv_x h̄],
h_out^BASE=τr_h^BASE/(τ+v_q).
The comparison changes only h̄ to Rh̄ inside that reaction.

**Proof.** The two pseudo-observations differ by
−v_q αNv_x(R−I)h̄.
The same Gaussian denoiser multiplies this by τ/(τ+v_q), giving
b=h_out^R−h_out^BASE=−k(R−I)h̄,
k=αNv_x/(P+1/v_q).
There is no extra damping multiplier: damping already formed α,h̄,x̄, and the source does not additionally damp the resulting Gaussian gain mean. The floor belongs inside 1/v_q=max(q_g,10^(−12)); it must not be discarded. The data precision floor 1/max(αh̄^HRh̄,10^(−12)) affects v_r and future propagation but not this common-state subtraction. For fixed-gain mode the update is disabled; this statement is for the production joint mode.

For any b, linearity and SC-C1 give
||Σ_i b_i U_i||_F²/N=b^HRb.
Since k is real and R is Hermitian,
ε_H²=b^HRb=k²h̄^H(R−I)R(R−I)h̄.
η_reaction=||(R−I)h̄||/||h̄|| is defined only for nonzero h̄. For h̄=0, b=0 and ε_H=0 while η is undefined. Near zero, report the norm and numerical conditioning; do not silently invent a normalized value.

**Source/test/boundary.** CM-ALPHA/CM-VQ/CM-HBAR/CM-DENOISER; numerical IDs `eq5_finite_gain_difference`, `eq6_physical_norm`, `eq6_quadratic_form`, `duplicate_null_physical`; floor/zero states are explicit cases. b is the exact finite difference between two synthetic common-state mean maps, not a predicted complete-trajectory displacement. For duplicate operators R can be singular: a nonzero coefficient displacement may have zero physical norm. Neither η nor ε_H is a receiver-utility theorem.

## Geometry reachability and manuscript scope

The frozen native receive function calls time_refine before every scalar_joint call. That refinement applies np.unique to delays, picks one Doppler center per delay and subsequently adjusts Doppler only. Therefore the **retained geometry entering each native pre-CSTATE TF call** has distinct delays and R=I. The initial acquisition dictionary/support may contain several Dopplers at one delay; it is not covered by that assertion. CSTATE admits distinct same-delay Dopplers and can make R−I nonzero; it need not do so on every observation. Architecture classification: A only at the explicitly stated TF entry boundary.

The minimum manuscript package is SC-P1 + SC-C1, SC-P2 + SC-C2, and the common-state corollary SC-C3. Present it as a project-specific limitation/consistency result. TF remains an exact low-state implementation of its **declared approximate scalar inference map**. These identities neither refute that implementation equivalence nor upgrade CGR's failed/insufficient experimental gates.

## Open risks and non-claims

The proof is conditional on the frozen integer-delay/sufficient-CPP operators and working covariance representation. It does not prove a true posterior covariance, general AMP robustness, global optimization of geometry, or FER improvement. Archive-based architectural conclusions are static source conclusions, not a new receiver replay. Numerical finite-dimensional tests complement the proofs; they do not establish asymptotic validity.

Synthetic duplicate operators and Doppler separations below1e−6 test the broader Channel/operator representation; they are not claimed as admissible final CSTATE geometries, whose duplicate rule rejects them. No asymptotic or decoder claim is inferred from these boundary examples.
