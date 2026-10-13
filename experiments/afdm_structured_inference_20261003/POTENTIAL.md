# Finite bilinear potential: verified contract and learning boundary

POTENTIAL-01 supports the source-derivative identities for an explicitly finite
bilinear working model. It does not establish an accurate scalable receiver, an
Onsager correction, or a learned closure. The finite gain prior is distinct from
the proper-Gaussian gain integral used elsewhere in this task.

Evidence: [registration](../../.mission/20261003_10-41-29-afdm-structured-inference-exploration/execution/potential_v1/registration.json),
[results](../../.mission/20261003_10-41-29-afdm-structured-inference-exploration/execution/potential_v1/results.json),
[tests](../../.mission/20261003_10-41-29-afdm-structured-inference-exploration/execution/potential_v1/tests.json).
All eight cases and their probabilities, states, physical operators, finite
differences, moments, and pseudo-covariances are retained as `case_00..07.npz`.

## Object and derivation

Let real-augmented `z=[Re(h,d), Im(h,d)]`, with finite QPSK data and an explicitly
finite four-point gain prior per path. For each state use the frozen CPP physical
operator to construct the original bilinear response

`f_C(z) = sum_p h_p U_p (pilot + d)`, `f = [Re(f_C), Im(f_C)]`.

With a normalized observation-independent base `p0`, positive complex noise
variance `sigma2`, `eta=2 y_R/sigma2`, and a source `xi`, define

`Psi(eta,xi) = log sum_s p0_s exp(eta^T f_s - ||f_s||²/sigma2 + xi^T z_s)`.

The omitted likelihood term `-||y_R||²/sigma2` is independent of `z`; it does not
affect posterior moments or the derivative of those moments. Direct
differentiation of this one normalized distribution gives

- `d_xi Psi = E[z]`, `d_eta Psi = E[f]`;
- `d_xi² Psi = Cov(z,z)`, `d_eta² Psi = Cov(f,f)`;
- `d_xi d_eta Psi = Cov(z,f)`;
- `d E[z]/d y_R = 2 Cov(z,f)/sigma2`.

The last matrix has shape `dim(z) x dim(y_R)`, here `8 x 4`. Substituting
`Cov(z,z)` would both change its meaning and give the wrong dimensions.

`finite_potential(z,f,log_prior,eta,xi,sigma2)` returns the partition,
probabilities, both means and the three covariance blocks. `source_jvp` computes
the mean JVP directly as a weighted centered-state reduction, without forming a
dense Hessian. The enumerator validates shape, real augmentation, normalized
base probabilities, finite states/sources, and positive noise.

## Registered evidence

The development geometry and a separately declared absolute-center/CPP geometry
each contain general, noncircular, known-gain, and constant-state cases. The
general cases have 256 states, known-gain cases 16, and constant cases one.
Neither geometry was selected by its result. Real augmentation retains improper
moments; the noncircular cases have gain pseudo-covariance norms 0.1684 and
0.1387. Known-gain and constant-state covariance rows vanish to roundoff.

| Check | Largest absolute discrepancy |
|---|---:|
| Partition gradient versus mean | 1.760e-11 |
| Mean source Jacobian versus covariance | 1.011e-11 |
| Mixed source derivative versus `Cov(z,f)` | 7.674e-12 |
| Matrix-free JVP versus finite difference | 6.069e-12 |
| Physical observation response | 2.193e-11 |
| Path permutation of mean | 1.111e-16 |
| Joint phase-transformed physical response | 4.441e-16 |
| Phase-transformed posterior probabilities | 6.246e-17 |

The registered finite-difference step is `2e-5` and error threshold `2e-8`.
Seven contract tests pass, including an observation-dependent-base counterexample.
The separate two-state limit `z in {-1,+1}`, `f=a z` gives
`Psi=log cosh(eta^T a+xi)-||a||²/sigma2`, mean `tanh`, and variance `sech²`;
its three checked errors are zero at the registered floating-point inputs.
This limit is not substituted for the bilinear cases.

The run used one verified BLAS thread, 0.103 CPU seconds and 0.105 wall seconds,
including tests and raw output, inside the 90 CPU/120 wall cap. These are shared
local-machine diagnostic measurements, potentially overlapping other mathematical
work; they are not isolated deployment latency or cross-method cost evidence.
There were zero production receiver, remote, GPU, or production-Hessian calls.

## Symmetry and base-measure conditions

Permuting path slots must permute the corresponding operators, gain coordinates,
source entries, and prior. The physical sum then stays unchanged. The numeric
test checks the equivalent reordered source representation.

The transformation `h -> i h`, `d -> -i d`, `pilot -> -i pilot` preserves the
bilinear physical response with the base measure pushed forward. A fixed nonzero
pilot does not generally admit this as a symmetry of the same inference problem;
the recorded check is an equivariance between transformed problems. A
nonuniform/improper prior must transform as well.

If `p0(z;y)` or learned base logits depend on the observation, the total response
also contains `Cov(z, d_y log p0)` (and derivatives of any other observation-
dependent features). The test with `f=0` and base logits `y*z` gives the nonzero
response `sech²(y)` despite `Cov(z,f)=0`. Stopping gradients through that base
would produce a false identity. Geometry-conditioned, observation-independent
base logits avoid this specific problem, but change the modeled prior unless
their interpretation is separately justified.

## Admissible learning interface and remaining question

A local finite log-sum-exp potential over **fixed legal states** can supply means,
covariances and JVPs from one distribution, and therefore preserves that support.
It may use shared local/path-permutation structure; sum over small local factors
rather than a global state enumeration when defining a scalable approximation.
Its accuracy as a receiver message still requires a cavity/tilted-factor contract
and comparison with appropriate teachers and inference baselines.

A general convex/ICNN potential guarantees necessary integrability/PSD properties,
but not QPSK support. For example `Psi(xi)=xi²/2` has symmetric positive Hessian
and mean `xi`; at `xi=2`, its mean 2 and variance 1 exceed the feasible bounds of
a QPSK real coordinate supported at `+/-0.5`. Thus consistency is not a
finite-constellation posterior certificate or an Onsager theorem.

Exact finite means/JVPs cost `O(K*(dim(z)+dim(f)))` for `K` states; `K` grows
exponentially in the full model. Explicit small-case covariances are diagnostics.
No production `N²` Hessian is required by the JVP interface. The supported result
is the legal mathematical object and its tests. Which local factorization and
learned correction improve proper scoring and complete receiver cost remains a
LEARN/MESSAGE/TRANSFER question, not a negative result for learning.
