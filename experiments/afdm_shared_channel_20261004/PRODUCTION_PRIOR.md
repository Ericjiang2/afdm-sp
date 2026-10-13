# Actual production gain normalization

This NORMALIZATION-01 audit uses only the three previously saved channel
clusters. Physical geometry and recovered latent PDP are **offline oracle
inputs**. They are not delivered to any receiver. No receiver, decoder,
`make_frame`, `generate_channel_matrix` or observation generation is called.

## Source law

All source references below are inside the frozen
`experiments/sp_afdm_frozen_20260920/upstream/spafdm_receiver_handoff/` tree.

1. `afdm_sp_joint_unrolled/afdm_env.py:311-332` draws exponential delay
   increments, sets the conditional PDP `d_i=exp(-alpha*delay_vec_i)`, draws
   independent Rayleigh amplitudes with scale squared
   `2*d_i/(4-pi)` and independent uniform phases, then divides amplitudes by
   their Euclidean norm. Thus before that division the complex vector is
   proper Gaussian with covariance `4 D/(4-pi)`, where D=diag(d).
   The common multiplier cancels every subsequent radial normalization.
   **This direction is not isotropic unless D is scalar.**
2. `afdm_env.py:337-358` conditions acceptance on delay/velocity support,
   with the documented final-attempt clipping branch. It does not accept or
   reject based on gain amplitude. Conditional on the realized latent PDP
   and geometry, the amplitude/phase law above therefore applies.
3. `afdm_env.py:586-612` normalizes each complete local Dirichlet weight
   vector, then clips out-of-range integer Dopplers and prunes weak weights.
   `budgeted_support_diagnostics.py:82-105` provides the existing exact
   physical-to-integer coefficient matrix W; this audit reuses that helper.
4. `afdm_env.py:630-641` computes the Frobenius norm of the **G0 truncated
   integer-atom matrix**, multiplies it by sqrt(N)/norm, and multiplies
   the physical gain vector by the same factor.
5. `supplement_g1.py:13-14,72-121` constructs untruncated CPP propagation
   using these same physical gains, with rule
   `reuse_g0_physical_gains_without_rescaling`.

For physical path i, let A_i be its G0 integer-atom matrix after the
weight-normalize/clip/prune sequence. Define

\[
R_{ij}=N^{-1}\operatorname{tr}(A_i^H A_j).
\]

For the legal frozen Python convention, integer delays in [0,N) and Doppler
indices without modulo-N aliases form an orthogonal Frobenius basis with
norm squared N. A coincident displacement with different integer delays
still has zero inner product by the finite Fourier sum. Consequently
`R_G0=W^H W`; overlapping physical paths retain complex off-diagonal terms.
An independent dense contraction using the actual `gen_h_daft` verifies
this identity, including same-delay overlapping fractional clusters.

If g is the initially Euclidean-normalized gain direction, the production
output is

\[
h=\frac{g}{\sqrt{g^H R_{G0}g}}.
\]

Writing z~CN(0,I) and s=z/||z||, both radial divisions cancel, giving

\[
\boxed{
h=\frac{D^{1/2}s}
{\sqrt{s^H D^{1/2}R_{G0}D^{1/2}s}}.
}
\]

The pushforward `s/sqrt(s^H R s)` is correct only for isotropic raw gains.
The uniform unit sphere is the further special case D proportional to I
and R=I. A common positive scale in D does not change this law. In general
`h^H R h=1`, while `||h||²` varies; with R positive definite it lies between
`1/lambda_max(R)` and `1/lambda_min(R)`. Rank-deficient geometries require
separate integrability analysis; this audit does not claim all fourth
moments remain bounded there. Fixed finite path count, clipping/pruning and
PDP anisotropy do not supply an automatic large-N Gaussian limit.

## Saved reconstruction and numerical comparison

The archive saves g_i, `diagnostics.g0_fro_scale`, physical delays/Dopplers
and channel stream IDs, but omits `g_i_raw` and `path_var`. Division by the
saved scale recovers g_i_raw. To recover the omitted PDP, the audit follows
the original `budgeted_support_eval.make_frame:117-119` seed conversion and
replays **only** `generate_uwa_channel` on the original saved channel seed.
It preserves/restores global RNG state and requires reconstructed raw
gains, integer delays and physical Dopplers to match the archive before
using any recovered PDP. It does not replay a channel matrix generator or
generate y, noise, coded bits or another observation.

For every cluster it verifies the predicted G0 scale, h, `h^H R h=1`,
and direct G0 matrix norm. Each study condition is the realized latent PDP
plus the saved geometry; this is not a marginal over all latent PDPs that
could produce the same quantized geometry, nor the unconditional production
prior. The three cluster gain energies measured previously are 1.01601854,
1.00986004 and 1.00894574, already ruling out a strict unit-energy identity.

Positive equal-weight Sobol rules of sizes 2^12, 2^15 and 2^18, each with two
fixed independent scrambles, compare:

- old working iid CN(0,I/P) gains;
- controlled uniform unit-sphere gains;
- conditional PDP-normalized sphere gains (isolates the G0 quadratic step);
- the conditional actual G0-normalized pushforward above.

Directions include first/last path coordinates and two fixed known-pilot
response projections for the actual saved geometry. The outputs retain
second/fourth projection moments, full gain second moments and total-energy
moments. Base nodes, positive weights, exact geometry, D, R and directions
are saved for reproduction. No projection uses unknown data or truth gains.
Gaussian and sphere projections have analytic control moments
`E|u^H h|²=1/P`, respectively `E|u^H h|⁴=2/P²` and `2/[P(P+1)]`, for unit u.

For the saved distinct-delay geometries, R is diagonal, permitting an
independent one-dimensional positive quadrature. With X_i~Exp(1),
`a_i=R_ii d_i` and `L(t)=prod_j(1+t a_j)^(-1)`,

\[
E|h_i|^2=d_i\int_0^\infty\frac{L(t)}{1+t a_i}\,dt,
\]
\[
E|h_i|^4=2d_i^2\int_0^\infty
\frac{tL(t)}{(1+t a_i)^2}\,dt,
\quad
E|h_i|^2|h_j|^2=d_i d_j\int_0^\infty
\frac{tL(t)}{(1+t a_i)(1+t a_j)}\,dt\quad(i\ne j).
\]

Independent uniform phases give the full projection fourth moment by
diagonal terms plus four times each pair cross term. Gauss-Legendre orders
64/128/256 after a fixed positive map from (0,1) to (0,infinity) evaluate
these analytic integral representations. The integrals are numerically
refined references, not exact numerical answers. Both refinement and
independent-scramble/reference discrepancies are retained; a 1% relative
threshold covers the specified second/fourth projection moments. Failed
refinement stays visible rather than selecting successful cases.

Because the actual conditional second moment need not equal I/P, the old
Gaussian-pair second-moment identity remains correct for its own declared
working prior but does not establish the actual production second moment.
This prior mismatch is another confound beside mixture Gaussianization.

Validation: 9 focused tests pass, including the real frozen G0 dense matrix,
the saved first-cluster scale, anisotropic/sphere distinction, homogeneous
normalization, invalid Gram rejection and the analytic sphere limit of the
positive Laplace quadrature.

Registered command (source commit `b9eeb3a9`; completed):

```sh
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1 CUDA_VISIBLE_DEVICES='' \
/tmp/afdm-shared-channel-env/bin/python -m experiments.afdm_shared_channel_20261004.production_prior --stage normalization_v1
```

## Completed saved-geometry results

`execution/normalization_v1` completed with `all_refined=true` in 4.4685 s
wall / 4.4419 s CPU. There were zero receiver/decoder calls and zero new
observations. The original three channel streams accepted their latent draw
after 23, 26 and 1 attempts; replay follows those original rejections and
does not select a new favorable draw.

Across the three saved clusters, integer delays and physical Dopplers match
exactly; reconstructed raw gain error is at most 6.21e-17. Predicted scale
error is at most 1.11e-15, predicted physical gain error 6.68e-16, and direct
matrix-versus-Gram power error 2.23e-15. The saved gains satisfy h^H R h=1
within 2.0e-15. The smallest R eigenvalues are approximately 0.95909, 0.97441
and 0.98547; every sampled conditional prior is bounded on its ellipsoid.
The complete recovered PDP vectors, R eigenvalues and original identities
are in `identities.json` and `geometry_*.npz`.

The table uses the independently refined order-256 Laplace reference.
All directions have unit Euclidean norm. The first/last columns below refer
to original physical path order, not a gain-ranked path selection.

| Conditional prior / cluster | E\|h\|² | Var(\|h\|²) | E\|h_first\|² | E\|h_last\|² | E\|h_first\|⁴ | E\|h_last\|⁴ |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Actual / 0 | 1.015181 | 3.75975e-5 | 0.235178 | 0.067359 | 0.086435 | 0.009124 |
| Actual / 1 | 1.010727 | 8.49940e-6 | 0.182727 | 0.087060 | 0.055030 | 0.014489 |
| Actual / 2 | 1.008708 | 2.44241e-6 | 0.172331 | 0.073612 | 0.049503 | 0.010628 |
| Isotropic sphere / all | 1 | 0 | 0.125 | 0.125 | 0.027778 | 0.027778 |
| iid Gaussian / all | 1 | 0.125 | 0.125 | 0.125 | 0.031250 | 0.031250 |

Removing just G0 quadratic normalization while retaining the actual PDP
gives first-path second moments 0.230801, 0.180586 and 0.170882. Thus, for
these conditional cases, PDP anisotropy supplies most of the observed
directional second-moment difference, with a smaller additional G0
normalization effect. This is an attribution between specified prior
models and gain moments, not an attribution of production decoding errors.

Known-pilot response projections also vary. For the two registered pilot
directions, actual second moments are respectively
`[0.139581, 0.130234]`, `[0.129479, 0.125455]` and
`[0.125221, 0.127016]`; their actual fourth moments are
`[0.033222, 0.029417]`, `[0.029443, 0.027826]` and
`[0.027763, 0.028470]`. These are conditional gain/known-pilot projections,
not the unknown-data observation distribution or a bit posterior.

Maximum relative coarse/fine or independent-scramble discrepancy is
0.53844%. Fine Sobol versus the independent Laplace reference differs by
at most 0.10857%; Laplace order 128 versus 256 differs by at most 2.93e-14.
The analytic Gaussian and sphere controls differ by at most 0.16954% and
0.09720%, respectively. All 72 numerical conditions are retained. Small
negative Laplace estimates of the PDP-sphere energy variance (about
-2.5e-14) are recorded subtraction roundoff; that variance is analytically
zero. No values were silently clipped. Exported gain `covariance` arrays
estimate E[hh^H], using the known zero mean of the underlying prior;
finite-rule mean residuals are stored separately.

The saved energies of the three realized gains and these **conditional
expectations** are different quantities. Likewise, the conditional law given
each recovered PDP is not the unconditional production prior over random
geometry/PDP, and truth-derived PDP/geometry is not a deployable estimator.
The result establishes a precise production-prior mismatch for the old iid
working model; it does not prove that correcting it alone rescues FER.
