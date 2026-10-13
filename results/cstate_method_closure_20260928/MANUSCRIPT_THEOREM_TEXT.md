# Compact manuscript theorem and corollary

**Proposition (operator–covariance compatibility).** Let U_1,…,U_P be unitary N×N complex path operators and let F be a specified family of Hermitian PSD data covariances. Define Γ_ij(V)=tr(U_i^HU_jV). Then Γ(V)=tr(V)I_P for every V∈F iff tr(U_i^HU_jV)=0 for all i≠j and V∈F. In particular, compatibility with all isotropic covariances is equivalent to tr(U_i^HU_j)=0. Compatibility with all covariances diagonal in a fixed orthonormal basis B is equivalent to diag(B^HU_i^HU_jB)=0. Compatibility with every PSD covariance would require U_i^HU_j=0 and is therefore impossible for P≥2 unitary paths.

*Proof.* Unitarity gives Γ_ii(V)=tr(V), leaving only off-diagonal conditions. Isotropic and basis-diagonal families test respectively the trace and each basis-diagonal entry. For the PSD family, V=xx^H tests x^HU_i^HU_jx for every complex x; complex polarization forces U_i^HU_j=0, contradicting unitarity. ∎

**AFDM/CPP corollary.** For the frozen integer-delay, sufficient-CPP operators U(l,ν)=AD_νC_lS_lA^H with positive Doppler modulation, the normalized operator Gram is R_ij=1[l_i=l_j]D_N(ν_j−ν_i). At equal delay, diag(U_i^HU_j)=D_N(ν_j−ν_i)1 in AF coordinates. A same-delay doublet thus has R=[[1,ρ],[ρ*,1]], ρ=D_N(ν_2−ν_1), and
λ(R)={1−|ρ|,1+|ρ|},  min_c||R−cI||_2=||R−I||_2=|ρ|.
For fixed noninteger Doppler-bin separation δ,
D_N(δ)=e^{πi(N−1)δ/N}sinc(δ)/sinc(δ/N) → e^{πiδ}sinc(δ).

*Proof.* Unitary conjugation and cancellation of equal-delay CPP phases reduce the operator trace to a positive-sign finite Doppler sum; unequal cyclic delays have zero trace. The DAFT's constant entry magnitudes make the equal-delay AF diagonal constant. The doublet characteristic polynomial and midpoint minimax identity give the norm result; the finite geometric sum gives the limit. ∎

**Scope paragraph.** These statements separate physical operator geometry, a declared working-covariance family, and one scalar contraction. Distinct retained delays make R=I and remove equal-delay Gram coherence, but nonuniform AF-diagonal variances may still generate cross-delay entries in Γ(V). We therefore do not claim the pre-CSTATE receiver is fully exact under its actual variances. The result is a consistency/limitation analysis of an approximate inference map, not a new AMP theorem or a prediction of FER, usefulness of scalar retuning, or necessity of global geometry reopening.
