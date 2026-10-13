# Joint delay–CFO identifiability through fourth-power phase codes

## Target
Characterize equality of complete unknown-QPSK observation laws and determine whether a classical two-dimensional sequence construction can remove the ambiguity of a CFO-oriented quadratic code.

## Status
COHERENT AFTER REFRAMING / EXTRA ASSUMPTION — analytically verified within scope; see JOINT_REVIEW.md. No numerical execution or performance claim.

## Invariant Object
The observation probability law modulo an unknown scalar gain phase. Fourth-order tensors are witnesses, not a replacement for that law.

## Assumptions and Notation
One circular path; known useful-block boundaries; sufficient guard; guard samples excluded. Symbols are independent uniform rotated QPSK with unit modulus. Noise is proper white Gaussian with the same known variance under both hypotheses. Gain h is nonzero and fixed. Let F[n,j]=exp(-2πinj/N)/sqrt(N), D_a[n,n]=exp(2πian/N), and Π_l x[n]=x[n-l mod N]. Let C=diag(v), |v_j|=1, w_j=v_j^4. Indices of v,w are cyclic. For integer s, a row chirp R[n,n]=exp(-πis n²/N) is periodic if sN is even; we impose both s∈Z and sN even. The useful-block model is y=h D_ν Π_l R F^H C S+η. Integer l is modulo N; ν is real modulo N. Unknown scalar phases absorb constants from row-chirp removal.

After removing R, write U_(a,l)=D_a F^H C E_l, where a=ν+sl and E_l[j,j]=exp(-2πilj/N). Compare parameters (a0,l0),(a1,l1), with d=l1-l0 and k=a1-a0. This definition fixes all signs below.

## Derivation Strategy and Map
1. Deconvolve Gaussian noise and identify gain magnitude from covariance.
2. Characterize unitary automorphisms of independent QPSK.
3. Reduce integer delay–CFO ambiguity to a Weyl coefficient of w.
4. Compare quadratic and classical cubic codes; distinguish even-N obstruction and prime-N remedy.
5. State temporal-phase and AFDM applicability limits explicitly.

## Main Derivation

### 1. Proposition: complete-law equality reduces to a monomial symmetry
The Gaussian characteristic function never vanishes, so equal noisy laws imply equal noiseless laws. Covariance gives |h0|=|h1|. Consequently equality holds iff a scalar-phase multiple of Q=U0^H U1 maps the QPSK product law to itself.

For any row r of a unitary matrix, independence and proper QPSK give E|Σ_j r_j S_j|^4=2(Σ_j|r_j|²)²-Σ_j|r_j|⁴. If its output is QPSK, the left side is 1; unitarity then gives Σ_j|r_j|⁴=1 with Σ_j|r_j|²=1. Thus each row has exactly one nonzero entry. Unitarity makes this a permutation with unit-modulus coefficients. Product-law equality then requires those coefficients, after one shared scalar phase, to lie in C4={1,i,-1,-i}. Conversely these transformations preserve the product law.

### 2. Identity and exact ambiguity criterion
Q=E_l0^H C^H F D_k F^H C E_l1. For noninteger k, every entry of F D_k F^H is nonzero (finite geometric sum: numerator 1-exp(2πik) is nonzero, as are the denominators). Thus for N>1 it is not monomial, and equality is impossible.

For integer k, F D_k F^H maps input j-k to output j. The nonzero coefficient in row j of Q is

α_j=(v_(j-k)/v_j) exp(-2πidj/N) exp(2πil1k/N).

Its fourth power, apart from a constant, is w_(j-k) conjugate(w_j) exp(-2πi4dj/N). Define

A_w(k,m)=N^(-1) Σ_j w_(j-k) conjugate(w_j) exp(-2πimj/N).

All summands have unit modulus. Their mean has modulus one iff they are identical. Therefore, allowing unknown gain phase, the complete single-frame laws coincide **iff** k is integer and |A_w(k,4d)|=1. This is both necessary and sufficient, not only a fourth-moment test.

### 3. Quadratic code: perfect CFO slice but an ambiguity line
For even N and gcd(q,N)=1, w_j=exp(-πiqj²/N) is periodic. Substitution gives

A_w(k,m)=exp(-πiqk²/N) 1_{qk-m=0 mod N}.

The CFO-only slice d=0 has no nonzero ambiguity, but the joint problem has a full line qk=4d mod N. Comparing a true (ν,l) to (νeff,0) gives νeff=ν+(s-4q^(-1))l modulo N. This recovers the obstruction in CONTINUOUS_THEORY.md §6.

Concrete parameters: N=64, s=5, q=1, l=1, νeff=ν+1. The fixed gain phases can be chosen to match the complete laws. In continuously evolving frames spaced L=80 samples, the extra interframe phase is a C4 rotation because 4L(νeff-ν)/N=5. Hence independent unknown-QPSK useful blocks remain indistinguishable for every frame count and noise level. Both hypotheses must lie in the admitted prior; the result does not imply failure under a narrow prior excluding one of them or when guard samples are observed.

Two quadratic codes q=1 and q=-1 yield effective signatures ν+l and ν+9l for s=5. Their difference 8l can identify a sufficiently short delay prior. This is a sufficient signature construction only; shared gain phases might supply more information. We do not claim an iff classification for that multi-code experiment.

### 4a. Universal obstruction for composite lengths, independent of column code
Let g=gcd(N,4). For every unit-modulus code w, A_w(0,4d)=1 whenever d is a multiple of N/g. Taking Δν=-sd gives k=0 and therefore an exact complete-law ambiguity for every diagonal column precoder. When N is divisible by four, d=N/4 is unavoidable over the unrestricted parameter set. A full-range power-of-two design cannot remove this symmetry merely by choosing a better v. This does not imply ambiguity within a short prior excluding such delay differences. In continuous frames the ambiguity survives if 4LΔν/N is integer; for d=N/g, integer s,L and g dividing 4 this condition always holds.

This follows directly from E_d having only C4 phases and commuting with C: unknown independent QPSK absorbs the delay modulation. For even N, all d=N/2 also survive. For odd N the universal obstruction is absent because gcd(N,4)=1. This length dependence must be included in any proposed deployment claim.

### 4b. Proposition: classical Alltop fourth-power code removes the joint lattice ambiguity
Let N=p≥5 be prime. Choose w_j=exp(2πij³/p) and choose any fixed fourth root v_j for every coordinate. Use even s so that the row chirp is p-periodic. This is a different design regime from the even-N counterexample.

For k=0, A_w(0,m)=1_{m=0}. For k≠0, the exponent in A is the quadratic polynomial

-3k j²+(3k²-m)j-k³ modulo p.

Its leading coefficient is nonzero. To establish the Gauss magnitude directly, let G=Σ_j exp(2πi(aj²+bj)/p), a≠0. Expand |G|² using j=t+u and the other index t. The inner sum over t vanishes for every u≠0 since 2au≠0, and equals p for u=0. Thus |G|=sqrt(p), so |A_w(k,m)|=1/sqrt(p) for k≠0.

Since 4 is invertible modulo p, |A_w(k,4d)|=1 occurs only at (k,d)=(0,0). Section 2 also excludes noninteger k. Therefore single-frame population laws identify l modulo p and ν modulo p, with h identifiable only to the intrinsic C4 ambiguity. This is population identifiability from the law, not exact recovery from one realized frame.

### 4c. Strong baseline: standard irrational quadratic c2 already attains the minimal ambiguity group
For N≥3 take the conventional v_j=exp(-2πic2 j²) on representatives j=0,...,N-1 with irrational c2; its cyclic extension is by lookup, not by extending the polynomial to all integers. For integer 1≤k<N, define f(j)=(j-k mod N)²-j². On each of the two no-wrap/wrap index segments f is affine with slope -2k or 2(N-k). At least one segment contains two consecutive indices since N≥3. If the summands defining A_w(k,4d) were constant, their ratio on this pair would require -4c2[f(j+1)-f(j)]-4d/N to be an integer. The first term is irrational and the second rational, which is impossible. Thus |A|<1 for every nonzero k, for all integer d.

At k=0 the exact ambiguities are precisely N|4d. Therefore conventional irrational quadratic c2 has exactly the unavoidable group from §4a. In odd dimensions it already gives full single-path population identifiability. This defeats any claim that cubic scrambling is necessary to restore identifiability over the standard AFDM baseline. Cubic coding's remaining possible distinction is a quantitative lattice separation bound, not basic identifiability; numerical conditioning of finite-precision irrational-like codes remains a separate question. The specially rational CFO-CAZAC c2=q/(8N) creates extra ambiguities that conventional c2 avoids.

### 4d. Actual small rational c2 baseline also attains the minimal group
The pilot baseline is c2=1/(10N²), not literally irrational. In the same consecutive-index ratio argument, the quadratic phase increment has nonzero magnitude 8|c2|t with 1≤t≤N-1. If 0<8|c2|(N-1)<1/N, that increment has magnitude strictly between 0 and 1/N. It cannot cancel the rational term 4d/N modulo an integer: a nonzero residue of 4d/N has distance at least gcd(N,4)/N≥1/N from the integers, while a zero residue cannot cancel the nonzero increment either. Thus no k≠0 ambiguity exists under this sufficient small-c2 condition. The actual c2=1/(10N²) satisfies it for every N≥3.

Consequently the extra CAZAC ambiguity is also a regression relative to the project's actual small rational baseline, not merely a comparison to an ideal irrational coefficient. Population uniqueness still provides no quantitative conditioning guarantee.

### 5. Exact tensor separation on the integer lattice
Let T(U)=Σ_j u_j^(⊗4), where u_j are the columns of the unitary U. For rotated QPSK, the holomorphic fourth moment of y equals κ h⁴T(U), where |κ|=1; cross pairings vanish because E S²=0. Proper Gaussian noise contributes zero to this holomorphic tensor.

The tensors u_j^(⊗4) are orthonormal, so ||T(U)||_F²=N. For integer k, Q=U0^H U1 is monomial and

|〈T(U0),T(U1)〉|=|Σ_j α_j⁴|=N|A_w(k,4d)|.

Consequently, for equal gain magnitude, minimization over their relative phase gives exactly

min_θ || |h|⁴ T(U0)-exp(iθ)|h|⁴ T(U1)||_F²
=2N|h|⁸(1-|A_w(k,4d)|).

The cubic construction has lower bound 2p|h|⁸(1-1/sqrt(p)) over distinct integer lattice hypotheses. A quadratic code has zero separation on its ambiguity line. This is not a bound for arbitrarily close real CFOs, not a probability-of-error bound, and not a sample-complexity or CRB result. An empirical full tensor has p⁴ entries and may be impractical.

## Remarks and Interpretation
The scientific intuition is that orthogonality along a one-dimensional CFO slice does not control the two-dimensional time–frequency orbit. Independent unknown QPSK makes the relevant design variable v⁴; it is the projective orbit of this code that must be separated. The cubic sequence and its Gauss sums are classical. Candidate contribution is the complete-law reduction and its consequence for this blind AFDM model, not invention of Alltop codes or ambiguity-function design.

## Boundaries and Non-Claims
The cubic v is additional known diagonal phase scrambling: Unew=U_AFDM P. For a fixed physical channel the transformed effective channel is P^H H_eff P, preserving zero pattern and singular values. This fact does not prove finite-alphabet full diversity, unchanged PAPR, or equal BER. Standard quadratic-only AFDM is not silently replaced. No production files are changed.

Prime lengths are not power-of-two production lengths. The unrestricted delay/CFO parameter set differs from the project's narrow operational prior. Multipath, fractional delay, coding across frames, unknown timing/guard, channel evolution, and practical high-order moment sample budgets are outside the proof. Continuous observation cannot destroy the single-frame identifiability of the cubic model, but temporal progress may help other codes and must be treated with its correct phase law.

## Open Risks
Independent algebra review pending. Closest prior art includes classical Alltop operator sounding, AFDM CAZAC pilot ambiguity design, and recent dual-chirp delay–Doppler separation. Novelty search must determine whether the unknown-payload fourth-power law characterization is already known. No claim of a major innovation or finite-sample usefulness is justified yet.

## Current verification record (2026-10-06)
Independent mathematical review in JOINT_REVIEW.md passed this note within its explicit scope. Any earlier pending-proof risks above record the derivation history; the identified s-integer, lattice-quantifier and repeated-frame wording issues have been corrected. Numerical performance and first-in-literature claims remain unestablished. COMPOSITE_LATTICE_ESTIMATION.md supersedes the earlier pairwise-only limitation for the specified lattice and compact gain annulus; it does not establish efficient computation or continuous-CFO estimation.
