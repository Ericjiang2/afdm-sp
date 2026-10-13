# Collision information and observation-only estimation

This module studies equal independent proper complex Gaussian path gains with
total variance tau, a common fixed integer delay, center mu and half gap delta.
The two Dopplers are mu-delta and mu+delta, and **q=delta²**. Delay/model order
are supplied design restrictions; this is not unknown-support discovery.

For fixed data x (an oracle object), write a(nu)=U(nu)x. Gain elimination gives

\[
K=\sigma^2I+\frac\tau2(a_{\mu-\delta}a_{\mu-\delta}^H+
a_{\mu+\delta}a_{\mu+\delta}^H),\quad
K_q(0)=\frac\tau2(a''a^H+2a'a'^H+aa''^H).
\]

There is no free jet prior. The remainder is O(q²). Using the full gap squared
would divide this coefficient by four. `CollisionModel` also accepts an
observation-independent cavity mean m and diagonal variance v. It uses
X=mm^H+diag(v) inside the same covariance. With unknown QPSK data this defines
a **second-moment Gaussian working likelihood**, not the exact QPSK likelihood.

The implementation applies the existing physical inverse DAFT and exact CPP
delay to X once. In time coordinates, with omega_ij=2 pi (i-j)/N,

\[
K_{ij}=\tau C_{ij}e^{i\omega_{ij}\mu}\cos(\omega_{ij}\sqrt q)
+\sigma^2\mathbf1_{i=j}.
\]

Its q derivative is evaluated with sinc at zero, without a jitter parameter.
The nuisance directions are center, total power and noise variance. For a
proper complex Gaussian, the Fisher matrix is
I_ab=Re tr(K^-1 K_a K^-1 K_b), **without the real-Gaussian factor 1/2**.
Whitening each derivative by K^-1/2 turns this into a real Frobenius Gram matrix.
The code independently compares its least-squares nuisance projection with
I_qq-I_qλ I_λλ^† I_λq. Rank deficiency is permitted, not regularized away.

Important limits:

- With no pilot, uniform zero-mean data and fixed total gain power,
  K=(sigma²+tau pd)I. Both center and q derivatives are exactly zero in this
  second-moment model. This says nothing about information in higher moments.
- A two-sample known-data example has positive raw I_qq but its q direction
  lies in the total-power/noise span; effective information is zero.
- For delta>0, I_eff(delta)=4 delta² I_eff(q). q>=0 is a nonregular boundary at
  collision. No ordinary interior-point CRLB or newly created information is
  claimed by changing coordinates.

`estimate(model,y,coordinates,search)` receives no truth. Its fixed full domain
is mu in [-1.5,1.5], half gap in [0,.6], power in [.05,5], noise in [.01,2].
Both coordinates evaluate the same 13x7 coarse physical grid and take the same
four best starts into SLSQP, using the same objective and analytic gradient.
Original two-path coordinates enforce ordering, center and gap with linear
constraints. Center/q uses rectangular bounds. The collision starts expose
the original gap's zero gradient; multistart reduces but does not prove removal
of optimization failures. A best coarse point is an explicit candidate when
local optimization is worse, labeled unsuccessful rather than converged.
All starts, failures, boundaries, grid scores and evaluations are retained.
Nonidentifiable models return no center/q estimate; their stored grid objective
uses the declared fixed initial nuisance values and is not a fitted optimum.

The estimation study generates actual QPSK with Gaussian gains, then fits this
working covariance model. Pilot-only uniform, fixed legal soft-cavity, and
no-pilot uniform cases share exogenous draws across geometry/noise and the two
coordinate algorithms see identical y. Soft I/Q probabilities are fixed before
y and obey |E d_R|,|E d_I|<=.5; variance=.5-|E d|². Truth is saved only beside
the observation for scoring. The 144 records include only three exogenous
clusters, so record count is not an independent sample size or FER study.

Run after committing bound source bytes:

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 /tmp/afdm-shared-channel-env/bin/python -m unittest experiments.afdm_shared_channel_20261004.test_collision -v
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 /tmp/afdm-shared-channel-env/bin/python -m experiments.afdm_shared_channel_20261004.collision information --stage collision_information_v1
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 /tmp/afdm-shared-channel-env/bin/python -m experiments.afdm_shared_channel_20261004.collision estimation --stage collision_estimation_v1
```

The common runner freezes configuration, sources, effective thread binding and
a 600-second cap. Each named stage is immutable. Saved covariance derivatives
and observation/grid arrays support independent replay. These are local
mathematical/estimation diagnostics, not a production receiver.

Initial implementation-test failures were a duplicate result-key merge and a
floating-point literal equality in a test (difference 1.11e-16); both were
reproduced and corrected before registration. They were not receiver defects.
