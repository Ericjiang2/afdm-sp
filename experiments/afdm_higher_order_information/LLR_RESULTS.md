# Controlled LLR integration results

The frozen `llr_v1` study completed all 48 cases, 12 distinct observations and 2,304 message estimates. All 48 reference integrations met the registered gates. Gaussian and controlled isotropic-sphere priors remain distinct from the actual production prior. The two likelihood objects are compared separately; an accurate Gaussian-outside integral is not called the exact QPSK likelihood.

The source commit was `09bfc7bc`. The attempt verified Apple Accelerate single-thread mode 1. Whole-stage wall time was 162.444 s and CPU time 162.296 s; whole-process peak RSS was 493.4 MB. Reference-node setup took 0.460 s, independent/reference likelihoods 149.551 s, and complete message estimates including raw persistence 11.866 s. One-time fixed geometry construction was recorded separately. These are local instrumented mathematical costs, not production receiver latency.

## Fixed-threshold comparison, independently recounted

Each entry below is the cheapest tested budget meeting the same full-group precision gates: LLR RMSE <= .05, 95th-percentile absolute LLR error <= .1, and both-side relative-density RMSE <= .05. All groups include the full registered observation/cavity population and all four estimator replicates. Candidate pilot nodes are included in its budget.

| Prior / object | Fixed common Sobol | Defensive contrast candidate | Interpretation |
|---|---|---|---|
| Gaussian / QPSK | 4096 nodes, 15.288 ms | 4096 nodes, 15.741 ms | Candidate passes, but Sobol is more accurate and no more costly |
| Sphere / QPSK | 4096 nodes, 15.350 ms | No admitted tested budget | Candidate at 4096 has p95 .10421 and density RMSE .05024 |
| Gaussian / Gaussian-outside | 1024 nodes, 1.806 ms | 4096 nodes, 6.240 ms | Existing fixed common rule is substantially cheaper at the registered precision |
| Sphere / Gaussian-outside | 4096 nodes, 5.842 ms | 4096 nodes, 6.325 ms | Sobol has smaller errors and lower measured cost |

The candidate improves some errors relative to ordinary IID prior sampling, but that alone is not a fair novelty or utility test: the existing fixed common Sobol rule is a required baseline. Independent-side IID did not pass any group at the tested budgets. Common-prior IID passed both Gaussian-outside groups at 4096 and failed both QPSK groups. In the sphere Gaussian-outside group, common-prior IID's 5.674 ms versus Sobol's 5.842 ms is a small local timing difference with different error margins; no robust speed ordering is claimed from that difference.

Some thresholds are close. The separate immutable `llr_recount_v1` recomputed true base pi/rho corrections using dense inverses and determinants, independently reconstructed likelihood means, and verified population counts and the leaf-work/factorization/byte/cost ledgers. It checked all 2,395 source artifact hashes, all 48 cases, all 12 observation identities, and all 2,304 message cells. No nodes or observations were generated. Maximum errors were 7.11e-15 for pi/rho log correction, 3.55e-15 for log likelihood means, 1.11e-15 for probabilities and 1.47e-15 for full-group quality metrics. The complete message cost sum matched exactly.

Every stored admitted reference was used to repeat the unchanged precision tests. All 48 arm/budget/prior/object group classifications were stable; none was reference-sensitive. Gaussian QPSK retained its analytic reference. Gaussian-outside under Gaussian gains used Hermite 33, Sobol 2^18/2^19 and an independent 2^19 scramble. Both sphere objects used sphere rules 13/21 plus the three Sobol references. The sphere-QPSK candidate at budget 4096 remained unqualified: its p95 absolute LLR error ranged from .103780 to .104303, and density RMSE from .050116 to .050293, both above their original thresholds. The sphere Gaussian-outside Sobol arm at budget 1024 also remained unqualified, with p95 .100876–.101117; it was not promoted across the .1 boundary.

These ranges are empirical variation across stored numerical references, not certified integration-error bounds or statistical confidence intervals. The four repetitions share the same 12 observations and three exogenous gain/data/noise draws; neither the 2,304 messages nor multiple cavities are independent communication frames. No threshold was relaxed and no successful subset was scored. The saved-only recount took 1.639 s under committed source `8ed52730`.

## Evidence and reproduction

Original immutable registration, snapshots, all message nodes/log likelihoods/proposal data and costs are under `results/afdm_higher_order_information/llr_v1/`. `LLR.md` and the producing sources remain unchanged. Reproduction uses a new stage name after source admission:

```sh
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 /tmp/afdm-shared-channel-env/bin/python -m experiments.afdm_higher_order_information.llr_study --stage llr_new_attempt
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 /tmp/afdm-shared-channel-env/bin/python -m experiments.afdm_higher_order_information.llr_recount --stage llr_recount_new_attempt
```

The bounded verdict is no demonstrated superiority for this proposal over fixed common Sobol. It does not refute importance sampling in general, establish a high-dimensional result, or change the existing higher-order-information model limitations. The theorem's IID/finite-variance assumptions are separate from the empirical QMC refinement checks.

Eight likelihood-ratio/proposal contracts, three recorder contracts and three independent-recount contracts passed. The recorder's uncommitted-source rejection prevented a study from silently binding uncommitted new-package code. The mathematical statements remain classical identities/conditional IID results; the adaptive candidate should be narrowed to a tested negative engineering result at N=3/P=2, not presented as a new superior LLR algorithm.
