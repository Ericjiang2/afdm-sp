# Why a known column phase code can fit the AFDM transform chain

Analytical note, not a multipath performance experiment or novelty certificate.

Let the fixed row-chirp modulation front be B=R F^H and let C_v=diag(v), |v_j|=1. Transmit x=B C_v S and use the matched inverse C_v^H B^H at a coherent receiver. For any fixed physical effective-block channel H_time (including a fixed multipath realization), define G=B^H H_time B. The effective symbol-domain channel is

H_v=C_v^H G C_v.

Therefore entrywise |H_v[p,q]|=|G[p,q]|, exact zero support is identical, and every singular value and Frobenius/operator norm is identical. Relative to another unit-modulus quadratic code C_q, H_v=D^H H_q D with D=C_q^H C_v. These statements follow immediately from diagonal unitary conjugation, independent of whether v is quadratic. Thus replacing the known column chirp coefficients need not destroy the AFDM channel's absolute-value sparsity/leakage pattern; the row chirp and physical useful-block operator remain the same.

This is a useful compatibility argument for exploring classical phase-code adaptation. Applying a precomputed general code needs the same N unit-modulus multiplications as a precomputed quadratic column chirp. Code storage/design costs still belong in the account; no overall transmitter/receiver speedup follows just from equal multiplication count.

Limits: identical singular values imply identical Gaussian-input log-det capacity for the same physical channel and SNR. They do NOT generally imply identical finite-QPSK coherent BER, pairwise codeword distances, iterative-receiver convergence, or diversity properties; general diagonal phases do not preserve the QPSK product alphabet. In a monomial single-path channel, per-coordinate coherent equalization gives the usual scalar constellation after phase removal, but a sum of paths requires actual analysis/testing. The current blind likelihood benefit arises precisely because the unknown finite-alphabet distribution is sensitive to phases that covariance/singular-value summaries cannot see.

The identities assume the same physical H_time and row-chirp/block window across designs. They do not justify replacing the physical prefix law, fractional offset model or unknown payload prior with a more favorable one. This is a general unitary-modulation fact, not AFDM-exclusive mathematics and not a first-in-literature claim.

Independent check (2026-10-07; internal analytical scope): PASS. Substitution gives D^H H_q D=C_v^H C_q(C_q^H G C_q)C_q^H C_v=C_v^H G C_v, confirming the direction and signs. The Gaussian log-det statement uses the usual white proper Gaussian noise and common power/SNR convention, so log det(I+γH_vH_v^H) is unchanged; singular values alone are not a claim about an arbitrary colored-noise convention. The single-path exception requires a monomial effective channel and known coherent phase removal, and does not assert that every fractional-offset single path is monomial. No additional experiment was performed.
