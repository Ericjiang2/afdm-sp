# Positive fixed-prior integration and legal response

`quadrature.py` approximates a declared, observation-independent gain prior. Tensor Hermite nodes represent proper Gaussian gains on their exact PSD support; phase/Legendre nodes represent uniform complex-sphere gains for P=1/2. All weights are positive and normalized. Point caps are checked before enumeration. Independent scrambled Sobol Gaussian draws, normalized for the sphere case, provide a second integration family. Discrete data nodes remain on the original QPSK support; repeated data states correspond to distinct gain nodes, not new symbols.

For real-augmented data state s and response f, the reused finite potential is

\[
\Psi(\eta,\xi)=\log\sum_k w_k\exp\{\eta^Tf_k-\|f_k\|^2/\sigma^2+\xi^Ts_k\}.
\]

The fixed normalized base gives `partial_xi Psi=E[s]`, `partial_xixi Psi=Cov(s)`, and `partial_xieta Psi=Cov(s,f)`. With `eta=2 y_R/sigma²`, the receiver source response at fixed base is `2 Cov(s,f)/sigma²`; it is not generally `2 Cov(s,s)/sigma²`. Binary coordinate support implies `Var(s_j)=a²-E[s_j]²` and covariance is positive semidefinite. Central finite differences separately test the mean, covariance and mixed response identities.

The full complex Gaussian likelihood includes the additional constant `-||y||²/sigma²-N log(pi sigma²)`, absent from Psi but retained by `conditional_scores`. Candidate posterior normalization can cancel common constants; absolute model evidence cannot drop them. The integration base comparison saves full normalized density scores against the independent analytic Gaussian-gain integral and an independent Sobol rule.

For a moving base, nodes, responses or states, write unnormalized log weights as `ell_k(y)`. The total derivative is

\[
\frac{d E[s]}{dy}=E[\partial_y s]+\operatorname{Cov}(s,\partial_y\ell),
\]

where `partial_y ell` includes `partial_y log w`, source terms, `eta^T partial_y f`, `-2 f^T partial_y f/sigma²`, and `xi^T partial_y s`. With fixed s,f and normalized `w_y proportional w exp(alpha*y*s_1)`, the missing term in the first-coordinate response is exactly `alpha Var_post(s_1)`. The counterexample saves both the incorrect fixed-base response and the corrected finite-difference match. Learned observation-dependent geometry would likewise require its full chain derivatives; stop-gradient partial responses do not establish a total Onsager correction.

Changing arbitrary complete-state weights changes the prior; it is not approximation of the originally fixed model. This module neither learns such weights nor hides normalization changes. Positive weights and legal support guarantee internally consistent probabilities, not closeness to the true posterior. Finite exponential-family identities and positive quadrature are classical; this is an integration tool for the shared-channel test, not an independently novel inference method.

```sh
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 /tmp/afdm-shared-channel-env/bin/python -m experiments.afdm_shared_channel_20261004.quadrature --stage message_v1
```

The registration is immutable and precedes work. Raw finite-state responses and derivative arrays, analytic density comparisons, independent nodes, refinement errors, and every attempt status are retained under the current Mission's `execution/message_v1`. Full probability-study refinement and independent-rule checks are in the separate probability stage.

The completed `message_v1` stage took 0.0723 seconds. Mean/covariance/mixed finite-difference maximum errors were 2.07e-11, 1.19e-11 and 1.41e-11; the binary-support variance identity error was 1.94e-16. In the moving-base example, total response was 0.46793942 versus fixed-base 0.05623693, with missing chain term 0.41170249 and corrected residual 2.59e-11. Gaussian density errors fell from 0.0031036 (order 5) to 9.10e-6 (order 9) to 1.06e-7 (order 13); independent Sobol error was 7.11e-7. This verifies the declared integration and response contracts, not a deployable receiver or new algorithm.
