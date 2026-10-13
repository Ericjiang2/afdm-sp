# Shared local potential: trained comparison and legality result

The registered experiment trained six networks and one scalar step correction.
The shared potential improved two squared-error metrics relative to independent
heads on the primary held-out geometries, but neither network family delivered
valid finite-support moments over its complete test cohort. A legal one-scalar
mean-field correction was more accurate than either network in this experiment.
This is evidence about these small local architectures and this finite teacher,
not a rejection of learned inference or a production receiver result.

Evidence: [frozen design](../../.mission/20261003_10-41-29-afdm-structured-inference-exploration/learn_config.json),
[run registration](../../.mission/20261003_10-41-29-afdm-structured-inference-exploration/execution/learn_v1/registration.json),
[results](../../.mission/20261003_10-41-29-afdm-structured-inference-exploration/execution/learn_v1/results.json),
[complete cohort metrics](../../.mission/20261003_10-41-29-afdm-structured-inference-exploration/execution/learn_v1/metrics.json),
[training curves](../../.mission/20261003_10-41-29-afdm-structured-inference-exploration/execution/learn_v1/training.json),
[tests](../../.mission/20261003_10-41-29-afdm-structured-inference-exploration/execution/learn_v1/tests.json).
`dataset.npz`, 24 geometry NPZs, six checkpoints, and every prediction are retained
beside the registration. No failed cohort, initialization, or transformed sample
was removed. The registration binds the design and all teacher/training sources.

## Experimental unit, teacher, and objective

The teacher is the exact 256-state `N=2, P=2` finite bilinear model from
POTENTIAL-01, with QPSK data and four-point gain priors. It is neither a
Gaussian-gain integral nor a production approximation teacher. Source derivatives
were independently checked to approximately `2.2e-11` in POTENTIAL-01; the errors
below are much larger than that finite-difference numerical scale.

There are 12 training, 4 validation, and 8 test geometry clusters, with 8
observations each. Independent random streams are 70/71/72 under the frozen
namespace. A source `xi~N(0,0.35² I)` tilts the legal finite prior before a random
gain/data state is drawn; observations use complex noise variance 0.7. This is
random-word generation, not all-zero codeword training. Test geometries comprise
four unseen negative-center clusters and four unseen positive-center/nontrivial
CPP clusters. No old 48-condition trajectory was split into train/test data.

The 64 path-permuted and 64 jointly phase-transformed test observations reuse
the original 64 test observations. They are paired equivariance diagnostics,
not additional independent samples. Uncertainty uses a stratified bootstrap over
the eight geometry clusters, keeping four clusters from each test family and
averaging the three network initializations before resampling. These are
descriptive intervals from a small development experiment, not confirmatory
power or multiplicity-controlled production evidence.

Every network receives the same 33 real inputs: `eta/4`, `xi`, the two physical
operators, pilot, and noise variance. Targets are the eight components of
`E[z]` and the eight components of `Cov(z,f) v`, with
`v=(0.5,-0.5,0.5,-0.5)`. The loss is their two mean squared errors summed. The
mixed derivative restores the factor `1/4` from the normalized eta feature;
its units are natural-source response, not observation response. Multiplication
by `2/sigma2` would convert to the corresponding observation-direction response.

## Architectures and controls

The shared model is a 32-unit smooth convex scalar potential with positive
softplus output weights. Its gradient in `xi` gives the mean; its mixed
eta/xi derivative gives the response. It has 1,121 trainable parameters, including
the additive partition constant that is unidentifiable from derivative-only
targets. The independent model has a 22-unit tanh hidden layer and 16 independent
mean/response outputs, with 1,116 parameters. These capacities differ by less
than 0.5%, but activation and derivative parameterization also differ: this is
not an isolated causal test of just one abstract constraint.

All six networks use the same 96 training examples, 200 full-batch Adam steps,
learning rate 0.01, and three frozen initializations. The final checkpoint is
always used; validation losses are diagnostic and do not select epochs or
hyperparameters. Final training losses are 0.00232–0.00237 for shared and
0.00334–0.00448 for independent models; final validation losses are
0.00822–0.00932 and 0.01157–0.01359, respectively. Actual model execution order
was randomized and retained.

The analytic control is one parallel binary mean-field update, initialized with
uniform product cavities. For coordinate `j`, let `B_j` be the difference of
the expected log physical factor conditional on `z_j=+0.5` versus `-0.5`, with
all other coordinates uniform. Its output is

`logit_j = xi_j + alpha B_j`,
`m_j = 0.5 tanh(logit_j/2)`,
`response_j = 0.25 sech²(logit_j/2) alpha (Delta E[f])_j^T v`.

`alpha=1` is analytic. A second control learns only the positive scalar alpha
using the identical 200-step objective, obtaining `alpha=0.429495`. These outputs
define a legal product distribution on the finite support and preserve the
diagonal moment identity. Their cavity approximation remains an approximation
to the exact joint posterior; the fitted alpha is a local correction, not a new
production algorithm. The exact teacher is also retained as a reference method.

The mean-field response is the derivative of its approximate update map. It is
not asserted to equal `Cov_q(z,f_original)` under that product distribution:
the uniform-cavity log-factor projection changes the source model. Thus this
control supplies legal finite-support messages and an accurate approximate JVP,
but is not certified as the original physical log-partition or an Onsager term.

These networks consume one fixed `N=2, P=2` local factor. They are not a global
`N=1024` network and construct no production Hessian. Their ordered operator
features are not path-permutation equivariant. The analytic and scalar controls
are equivariant; the transformed neural results diagnose the missing structure,
not an impossibility of a shared/equivariant local potential.

## Held-out results

| Method | Mean MSE | Response MSE | Expected bit Brier | Expected bit log score |
|---|---:|---:|---:|---:|
| Shared scalar, three seeds averaged | 0.02658 | 0.001762 | not admitted | not admitted |
| Independent heads, three seeds averaged | 0.03090 | 0.001956 | not admitted | not admitted |
| Analytic mean field, alpha=1 | 0.02894 | 0.000907 | 0.27433 | 0.74815 |
| One learned positive step | 0.01393 | 0.000656 | 0.24941 | 0.69214 |
| Exact finite teacher | 0 | 0 | 0.22787 | 0.64619 |

The paired shared-minus-independent mean MSE difference is -0.004318, with a
descriptive 95% cluster interval [-0.005110,-0.003455]. The response MSE
difference is -0.0001941, interval [-0.0003448,-0.0000411]. Thus the shared model
has a limited predictive benefit over the chosen independent architecture on
these untransformed test geometries. It does not beat the smaller legal step
control. Its product-sign action posterior-mass regret is 0.08310 versus 0.07690
for independent heads; the paired difference interval includes zero.

All proper scores use exact posterior-conditional expected bit scores, not
training labels or only successful cases. One invalid predicted probability
invalidates the **entire model/initialization/cohort** for proper scoring. The
main cohort has 1–2 invalid observations out of 64 per shared seed and 1–4 per
independent seed; no network receives a proper score and no values were clipped.
Mean/response/action errors still include all 64 observations.

The shared Hessian is PSD and symmetric to roundoff, and its source-response
finite differences agree to at most `8.94e-12` on the main cohort. Nonetheless,
its maximum discrepancy from the necessary finite-support identity
`Cov(z_j,z_j)=0.25-E[z_j]²` is 0.239–0.324. PSD/integrability therefore do not
provide the missing finite-posterior legality. Independent heads additionally
have response-versus-mean-Jacobian discrepancies of 0.131–0.174 and do not output
a covariance matrix.

For path permutations, shared versus independent mean MSE is 0.14206 versus
0.08553; for the joint phase transform it is 0.06609 versus 0.06006. Shared
response MSE remains lower in these particular tests, but neither family is
equivariant or support-valid. The analytic and scalar-control metrics are
unchanged under the two transformations to numerical precision. The phase test
rotates the pilot and prior/source with the latent variables, as required; it
does not claim a free phase symmetry with a fixed nonzero pilot.

The hard-action metric selects the legal state given by `sign(mean)` and scores
its exact posterior mass. It is not joint MAP decoding. Even the exact
posterior's marginal-mean action has nonzero joint-mode regret (0.03484), because
joint and marginal modes need not agree. This distinction prevents assigning a
false zero mode error to the teacher.

## Cost, validation, and feedback

Five fresh contract tests verify natural-source derivative units, backward
gradients through the mixed derivative, actual parameter counts, the analytic
prior limit, equivariance of the finite teacher, and whole-cohort rejection of
invalid probabilities. The registered run completes in 0.552 CPU / 0.637 wall
seconds with one verified thread, within the 300 CPU / 420 wall cap. Teacher,
raw-data, training, automatic differentiation and analysis work are included.
The 320 direct finite-teacher evaluations cost 0.0324 seconds; total dataset
construction and output cost 0.1069 seconds. Each shared fit takes roughly
0.058 seconds, independent fits roughly 0.026 seconds, and the one-scalar fit
0.0243 seconds. These are shared-machine microtimings, not isolated deployment
latencies. Checkpoint loading and production initialization/LDPC do not occur
inside a deployment benchmark here.

The original batched neural output path includes mean and automatic mixed
derivatives, not just `network.forward`. Those kernel measurements are superseded
for local inference-cost interpretation by the frozen-weight follow-up below.
Equal training steps and nearly equal parameter counts still do not imply equal
inference budgets.

### Frozen-weight full local cost audit

The [cost registration](../../.mission/20261003_10-41-29-afdm-structured-inference-exploration/execution/learn_v2/registration.json)
and [cost results](../../.mission/20261003_10-41-29-afdm-structured-inference-exploration/execution/learn_v2/results.json)
bind the original registration, training/teacher sources, 64 saved main-test
observations, geometry files, and six checkpoints. No source/weight was changed,
no observation was generated, and no training was repeated. Its own 30 CPU / 60
wall limit is enforced with CPU/wall timers inside the looser common stage cap.
The audit completes in 0.987 CPU / 1.062 wall seconds.

Starting from supplied local center/stride, pilot/noise, complex observation and
source, each cold call reconstructs the actual two CPP operators. Neural calls
then build all 33 physical features and run the single-observation mean/JVP
output path, including autograd for the shared potential. Mean-field calls also
construct 256 physical-state responses and their cavity statistics. Exact calls
construct those responses and invoke the actual public finite-moment API. The
second condition builds the geometry-dependent work once and charges exactly
one eighth of its measured cost to each of the same geometry's eight observed
records. Neither condition uses free physical-feature preprocessing.

| Actual method | Cold geometry, median microseconds/observation | Geometry cost amortized over 8 observations |
|---|---:|---:|
| Shared potential, range across three seeds | 196.9–198.6 | 95.1–97.6 |
| Independent heads, range across three seeds | 133.2–137.3 | 32.1–32.7 |
| Analytic mean field | 270.9 | 40.1 |
| Learned positive step | 266.6 | 40.6 |
| Exact finite moment API | 260.1 | 130.3 |

There are three randomized timing repeats, 192 calls per method/cache condition,
and 3,456 calls in total. These repeat the same 64 observations; they do not
increase the statistical sample size. Every output is checked against its
saved prediction: maximum mean error is `3.68e-16`, maximum JVP error `1.70e-16`.
Per-call preprocessing, prediction, total time, and parity errors are retained
in [cost_records.json](../../.mission/20261003_10-41-29-afdm-structured-inference-exploration/execution/learn_v2/cost_records.json).

This cost evidence changes the interpretation of the smaller learned control:
it is faster than the shared potential when its geometry statistics are reused
over these eight observations, but its cold statistic construction is more
expensive. The independent head is faster than both in the amortized condition
while retaining its reported accuracy/legality limitations. The shared model's
small MSE benefit over independent heads therefore comes with higher actual
local inference cost. None is established as an equal-budget production winner.

The per-call boundary excludes support/geometry discovery, interpreter/library
startup, checkpoint loading, file IO, LDPC, and receiver-global initialization.
Startup/model-load times are separately recorded; first checkpoint/model setup
costs 12.1 ms, subsequent model loads 0.25–0.34 ms. Parameter storage is 8,968
bytes per shared model and 8,928 bytes per independent model in float64. Whole
audit-process peak RSS is approximately 315 MiB and includes torch, all arms,
the dataset and audit storage; it is not a per-model deployment memory figure.
The exact API computes small covariance blocks beyond the requested mean/JVP,
so its measured cost is an implementation cost, not an intrinsic lower bound.
These are local `N=2, P=2` shared-machine timings with supplied geometry; no
`N=1024`, production latency, FER, or complete-receiver cost claim follows.

Supported: the chosen shared derivative parameterization has smaller primary
mean/JVP error than the chosen independent heads after real fixed-budget training.
It also satisfies the mathematical consistency its architecture was designed to
provide. These claims are local and architecture-specific.

Not admitted: either trained neural model as a finite-support soft posterior.
The counterexample consists of actual held-out predictions, not an untrained
architecture argument. The underlying legal finite potential from POTENTIAL-01
remains available, and the positive one-scalar mean-field correction is a legal
trained alternative that performs better on the measured errors and proper
scores here.

No extra training was launched merely to improve these results. Canonicalizing
path labels could address the transformation mismatch but would not repair the
shared model's finite-support moment contradiction. A support-preserving local
log-sum-exp factor or an explicitly equivariant local model would be a distinct
mechanism revision requiring its own contract; the current results do not say
either is futile. The learned step's possible production relevance and novelty
remain SELECT/TRANSFER questions under the unchanged scientific/resource gates.
