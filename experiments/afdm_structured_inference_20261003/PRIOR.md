# PRIOR-01: representation conservation

Result: **supported within the stated Gaussian working model**. Correct
pushforward preserves exact inference. The current scalar joint approximation
changes under balanced redundant splitting even when that physical prior is
preserved. Neither finding establishes a production error rate effect.

## Contract and provenance

Entry point: `python -m experiments.afdm_structured_inference_20261003.prior`.
Run: `.mission/20261003_10-41-29-afdm-structured-inference-exploration/execution/prior_v1/`.
Registration, source hashes, effective one-thread binding, per-case raw NPZ,
per-arm receiver trajectories, results and attempt cost are retained there.
No frozen source, old result, decoder, production receiver or remote job was
changed or called. The exact oracle and true CPP Channel action are imported.

Six conditions use three independent new exogenous draws, each paired across
two geometries. N=3, U and V have distinct fractional Dopplers; one geometry
also has distinct delays and the other shares delay 1, exercising CPP wrapping.
All legal uncoded QPSK words are enumerated. Noise variance is 0.2 and pilot
amplitude is 0.6. These are mathematical cases, not six independent trials or
samples from the normalized production generator.

## Exact model conservation

For alpha=T beta, use D_beta=D_alpha T and require
`T m_beta=m_alpha`, `T C_beta T^H=C_alpha`. A right-inverse support prior uses
`m_beta=T^+ m_alpha`, `C_beta=T^+ C_alpha (T^+)^H`. An independent Gaussian in
the nullspace changes coordinates but does not change H. Both the singular
support prior and a full-support redundant prior are tested. For zero-mean iid
alpha variance 1/2, the full-support split is exactly
`diag(1/4,1/4,1/2)` on `(a1,a2,b)`.

Tests cover invertible complex coordinate mixing, repeated U columns, nonzero
mean and correlated covariance. Predictive covariance includes both gain and
data uncertainty and the nonzero-mean contribution, not merely B C B^H for one
chosen word. Mean/covariance pushforward, prior predictive mean/covariance,
exact evidence, exact bit LLRs and physical posterior moments agree with maximum
absolute/norm error **8.8818e-15**, below the frozen **2e-11** tolerance.

Splitting only U and automatically applying iid 1/P is a different model:

| Representation | Induced covariance of (a,b) | Exact LLR L2 difference from UV |
|---|---|---:|
| UV, iid 1/2 | diag(1/2,1/2) | 0 |
| UUV, iid 1/3 | diag(2/3,1/3) | 0.09267–1.84052 |
| UUVV, iid 1/4 | diag(1/2,1/2) | at most 2.5122e-15 |

The UUV prior-predictive covariance Frobenius difference is 0.25118 in the
separated geometry and 0.03277 with the shared delay. This is a modeling
difference, not numerical error. Genuine extra scatterers need not obey a
redundant-representation invariance requirement.

## Actual interface and approximation error

The unchanged `twofft.scalar_joint` hardcodes iid CN(0,I/P). It cannot consume
the general transported covariance. Rather than invent an alternate interface,
the UV/UUVV pair uses priors that are both legal in the actual interface and
induce exactly the same physical H distribution. Both start from the same
physical H (maximum construction difference 2.31e-16), receive the same y,
pilot and zero bit prior, and perform 20 iterations with damping 0.3.

Across all six cases, UV versus UUVV final scalar LLR L2 differences range from
**0.06695 to 1.19304**. The aggregated gain means already differ after the first
iteration by **0.00494–0.02174**, which is far above initial rounding error.
The exact physical model remains invariant throughout this comparison.

This localizes a real approximation sensitivity: duplicate regressors have
nonzero cross information, while the scalar gain update uses one diagonal
variance and scalar pseudo precision per slot. Splitting changes its shrinkage
tau from 1/2 to 1/4 and the per-coordinate pseudo observations. Summing the
duplicate scalar updates does not reproduce the unsplit update. Correcting
the input prior alone cannot establish representation-invariant messages.
It is not evidence that one representation is systematically better.

## Cost, limits and feedback

There were exactly 18 scalar calls, each with 20 iterations and 41 FFTs. Arm
order rotates across seeds. Per-arm elapsed times including Channel and path
preprocessing, the complete scalar call, trace collection and raw saving range
from 4.782 to 5.461 ms; the complete branch used 0.329 CPU seconds and
0.367 wall seconds. The shared machine and tiny instrumented cases make these
cost accounting observations, not deployment timing. Inputs/operator/oracle
construction are outside per-arm timing and inside branch timing. There is no
decoder in this interface; peak memory was not isolated. Equal iteration/FFT
counts do not mean equal arithmetic or wall budgets, so there is **no
same-time performance claim**.

Feedback: preserve the physical prior when changing coordinates, then address
joint path covariance / sufficient-statistic contractions at the message
interface. The balanced-split counterexample gives a concrete contract for a
future candidate. This work did not implement a new receiver, tune a prior to
win, or determine how often redundancy causes production errors. Those remain
separate admission and transfer questions; the prior direction is not ruled out.

Validation: the focused unittest suite independently checks finite conditional
probabilities and Gaussian pushforward, then recounts all six saved prior cases
and the unchanged receiver's saved first/final trajectories without rerunning
it. Registration/source checks and the branch's identity gate passed.
