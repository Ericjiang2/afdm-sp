# Candidate worst-pair barrier for every quadratic column chirp

Status: analytically verified within scope; see JOINT_REVIEW.md. Extends STATISTICAL_SEPARATION.md to an optimized-c2 baseline. No code or numerical observations.

## Target, assumptions, and invariant
Fixed single circular path, N≥3, integer s with sN even, fixed per-symbol SNR ρ²/σ²>0, independent QPSK. The comparison is restricted to the unit-spaced effective-frequency lattice a=ν+sl∈Z modulo N, with all N frequency bins admitted (equivalently integer ν since s,l are integers); integer delays range over J={0,...,N/g-1}, g=gcd(N,4). This large delay prior excludes duplicate representatives of the universal delay symmetry, but is wider than many practical channels. Sufficient guard for all allowed delays is assumed. The comparison is over complete single-frame laws and unknown scalar gain phases.

Let v_j=exp(-2πic2 j²) for any real c2, allowed to depend on N and chosen optimally. The invariant is worst-pair KL divergence, minimized over distinct allowed lattice hypotheses and their gain phases. We claim a sublinear upper bound for this quantity for every quadratic c2.

## Dirichlet step
For any integer K with 1≤K<N and any real x, the pigeonhole principle applied to K+1 fractional parts {rx}, r=0,...,K, partitioned into K intervals gives integers 1≤k≤K and d with |kx-d|≤1/K. Take x=2Nc2 and write ε=2Nc2 k-d.

Compare relative effective-frequency shift k and delay difference d. For no-wrap rows j=k,...,N-1 the monomial coefficient from JOINT is, apart from a shared phase,

α_j=exp[2πi(2Nc2 k-d)j/N]=exp(2πi ε j/N).

The common quadratic constant and l1k constant are absorbed into the relative unknown gain phase. Thus on N-k coordinates, |arg α_j|≤2π/K. There are k remaining wrap coordinates; their phases may be arbitrary.

## Allowed parameter representatives
Replace d by d'=d mod (N/g), choosing 0≤d'<N/g, and take l0=0,l1=d'. The resulting coefficient multiplies each row by exp(2πi rj/g) for an integer r. Since g divides 4, these are C4 factors, which do not change the QPSK mixture laws. Set ν0=0 and ν1=k-sd' modulo N. Both are allowed by the full N-bin CFO lattice prior. Since 1≤k<N, the two effective-frequency parameters differ, so this is a distinct pair even when d'=0. This step is why the result does not automatically cover narrow CFO or short-delay priors.

## KL upper bound
Couple the same QPSK label after the rowwise C4 adjustment. The scalar mixture KL upper bound in STATISTICAL_SEPARATION gives

KL(P0||P1) ≤ (ρ²/σ²)[4k+(N-k)4π²/K²]
≤ (ρ²/σ²)[4K+4π²N/K²].

Choose K=floor(N^(1/3)) for sufficiently large N, so the bound is O((ρ²/σ²)N^(1/3)), uniformly over every real c2. The elementary bound is conservative; no finite-N superiority follows from the constants. Bretagnolle–Huber yields a worst-pair Bayes-error lower bound exp[-O(N^(1/3))]/4 at fixed SNR. Thus no sequence of optimized quadratic c2 can have a positive linear-in-N worst-pair simple-hypothesis error exponent over this admitted joint parameter set.

## Comparison and scope
The classical random phase-code existence bound in STATISTICAL_SEPARATION gives max |A|=O(sqrt(log N/N)) over all k≠0. On the representative delay prior J, k=0 distinct pairs have m=4d≠0 modulo N. Hence every distinct integer effective-frequency lattice pair has affinity at most exp[-cN(1-o(1))], even for powers of two. Classical Alltop supplies the analogous construction for prime N.

This compares *pairwise simple-hypothesis distinguishability* uniform over nuisance phase, not a proved implementable joint estimator or its composite minimax rate. The strong theoretical distinction is linear versus sublinear worst-pair error exponent between unrestricted column phase coding and the entire quadratic column-chirp class, under a broad explicit joint prior. It does not prove a benefit in the project's short-delay/narrow-CFO production regime, fixed total block energy, multipath or fractional delay. The standard row chirp s is allowed but only shears which CFO pair realizes the bound; it cannot remove it under a full N-bin CFO lattice prior.

## Open risks
Independent verification of the Dirichlet normalization, cyclic wrap, representative-delay/C4 reduction, and error-exponent interpretation is required. Prior literature on quadratic chirp ambiguity and blind finite-alphabet synchronization may already contain this phenomenon. A useful bounded study should first check whether the obstruction remains in realistic acquisition priors, rather than run a broad-prior demonstration and call it general AFDM superiority.

## Current verification record (2026-10-06)
Independent mathematical review in JOINT_REVIEW.md passed this note within its explicit scope. Any earlier pending-proof risks above record the derivation history; the identified s-integer, lattice-quantifier and repeated-frame wording issues have been corrected. Numerical performance and first-in-literature claims remain unestablished. COMPOSITE_LATTICE_ESTIMATION.md supersedes the earlier pairwise-only limitation for the specified lattice and compact gain annulus; it does not establish efficient computation or continuous-CFO estimation.
