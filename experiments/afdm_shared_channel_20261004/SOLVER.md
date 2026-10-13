# Exact conditional CPP covariance under uniform outside variance

At a **fixed gain node h**, let T_h be the exact time-domain CPP channel and A
the unitary DAFT, so H_h=A T_h A^H. Each time row of T_h has at most P delay
entries; duplicate delays are summed. Fractional Doppler affects their phase,
including the CPP phase on wrapped samples, not this time sparsity.

For a target block B and uniform outside symbol variance v,

\[
S_h=\sigma^2I+vH_hH_h^H-vH_hE_BE_B^HH_h^H.
\]

In time coordinates define B0=sigma² I+v T_h T_h^H and
V=sqrt(v) T_h A^H E_B. Then S_t=B0-VV^H, and

\[
S_t^{-1}=B_0^{-1}+W(I-V^H W)^{-1}W^H,\quad W=B_0^{-1}V,
\]
\[
\log\det S_t=\log\det B_0+\log\det(I-V^H W).
\]

The sparse base is positive definite by positive noise. The block downdate is
also positive definite because it removes only target variance from the
positive noise-plus-outside covariance. No diagonal jitter is used. Sparse LU
of the base is generic and exact up to floating-point arithmetic; a small
Cholesky computes the downdate. `logdet(B0)` is the sum of log absolute LU
diagonals: permutation signs have unit modulus and B0 is positive definite.

If delays lie in a finite interval of width L, B0 has cyclic bandwidth at most
L. CPP wrap edges remain in the sparse matrix; they are not dropped to obtain
an ordinary banded matrix. More generally its offsets are pairwise delay
differences. Sparse LU fill and cost depend on this geometry and N. A small P
alone is not a cost bound.

Yi et al., [AFDM dual-domain EP](https://arxiv.org/html/2603.29218),
Sections III-B5/C/D, already use quasi-banded time-domain AFDM covariance and
LU with an inverse-banding approximation. CPP sparsity, domain conversion and
banded LU alone are therefore not novelty claims here. Our computational
object is the exact fixed-h conditional likelihood with a target-block
downdate; that narrower distinction also does not establish novelty.

Nonuniform **outside** DAFT variance is explicitly unsupported. A^H diag(v) A
is then generally dense, and replacing v by its mean would change the model.
Variance values on B are ignored because those symbols are conditioned on.
No outside symbols gives noise-only covariance. The mean input to each score
is pilot+fixed target+outside cavity mean. All scores retain N log(pi) and
the log determinant; no candidate-dependent normalization is omitted.

Operation accounting is per node and candidate:

| Work | Per gain node | Per candidate |
|---|---:|---:|
| Sparse base factorization | 1 | 0 |
| Sparse solve RHS | b (downdate setup) | 1 |
| Small b x b Cholesky | 1 for b>0 | 0 |
| Small solve RHS | 0 | 1 for b>0 |
| Log determinant reductions | 2 for b>0 | 0 |
| Low-rank downdate construction | 1 for b>0 | 0 |
| Inverse DAFT vectors | b | 2 |
| Sparse channel matvecs | b | 1 |

Each candidate also performs dense N x b low-rank contractions and a residual
quadratic. The independent unit tests additionally validate the public solve
interface; the full-message benchmark does not include extra validation solves
in its measured message path. Base factors can be reused across candidates
at one node, but generally not across different h nodes. A complete block
message with K gain nodes and 4^b legal candidates must account for all K
factorizations/downdates and K*4^b scores, and for node generation,
normalization and prior weighting. `finite_block_message` now measures that
complete evaluation for a supplied finite node measure: alphabet construction,
candidate means, all node setup/scoring, weighted logsumexp, uniform-target
normalization and all 2b bit LLRs. Fixed-node prior generation is recorded
separately once and reused across all eight size/block cases. Storage/evidence
writing is outside message timing. This does not establish continuous-prior
integration cost or receiver latency.

The registered benchmark uses N=16,64,256,1024, P=3, b=1,2, and three gain nodes
with fixed normalized weights [1/6,1/3,1/2]. The seeded nodes are drawn before
observations and then held fixed across every size/block. This **finite prior
measure is the declared object**, not a converged quadrature approximation of
a continuous Gaussian prior. Every block uses all 4^b legal QPSK words, with
power .5 and no incoming target factors. The complete pair message therefore
requires three sparse base factorizations, three block downdates and 48
conditional scores, versus 12 scores for singleton. Normalized scores,
probabilities, evidence and bit LLRs are compared against an independent dense
calculation with the same nodes and weights.

It saves paired raw conditional/marginal log likelihoods, normalized messages,
observations, legal candidates/bits and node measure, actual sparse/base/factor
nonzeros, per-node setup/score times and complete message times, alongside the
independent dense counts/times. Dense covariance uses existing
`Channel.apply` column by column, independently of sparse CPP construction.
Small tests additionally cover wrapped delay N-1, aliased delays, empty/full
target, zero variance, multiple RHS and nonuniform rejection. The full finite
pair test additionally checks direct probability-domain weighted summation,
all 16 legal states, all 48 scores and the 54 sparse right-hand sides (six
setup plus 48 score solves). Unequal node weights are necessary for the test's
expected posterior; dropping them changes the result.

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 /tmp/afdm-shared-channel-env/bin/python -m unittest experiments.afdm_shared_channel_20261004.test_conditional_solver -v
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 /tmp/afdm-shared-channel-env/bin/python -m experiments.afdm_shared_channel_20261004.conditional_solver --stage conditional_solver_v1
```

Commit sources before running the study. The common runner freezes source and
configuration, binds one BLAS thread and caps wall time at 600 seconds. Every
attempt has a fresh immutable directory, including failures. N1024 here means
only this complete finite-node block message, not N1024 decoding or FER.
