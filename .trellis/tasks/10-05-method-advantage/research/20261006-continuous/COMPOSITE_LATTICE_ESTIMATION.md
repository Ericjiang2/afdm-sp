# Candidate composite estimator: unknown complex gain and a lattice minimax gap

Status: analytically verified within scope; see JOINT_REVIEW.md. This closes a specific missing link between pairwise separation and existence of a data-only estimator. It does not claim computational efficiency or numerical validation.

## Target and frozen scope
Use the integer lattice Θ_N={(a,l):a∈{0,...,N-1}, l∈{0,...,N/g-1}}, g=gcd(N,4), and ν=a-sl modulo N. Same one-path circular model, known boundaries/σ²>0, fixed per-symbol SNR. Gain is unknown within a known fixed annulus 0<ρmin≤|h|≤ρmax<∞, independent of N. We estimate θ=(a,l), not the intrinsic C4 phase of h. This is wide-range lattice acquisition, not continuous CFO refinement.

## Direct scalar Hellinger bound, also for unequal gain magnitudes
Let p,q be the scalar QPSK-plus-Gaussian densities for gains h0,h1. Write B for their affinity and m4(p)=κ h0⁴, m4(q)=κ h1⁴, |κ|=1. Cauchy–Schwarz gives

|m4(p)-m4(q)|²
≤ [∫(sqrt(p)-sqrt(q))²] [∫|z|⁸(sqrt(p)+sqrt(q))²]
≤4(1-B)[E_p|z|⁸+E_q|z|⁸].

For every gain in the annulus, the eighth moment is bounded by

M8=ρmax⁸+16ρmax⁶σ²+72ρmax⁴σ⁴+96ρmax²σ⁶+24σ⁸.

Writing h0=ρ0 exp(iφ0), h1=ρ1 exp(iφ1), the moment difference squared is at least 2ρmin⁸[1-cos(4(φ1-φ0))]. Thus

1-B≥c0[1-cos(4(φ1-φ0))], c0=ρmin⁸/(4M8)>0.

This explicit conservative inequality avoids the scalar Fisher regularity argument and holds uniformly over unequal gain magnitudes in the annulus. Product factorization then gives the full-frame uniform-gain affinity bound exp[-c0 N(1-|A_w(k,4d)|)] for distinct lattice hypotheses.

## Data-only finite-grid likelihood estimator
Choose a deterministic Euclidean N^(-2)-net H_N of the compact complex annulus, consisting of points in the annulus, with cardinality O(N⁴). Define

(θhat,hhat)=argmax_(θ∈Θ_N,h∈H_N) p_(θ,h)(y),

with fixed deterministic tie breaking. Each density is the exact product of scalar four-component Gaussian mixtures after applying U_θ^H to y. All templates and gain bounds are known; no true θ,h or symbols are used. This is a theoretical finite computation, not an efficient implemented receiver.

## Uniform exponential error bound
Because ||h U_θ S||=|h|sqrt(N) deterministically, there exist constants C,cE>0 depending only on the gain/noise bounds such that E_N={||y||≤C sqrt(N)} has P(E_N^c)≤exp(-cE N), uniformly in θ,h. This follows directly from Gaussian norm concentration and the triangle inequality.

For fixed θ, the scalar mixture log-density derivative along a complex-gain increment dh is bounded by (2/σ²)(|z_j|+ρmax)|dh|. Along the segment joining two annulus points the magnitude stays ≤ρmax, even if the segment passes inside the annulus. Summing and using Σ|z_j|≤sqrt(N)||y|| yields a log-likelihood Lipschitz bound C1N on E_N, uniform over θ.

For the true (θ*,h*), a net point h° within N^(-2) obeys log p_(θ*,h°)(y)≥log p_(θ*,h*)(y)-C1/N on E_N. If the maximum-likelihood grid chooses a wrong θ, some wrong (θ,h) must therefore satisfy p_(θ,h)/p_(θ*,h*)≥exp(-C1/N). Markov's inequality applied to the square-root likelihood ratio gives probability at most exp(C1/(2N)) Aff(P_(θ*,h*),P_(θ,h)).

If μ_N=max over nontrivial allowed lattice shifts |A_w(k,4d)|, the union bound over O(N⁶) grid hypotheses gives

sup_(θ*,h*) P{θhat≠θ*}
≤exp(-cE N)+O(N⁶) exp[C1/(2N)-c0 N(1-μ_N)].

For classical Alltop in prime dimensions, μ_N≤1/sqrt(N); for a fixed realization from the proven random-code existence argument, μ_N=O(sqrt(log N/N)). Thus a data-only estimator exists with positive linear-in-N worst-case acquisition-error exponent, including unknown complex gain and power-of-two N with the representative delay set.

## Contrast with all quadratic c2
QUADRATIC_BARRIER.md constructs an allowed pair, with equal gain magnitude selected inside the same annulus and adjusted phases, whose KL is O(N^(1/3)) for every c2(N). Any θ estimator induces a binary test on that pair, so its worst-case error is at least the equal-prior binary Bayes error, hence at least exp[-O(N^(1/3))]/4. Therefore the quadratic class cannot achieve a positive linear-in-N minimax acquisition-error exponent on this lattice, whereas general known unit-modulus column coding can.

This is a qualitative minimax exponent separation in a precisely defined model, not a tight optimal rate for quadratic codes. It is not derived by comparing a practical receiver to a truth-assisted detector. The proposed grid is expensive; finite constants can be weak. No assertion is made about production short priors, guard-inclusive observations, multiple paths, fixed total energy, continuous CFO, full diversity or actual BER.

## Current verification record (2026-10-06)
Independent mathematical review in JOINT_REVIEW.md passed this note within its explicit scope. Any earlier pending-proof risks above record the derivation history; the identified s-integer, lattice-quantifier and repeated-frame wording issues have been corrected. Numerical performance and first-in-literature claims remain unestablished. COMPOSITE_LATTICE_ESTIMATION.md supersedes the earlier pairwise-only limitation for the specified lattice and compact gain annulus; it does not establish efficient computation or continuous-CFO estimation.
