# Minimal known-symbol remedy: a classical adaptation candidate

Status: analytically verified within scope; see JOINT_REVIEW.md. Same circular single-path model and integer s with sN even as JOINT_IDENTIFIABILITY.md. Population-law statements only. No new scientific run.

## Target and invariant
Determine whether a small amount of known payload removes the universal QPSK ambiguity while retaining arbitrary column phase code and arbitrary N≥3. Invariant: complete law including its mean and centered covariance. This explicitly changes the no-pilot observation model.

## Two adjacent deterministic symbols suffice
Replace coordinates J={0,1} by known nonzero unit-modulus values p0,p1; all other coordinates remain iid zero-mean QPSK. Let U=D_a F^H C E_l and gain h≠0. The centered covariance is

K=|h|² U(I-P_J)U^H+σ²I,

where P_J is the diagonal coordinate projector. Trace(K-σ²I)=(N-2)|h|² identifies the gain magnitude. Equal covariances therefore imply Q P_J Q^H=P_J for Q=U0^H U1.

If k=a1-a0 is noninteger, all entries of Q are nonzero. Yet a unitary preserving the coordinate subspace span{e0,e1} must have zero entries from its columns to every row outside J. Since N≥3, this is a contradiction. Thus k is integer. For integer k, Q is a cyclic shift times diagonal phases, so preservation is equivalent to J+k=J modulo N. An adjacent pair has no nonzero cyclic stabilizer for N≥3: translating 0 to 1 forces translating 1 to 2, outside J except N=2. Hence k=0 modulo N.

Now Q=E_d with d=l1-l0, independent of C. Equality of means gives h0 p0=h1 p0 and h0 p1=h1 exp(-2πid/N)p1 in these two source coordinates. Since both p values are nonzero, h0=h1 and d=0 modulo N. Therefore ν1=ν0 modulo N as well. Mean and covariance alone identify all parameters in this model, with no residual C4 gain ambiguity. This holds for any phase code v, including c2=0, and for composite lengths.

## One known symbol does not always suffice
With J={j0}, covariance likewise forces k=0: a noninteger Fourier mixer cannot preserve the one-coordinate subspace and a nonzero cyclic shift moves it. The mean permits h1/h0=exp(2πidj0/N). For every remaining random coordinate j, equality of QPSK laws then requires exp(-2πid(j-j0)/N)∈C4. The data coordinates include an adjacent cyclic neighbor of j0, so the condition is exactly N|4d. It is also sufficient for every coordinate. Thus one known symbol leaves gcd(N,4) delay branches in the unrestricted set: four for N divisible by four, two for N even but not divisible by four, one for N odd. The gain is adjusted to match the known symbol.

For successive frames with the same fixed pilot position, temporal phase is constrained by the nonzero mean, not merely C4 invariance. Thus one pilot can acquire additional information over time. The one-pilot impossibility above is a single-frame population-law result; do not extend it to arbitrary continuous-frame experiments. With J={0}, choose d=N/g, g=gcd(N,4), Δν=-sd. Continuous equality additionally requires Lsd/N∈Z, which holds in the N64,L80,s5,d16 example but not for all L.

## Scientific interpretation and limits
Known coordinates break different symmetries: their covariance deficit labels a frequency-shift subspace, and the relative phase of two means labels delay. One coordinate leaves an unknown-gain phase tradeoff; adjacent coordinates remove it. This is an identifiability rationale for a conventional pilot mechanism, not a new pilot concept, finite-sample superiority, or multipath result.

The two-pilot covariance signal has rank two against N-2 random data components. Estimation quality, channel coherence length and practical sample cost are unproved. Widely separated pilots could improve delay sensitivity but may reintroduce modular delay aliases; a practical design needs conditioning and prior-aware analysis rather than treating adjacency as universally optimal. Baselines must include standard AFDM pilots and CP-based methods. This candidate is retained under the user's useful-adaptation criterion and does not itself establish the active larger-innovation goal.

## Current verification record (2026-10-06)
Independent mathematical review in JOINT_REVIEW.md passed this note within its explicit scope. Any earlier pending-proof risks above record the derivation history; the identified s-integer, lattice-quantifier and repeated-frame wording issues have been corrected. Numerical performance and first-in-literature claims remain unestablished. COMPOSITE_LATTICE_ESTIMATION.md supersedes the earlier pairwise-only limitation for the specified lattice and compact gain annulus; it does not establish efficient computation or continuous-CFO estimation.
