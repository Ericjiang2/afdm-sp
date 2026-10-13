# Full-law separation, beyond tensor distance

Status: analytically verified within scope; see JOINT_REVIEW.md. No simulations. Target: test whether code design changes actual hypothesis distinguishability as N grows, despite both codes being population identifiable. This is a new analytical VALUE-01 direction, not a finite-sample receiver claim.

## Fixed assumptions and invariant
Same circular single-path model as JOINT_IDENTIFIABILITY.md. Positive fixed Gaussian noise variance σ² and fixed nonzero gain magnitude ρ; gain phase unknown. Compare integer effective-frequency differences k and integer delay differences d. Each hypothesis uses the same known waveform. The noise variance and ρ do not scale with N. Thus total frame energy grows with N; no fixed-total-frame-energy exponent is claimed. Invariant: Bhattacharyya affinity of the complete frame laws, maximized over relative unknown gain phase.

Let f_θ be the complex scalar density of ρ exp(iθ) S+η for rotated unit QPSK S and η~CN(0,σ²). Define b(θ)=∫sqrt(f_0(z) f_θ(z)) dz. It is C4 periodic, ≤1, and equal to one iff θ∈(π/2)Z. The iff follows from Gaussian deconvolution of the four support points.

### Lemma needed for uniform scalar bound
For fixed ρ>0, σ>0 there is c(ρ,σ)>0 such that

1-b(θ) ≥ c(ρ,σ) [1-cos(4θ)] for all θ.

Proof route: away from C4 points, positivity and compactness give the bound. Near zero, b(θ)=1-Iθ θ²/8+o(θ²), with Iθ=∫(∂θ fθ|0)²/f0>0. Finiteness and differentiability follow from finite Gaussian mixtures and Gaussian tails; Iθ>0 because ∂θ fθ|0 cannot vanish identically: its fourth holomorphic moment derivative is 4i E[(ρS)^4]≠0. Thus the ratio tends to Iθ/64>0. The other C4 points follow by periodicity. This is fixed-SNR only; c can be very small at low SNR.

## Proposition: ambiguity coefficient controls complete-law affinity on the lattice
After the common unitary transform U0^H, integer k makes U0^H U1 monomial. Under either hypothesis, coordinates are independent scalar QPSK Gaussian mixtures, with relative phases θ_j (permutations are immaterial). Therefore frame affinity equals ∏_j b(θ_j).

Using 1-x≤exp(-x), the scalar lemma and the fourth-power coefficient identity give, for any common gain phase β,

Aff(P0,P1,β) ≤ exp[-c Σ_j(1-cos(4θ_j+4β))].

Minimizing the sum over β yields N-|Σ_j exp(4iθ_j)|=N(1-|A_w(k,4d)|). Hence

sup_β Aff(P0,P1,β) ≤ exp[-c N(1-|A_w(k,4d)|)].

For classical Alltop w at prime N, every nontrivial lattice pair has affinity ≤exp[-c N(1-1/sqrt(N))]. For T iid repetitions with the same distribution, affinity is the T-th power. With continuous CFO frame phases, it is instead the product of frame-specific affinities; the uniform relative-phase bound still gives exp[-cTN(1-1/sqrt(N))]. This does not automatically construct a uniform composite-hypothesis estimator over the unknown phase; it is a pairwise distribution separation bound uniform over that phase.

## Actual small-c2 baseline has a hard adjacent-CFO pair
Set c2=α/N² with α=1/10 and take d=0,k=1. Then α_j=v_(j-1)/v_j equals exp(2πic2(2j-1)) for j=1,...,N-1; the wrap coordinate is α_0=exp[-2πic2(N-1)²]. The N-1 regular phases are O(1/N), while one wrap phase tends to -2πα. Thus simply increasing N does not make every coordinate informative for this pair.

A rigorous KL upper bound follows by coupling the same QPSK symbol per coordinate and then marginalizing: joint convexity/log-sum gives

KL(f_0 || f_θ) ≤ (ρ²/σ²)|1-exp(iθ)|².

Consequently the full-frame pair (choose equal transformed gain phases) satisfies

KL(P0||P1) ≤ (ρ²/σ²) [4+16π²α²/N],

using |1-exp(iθ)|²≤θ² on regular coordinates and ≤4 on the wrap coordinate. The coefficient is conservative: Σ_(j=1)^(N-1)(2j-1)²≤4N³ gives the displayed term. This bound is uniform in N. The Bretagnolle–Huber bound then gives equal-prior pairwise Bayes error ≥(1/4)exp[-KL(P0||P1)], a strictly positive N-independent lower bound at fixed SNR (possibly numerically tiny).

By contrast, the Alltop pairwise equal-prior Bayes error obeys Pe≤Aff/2, hence an exp(-constant N) upper bound for every fixed distinct lattice pair, uniformly over their gain phase choices. Compare the codes at the same prime N; do not compare prime cubic to a different even block length. Delays can be equal (d=0), so the hard adjacent-CFO pair does not require a long delay prior, but it does require two CFO values separated by one subcarrier in the admitted search range.

## Supporting tensor interpretation
For the baseline above, N(1-|A_w(1,0)|)→1-cos(8πα). Proof: the N-1 regular summands have angles 8πc2(2j-1)=O(1/N), total real deficit O(1/N); the wrap summand tends to exp(-8πiα). The mean imaginary part is O(1/N), so replacing Re(A) by |A| changes N times the deficit by o(1). Thus total phase-quotient fourth-tensor distance stays bounded, consistent with the full-law KL result. The Alltop tensor distance grows linearly in N.

## Power-of-two extension by a classical random phase-code existence argument
Prime length is not essential if the admitted delay prior excludes the universal group. Let w_j be independent uniform unit phases, chosen once as a known deterministic code thereafter. For any k≠0 modulo N and any m, E A_w(k,m)=0. Changing one w_j changes at most two summands, and changes A by at most 4/N. McDiarmid's inequality applied to the real and imaginary parts and a union bound imply

Pr{|A_w(k,m)|≥t}≤4 exp(-Nt²/16).

Union over fewer than N² pairs gives max_(k≠0,m)|A|≤sqrt[16 log(4N²/δ)/N] with probability at least 1-δ. This is a conservative existence statement, useful only when the displayed bound is below one. For k=0, the ambiguity is exactly zero for every m≠0 regardless of code.

Choose a contiguous delay prior of width less than N/gcd(N,4), so distinct allowed delays never differ by a universal-group element. Then every distinct admitted integer lattice pair has either k≠0 and the bound above, or k=0,m=4d≠0 and zero ambiguity. The full-law affinity proposition consequently yields exp[-cN(1-t)] separation, also along sufficiently large power-of-two lengths. A fourth root of the chosen w specifies v. This is additional known column scrambling, with the same diversity/PAPR and fair-baseline limitations as the cubic candidate. It is not a claim of a new random-code construction or a performed random-code search. No code has been sampled or deployed here.

## Scope and value
This is a sharper candidate than “cubic code restores identifiability”: the actual small-c2 baseline is identifiable but can have only O(1) distinguishability for an adjacent integer-CFO pair, whereas classical cubic coding yields linear-in-N pairwise Chernoff-type separation at fixed positive SNR. No claim that Alltop or phase coding is new. Potential AFDM adaptation value lies in the precise full-law separation contrast and its limited wide-CFO use case.

Missing: independent check of scalar mixture regularity and constants; nearest literature on phase-coded blind synchronization; practical estimator and sample budget; power-of-two variant and fair conventional optimized-c2 baseline. Do not infer production BER gain, multipath superiority, full diversity, optimality, or a solved major-innovation goal from this candidate.

## Current verification record (2026-10-06)
Independent mathematical review in JOINT_REVIEW.md passed this note within its explicit scope. Any earlier pending-proof risks above record the derivation history; the identified s-integer, lattice-quantifier and repeated-frame wording issues have been corrected. Numerical performance and first-in-literature claims remain unestablished. COMPOSITE_LATTICE_ESTIMATION.md supersedes the earlier pairwise-only limitation for the specified lattice and compact gain annulus; it does not establish efficient computation or continuous-CFO estimation.
