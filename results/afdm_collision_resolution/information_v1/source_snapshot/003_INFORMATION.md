# Registered collision information study

`INFORMATION_CONFIG.json` freezes four distinct populations: mu=.27/.35,
tau=1, sigma2=.2/1, N=4. Each receives 2048 independent actual P0 observations;
first 1024 fit nuisance projections and score regressions, last 1024 evaluate
them. Populations and splits are never pooled. Total new observations: 8192.
The stage reserves 600 seconds, local single-thread CPU, no receiver, decoder,
remote/GPU work or confirmation stream. Source and theory bytes must be committed
and teacher/density qualification established before the parent starts it.

The primary output is the exact finite-QPSK/phase-eliminated score in coordinates
(r,mu,log_tau,log_sigma2). Every observation receives nuisance-density finite
difference checks at steps 1e-4, 5e-5 and 2.5e-5; absolute score discrepancy
must be <=3e-5 to be called numerically qualified. Unqualified observations are
retained in all raw summaries and carry their flags; no survivor-only summary.

Full-score nuisance projection uses an uncentered least-squares fit on the
training score, with rank cutoff 1e-10. Its frozen coefficient is applied to
heldout scores. Raw and residual second moments, score means, residual means,
Grams, ranks and singular values are saved for both splits. Eight consecutive
equal batches within each split give descriptive standard errors. The predeclared
four-standard-error positivity flag is a diagnostic, not a population Fisher
certificate, a confidence theorem, or an estimator guarantee. It also does not
remove finite training-projection error.

The two fixed moment spaces are all four coordinate powers, and those powers
plus all ten quadratic power products. No feature is selected after data access.
For each space, save analytic finite-sum means M, covariance V and derivative
matrix D. With the declared PSD support and no jitter,

    G = D^T V^+ D,
    beta = G_nuisance^+ G_nuisance,r,
    a = V^+ (D_r-D_nuisance beta).

The signed witness a has moment derivative a^T D_r and nuisance derivative
vector a^T D_nuisance; variance a^T V a is independently saved. These formulas
characterize optimal linear moment information under the density theorem.
Numerical nonzero residual is recorded without promoting it to a rigorously
rounded lower bound. Every covariance eigenvalue, retained rank, condition,
Gram and nuisance coefficient is saved. The analytical projection is applied to
the observed centered features and evaluated independently on heldout rows.

A separate regression of all four scores onto population-centered and
variance-scaled moment features is fit on the training rows. Its matrix and
predictions are saved, with heldout MSE and residual second moments. This is a
finite linear regression diagnostic; its squared predicted score is not called
exact information of the complete feature statistic. The heldout score/feature
cross-moment is compared with the analytic D, with each cross-product's batch SE.

Artifacts per point: latent/observed replay inputs, public point, complete teacher
components and PDP mixture, all scores and FD arrays, fixed split projections,
14-dimensional moment means/covariance/derivatives, both feature matrices,
regression models and predictions, and complete JSON statistics. Output costs
include sampling, teacher plus all FD evaluation, moment construction, fitting,
serialization and stage-recorded complete cost. The run returns all four points
and every instability/failure; no new seed or substitute population is allowed.

Entry point after parent-controlled commit/admission:

    python -m experiments.afdm_collision_resolution.information_study --stage information_v1

This study does not choose a deployable unknown-nuisance estimator, prove finite
sample efficiency, certify exact Fisher information numerically, or establish an
advantage over a production receiver.
